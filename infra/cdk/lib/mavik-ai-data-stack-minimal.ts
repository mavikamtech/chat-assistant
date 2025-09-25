import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';

export interface MavikAiDataStackMinimalProps extends cdk.StackProps {
  stackName: string;
  vpc: ec2.Vpc;
}

export class MavikAiDataStackMinimal extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MavikAiDataStackMinimalProps) {
    super(scope, id, props);

    // Just a simple S3 bucket to test
    const testBucket = new s3.Bucket(this, 'TestBucket', {
      bucketName: `test-bucket-${cdk.Aws.ACCOUNT_ID}-${cdk.Aws.REGION}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
  }
}
