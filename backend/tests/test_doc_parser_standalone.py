"""
Standalone test for the document parser MCP
Tests AWS Textract integration with S3
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp.doc_parser import extract_pdf_text

async def test_document_parser():
    """Test document parser with a real S3 file"""

    print("=" * 60)
    print("DOCUMENT PARSER MCP TEST")
    print("=" * 60)

    # Test 1: Check AWS credentials
    print("\n[1] Checking AWS Configuration...")
    aws_region = os.getenv('AWS_REGION')
    aws_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')

    if not aws_region:
        print("[FAIL] AWS_REGION not set")
        return False
    if not aws_key_id:
        print("[FAIL] AWS_ACCESS_KEY_ID not set")
        return False
    if not aws_secret:
        print("[FAIL] AWS_SECRET_ACCESS_KEY not set")
        return False

    print(f"[OK] AWS Region: {aws_region}")
    print(f"[OK] AWS Access Key ID: {aws_key_id[:10]}...")

    # Test 2: List recent files in S3
    print("\n[2] Checking S3 for recent uploads...")
    try:
        import boto3
        s3_client = boto3.client('s3', region_name=aws_region)

        # List objects in uploads folder
        response = s3_client.list_objects_v2(
            Bucket='mavik-uploads',
            Prefix='uploads/',
            MaxKeys=10
        )

        if 'Contents' not in response or len(response['Contents']) == 0:
            print("[FAIL] No files found in s3://mavik-uploads/uploads/")
            print("   Please upload a PDF through the frontend first")
            return False

        print(f"[OK] Found {len(response['Contents'])} files:")
        for obj in response['Contents'][:5]:
            size_kb = obj['Size'] / 1024
            print(f"   - {obj['Key']} ({size_kb:.1f} KB) - {obj['LastModified']}")

        # Get the most recent PDF
        pdf_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.pdf')]
        if not pdf_files:
            print("[FAIL] No PDF files found")
            return False

        latest_pdf = sorted(pdf_files, key=lambda x: x['LastModified'], reverse=True)[0]
        s3_url = f"s3://mavik-uploads/{latest_pdf['Key']}"
        print(f"\n[OK] Using latest PDF: {s3_url}")

    except Exception as e:
        print(f"[FAIL] S3 Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Extract text from PDF
    print("\n[3] Extracting text from PDF using AWS Textract...")
    try:
        result = await extract_pdf_text(s3_url)

        text = result.get('text', '')
        tables = result.get('tables', [])

        print(f"[OK] Extraction completed!")
        print(f"   - Extracted text length: {len(text)} characters")
        print(f"   - Number of tables: {len(tables)}")

        # Show first 500 characters
        print(f"\n[TEXT] First 500 characters of extracted text:")
        print("-" * 60)
        print(text[:500])
        print("-" * 60)

        if len(tables) > 0:
            print(f"\n[TABLE] First table preview:")
            print("-" * 60)
            table_data = tables[0].get('data', [])
            for row in table_data[:3]:
                print(row)
            print("-" * 60)

        return True

    except Exception as e:
        print(f"[FAIL] Textract Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nStarting document parser test...")
    print("Make sure you have:")
    print("1. Set AWS credentials in .env")
    print("2. Uploaded a PDF through the frontend")
    print()

    success = asyncio.run(test_document_parser())

    if success:
        print("\n" + "=" * 60)
        print("[SUCCESS] ALL TESTS PASSED - Document Parser is working!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[FAILED] TESTS FAILED - See errors above")
        print("=" * 60)
        sys.exit(1)
