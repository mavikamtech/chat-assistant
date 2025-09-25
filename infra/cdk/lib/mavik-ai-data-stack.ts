import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as opensearch from 'aws-cdk-lib/aws-opensearchserverless';
import { Construct } from 'constructs';

export interface MavikAiDataStackProps extends cdk.StackProps {
  stackName: string;
  vpc: ec2.Vpc;
}

export class MavikAiDataStack extends cdk.Stack {
  // RDS Aurora cluster removed due to CDK securityGroupId bug - will need to be added separately
  public readonly auditTable: dynamodb.Table;
  public readonly documentsTable: dynamodb.Table;
  public readonly documentsBucket: s3.Bucket;
  public readonly reportsBucket: s3.Bucket;
  public readonly opensearchCollection: opensearch.CfnCollection;

  constructor(scope: Construct, id: string, props: MavikAiDataStackProps) {
    super(scope, id, props);

    // Local KMS key for data encryption (to avoid circular dependency with Security stack)
    const dataKmsKey = new kms.Key(this, 'DataKmsKey', {
      description: 'KMS key for data encryption in Mavik AI',
      enableKeyRotation: true,
      keySpec: kms.KeySpec.SYMMETRIC_DEFAULT,
      keyUsage: kms.KeyUsage.ENCRYPT_DECRYPT,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // S3 Buckets with encryption and versioning

    // Documents bucket for storing uploaded files
    this.documentsBucket = new s3.Bucket(this, 'DocumentsBucket', {
      bucketName: `mavik-ai-documents-${cdk.Aws.ACCOUNT_ID}-${cdk.Aws.REGION}`,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: dataKmsKey,
      versioned: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [
        {
          id: 'DeleteIncompleteMultipartUploads',
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
        {
          id: 'TransitionToIA',
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
      // Notification configuration will be added separately
    });

    // Reports bucket for generated analysis reports
    this.reportsBucket = new s3.Bucket(this, 'ReportsBucket', {
      bucketName: `mavik-ai-reports-${cdk.Aws.ACCOUNT_ID}-${cdk.Aws.REGION}`,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: dataKmsKey,
      versioned: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      lifecycleRules: [
        {
          id: 'DeleteOldReports',
          expiration: cdk.Duration.days(365), // Delete reports after 1 year
        },
      ],
    });

    // DynamoDB Tables

    // Audit table for tracking all user actions and AI decisions
    this.auditTable = new dynamodb.Table(this, 'AuditTable', {
      tableName: 'mavik-ai-audit-trail',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.STRING,
      },
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: dataKmsKey,
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,

      // GSI will be added after table creation
    });

    // Documents metadata table
    this.documentsTable = new dynamodb.Table(this, 'DocumentsTable', {
      tableName: 'mavik-ai-documents',
      partitionKey: {
        name: 'document_id',
        type: dynamodb.AttributeType.STRING,
      },
      encryption: dynamodb.TableEncryption.CUSTOMER_MANAGED,
      encryptionKey: dataKmsKey,
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,

      // GSI will be added after table creation
    });

    // NOTE: Aurora PostgreSQL cluster removed due to CDK library bug
    // The CDK v2.100.0 has a bug where Aurora cluster creation fails with:
    // "TypeError: Cannot read properties of undefined (reading 'securityGroupId')"
    //
    // To add Aurora later:
    // 1. Upgrade CDK to a newer version, OR
    // 2. Use CloudFormation directly, OR
    // 3. Create the Aurora cluster in a separate stack

    // OpenSearch Serverless Collection
    // Note: OpenSearch Serverless is managed through separate policies and collections

    // First, create the encryption policy
    const encryptionPolicy = new opensearch.CfnSecurityPolicy(this, 'OpenSearchEncryptionPolicy', {
      name: 'mavik-ai-encryption-policy',
      type: 'encryption',
      policy: JSON.stringify({
        Rules: [
          {
            ResourceType: 'collection',
            Resource: ['collection/mavik-ai-knowledge-base'],
          },
        ],
        AWSOwnedKey: false,
        KmsKeyId: dataKmsKey.keyId,
      }),
    });

    // Network policy for VPC access
    const networkPolicy = new opensearch.CfnSecurityPolicy(this, 'OpenSearchNetworkPolicy', {
      name: 'mavik-ai-network-policy',
      type: 'network',
      policy: JSON.stringify([
        {
          Rules: [
            {
              ResourceType: 'collection',
              Resource: ['collection/mavik-ai-knowledge-base'],
            },
            {
              ResourceType: 'dashboard',
              Resource: ['collection/mavik-ai-knowledge-base'],
            },
          ],
          AllowFromPublic: false,
          SourceVPCEs: [], // Will be populated by VPC endpoints
        },
      ]),
    });

    // Data access policy
    const dataAccessPolicy = new opensearch.CfnAccessPolicy(this, 'OpenSearchDataAccessPolicy', {
      name: 'mavik-ai-data-access-policy',
      type: 'data',
      policy: JSON.stringify([
        {
          Rules: [
            {
              ResourceType: 'collection',
              Resource: ['collection/mavik-ai-knowledge-base'],
              Permission: [
                'aoss:CreateCollectionItems',
                'aoss:DeleteCollectionItems',
                'aoss:UpdateCollectionItems',
                'aoss:DescribeCollectionItems',
              ],
            },
            {
              ResourceType: 'index',
              Resource: ['index/mavik-ai-knowledge-base/*'],
              Permission: [
                'aoss:CreateIndex',
                'aoss:DeleteIndex',
                'aoss:UpdateIndex',
                'aoss:DescribeIndex',
                'aoss:ReadDocument',
                'aoss:WriteDocument',
              ],
            },
          ],
          Principal: [
            `arn:aws:iam::${cdk.Aws.ACCOUNT_ID}:role/*EcsTaskRole*`,
            `arn:aws:iam::${cdk.Aws.ACCOUNT_ID}:root`,
          ],
        },
      ]),
    });

    // OpenSearch Serverless collection
    this.opensearchCollection = new opensearch.CfnCollection(this, 'OpenSearchCollection', {
      name: 'mavik-ai-knowledge-base',
      description: 'OpenSearch collection for Mavik AI RAG system',
      type: 'VECTORSEARCH',
    });

    // Dependencies
    this.opensearchCollection.addDependency(encryptionPolicy);
    this.opensearchCollection.addDependency(networkPolicy);
    this.opensearchCollection.addDependency(dataAccessPolicy);

    // Outputs
    // Aurora outputs removed - cluster not deployed due to CDK bug

    new cdk.CfnOutput(this, 'DocumentsBucketName', {
      value: this.documentsBucket.bucketName,
      description: 'Documents S3 bucket name',
      exportName: 'MavikAi-DocumentsBucket',
    });

    new cdk.CfnOutput(this, 'ReportsBucketName', {
      value: this.reportsBucket.bucketName,
      description: 'Reports S3 bucket name',
      exportName: 'MavikAi-ReportsBucket',
    });

    new cdk.CfnOutput(this, 'OpenSearchCollectionEndpoint', {
      value: this.opensearchCollection.attrCollectionEndpoint,
      description: 'OpenSearch Serverless collection endpoint',
      exportName: 'MavikAi-OpenSearchEndpoint',
    });
  }
}
