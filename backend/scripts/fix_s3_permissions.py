"""
Script to add the required bucket policy to mavik-uploads
This allows Textract to access PDFs stored in the bucket
"""

import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

def add_textract_bucket_policy():
    """Add bucket policy to allow Textract access"""

    s3 = boto3.client(
        's3',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    bucket_name = 'mavik-uploads'

    # Get current bucket policy (if any)
    try:
        response = s3.get_bucket_policy(Bucket=bucket_name)
        current_policy = json.loads(response['Policy'])
        print(f"Current bucket policy found for '{bucket_name}'")
        print(json.dumps(current_policy, indent=2))
    except s3.exceptions.NoSuchBucketPolicy:
        print(f"No existing bucket policy for '{bucket_name}'")
        current_policy = {"Version": "2012-10-17", "Statement": []}
    except Exception as e:
        print(f"Error getting bucket policy: {e}")
        return False

    # Add Textract permission
    textract_statement = {
        "Sid": "AllowTextractAccess",
        "Effect": "Allow",
        "Principal": {
            "Service": "textract.amazonaws.com"
        },
        "Action": [
            "s3:GetObject",
            "s3:GetObjectVersion"
        ],
        "Resource": f"arn:aws:s3:::{bucket_name}/*"
    }

    # Check if statement already exists
    existing_sids = [stmt.get('Sid') for stmt in current_policy.get('Statement', [])]
    if 'AllowTextractAccess' in existing_sids:
        print("\n✓ Textract permission already exists in bucket policy")
        return True

    # Add the statement
    current_policy.setdefault('Statement', []).append(textract_statement)

    # Update bucket policy
    try:
        s3.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(current_policy)
        )
        print(f"\n✓ Successfully added Textract permission to '{bucket_name}'")
        print("\nNew bucket policy:")
        print(json.dumps(current_policy, indent=2))
        return True
    except Exception as e:
        print(f"\n❌ Failed to update bucket policy: {e}")
        print("\nMANUAL FIX REQUIRED:")
        print("1. Go to AWS Console → S3 → mavik-uploads")
        print("2. Click 'Permissions' tab")
        print("3. Scroll to 'Bucket policy'")
        print("4. Add this policy:\n")
        print(json.dumps(current_policy, indent=2))
        return False

def main():
    print("=" * 60)
    print("S3 BUCKET POLICY FIX FOR TEXTRACT")
    print("=" * 60)
    print()

    print("This script will add permission for Textract to read from")
    print("the 'mavik-uploads' S3 bucket.")
    print()

    success = add_textract_bucket_policy()

    if success:
        print("\n" + "=" * 60)
        print("✓ FIX APPLIED SUCCESSFULLY")
        print("=" * 60)
        print("\nNext step: Run the test again to verify:")
        print("  python test_s3_textract.py")
    else:
        print("\n" + "=" * 60)
        print("❌ AUTOMATIC FIX FAILED")
        print("=" * 60)
        print("\nPlease apply the bucket policy manually (see AWS_SETUP.md)")

if __name__ == "__main__":
    main()
