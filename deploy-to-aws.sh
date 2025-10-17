#!/bin/bash
# AWS ECS Deployment Script for Mavik AI Chat Assistant
# Account: mavik-amtech (167067248318)

set -e

# Configuration
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="167067248318"
CLUSTER_NAME="mavik-ai-cluster"
ECR_BACKEND="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/backend"
ECR_FRONTEND="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/frontend"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Mavik AI - AWS ECS Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install it first.${NC}"
    exit 1
fi

# Verify AWS credentials
echo -e "${YELLOW}1. Verifying AWS credentials...${NC}"
if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    if [ "$ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
        echo -e "${RED}✗ Wrong AWS account. Expected: $AWS_ACCOUNT_ID, Got: $ACCOUNT${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ AWS credentials verified (Account: $ACCOUNT)${NC}"
else
    echo -e "${RED}✗ AWS credentials not configured${NC}"
    exit 1
fi

# Login to ECR
echo -e "${YELLOW}2. Logging in to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo -e "${GREEN}✓ ECR login successful${NC}"

# Build and push backend
echo -e "${YELLOW}3. Building backend image...${NC}"
cd backend
docker build -t mavik-ai/backend -f Dockerfile . --no-cache
echo -e "${GREEN}✓ Backend image built${NC}"

echo -e "${YELLOW}4. Pushing backend image to ECR...${NC}"
docker tag mavik-ai/backend:latest $ECR_BACKEND:latest
docker tag mavik-ai/backend:latest $ECR_BACKEND:$(date +%Y%m%d-%H%M%S)
docker push $ECR_BACKEND:latest
docker push $ECR_BACKEND:$(date +%Y%m%d-%H%M%S)
echo -e "${GREEN}✓ Backend image pushed${NC}"

# Build and push frontend
echo -e "${YELLOW}5. Building frontend image...${NC}"
cd ../frontend
docker build -t mavik-ai/frontend -f Dockerfile.prod . --no-cache
echo -e "${GREEN}✓ Frontend image built${NC}"

echo -e "${YELLOW}6. Pushing frontend image to ECR...${NC}"
docker tag mavik-ai/frontend:latest $ECR_FRONTEND:latest
docker tag mavik-ai/frontend:latest $ECR_FRONTEND:$(date +%Y%m%d-%H%M%S)
docker push $ECR_FRONTEND:latest
docker push $ECR_FRONTEND:$(date +%Y%m%d-%H%M%S)
echo -e "${GREEN}✓ Frontend image pushed${NC}"

# Update ECS services
echo -e "${YELLOW}7. Updating backend service...${NC}"
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service mavik-ai-backend-service \
  --force-new-deployment \
  --region $AWS_REGION > /dev/null

echo -e "${GREEN}✓ Backend service updated${NC}"

echo -e "${YELLOW}8. Updating frontend service...${NC}"
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service mavik-ai-frontend-service \
  --force-new-deployment \
  --region $AWS_REGION > /dev/null

echo -e "${GREEN}✓ Frontend service updated${NC}"

# Wait for deployment
echo -e "${YELLOW}9. Waiting for services to stabilize...${NC}"
echo "   This may take 2-3 minutes..."

aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services mavik-ai-backend-service mavik-ai-frontend-service \
  --region $AWS_REGION

echo -e "${GREEN}✓ Services are stable${NC}"

# Check service status
echo -e "${YELLOW}10. Checking service health...${NC}"
BACKEND_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services mavik-ai-backend-service --region $AWS_REGION --query 'services[0].deployments[0].rolloutState' --output text)
FRONTEND_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services mavik-ai-frontend-service --region $AWS_REGION --query 'services[0].deployments[0].rolloutState' --output text)

echo "   Backend: $BACKEND_STATUS"
echo "   Frontend: $FRONTEND_STATUS"

# Display task info
echo ""
echo -e "${YELLOW}11. Running tasks:${NC}"
aws ecs list-tasks --cluster $CLUSTER_NAME --region $AWS_REGION --query 'taskArns' --output table

# Show recent logs
echo ""
echo -e "${YELLOW}12. Recent backend logs (last 20 lines):${NC}"
aws logs tail /ecs/mavik-ai-backend --since 5m --region $AWS_REGION | tail -n 20 || echo "No logs available yet"

# Success message
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   ✅ Deployment Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 Your application should be available at:${NC}"
echo -e "${GREEN}   https://ai.mavik-ssot.com${NC}"
echo ""
echo -e "${YELLOW}📊 Monitor deployment:${NC}"
echo "   AWS Console: https://console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters/$CLUSTER_NAME"
echo ""
echo -e "${YELLOW}📝 View logs:${NC}"
echo "   aws logs tail /ecs/mavik-ai-backend --follow --region $AWS_REGION"
echo "   aws logs tail /ecs/mavik-ai-frontend --follow --region $AWS_REGION"
echo ""

# Cleanup old images (optional)
read -p "Do you want to cleanup old Docker images locally? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🧹 Cleaning up old images...${NC}"
    docker system prune -f
    echo -e "${GREEN}✓ Cleanup complete${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment finished successfully!${NC}"
