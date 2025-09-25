import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';

export interface MavikAiInfrastructureStackProps extends cdk.StackProps {
  stackName: string;
  vpc: ec2.Vpc;
  kmsKey: kms.Key;
}

export class MavikAiInfrastructureStack extends cdk.Stack {
  public readonly vpcEndpoints: { [key: string]: ec2.VpcEndpoint };

  constructor(scope: Construct, id: string, props: MavikAiInfrastructureStackProps) {
    super(scope, id, props);

    // VPC Endpoints for secure AWS service access
    this.vpcEndpoints = {};

    // S3 Gateway Endpoint (no cost)
    this.vpcEndpoints['s3'] = new ec2.GatewayVpcEndpoint(this, 'S3VpcEndpoint', {
      vpc: props.vpc,
      service: ec2.GatewayVpcEndpointAwsService.S3,
      subnets: [
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });

    // DynamoDB Gateway Endpoint (no cost)
    this.vpcEndpoints['dynamodb'] = new ec2.GatewayVpcEndpoint(this, 'DynamoDbVpcEndpoint', {
      vpc: props.vpc,
      service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
      subnets: [
        {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
      ],
    });

    // Interface VPC Endpoints (cost per hour + data transfer)
    const interfaceEndpoints = [
      { name: 'SecretsManager', service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER },
      { name: 'KMS', service: ec2.InterfaceVpcEndpointAwsService.KMS },
      { name: 'ECR', service: ec2.InterfaceVpcEndpointAwsService.ECR },
      { name: 'ECRDockerRegistry', service: ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER },
      { name: 'CloudWatchLogs', service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS },
      { name: 'CloudWatchMonitoring', service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_MONITORING },
      { name: 'STS', service: ec2.InterfaceVpcEndpointAwsService.STS },
    ];

    // Security group for VPC endpoints
    const vpcEndpointSecurityGroup = new ec2.SecurityGroup(this, 'VpcEndpointSecurityGroup', {
      vpc: props.vpc,
      description: 'Security group for VPC endpoints',
      allowAllOutbound: false,
    });

    // Allow HTTPS traffic from private subnets
    vpcEndpointSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(443),
      'Allow HTTPS from private subnets'
    );

    interfaceEndpoints.forEach(endpoint => {
      this.vpcEndpoints[endpoint.name.toLowerCase()] = new ec2.InterfaceVpcEndpoint(this, `${endpoint.name}VpcEndpoint`, {
        vpc: props.vpc,
        service: endpoint.service,
        subnets: {
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        securityGroups: [vpcEndpointSecurityGroup],
        privateDnsEnabled: true,
      });
    });

    // OpenSearch Serverless VPC Endpoint (custom service)
    this.vpcEndpoints['opensearch'] = new ec2.InterfaceVpcEndpoint(this, 'OpenSearchVpcEndpoint', {
      vpc: props.vpc,
      service: new ec2.InterfaceVpcEndpointService(`com.amazonaws.${cdk.Aws.REGION}.aoss`),
      subnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [vpcEndpointSecurityGroup],
      privateDnsEnabled: true,
    });

    // TODO: Bedrock Guardrail will be added when available in CDK (post v2.100.0)
    // For now, Bedrock services will be configured directly via AWS console or CLI

    // Output VPC Endpoint IDs
    Object.entries(this.vpcEndpoints).forEach(([name, endpoint]) => {
      new cdk.CfnOutput(this, `${name}VpcEndpointId`, {
        value: endpoint.vpcEndpointId,
        description: `${name} VPC Endpoint ID`,
        exportName: `MavikAi-${name}VpcEndpointId`,
      });
    });
  }
}
