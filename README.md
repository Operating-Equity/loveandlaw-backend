# Love & Law Backend

A therapeutic conversational AI backend for family law assistance, built with Python, FastAPI, LangGraph, and WebSockets.

## Overview

This system provides a 24×7 family law assistant that:
- Listens like a therapist with active listening and validation
- Guides like a paralegal with clear next steps
- Matches users to local attorneys based on their needs
- Learns continuously to provide personalized support
- Protects vulnerable users with ethical safeguards

## Architecture

```
   CloudFront (wss / https)
          │
    API Gateway
          │
┌────────────────── Chat Edge Service ──────────────────┐
│  • WebSocket session management                      │
│  • PII redaction                                     │
│  • Token streaming                                   │
│  • Delegates to Therapeutic Engine                   │
└───────────────────────────────────────────────────────┘
          │
   ──> Therapeutic Engine (LangGraph Orchestrator)
          │
   DynamoDB · OpenSearch · S3 · Redis
```

## Key Features

- **Adaptive Empathy**: Adjusts responses based on distress level and engagement
- **Therapeutic Alliance Tracking**: Monitors bond, goal, and task alignment
- **Crisis Detection**: Immediate safety interventions when needed
- **PII Protection**: Automatic redaction of sensitive information
- **Lawyer Matching**: AI-powered matching with local attorneys
- **Real-time Streaming**: WebSocket-based conversational interface

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd loveandlaw-backend
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

   The services will start on:
   - REST API: http://localhost:8000
   - WebSocket: ws://localhost:8001

## API Endpoints

### REST API

- `GET /` - Health check
- `POST /api/v1/match` - Match lawyers based on criteria
- `POST /api/v1/lawyers/upload` - Upload lawyers via CSV (admin)
- `GET /api/v1/profile/{user_id}` - Get user profile

### WebSocket Protocol

Connect to `ws://localhost:8001` and authenticate:

```json
{
  "type": "auth",
  "user_id": "your-user-id"
}
```

Send messages:
```json
{
  "type": "user_msg",
  "cid": "unique-message-id",
  "text": "I need help with custody arrangements"
}
```

## Project Structure

```
src/
├── agents/          # Therapeutic agents (safety, listener, etc.)
├── api/            # REST API endpoints
├── config/         # Configuration management
├── core/           # Core services (therapeutic engine, websocket)
├── models/         # Data models
├── services/       # External services (database, PII, etc.)
└── utils/          # Utilities (logging, etc.)
```

## Configuration

Key environment variables:

- `GROQ_API_KEY` - Groq API for Llama 4 models
- `AWS_REGION` - AWS region for services
- `ELASTICSEARCH_URL` - Elasticsearch endpoint
- `JWT_SECRET_KEY` - Secret for JWT tokens

See `.env.example` for full configuration options.

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black src/
flake8 src/
mypy src/
```

### Local Services

For local development, you'll need:
- Elasticsearch (port 9200)
- Redis (port 6379)
- DynamoDB Local (optional, port 8000)

## Deployment

See `TODO.md` for deployment tasks and AWS setup requirements.

## Security

- All PII is automatically redacted before storage
- JWT-based authentication
- Role-based access control
- TLS encryption for all connections
- GDPR-compliant data handling

## License

Proprietary - All rights reserved

## Support

For issues and questions, please refer to the documentation or contact the development team.
