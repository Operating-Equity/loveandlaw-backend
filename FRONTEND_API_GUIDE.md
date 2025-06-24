# Love & Law Frontend API Integration Guide

This guide provides comprehensive documentation for frontend engineers to integrate with the Love & Law backend APIs, including WebSocket connections, lawyer matching, and REST endpoints.

## Table of Contents
1. [Overview](#overview)
2. [Environment Setup](#environment-setup)
3. [Authentication](#authentication)
4. [WebSocket API](#websocket-api)
5. [REST API Endpoints](#rest-api-endpoints)
   - [Health Check](#1-health-check)
   - [Lawyer Endpoints](#2-lawyer-endpoints)
   - [User Profile](#3-user-profile)
   - [Conversation Management](#4-conversation-management)
   - [Lawyer CSV Upload](#5-lawyer-csv-upload-admin-only)
6. [Error Handling](#error-handling)
7. [Testing Guide](#testing-guide)
8. [Production Deployment](#production-deployment)
9. [Examples](#examples)

## Overview

The Love & Law backend provides:
- **WebSocket API** for real-time chat conversations with AI therapeutic responses
- **REST API** for lawyer search, profile management, conversation history, and administrative functions

### API Endpoints by Environment

| Environment | REST API Base URL | WebSocket URL |
|-------------|------------------|---------------|
| Local Development | `http://localhost:8000` | `ws://localhost:8000/ws` |
| Production | `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production` | `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production` |

**Note**: Production URLs use AWS API Gateway which routes to ECS backend services. Always use HTTPS/WSS in production.

## Environment Setup

### Development Environment

1. **Local Backend Setup**:
   ```bash
   # Clone and setup backend
   cd loveandlaw-backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Create .env file with required variables
   cp .env.example .env
   # Edit .env with your API keys
   
   # Start services
   ./start-elasticsearch.sh  # Requires Docker
   python -m uvicorn src.api.main:app --reload
   ```

2. **Frontend Configuration**:
   ```javascript
   // config/api.js
   const config = {
     development: {
       apiBase: 'http://localhost:8000',
       wsBase: 'ws://localhost:8000/ws',
       authRequired: false
     },
     production: {
       apiBase: 'https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production',
       wsBase: 'wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production',
       authRequired: false  // TEMPORARY: Auth disabled
     }
   };
   
   export default config[process.env.NODE_ENV || 'development'];
   ```

### Production Environment

Production currently has authentication disabled for ease of development.

## Authentication

### Current Status: Authentication Disabled 🔓

**TEMPORARY**: Authentication is currently disabled for all environments to simplify integration during development. All API endpoints are accessible without authentication tokens.

- All users automatically receive admin privileges
- No JWT tokens required
- No login/registration needed
- Each request gets a unique temporary user ID

### Future Authentication (Coming Soon)

When authentication is re-enabled, the system will support:
- JWT-based authentication
- User registration and login
- Role-based access control (user/admin)
- Secure token management

For now, you can make API calls without any authentication headers.

## WebSocket API

### Connection Setup

```javascript
class LoveAndLawWebSocket {
  constructor(config) {
    this.wsUrl = config.wsBase;
    this.authToken = config.authToken;
    this.reconnectAttempts = 0;
    this.maxReconnects = 5;
  }

  connect() {
    this.ws = new WebSocket(this.wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      
      // No authentication needed currently
      // Just start sending messages
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }
  
  send(data) {
    if (this.ws.readyState === WebSocket.OPEN) {
      // Production requires 'action' wrapper
      const message = this.wsUrl.includes('amazonaws.com') 
        ? { action: 'sendMessage', data }
        : data;
        
      this.ws.send(JSON.stringify(message));
    }
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnects) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
    }
  }
  
  handleMessage(data) {
    switch(data.type) {
      case 'connection_established':
        console.log('Connection established:', data.connection_id);
        break;
        
      case 'auth_success':
        console.log('Authenticated:', data.user_id);
        break;
        
      case 'message_received':
        console.log('Message acknowledged:', data.cid);
        break;
        
      case 'ai_chunk':
        // Append to chat UI
        this.appendAIResponse(data.text_fragment);
        break;
        
      case 'ai_complete':
        // Enable user input
        this.enableUserInput();
        break;
        
      case 'cards':
        // Display lawyer recommendations
        this.displayLawyerCards(data.cards);
        break;
        
      case 'suggestions':
        // Show suggested questions
        this.displaySuggestions(data.suggestions);
        break;
        
      case 'reflection':
        // Show reflection insights
        this.displayReflection(data.reflection_type, data.reflection_insights);
        break;
        
      case 'error':
        console.error('WebSocket error:', data.message);
        break;
    }
  }
}
```

### Message Types

#### Sending Messages
```javascript
// User message
ws.send({
  type: 'user_msg',
  text: 'I need help with child custody',
  cid: generateUUID() // Client-side generated ID
});

// Heartbeat (optional)
ws.send({
  type: 'heartbeat'
});
```

#### Receiving Messages

1. **AI Response Chunks** (Streaming):
   ```json
   {
     "type": "ai_chunk",
     "cid": "message-id",
     "text_fragment": "I understand you're"
   }
   ```

2. **Lawyer Cards**:
   ```json
   {
     "type": "cards",
     "cid": "message-id",
     "cards": [
       {
         "id": "lawyer-123",
         "name": "Jane Doe, Esq.",
         "firm": "Doe Law Firm",
         "match_score": "92%",
         "blurb": "Experienced in child custody cases",
         "link": "/lawyer/lawyer-123",
         "match_explanation": "Specializes in custody, near your location",
         "practice_areas": ["Family Law", "Child Custody"],
         "location": { "city": "Chicago", "state": "IL" },
         "rating": 4.8,
         "reviews_count": 156,
         "budget_range": "$$"
       }
     ]
   }
   ```

3. **Suggestions**:
   ```json
   {
     "type": "suggestions",
     "cid": "message-id",
     "suggestions": [
       "What are my rights as a parent?",
       "How is custody determined?",
       "What documents do I need?"
     ]
   }
   ```

4. **Reflection Prompts**:
   ```json
   {
     "type": "reflection",
     "cid": "message-id",
     "reflection_type": "emotional",
     "reflection_insights": [
       "You're taking positive steps",
       "Your concerns are valid"
     ]
   }
   ```

5. **Metrics** (Debug mode only):
   ```json
   {
     "type": "metrics",
     "cid": "message-id",
     "metrics": {
       "distress_score": 4.2,
       "engagement_level": 7.5,
       "alliance_bond": 6.8,
       "sentiment": "neu",
       "legal_intent": ["custody", "divorce"]
     }
   }
   ```

## REST API Endpoints

### 1. Health Check

#### Basic Health Check
```javascript
// GET /health
const response = await fetch(`${API_BASE}/health`);
const data = await response.json();
// Returns: { status: "healthy", service: "Love & Law Backend", version: "1.0.0" }
```

#### Detailed API Health
```javascript
// GET /api/v1/health
const response = await fetch(`${API_BASE}/api/v1/health`);
const data = await response.json();
// Returns service status for elasticsearch, dynamodb, redis
```

### 2. Lawyer Endpoints

#### Search/Match Lawyers
```javascript
// POST /api/v1/match
const response = await fetch(`${API_BASE}/api/v1/match`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    facts: {
      zip: '60601',
      city: 'Chicago',
      state: 'IL',
      practice_areas: ['divorce', 'custody'],
      budget_range: '$$',
      search_text: 'experienced collaborative divorce'
    },
    limit: 10
  })
});

const { cards } = await response.json();
```

#### Create Lawyer (Admin Only)
```javascript
// POST /api/v1/lawyers
const response = await fetch(`${API_BASE}/api/v1/lawyers`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'John Smith, Esq.',
    firm: 'Smith & Associates',
    profile_summary: 'Experienced family law attorney',
    city: 'Philadelphia',
    state: 'PA',
    zip: '19104',
    practice_areas: ['Divorce', 'Child Custody', 'Mediation'],
    specialties: [
      {
        name: 'Collaborative Divorce',
        description: 'Non-adversarial approach'
      }
    ],
    education: [
      {
        institution: 'University of Pennsylvania',
        degree: 'J.D.',
        year: 2010
      }
    ],
    years_of_experience: 15,
    languages: ['English', 'Spanish'],
    payment_methods: ['Credit Card', 'Check', 'Payment Plans'],
    phone_numbers: ['(215) 555-0123'],
    email: 'john@smithlaw.com',
    website: 'https://smithlaw.com',
    budget_range: '$$',
    active: true
  })
});

const { id, message } = await response.json();
```

#### Get Lawyer Details
```javascript
// GET /api/v1/lawyers/{lawyer_id}
const response = await fetch(`${API_BASE}/api/v1/lawyers/${lawyerId}`);

const lawyerDetails = await response.json();
```

#### Upload Lawyers CSV (Admin Only)
```javascript
// POST /api/v1/lawyers/upload
const formData = new FormData();
formData.append('file', csvFile);

const response = await fetch(`${API_BASE}/api/v1/lawyers/upload`, {
  method: 'POST',
  body: formData
});

const { status, indexed_count, errors } = await response.json();
```

### 3. User Profile

#### Get Profile
```javascript
// GET /api/v1/profile/{user_id}
const response = await fetch(`${API_BASE}/api/v1/profile/${userId}`);

const { profile } = await response.json();
```

#### Update Profile
```javascript
// PUT /api/v1/profile/{user_id}
const response = await fetch(`${API_BASE}/api/v1/profile/${userId}`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Jane Doe',
    email: 'jane@example.com',
    preferred_avatar: 'avatar-2',
    saved_lawyers: ['lawyer-123', 'lawyer-456'],
    legal_situation: {
      type: 'divorce',
      status: 'considering',
      children_involved: true,
      stage: 'initial_consultation'
    },
    current_goals: ['understand_process', 'find_lawyer'],
    preferences: {
      communication_style: 'supportive',
      notification_preferences: {
        email: true,
        sms: false,
        in_app: true
      }
    }
  })
});
```

### 4. Conversation Management

#### Get All Conversations
```javascript
// GET /api/v1/conversations
const response = await fetch(`${API_BASE}/api/v1/conversations?limit=20&offset=0`);

const { conversations, total, limit, offset } = await response.json();

// Response includes:
conversations.forEach(conv => {
  console.log({
    id: conv.conversation_id,
    created: conv.created_at,
    updated: conv.updated_at,
    lastMessage: conv.last_message,
    messageCount: conv.message_count,
    averageDistress: conv.average_distress_score,
    topics: conv.legal_topics
  });
});
```

#### Get Conversation Messages
```javascript
// GET /api/v1/conversations/{conversation_id}/messages
const response = await fetch(
  `${API_BASE}/api/v1/conversations/${convId}/messages?limit=50&order=asc`
);

const { messages, total } = await response.json();

// Messages include both user and assistant messages
messages.forEach(msg => {
  console.log({
    id: msg.message_id,
    role: msg.role, // 'user' or 'assistant'
    content: msg.content,
    timestamp: msg.timestamp,
    redacted: msg.redacted // true if PII was removed
  });
});
```

## Error Handling

### Common Error Responses

```javascript
// 404 Not Found
{
  "detail": "Lawyer not found"
}

// 422 Validation Error
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}

// 500 Internal Server Error
{
  "detail": "Internal server error"
}
```

Note: 401/403 authentication errors won't occur while auth is disabled.

### Error Handling Best Practices

```javascript
class APIClient {
  async request(url, options = {}) {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new APIError(response.status, error.detail);
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof APIError) {
        this.handleAPIError(error);
      } else {
        console.error('Network error:', error);
        throw error;
      }
    }
  }
  
  handleAPIError(error) {
    switch (error.status) {
      case 422:
        // Show validation errors
        this.showValidationErrors(error.details);
        break;
      case 404:
        // Show not found error
        this.showError('Resource not found');
        break;
      default:
        // Show generic error
        this.showError('An error occurred. Please try again.');
    }
  }
}
```

## Testing Guide

### Local Testing

1. **Start Backend Services**:
   ```bash
   # Terminal 1: Start Elasticsearch
   ./start-elasticsearch.sh
   
   # Terminal 2: Start backend
   source venv/bin/activate
   python -m uvicorn src.api.main:app --reload
   ```

2. **Test WebSocket Connection**:
   ```javascript
   // test-websocket.js
   const ws = new WebSocket('ws://localhost:8000/ws');
   
   ws.onopen = () => {
     console.log('Connected');
     ws.send(JSON.stringify({
       type: 'user_msg',
       text: 'Test message',
       cid: 'test-123'
     }));
   };
   
   ws.onmessage = (event) => {
     console.log('Received:', JSON.parse(event.data));
   };
   ```

3. **Test REST Endpoints**:
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Match lawyers
   curl -X POST http://localhost:8000/api/v1/match \
     -H "Content-Type: application/json" \
     -d '{"facts": {"zip": "19104"}, "limit": 5}'
   ```

### Production Testing

1. **Test Production Endpoints** (No Authentication Required):
   ```bash
   # Health check
   curl https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/health
   
   # Get conversations
   curl https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/conversations
   
   # Match lawyers
   curl -X POST https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/match \
     -H "Content-Type: application/json" \
     -d '{"facts": {"zip": "19104"}, "limit": 5}'
   ```

2. **Monitor Logs**:
   - CloudWatch Logs: Check ECS task logs
   - API Gateway Logs: Monitor request/response
   - WebSocket Connection Logs: Check Lambda function logs

## Production Deployment

### Frontend Deployment Checklist

1. **Environment Variables**:
   ```javascript
   // .env.production
   REACT_APP_API_BASE=https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production
   REACT_APP_WS_BASE=wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production
   REACT_APP_AUTH_REQUIRED=true
   ```

2. **CORS Configuration**:
   - Ensure your frontend domain is whitelisted in backend CORS settings
   - Contact backend team to add your domain if needed

3. **SSL/TLS**:
   - Frontend must be served over HTTPS in production
   - WebSocket connections require WSS protocol

4. **Error Monitoring**:
   ```javascript
   // Add error boundary for API failures
   class APIErrorBoundary extends React.Component {
     componentDidCatch(error, errorInfo) {
       // Log to monitoring service
       console.error('API Error:', error, errorInfo);
       // Show user-friendly error
     }
   }
   ```

5. **Performance Optimization**:
   - Implement request caching where appropriate
   - Use connection pooling for WebSocket
   - Add retry logic with exponential backoff

### Security Best Practices

1. **Request Validation**:
   - Always validate user input before sending to API
   - Sanitize data to prevent XSS attacks
   - Use HTTPS for all production requests

2. **Rate Limiting**:
   - Implement client-side rate limiting
   - Handle 429 (Too Many Requests) responses gracefully

3. **Future Security** (When Auth is Re-enabled):
   - Token storage in secure locations
   - Regular token refresh
   - Proper session management

## Examples

### Complete React Integration Example

```jsx
// hooks/useLoveAndLawAPI.js
import { useState, useEffect, useCallback } from 'react';
import config from '../config/api';

export function useLoveAndLawChat() {
  const [ws, setWs] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  
  useEffect(() => {
    const websocket = new WebSocket(config.wsBase);
    
    websocket.onopen = () => {
      setIsConnected(true);
      setWs(websocket);
    };
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };
    
    websocket.onclose = () => {
      setIsConnected(false);
      // Implement reconnection logic
    };
    
    return () => {
      websocket.close();
    };
  }, []);
  
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'ai_chunk':
        setIsTyping(true);
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant' && last.id === data.cid) {
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + data.text_fragment }
            ];
          }
          return [...prev, {
            id: data.cid,
            role: 'assistant',
            content: data.text_fragment,
            timestamp: new Date()
          }];
        });
        break;
        
      case 'ai_complete':
        setIsTyping(false);
        break;
        
      case 'cards':
        setMessages(prev => [...prev, {
          id: `cards-${Date.now()}`,
          type: 'lawyer_cards',
          cards: data.cards,
          timestamp: new Date()
        }]);
        break;
        
      case 'suggestions':
        setMessages(prev => [...prev, {
          id: `suggestions-${Date.now()}`,
          type: 'suggestions',
          suggestions: data.suggestions,
          timestamp: new Date()
        }]);
        break;
    }
  };
  
  const sendMessage = useCallback((text) => {
    if (!ws || !isConnected) return;
    
    const messageId = `msg-${Date.now()}`;
    
    // Add user message to UI
    setMessages(prev => [...prev, {
      id: messageId,
      role: 'user',
      content: text,
      timestamp: new Date()
    }]);
    
    // Send to backend
    const message = this.wsUrl.includes('amazonaws.com')
      ? { action: 'sendMessage', data: { type: 'user_msg', text, cid: messageId } }
      : { type: 'user_msg', text, cid: messageId };
      
    ws.send(JSON.stringify(message));
  }, [ws, isConnected]);
  
  return {
    messages,
    sendMessage,
    isConnected,
    isTyping
  };
}

// components/ChatInterface.jsx
function ChatInterface() {
  const { messages, sendMessage, isConnected, isTyping } = useLoveAndLawChat();
  const [input, setInput] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && isConnected) {
      sendMessage(input);
      setInput('');
    }
  };
  
  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map(msg => (
          <Message key={msg.id} {...msg} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>
      
      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={!isConnected}
        />
        <button type="submit" disabled={!isConnected}>
          Send
        </button>
      </form>
    </div>
  );
}
```

### Lawyer Search Integration

```jsx
// services/lawyerService.js
class LawyerService {
  constructor(apiBase) {
    this.apiBase = apiBase;
  }
  
  async searchLawyers(criteria) {
    const response = await fetch(`${this.apiBase}/api/v1/match`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        facts: criteria,
        limit: 10
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to search lawyers');
    }
    
    return await response.json();
  }
  
  async getLawyerDetails(lawyerId) {
    const response = await fetch(
      `${this.apiBase}/api/v1/lawyers/${lawyerId}`
    );
    
    if (!response.ok) {
      throw new Error('Failed to get lawyer details');
    }
    
    return await response.json();
  }
}

// components/LawyerSearch.jsx
function LawyerSearch() {
  const [lawyers, setLawyers] = useState([]);
  const [loading, setLoading] = useState(false);
  const lawyerService = new LawyerService(config.apiBase);
  
  const handleSearch = async (criteria) => {
    setLoading(true);
    try {
      const { cards } = await lawyerService.searchLawyers(criteria);
      setLawyers(cards);
    } catch (error) {
      console.error('Search failed:', error);
      // Handle error
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <SearchForm onSubmit={handleSearch} />
      {loading && <LoadingSpinner />}
      <LawyerGrid lawyers={lawyers} />
    </div>
  );
}
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**:
   - Check if using correct protocol (ws:// for local, wss:// for production)
   - Verify API Gateway WebSocket route is configured
   - Check browser console for CORS errors

2. **CORS Errors**:
   - Frontend domain must be in backend CORS whitelist
   - Use proxy in development if needed

3. **Empty Responses**:
   - Check if Elasticsearch is running (for lawyer data)
   - Verify data is loaded in Elasticsearch

### Debug Mode

Enable debug mode to see additional metrics:
```javascript
// In development, metrics are automatically included
// Look for messages with type: 'metrics' in WebSocket responses
```

## Support

For issues or questions:
- Backend Issues: Create issue in backend repository
- API Changes: Check API documentation
- Production Issues: Contact DevOps team
- Security Concerns: Contact security team immediately