# LoveAndLaw Backend - Production Deployment Guide

## Overview

The LoveAndLaw backend provides therapeutic conversational AI support for family law issues, with lawyer matching and contextual guidance.

**Status**: ✅ Production deployment is fully operational with WebSocket support.

## Live Endpoints

- **REST API**: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
- **WebSocket**: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`
- **Health Check**: `GET https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/health`

## Architecture

```
REST API:  Client → API Gateway → ALB → ECS → Backend Services
WebSocket: Client → API Gateway → Lambda → ECS (via HTTP) → Backend Services
                                    ↓
                             DynamoDB (connections)
```

## Local Development

### Prerequisites
- Python 3.8+
- Docker
- AWS CLI configured

### Setup

1. Clone repository and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start Elasticsearch (for local development):
```bash
./start-elasticsearch.sh
```
Note: Production uses Elastic Cloud. Configure `ELASTICSEARCH_URL` and `ELASTICSEARCH_API_KEY` in `.env`

4. Run locally:
```bash
python main.py
```

## AWS Deployment

### Quick Deploy

Use the automated deployment script for a complete deployment with testing:

```bash
# Full deployment with build, deploy, and test
./deploy.sh

# Run production tests only
./deploy.sh test

# Check service health only
./deploy.sh health
```

The deploy script will:
1. Run local syntax checks
2. Build and push Docker image to ECR
3. Update ECS service with new image
4. Update Lambda function if needed
5. Wait for services to stabilize
6. Run production API tests
7. Verify service health

### Manual Deployment

If you need to deploy manually:

1. Build and push Docker image:
```bash
./scripts/aws/deploy.sh
```

2. Update ECS service:
```bash
aws ecs update-service \
  --cluster loveandlaw-production-cluster \
  --service loveandlaw-api \
  --force-new-deployment
```

### Automated Deployment (GitHub Actions)

Push to `main` branch to trigger automatic deployment:
- Runs tests
- Builds and pushes Docker image
- Updates ECS service
- Runs production tests
- Sends notifications

Configure GitHub secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## API Documentation

### WebSocket Protocol

Connect and send messages:

```javascript
const ws = new WebSocket('wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production');

ws.send(JSON.stringify({
  action: "sendMessage",
  data: {
    type: "user_msg",
    cid: "unique-id",
    text: "I need help with divorce"
  }
}));
```

Response types:
- `ai_chunk`: Streaming AI response
- `cards`: Lawyer recommendations
- `suggestions`: Follow-up questions
- `stream_end`: End of response

## Monitoring

- **CloudWatch Dashboard**: [LoveAndLaw-Production](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=LoveAndLaw-Production)
- **Logs**: 
  - Lambda: `/aws/lambda/loveandlaw-websocket-handler`
  - ECS: `/ecs/loveandlaw-production`

## Testing

Run the test suite:
```bash
python test_production_api.py
```

## SSL Certificate

Pending DNS validation. Add this CNAME record:
```
Name: _70abf58bb6c1ad908ac6cd3efb87be95.loveandlaw.xyz
Type: CNAME
Value: _b655fd4fa7972a4c21ee6df4bc3482c5.xlfgrmvvlj.acm-validations.aws
```

## Support

For issues, check:
1. CloudWatch logs
2. ECS task health
3. Lambda function logs

## Environment Variables

Required in production:
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_API_KEY`
- `JWT_SECRET_KEY`