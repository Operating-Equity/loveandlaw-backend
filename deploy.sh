#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="085603066392.dkr.ecr.us-east-1.amazonaws.com/loveandlaw-backend"
ECS_CLUSTER="loveandlaw-production-cluster"
ECS_SERVICE="loveandlaw-api"
LAMBDA_FUNCTION="loveandlaw-websocket-handler"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to check if AWS CLI is configured
check_aws_config() {
    if ! aws sts get-caller-identity &>/dev/null; then
        print_error "AWS CLI not configured. Please run 'aws configure'"
        exit 1
    fi
}

# Function to run tests locally before deployment
run_local_tests() {
    print_status "Running local tests..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_warning "Virtual environment not found. Creating one..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and run tests
    source venv/bin/activate
    
    # Check syntax
    print_status "Checking Python syntax..."
    python -m py_compile src/**/*.py || {
        print_error "Python syntax errors found"
        exit 1
    }
    
    print_success "Local tests passed"
}

# Function to build and push Docker image
build_and_push_docker() {
    print_status "Building Docker image..."
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY
    
    # Build image
    docker build -t loveandlaw-backend:latest .
    
    # Tag image
    docker tag loveandlaw-backend:latest $ECR_REPOSITORY:latest
    docker tag loveandlaw-backend:latest $ECR_REPOSITORY:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    # Push image
    print_status "Pushing Docker image to ECR..."
    docker push $ECR_REPOSITORY:latest
    docker push $ECR_REPOSITORY:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    print_success "Docker image pushed successfully"
}

# Function to update ECS service
update_ecs_service() {
    print_status "Updating ECS service..."
    
    # Force new deployment
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --force-new-deployment \
        --region $AWS_REGION \
        --output json > /dev/null
    
    print_status "Waiting for ECS deployment to stabilize..."
    
    # Wait for service to stabilize (max 10 minutes)
    if aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --region $AWS_REGION; then
        print_success "ECS service updated successfully"
    else
        print_error "ECS service failed to stabilize"
        
        # Get deployment status
        aws ecs describe-services \
            --cluster $ECS_CLUSTER \
            --services $ECS_SERVICE \
            --region $AWS_REGION \
            --query 'services[0].deployments[0].{Status:status,RunningCount:runningCount,FailedTasks:failedTasks}' \
            --output json
        
        exit 1
    fi
}

# Function to update Lambda function (if changed)
update_lambda_if_needed() {
    print_status "Checking Lambda function..."
    
    # Check if Lambda code has changed
    if [ -f "lambda_websocket_handler.py" ]; then
        print_status "Updating Lambda function..."
        
        # Create deployment package
        zip lambda_deployment.zip lambda_websocket_handler.py
        
        # Update function code
        aws lambda update-function-code \
            --function-name $LAMBDA_FUNCTION \
            --zip-file fileb://lambda_deployment.zip \
            --region $AWS_REGION \
            --output json > /dev/null
        
        # Wait for update to complete
        aws lambda wait function-updated \
            --function-name $LAMBDA_FUNCTION \
            --region $AWS_REGION
        
        rm lambda_deployment.zip
        print_success "Lambda function updated"
    else
        print_status "No Lambda changes detected"
    fi
}

# Function to run production tests
run_production_tests() {
    print_status "Running production tests..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run the production test suite
    python test_production_api.py
    
    # Check exit code
    if [ $? -eq 0 ]; then
        print_success "All production tests passed!"
    else
        print_error "Production tests failed!"
        exit 1
    fi
}

# Function to check service health
check_service_health() {
    print_status "Checking service health..."
    
    # Check REST API health
    HEALTH_URL="https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/health"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "REST API is healthy"
    else
        print_error "REST API health check failed (HTTP $HTTP_CODE)"
        exit 1
    fi
    
    # Check ECS tasks
    RUNNING_TASKS=$(aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --region $AWS_REGION \
        --query 'services[0].runningCount' \
        --output text)
    
    DESIRED_TASKS=$(aws ecs describe-services \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --region $AWS_REGION \
        --query 'services[0].desiredCount' \
        --output text)
    
    if [ "$RUNNING_TASKS" -eq "$DESIRED_TASKS" ]; then
        print_success "ECS tasks are healthy ($RUNNING_TASKS/$DESIRED_TASKS running)"
    else
        print_warning "ECS tasks not fully healthy ($RUNNING_TASKS/$DESIRED_TASKS running)"
    fi
}

# Function to show deployment summary
show_summary() {
    echo ""
    echo "======================================"
    echo -e "${GREEN}🎉 Deployment Complete!${NC}"
    echo "======================================"
    echo ""
    echo "📊 Deployment Summary:"
    echo "  - Docker Image: $ECR_REPOSITORY:latest"
    echo "  - ECS Service: $ECS_SERVICE"
    echo "  - API Endpoint: https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production"
    echo "  - WebSocket: wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Monitor CloudWatch logs for any issues"
    echo "  2. Check CloudWatch dashboard for metrics"
    echo "  3. Test the API endpoints manually if needed"
    echo ""
}

# Main deployment flow
main() {
    echo "======================================"
    echo "🚀 LoveAndLaw Backend Deployment"
    echo "======================================"
    echo ""
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    check_aws_config
    
    # Run local tests
    run_local_tests
    
    # Build and push Docker image
    build_and_push_docker
    
    # Update services
    update_ecs_service
    update_lambda_if_needed
    
    # Wait a bit for services to fully initialize
    print_status "Waiting for services to initialize..."
    sleep 30
    
    # Check health
    check_service_health
    
    # Run production tests
    run_production_tests
    
    # Show summary
    show_summary
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    test)
        print_status "Running production tests only..."
        run_production_tests
        ;;
    health)
        print_status "Checking service health only..."
        check_service_health
        ;;
    *)
        echo "Usage: $0 [deploy|test|health]"
        echo "  deploy - Full deployment with tests (default)"
        echo "  test   - Run production tests only"
        echo "  health - Check service health only"
        exit 1
        ;;
esac