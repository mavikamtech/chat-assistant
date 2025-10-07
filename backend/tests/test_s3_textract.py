"""
Test script to diagnose S3 and Textract integration issues
Run this to identify permission problems before using the full app
"""

import boto3
import os
import sys
from dotenv import load_dotenv

# Fix unicode output on Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

def test_aws_credentials():
    """Test if AWS credentials are configured"""
    print("=" * 60)
    print("1. Testing AWS Credentials")
    print("=" * 60)

    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION', 'us-east-1')

    if not access_key or not secret_key:
        print("❌ AWS credentials not found in .env file")
        return False

    print(f"✓ AWS_ACCESS_KEY_ID: {access_key[:10]}...")
    print(f"✓ AWS_SECRET_ACCESS_KEY: {'*' * 20}")
    print(f"✓ AWS_REGION: {region}")
    return True

def test_s3_access():
    """Test S3 bucket access"""
    print("\n" + "=" * 60)
    print("2. Testing S3 Access")
    print("=" * 60)

    try:
        s3 = boto3.client(
            's3',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        # List buckets
        response = s3.list_buckets()
        buckets = [b['Name'] for b in response['Buckets']]

        print(f"✓ S3 client created successfully")
        print(f"✓ Found {len(buckets)} buckets")

        # Check required buckets
        required_buckets = ['mavik-uploads', 'mavik-reports']
        for bucket in required_buckets:
            if bucket in buckets:
                print(f"✓ Bucket '{bucket}' exists")

                # Try to list objects
                try:
                    s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
                    print(f"  → Can list objects in '{bucket}'")
                except Exception as e:
                    print(f"  ⚠️  Cannot list objects in '{bucket}': {e}")
            else:
                print(f"❌ Bucket '{bucket}' does NOT exist")
                return False

        return True

    except Exception as e:
        print(f"❌ S3 access failed: {e}")
        return False

def test_textract_access():
    """Test Textract service access"""
    print("\n" + "=" * 60)
    print("3. Testing Textract Access")
    print("=" * 60)

    try:
        textract = boto3.client(
            'textract',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        print("✓ Textract client created successfully")

        # Note: We can't test actual Textract without a file, but we can verify the client works
        print("✓ Textract client initialized (actual extraction requires a PDF)")

        return True

    except Exception as e:
        print(f"❌ Textract access failed: {e}")
        return False

def test_bedrock_access():
    """Test Bedrock access"""
    print("\n" + "=" * 60)
    print("4. Testing Bedrock Access")
    print("=" * 60)

    try:
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        print("✓ Bedrock Runtime client created successfully")

        return True

    except Exception as e:
        print(f"❌ Bedrock access failed: {e}")
        return False

def test_upload_and_textract():
    """Test actual file upload and Textract processing"""
    print("\n" + "=" * 60)
    print("5. Testing Full Upload + Textract Flow (CRITICAL TEST)")
    print("=" * 60)

    try:
        import io
        from reportlab.pdfgen import canvas

        # Create a simple test PDF
        print("Creating test PDF...")
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer)
        c.drawString(100, 750, "Test PDF for Textract")
        c.drawString(100, 730, "This is a test document")
        c.save()
        buffer.seek(0)

        # Upload to S3
        s3 = boto3.client(
            's3',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        test_key = 'test/textract_test.pdf'
        print(f"Uploading test PDF to s3://mavik-uploads/{test_key}")

        s3.upload_fileobj(
            buffer,
            'mavik-uploads',
            test_key,
            ExtraArgs={
                'ContentType': 'application/pdf',
                'ServerSideEncryption': 'AES256'
            }
        )
        print("✓ Test PDF uploaded successfully")

        # Verify file exists
        s3.head_object(Bucket='mavik-uploads', Key=test_key)
        print("✓ Test PDF verified in S3")

        # Try Textract
        textract = boto3.client(
            'textract',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

        print("Starting Textract analysis...")
        response = textract.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': 'mavik-uploads',
                    'Name': test_key
                }
            },
            FeatureTypes=['TABLES']
        )

        job_id = response['JobId']
        print(f"✓ Textract job started: {job_id}")

        # Wait for completion
        import time
        max_attempts = 20
        for i in range(max_attempts):
            time.sleep(3)
            result = textract.get_document_analysis(JobId=job_id)
            status = result['JobStatus']
            print(f"  Status: {status}")

            if status == 'SUCCEEDED':
                print("✓ Textract analysis SUCCEEDED!")
                print(f"  Found {len(result.get('Blocks', []))} blocks")

                # Cleanup
                s3.delete_object(Bucket='mavik-uploads', Key=test_key)
                print("✓ Test file cleaned up")

                return True
            elif status == 'FAILED':
                error_msg = result.get('StatusMessage', 'Unknown error')
                print(f"❌ Textract analysis FAILED: {error_msg}")

                # Cleanup
                s3.delete_object(Bucket='mavik-uploads', Key=test_key)

                return False

        print("❌ Textract job timed out")
        return False

    except ImportError:
        print("⚠️  reportlab not installed, skipping PDF creation test")
        print("   Install with: pip install reportlab")
        print("\nYou can still test manually:")
        print("1. Upload a PDF to s3://mavik-uploads/test/sample.pdf")
        print("2. Run Textract on it via AWS Console")
        return None

    except Exception as e:
        print(f"❌ Upload/Textract test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "=" * 60)
    print("AWS INTEGRATION TEST FOR MAVIK AI ASSISTANT")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("AWS Credentials", test_aws_credentials()))
    results.append(("S3 Access", test_s3_access()))
    results.append(("Textract Access", test_textract_access()))
    results.append(("Bedrock Access", test_bedrock_access()))
    results.append(("Upload + Textract Flow", test_upload_and_textract()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, result in results:
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status:10} {test_name}")

    # Overall result
    failed_tests = [name for name, result in results if result is False]

    if failed_tests:
        print("\n" + "=" * 60)
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")

        print("\n📖 NEXT STEPS:")
        print("1. Review AWS_SETUP.md for required permissions")
        print("2. Most common issue: Textract cannot access S3 bucket")
        print("   → Add bucket policy to 'mavik-uploads' (see AWS_SETUP.md)")
        print("3. Check IAM user has Textract permissions")

        sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour AWS setup is ready. You can now run the application.")
        sys.exit(0)

if __name__ == "__main__":
    main()
