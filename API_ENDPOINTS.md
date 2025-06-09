# LoveAndLaw API Endpoints

## Base URL
- Local: `http://localhost:8000`
- WebSocket: `ws://localhost:8000/ws/{conversation_id}`

## REST Endpoints

### Health Check
```bash
GET /
```

### Authentication
```bash
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "password123"
}

POST /api/v1/auth/login
{
  "email": "user@example.com", 
  "password": "password123"
}
```

### Lawyer Matching
```bash
POST /api/v1/match
{
  "facts": {
    "zip": "19104",
    "practice_area": "divorce",
    "budget": "$-$$",
    "urgency": "urgent",
    "case_complexity": "contested"
  }
}
```

### Lawyer Data Management
```bash
# Upload lawyers via CSV
POST /api/v1/lawyers/upload
Content-Type: multipart/form-data
file: [CSV file]

# Search lawyers with Elasticsearch
POST /api/v1/lawyers/search
{
  "query": {
    "location": "Philadelphia, PA",
    "specialties": ["divorce", "child custody"],
    "budget_range": "$-$$"
  }
}
```

### User Profiles
```bash
GET /api/v1/profile/{user_id}
```

## WebSocket Chat

### Connect
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/test-conversation-123');

ws.onopen = () => {
  console.log('Connected to LoveAndLaw chat');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Send Message
```javascript
ws.send(JSON.stringify({
  type: 'user_msg',
  cid: 'test-conversation-123',
  text: 'I need help with a divorce case'
}));
```

### Message Types

**From Client:**
- `user_msg`: User's message
- `heartbeat`: Keep connection alive

**From Server:**
- `ai_chunk`: Streaming AI response
- `cards`: Lawyer recommendation cards
- `reflection`: Reflection prompts
- `suggestions`: Suggested questions
- `error`: Error messages
- `session_end`: Session terminated

## Example Usage

### 1. Test Lawyer Matching
```bash
curl -X POST http://localhost:8000/api/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "facts": {
      "zip": "19104",
      "practice_area": "divorce",
      "budget": "$$"
    }
  }'
```

### 2. Test WebSocket Chat
```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Bot: {data.get('text', '')}")

def on_open(ws):
    ws.send(json.dumps({
        "type": "user_msg",
        "cid": "test-123",
        "text": "I need help with child custody"
    }))

ws = websocket.WebSocketApp(
    "ws://localhost:8000/ws/test-123",
    on_message=on_message,
    on_open=on_open
)
ws.run_forever()
```

## Testing with Swagger UI

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test all REST endpoints directly from the Swagger UI interface.