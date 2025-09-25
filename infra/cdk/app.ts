#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { MavikAiNetworkStack } from './lib/mavik-ai-network-stack';
import { MavikAiSecurityStack } from './lib/mavik-ai-security-stack';
import { MavikAiDataStack } from './lib/mavik-ai-data-stack';
import { MavikAiComputeStack } from './lib/mavik-ai-compute-stack';
import { MavikAiApiStackMinimal } from './lib/mavik-ai-api-stack-minimal';
import { MavikAiInfrastructureStack } from './lib/mavik-ai-infrastructure-stack';

const app = new cdk.App();

// Environment configuration
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

// Stack naming convention
const prefix = 'MavikAi';
const stage = process.env.STAGE || 'dev';

// 1. Network Foundation (VPC, Subnets, NAT Gateways)
const networkStack = new MavikAiNetworkStack(app, `${prefix}Network${stage}`, {
  env,
  stackName: `${prefix}-Network-${stage}`,
  description: 'Network infrastructure for Mavik AI (VPC, Subnets, NAT)',
});

// 2. Security Foundation (KMS, Secrets, IAM Roles)
const securityStack = new MavikAiSecurityStack(app, `${prefix}Security${stage}`, {
  env,
  stackName: `${prefix}-Security-${stage}`,
  description: 'Security infrastructure for Mavik AI (KMS, Secrets, IAM)',
  vpc: networkStack.vpc,
});

// 3. Data Layer (RDS, DynamoDB, OpenSearch, S3)
const dataStack = new MavikAiDataStack(app, `${prefix}Data${stage}`, {
  env,
  stackName: `${prefix}-Data-${stage}`,
  description: 'Data infrastructure for Mavik AI (RDS, DynamoDB, OpenSearch, S3)',
  vpc: networkStack.vpc,
});

// 4. Compute Layer (ECS, ECR, Lambda)
const computeStack = new MavikAiComputeStack(app, `${prefix}Compute${stage}`, {
  env,
  stackName: `${prefix}-Compute-${stage}`,
  description: 'Compute infrastructure for Mavik AI (ECS, ECR, Lambda)',
  vpc: networkStack.vpc,
  kmsKey: securityStack.kmsKey,
  ecsSecurityGroup: securityStack.ecsSecurityGroup,
  lambdaSecurityGroup: securityStack.lambdaSecurityGroup,
});

// 5. API Layer (API Gateway, Cognito, WAF)
const apiStack = new MavikAiApiStackMinimal(app, `${prefix}Api${stage}`, {
  env,
  stackName: `${prefix}-Api-${stage}`,
  description: 'API infrastructure for Mavik AI (API Gateway, Cognito, WAF)',
  vpc: networkStack.vpc,
  kmsKey: securityStack.kmsKey,
  apiSecurityGroup: securityStack.apiSecurityGroup,
  ecsCluster: computeStack.ecsCluster,
});

// 6. Main Infrastructure Stack (Bedrock, Guardrails, VPC Endpoints)
const infrastructureStack = new MavikAiInfrastructureStack(app, `${prefix}Infrastructure${stage}`, {
  env,
  stackName: `${prefix}-Infrastructure-${stage}`,
  description: 'Core infrastructure for Mavik AI (Bedrock, Guardrails, VPCEs)',
  vpc: networkStack.vpc,
  kmsKey: securityStack.kmsKey,
});

// Stack dependencies
securityStack.addDependency(networkStack);
dataStack.addDependency(networkStack);
computeStack.addDependency(securityStack);
apiStack.addDependency(computeStack);
infrastructureStack.addDependency(networkStack);

// Tags for all resources
const commonTags = {
  Project: 'MavikAI',
  Environment: stage,
  ManagedBy: 'AWS-CDK',
  CostCenter: 'AI-Platform',
  DataClassification: 'Internal',
  BackupRequired: 'true',
};

Object.values(app.node.children).forEach((stack) => {
  if (stack instanceof cdk.Stack) {
    Object.entries(commonTags).forEach(([key, value]) => {
      cdk.Tags.of(stack).add(key, value);
    });
  }
});
