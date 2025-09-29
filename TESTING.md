# 🧪 Mavik AI Testing Guide

## Quick Start - How to Test Everything

### 1. 🚀 Setup Environment (First Time)

```powershell
# Windows PowerShell
.\scripts\setup-dev-environment.ps1

# Or bash
chmod +x scripts/setup-dev-environment.sh
./scripts/setup-dev-environment.sh
```

### 2. 🐳 Start All Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check service status  
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. ⚡ Quick Health Check

```bash
# Check all server health endpoints
curl http://localhost:8001/health  # RAG Server
curl http://localhost:8002/health  # Parser Server  
curl http://localhost:8003/health  # FinDB Server
```

Expected responses:
- **RAG Server**: `{"status": "healthy", "opensearch_connected": true}`
- **Parser Server**: `{"status": "healthy", "textract_available": true, "s3_connected": true}`
- **FinDB Server**: `{"status": "healthy", "database_connected": true, "data_freshness": "good"}`

### 4. 🔬 Run Individual Server Tests

```bash
# Test each server individually
python scripts/test-rag-server.py      # RAG functionality
python scripts/test-parser-server.py   # Document parsing
python scripts/test-findb-server.py    # Financial analysis
```

### 5. 🎯 Complete Integration Test

```bash
# Run comprehensive end-to-end test
python scripts/test-integration.py
```

## 📋 Manual Testing Scenarios

### Scenario 1: Document Processing Pipeline

1. **Upload Document** (Parser Server)
```bash
curl -X POST http://localhost:8002/api/upload \
  -F "file=@packages/evals/fixtures/300_Hillsborough_OM.pdf" \
  -F "document_type=offering_memorandum"
```

2. **Index for Search** (RAG Server)
```bash
curl -X POST http://localhost:8001/api/upload \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Parsed document content here...",
    "filename": "hillsborough_om.txt",
    "document_type": "offering_memorandum"
  }'
```

3. **Search Documents** (RAG Server)
```bash
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "investment opportunity cap rate",
    "limit": 5
  }'
```

### Scenario 2: Financial Analysis

1. **Get Market Data** (FinDB Server)
```bash
curl -X POST http://localhost:8003/api/market-data \
  -H "Content-Type: application/json" \
  -d '{
    "property_type": "office",
    "city": "New York",
    "state": "NY", 
    "start_date": "2023-01-01T00:00:00",
    "end_date": "2023-12-31T23:59:59"
  }'
```

2. **Find Comparable Properties** (FinDB Server)
```bash
curl -X POST http://localhost:8003/api/comparable-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "prop_001",
    "radius_miles": 5.0,
    "max_results": 5
  }'
```

3. **Property Valuation** (FinDB Server)
```bash
curl -X POST http://localhost:8003/api/property-valuation \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "prop_001",
    "market_cap_rate": 0.065
  }'
```

### Scenario 3: WebSocket MCP Protocol

Use a WebSocket client or this Node.js script:

```javascript
// test-websocket.js
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8001/mcp');

ws.on('open', function open() {
  // Send MCP request
  const request = {
    jsonrpc: "2.0",
    id: "test_001",
    method: "search_documents",
    params: {
      query: "office building investment",
      limit: 3
    }
  };
  
  ws.send(JSON.stringify(request));
});

ws.on('message', function message(data) {
  const response = JSON.parse(data);
  console.log('MCP Response:', JSON.stringify(response, null, 2));
  ws.close();
});
```

## 🔍 Monitoring and Debugging

### View Service Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f rag-server
docker-compose logs -f parser-server
docker-compose logs -f findb-server
```

### Database Inspection
```bash
# Connect to PostgreSQL
docker exec -it mavik-postgres psql -U findb_user -d findb_test

# Check sample data
SELECT COUNT(*) FROM properties;
SELECT COUNT(*) FROM financials;
SELECT property_type, COUNT(*) FROM properties GROUP BY property_type;
```

### OpenSearch Inspection
```bash
# Check indices
curl http://localhost:9200/_cat/indices

# Check document count
curl http://localhost:9200/documents/_count

# Search test
curl -X GET "http://localhost:9200/documents/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match_all": {}}, "size": 1}'
```

## 🚨 Troubleshooting

### Common Issues

1. **Services Won't Start**
   - Check Docker is running: `docker info`
   - Check ports aren't in use: `netstat -an | grep :8001`
   - Restart Docker Compose: `docker-compose down && docker-compose up -d`

2. **Database Connection Errors**
   - Check PostgreSQL is ready: `docker-compose logs postgres`
   - Verify database initialization: `docker exec -it mavik-postgres psql -U findb_user -d findb_test -c "SELECT COUNT(*) FROM properties;"`

3. **OpenSearch Issues**
   - Check cluster health: `curl http://localhost:9200/_cluster/health`
   - Check available memory: `docker stats mavik-opensearch`

4. **Permission Errors**
   - On Windows: Run PowerShell as Administrator
   - On Linux/Mac: Check file permissions with `ls -la`

### Service URLs
- **RAG Server**: http://localhost:8001
  - Health: `/health`
  - Docs: `/docs`
  - WebSocket: `ws://localhost:8001/mcp`

- **Parser Server**: http://localhost:8002  
  - Health: `/health`
  - Docs: `/docs`
  - WebSocket: `ws://localhost:8002/mcp`

- **FinDB Server**: http://localhost:8003
  - Health: `/health` 
  - Docs: `/docs`
  - WebSocket: `ws://localhost:8003/mcp`

- **Supporting Services**:
  - PostgreSQL: `localhost:5432`
  - OpenSearch: `localhost:9200`
  - Redis: `localhost:6379`
  - LocalStack: `localhost:4566`

## ✅ Success Criteria

Your system is working correctly when:

1. ✅ All health endpoints return `{"status": "healthy"}`
2. ✅ Document upload and parsing works
3. ✅ Financial analysis returns realistic data
4. ✅ Search functionality finds relevant documents
5. ✅ WebSocket MCP protocol responds correctly
6. ✅ Database contains sample property data
7. ✅ OpenSearch has indexed documents
8. ✅ Integration test script passes all checks

## 📊 Performance Expectations

- **Health checks**: < 100ms response time
- **Document parsing**: < 5s for typical PDFs
- **Search queries**: < 500ms for simple queries
- **Financial analysis**: < 1s for comparable properties
- **Database queries**: < 200ms for typical queries

## 🎯 Next Steps

Once all tests pass:
1. Deploy to AWS using CDK: `cd infra/cdk && npm run deploy`
2. Test with real estate documents
3. Configure production monitoring
4. Set up CI/CD pipeline
5. Scale services based on usage