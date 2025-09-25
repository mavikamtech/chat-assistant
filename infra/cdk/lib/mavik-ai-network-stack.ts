import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export interface MavikAiNetworkStackProps extends cdk.StackProps {
  stackName: string;
}

export class MavikAiNetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly privateSubnets: ec2.ISubnet[];
  public readonly publicSubnets: ec2.ISubnet[];
  public readonly isolatedSubnets: ec2.ISubnet[];

  constructor(scope: Construct, id: string, props: MavikAiNetworkStackProps) {
    super(scope, id, props);

    // Create VPC with proper subnet configuration for production workloads
    this.vpc = new ec2.Vpc(this, 'MavikAiVpc', {
      vpcName: 'mavik-ai-vpc',
      ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
      maxAzs: 3, // Use 3 AZs for high availability

      subnetConfiguration: [
        {
          // Public subnets for NAT Gateways, ALB, and bastion hosts
          cidrMask: 24,
          name: 'PublicSubnet',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          // Private subnets for ECS services, Lambda functions
          cidrMask: 22, // Larger subnet for services (/22 = 1024 IPs)
          name: 'PrivateSubnet',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          // Isolated subnets for RDS, OpenSearch (no internet access)
          cidrMask: 24,
          name: 'IsolatedSubnet',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],

      // NAT Gateway configuration for production
      natGateways: 3, // One per AZ for high availability
      natGatewayProvider: ec2.NatProvider.gateway(),

      // Enable DNS
      enableDnsHostnames: true,
      enableDnsSupport: true,

      // VPC Flow Logs for security monitoring
      flowLogs: {
        cloudWatchLogs: {
          destination: ec2.FlowLogDestination.toCloudWatchLogs(),
          trafficType: ec2.FlowLogTrafficType.ALL,
        },
      },
    });

    // Store subnet references for other stacks
    this.privateSubnets = this.vpc.privateSubnets;
    this.publicSubnets = this.vpc.publicSubnets;
    this.isolatedSubnets = this.vpc.isolatedSubnets;

    // Output important VPC information
    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC ID for Mavik AI infrastructure',
      exportName: 'MavikAi-VpcId',
    });

    new cdk.CfnOutput(this, 'VpcCidr', {
      value: this.vpc.vpcCidrBlock,
      description: 'VPC CIDR block',
      exportName: 'MavikAi-VpcCidr',
    });

    new cdk.CfnOutput(this, 'PrivateSubnetIds', {
      value: this.privateSubnets.map(subnet => subnet.subnetId).join(','),
      description: 'Private subnet IDs',
      exportName: 'MavikAi-PrivateSubnetIds',
    });

    new cdk.CfnOutput(this, 'IsolatedSubnetIds', {
      value: this.isolatedSubnets.map(subnet => subnet.subnetId).join(','),
      description: 'Isolated subnet IDs for databases',
      exportName: 'MavikAi-IsolatedSubnetIds',
    });

    // Add resource tags
    cdk.Tags.of(this.vpc).add('Name', 'MavikAI-VPC');
    cdk.Tags.of(this.vpc).add('Purpose', 'AI-Underwriting-Platform');
  }
}
