#!/bin/bash

# Deploy Clerk Authentication Update to AWS
# This script deploys the Clerk authentication changes to production

set -e

echo "====================================="
echo "Deploying Clerk Authentication Update"
echo "====================================="

# Load environment variables from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if required Clerk variables are set
if [ -z "$CLERK_PUBLISHABLE_KEY" ] || [ -z "$CLERK_SECRET_KEY" ] || [ -z "$CLERK_FRONTEND_API" ]; then
    echo "ERROR: Clerk environment variables not set in .env file"
    echo "Please ensure the following are set:"
    echo "  - CLERK_PUBLISHABLE_KEY"
    echo "  - CLERK_SECRET_KEY"
    echo "  - CLERK_FRONTEND_API"
    exit 1
fi

# Commit and push changes
echo "1. Pushing code changes to repository..."
git add -A
git commit -m "Add Clerk authentication support

- Implemented Clerk JWT verification
- Updated authentication middleware to support both Clerk and standard JWT
- Added Clerk environment variables to deployment configuration
- Updated Terraform configuration for ECS deployment"
git push origin main

# Build and push Docker image
echo "2. Building and pushing Docker image..."
./scripts/aws/build-push.sh

# Update AWS Secrets Manager with Clerk secret
echo "3. Updating AWS Secrets Manager..."
aws secretsmanager update-secret \
    --secret-id loveandlaw-production-api-keys \
    --secret-string "{
        \"GROQ_API_KEY\": \"$GROQ_API_KEY\",
        \"ANTHROPIC_API_KEY\": \"$ANTHROPIC_API_KEY\",
        \"JWT_SECRET_KEY\": \"$JWT_SECRET_KEY\",
        \"ELASTICSEARCH_API_KEY\": \"$ELASTICSEARCH_API_KEY\",
        \"CLERK_SECRET_KEY\": \"$CLERK_SECRET_KEY\"
    }" \
    --region us-east-1

# Deploy with Terraform
echo "4. Deploying with Terraform..."
cd terraform

# Create terraform.tfvars with Clerk configuration
cat > terraform.tfvars <<EOF
# Auto-generated file for deployment
project_name = "loveandlaw"
environment  = "production"
aws_region   = "us-east-1"

# Container configuration
container_image = "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/loveandlaw-backend"
container_cpu    = 1024
container_memory = 2048

# Elasticsearch endpoint
elasticsearch_endpoint = "$ELASTICSEARCH_URL"

# API Keys
groq_api_key          = "$GROQ_API_KEY"
anthropic_api_key     = "$ANTHROPIC_API_KEY"
jwt_secret_key        = "$JWT_SECRET_KEY"
elasticsearch_api_key = "$ELASTICSEARCH_API_KEY"

# Clerk Configuration
clerk_publishable_key = "$CLERK_PUBLISHABLE_KEY"
clerk_secret_key      = "$CLERK_SECRET_KEY"
clerk_frontend_api    = "$CLERK_FRONTEND_API"

alert_email = "admin@loveandlaw.com"
EOF

# Apply Terraform changes
terraform init -upgrade
terraform plan -out=tfplan
terraform apply tfplan

# Force new deployment to pick up environment changes
echo "5. Forcing ECS service update..."
aws ecs update-service \
    --cluster loveandlaw-production \
    --service loveandlaw-production-api \
    --force-new-deployment \
    --region us-east-1

echo "6. Waiting for deployment to stabilize..."
aws ecs wait services-stable \
    --cluster loveandlaw-production \
    --services loveandlaw-production-api \
    --region us-east-1

# Clean up
rm -f terraform.tfvars tfplan

echo "====================================="
echo "Deployment Complete!"
echo "====================================="
echo ""
echo "Clerk authentication has been deployed to production."
echo "Your frontend can now authenticate using Clerk JWT tokens."
echo ""
echo "Test the authentication with:"
echo "curl -H 'Authorization: Bearer YOUR_CLERK_JWT_TOKEN' \\"
echo "     https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/profile/user_id"
echo ""