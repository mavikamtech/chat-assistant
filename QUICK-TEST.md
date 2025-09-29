# Quick Test Commands

## 🚀 Quick Start
```bash
# Setup environment
./scripts/setup-dev-environment.sh   # Linux/Mac
# OR
./scripts/setup-dev-environment.ps1  # Windows

# Start all services
docker-compose up -d

# Run all tests
python scripts/run-all-tests.py
```

## 📋 Individual Tests

### Infrastructure
```bash
python scripts/test-infrastructure.py
```

### MCP Servers
```bash
python scripts/test-rag-server.py      # Document search & retrieval
python scripts/test-parser-server.py   # Document parsing 
python scripts/test-findb-server.py    # Financial database
```

### Integration
```bash
python scripts/test-integration.py     # End-to-end workflows
```

## 🔍 Service Health Checks

### Quick Status
```bash
docker-compose ps                       # Service status
curl http://localhost:8001/health      # RAG server
curl http://localhost:8002/health      # Parser server  
curl http://localhost:8003/health      # FinDB server
```

### Service Logs
```bash
docker-compose logs rag-server          # RAG logs
docker-compose logs parser-server       # Parser logs
docker-compose logs findb-server        # FinDB logs
docker-compose logs postgres            # Database logs
```

## 🎯 Test Scenarios

### Document Processing
1. Upload PDF: `POST http://localhost:8002/parse` 
2. Index document: `WebSocket ws://localhost:8001/mcp`
3. Search content: `WebSocket ws://localhost:8001/mcp`

### Financial Analysis  
1. Get comparable properties: `WebSocket ws://localhost:8003/mcp`
2. Calculate valuation: `WebSocket ws://localhost:8003/mcp`
3. Market analysis: `WebSocket ws://localhost:8003/mcp`

### End-to-End
1. Parse OM document
2. Extract financial data
3. Find comparable properties
4. Generate valuation report

## ⚡ Performance Targets

| Service | Response Time | Throughput |
|---------|---------------|------------|
| RAG     | < 800ms       | 10 req/s   |
| Parser  | < 30s         | 2 req/s    |
| FinDB   | < 200ms       | 50 req/s   |

## 🛠️ Troubleshooting

### Services Won't Start
```bash
docker-compose down
docker-compose up -d --build
```

### Database Issues
```bash
docker-compose exec postgres psql -U postgres -d mavikdb -c "\dt"
```

### Network Issues
```bash
docker network ls
docker network inspect chat-assistant_default
```

### Reset Everything
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d    # Fresh start
```

## 📊 Success Indicators

✅ All containers running (`docker-compose ps`)  
✅ Health endpoints responding (200 OK)  
✅ Database tables created and populated  
✅ MCP WebSocket connections successful  
✅ Document parsing completes without errors  
✅ Search returns relevant results  
✅ Financial calculations produce expected values  

## 🎉 Next Steps

Once all tests pass:
1. **Build Web MCP Server** - Search & scraping capabilities
2. **Add Calculator MCP Server** - Advanced financial modeling  
3. **Create Report Lambda** - PDF generation
4. **Deploy LangGraph Orchestrator** - Multi-agent coordination
5. **Update Infrastructure** - Production deployment

---
*For detailed testing procedures, see [TESTING.md](TESTING.md)*