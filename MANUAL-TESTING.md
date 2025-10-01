# 🧪 **MANUAL TESTING GUIDE**
**Step-by-step testing without automated scripts**

## 🚀 **Prerequisites**

### 1. Install Requirements
```powershell
# Install Docker Desktop if not installed
# Download from: https://www.docker.com/products/docker-desktop/

# Install Poetry
pip install poetry

# Install Node.js & pnpm if needed
# Download Node.js from: https://nodejs.org/
npm install -g pnpm
```

### 2. Build and Start Services
```powershell
# Navigate to project root
cd c:\Users\ankita\chat-assistant

# Build all containers
docker-compose build

# Start all services
docker-compose up -d
```

### 3. Verify Services Are Running
```powershell
# Check all containers
docker-compose ps

# Should show:
# - postgres (healthy)
# - redis (healthy)
# - opensearch (healthy)
# - localstack (healthy)
# - rag-server (healthy)
# - parser-server (healthy)
# - findb-server (healthy)
```

---

## 🏥 **Step 1: Health Check All Services**

### Check Service Status
```powershell
# RAG Server Health
curl http://localhost:8001/health

# Expected Response:
# {"status": "healthy", "service": "rag-server", "timestamp": "2025-09-29T..."}

# Parser Server Health
curl http://localhost:8002/health

# Expected Response:
# {"status": "healthy", "service": "parser-server", "timestamp": "2025-09-29T..."}

# FinDB Server Health
curl http://localhost:8003/health

# Expected Response:
# {"status": "healthy", "service": "findb-server", "timestamp": "2025-09-29T..."}
```

### Check Database Connection
```powershell
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d mavikdb

# Inside PostgreSQL, run:
\dt          # List tables
SELECT COUNT(*) FROM locations;     # Should show sample data
SELECT COUNT(*) FROM properties;    # Should show sample data
\q           # Exit
```

### Check OpenSearch
```powershell
# OpenSearch Health
curl http://localhost:9200/_cluster/health

# Expected Response:
# {"cluster_name": "opensearch-cluster", "status": "yellow" or "green", ...}
```

---

## 📄 **Step 2: Test Document Parser (Manual)**

### Test 1: Simple PDF Upload
```powershell
# Create a test file (or use existing PDF)
# Save any PDF as "test-document.pdf" in current directory

# Upload via REST API
curl -X POST "http://localhost:8002/parse" -F "file=@test-document.pdf" -F "format=pdf"

# Expected Response:
# {
#   "success": true,
#   "document_id": "doc_12345",
#   "content": "Extracted text content...",
#   "metadata": {...},
#   "pages": [...],
#   "tables": [...]
# }
```

### Test 2: Check Document Processing
```powershell
# List processed documents
curl http://localhost:8002/documents

# Get specific document
curl "http://localhost:8002/documents/{document_id}"
```

### Test 3: Manual MCP WebSocket (Advanced)
```powershell
# Install wscat for WebSocket testing
npm install -g wscat

# Connect to Parser MCP
wscat -c ws://localhost:8002/mcp

# Send MCP initialization (copy/paste this JSON):
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "manual-test", "version": "1.0.0"}
  }
}

# Expected Response:
# {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", ...}}

# List available tools:
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}

# Expected Response showing available tools like parse_document
```

---

## 🔍 **Step 3: Test RAG Server (Manual)**

### Test 1: Document Upload & Indexing
```powershell
# Upload document for indexing
curl -X POST "http://localhost:8001/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a test commercial real estate offering memorandum for 300 Hillsborough Street. The property is a mixed-use development with retail and office space.",
    "metadata": {
      "title": "Test OM",
      "type": "offering_memorandum",
      "property_address": "300 Hillsborough Street"
    }
  }'

# Expected Response:
# {"document_id": "doc_xyz", "status": "indexed", "chunks": 3}
```

### Test 2: Search Documents
```powershell
# Search for content
curl -X POST "http://localhost:8001/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "commercial real estate offering memorandum",
    "limit": 5
  }'

# Expected Response:
# {
#   "results": [
#     {"document_id": "doc_xyz", "score": 0.85, "content": "...", "metadata": {...}},
#     ...
#   ]
# }
```

### Test 3: RAG MCP WebSocket
```powershell
# Connect to RAG MCP
wscat -c ws://localhost:8001/mcp

# Initialize connection (same as above)
# Then search via MCP:
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_documents",
    "arguments": {
      "query": "commercial real estate",
      "limit": 3
    }
  }
}
```

---

## 💰 **Step 4: Test Financial Database (Manual)**

### Test 1: Check Database Data
```powershell
# Connect to database
docker-compose exec postgres psql -U postgres -d mavikdb

# Check sample data:
SELECT * FROM locations LIMIT 5;
SELECT * FROM properties LIMIT 5;
SELECT * FROM financials LIMIT 5;
SELECT * FROM property_metrics LIMIT 5;

# Exit database
\q
```

### Test 2: FinDB REST API
```powershell
# Get comparable properties
curl -X POST "http://localhost:8003/comparable-properties" \
  -H "Content-Type: application/json" \
  -d '{
    "property_type": "office",
    "location": "downtown",
    "square_feet": 50000,
    "limit": 5
  }'

# Expected Response:
# {
#   "comparable_properties": [
#     {"property_id": "prop_123", "similarity_score": 0.92, "details": {...}},
#     ...
#   ]
# }
```

### Test 3: Market Analysis
```powershell
# Get market data
curl -X POST "http://localhost:8003/market-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "downtown",
    "property_type": "office",
    "analysis_type": "rent_trends"
  }'

# Expected Response:
# {
#   "market_data": {
#     "average_rent_psf": 28.50,
#     "occupancy_rate": 0.87,
#     "trends": {...}
#   }
# }
```

### Test 4: FinDB MCP WebSocket
```powershell
# Connect to FinDB MCP
wscat -c ws://localhost:8003/mcp

# Initialize, then call financial analysis:
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "analyze_comparable_properties",
    "arguments": {
      "property_type": "office",
      "square_feet": 45000,
      "location": "downtown"
    }
  }
}
```

---

## 🔗 **Step 5: End-to-End Manual Test**

### Complete Workflow Test
```powershell
# 1. Parse a document
curl -X POST "http://localhost:8002/parse" -F "file=@packages/evals/fixtures/300_Hillsborough_OM.pdf" -F "format=pdf"
# Note the document_id from response

# 2. Index the parsed content in RAG
curl -X POST "http://localhost:8001/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "[paste extracted text from step 1]",
    "metadata": {"title": "300 Hillsborough OM", "type": "offering_memorandum"}
  }'

# 3. Search for the document
curl -X POST "http://localhost:8001/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hillsborough commercial property", "limit": 3}'

# 4. Get comparable properties
curl -X POST "http://localhost:8003/comparable-properties" \
  -H "Content-Type: application/json" \
  -d '{
    "property_type": "office",
    "location": "downtown",
    "square_feet": 50000
  }'

# 5. Verify all responses are successful and contain expected data
```

---

## 🛠️ **Troubleshooting Manual Steps**

### Services Not Starting
```powershell
# Check logs for specific service
docker-compose logs rag-server
docker-compose logs parser-server
docker-compose logs findb-server
docker-compose logs postgres

# Restart specific service
docker-compose restart rag-server

# Rebuild and restart
docker-compose down
docker-compose build rag-server
docker-compose up -d
```

### Database Issues
```powershell
# Reset database with fresh data
docker-compose down postgres
docker volume rm chat-assistant_postgres_data
docker-compose up -d postgres

# Wait for database to initialize, then check
docker-compose logs postgres
```

### Network/Connection Issues
```powershell
# Check network
docker network ls
docker network inspect chat-assistant_default

# Test internal connectivity
docker-compose exec rag-server ping postgres
docker-compose exec findb-server curl http://opensearch:9200
```

---

## ✅ **Success Indicators**

### All Tests Pass If:
- ✅ All health endpoints return 200 OK
- ✅ Database contains sample data (locations, properties, etc.)
- ✅ Document parsing extracts text and metadata
- ✅ RAG indexing and search return relevant results
- ✅ FinDB returns comparable properties and market data
- ✅ MCP WebSocket connections establish successfully
- ✅ End-to-end workflow completes without errors

### Performance Benchmarks:
- **RAG responses**: < 800ms
- **Parser processing**: < 30s for typical documents
- **FinDB queries**: < 200ms
- **Search results**: Relevant and properly scored

---

## 🎯 **What Each Test Validates**

| Component       | Manual Test              | Validates              |
| --------------- | ------------------------ | ---------------------- |
| **Docker**      | `docker-compose ps`      | All services running   |
| **Health**      | `curl /health` endpoints | Service availability   |
| **Database**    | PostgreSQL queries       | Data persistence       |
| **Parser**      | PDF upload via API       | Document processing    |
| **RAG**         | Document indexing/search | Vector search          |
| **FinDB**       | Property analysis API    | Financial calculations |
| **MCP**         | WebSocket connections    | Tool protocol          |
| **Integration** | End-to-end workflow      | Complete system        |

**This manual approach gives you complete control and visibility into each step!** 🚀
