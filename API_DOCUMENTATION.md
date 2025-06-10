# LoveAndLaw API Documentation

## Overview

The LoveAndLaw API provides therapeutic conversational support for individuals navigating family law issues. It combines empathetic AI responses with practical legal guidance and lawyer matching services.

## Base URLs

- **REST API**: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
- **WebSocket**: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`

## Authentication

JWT authentication framework is implemented but currently disabled for development/testing. To enable authentication in production, set `AUTH_ENABLED=true` in environment variables.

## REST API Endpoints

### Health Check

Check if the API is operational.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "environment": "production"
}
```

**Status Codes**:
- `200`: Service is healthy
- `503`: Service is unhealthy

### Lawyer Match (Coming Soon)

Find lawyers based on user requirements.

**Endpoint**: `POST /v1/match`

**Request Body**:
```json
{
  "facts": {
    "zip": "19104",
    "practice_area": "divorce",
    "budget": "$$",
    "preferences": {
      "gender": "female",
      "languages": ["English", "Spanish"],
      "specializations": ["collaborative divorce", "mediation"]
    }
  }
}
```

**Response**:
```json
{
  "cards": [
    {
      "id": "lawyer123",
      "name": "Sarah Johnson, Esq.",
      "firm": "Johnson Family Law",
      "match_score": 0.95,
      "blurb": "Specializes in collaborative divorce and mediation",
      "phone": "(215) 555-0123",
      "email": "sarah@johnsonlaw.com",
      "website": "https://johnsonlaw.com",
      "address": "123 Market St, Philadelphia, PA 19104"
    }
  ]
}
```

## WebSocket API

The WebSocket API provides real-time conversational support with streaming responses.

### Connection

Connect to: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`

### Message Protocol

All messages must include an `action` field. The primary action is `sendMessage`.

### Sending Messages

**Request Format**:
```json
{
  "action": "sendMessage",
  "data": {
    "type": "user_msg",
    "cid": "unique-conversation-id",
    "text": "User's message text"
  }
}
```

**Fields**:
- `action`: Always "sendMessage" for user messages
- `data.type`: Always "user_msg" for user messages
- `data.cid`: Unique conversation ID (generate client-side)
- `data.text`: The user's message

### Response Types

The server will send multiple response types:

#### 1. AI Response Chunks

Therapeutic responses are streamed in chunks for a natural conversation feel.

```json
{
  "type": "ai_chunk",
  "cid": "unique-conversation-id",
  "text_fragment": "I understand you're going through a difficult time..."
}
```

#### 2. Lawyer Cards

Matched lawyers based on the conversation context.

```json
{
  "type": "cards",
  "cid": "unique-conversation-id",
  "cards": [
    {
      "id": "lawyer1",
      "name": "Sarah Johnson, Esq.",
      "firm": "Johnson Family Law",
      "match_score": 0.95,
      "blurb": "Specializes in collaborative divorce",
      "link": "https://example.com/lawyers/sarah-johnson"
    }
  ]
}
```

#### 3. Suggestions

Contextual suggestions for follow-up questions.

```json
{
  "type": "suggestions",
  "cid": "unique-conversation-id",
  "suggestions": [
    "What are the first steps in filing for divorce?",
    "How is property divided in Pennsylvania?",
    "What should I know about child custody?"
  ]
}
```

#### 4. Stream End

Indicates the AI has finished responding.

```json
{
  "type": "stream_end",
  "cid": "unique-conversation-id"
}
```

#### 5. Error

Error messages if something goes wrong.

```json
{
  "type": "error",
  "message": "Error description"
}
```

### Example WebSocket Flow

```javascript
// Connect
const ws = new WebSocket('wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production');

// Send message
ws.send(JSON.stringify({
  action: "sendMessage",
  data: {
    type: "user_msg",
    cid: "conv-123",
    text: "I need help with a divorce in Philadelphia"
  }
}));

// Receive responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'ai_chunk':
      // Append to conversation
      appendToChat(data.text_fragment);
      break;
      
    case 'cards':
      // Display lawyer recommendations
      showLawyerCards(data.cards);
      break;
      
    case 'suggestions':
      // Show suggestion buttons
      showSuggestions(data.suggestions);
      break;
      
    case 'stream_end':
      // AI finished responding
      enableUserInput();
      break;
  }
};
```

## Rate Limits

- REST API: 100 requests per minute
- WebSocket: 10 messages per minute per connection

## Error Handling

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

Common error codes:
- `RATE_LIMITED`: Too many requests
- `INVALID_INPUT`: Malformed request
- `INTERNAL_ERROR`: Server error

## Best Practices

1. **Connection Management**: Reuse WebSocket connections for multiple messages
2. **Error Recovery**: Implement exponential backoff for reconnection
3. **Message IDs**: Use unique conversation IDs (cid) for tracking
4. **Streaming**: Process AI chunks as they arrive for better UX

## Support

For API support, please contact: support@loveandlaw.xyz

## Changelog

- **v1.0.0** (2025-06-10): Initial production release
  - WebSocket therapeutic conversations
  - Mock lawyer matching
  - Contextual suggestions