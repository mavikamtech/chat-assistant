# RAG MCP Server

Document search and retrieval service using OpenSearch and AWS Bedrock for the Mavik AI system.

## Overview

The RAG (Retrieval Augmented Generation) MCP server provides document processing, indexing, and search capabilities for the Mavik AI platform. It uses OpenSearch for vector and text search, AWS Bedrock for embeddings, and implements the Model Context Protocol (MCP) for communication.

## Features

- **Document Processing**: Text extraction, chunking with overlap, and metadata management
- **Vector Search**: Semantic search using AWS Bedrock embeddings (Titan Text v2)
- **Text Search**: BM25-based text matching with highlighting
- **Hybrid Search**: Combines vector and text search for optimal results
- **MCP Protocol**: WebSocket-based JSON-RPC communication
- **Health Monitoring**: Comprehensive health checks and performance monitoring
- **Scalable Architecture**: Docker containerization with configurable resources

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LangGraph     │───▶│   RAG MCP        │───▶│   OpenSearch    │
│   Orchestrator  │    │   Server         │    │   Serverless    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌──────────────────┐
                       │   AWS Bedrock    │
                       │   (Embeddings)   │
                       └──────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- AWS credentials configured
- OpenSearch cluster (local or AWS)

### Local Development

```bash
# Clone the repository
cd services/mcp_servers/rag

# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your AWS and OpenSearch settings

# Run the server
poetry run python -m uvicorn src.rag_server.main:app --reload --port 8001
```

### Docker

```bash
# Build the image
docker build -t mavik-rag-server .

# Run the container
docker run -p 8001:8001 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e OPENSEARCH_ENDPOINT=your_endpoint \
  mavik-rag-server
```

## Configuration

### Environment Variables

| Variable                  | Description                 | Default                        |
| ------------------------- | --------------------------- | ------------------------------ |
| `OPENSEARCH_ENDPOINT`     | OpenSearch cluster endpoint | `localhost:9200`               |
| `OPENSEARCH_INDEX_NAME`   | Index name for documents    | `mavik-documents`              |
| `BEDROCK_REGION`          | AWS region for Bedrock      | `us-east-1`                    |
| `BEDROCK_EMBEDDING_MODEL` | Embedding model ID          | `amazon.titan-embed-text-v2:0` |
| `RAG_TIMEOUT_SECONDS`     | Request timeout             | `30`                           |
| `LOG_LEVEL`               | Logging level               | `INFO`                         |

### Document Processing Settings

```python
# Chunk configuration
CHUNK_SIZE = 1000          # Characters per chunk
CHUNK_OVERLAP = 200        # Overlap between chunks
MAX_CHUNKS_PER_DOC = 500   # Limit chunks per document

# Search configuration
DEFAULT_SEARCH_LIMIT = 10  # Default results per search
MAX_SEARCH_LIMIT = 100     # Maximum results per search
```

## API Reference

### WebSocket Endpoint

**URL**: `ws://localhost:8001/mcp`

The server implements the MCP protocol over WebSocket with JSON-RPC messaging.

### Available Methods

#### 1. Document Search

Search documents using vector similarity and text matching.

**Method**: `rag/search`

**Request**:
```json
{
  "id": "search_001",
  "method": "rag/search",
  "params": {
    "query": "commercial real estate investment",
    "limit": 10,
    "filters": {
      "document_ids": ["doc_1", "doc_2"],
      "source_types": ["pdf"],
      "mnpi_classification": "public"
    },
    "use_vector_search": true,
    "use_text_search": true,
    "include_metadata": true
  }
}
```

**Response**:
```json
{
  "id": "search_001",
  "result": {
    "chunks": [
      {
        "chunk_id": "chunk_123",
        "document_id": "doc_1",
        "content": "Commercial real estate investment opportunity...",
        "page_number": 1,
        "chunk_index": 0,
        "source_type": "pdf",
        "metadata": {
          "title": "Investment Memorandum",
          "deal_id": "deal_001"
        },
        "relevance_score": 0.95,
        "highlights": ["<em>commercial</em> real estate investment"]
      }
    ],
    "total_results": 25,
    "query": "commercial real estate investment",
    "search_time_ms": 45
  }
}
```

#### 2. Index Documents

Index document chunks for search.

**Method**: `rag/index`

**Request**:
```json
{
  "id": "index_001",
  "method": "rag/index",
  "params": {
    "chunks": [
      {
        "chunk_id": "new_chunk_1",
        "document_id": "new_doc",
        "content": "Document content to index...",
        "page_number": 1,
        "chunk_index": 0,
        "source_type": "pdf",
        "metadata": {
          "title": "New Document",
          "deal_id": "deal_002"
        }
      }
    ]
  }
}
```

#### 3. Delete Document

Remove all chunks for a document.

**Method**: `rag/delete`

**Request**:
```json
{
  "id": "delete_001",
  "method": "rag/delete",
  "params": {
    "document_id": "doc_to_delete"
  }
}
```

#### 4. Process Document

Process and index a document from S3.

**Method**: `rag/process_document`

**Request**:
```json
{
  "id": "process_001",
  "method": "rag/process_document",
  "params": {
    "s3_bucket": "mavik-documents",
    "s3_key": "deals/property_om.pdf",
    "document_id": "property_om_123",
    "metadata": {
      "title": "Property Offering Memorandum",
      "deal_id": "deal_123",
      "mnpi_classification": "confidential"
    }
  }
}
```

### HTTP Endpoints

#### Health Check

**GET** `/health`

Returns server health status and component information.

```json
{
  "service": "rag-mcp-server",
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "opensearch": true,
    "index_exists": true
  }
}
```

## Document Processing

### Supported Formats

- PDF documents (via AWS Textract)
- Plain text files
- HTML content (basic extraction)

### Processing Pipeline

1. **Document Extraction**: Extract text from various formats
2. **Text Cleaning**: Remove artifacts, normalize whitespace
3. **Chunking**: Split text into overlapping chunks with sentence boundary detection
4. **Metadata Enhancement**: Add document-level and chunk-level metadata
5. **Embedding Generation**: Create vector embeddings using AWS Bedrock
6. **Indexing**: Store chunks and embeddings in OpenSearch

### Chunking Strategy

The system uses intelligent chunking with:

- **Sentence Boundary Detection**: Avoid breaking sentences
- **Paragraph Awareness**: Preserve document structure
- **Overlap Management**: Ensure context continuity
- **Size Optimization**: Balance chunk size with search relevance

## Search Capabilities

### Vector Search

- **Embedding Model**: Amazon Titan Text Embeddings v2 (1536 dimensions)
- **Similarity Metric**: Cosine similarity
- **Index Type**: OpenSearch k-NN with HNSW algorithm

### Text Search

- **Algorithm**: BM25 scoring
- **Features**: Fuzzy matching, field boosting, phrase queries
- **Highlighting**: Fragment extraction with match emphasis

### Hybrid Search

Combines vector and text search using:
- **Query Rewriting**: Optimize for both search types
- **Score Fusion**: Weighted combination of relevance scores
- **Result Reranking**: Final ranking based on multiple signals

## Performance

### Benchmarks

| Operation            | Latency (p95) | Throughput |
| -------------------- | ------------- | ---------- |
| Document Search      | 150ms         | 100 req/s  |
| Document Indexing    | 2s            | 10 docs/s  |
| Embedding Generation | 300ms         | 50 req/s   |

### Optimization

- **Connection Pooling**: Reuse OpenSearch connections
- **Batch Processing**: Group embedding requests
- **Caching**: Cache frequently accessed embeddings
- **Parallel Processing**: Concurrent chunk processing

## Monitoring

### Health Checks

The server provides comprehensive health monitoring:

- **Component Health**: OpenSearch connectivity, index status
- **Performance Metrics**: Search latency, indexing throughput
- **Error Tracking**: Failed requests, timeout monitoring
- **Resource Usage**: Memory, CPU, connection counts

### Logging

Structured logging with:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "rag-mcp-server",
  "operation": "document_search",
  "query": "investment opportunity",
  "results": 15,
  "latency_ms": 120,
  "filters": {"deal_id": "deal_123"}
}
```

### Metrics

Key metrics tracked:

- Request rate and latency percentiles
- Error rates by operation type
- OpenSearch query performance
- Bedrock API usage and costs
- Document processing throughput

## Security

### Authentication

- **MCP Protocol**: WebSocket connection-based authentication
- **AWS IAM**: Service-to-service authentication for AWS resources
- **MNPI Classification**: Metadata-based access control

### Data Protection

- **Encryption in Transit**: TLS for all connections
- **Encryption at Rest**: OpenSearch and S3 encryption
- **Access Logging**: Comprehensive audit trails
- **Data Retention**: Configurable retention policies

## Development

### Testing

```bash
# Run unit tests
poetry run pytest tests/ -v

# Run integration tests
poetry run pytest tests/ -m integration

# Run with coverage
poetry run pytest --cov=src tests/
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

### Debugging

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
poetry run python -m uvicorn src.rag_server.main:app --reload
```

## Deployment

### Production Considerations

1. **Resource Allocation**:
   - Memory: 2GB minimum for embedding operations
   - CPU: 2 cores minimum for concurrent processing
   - Storage: Depends on document volume

2. **OpenSearch Configuration**:
   - Use dedicated master nodes for clusters >3 nodes
   - Configure appropriate shard sizing
   - Enable slow query logging

3. **Security**:
   - Enable VPC endpoints for AWS services
   - Configure security groups and NACLs
   - Use IAM roles instead of access keys

4. **Monitoring**:
   - Set up CloudWatch alarms
   - Configure log aggregation
   - Monitor costs and usage

### Scaling

The service can be scaled horizontally:

- **Stateless Design**: No local state, supports multiple instances
- **Load Balancing**: Use ALB with WebSocket support
- **Database Scaling**: OpenSearch cluster scaling
- **Caching**: Redis for embedding and search result caching

## Troubleshooting

### Common Issues

1. **Connection Timeouts**:
   - Check OpenSearch cluster health
   - Verify network connectivity and security groups
   - Increase timeout values if needed

2. **Embedding Failures**:
   - Verify Bedrock model availability in region
   - Check rate limits and quotas
   - Ensure proper IAM permissions

3. **Search Performance**:
   - Review index configuration and mapping
   - Check query complexity and filters
   - Monitor resource usage

### Debug Commands

```bash
# Check OpenSearch connectivity
curl -X GET "localhost:9200/_cluster/health"

# Test embedding generation
aws bedrock-runtime invoke-model \
  --model-id amazon.titan-embed-text-v2:0 \
  --body '{"inputText":"test"}' \
  response.json

# Check server health
curl http://localhost:8001/health
```

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation for API changes
4. Use semantic versioning for releases

## License

Internal Mavik AI codebase - All rights reserved.
