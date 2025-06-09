# LoveAndLaw Backend - Quick Start Guide

## Current Status

The LoveAndLaw backend is ready to run with the following components:

### ✅ Implemented
- **FastAPI REST API** with endpoints for lawyer matching, profile management, and CSV upload
- **WebSocket server** for real-time chat conversations
- **Therapeutic Engine** with all agents (Listener, Advisor, Safety, etc.)
- **Legal Specialist Agents** for specialized intake (divorce, custody, support, etc.)
- **Authentication** framework (with development bypass)
- **Database services** with graceful fallback

### 🚧 Dependencies Required
- **Elasticsearch** - For lawyer search functionality
- **Groq API Key** - For AI model access

### 📝 Optional Dependencies
- **Redis** - For caching (can run without)
- **AWS DynamoDB** - For user profiles (can run without)
- **Anthropic API Key** - Not currently used

## Quick Start

### 1. Install Minimal Dependencies

```bash
# Option A: Install minimal requirements (recommended for testing)
pip install -r requirements-minimal.txt

# Option B: Install all requirements (if you have all services)
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET_KEY=development_secret_key_not_for_production

# Optional (defaults work for local development)
ELASTICSEARCH_URL=http://localhost:9200
ENVIRONMENT=development
DEBUG=True
```

### 3. Start Elasticsearch

```bash
# Using Docker (recommended)
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.17.0

# Or download and run locally from https://www.elastic.co/downloads/elasticsearch
```

### 4. Test Elasticsearch Connection

```bash
python test_elasticsearch.py
```

### 5. Populate Sample Lawyer Data

```bash
python scripts/populate_lawyers.py
```

### 6. Run the API

```bash
# Option A: Run minimal API only (recommended for testing)
python run_minimal.py

# Option B: Run full stack (API + WebSocket)
python main.py
```

## Testing the API

### 1. Health Check
```bash
curl http://localhost:8000/
```

### 2. API Documentation
Open http://localhost:8000/docs in your browser

### 3. Match Lawyers (No Auth in Dev Mode)
```bash
curl -X POST http://localhost:8000/api/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "facts": {
      "zip": "19104",
      "practice_areas": ["divorce", "custody"],
      "budget_range": "$$"
    },
    "limit": 5
  }'
```

### 4. WebSocket Test (if running full stack)
```javascript
// In browser console or Node.js
const ws = new WebSocket('ws://localhost:8001');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    user_id: 'test_user_123'
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};

// After auth success, send a message
ws.send(JSON.stringify({
  type: 'user_msg',
  text: 'I need help with divorce proceedings'
}));
```

## Troubleshooting

### Elasticsearch Connection Failed
- Make sure Elasticsearch is running on port 9200
- Check if another service is using port 9200
- Try: `curl http://localhost:9200` to test

### Missing Groq API Key
- Sign up at https://console.groq.com to get an API key
- Add it to your `.env` file

### Import Errors
- Make sure you're in the project root directory
- Install dependencies: `pip install -r requirements-minimal.txt`
- Check Python version: requires Python 3.8+

### Port Already in Use
- API runs on port 8000, WebSocket on 8001
- Change ports in `.env` file if needed

## Next Steps

1. **Get Groq API Key**: Required for AI features to work
2. **Populate More Lawyers**: Modify `scripts/populate_lawyers.py` or use the CSV upload endpoint
3. **Test Chat Flow**: Connect via WebSocket to test the therapeutic engine
4. **Deploy to AWS**: See deployment guide (coming soon)

## Development Mode Features

In development mode (`DEBUG=True`):
- Authentication is bypassed (returns dev user)
- Detailed error messages
- Hot reload enabled
- WebSocket metrics visible

## Production Checklist

Before deploying to production:
- [ ] Set proper JWT_SECRET_KEY
- [ ] Enable authentication
- [ ] Configure AWS services
- [ ] Set up monitoring (Sentry)
- [ ] Enable HTTPS/WSS
- [ ] Configure CORS properly
- [ ] Set DEBUG=False