# AWS Deployment Guide - Integrating with Existing Infrastructure

## Overview

This guide shows how to deploy the Mavik AI Chat Assistant to your existing AWS infrastructure at **mavik-ssot.com** using:
- AWS Route 53 (existing)
- Application Load Balancer (existing)
- AWS ECS/Fargate (new - for your app)
- AWS ECR (for Docker images)

**Account**: mavik-amtech (167067248318)

---

## Architecture

```
Route 53 (mavik-ssot.com)
    ↓
Application Load Balancer
    ↓
    ├─→ Paul's GQL API (existing)
    │   Path: /graphql or default
    │
    └─→ Your Chat Assistant (new)
        Path: /ai/* or subdomain: ai.mavik-ssot.com
        ↓
        ECS Fargate Service
        ├─→ Frontend Task (Next.js)
        └─→ Backend Task (FastAPI)
```

---

## Deployment Options

### Option 1: Subdomain (Recommended)
- **URL**: `https://ai.mavik-ssot.com`
- **Clean separation** from Paul's API
- **Easiest to manage**

### Option 2: Path-based Routing
- **URL**: `https://mavik-ssot.com/ai`
- **Shares same domain** with Paul's API
- **Requires ALB path configuration**

---

## Prerequisites

- [ ] AWS CLI installed and configured
- [ ] Docker installed locally
- [ ] Access to AWS account: mavik-amtech (167067248318)
- [ ] IAM permissions for: ECS, ECR, Route53, ALB, Bedrock, S3
- [ ] S3 buckets created: `mavik-uploads`, `mavik-reports`

---

## Step 1: Setup AWS ECR Repositories

Create repositories for your Docker images:

```bash
# Login to AWS
aws configure
# Enter credentials for mavik-amtech account

# Set variables
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="167067248318"

# Create ECR repositories
aws ecr create-repository --repository-name mavik-ai/backend --region $AWS_REGION
aws ecr create-repository --repository-name mavik-ai/frontend --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

---

## Step 2: Build and Push Docker Images

```bash
cd /path/to/chat-assistant

# Build and push backend
cd backend
docker build -t mavik-ai/backend -f Dockerfile .
docker tag mavik-ai/backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/backend:latest

# Build and push frontend
cd ../frontend
docker build -t mavik-ai/frontend -f Dockerfile.prod .
docker tag mavik-ai/frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/frontend:latest
```

---

## Step 3: Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
  --cluster-name mavik-ai-cluster \
  --region $AWS_REGION

# Verify
aws ecs list-clusters --region $AWS_REGION
```

---

## Step 4: Create IAM Execution Role

This role allows ECS tasks to pull images and write logs.

```bash
# Create trust policy
cat > ecs-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-trust-policy.json

# Attach AWS managed policies
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

---

## Step 5: Create Task Definitions

### Backend Task Definition

Create `backend-task-def.json`:

```json
{
  "family": "mavik-ai-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::167067248318:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::167067248318:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "167067248318.dkr.ecr.us-east-1.amazonaws.com/mavik-ai/backend:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        },
        {
          "name": "S3_BUCKET_UPLOADS",
          "value": "mavik-uploads"
        },
        {
          "name": "S3_BUCKET_REPORTS",
          "value": "mavik-reports"
        },
        {
          "name": "BEDROCK_MODEL_ID",
          "value": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        },
        {
          "name": "BEDROCK_MODEL_ID_HAIKU",
          "value": "us.anthropic.claude-3-5-haiku-20241022-v1:0"
        }
      ],
      "secrets": [
        {
          "name": "AWS_ACCESS_KEY_ID",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:167067248318:secret:mavik-ai/aws-credentials:AWS_ACCESS_KEY_ID::"
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:167067248318:secret:mavik-ai/aws-credentials:AWS_SECRET_ACCESS_KEY::"
        },
        {
          "name": "TAVILY_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:167067248318:secret:mavik-ai/api-keys:TAVILY_API_KEY::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mavik-ai-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Frontend Task Definition

Create `frontend-task-def.json`:

```json
{
  "family": "mavik-ai-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::167067248318:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "167067248318.dkr.ecr.us-east-1.amazonaws.com/mavik-ai/frontend:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NODE_ENV",
          "value": "production"
        },
        {
          "name": "NEXT_PUBLIC_BACKEND_URL",
          "value": "https://ai.mavik-ssot.com/api"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mavik-ai-frontend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:3000 || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Register task definitions:

```bash
# Create CloudWatch log groups
aws logs create-log-group --log-group-name /ecs/mavik-ai-backend --region $AWS_REGION
aws logs create-log-group --log-group-name /ecs/mavik-ai-frontend --region $AWS_REGION

# Register task definitions
aws ecs register-task-definition --cli-input-json file://backend-task-def.json --region $AWS_REGION
aws ecs register-task-definition --cli-input-json file://frontend-task-def.json --region $AWS_REGION
```

---

## Step 6: Store Secrets in AWS Secrets Manager

```bash
# Create secrets
aws secretsmanager create-secret \
  --name mavik-ai/aws-credentials \
  --secret-string '{"AWS_ACCESS_KEY_ID":"AKIA...","AWS_SECRET_ACCESS_KEY":"..."}' \
  --region $AWS_REGION

aws secretsmanager create-secret \
  --name mavik-ai/api-keys \
  --secret-string '{"TAVILY_API_KEY":"tvly-..."}' \
  --region $AWS_REGION
```

---

## Step 7: Configure Application Load Balancer

### Option A: Subdomain (Recommended)

Ask Paul or your DevOps team to:

1. **Create Target Groups**:
   - Name: `mavik-ai-frontend-tg`
   - Target type: IP
   - Protocol: HTTP
   - Port: 3000
   - Health check path: `/`

   - Name: `mavik-ai-backend-tg`
   - Target type: IP
   - Protocol: HTTP
   - Port: 8000
   - Health check path: `/health`

2. **Add Listener Rule** (HTTPS:443):
   - **Condition**: Host header = `ai.mavik-ssot.com`
   - **Action**: Forward to `mavik-ai-frontend-tg`

   - **Condition**: Host header = `ai.mavik-ssot.com` AND Path = `/api/*`
   - **Action**: Forward to `mavik-ai-backend-tg`

3. **Configure Route 53**:
   - Add A record (Alias): `ai.mavik-ssot.com` → ALB

### Option B: Path-based Routing

Add listener rules:
- **Condition**: Path = `/ai/*`
- **Action**: Forward to `mavik-ai-frontend-tg`

- **Condition**: Path = `/ai/api/*`
- **Action**: Forward to `mavik-ai-backend-tg`

---

## Step 8: Create ECS Services

```bash
# Get VPC and subnet info (use Paul's existing VPC)
VPC_ID="vpc-xxxxxx"  # Ask Paul for VPC ID
SUBNET_1="subnet-xxxxx"  # Private subnet 1
SUBNET_2="subnet-xxxxx"  # Private subnet 2
SECURITY_GROUP="sg-xxxxx"  # Security group with port 8000, 3000

# Create backend service
aws ecs create-service \
  --cluster mavik-ai-cluster \
  --service-name mavik-ai-backend-service \
  --task-definition mavik-ai-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:167067248318:targetgroup/mavik-ai-backend-tg/xxxxx,containerName=backend,containerPort=8000" \
  --region $AWS_REGION

# Create frontend service
aws ecs create-service \
  --cluster mavik-ai-cluster \
  --service-name mavik-ai-frontend-service \
  --task-definition mavik-ai-frontend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:167067248318:targetgroup/mavik-ai-frontend-tg/xxxxx,containerName=frontend,containerPort=3000" \
  --region $AWS_REGION
```

---

## Step 9: Verify Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster mavik-ai-cluster \
  --services mavik-ai-backend-service mavik-ai-frontend-service \
  --region $AWS_REGION

# Check tasks
aws ecs list-tasks \
  --cluster mavik-ai-cluster \
  --region $AWS_REGION

# View logs
aws logs tail /ecs/mavik-ai-backend --follow --region $AWS_REGION
aws logs tail /ecs/mavik-ai-frontend --follow --region $AWS_REGION
```

Visit: `https://ai.mavik-ssot.com`

---

## Deployment Automation Script

Create `deploy-to-aws.sh`:

```bash
#!/bin/bash
set -e

AWS_REGION="us-east-1"
AWS_ACCOUNT_ID="167067248318"
ECR_BACKEND="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/backend"
ECR_FRONTEND="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mavik-ai/frontend"

echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "🏗️ Building backend..."
cd backend
docker build -t mavik-ai/backend -f Dockerfile .
docker tag mavik-ai/backend:latest $ECR_BACKEND:latest
docker push $ECR_BACKEND:latest

echo "🏗️ Building frontend..."
cd ../frontend
docker build -t mavik-ai/frontend -f Dockerfile.prod .
docker tag mavik-ai/frontend:latest $ECR_FRONTEND:latest
docker push $ECR_FRONTEND:latest

echo "🔄 Updating ECS services..."
aws ecs update-service --cluster mavik-ai-cluster --service mavik-ai-backend-service --force-new-deployment --region $AWS_REGION
aws ecs update-service --cluster mavik-ai-cluster --service mavik-ai-frontend-service --force-new-deployment --region $AWS_REGION

echo "✅ Deployment complete!"
echo "🌐 Your app: https://ai.mavik-ssot.com"
```

---

## Coordination with Paul

### Information to Request from Paul:

1. **VPC Configuration**:
   - VPC ID
   - Private subnet IDs (2 for availability)
   - Security group ID (or create new one)

2. **Load Balancer Details**:
   - ALB ARN
   - Listener ARN (HTTPS:443)
   - Certificate ARN (for SSL)

3. **Route 53**:
   - Hosted Zone ID for mavik-ssot.com
   - Permission to create subdomain record

4. **Existing Infrastructure**:
   - Which paths are used by GQL API
   - Any rate limiting or WAF rules

### What You'll Add:

- ECS Cluster: `mavik-ai-cluster`
- ECS Services: `mavik-ai-backend-service`, `mavik-ai-frontend-service`
- Target Groups: `mavik-ai-backend-tg`, `mavik-ai-frontend-tg`
- Route 53 Record: `ai.mavik-ssot.com`

---

## Cost Estimation

**Monthly AWS Costs:**
- ECS Fargate (2 tasks, small): ~$30-40
- Application Load Balancer: ~$20 (shared with Paul)
- S3 Storage: ~$5
- Bedrock (Claude): Pay per use (~$10-20)
- Data Transfer: ~$5-10
- **Total**: ~$70-95/month

---

## Auto-Scaling Configuration (Optional)

```bash
# Create auto-scaling target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/mavik-ai-cluster/mavik-ai-backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 4

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/mavik-ai-cluster/mavik-ai-backend-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

---

## Monitoring & Alerts

Set up CloudWatch alarms:

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name mavik-ai-backend-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## Next Steps

1. **Coordinate with Paul** - Get VPC, ALB, and Route 53 details
2. **Setup ECR** - Create repositories
3. **Push Images** - Build and push Docker images
4. **Create Resources** - Task definitions, services
5. **Configure ALB** - Add target groups and rules
6. **Test** - Verify at `https://ai.mavik-ssot.com`

---

## Support

**Questions for Paul:**
- Can you share the VPC ID and subnet IDs?
- Can I create a subdomain `ai.mavik-ssot.com` in Route 53?
- Should I use the existing ALB or create a new one?
- Are there any security group requirements?

**AWS Documentation:**
- [ECS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [Route 53](https://docs.aws.amazon.com/route53/)
