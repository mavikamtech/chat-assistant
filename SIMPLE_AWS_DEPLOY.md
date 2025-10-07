# Simple AWS Deployment Guide - Deploy on Your Own

Since you have AWS credentials for the **mavik-amtech** account and the domain **mavik-ssot.com** is already configured, you can deploy independently using ECS Fargate.

## 🎯 Strategy: Deploy to Subdomain Independently

**Your app**: `https://ai.mavik-ssot.com`
**Paul's API**: `https://mavik-ssot.com` (won't be affected)

---

## Quick Deployment Steps

### Prerequisites
- ✅ AWS credentials (you have these)
- ✅ Domain registered: mavik-ssot.com (Paul already did this)
- ✅ Docker installed on your machine
- ✅ AWS CLI installed

---

## Step 1: Configure AWS CLI

```bash
aws configure
```

Enter your credentials:
- AWS Access Key ID: `[Your key from mavik-amtech account]`
- AWS Secret Access Key: `[Your secret]`
- Default region: `us-east-1`
- Output format: `json`

Verify:
```bash
aws sts get-caller-identity
# Should show Account: 167067248318
```

---

## Step 2: Create S3 Buckets (if not exists)

```bash
# Check if buckets exist
aws s3 ls | grep mavik

# Create buckets if needed
aws s3 mb s3://mavik-uploads --region us-east-1
aws s3 mb s3://mavik-reports --region us-east-1

# Enable CORS on upload bucket
cat > cors.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://ai.mavik-ssot.com"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws s3api put-bucket-cors --bucket mavik-uploads --cors-configuration file://cors.json
```

---

## Step 3: Store Secrets in AWS Secrets Manager

```bash
# Create secret for AWS credentials (for ECS tasks to use Bedrock/S3)
aws secretsmanager create-secret \
  --name mavik-ai/aws-credentials \
  --description "AWS credentials for Mavik AI tasks" \
  --secret-string "{
    \"AWS_ACCESS_KEY_ID\":\"YOUR_ACCESS_KEY\",
    \"AWS_SECRET_ACCESS_KEY\":\"YOUR_SECRET_KEY\"
  }" \
  --region us-east-1

# Create secret for API keys
aws secretsmanager create-secret \
  --name mavik-ai/api-keys \
  --description "API keys for Mavik AI" \
  --secret-string "{
    \"TAVILY_API_KEY\":\"tvly-YOUR_KEY_HERE\"
  }" \
  --region us-east-1
```

---

## Step 4: Create ECR Repositories

```bash
# Create repositories for Docker images
aws ecr create-repository \
  --repository-name mavik-ai/backend \
  --region us-east-1

aws ecr create-repository \
  --repository-name mavik-ai/frontend \
  --region us-east-1
```

---

## Step 5: Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name mavik-ai-cluster \
  --region us-east-1
```

---

## Step 6: Create VPC and Networking (if you don't have one)

**Option A: Use Default VPC**
```bash
# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
echo "VPC ID: $VPC_ID"

# Get default subnets
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].[SubnetId,AvailabilityZone]' --output table
```

**Option B: Create New VPC** (recommended for production)
```bash
# This is more complex - skip for now and use default VPC
```

---

## Step 7: Create Security Group

```bash
# Get VPC ID (from Step 6)
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)

# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name mavik-ai-sg \
  --description "Security group for Mavik AI ECS tasks" \
  --vpc-id $VPC_ID \
  --output text)

echo "Security Group: $SG_ID"

# Allow inbound HTTP/HTTPS from anywhere (for ALB)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 3000 \
  --cidr 0.0.0.0/0

# Allow all outbound
aws ec2 authorize-security-group-egress \
  --group-id $SG_ID \
  --protocol -1 \
  --cidr 0.0.0.0/0
```

---

## Step 8: Create IAM Execution Role

```bash
# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "ecs-tasks.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://trust-policy.json

# Attach managed policies
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

---

## Step 9: Build and Push Docker Images

```bash
cd /path/to/chat-assistant

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 167067248318.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
cd backend
docker build -t mavik-ai/backend .
docker tag mavik-ai/backend:latest 167067248318.dkr.ecr.us-east-1.amazonaws.com/mavik-ai/backend:latest
docker push 167067248318.dkr.ecr.us-east-1.amazonaws.com/mavik-ai/backend:latest

# Build and push frontend
cd ../frontend
docker build -t mavik-ai/frontend -f Dockerfile.prod .
docker tag mavik-ai/frontend:latest 167067248318.dkr.ecr.us-east-1.amazonaws.com/mavik-ai/frontend:latest
docker push 167067248318.dkr.ecr.us-east-1.amazonaws.com/mavik-ai/frontend:latest
```

---

## Step 10: Create CloudWatch Log Groups

```bash
aws logs create-log-group --log-group-name /ecs/mavik-ai-backend --region us-east-1
aws logs create-log-group --log-group-name /ecs/mavik-ai-frontend --region us-east-1
```

---

## Step 11: Register Task Definitions

Use the JSON files in the `aws/` folder:

```bash
cd /path/to/chat-assistant

# Register backend task
aws ecs register-task-definition \
  --cli-input-json file://aws/backend-task-def.json \
  --region us-east-1

# Register frontend task
aws ecs register-task-definition \
  --cli-input-json file://aws/frontend-task-def.json \
  --region us-east-1
```

---

## Step 12: Create Application Load Balancer

```bash
# Get subnet IDs (need at least 2 in different AZs)
SUBNETS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0:2].SubnetId' \
  --output text | tr '\t' ' ')

echo "Subnets: $SUBNETS"

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name mavik-ai-alb \
  --subnets $SUBNETS \
  --security-groups $SG_ID \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

echo "ALB ARN: $ALB_ARN"

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "ALB DNS: $ALB_DNS"
```

---

## Step 13: Create Target Groups

```bash
# Frontend target group
FRONTEND_TG_ARN=$(aws elbv2 create-target-group \
  --name mavik-ai-frontend-tg \
  --protocol HTTP \
  --port 3000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path / \
  --health-check-interval-seconds 30 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

echo "Frontend TG: $FRONTEND_TG_ARN"

# Backend target group
BACKEND_TG_ARN=$(aws elbv2 create-target-group \
  --name mavik-ai-backend-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

echo "Backend TG: $BACKEND_TG_ARN"
```

---

## Step 14: Request SSL Certificate

```bash
# Request certificate for ai.mavik-ssot.com
CERT_ARN=$(aws acm request-certificate \
  --domain-name ai.mavik-ssot.com \
  --validation-method DNS \
  --region us-east-1 \
  --query 'CertificateArn' \
  --output text)

echo "Certificate ARN: $CERT_ARN"

# Get validation records
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'
```

**IMPORTANT**: You need to add the CNAME record to Route 53 to validate the certificate.

---

## Step 15: Create ALB Listeners

```bash
# HTTP listener (redirect to HTTPS)
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}"

# HTTPS listener (after certificate is validated)
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=$CERT_ARN \
  --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN \
  --query 'Listeners[0].ListenerArn' \
  --output text)

# Add rule for backend API
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 1 \
  --conditions Field=path-pattern,Values='/api/*' \
  --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
```

---

## Step 16: Configure Route 53

```bash
# Get hosted zone ID
ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='mavik-ssot.com.'].Id" \
  --output text | cut -d'/' -f3)

echo "Zone ID: $ZONE_ID"

# Get ALB hosted zone ID
ALB_ZONE_ID=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].CanonicalHostedZoneId' \
  --output text)

# Create A record for ai.mavik-ssot.com
cat > route53-change.json <<EOF
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "ai.mavik-ssot.com",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "$ALB_ZONE_ID",
        "DNSName": "$ALB_DNS",
        "EvaluateTargetHealth": true
      }
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch file://route53-change.json
```

---

## Step 17: Create ECS Services

```bash
# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[0:2].SubnetId' \
  --output text | sed 's/\t/,/g')

# Backend service
aws ecs create-service \
  --cluster mavik-ai-cluster \
  --service-name mavik-ai-backend-service \
  --task-definition mavik-ai-backend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$BACKEND_TG_ARN,containerName=backend,containerPort=8000" \
  --region us-east-1

# Frontend service
aws ecs create-service \
  --cluster mavik-ai-cluster \
  --service-name mavik-ai-frontend-service \
  --task-definition mavik-ai-frontend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=$FRONTEND_TG_ARN,containerName=frontend,containerPort=3000" \
  --region us-east-1
```

---

## Step 18: Verify Deployment

```bash
# Check services
aws ecs describe-services \
  --cluster mavik-ai-cluster \
  --services mavik-ai-backend-service mavik-ai-frontend-service \
  --region us-east-1

# Check tasks
aws ecs list-tasks --cluster mavik-ai-cluster --region us-east-1

# View logs
aws logs tail /ecs/mavik-ai-backend --follow --region us-east-1
```

Wait 5-10 minutes for:
1. Certificate validation
2. DNS propagation
3. ECS tasks to start

Then visit: **https://ai.mavik-ssot.com**

---

## Automated Script

I've created `deploy-to-aws.sh` which automates steps 9 and 17 (building and deploying).

After initial setup (steps 1-16), you can update with:
```bash
./deploy-to-aws.sh
```

---

## Troubleshooting

### Certificate not validated
- Check Route 53 for CNAME validation record
- Wait 30 minutes for DNS propagation

### Tasks not starting
```bash
aws ecs describe-tasks --cluster mavik-ai-cluster --tasks <task-id> --region us-east-1
```

### 503 errors
- Check target group health
- Verify security group allows traffic

---

## Cost Estimate

- **ECS Fargate**: ~$40/month (2 small tasks)
- **Application Load Balancer**: ~$20/month
- **S3**: ~$5/month
- **Bedrock**: Pay per use
- **Total**: ~$65-75/month + usage

---

## Next Steps

1. Run through steps 1-17
2. Test at https://ai.mavik-ssot.com
3. Set up monitoring and alerts
4. Configure auto-scaling if needed

You can do this completely independently without Paul's help!
