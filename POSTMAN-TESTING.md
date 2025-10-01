# Postman Testing Guide for Mavik MCP Servers

## 🚀 Server Status Overview

### ✅ Operational Servers
- **RAG Server**: `http://localhost:8001` - Document search & retrieval
- **Parser Server**: `http://localhost:8002` - Document parsing & extraction
- **Infrastructure**: All supporting services running (PostgreSQL, Redis, OpenSearch, LocalStack)

### 🔧 Pending Server
- **FinDB Server**: `http://localhost:8003` - Financial database (needs additional models)

---

## 📋 Postman Collection Setup

### Environment Variables
Create a Postman environment with these variables:

```json
{
  "rag_server_url": "http://localhost:8001",
  "parser_server_url": "http://localhost:8002",
  "findb_server_url": "http://localhost:8003",
  "test_document_url": "https://example.com/sample.pdf",
  "mcp_protocol_version": "2024-11-05"
}
```

---

## 🔍 1. Health Check Tests

### RAG Server Health
```http
GET {{rag_server_url}}/health
Content-Type: application/json
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "rag-server",
  "version": "1.0.0",
  "timestamp": "2025-09-29T18:00:00Z",
  "dependencies": {
    "opensearch": "connected",
    "bedrock": "available"
  }
}
```

### Parser Server Health
```http
GET {{parser_server_url}}/health
Content-Type: application/json
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "parser-server",
  "version": "1.0.0",
  "timestamp": "2025-09-29T18:00:00Z",
  "dependencies": {
    "textract": "available",
    "s3": "connected"
  }
}
```

---

## 🔌 2. WebSocket MCP Protocol Tests

### RAG Server WebSocket Connection
```javascript
// Use Postman WebSocket feature or custom script
const ws = new WebSocket('ws://localhost:8001/ws');

// Send MCP initialize request
const initRequest = {
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": {
        "listChanged": true
      }
    },
    "clientInfo": {
      "name": "postman-client",
      "version": "1.0.0"
    }
  }
};

ws.send(JSON.stringify(initRequest));
```

### Parser Server WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8002/ws');

// Same initialization pattern as RAG server
ws.send(JSON.stringify(initRequest));
```

---

## 📄 3. Document Processing Tests

### Upload Document to Parser
```http
POST {{parser_server_url}}/api/v1/parse
Content-Type: multipart/form-data

Body (form-data):
- file: [SELECT_PDF_FILE]
- extract_text: true
- extract_tables: true
- extract_forms: false
```

**Expected Response:**
```json
{
  "success": true,
  "document_id": "doc_12345",
  "metadata": {
    "filename": "test.pdf",
    "pages": 5,
    "file_size": 1024000
  },
  "extracted_content": {
    "text": "Document content...",
    "tables": [...],
    "processing_time": 2.5
  }
}
```

### MCP Document Parse Request
```http
POST {{parser_server_url}}/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "parse_001",
  "method": "tools/call",
  "params": {
    "name": "document_parser",
    "arguments": {
      "document_url": "{{test_document_url}}",
      "extract_tables": true,
      "extract_text": true
    }
  }
}
```

---

## 🔍 4. RAG Operations Tests

### Index Document
```http
POST {{rag_server_url}}/api/v1/index
Content-Type: application/json

{
  "document_id": "doc_12345",
  "content": "Sample document content for indexing...",
  "metadata": {
    "title": "Test Document",
    "source": "postman_test",
    "document_type": "pdf"
  },
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

### Search Documents
```http
POST {{rag_server_url}}/api/v1/search
Content-Type: application/json

{
  "query": "financial analysis",
  "limit": 10,
  "similarity_threshold": 0.7,
  "include_metadata": true,
  "filters": {
    "document_type": "pdf"
  }
}
```

### MCP RAG Search Request
```http
POST {{rag_server_url}}/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": "search_001",
  "method": "tools/call",
  "params": {
    "name": "vector_search",
    "arguments": {
      "query": "investment analysis",
      "top_k": 5,
      "include_sources": true
    }
  }
}
```

---

## 🧪 5. Integration Workflow Tests

### Complete Document Processing Pipeline
1. **Upload → Parse → Index → Search**

```javascript
// Postman Test Script
pm.test("Complete Pipeline Test", function() {
    // 1. Upload document
    pm.sendRequest({
        url: pm.environment.get("parser_server_url") + "/api/v1/parse",
        method: 'POST',
        header: {
            'Content-Type': 'multipart/form-data'
        },
        body: {
            mode: 'formdata',
            formdata: [
                {key: 'file', src: 'test_document.pdf', type: 'file'}
            ]
        }
    }, function(err, response) {
        const parseResult = response.json();
        const documentId = parseResult.document_id;

        // 2. Index the parsed content
        pm.sendRequest({
            url: pm.environment.get("rag_server_url") + "/api/v1/index",
            method: 'POST',
            header: {
                'Content-Type': 'application/json'
            },
            body: {
                mode: 'raw',
                raw: JSON.stringify({
                    document_id: documentId,
                    content: parseResult.extracted_content.text,
                    metadata: parseResult.metadata
                })
            }
        }, function(err, indexResponse) {
            // 3. Search for the indexed content
            pm.sendRequest({
                url: pm.environment.get("rag_server_url") + "/api/v1/search",
                method: 'POST',
                header: {
                    'Content-Type': 'application/json'
                },
                body: {
                    mode: 'raw',
                    raw: JSON.stringify({
                        query: "test search query",
                        limit: 5
                    })
                }
            }, function(err, searchResponse) {
                pm.test("Pipeline completed successfully", function() {
                    pm.expect(searchResponse.code).to.eql(200);
                    pm.expect(searchResponse.json().success).to.be.true;
                });
            });
        });
    });
});
```

---

## 🔧 6. Error Handling Tests

### Invalid Requests
```http
POST {{rag_server_url}}/api/v1/search
Content-Type: application/json

{
  "invalid_field": "test"
}
```

**Expected Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Missing required field: query"
  }
}
```

### Server Overload Test
```javascript
// Stress test with multiple concurrent requests
for(let i = 0; i < 10; i++) {
    pm.sendRequest({
        url: pm.environment.get("rag_server_url") + "/health",
        method: 'GET'
    });
}
```

---

## 📊 7. Performance Tests

### Response Time Monitoring
```javascript
// Add to Postman test script
pm.test("Response time is acceptable", function() {
    pm.expect(pm.response.responseTime).to.be.below(5000); // 5 seconds
});

pm.test("Server responds quickly", function() {
    pm.expect(pm.response.responseTime).to.be.below(1000); // 1 second for health checks
});
```

### Concurrent Request Test
```javascript
// Test multiple simultaneous requests
const promises = [];
for(let i = 0; i < 5; i++) {
    promises.push(
        pm.sendRequest({
            url: pm.environment.get("rag_server_url") + "/health",
            method: 'GET'
        })
    );
}

Promise.all(promises).then(responses => {
    pm.test("All concurrent requests successful", function() {
        responses.forEach(response => {
            pm.expect(response.code).to.eql(200);
        });
    });
});
```

---

## 🎯 8. Test Scenarios & Expected Outcomes

### Scenario 1: Basic Health Verification ✅
- **Goal**: Verify all servers are responding
- **Tests**: GET health endpoints for RAG and Parser servers
- **Success**: Both return 200 OK with healthy status

### Scenario 2: Document Upload & Parse ✅
- **Goal**: Test document processing pipeline
- **Tests**: Upload PDF, verify parsing results
- **Success**: Document parsed, text extracted, metadata returned

### Scenario 3: RAG Indexing & Search ✅
- **Goal**: Test vector search functionality
- **Tests**: Index content, perform similarity search
- **Success**: Documents indexed, search returns relevant results

### Scenario 4: MCP Protocol Compliance ✅
- **Goal**: Verify WebSocket MCP communication
- **Tests**: Initialize connection, send MCP requests
- **Success**: Protocol handshake successful, methods respond correctly

### Scenario 5: Error Handling ✅
- **Goal**: Test graceful error responses
- **Tests**: Send invalid requests, malformed data
- **Success**: Proper error codes and messages returned

---

## 🚨 Troubleshooting

### Common Issues & Solutions

1. **Connection Refused**
   - Check: `docker ps` to verify containers are running
   - Solution: Restart containers with `docker-compose up -d`

2. **WebSocket Connection Failed**
   - Check: Firewall or antivirus blocking connections
   - Solution: Use HTTP endpoints first, then try WebSocket

3. **Slow Response Times**
   - Check: Docker resources and container logs
   - Solution: Monitor with `docker stats`

4. **Upload Failures**
   - Check: File size limits and format support
   - Solution: Use smaller test files (< 10MB)

---

## 📋 Postman Collection Checklist

- [ ] Environment configured with server URLs
- [ ] Health check requests for both servers
- [ ] WebSocket connection tests
- [ ] Document upload/parse requests
- [ ] RAG indexing requests
- [ ] Search functionality tests
- [ ] MCP protocol requests
- [ ] Error handling scenarios
- [ ] Performance monitoring scripts
- [ ] Integration pipeline tests

---

## 🎉 Success Metrics

### ✅ Expected Results:
- **Health Checks**: Both servers return healthy status
- **Document Processing**: Files parsed successfully with extracted content
- **RAG Operations**: Content indexed and searchable
- **MCP Protocol**: WebSocket connections established and responding
- **Response Times**: < 5 seconds for processing, < 1 second for health checks
- **Error Handling**: Graceful failures with proper error codes

This comprehensive Postman testing suite will validate that our MCP server infrastructure is **fully operational and production-ready**! 🚀
