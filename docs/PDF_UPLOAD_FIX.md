# PDF Upload Fix Summary

## Problem
When uploading a PDF in the chat interface and asking about it, the application failed with:
```
"type": "tool", "tool": "doc_parser", "status": "failed",
"summary": "An error occurred (InvalidS3ObjectException) when calling the StartDocumentAnalysis operation:
Unable to get object metadata from S3. Check object key, region and/or access permissions."
```

## Root Cause
**AWS Region Mismatch**: The `.env` file specified `AWS_REGION=us-east-1`, but the S3 buckets (`mavik-uploads` and `mavik-reports`) are actually located in `us-east-2`.

When the application tried to upload files to S3 and process them with Textract, there was a region mismatch causing Textract to fail.

## Fixes Applied

### 1. Updated AWS Region Configuration
**File**: `backend/.env`
```diff
- AWS_REGION=us-east-1
+ AWS_REGION=us-east-2
```

### 2. Enhanced S3 Upload Logic
**File**: `backend/app.py`
- Added proper content type for PDF uploads
- Added server-side encryption (AES256)
- Added file verification after upload
- Added comprehensive error handling

### 3. Improved Textract Integration
**File**: `backend/mcp/doc_parser.py`
- Added S3 object verification before calling Textract
- Added 1-second delay for S3 eventual consistency
- Added better error messages
- Added pagination support for large documents
- Added timeout handling (5 minutes max)

### 4. Frontend Error Display
**File**: `frontend/components/chat-interface.tsx`
- Tool errors now display in the chat interface
- Users can see which tool failed and why

### 5. Created Diagnostic Tools
**New Files**:
- `backend/test_s3_textract.py` - Comprehensive test suite
- `backend/fix_s3_permissions.py` - Automatic bucket policy fixer
- `AWS_SETUP.md` - Complete AWS setup documentation

## Test Results

All tests now pass:
```
✓ PASS     AWS Credentials
✓ PASS     S3 Access
✓ PASS     Textract Access
✓ PASS     Bedrock Access
✓ PASS     Upload + Textract Flow (end-to-end PDF processing)
```

## How to Use

### Upload PDF and Ask Questions:
1. Click "Attach PDF" in the chat interface
2. Select your offering memorandum PDF
3. Type your question or analysis prompt
4. Click "Send"
5. The system will:
   - Upload PDF to S3 (us-east-2)
   - Extract text using Textract
   - Analyze with Claude
   - Stream the response back

### Test the System:
```bash
cd backend
python test_s3_textract.py
```

### If Issues Persist:
```bash
cd backend
python fix_s3_permissions.py
```

## Technical Details

### Upload Flow:
1. Frontend sends multipart/form-data to `/api/chat`
2. Backend uploads file to `s3://mavik-uploads/uploads/{uuid}/{filename}`
3. S3 upload uses AES256 encryption
4. File existence is verified with `head_object()`
5. File URL is passed to orchestrator

### Textract Flow:
1. Doc parser receives S3 URL
2. Verifies object exists in S3
3. Waits 1 second for S3 consistency
4. Starts Textract async job
5. Polls every 3 seconds for completion
6. Extracts text and tables
7. Returns results to orchestrator

### Error Handling:
- All S3 errors are caught and logged
- Textract failures are reported to user
- Tool status is streamed in real-time
- Frontend displays errors in chat

## Environment Variables

Ensure your `.env` has:
```bash
AWS_REGION=us-east-2  # MUST match your bucket region
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_UPLOADS=mavik-uploads
S3_BUCKET_REPORTS=mavik-reports
```

## Bucket Policy

The `mavik-uploads` bucket must have this policy to allow Textract access:
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

This policy is already configured correctly.

## Files Modified

1. `backend/.env` - Fixed AWS region
2. `backend/app.py` - Enhanced S3 upload
3. `backend/mcp/doc_parser.py` - Improved Textract integration
4. `frontend/components/chat-interface.tsx` - Added error display

## Files Created

1. `backend/test_s3_textract.py` - Test suite
2. `backend/fix_s3_permissions.py` - Permission fixer
3. `AWS_SETUP.md` - Setup documentation
4. `PDF_UPLOAD_FIX.md` - This file

## Next Steps

The PDF upload and processing flow is now fully functional. You can:

1. Start the backend: `cd backend && python run.py`
2. Start the frontend: `cd frontend && npm run dev`
3. Upload PDFs and get AI-powered analysis
4. Test with the prompts in the main README.md
