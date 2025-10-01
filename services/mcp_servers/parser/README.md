# Parser MCP Server

Document parsing service using AWS Textract and local parsers for the Mavik AI system.

## Overview

The Parser MCP server provides comprehensive document parsing capabilities, including OCR, text extraction, table detection, and form processing. It integrates with AWS Textract for advanced document analysis and provides local fallback parsers for basic functionality.

## Features

- **Multi-Format Support**: PDF, images (PNG, JPEG, TIFF), text files, and Office documents
- **AWS Textract Integration**: Advanced OCR, table extraction, and form processing
- **Local Parsing Fallbacks**: PyPDF2 for PDFs, basic text extraction
- **Format Detection**: Automatic document format detection with validation
- **Structured Output**: Consistent parsed document format with metadata
- **MCP Protocol**: WebSocket-based JSON-RPC communication
- **HTTP Upload**: REST API for document upload and parsing
- **Comprehensive Testing**: Unit and integration tests with mocking

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LangGraph     │───▶│   Parser MCP     │───▶│   AWS Textract  │
│   Orchestrator  │    │   Server         │    │   (Advanced)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌──────────────────┐
                       │   Local Parsers  │
                       │   (Fallback)     │
                       └──────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- AWS credentials configured (for Textract)
- Poppler utilities (for PDF processing)
- Tesseract OCR (optional, for image processing)

### Local Development

```bash
# Clone the repository
cd services/mcp_servers/parser

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install poppler-utils tesseract-ocr

# Install Python dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your AWS settings

# Run the server
poetry run python -m uvicorn src.parser_server.main:app --reload --port 8002
```

### Docker

```bash
# Build the image
docker build -t mavik-parser-server .

# Run the container
docker run -p 8002:8002 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e AWS_REGION=us-east-1 \
  mavik-parser-server
```

## Configuration

### Environment Variables

| Variable                 | Description                   | Default     |
| ------------------------ | ----------------------------- | ----------- |
| `AWS_REGION`             | AWS region for Textract       | `us-east-1` |
| `TEXTRACT_MAX_PAGES`     | Maximum pages per document    | `3000`      |
| `PARSER_TIMEOUT_SECONDS` | Request timeout               | `300`       |
| `USE_LOCAL_FALLBACK`     | Enable local parsing fallback | `true`      |
| `LOG_LEVEL`              | Logging level                 | `INFO`      |

### Parser Configuration

```python
# Document processing limits
MAX_FILE_SIZE_MB = 500        # Maximum file size
MAX_PAGES_PER_DOC = 3000      # Textract limit
SUPPORTED_FORMATS = {
    'pdf': ['.pdf'],
    'image': ['.png', '.jpg', '.jpeg', '.tiff', '.gif', '.bmp'],
    'text': ['.txt', '.md', '.rtf'],
    'office': ['.docx', '.doc', '.pptx', '.ppt']
}

# Textract features
EXTRACT_TABLES = True         # Extract table data
EXTRACT_FORMS = True          # Extract key-value pairs
EXTRACT_SIGNATURES = False    # Detect signatures (premium)
```

## API Reference

### WebSocket Endpoint

**URL**: `ws://localhost:8002/mcp`

The server implements the MCP protocol over WebSocket with JSON-RPC messaging.

### Available Methods

#### 1. Parse Document

Parse document from file path or S3 location.

**Method**: `parser/parse_document`

**Request**:
```json
{
  "id": "parse_001",
  "method": "parser/parse_document",
  "params": {
    "document_source": "s3://bucket/document.pdf",
    "document_id": "doc_123",
    "options": {
      "extract_tables": true,
      "extract_forms": true,
      "extract_signatures": false
    }
  }
}
```

**Response**:
```json
{
  "id": "parse_001",
  "result": {
    "document_id": "doc_123",
    "parsed_document": {
      "metadata": {
        "document_id": "doc_123",
        "source_location": "s3://bucket/document.pdf",
        "processing_timestamp": "2024-01-15T10:30:00Z",
        "total_pages": 5,
        "content_type": "application/pdf",
        "file_size": 2048576,
        "parser_version": "textract-1.0"
      },
      "pages": [
        {
          "page_number": 1,
          "elements": [
            {
              "element_type": "line",
              "text": "OFFERING MEMORANDUM",
              "bounding_box": {
                "left": 0.1,
                "top": 0.1,
                "width": 0.8,
                "height": 0.05
              },
              "confidence": 99.5,
              "properties": {
                "word_count": 2,
                "words": [...]
              }
            }
          ],
          "bounding_box": {...},
          "width": 1.0,
          "height": 1.0
        }
      ],
      "tables": [
        {
          "table_id": "table_1",
          "rows": [
            ["Tenant", "SF", "Lease Exp", "Credit"],
            ["DataTech Solutions", "25,000", "Dec 2029", "BBB+"]
          ],
          "bounding_box": {...},
          "confidence": 95.0
        }
      ],
      "forms": [
        {
          "key": "Purchase Price",
          "value": "$50,000,000",
          "confidence": 94.5,
          "key_bounding_box": {...},
          "value_bounding_box": {...}
        }
      ],
      "full_text": "OFFERING MEMORANDUM\n300 Hillsborough Street..."
    },
    "processing_timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### 2. Upload Document

Parse document uploaded to S3.

**Method**: `parser/upload_document`

**Request**:
```json
{
  "id": "upload_001",
  "method": "parser/upload_document",
  "params": {
    "s3_bucket": "mavik-documents",
    "s3_key": "uploads/temp/doc.pdf",
    "document_id": "upload_123",
    "filename": "investment-memo.pdf",
    "options": {
      "extract_tables": true,
      "extract_forms": false
    }
  }
}
```

#### 3. Get Capabilities

Get parser capabilities and supported formats.

**Method**: `parser/get_capabilities`

**Request**:
```json
{
  "id": "caps_001",
  "method": "parser/get_capabilities",
  "params": {}
}
```

**Response**:
```json
{
  "id": "caps_001",
  "result": {
    "capabilities": {
      "parsers": {
        "textract": true,
        "local_pdf": true,
        "local_text": true
      },
      "capabilities": {
        "s3_documents": true,
        "local_files": true,
        "table_extraction": true,
        "form_extraction": true,
        "ocr": true
      },
      "supported_formats": ["pdf", "image", "text", "office"]
    },
    "server_info": {
      "version": "1.0.0",
      "service": "parser-mcp-server",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  }
}
```

### HTTP Endpoints

#### Health Check

**GET** `/health`

Returns server health status and capabilities.

```json
{
  "service": "parser-mcp-server",
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "capabilities": {
    "parsers": {
      "textract": true,
      "local_pdf": true,
      "local_text": true
    },
    "supported_formats": ["pdf", "image", "text"]
  }
}
```

#### Upload Document

**POST** `/upload`

Upload and parse document via HTTP multipart.

**Request**:
```bash
curl -X POST "http://localhost:8002/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "document_id=my_doc_123" \
  -F "extract_tables=true" \
  -F "extract_forms=true"
```

**Response**:
```json
{
  "document_id": "my_doc_123",
  "filename": "document.pdf",
  "parsed_document": {...},
  "processing_time": "2024-01-15T10:30:00Z"
}
```

## Document Processing

### Supported Formats

| Format | Extensions                                       | Parser          | Features                 |
| ------ | ------------------------------------------------ | --------------- | ------------------------ |
| PDF    | `.pdf`                                           | Textract/PyPDF2 | Text, tables, forms, OCR |
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.gif`, `.bmp` | Textract        | OCR, tables, forms       |
| Text   | `.txt`, `.md`, `.rtf`                            | Local           | Text extraction          |
| Office | `.docx`, `.doc`, `.pptx`, `.ppt`                 | Future          | Text, structure          |

### Processing Pipeline

1. **Format Detection**: Identify document type and validate format
2. **Parser Selection**: Choose Textract (advanced) or local parser (fallback)
3. **Content Extraction**: Extract text, detect structure, OCR if needed
4. **Structure Analysis**: Identify tables, forms, key-value pairs
5. **Metadata Generation**: Create document metadata and processing info
6. **Response Formatting**: Structure output according to common models

### Textract Features

#### Text Extraction
- **OCR**: Optical character recognition for scanned documents
- **Layout Analysis**: Preserve document structure and reading order
- **Confidence Scores**: Per-word and per-line confidence ratings
- **Bounding Boxes**: Precise coordinate information for all elements

#### Table Detection
- **Automatic Detection**: Identify tables without manual configuration
- **Cell Extraction**: Extract individual cell content and structure
- **Header Recognition**: Distinguish header rows and columns
- **Spanning Cells**: Handle merged cells and complex layouts

#### Form Processing
- **Key-Value Pairs**: Extract form fields and their values
- **Relationship Mapping**: Link form keys to their corresponding values
- **Field Types**: Identify checkboxes, text fields, and selection boxes
- **Confidence Scoring**: Quality assessment for extracted form data

### Local Parser Capabilities

#### PDF Processing (PyPDF2)
- **Text Extraction**: Basic text content extraction
- **Page Separation**: Process multi-page documents
- **Metadata**: Extract PDF properties and information
- **Fallback Mode**: Available when Textract is unavailable

#### Text Processing
- **Encoding Detection**: Handle various text encodings
- **Format Preservation**: Maintain line breaks and structure
- **Metadata Creation**: Generate processing information

## Performance

### Benchmarks

| Operation           | Textract      | Local Parser  |
| ------------------- | ------------- | ------------- |
| PDF Text Extraction | 10s (5 pages) | 2s (5 pages)  |
| Table Detection     | 15s (complex) | Not available |
| Form Processing     | 12s (2 forms) | Not available |
| Image OCR           | 8s (1 page)   | Not available |

### Optimization

- **Parallel Processing**: Concurrent page processing where possible
- **Format Detection**: Skip expensive operations for simple documents
- **Local Fallback**: Fast processing when advanced features not needed
- **Connection Pooling**: Reuse AWS connections for efficiency

## Error Handling

### Common Error Types

1. **ValidationError**: Invalid input parameters or unsupported formats
2. **DocumentProcessingError**: Parsing failures or corrupted documents
3. **AWSServiceError**: Textract service issues or quota limits
4. **TimeoutError**: Processing timeout for large documents

### Error Response Format

```json
{
  "id": "request_123",
  "error": {
    "code": "PROCESSING_ERROR",
    "message": "Document parsing failed: Invalid PDF structure",
    "details": {
      "document_id": "failed_doc",
      "parser_used": "textract",
      "error_location": "page 3"
    }
  }
}
```

### Retry and Fallback

- **Textract Failures**: Automatic fallback to local parsers
- **Quota Limits**: Queue requests and retry with exponential backoff
- **Timeout Handling**: Cancel long-running operations gracefully
- **Partial Success**: Return successfully processed pages even if some fail

## Security

### Input Validation

- **File Size Limits**: Prevent oversized document uploads
- **Format Validation**: Verify file types and content
- **Content Scanning**: Basic malware prevention (file signatures)
- **Rate Limiting**: Prevent abuse and resource exhaustion

### Data Protection

- **Temporary Files**: Secure handling and cleanup of temp files
- **Memory Management**: Clear sensitive content from memory
- **Access Logging**: Track document processing activities
- **AWS Security**: Use IAM roles and secure connections

## Development

### Testing

```bash
# Run unit tests
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest --cov=src tests/

# Run integration tests
poetry run pytest tests/ -m integration

# Test specific parser
poetry run pytest tests/test_parser_server.py::TestTextractParser -v
```

### Code Quality

```bash
# Format code
poetry run ruff format src/ tests/

# Lint code
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/
```

### Local Testing

```bash
# Test with local PDF
curl -X POST "http://localhost:8002/upload" \
  -F "file=@test.pdf" \
  -F "document_id=test_123"

# Test WebSocket connection
python -c "
import asyncio
import websockets
import json

async def test():
    uri = 'ws://localhost:8002/mcp'
    async with websockets.connect(uri) as ws:
        request = {
            'id': 'test_1',
            'method': 'parser/get_capabilities',
            'params': {}
        }
        await ws.send(json.dumps(request))
        response = await ws.recv()
        print(response)

asyncio.run(test())
"
```

## Deployment

### Production Considerations

1. **Resource Allocation**:
   - Memory: 4GB minimum for large document processing
   - CPU: 4 cores minimum for parallel processing
   - Storage: Temporary space for document processing

2. **AWS Configuration**:
   - Textract service limits and quotas
   - IAM roles with appropriate permissions
   - S3 access for document storage

3. **Security**:
   - VPC endpoints for AWS services
   - Document encryption in transit and at rest
   - Access controls and audit logging

4. **Monitoring**:
   - Processing time and success rates
   - AWS service usage and costs
   - Error rates and failure patterns

### Scaling

- **Horizontal Scaling**: Multiple parser instances
- **Load Balancing**: Distribute processing load
- **Queue Management**: Handle processing backlogs
- **Resource Monitoring**: Auto-scaling based on demand

## Troubleshooting

### Common Issues

1. **Textract Quota Exceeded**:
   - Check AWS service quotas
   - Implement request queuing
   - Use local fallback parsers

2. **Large Document Timeout**:
   - Increase timeout settings
   - Break documents into smaller chunks
   - Use asynchronous processing

3. **Poor OCR Quality**:
   - Check document image quality
   - Verify supported formats
   - Consider preprocessing images

### Debug Commands

```bash
# Check Textract service
aws textract describe-document-analysis --job-id YOUR_JOB_ID

# Test local PDF parsing
python -c "
from parser_server.document_parser import LocalPDFParser
import asyncio
parser = LocalPDFParser()
result = asyncio.run(parser.parse_pdf('test.pdf', 'test'))
print(f'Pages: {len(result.pages)}')
"

# Check server health
curl http://localhost:8002/health
```

## Contributing

1. Follow existing code patterns and architecture
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Consider performance impact of changes
5. Test with various document types and sizes

## License

Internal Mavik AI codebase - All rights reserved.
