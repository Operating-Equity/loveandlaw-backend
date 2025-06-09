# AWS Deployment Guide for LoveAndLaw Backend

## Architecture Overview

```
CloudFront (CDN)
    │
    ├── API Gateway (REST API)
    │   └── ALB → ECS Fargate (API containers)
    │
    └── API Gateway (WebSocket)
        └── ALB → ECS Fargate (WebSocket containers)
            
Backend Services:
- DynamoDB (User profiles, conversations)
- OpenSearch (Lawyer data)
- ElastiCache (Redis for sessions)
- S3 (Static assets, logs)
- Secrets Manager (API keys)
```

## Prerequisites

1. AWS CLI installed and configured
2. Docker installed locally
3. AWS CDK or Terraform (optional, for IaC)

## Step 1: Prepare Secrets

```bash
# Store your API keys in AWS Secrets Manager
aws secretsmanager create-secret \
  --name loveandlaw/api-keys \
  --secret-string '{
    "GROQ_API_KEY": "your-groq-key",
    "ANTHROPIC_API_KEY": "your-anthropic-key",
    "JWT_SECRET_KEY": "generate-strong-key-here"
  }'
```

## Step 2: Create ECR Repository

```bash
# Create repository for Docker images
aws ecr create-repository \
  --repository-name loveandlaw-backend \
  --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

## Step 3: Build and Push Docker Image

Create `Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_lg

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "start_api.py"]
```

Build and push:
```bash
docker build -t loveandlaw-backend .
docker tag loveandlaw-backend:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/loveandlaw-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/loveandlaw-backend:latest
```

## Step 4: Create VPC and Networking

```bash
# Use AWS CDK or CloudFormation template
# Key components:
# - VPC with public/private subnets across 2 AZs
# - NAT Gateway for private subnet internet access
# - Security groups for ALB, ECS, databases
```

## Step 5: Set up Databases

### DynamoDB Tables
```bash
# Conversations table
aws dynamodb create-table \
  --table-name loveandlaw-conversations \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=turn_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=turn_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# User profiles table
aws dynamodb create-table \
  --table-name loveandlaw-profiles \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### OpenSearch Domain
```bash
aws opensearch create-domain \
  --domain-name loveandlaw-lawyers \
  --elasticsearch-version OpenSearch_2.11 \
  --elasticsearch-cluster-config \
    InstanceType=m5.large.search,InstanceCount=2 \
  --ebs-options \
    EBSEnabled=true,VolumeType=gp3,VolumeSize=100
```

### ElastiCache Redis
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id loveandlaw-redis \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1
```

## Step 6: Create ECS Cluster and Task Definition

Create `ecs-task-definition.json`:
```json
{
  "family": "loveandlaw-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/loveandlaw-task-role",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/loveandlaw-execution-role",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/loveandlaw-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "AWS_REGION", "value": "us-east-1"},
        {"name": "ELASTICSEARCH_URL", "value": "https://YOUR_OPENSEARCH_ENDPOINT"},
        {"name": "REDIS_URL", "value": "redis://YOUR_REDIS_ENDPOINT:6379"}
      ],
      "secrets": [
        {
          "name": "GROQ_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:loveandlaw/api-keys:GROQ_API_KEY::"
        },
        {
          "name": "ANTHROPIC_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:loveandlaw/api-keys:ANTHROPIC_API_KEY::"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:loveandlaw/api-keys:JWT_SECRET_KEY::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/loveandlaw-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Create ECS cluster and service:
```bash
# Create cluster
aws ecs create-cluster --cluster-name loveandlaw-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create service (after ALB is created)
aws ecs create-service \
  --cluster loveandlaw-cluster \
  --service-name loveandlaw-api \
  --task-definition loveandlaw-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=api,containerPort=8000
```

## Step 7: Set up Load Balancer and API Gateway

### Application Load Balancer
```bash
# Create ALB (use console or CloudFormation for easier setup)
# - Internet-facing ALB for API Gateway integration
# - Target group pointing to ECS tasks
# - Health check on /health endpoint
```

### API Gateway
```bash
# REST API for /api/* routes
# WebSocket API for /ws/* routes
# Both integrate with ALB via VPC Link
```

## Step 8: Configure CloudFront

```bash
# Create CloudFront distribution
# - Origin 1: API Gateway REST API
# - Origin 2: API Gateway WebSocket
# - Cache behaviors configured appropriately
# - Custom domain with ACM certificate
```

## Step 9: Data Migration

```bash
# Upload lawyer data to S3
aws s3 cp .data/ s3://loveandlaw-data-bucket/initial-load/ --recursive

# Create Lambda function to load data from S3 to OpenSearch
# Or use ECS task with larger memory allocation
```

## Step 10: Monitoring and Logging

1. **CloudWatch Logs**: Already configured in ECS task
2. **CloudWatch Metrics**: ECS, ALB, API Gateway metrics
3. **X-Ray**: Add tracing to the application
4. **Alarms**: Set up for high error rates, latency, etc.

## Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=False

# Removed - using IAM roles
# AWS_ACCESS_KEY_ID=xxx
# AWS_SECRET_ACCESS_KEY=xxx

# Using service discovery or environment-specific values
ELASTICSEARCH_URL=https://search-loveandlaw-xxx.us-east-1.es.amazonaws.com
REDIS_URL=redis://loveandlaw-redis.xxx.cache.amazonaws.com:6379

# From Secrets Manager
# GROQ_API_KEY=xxx
# ANTHROPIC_API_KEY=xxx
# JWT_SECRET_KEY=xxx
```

## Cost Optimization Tips

1. **ECS Fargate Spot**: Use for non-critical workloads
2. **Auto Scaling**: Configure based on CPU/memory metrics
3. **Reserved Instances**: For predictable workloads
4. **S3 Lifecycle**: Move old logs to Glacier
5. **DynamoDB On-Demand**: Start with on-demand, switch to provisioned if predictable

## Security Best Practices

1. **Never commit secrets**: Use Secrets Manager
2. **IAM Roles**: Use task roles instead of access keys
3. **VPC**: Keep databases in private subnets
4. **Security Groups**: Principle of least privilege
5. **Encryption**: Enable at-rest and in-transit encryption
6. **WAF**: Add AWS WAF to CloudFront

## Deployment Commands Summary

```bash
# 1. Build and push Docker image
./scripts/deploy.sh build

# 2. Update ECS service (rolling deployment)
./scripts/deploy.sh update-service

# 3. Run database migrations
./scripts/deploy.sh migrate

# 4. Load lawyer data
./scripts/deploy.sh load-data
```

## Estimated Monthly Costs (2 AZs, moderate traffic)

- ECS Fargate (2 tasks, 1 vCPU, 2GB): ~$70
- ALB: ~$25
- DynamoDB (on-demand): ~$50-200
- OpenSearch (2 nodes): ~$200
- ElastiCache: ~$25
- CloudFront: ~$10-50
- Secrets Manager: ~$2
- **Total: ~$400-600/month**

## Next Steps

1. Create deployment scripts in `scripts/aws/`
2. Set up CI/CD with GitHub Actions or AWS CodePipeline
3. Implement blue-green deployments
4. Add AWS Backup for DynamoDB
5. Configure auto-scaling policies