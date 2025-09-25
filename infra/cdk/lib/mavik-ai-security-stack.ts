import * as cdk from 'aws-cdk-lib';
import { Stack } from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';

import { Construct } from 'constructs';

export interface MavikAiSecurityStackProps extends cdk.StackProps {
  stackName: string;
  vpc: ec2.Vpc;
}

export class MavikAiSecurityStack extends cdk.Stack {
  public readonly kmsKey: kms.Key;
  public readonly ecsSecurityGroup: ec2.SecurityGroup;
  public readonly dbSecurityGroup: ec2.SecurityGroup;
  public readonly lambdaSecurityGroup: ec2.SecurityGroup;
  public readonly apiSecurityGroup: ec2.SecurityGroup;
  public readonly ecsTaskRole: iam.Role;
  public readonly ecsExecutionRole: iam.Role;
  public readonly lambdaExecutionRole: iam.Role;

  constructor(scope: Construct, id: string, props: MavikAiSecurityStackProps) {
    super(scope, id, props);

    // KMS Key for encryption at rest
    this.kmsKey = new kms.Key(this, 'MavikAiKmsKey', {
      description: 'KMS key for Mavik AI data encryption',
      enableKeyRotation: true,
      // Key rotation is enabled by default with enableKeyRotation: true
      policy: new iam.PolicyDocument({
        statements: [
          // Root account full access
          new iam.PolicyStatement({
            sid: 'RootAccountAccess',
            effect: iam.Effect.ALLOW,
            principals: [new iam.AccountRootPrincipal()],
            actions: ['kms:*'],
            resources: ['*'],
          }),
          // Allow AWS services to use the key
          new iam.PolicyStatement({
            sid: 'AWSServicesAccess',
            effect: iam.Effect.ALLOW,
            principals: [
              new iam.ServicePrincipal('s3.amazonaws.com'),
              new iam.ServicePrincipal('rds.amazonaws.com'),
              new iam.ServicePrincipal('dynamodb.amazonaws.com'),
              new iam.ServicePrincipal('opensearch.amazonaws.com'),
              new iam.ServicePrincipal('secretsmanager.amazonaws.com'),
              new iam.ServicePrincipal('logs.amazonaws.com'),
            ],
            actions: [
              'kms:Decrypt',
              'kms:DescribeKey',
              'kms:Encrypt',
              'kms:GenerateDataKey*',
              'kms:ReEncrypt*',
            ],
            resources: ['*'],
          }),
        ],
      }),
    });

    // Alias for the KMS key
    new kms.Alias(this, 'MavikAiKmsKeyAlias', {
      aliasName: 'alias/mavik-ai-key',
      targetKey: this.kmsKey,
    });

    // Database credentials secret will be created by Aurora cluster in data stack
    // We'll export KMS key for the data stack to use for secret encryption

    // Security Groups

    // ECS Services Security Group
    this.ecsSecurityGroup = new ec2.SecurityGroup(this, 'EcsSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for ECS services',
      allowAllOutbound: true, // We'll restrict this with NACLs and VPCEs
    });

    // Allow ECS services to communicate with each other
    this.ecsSecurityGroup.addIngressRule(
      this.ecsSecurityGroup,
      ec2.Port.allTcp(),
      'Allow ECS services to communicate with each other'
    );

    // Database Security Group
    this.dbSecurityGroup = new ec2.SecurityGroup(this, 'DbSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for RDS Aurora cluster',
      allowAllOutbound: false,
    });

    // Allow ECS services to connect to database
    this.dbSecurityGroup.addIngressRule(
      this.ecsSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow ECS services to connect to PostgreSQL'
    );

    // Lambda Security Group
    this.lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for Lambda functions',
      allowAllOutbound: true,
    });

    // Allow Lambda to connect to database (for report generation)
    this.dbSecurityGroup.addIngressRule(
      this.lambdaSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow Lambda functions to connect to PostgreSQL'
    );

    // API Gateway Security Group (for VPC Link)
    this.apiSecurityGroup = new ec2.SecurityGroup(this, 'ApiSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for API Gateway VPC Link',
      allowAllOutbound: false,
    });

    // Allow API Gateway to forward to ECS services
    this.apiSecurityGroup.addEgressRule(
      this.ecsSecurityGroup,
      ec2.Port.allTcp(),
      'Allow API Gateway to forward to ECS services'
    );

    // Allow ECS services to receive from API Gateway
    this.ecsSecurityGroup.addIngressRule(
      this.apiSecurityGroup,
      ec2.Port.tcp(8000),
      'Allow API Gateway to forward to orchestrator'
    );

    // IAM Roles

    // ECS Task Role (permissions for application code)
    this.ecsTaskRole = new iam.Role(this, 'EcsTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      description: 'IAM role for ECS tasks with AWS service permissions',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
      ],
      inlinePolicies: {
        BedrockAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'bedrock:InvokeModel',
                'bedrock:InvokeModelWithResponseStream',
                'bedrock:GetFoundationModel',
                'bedrock:ListFoundationModels',
              ],
              resources: [
                `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-*`,
                `arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-*`,
              ],
            }),
          ],
        }),
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:GetObject',
                's3:PutObject',
                's3:DeleteObject',
                's3:GetObjectVersion',
              ],
              resources: ['arn:aws:s3:::mavik-ai-*/*'],
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['s3:ListBucket'],
              resources: ['arn:aws:s3:::mavik-ai-*'],
            }),
          ],
        }),
        OpenSearchAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'es:ESHttpGet',
                'es:ESHttpPost',
                'es:ESHttpPut',
                'es:ESHttpDelete',
                'es:ESHttpHead',
              ],
              resources: ['arn:aws:es:*:*:domain/mavik-ai-*/*'],
            }),
          ],
        }),
        DynamoDBAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'dynamodb:GetItem',
                'dynamodb:PutItem',
                'dynamodb:UpdateItem',
                'dynamodb:DeleteItem',
                'dynamodb:Query',
                'dynamodb:Scan',
              ],
              resources: ['arn:aws:dynamodb:*:*:table/mavik-ai-*'],
            }),
          ],
        }),
        KMSAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'kms:Decrypt',
                'kms:Encrypt',
                'kms:GenerateDataKey',
                'kms:DescribeKey',
              ],
              resources: [this.kmsKey.keyArn],
            }),
          ],
        }),

      },
    });

    // ECS Execution Role (permissions for ECS service)
    this.ecsExecutionRole = new iam.Role(this, 'EcsExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      description: 'IAM role for ECS task execution',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
      inlinePolicies: {
        ECRAndSecretsAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'kms:Decrypt',
              ],
              resources: [this.kmsKey.keyArn],
            }),
          ],
        }),
      },
    });

    // Lambda Execution Role
    this.lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'IAM role for Lambda functions',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
      ],
      inlinePolicies: {
        LambdaPermissions: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:GetObject',
                's3:PutObject',
                's3:PutObjectAcl',
              ],
              resources: ['arn:aws:s3:::mavik-ai-*/*'],
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'kms:Decrypt',
                'kms:Encrypt',
                'kms:GenerateDataKey',
              ],
              resources: [this.kmsKey.keyArn],
            }),
          ],
        }),
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'KmsKeyId', {
      value: this.kmsKey.keyId,
      description: 'KMS Key ID for encryption',
      exportName: 'MavikAi-KmsKeyId',
    });

    new cdk.CfnOutput(this, 'KmsKeyArn', {
      value: this.kmsKey.keyArn,
      description: 'KMS Key ARN for encryption',
      exportName: 'MavikAi-KmsKeyArn',
    });


  }
}
