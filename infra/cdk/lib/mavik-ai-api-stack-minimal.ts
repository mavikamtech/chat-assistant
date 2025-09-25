import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';

export interface MavikAiApiStackMinimalProps extends cdk.StackProps {
  stackName: string;
  vpc: ec2.Vpc;
  kmsKey: kms.Key;
  apiSecurityGroup: ec2.SecurityGroup;
  ecsCluster: ecs.Cluster;
}

export class MavikAiApiStackMinimal extends cdk.Stack {
  public readonly restApi: apigateway.RestApi;

  constructor(scope: Construct, id: string, props: MavikAiApiStackMinimalProps) {
    super(scope, id, props);

    // Simple REST API Gateway without VPC Link
    this.restApi = new apigateway.RestApi(this, 'RestApi', {
      restApiName: 'mavik-ai-api-minimal',
      description: 'Minimal Mavik AI REST API Gateway',
    });

    // Simple health check
    const healthResource = this.restApi.root.addResource('health');
    healthResource.addMethod('GET', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '200',
        responseTemplates: {
          'application/json': JSON.stringify({ status: 'healthy' }),
        },
      }],
      requestTemplates: {
        'application/json': '{"statusCode": 200}',
      },
    }), {
      methodResponses: [{
        statusCode: '200',
      }],
    });

    // Output
    new cdk.CfnOutput(this, 'RestApiUrl', {
      value: this.restApi.url,
      description: 'REST API Gateway URL',
      exportName: 'MavikAi-RestApiUrl',
    });
  }
}
