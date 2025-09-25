import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as wafv2 from 'aws-cdk-lib/aws-wafv2';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface MavikAiApiStackProps extends cdk.StackProps {
  stackName: string;
  vpc: ec2.Vpc;
  kmsKey: kms.Key;
  apiSecurityGroup: ec2.SecurityGroup;
  ecsCluster: ecs.Cluster;
}

export class MavikAiApiStack extends cdk.Stack {
  public readonly restApi: apigateway.RestApi;
  public readonly webSocketApi: apigatewayv2.CfnApi;
  public readonly userPool: cognito.UserPool;
  public readonly webAcl: wafv2.CfnWebACL;

  constructor(scope: Construct, id: string, props: MavikAiApiStackProps) {
    super(scope, id, props);

    // Cognito User Pool for authentication
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: 'mavik-ai-users',

      // Sign-in configuration
      signInAliases: {
        email: true,
        username: true,
      },

      // Password policy
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },

      // MFA configuration
      mfa: cognito.Mfa.REQUIRED,
      mfaSecondFactor: {
        sms: true,
        otp: true,
      },

      // Account recovery
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,

      // User attributes
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
        givenName: {
          required: true,
          mutable: true,
        },
        familyName: {
          required: true,
          mutable: true,
        },
      },

      // Custom attributes
      customAttributes: {
        'tenant_id': new cognito.StringAttribute({ minLen: 1, maxLen: 256, mutable: true }),
        'role': new cognito.StringAttribute({ minLen: 1, maxLen: 50, mutable: true }),
      },

      // Email configuration
      email: cognito.UserPoolEmail.withCognito(),

      // Lambda triggers for user management
      lambdaTriggers: {
        // Will add custom Lambda functions for user validation
      },

      // Deletion protection
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // User Pool Client
    const userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: 'mavik-ai-web-client',

      // OAuth configuration
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: ['https://app.mavik.ai/callback'], // Update with actual domain
        logoutUrls: ['https://app.mavik.ai/logout'],
      },

      // Token validity
      accessTokenValidity: cdk.Duration.hours(1),
      idTokenValidity: cdk.Duration.hours(1),
      refreshTokenValidity: cdk.Duration.days(30),

      // Security settings
      preventUserExistenceErrors: true,
      generateSecret: false, // For web clients
    });

    // User Pool Domain
    const userPoolDomain = new cognito.UserPoolDomain(this, 'UserPoolDomain', {
      userPool: this.userPool,
      cognitoDomain: {
        domainPrefix: `mavik-ai-${cdk.Aws.ACCOUNT_ID}`, // Must be globally unique
      },
    });

    // WAF Web ACL for API protection
    this.webAcl = new wafv2.CfnWebACL(this, 'ApiWebAcl', {
      name: 'mavik-ai-api-waf',
      scope: 'REGIONAL',
      defaultAction: { allow: {} },

      rules: [
        // Rate limiting rule
        {
          name: 'RateLimitRule',
          priority: 1,
          action: { block: {} },
          statement: {
            rateBasedStatement: {
              limit: 2000, // 2000 requests per 5-minute window
              aggregateKeyType: 'IP',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'RateLimitRule',
          },
        },

        // AWS Managed Core Rule Set
        {
          name: 'AWSManagedRulesCommonRuleSet',
          priority: 2,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: 'AWS',
              name: 'AWSManagedRulesCommonRuleSet',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'CommonRuleSetMetric',
          },
        },

        // Known bad inputs rule set
        {
          name: 'AWSManagedRulesKnownBadInputsRuleSet',
          priority: 3,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: 'AWS',
              name: 'AWSManagedRulesKnownBadInputsRuleSet',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'KnownBadInputsRuleSetMetric',
          },
        },
      ],

      visibilityConfig: {
        sampledRequestsEnabled: true,
        cloudWatchMetricsEnabled: true,
        metricName: 'MavikAiApiWebAcl',
      },
    });

    // NOTE: VPC Link removed to fix validation error - will be added once NLB is available

    // REST API Gateway
    this.restApi = new apigateway.RestApi(this, 'RestApi', {
      restApiName: 'mavik-ai-api',
      description: 'Mavik AI REST API Gateway',

      // CORS configuration
      defaultCorsPreflightOptions: {
        allowOrigins: ['https://app.mavik.ai'], // Update with actual domain
        allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowHeaders: ['Content-Type', 'Authorization', 'X-Amz-Date', 'X-Api-Key'],
        allowCredentials: true,
      },

      // API Key configuration
      apiKeySourceType: apigateway.ApiKeySourceType.HEADER,

      // Request validation will be configured per resource/method

      // CloudWatch logging
      cloudWatchRole: true,

      // Deployment options
      deployOptions: {
        stageName: 'v1',
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,

        // Throttling will be configured at method level
      },
    });

    // Associate WAF with API Gateway
    new wafv2.CfnWebACLAssociation(this, 'ApiWebAclAssociation', {
      resourceArn: this.restApi.deploymentStage.stageArn,
      webAclArn: this.webAcl.attrArn,
    });

    // Cognito Authorizer
    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [this.userPool],
      authorizerName: 'mavik-ai-authorizer',
      identitySource: 'method.request.header.Authorization',
    });

    // API Resources and Methods

    // Health check (no auth)
    const healthResource = this.restApi.root.addResource('health');
    healthResource.addMethod('GET', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '200',
        responseTemplates: {
          'application/json': JSON.stringify({
            status: 'healthy',
            timestamp: '$context.requestTime',
          }),
        },
      }],
      requestTemplates: {
        'application/json': '{"statusCode": 200}',
      },
    }), {
      methodResponses: [{
        statusCode: '200',
        responseModels: {
          'application/json': apigateway.Model.EMPTY_MODEL,
        },
      }],
    });

    // API v1 resource with Cognito auth
    const v1Resource = this.restApi.root.addResource('api').addResource('v1');

    // Documents resource
    const documentsResource = v1Resource.addResource('documents');
    documentsResource.addMethod('GET', new apigateway.HttpIntegration('http://internal-nlb.example.com/documents'), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });

    documentsResource.addMethod('POST', new apigateway.HttpIntegration('http://internal-nlb.example.com/documents'), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });

    // WebSocket API for real-time communication (using CFN construct for CDK v2.100.0)
    this.webSocketApi = new apigatewayv2.CfnApi(this, 'WebSocketApi', {
      name: 'mavik-ai-websocket',
      description: 'Mavik AI WebSocket API for real-time communication',
      protocolType: 'WEBSOCKET',
      routeSelectionExpression: '$request.body.action',
    });

    // WebSocket stages
    const webSocketStage = new apigatewayv2.CfnStage(this, 'WebSocketStage', {
      apiId: this.webSocketApi.ref,
      stageName: 'v1',
      autoDeploy: true,

      // Throttling (using default route settings for CFN)
      defaultRouteSettings: {
        throttlingRateLimit: 1000,
        throttlingBurstLimit: 2000,
      },
    });

    // CloudWatch Log Group for API Gateway
    new logs.LogGroup(this, 'ApiGatewayLogGroup', {
      logGroupName: `API-Gateway-Execution-Logs_${this.restApi.restApiId}/v1`,
      retention: logs.RetentionDays.ONE_MONTH,
      encryptionKey: props.kmsKey,
    });

    // Outputs
    new cdk.CfnOutput(this, 'RestApiUrl', {
      value: this.restApi.url,
      description: 'REST API Gateway URL',
      exportName: 'MavikAi-RestApiUrl',
    });

    new cdk.CfnOutput(this, 'WebSocketApiUrl', {
      value: `wss://${this.webSocketApi.ref}.execute-api.${cdk.Aws.REGION}.amazonaws.com/v1`,
      description: 'WebSocket API Gateway URL',
      exportName: 'MavikAi-WebSocketApiUrl',
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: 'MavikAi-UserPoolId',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
      exportName: 'MavikAi-UserPoolClientId',
    });

    new cdk.CfnOutput(this, 'CognitoDomainUrl', {
      value: `https://${userPoolDomain.domainName}.auth.${cdk.Aws.REGION}.amazoncognito.com`,
      description: 'Cognito Domain URL',
      exportName: 'MavikAi-CognitoDomainUrl',
    });
  }
}
