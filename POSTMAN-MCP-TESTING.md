# Postman MCP Server Testing Guide

## Overview
This guide provides step-by-step instructions for testing both RAG Server (port 8001) and Parser Server (port 8002) using Postman without requiring admin access or command-line tools.

## Prerequisites
- Postman Desktop Application installed
- Both MCP servers running (confirmed via `docker-compose ps`)
- RAG Server: http://localhost:8001
- Parser Server: http://localhost:8002

---

## 1. RAG SERVER TESTING (Port 8001)

### 1.1 Health Check Test

**Request Setup:**
- **Method:** GET
- **URL:** `http://localhost:8001/health`
- **Headers:** None required

**Expected Response:**
```json
{
    "service": "rag-mcp-server",
    "status": "healthy",
    "timestamp": "2025-09-30T13:36:48.123Z",
    "version": "1.0.0",
    "dependencies": {
        "opensearch": true,
        "index_exists": true
    }
}
```

**Status Code:** 200 OK

---

### 1.2 MCP WebSocket Testing for RAG Server

Since Postman doesn't natively support WebSocket MCP protocol testing, we'll use HTTP requests to test the core functionality that the MCP WebSocket would use.

#### 1.2.1 Test RAG Search Functionality

**Create a new request:**
- **Method:** POST
- **URL:** `http://localhost:8001/test-search` *(Note: This endpoint may not exist, we'll test via WebSocket simulation)*

**Alternative approach - Test OpenSearch connection:**
- **Method:** GET
- **URL:** `http://localhost:9200/_cluster/health`
- **Headers:** None

**Expected Response:**
```json
{
    "cluster_name": "docker-cluster",
    "status": "yellow",
    "timed_out": false,
    "number_of_nodes": 1
}
```

#### 1.2.2 Simulate MCP JSON-RPC Request Structure

Create a POST request to test the WebSocket MCP endpoint structure:

**Request Setup:**
- **Method:** POST
- **URL:** `http://localhost:8001/mcp-test` *(Simulated endpoint)*
- **Headers:**
  - `Content-Type: application/json`

**Body (raw JSON):**
```json
{
    "jsonrpc": "2.0",
    "method": "list_tools",
    "params": {},
    "id": "test-001"
}
```

**Expected Response Structure:**
```json
{
    "jsonrpc": "2.0",
    "result": {
        "tools": [
            {
                "name": "rag_search",
                "description": "Search documents using vector similarity and text matching",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text"
                        }
                    }
                }
            }
        ]
    },
    "id": "test-001"
}
```

---

## 2. PARSER SERVER TESTING (Port 8002)

### 2.1 Health Check Test

**Request Setup:**
- **Method:** GET
- **URL:** `http://localhost:8002/health`
- **Headers:** None required

**Expected Response:**
```json
{
    "service": "parser-mcp-server",
    "status": "healthy",
    "timestamp": "2025-09-30T13:36:48.123Z",
    "version": "1.0.0",
    "capabilities": {
        "textract_available": true,
        "supported_formats": ["pdf", "docx", "xlsx", "pptx", "png", "jpg"],
        "local_fallback": true
    }
}
```

**Status Code:** 200 OK

---

### 2.2 Document Upload Test

**Request Setup:**
- **Method:** POST
- **URL:** `http://localhost:8002/upload`
- **Headers:**
  - `Content-Type: multipart/form-data` (Postman will set this automatically)

**Body (form-data):**
- **Key:** `file` (type: File)
  - **Value:** Upload a test PDF/Word document
- **Key:** `document_id` (type: Text)
  - **Value:** `test-doc-001`
- **Key:** `extract_tables` (type: Text)
  - **Value:** `true`
- **Key:** `extract_forms` (type: Text)
  - **Value:** `true`

**Expected Response:**
```json
{
    "document_id": "test-doc-001",
    "filename": "test-document.pdf",
    "parsed_document": {
        "document_id": "test-doc-001",
        "content": "Extracted text content...",
        "tables": [],
        "confidence": 0.95
    },
    "processing_time": "2025-09-30T13:36:48.123Z"
}
```

**Status Code:** 200 OK

---

### 2.3 MCP WebSocket Simulation for Parser

#### 2.3.1 Test Parser Capabilities

**Request Setup:**
- **Method:** POST
- **URL:** `http://localhost:8002/mcp-test` *(Simulated)*
- **Headers:**
  - `Content-Type: application/json`

**Body (raw JSON):**
```json
{
    "jsonrpc": "2.0",
    "method": "parser/get_capabilities",
    "params": {},
    "id": "parser-test-001"
}
```

**Expected Response:**
```json
{
    "jsonrpc": "2.0",
    "result": {
        "capabilities": {
            "textract_available": true,
            "supported_formats": ["pdf", "docx", "xlsx", "pptx", "png", "jpg"],
            "local_fallback": true
        },
        "server_info": {
            "version": "1.0.0",
            "service": "parser-mcp-server"
        }
    },
    "id": "parser-test-001"
}
```

---

## 3. INFRASTRUCTURE VALIDATION

### 3.1 OpenSearch Health Check

**Request Setup:**
- **Method:** GET
- **URL:** `http://localhost:9200/_cluster/health`

**Expected Response:**
```json
{
    "cluster_name": "docker-cluster",
    "status": "yellow",
    "timed_out": false,
    "number_of_nodes": 1,
    "number_of_data_nodes": 1
}
```

### 3.2 LocalStack Health Check (AWS Services)

**Request Setup:**
- **Method:** GET
- **URL:** `http://localhost:4566/_localstack/health`

**Expected Response:**
```json
{
    "services": {
        "s3": "available",
        "textract": "available"
    },
    "edition": "community"
}
```

---

## 4. ERROR TESTING

### 4.1 Test Invalid Endpoints

#### 4.1.1 RAG Server - Invalid Endpoint
- **Method:** GET
- **URL:** `http://localhost:8001/invalid-endpoint`
- **Expected:** 404 Not Found

#### 4.1.2 Parser Server - Invalid Method
- **Method:** GET
- **URL:** `http://localhost:8002/mcp`
- **Expected:** 405 Method Not Allowed (WebSocket endpoint)

### 4.2 Test Invalid JSON-RPC Requests

**Request Setup:**
- **Method:** POST
- **URL:** `http://localhost:8001/health` (wrong endpoint for JSON-RPC)
- **Headers:** `Content-Type: application/json`
- **Body:**
```json
{
    "invalid": "json-rpc-request"
}
```

**Expected:** 405 Method Not Allowed or validation error

---

## 5. POSTMAN COLLECTION SETUP

### 5.1 Create Environment Variables

1. Click "Environment" tab in Postman
2. Create new environment: "MCP Local Testing"
3. Add variables:
   - `rag_base_url`: `http://localhost:8001`
   - `parser_base_url`: `http://localhost:8002`
   - `opensearch_url`: `http://localhost:9200`
   - `localstack_url`: `http://localhost:4566`

### 5.2 Organize Requests into Collections

Create collections:
1. **RAG Server Tests**
   - Health Check
   - OpenSearch Connection
   - MCP Protocol Simulation

2. **Parser Server Tests**
   - Health Check
   - Document Upload
   - MCP Capabilities

3. **Infrastructure Tests**
   - OpenSearch Health
   - LocalStack Health

---

## 6. VALIDATION CHECKLIST

### ✅ RAG Server Validation
- [ ] Health endpoint returns 200 OK
- [ ] Response includes "healthy" status
- [ ] Dependencies show OpenSearch connection
- [ ] Response time < 100ms

### ✅ Parser Server Validation
- [ ] Health endpoint returns 200 OK
- [ ] Capabilities include supported formats
- [ ] Document upload accepts files
- [ ] Parsing returns structured content

### ✅ Infrastructure Validation
- [ ] OpenSearch cluster accessible
- [ ] LocalStack services available
- [ ] All Docker containers healthy
- [ ] Network connectivity confirmed

---

## 7. TROUBLESHOOTING

### Common Issues:
1. **Connection Refused:** Server not running - check `docker-compose ps`
2. **404 Not Found:** Incorrect endpoint URL
3. **405 Method Not Allowed:** Wrong HTTP method for endpoint
4. **503 Service Unavailable:** Service dependencies not ready

### Debug Steps:
1. Verify Docker containers are running and healthy
2. Check port accessibility: 8001 (RAG), 8002 (Parser), 9200 (OpenSearch)
3. Validate JSON syntax in request bodies
4. Check Postman console for detailed error messages

---

## 8. NEXT STEPS

After successful Postman testing:
1. **WebSocket Testing:** Use specialized WebSocket client for full MCP protocol testing
2. **Integration Testing:** Test complete document processing workflows
3. **Performance Testing:** Measure response times under load
4. **Error Handling:** Validate comprehensive error scenarios

**Note:** For true WebSocket MCP testing, consider using tools like:
- WebSocket King (Chrome extension)
- wscat (if available)
- Custom WebSocket client applications
