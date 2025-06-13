#!/bin/bash

# Update ECS task definition to use latest image

echo "Updating ECS task definition to use latest image..."

# Get current task definition
aws ecs describe-task-definition --task-definition loveandlaw-production --region us-east-1 > /tmp/task-def.json

# Update the image to latest
cat /tmp/task-def.json | jq '.taskDefinition | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy) | .containerDefinitions[0].image = "085603066392.dkr.ecr.us-east-1.amazonaws.com/loveandlaw-backend:latest"' > /tmp/new-task-def.json

# Register new task definition
NEW_REVISION=$(aws ecs register-task-definition --cli-input-json file:///tmp/new-task-def.json --region us-east-1 | jq -r '.taskDefinition.revision')

echo "Registered new task definition: loveandlaw-production:$NEW_REVISION"

# Update service
aws ecs update-service \
    --cluster loveandlaw-production-cluster \
    --service loveandlaw-api \
    --task-definition loveandlaw-production:$NEW_REVISION \
    --force-new-deployment \
    --region us-east-1 > /dev/null

echo "Service updated. Waiting for deployment..."

# Wait for deployment
sleep 30

echo "Deployment in progress. The recursion limit fix should be applied shortly."