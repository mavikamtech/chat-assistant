# WebSocket MCP Protocol Testing Guide

## Overview
This guide covers testing the actual MCP (Model Context Protocol) WebSocket endpoints since the core MCP functionality uses JSON-RPC 2.0 over WebSocket connections.

## WebSocket Testing Options (No Admin Access Required)

### Option 1: Browser Developer Tools (Recommended)

1. **Open Browser Developer Console:**
   - Press F12 in Chrome/Edge
   - Go to Console tab

2. **Test RAG Server WebSocket:**
```javascript
// Connect to RAG MCP WebSocket
const ragSocket = new WebSocket('ws://localhost:8001/mcp');

ragSocket.onopen = function(event) {
    console.log('RAG MCP WebSocket Connected');

    // Send list_tools request
    const request = {
        "jsonrpc": "2.0",
        "method": "list_tools",
        "params": {},
        "id": "rag-test-001"
    };

    ragSocket.send(JSON.stringify(request));
};

ragSocket.onmessage = function(event) {
    console.log('RAG Response:', JSON.parse(event.data));
};

ragSocket.onerror = function(error) {
    console.error('RAG WebSocket Error:', error);
};

// Test RAG search
ragSocket.onopen = function() {
    const searchRequest = {
        "jsonrpc": "2.0",
        "method": "rag/search",
        "params": {
            "query": "test search",
            "limit": 5,
            "use_vector_search": true
        },
        "id": "search-001"
    };
    ragSocket.send(JSON.stringify(searchRequest));
};
```

3. **Test Parser Server WebSocket:**
```javascript
// Connect to Parser MCP WebSocket
const parserSocket = new WebSocket('ws://localhost:8002/mcp');

parserSocket.onopen = function(event) {
    console.log('Parser MCP WebSocket Connected');

    // Send capabilities request
    const request = {
        "jsonrpc": "2.0",
        "method": "parser/get_capabilities",
        "params": {},
        "id": "parser-test-001"
    };

    parserSocket.send(JSON.stringify(request));
};

parserSocket.onmessage = function(event) {
    console.log('Parser Response:', JSON.parse(event.data));
};

parserSocket.onerror = function(error) {
    console.error('Parser WebSocket Error:', error);
};
```

### Option 2: Online WebSocket Tester

1. **Go to:** https://www.websocket.org/echo.html
2. **Or use:** https://hoppscotch.io/realtime/websocket

**For RAG Server:**
- **URL:** `ws://localhost:8001/mcp`
- **Message:**
```json
{
    "jsonrpc": "2.0",
    "method": "list_tools",
    "params": {},
    "id": "test-001"
}
```

**For Parser Server:**
- **URL:** `ws://localhost:8002/mcp`
- **Message:**
```json
{
    "jsonrpc": "2.0",
    "method": "parser/get_capabilities",
    "params": {},
    "id": "test-001"
}
```

### Option 3: Simple HTML Test Page

Create a local HTML file for testing:

```html
<!DOCTYPE html>
<html>
<head>
    <title>MCP WebSocket Tester</title>
</head>
<body>
    <h1>MCP WebSocket Protocol Tester</h1>

    <div>
        <h2>RAG Server Test</h2>
        <button onclick="testRAGServer()">Test RAG WebSocket</button>
        <pre id="ragResults"></pre>
    </div>

    <div>
        <h2>Parser Server Test</h2>
        <button onclick="testParserServer()">Test Parser WebSocket</button>
        <pre id="parserResults"></pre>
    </div>

    <script>
        function testRAGServer() {
            const resultsDiv = document.getElementById('ragResults');
            resultsDiv.textContent = 'Connecting to RAG server...\n';

            const socket = new WebSocket('ws://localhost:8001/mcp');

            socket.onopen = function() {
                resultsDiv.textContent += 'Connected!\n';

                const request = {
                    "jsonrpc": "2.0",
                    "method": "list_tools",
                    "params": {},
                    "id": "test-001"
                };

                socket.send(JSON.stringify(request));
                resultsDiv.textContent += 'Sent: ' + JSON.stringify(request, null, 2) + '\n';
            };

            socket.onmessage = function(event) {
                resultsDiv.textContent += 'Response: ' + JSON.stringify(JSON.parse(event.data), null, 2) + '\n';
            };

            socket.onerror = function(error) {
                resultsDiv.textContent += 'Error: ' + error + '\n';
            };
        }

        function testParserServer() {
            const resultsDiv = document.getElementById('parserResults');
            resultsDiv.textContent = 'Connecting to Parser server...\n';

            const socket = new WebSocket('ws://localhost:8002/mcp');

            socket.onopen = function() {
                resultsDiv.textContent += 'Connected!\n';

                const request = {
                    "jsonrpc": "2.0",
                    "method": "parser/get_capabilities",
                    "params": {},
                    "id": "test-001"
                };

                socket.send(JSON.stringify(request));
                resultsDiv.textContent += 'Sent: ' + JSON.stringify(request, null, 2) + '\n';
            };

            socket.onmessage = function(event) {
                resultsDiv.textContent += 'Response: ' + JSON.stringify(JSON.parse(event.data), null, 2) + '\n';
            };

            socket.onerror = function(error) {
                resultsDiv.textContent += 'Error: ' + error + '\n';
            };
        }
    </script>
</body>
</html>
```

## MCP Protocol Test Scenarios

### 1. RAG Server MCP Tests

#### Test 1: List Tools
```json
{
    "jsonrpc": "2.0",
    "method": "list_tools",
    "params": {},
    "id": "rag-list-001"
}
```

**Expected Response:**
```json
{
    "jsonrpc": "2.0",
    "result": {
        "tools": [
            {
                "name": "rag_search",
                "description": "Search documents using vector similarity and text matching"
            },
            {
                "name": "rag_index",
                "description": "Index document chunks for search"
            }
        ]
    },
    "id": "rag-list-001"
}
```

#### Test 2: RAG Search
```json
{
    "jsonrpc": "2.0",
    "method": "rag/search",
    "params": {
        "query": "test search query",
        "limit": 10,
        "use_vector_search": true,
        "use_text_search": true
    },
    "id": "rag-search-001"
}
```

#### Test 3: Invalid Method
```json
{
    "jsonrpc": "2.0",
    "method": "invalid/method",
    "params": {},
    "id": "rag-invalid-001"
}
```

**Expected Error:**
```json
{
    "jsonrpc": "2.0",
    "error": {
        "code": "METHOD_NOT_FOUND",
        "message": "Unknown method: invalid/method"
    },
    "id": "rag-invalid-001"
}
```

### 2. Parser Server MCP Tests

#### Test 1: Get Capabilities
```json
{
    "jsonrpc": "2.0",
    "method": "parser/get_capabilities",
    "params": {},
    "id": "parser-caps-001"
}
```

#### Test 2: Parse Document (S3)
```json
{
    "jsonrpc": "2.0",
    "method": "parser/parse_document",
    "params": {
        "document_source": "s3://test-bucket/test-doc.pdf",
        "document_id": "test-doc-001",
        "options": {
            "extract_tables": true,
            "extract_forms": true
        }
    },
    "id": "parser-parse-001"
}
```

#### Test 3: Upload Document
```json
{
    "jsonrpc": "2.0",
    "method": "parser/upload_document",
    "params": {
        "s3_bucket": "test-bucket",
        "s3_key": "documents/test.pdf",
        "document_id": "upload-001",
        "filename": "test.pdf",
        "options": {
            "extract_tables": true
        }
    },
    "id": "parser-upload-001"
}
```

## Validation Checklist

### ✅ RAG Server WebSocket Tests
- [ ] Connection establishes successfully
- [ ] list_tools returns available tools
- [ ] rag/search accepts query parameters
- [ ] Error handling for invalid methods
- [ ] Response format follows JSON-RPC 2.0

### ✅ Parser Server WebSocket Tests
- [ ] Connection establishes successfully
- [ ] get_capabilities returns supported formats
- [ ] parse_document handles S3 sources
- [ ] upload_document processes files
- [ ] Response format follows JSON-RPC 2.0

### ✅ Protocol Compliance
- [ ] All responses include jsonrpc: "2.0"
- [ ] Request IDs are properly echoed
- [ ] Error responses follow JSON-RPC error format
- [ ] WebSocket connection handles multiple requests

## Expected Results Summary

| Test                        | Expected Result                                                          |
| --------------------------- | ------------------------------------------------------------------------ |
| RAG WebSocket Connection    | Successful connection to ws://localhost:8001/mcp                         |
| RAG list_tools              | Returns 4 tools: rag_search, rag_index, rag_delete, rag_process_document |
| Parser WebSocket Connection | Successful connection to ws://localhost:8002/mcp                         |
| Parser get_capabilities     | Returns supported formats and textract availability                      |
| Invalid Method Test         | JSON-RPC error response with METHOD_NOT_FOUND                            |
| Malformed JSON              | Connection closes or INVALID_REQUEST error                               |

## Troubleshooting

### Connection Issues:
- **WebSocket connection failed:** Verify servers are running with `docker-compose ps`
- **CORS errors:** Use same origin (localhost) for testing
- **Port blocked:** Confirm ports 8001, 8002 are accessible

### Protocol Issues:
- **No response:** Check JSON format and required fields
- **Error responses:** Validate method names and parameters
- **Timeout:** Server may be processing - wait or check logs

This WebSocket testing will validate the core MCP protocol functionality that Postman HTTP tests cannot cover!
