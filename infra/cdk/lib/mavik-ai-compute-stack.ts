import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface MavikAiComputeStackProps extends cdk.StackProps {
  stackName: string;
  vpc: ec2.Vpc;
  kmsKey: kms.Key;
  ecsSecurityGroup: ec2.SecurityGroup;
  lambdaSecurityGroup: ec2.SecurityGroup;
}

export class MavikAiComputeStack extends cdk.Stack {
  public readonly ecsCluster: ecs.Cluster;
  public readonly orchestratorRepository: ecr.Repository;
  public readonly mcpServicesRepositories: { [key: string]: ecr.Repository };
  public readonly reportGeneratorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: MavikAiComputeStackProps) {
    super(scope, id, props);

    // ECS Cluster with Fargate capacity
    this.ecsCluster = new ecs.Cluster(this, 'EcsCluster', {
      clusterName: 'mavik-ai-cluster',
      vpc: props.vpc,
      containerInsights: true, // Enable CloudWatch Container Insights
    });

    // Add Fargate capacity provider
    // Enable Fargate capacity providers (they are added automatically)
    this.ecsCluster.enableFargateCapacityProviders();

    // Default capacity provider strategy for Fargate
    this.ecsCluster.addDefaultCapacityProviderStrategy([
      {
        capacityProvider: 'FARGATE',
        weight: 1,
      },
      {
        capacityProvider: 'FARGATE_SPOT',
        weight: 1,
      },
    ]);

    // ECR Repositories for container images

    // Orchestrator service repository
    this.orchestratorRepository = new ecr.Repository(this, 'OrchestratorRepository', {
      repositoryName: 'mavik-ai/orchestrator',
      encryption: ecr.RepositoryEncryption.KMS,
      encryptionKey: props.kmsKey,
      imageScanOnPush: true,
      lifecycleRules: [
        {
          description: 'Keep last 10 images',
          maxImageCount: 10,
        },
      ],
    });

    // MCP Services repositories
    const mcpServices = [
      'mcp-rag',
      'mcp-parser',
      'mcp-findb',
      'mcp-web',
      'mcp-calc',
    ];

    this.mcpServicesRepositories = {};
    mcpServices.forEach(serviceName => {
      this.mcpServicesRepositories[serviceName] = new ecr.Repository(this, `${serviceName}Repository`, {
        repositoryName: `mavik-ai/${serviceName}`,
        encryption: ecr.RepositoryEncryption.KMS,
        encryptionKey: props.kmsKey,
        imageScanOnPush: true,
        lifecycleRules: [
          {
            description: 'Keep last 10 images',
            maxImageCount: 10,
          },
        ],
      });
    });

    // Lambda function for report generation

    // CloudWatch Log Group for Lambda
    const reportLambdaLogGroup = new logs.LogGroup(this, 'ReportLambdaLogGroup', {
      logGroupName: '/aws/lambda/mavik-ai-report-generator',
      retention: logs.RetentionDays.ONE_MONTH,
      encryptionKey: props.kmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Lambda function
    this.reportGeneratorFunction = new lambda.Function(this, 'ReportGeneratorFunction', {
      functionName: 'mavik-ai-report-generator',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'main.handler',
      code: lambda.Code.fromAsset('../services/mcp-report/lambda'), // Will create this

      // Resource configuration
      timeout: cdk.Duration.minutes(15), // Max for Lambda
      memorySize: 3008, // Max memory for better performance

      // Network configuration
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [props.lambdaSecurityGroup],

      // Environment variables
      environment: {
        KMS_KEY_ID: props.kmsKey.keyId,
        REPORTS_BUCKET: `mavik-ai-reports-${cdk.Aws.ACCOUNT_ID}-${cdk.Aws.REGION}`,
        LOG_LEVEL: 'INFO',
      },

      // Logging
      // Log group will be created automatically

      // Tracing
      tracing: lambda.Tracing.ACTIVE,

      // Architecture
      architecture: lambda.Architecture.ARM_64, // Graviton2 for better price/performance

      // Reserved concurrency to prevent cost overruns
      reservedConcurrentExecutions: 10,
    });

    // Lambda Layer for shared dependencies
    const sharedLayer = new lambda.LayerVersion(this, 'SharedDependenciesLayer', {
      layerVersionName: 'mavik-ai-shared-dependencies',
      code: lambda.Code.fromAsset('../packages/lambda-layer'), // Will create this
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      description: 'Shared dependencies for Mavik AI Lambda functions',
    });

    this.reportGeneratorFunction.addLayers(sharedLayer);

    // ECS Task Definitions (will be created by service-specific stacks)
    // Here we just set up the base infrastructure

    // CloudWatch Log Groups for ECS services
    const ecsLogGroups: { [key: string]: logs.LogGroup } = {};

    const services = ['orchestrator', ...mcpServices];
    services.forEach(serviceName => {
      ecsLogGroups[serviceName] = new logs.LogGroup(this, `${serviceName}LogGroup`, {
        logGroupName: `/ecs/mavik-ai-${serviceName}`,
        retention: logs.RetentionDays.ONE_MONTH,
        encryptionKey: props.kmsKey,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
      });
    });

    // Example ECS Service (Orchestrator) - Others will be similar
    const orchestratorTaskDefinition = new ecs.FargateTaskDefinition(this, 'OrchestratorTaskDefinition', {
      family: 'mavik-ai-orchestrator',
      cpu: 512, // 0.5 vCPU
      memoryLimitMiB: 1024, // 1 GB RAM

      // Execution role for pulling images and logging
      executionRole: iam.Role.fromRoleArn(
        this,
        'ImportedEcsExecutionRole',
        `arn:aws:iam::${cdk.Aws.ACCOUNT_ID}:role/*EcsExecutionRole*`,
        { mutable: false }
      ),

      // Task role for application permissions
      taskRole: iam.Role.fromRoleArn(
        this,
        'ImportedEcsTaskRole',
        `arn:aws:iam::${cdk.Aws.ACCOUNT_ID}:role/*EcsTaskRole*`,
        { mutable: false }
      ),
    });

    // Container definition
    const orchestratorContainer = orchestratorTaskDefinition.addContainer('orchestrator', {
      containerName: 'orchestrator',
      image: ecs.ContainerImage.fromEcrRepository(this.orchestratorRepository, 'latest'),

      // Resource limits
      cpu: 512,
      memoryLimitMiB: 1024,

      // Logging
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'orchestrator',
        logGroup: ecsLogGroups['orchestrator'],
      }),

      // Health check
      healthCheck: {
        command: ['CMD-SHELL', 'curl -f http://localhost:8000/health || exit 1'],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
        startPeriod: cdk.Duration.seconds(60),
      },

      // Environment variables
      environment: {
        PORT: '8000',
        ENVIRONMENT: 'production',
        LOG_LEVEL: 'INFO',
      },

      // Secrets from Secrets Manager
      secrets: {
        DB_PASSWORD: ecs.Secret.fromSecretsManager(
          cdk.aws_secretsmanager.Secret.fromSecretNameV2(this, 'ImportedDbSecret', 'mavik-ai-db-credentials'),
          'password'
        ),
      },
    });

    // Port mapping
    orchestratorContainer.addPortMappings({
      containerPort: 8000,
      protocol: ecs.Protocol.TCP,
    });

    // ECS Service
    const orchestratorService = new ecs.FargateService(this, 'OrchestratorService', {
      cluster: this.ecsCluster,
      taskDefinition: orchestratorTaskDefinition,
      serviceName: 'mavik-ai-orchestrator',

      // Deployment configuration
      desiredCount: 2, // Multi-AZ for high availability
      minHealthyPercent: 50,
      maxHealthyPercent: 200,

      // Network configuration
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [props.ecsSecurityGroup],

      // Platform version
      platformVersion: ecs.FargatePlatformVersion.LATEST,

      // Circuit breaker for faster rollbacks
      circuitBreaker: {
        rollback: true,
      },

      // Enable logging
      // Logging is enabled by default in CDK v2
    });

    // Auto Scaling
    const orchestratorScaling = orchestratorService.autoScaleTaskCount({
      minCapacity: 2,
      maxCapacity: 10,
    });

    // Scale on CPU utilization
    orchestratorScaling.scaleOnCpuUtilization('OrchestratorCpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.minutes(5),
      scaleOutCooldown: cdk.Duration.minutes(2),
    });

    // Scale on memory utilization
    orchestratorScaling.scaleOnMemoryUtilization('OrchestratorMemoryScaling', {
      targetUtilizationPercent: 80,
      scaleInCooldown: cdk.Duration.minutes(5),
      scaleOutCooldown: cdk.Duration.minutes(2),
    });

    // Outputs
    new cdk.CfnOutput(this, 'EcsClusterName', {
      value: this.ecsCluster.clusterName,
      description: 'ECS cluster name',
      exportName: 'MavikAi-EcsClusterName',
    });

    new cdk.CfnOutput(this, 'EcsClusterArn', {
      value: this.ecsCluster.clusterArn,
      description: 'ECS cluster ARN',
      exportName: 'MavikAi-EcsClusterArn',
    });

    new cdk.CfnOutput(this, 'OrchestratorRepositoryUri', {
      value: this.orchestratorRepository.repositoryUri,
      description: 'Orchestrator ECR repository URI',
      exportName: 'MavikAi-OrchestratorRepositoryUri',
    });

    new cdk.CfnOutput(this, 'ReportGeneratorFunctionArn', {
      value: this.reportGeneratorFunction.functionArn,
      description: 'Report generator Lambda function ARN',
      exportName: 'MavikAi-ReportGeneratorArn',
    });
  }
}
