# LoveAndLaw Backend

AI-powered therapeutic conversational support for family law issues.

## Production Endpoints

- **REST API**: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
- **WebSocket**: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`

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
python test_production_api.py
```

### Deployment

```bash
# Complete deployment with testing
./deploy.sh

# Check production health
./deploy.sh health
```

## Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - AWS deployment instructions
- [API Documentation](API_DOCUMENTATION.md) - API reference and examples
- [Startup Guide](STARTUP_GUIDE.md) - Detailed setup instructions

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
- **Data**: Elasticsearch, DynamoDB
- **Monitoring**: CloudWatch

## License

Proprietary - See LICENSE.txt