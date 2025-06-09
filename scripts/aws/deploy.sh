#!/bin/bash
# AWS Deployment Script for LoveAndLaw Backend

set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="loveandlaw-backend"
ECS_CLUSTER="loveandlaw-cluster"
ECS_SERVICE="loveandlaw-api"
IMAGE_TAG=${IMAGE_TAG:-latest}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build       Build and push Docker image to ECR"
    echo "  deploy      Update ECS service with new image"
    echo "  migrate     Run database migrations"
    echo "  load-data   Load lawyer data into OpenSearch"
    echo "  full        Run build and deploy"
    echo ""
}

function build_and_push() {
    echo -e "${GREEN}Building Docker image...${NC}"
    docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} .
    
    echo -e "${GREEN}Logging into ECR...${NC}"
    aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
    
    echo -e "${GREEN}Tagging image...${NC}"
    docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} \
        ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}
    
    echo -e "${GREEN}Pushing image to ECR...${NC}"
    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}
    
    echo -e "${GREEN}Build and push completed!${NC}"
}

function deploy_to_ecs() {
    echo -e "${GREEN}Updating ECS service...${NC}"
    
    # Force new deployment
    aws ecs update-service \
        --cluster ${ECS_CLUSTER} \
        --service ${ECS_SERVICE} \
        --force-new-deployment \
        --region ${AWS_REGION}
    
    echo -e "${YELLOW}Waiting for service to stabilize...${NC}"
    aws ecs wait services-stable \
        --cluster ${ECS_CLUSTER} \
        --services ${ECS_SERVICE} \
        --region ${AWS_REGION}
    
    echo -e "${GREEN}Deployment completed!${NC}"
}

function run_migrations() {
    echo -e "${GREEN}Running database migrations...${NC}"
    
    # Run as ECS task
    TASK_ARN=$(aws ecs run-task \
        --cluster ${ECS_CLUSTER} \
        --task-definition loveandlaw-migrate:latest \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${PRIVATE_SUBNET_IDS}],securityGroups=[${SECURITY_GROUP_ID}]}" \
        --query 'tasks[0].taskArn' \
        --output text)
    
    echo -e "${YELLOW}Migration task started: ${TASK_ARN}${NC}"
    
    # Wait for task to complete
    aws ecs wait tasks-stopped --cluster ${ECS_CLUSTER} --tasks ${TASK_ARN}
    
    # Check exit code
    EXIT_CODE=$(aws ecs describe-tasks \
        --cluster ${ECS_CLUSTER} \
        --tasks ${TASK_ARN} \
        --query 'tasks[0].containers[0].exitCode' \
        --output text)
    
    if [ "$EXIT_CODE" -eq "0" ]; then
        echo -e "${GREEN}Migrations completed successfully!${NC}"
    else
        echo -e "${RED}Migrations failed with exit code: ${EXIT_CODE}${NC}"
        exit 1
    fi
}

function load_lawyer_data() {
    echo -e "${GREEN}Loading lawyer data into OpenSearch...${NC}"
    
    # This could be a Lambda function or ECS task
    # For large data, consider using AWS Glue or EMR
    
    echo -e "${YELLOW}This is a placeholder. Implement based on your data size and requirements.${NC}"
}

# Main script
case "$1" in
    build)
        build_and_push
        ;;
    deploy)
        deploy_to_ecs
        ;;
    migrate)
        run_migrations
        ;;
    load-data)
        load_lawyer_data
        ;;
    full)
        build_and_push
        deploy_to_ecs
        ;;
    *)
        print_usage
        exit 1
        ;;
esac