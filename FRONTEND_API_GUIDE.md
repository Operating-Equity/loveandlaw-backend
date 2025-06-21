# Love & Law Frontend API Integration Guide

This guide provides comprehensive documentation for frontend engineers to integrate with the Love & Law backend APIs, including WebSocket connections, lawyer matching, and REST endpoints.

## Table of Contents
1. [Overview](#overview)
2. [WebSocket API](#websocket-api)
3. [REST API Endpoints](#rest-api-endpoints)
   - [Health Check](#1-health-check)
   - [Lawyer Endpoints](#2-lawyer-endpoints)
   - [User Profile](#3-user-profile)
   - [Conversation Management](#4-conversation-management)
   - [Lawyer CSV Upload](#5-lawyer-csv-upload-admin-only)
4. [Authentication](#authentication)
5. [Error Handling](#error-handling)
6. [Examples](#examples)

## Overview

The Love & Law backend provides:
- **WebSocket API** for real-time chat conversations
- **REST API** for lawyer search, profile management, and file uploads

Base URLs:
- Local Development: `http://localhost:8000`
- Production REST API: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
- Production WebSocket: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`

**Note**: The production URLs are AWS API Gateway endpoints that route to the ECS backend service. These use HTTPS/WSS for secure connections.

## WebSocket API

### Connection

```javascript
// Local Development
const ws = new WebSocket('ws://localhost:8000/ws');

// Production (use this for deployed frontend)
const ws = new WebSocket('wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production');
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

### 2. Lawyer Endpoints

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

#### GET `/api/v1/lawyers/{lawyer_id}`
Get detailed information about a specific lawyer.

Headers:
```
Authorization: Bearer <jwt-token>
```

Response:
```json
{
  "id": "lawyer-123",
  "name": "Jane Doe",
  "firm": "Doe Law Firm",
  "profile_summary": "I am a dedicated family law attorney with 15 years of experience helping clients navigate divorce and custody issues with compassion and expertise.",
  "city": "Chicago",
  "state": "IL",
  "location": {
    "lat": 41.8781,
    "lon": -87.6298
  },
  "practice_areas": ["Family Law", "Divorce", "Child Custody"],
  "specialties": [
    {
      "name": "Collaborative Divorce",
      "description": "A cooperative approach to divorce"
    },
    {
      "name": "High-Asset Divorce",
      "description": "Complex property division cases"
    }
  ],
  "education": [
    {
      "institution": "Northwestern University School of Law",
      "degree": "J.D.",
      "year": 2010
    }
  ],
  "professional_experience": "15 years specializing in family law with a focus on helping clients achieve amicable resolutions.",
  "years_of_experience": 15,
  "languages": ["English", "Spanish"],
  "payment_methods": ["Credit Card", "Cash", "Payment Plans"],
  "ratings": {
    "overall": 4.8,
    "communication": 4.9,
    "expertise": 4.7,
    "value": 4.6
  },
  "reviews": [
    {
      "author": "Client",
      "rating": 5,
      "text": "Jane made a difficult process much easier with her guidance."
    }
  ],
  "phone_numbers": ["(312) 555-1234"],
  "email": "jane@doelawfirm.com",
  "website": "https://doelawfirm.com",
  "awards": ["SuperLawyers 2022", "Best Family Lawyers in Chicago 2023"],
  "associations": ["Illinois State Bar Association", "American Bar Association"],
  "fee_structure": {
    "free_consultation": true,
    "consultation_length": "60 minutes",
    "hourly_rate": "$300-$350"
  },
  "budget_range": "$$",
  "active": true
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
    "name": "John Doe",
    "email": "john.doe@example.com",
    "preferred_avatar": "avatar-url-or-id",
    "saved_lawyers": ["lawyer-123", "lawyer-456"],
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

#### PUT `/api/v1/profile/{user_id}`
Update user profile information.

Headers:
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

Request Body (all fields optional):
```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "preferred_avatar": "avatar-url-or-id",
  "saved_lawyers": ["lawyer-123", "lawyer-456"],
  "legal_situation": {
    "type": "divorce",
    "stage": "attorney_contacted"
  },
  "current_goals": ["understand_process", "file_paperwork"],
  "preferences": {
    "communication_style": "formal",
    "notification_preferences": {
      "email": true,
      "sms": false,
      "in_app": true
    }
  }
}
```

Response:
```json
{
  "profile": {
    // Same structure as GET response
  }
}
```

### 4. Conversation Management

#### GET `/api/v1/conversations`
Get all chat histories for the authenticated user.

Headers:
```
Authorization: Bearer <jwt-token>
```

Query Parameters:
- `limit` (optional): Number of conversations to return (default: 20)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Filter by conversation status (active, archived)

Response:
```json
{
  "conversations": [
    {
      "conversation_id": "conv-uuid-1",
      "user_id": "user-uuid",
      "created_at": "2025-06-10T12:00:00Z",
      "updated_at": "2025-06-10T13:00:00Z",
      "status": "active",
      "last_message": "I need help with custody arrangements",
      "summary": "User seeking help with child custody during divorce",
      "message_count": 15,
      "average_distress_score": 4.5,
      "legal_topics": ["divorce", "custody"]
    },
    {
      "conversation_id": "conv-uuid-2",
      "user_id": "user-uuid",
      "created_at": "2025-06-09T10:00:00Z",
      "updated_at": "2025-06-09T11:30:00Z",
      "status": "archived",
      "last_message": "Thank you for your help",
      "summary": "User received lawyer recommendations for divorce case",
      "message_count": 8,
      "average_distress_score": 3.2,
      "legal_topics": ["divorce"]
    }
  ],
  "total": 2,
  "limit": 20,
  "offset": 0
}
```

#### GET `/api/v1/conversations/{conversation_id}/messages`
Retrieve all messages for a specific conversation.

Headers:
```
Authorization: Bearer <jwt-token>
```

Query Parameters:
- `limit` (optional): Number of messages to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `order` (optional): Sort order - "asc" or "desc" (default: "asc")

Response:
```json
{
  "conversation_id": "conv-uuid",
  "messages": [
    {
      "message_id": "msg-uuid-1",
      "turn_id": "turn-uuid-1",
      "timestamp": "2025-06-10T12:00:00Z",
      "role": "user",
      "content": "I need help with a divorce in Chicago",
      "redacted": false
    },
    {
      "message_id": "msg-uuid-2",
      "turn_id": "turn-uuid-1",
      "timestamp": "2025-06-10T12:00:05Z",
      "role": "assistant",
      "content": "I understand you're going through a difficult time and need help with a divorce in Chicago. I'm here to support you through this process...",
      "metadata": {
        "sentiment": "neutral",
        "distress_score": 4.5,
        "engagement_level": 7.0,
        "legal_intent": ["divorce"]
      }
    },
    {
      "message_id": "msg-uuid-3",
      "turn_id": "turn-uuid-1",
      "timestamp": "2025-06-10T12:00:10Z",
      "role": "system",
      "content": "lawyer_cards",
      "cards": [
        {
          "id": "lawyer-123",
          "name": "Jane Doe",
          "firm": "Doe Law Firm",
          "match_score": 0.92
        }
      ]
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

#### POST `/api/v1/conversations`
Initiate a new conversation.

Headers:
```
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

Request Body (optional):
```json
{
  "initial_message": "I need help with a family law matter",
  "metadata": {
    "source": "website",
    "referrer": "google"
  }
}
```

Response:
```json
{
  "conversation_id": "conv-uuid-new",
  "user_id": "user-uuid",
  "created_at": "2025-06-10T14:00:00Z",
  "status": "active",
  "websocket_url": "wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production",
  "auth_token": "temporary-websocket-token"
}
```

Note: After creating a conversation, connect to the WebSocket using the provided URL and authenticate with the conversation_id.

### 5. Lawyer CSV Upload (Admin Only)

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
// For production, use the AWS API Gateway WebSocket endpoint
const wsUrl = process.env.NODE_ENV === 'production' 
  ? 'wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production'
  : 'ws://localhost:8000/ws';

const ws = new WebSocket(wsUrl);
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
// Set base URL based on environment
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production'
  : 'http://localhost:8000';

// Search for lawyers
async function searchLawyers() {
  const response = await fetch(`${API_BASE_URL}/api/v1/match`, {
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

// Get lawyer details
async function getLawyerDetails(lawyerId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/lawyers/${lawyerId}`, {
    headers: {
      'Authorization': `Bearer ${authToken}`
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch lawyer details: ${response.status}`);
  }
  
  return response.json();
}

// Get user profile
async function getUserProfile(userId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/profile/${userId}`, {
    headers: {
      'Authorization': `Bearer ${authToken}`
    }
  });
  
  return response.json();
}

// Health check
async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);
  return response.json();
}
```

## Important Notes

1. **Lawyer Matching**: The system uses progressive information gathering. Initial messages may not return lawyer matches until enough information is collected (location, legal issue, etc.).

2. **Crisis Handling**: If a user's distress score is >= 7, the system prioritizes emotional support over lawyer matching.

3. **Legal Specialists**: The system routes conversations to appropriate legal specialists based on the detected legal intent (divorce, custody, adoption, etc.).

4. **PII Protection**: All user messages are automatically scanned and redacted for personally identifiable information (PII) before processing.

5. **Rate Limiting**: WebSocket connections are limited to prevent abuse. Implement exponential backoff for reconnections.

## Lawyer Details Integration

When integrating the lawyer details endpoint into your frontend, follow these best practices:

### When to Fetch Lawyer Details

1. **After Initial Matching**: Fetch detailed profiles when a user clicks on a lawyer card from the matching results
2. **For Comparison Views**: When displaying lawyer comparison features
3. **Before Scheduling Consultations**: Fetch full details before a user schedules a consultation

### Implementation Example

```javascript
// Component for displaying lawyer details
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { API_BASE_URL } from '../config';

function LawyerProfile() {
  const [lawyer, setLawyer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { lawyerId } = useParams();
  
  useEffect(() => {
    const fetchLawyerDetails = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/v1/lawyers/${lawyerId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        if (!response.ok) {
          throw new Error(`Failed to fetch lawyer details: ${response.status}`);
        }
        
        const data = await response.json();
        setLawyer(data);
      } catch (err) {
        setError(err.message);
        console.error('Error fetching lawyer details:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchLawyerDetails();
  }, [lawyerId]);
  
  if (loading) return <div className="loading-spinner">Loading...</div>;
  if (error) return <div className="error-message">Error: {error}</div>;
  if (!lawyer) return <div>No lawyer found</div>;
  
  return (
    <div className="lawyer-profile">
      <header>
        <h1>{lawyer.name}</h1>
        <h2>{lawyer.firm}</h2>
        <div className="rating">
          <span className="stars">{renderStars(lawyer.ratings.overall)}</span>
          <span className="review-count">({lawyer.reviews.length} reviews)</span>
        </div>
      </header>
      
      <div className="contact-info">
        <p>Phone: {lawyer.phone_numbers[0]}</p>
        <p>Email: {lawyer.email}</p>
        <a href={lawyer.website} target="_blank" rel="noopener noreferrer">Visit Website</a>
      </div>
      
      <div className="profile-summary">
        <h3>About</h3>
        <p>{lawyer.profile_summary}</p>
      </div>
      
      <div className="specialties">
        <h3>Specialties</h3>
        <ul>
          {lawyer.specialties.map((specialty, index) => (
            <li key={index}>
              <strong>{specialty.name}</strong>: {specialty.description}
            </li>
          ))}
        </ul>
      </div>
      
      <div className="education">
        <h3>Education</h3>
        <ul>
          {lawyer.education.map((edu, index) => (
            <li key={index}>
              {edu.degree} from {edu.institution}, {edu.year}
            </li>
          ))}
        </ul>
      </div>
      
      <div className="reviews">
        <h3>Client Reviews</h3>
        {lawyer.reviews.map((review, index) => (
          <div key={index} className="review">
            <div className="review-rating">{renderStars(review.rating)}</div>
            <p className="review-text">{review.text}</p>
            <p className="review-author">— {review.author}</p>
          </div>
        ))}
      </div>
      
      <div className="cta">
        <button className="schedule-consultation">
          Schedule Consultation
        </button>
      </div>
    </div>
  );
}

function renderStars(rating) {
  const fullStars = Math.floor(rating);
  const halfStar = rating % 1 >= 0.5;
  const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);
  
  return (
    <>
      {'★'.repeat(fullStars)}
      {halfStar ? '½' : ''}
      {'☆'.repeat(emptyStars)}
    </>
  );
}

export default LawyerProfile;
```

### Error Handling and Fallbacks

Always implement proper error handling for lawyer detail fetching:

1. **Network Errors**: Display user-friendly error messages with retry options
2. **404 Not Found**: Provide navigation back to search results or suggest similar lawyers
3. **Auth Errors**: Redirect to login if token is expired

### Caching Strategy

Consider implementing a caching strategy for lawyer details:

```javascript
// Simple lawyer profile cache
const lawyerCache = new Map();

export async function getLawyerDetails(lawyerId) {
  // Check cache first
  if (lawyerCache.has(lawyerId)) {
    const cachedData = lawyerCache.get(lawyerId);
    const cacheAge = Date.now() - cachedData.timestamp;
    
    // Use cache if less than 5 minutes old
    if (cacheAge < 5 * 60 * 1000) {
      return cachedData.data;
    }
  }
  
  // Fetch fresh data
  const response = await fetch(`${API_BASE_URL}/api/v1/lawyers/${lawyerId}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
    }
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch lawyer details: ${response.status}`);
  }
  
  const data = await response.json();
  
  // Update cache
  lawyerCache.set(lawyerId, {
    data,
    timestamp: Date.now()
  });
  
  return data;
}
```

## Production Configuration

### Environment Variables for Frontend
```javascript
// .env.production
REACT_APP_API_BASE_URL=https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production
REACT_APP_WS_URL=wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production

// .env.development
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
```

### CORS Configuration
The production backend is configured to accept requests from your frontend domain. Make sure your frontend domain is whitelisted in the backend CORS settings.

### SSL/TLS
All production connections use SSL/TLS encryption:
- REST API: HTTPS
- WebSocket: WSS (WebSocket Secure)

## Support

For questions or issues:
- GitHub Issues: https://github.com/loveandlaw/backend/issues
- Technical Documentation: See ARCHITECTURE.md
- API Updates: Check CHANGELOG.md
- Deployment Guide: See DEPLOYMENT_GUIDE.md