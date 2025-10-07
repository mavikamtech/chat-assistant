# AWS Setup for Mavik AI Assistant

## Required AWS Permissions

Your IAM user needs the following permissions for the application to work:

### 1. S3 Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:HeadObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::mavik-uploads/*",
        "arn:aws:s3:::mavik-uploads",
        "arn:aws:s3:::mavik-reports/*",
        "arn:aws:s3:::mavik-reports"
      ]
    }
  ]
}
```

### 2. Textract Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "textract:StartDocumentAnalysis",
        "textract:GetDocumentAnalysis",
        "textract:StartDocumentTextDetection",
        "textract:GetDocumentTextDetection"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Bedrock Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
      ]
    }
  ]
}
```

## CRITICAL: S3 Bucket Policy for Textract

**The most common issue** is that Textract cannot read from your S3 bucket. You need to add a bucket policy to allow Textract to access the files.

### Add this Bucket Policy to `mavik-uploads` bucket:

1. Go to AWS Console → S3 → `mavik-uploads` bucket
2. Click **Permissions** tab
3. Scroll to **Bucket Policy**
4. Add this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowTextractAccess",
      "Effect": "Allow",
      "Principal": {
        "Service": "textract.amazonaws.com"
      },
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::mavik-uploads/*"
    }
  ]
}
```

### Alternative: Create IAM Role for Textract

If the bucket policy doesn't work, you can create an IAM role that Textract can assume:

1. Create IAM Role named `TextractS3AccessRole`
2. Trust relationship:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "textract.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

3. Attach policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::mavik-uploads/*"
    }
  ]
}
```

4. Update the code to use this role (see `doc_parser.py`)

## Testing Permissions

Run this script to verify your setup:

```bash
cd backend
python -c "
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Test S3
s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION'))
buckets = [b['Name'] for b in s3.list_buckets()['Buckets']]
print('✓ S3 Access OK')
print(f'  Buckets: {buckets}')

# Test Textract
textract = boto3.client('textract', region_name=os.getenv('AWS_REGION'))
print('✓ Textract Client OK')

# Test Bedrock
bedrock = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION'))
print('✓ Bedrock Runtime Client OK')
"
```

## Troubleshooting

### Error: "Unable to get object metadata from S3"

This means Textract cannot access the S3 object. Solutions:

1. **Add the Bucket Policy** above to `mavik-uploads` bucket
2. Ensure the S3 object exists: check in AWS Console
3. Verify the bucket is in the same region as Textract (us-east-1)
4. Check if server-side encryption is compatible (use AES256, not KMS with custom keys)

### Error: "Access Denied"

Your IAM user lacks permissions. Attach the policies above to your IAM user.

### Error: "InvalidS3ObjectException"

The S3 object key is incorrect or file doesn't exist. Check:
- File was uploaded successfully
- The key path is correct (should start with `uploads/`)
- No special characters in filename

## Region Considerations

- Textract is available in limited regions
- Ensure all services (S3, Textract, Bedrock) are in `us-east-1`
- If you need a different region, update `.env` and verify service availability
