# LoveAndLaw Backend

AI-powered therapeutic conversational support for family law issues.

## 🚀 Production Status

✅ **FULLY OPERATIONAL** - WebSocket and REST APIs are live and working!

- **REST API**: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
- **WebSocket**: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`
- **Current Deployment**: ECS revision 24 (ARM64 architecture)

## Quick Start

### Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python main.py
```

### Testing

```bash
# Test REST API health
curl https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/health

# Test WebSocket with Postman (see POSTMAN_TESTING_GUIDE.md)
# Import: loveandlaw-postman-collection.json
```

### Deployment

```bash
# Complete deployment with testing
./deploy.sh

# Check production health
./deploy.sh health
```

## Documentation

- [Architecture Guide](ARCHITECTURE.md) - Complete system architecture and design
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - AWS deployment instructions
- [API Documentation](API_DOCUMENTATION.md) - API reference and examples
- [Startup Guide](STARTUP_GUIDE.md) - Detailed setup instructions
- [Postman Testing Guide](POSTMAN_TESTING_GUIDE.md) - WebSocket testing instructions
- [Claude Instructions](CLAUDE.md) - AI assistant instructions for development

## Project Structure

```
src/
├── agents/          # AI agents (therapeutic, legal specialists)
├── api/             # FastAPI application
├── core/            # Core engine and WebSocket handling
├── models/          # Data models
├── services/        # Database and external services
└── utils/           # Utilities and logging

scripts/
├── aws/             # Deployment scripts
└── *.py             # Data loading scripts

terraform/           # Infrastructure as code
prompts/            # AI agent prompts
```

## Technologies

- **Backend**: Python, FastAPI, WebSockets
- **AI**: Groq Llama 4, LangGraph
- **Infrastructure**: AWS (ECS, Lambda, API Gateway)
- **Data**: Elasticsearch (required), DynamoDB (AWS), Redis (optional)
- **Monitoring**: CloudWatch

## AWS Services Setup

### DynamoDB Tables

The application uses two DynamoDB tables:
- `loveandlaw-conversations`: Stores conversation turn states
- `loveandlaw-userprofiles`: Stores user profiles and preferences

To create the tables in AWS:
```bash
python scripts/create_dynamodb_tables.py --region us-east-1
```

Or use Terraform:
```bash
cd terraform
terraform apply -target=module.database
```

## License

Proprietary - See LICENSE.txt