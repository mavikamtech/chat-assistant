#!/bin/bash
# Monitoring script for mavik-ssot.com
# Run this to check the health of your application

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_DIR="/home/ubuntu/chat-assistant"
COMPOSE_FILE="docker-compose.prod.yml"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}    Mavik AI Health Check Monitor${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if containers are running
echo -e "${YELLOW}1. Container Status:${NC}"
cd $APP_DIR
docker-compose -f $COMPOSE_FILE ps
echo ""

# Check backend health
echo -e "${YELLOW}2. Backend Health:${NC}"
if curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
    curl -s http://localhost:8000/health | jq '.' || echo ""
else
    echo -e "${RED}✗ Backend is not responding${NC}"
fi
echo ""

# Check frontend
echo -e "${YELLOW}3. Frontend Health:${NC}"
if curl -sf http://localhost:3000 > /dev/null; then
    echo -e "${GREEN}✓ Frontend is healthy${NC}"
else
    echo -e "${RED}✗ Frontend is not responding${NC}"
fi
echo ""

# Check OpenSearch
echo -e "${YELLOW}4. OpenSearch Health:${NC}"
if curl -sf http://localhost:9200/_cluster/health > /dev/null; then
    echo -e "${GREEN}✓ OpenSearch is healthy${NC}"
    curl -s http://localhost:9200/_cluster/health | jq '.' || echo ""
else
    echo -e "${RED}✗ OpenSearch is not responding${NC}"
fi
echo ""

# Check HTTPS endpoint
echo -e "${YELLOW}5. Public Endpoint (HTTPS):${NC}"
if curl -sf https://mavik-ssot.com/health > /dev/null; then
    echo -e "${GREEN}✓ Public endpoint is accessible${NC}"
else
    echo -e "${RED}✗ Public endpoint is not accessible${NC}"
fi
echo ""

# Disk usage
echo -e "${YELLOW}6. Disk Usage:${NC}"
df -h / | tail -n 1 | awk '{print "  Used: " $3 " / " $2 " (" $5 ")"}'
echo ""

# Memory usage
echo -e "${YELLOW}7. Memory Usage:${NC}"
free -h | grep Mem | awk '{print "  Used: " $3 " / " $2}'
echo ""

# Docker stats (CPU, Memory)
echo -e "${YELLOW}8. Container Resource Usage:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
echo ""

# Recent errors in logs
echo -e "${YELLOW}9. Recent Errors (last 20 lines):${NC}"
echo -e "${YELLOW}   Backend:${NC}"
docker-compose -f $COMPOSE_FILE logs backend --tail=100 | grep -i "error" | tail -n 5 || echo "  No errors found"
echo ""
echo -e "${YELLOW}   Frontend:${NC}"
docker-compose -f $COMPOSE_FILE logs frontend --tail=100 | grep -i "error" | tail -n 5 || echo "  No errors found"
echo ""

# SSL certificate expiry
echo -e "${YELLOW}10. SSL Certificate:${NC}"
if command -v openssl &> /dev/null; then
    EXPIRY=$(echo | openssl s_client -servername mavik-ssot.com -connect mavik-ssot.com:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
    echo "  Expires: $EXPIRY"
else
    echo "  (openssl not installed, skipping check)"
fi
echo ""

# Uptime
echo -e "${YELLOW}11. System Uptime:${NC}"
uptime -p
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Health check complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
