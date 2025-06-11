# Love & Law Frontend API Integration Guide

This guide provides comprehensive documentation for frontend engineers to integrate with the Love & Law backend APIs, including WebSocket connections, lawyer matching, and REST endpoints.

## Table of Contents
1. [Overview](#overview)
2. [WebSocket API](#websocket-api)
3. [REST API Endpoints](#rest-api-endpoints)
4. [Authentication](#authentication)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

## Overview

The Love & Law backend provides:
- **WebSocket API** for real-time chat conversations
- **REST API** for lawyer search, profile management, and file uploads

Base URLs:
- Development: `http://localhost:8000`
- Production: `https://api.loveandlaw.com` (configure as needed)

## WebSocket API

### Connection

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');
// Production: wss://api.loveandlaw.com/ws
```

### Message Flow

#### 1. Connection Established
When connected, you'll receive:
```json
{
  "type": "connection_established",
  "connection_id": "uuid",
  "message": "Connected to Love & Law Assistant"
}
```

#### 2. Authentication (Optional in Development)
Send authentication message:
```json
{
  "type": "auth",
  "user_id": "user-uuid",
  "conversation_id": "conversation-uuid" // optional, will be generated if not provided
}
```

Response:
```json
{
  "type": "auth_success",
  "user_id": "user-uuid",
  "conversation_id": "conversation-uuid"
}
```

**Note**: In development mode (`DEBUG=true`), authentication is optional. Messages will use `debug_user` if not authenticated.

#### 3. Sending User Messages
```json
{
  "type": "user_msg",
  "text": "I need a divorce lawyer in Chicago, IL 60601",
  "cid": "unique-message-id" // client-generated UUID for this message
}
```

#### 4. Receiving Responses

The backend will send multiple message types in response:

##### a. Message Acknowledgment
```json
{
  "type": "message_received",
  "cid": "unique-message-id"
}
```

##### b. AI Response (Streaming)
The response comes in chunks for real-time display:
```json
{
  "type": "ai_chunk",
  "cid": "unique-message-id",
  "text_fragment": "I understand you're looking"
}
```

##### c. AI Response Complete
```json
{
  "type": "ai_complete",
  "cid": "unique-message-id"
}
```

##### d. Lawyer Cards (When Matches Found)
```json
{
  "type": "cards",
  "cid": "unique-message-id",
  "cards": [
    {
      "id": "lawyer-id",
      "name": "John Smith",
      "firm": "Smith & Associates",
      "match_score": "85%",
      "blurb": "Experienced divorce attorney with 15 years...",
      "link": "/lawyer/lawyer-id",
      "match_explanation": "Matched because: specializes in divorce, located near you",
      "practice_areas": ["Family Law", "Divorce"],
      "location": {
        "city": "Chicago",
        "state": "illinois"
      },
      "rating": 4.5,
      "reviews_count": 127,
      "budget_range": "$$"
    }
  ]
}
```

**Note**: Lawyer cards are only sent when:
- The user's distress score is < 7 (not in crisis)
- Matching lawyers are found based on location and needs
- The system has enough information to make matches

##### e. Suggestions
```json
{
  "type": "suggestions",
  "cid": "unique-message-id",
  "suggestions": [
    "Would you like to know more about any of these lawyers?",
    "What questions do you have about the divorce process?",
    "When would you like to schedule a consultation?"
  ]
}
```

##### f. Reflection Prompts
```json
{
  "type": "reflection",
  "cid": "unique-message-id",
  "reflection_type": "emotional",
  "reflection_insights": [
    "You've shown great strength in taking this step",
    "Your concerns about the children are valid"
  ]
}
```

##### g. Metrics (Debug Mode Only)
```json
{
  "type": "metrics",
  "cid": "unique-message-id",
  "metrics": {
    "distress_score": 3.5,
    "engagement_level": 7.2,
    "alliance_bond": 6.0,
    "alliance_goal": 7.5,
    "alliance_task": 6.8,
    "sentiment": "neu",
    "enhanced_sentiment": "nervousness",
    "legal_intent": ["divorce", "custody"],
    "active_legal_specialist": "divorce_and_separation"
  }
}
```

#### 5. Heartbeat
The server sends periodic heartbeats:
```json
{
  "type": "heartbeat",
  "timestamp": "2025-06-10T12:00:00Z"
}
```

You can also send heartbeats to keep the connection alive:
```json
{
  "type": "heartbeat"
}
```

#### 6. Error Messages
```json
{
  "type": "error",
  "code": "ERROR_CODE",
  "message": "Human-readable error message"
}
```

#### 7. Session End
```json
{
  "type": "session_end",
  "message": "Session ended"
}
```

### WebSocket Best Practices

1. **Reconnection Logic**: Implement automatic reconnection with exponential backoff
2. **Message Queue**: Queue messages while disconnected and send on reconnection
3. **Heartbeat**: Send heartbeat every 30 seconds to keep connection alive
4. **Error Handling**: Display user-friendly messages for connection errors

## REST API Endpoints

### 1. Health Check

#### GET `/health`
Basic health check for load balancer.

Response:
```json
{
  "status": "healthy",
  "service": "Love & Law Backend",
  "version": "1.0.0",
  "environment": "development"
}
```

#### GET `/api/v1/health`
Detailed health check with service status.

Response:
```json
{
  "status": "healthy",
  "service": "Love & Law Backend API",
  "version": "1.0.0",
  "environment": "development",
  "checks": {
    "elasticsearch": "healthy",
    "dynamodb": "healthy",
    "redis": "not_configured"
  }
}
```

### 2. Lawyer Matching

#### POST `/api/v1/match`
Search for lawyers based on criteria.

Headers:
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

Request Body:
```json
{
  "facts": {
    "zip": "60601",
    "city": "Chicago",
    "state": "IL",
    "practice_areas": ["divorce", "custody"],
    "budget_range": "$$",
    "search_text": "experienced divorce lawyer"
  },
  "limit": 10
}
```

Response:
```json
{
  "cards": [
    {
      "id": "lawyer-123",
      "name": "Jane Doe",
      "firm": "Doe Law Firm",
      "match_score": 0.92,
      "blurb": "Experienced family law attorney...",
      "link": "/lawyer/lawyer-123",
      "practice_areas": ["Family Law", "Divorce"],
      "location": {
        "city": "Chicago",
        "state": "IL",
        "zip": "60601"
      },
      "rating": 4.8,
      "reviews_count": 245,
      "budget_range": "$$"
    }
  ]
}
```

### 3. User Profile

#### GET `/api/v1/profile/{user_id}`
Get user profile information.

Headers:
```
Authorization: Bearer <jwt-token>
```

Response:
```json
{
  "profile": {
    "user_id": "user-uuid",
    "created_at": "2025-06-10T12:00:00Z",
    "updated_at": "2025-06-10T13:00:00Z",
    "legal_situation": {
      "type": "divorce",
      "stage": "initial_consultation"
    },
    "milestones_completed": [
      "initial_contact",
      "situation_assessment"
    ],
    "current_goals": [
      "find_lawyer",
      "understand_process"
    ],
    "preferences": {
      "communication_style": "empathetic",
      "budget_range": "$$"
    },
    "average_distress_score": 4.2,
    "average_engagement_level": 7.5
  }
}
```

### 4. Lawyer CSV Upload (Admin Only)

#### POST `/api/v1/lawyers/upload`
Upload lawyers via CSV file.

Headers:
```
Authorization: Bearer <admin-jwt-token>
Content-Type: multipart/form-data
```

Form Data:
- `file`: CSV file with lawyer data

CSV Format:
```csv
id,name,firm,practice_areas,city,state,zip,budget_range,rating,reviews_count,description
1,John Smith,Smith Law,"Family Law,Divorce",Chicago,IL,60601,$$,4.5,150,"Experienced divorce attorney..."
```

Response:
```json
{
  "status": "completed",
  "indexed_count": 150,
  "errors": [
    "Row 5: Missing required field 'name'"
  ]
}
```

## Authentication

### Development Mode
- Set `DEBUG=true` in environment variables
- Authentication is optional
- Default user: `debug_user`

### Production Mode
- JWT tokens required for all REST endpoints
- WebSocket requires authentication message after connection
- Token format: `Bearer <jwt-token>`

### JWT Token Structure
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "user|admin",
  "exp": 1234567890
}
```

## Error Handling

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

### WebSocket Error Types
- `auth_failed`: Authentication failed
- `invalid_message`: Message format invalid
- `rate_limit`: Too many messages
- `internal_error`: Server error

## Examples

### Complete WebSocket Conversation Flow

```javascript
// 1. Connect and authenticate
const ws = new WebSocket('ws://localhost:8000/ws');
const userId = 'user-123';
const conversationId = 'conv-456';

ws.onopen = () => {
  console.log('Connected to Love & Law');
  
  // Send auth (optional in dev)
  ws.send(JSON.stringify({
    type: 'auth',
    user_id: userId,
    conversation_id: conversationId
  }));
};

// 2. Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'auth_success':
      // Ready to chat
      sendMessage("I need help with a divorce in Chicago");
      break;
      
    case 'ai_chunk':
      // Append to current response
      appendToChat(data.text_fragment);
      break;
      
    case 'ai_complete':
      // Response finished
      markResponseComplete();
      break;
      
    case 'cards':
      // Display lawyer matches
      displayLawyerCards(data.cards);
      break;
      
    case 'suggestions':
      // Show suggestion buttons
      displaySuggestions(data.suggestions);
      break;
      
    case 'reflection':
      // Show reflection insights
      displayReflection(data.reflection_insights);
      break;
      
    case 'metrics':
      // Debug metrics
      console.log('Conversation metrics:', data.metrics);
      break;
  }
};

// 3. Send a message
function sendMessage(text) {
  const message = {
    type: 'user_msg',
    text: text,
    cid: generateUUID()
  };
  ws.send(JSON.stringify(message));
}

// 4. Handle lawyer cards
function displayLawyerCards(cards) {
  cards.forEach(lawyer => {
    console.log(`${lawyer.name} - ${lawyer.match_score} match`);
    console.log(`  Firm: ${lawyer.firm}`);
    console.log(`  Location: ${lawyer.location.city}, ${lawyer.location.state}`);
    console.log(`  Rating: ${lawyer.rating} (${lawyer.reviews_count} reviews)`);
    console.log(`  Budget: ${lawyer.budget_range}`);
    console.log(`  Why matched: ${lawyer.match_explanation}`);
  });
}
```

### REST API Example

```javascript
// Search for lawyers
async function searchLawyers() {
  const response = await fetch('/api/v1/match', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      facts: {
        city: 'Chicago',
        state: 'IL',
        practice_areas: ['divorce'],
        budget_range: '$$'
      },
      limit: 5
    })
  });
  
  const data = await response.json();
  return data.cards;
}
```

## Important Notes

1. **Lawyer Matching**: The system uses progressive information gathering. Initial messages may not return lawyer matches until enough information is collected (location, legal issue, etc.).

2. **Crisis Handling**: If a user's distress score is >= 7, the system prioritizes emotional support over lawyer matching.

3. **Legal Specialists**: The system routes conversations to appropriate legal specialists based on the detected legal intent (divorce, custody, adoption, etc.).

4. **PII Protection**: All user messages are automatically scanned and redacted for personally identifiable information (PII) before processing.

5. **Rate Limiting**: WebSocket connections are limited to prevent abuse. Implement exponential backoff for reconnections.

## Support

For questions or issues:
- GitHub Issues: https://github.com/loveandlaw/backend/issues
- Technical Documentation: See ARCHITECTURE.md
- API Updates: Check CHANGELOG.md