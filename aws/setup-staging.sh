#!/bin/bash

# Configuration
AWS_REGION="us-east-2"
CLUSTER_NAME="mavik-ai-cluster"
VPC_ID="vpc-0fcb4fab23af94b3f"
SUBNET1="subnet-0a40aee8d766d2f3f"
SUBNET2="subnet-07c1f3bb40f068f94"
SECURITY_GROUP="sg-00906fb1a879e5cc6"

# ECR Repositories
BACKEND_REPO="mavik-backend-staging"
FRONTEND_REPO="mavik-frontend-staging"

# Environment variables
COGNITO_USER_POOL_ID="us-east-2_fuVW3us9r"
COGNITO_CLIENT_ID="2p0o0a78q99dbd1rj9k5dg3r1j"

echo "🚀 Setting up staging environment..."

# Create ECR repositories if they don't exist
echo "📦 Creating ECR repositories..."
aws ecr describe-repositories --repository-names $BACKEND_REPO --region $AWS_REGION 2>/dev/null || \
  aws ecr create-repository --repository-name $BACKEND_REPO --region $AWS_REGION

aws ecr describe-repositories --repository-names $FRONTEND_REPO --region $AWS_REGION 2>/dev/null || \
  aws ecr create-repository --repository-name $FRONTEND_REPO --region $AWS_REGION

# Create Target Groups
echo "🎯 Creating target groups..."
BACKEND_TG_ARN=$(aws elbv2 create-target-group \
  --name mavik-backend-staging-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --region $AWS_REGION \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text 2>/dev/null || aws elbv2 describe-target-groups --names mavik-backend-staging-tg --region $AWS_REGION --query 'TargetGroups[0].TargetGroupArn' --output text)

FRONTEND_TG_ARN=$(aws elbv2 create-target-group \
  --name mavik-frontend-staging-tg \
  --protocol HTTP \
  --port 3000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path / \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200,307 \
  --region $AWS_REGION \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text 2>/dev/null || aws elbv2 describe-target-groups --names mavik-frontend-staging-tg --region $AWS_REGION --query 'TargetGroups[0].TargetGroupArn' --output text)

echo "Backend Target Group: $BACKEND_TG_ARN"
echo "Frontend Target Group: $FRONTEND_TG_ARN"

# Get ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names mavik-ai-alb --region $AWS_REGION --query 'LoadBalancers[0].LoadBalancerArn' --output text)
echo "ALB ARN: $ALB_ARN"

# Create listener rules for staging (using different host headers)
echo "🔗 Creating ALB listener rules..."
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --region $AWS_REGION --query 'Listeners[?Port==`443`].ListenerArn' --output text)

# Create rule for staging frontend (staging.ai.mavik-ssot.com)
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 10 \
  --conditions Field=host-header,Values=staging.ai.mavik-ssot.com \
  --actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN \
  --region $AWS_REGION 2>/dev/null || echo "Frontend staging rule already exists"

# Create rule for staging backend (staging.ai.mavik-ssot.com/api/*)
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 11 \
  --conditions Field=host-header,Values=staging.ai.mavik-ssot.com Field=path-pattern,Values=/api/* \
  --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN \
  --region $AWS_REGION 2>/dev/null || echo "Backend staging rule already exists"

# Register backend task definition
echo "📝 Registering backend task definition..."
cat > /tmp/backend-staging-task.json <<EOF
{
  "family": "mavik-backend-staging",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "3072",
  "executionRoleArn": "arn:aws:iam::905418431067:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::905418431067:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "905418431067.dkr.ecr.us-east-2.amazonaws.com/mavik-backend-staging:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "staging"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mavik-backend-staging",
          "awslogs-region": "us-east-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition --cli-input-json file:///tmp/backend-staging-task.json --region $AWS_REGION

# Register frontend task definition
echo "📝 Registering frontend task definition..."
cat > /tmp/frontend-staging-task.json <<EOF
{
  "family": "mavik-frontend-staging",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::905418431067:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::905418431067:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "905418431067.dkr.ecr.us-east-2.amazonaws.com/mavik-frontend-staging:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "NEXT_PUBLIC_API_URL",
          "value": "https://staging.ai.mavik-ssot.com/api/chat"
        },
        {
          "name": "NEXT_PUBLIC_COGNITO_USER_POOL_ID",
          "value": "$COGNITO_USER_POOL_ID"
        },
        {
          "name": "NEXT_PUBLIC_COGNITO_CLIENT_ID",
          "value": "$COGNITO_CLIENT_ID"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mavik-frontend-staging",
          "awslogs-region": "us-east-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition --cli-input-json file:///tmp/frontend-staging-task.json --region $AWS_REGION

# Create CloudWatch log groups
echo "📊 Creating CloudWatch log groups..."
aws logs create-log-group --log-group-name /ecs/mavik-backend-staging --region $AWS_REGION 2>/dev/null || echo "Backend log group exists"
aws logs create-log-group --log-group-name /ecs/mavik-frontend-staging --region $AWS_REGION 2>/dev/null || echo "Frontend log group exists"

# Create ECS services
echo "🚀 Creating ECS services..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name mavik-backend-staging-service \
  --task-definition mavik-backend-staging \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$BACKEND_TG_ARN,containerName=backend,containerPort=8000" \
  --region $AWS_REGION 2>/dev/null || echo "Backend service already exists"

aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name mavik-frontend-staging-service \
  --task-definition mavik-frontend-staging \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$FRONTEND_TG_ARN,containerName=frontend,containerPort=3000" \
  --region $AWS_REGION 2>/dev/null || echo "Frontend service already exists"

echo "✅ Staging environment setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Update Route53 to point staging.ai.mavik-ssot.com to the ALB"
echo "2. Trigger a deployment with: git push origin feat/tavily-web-search"
echo "3. Access staging at: https://staging.ai.mavik-ssot.com"
