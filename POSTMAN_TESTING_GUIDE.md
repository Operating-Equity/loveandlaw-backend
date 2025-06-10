# LoveAndLaw API - Postman Testing Guide

## Quick Start

1. **Import the Collection**
   - Open Postman
   - Click "Import" → Select `loveandlaw-postman-collection.json`
   - The collection will appear in your workspace

2. **Configure Environment**
   - The collection includes pre-configured variables:
     - `base_url`: Production REST API endpoint
     - `ws_url`: Production WebSocket endpoint
     - `jwt_token`: Add your authentication token here (if needed)

## API Endpoints Overview

### 🟢 Health Checks (No Auth Required)
- **GET /** - Basic service status
- **GET /health** - AWS health check
- **GET /api/v1/health** - Detailed health with database status

### 💬 Primary Feature: WebSocket Chat
- **wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production**
- **IMPORTANT**: Lawyer matching happens automatically during chat!

### 🔐 Optional/Secondary Features (Auth Required)
- **POST /api/v1/match** - Standalone lawyer search (optional - matching happens automatically in chat)
- **GET /api/v1/profile/{user_id}** - Get user profile

### 🛡️ Admin Only
- **POST /api/v1/lawyers/upload** - Upload lawyer CSV data

## Testing Workflow

### 1. Test Health Endpoints First
```bash
# These should work without authentication
GET https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/
GET https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/health
GET https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Love & Law Backend",
  "version": "1.0.0",
  "environment": "production"
}
```

### 2. Test WebSocket Chat (Primary Feature)

**IMPORTANT**: Lawyer matching happens automatically during chat conversations!

Connect to WebSocket and send messages - lawyers will be matched automatically when:
- User provides location (ZIP code)
- Legal needs are identified
- User mentions "lawyer", "attorney", "legal help"
- User is not in crisis

**Example conversation that triggers lawyer matching**:
```json
{
  "type": "user_msg",
  "cid": "msg-001",
  "text": "I need a divorce lawyer in San Francisco 94105"
}
```

**You'll receive lawyer cards automatically**:
```json
{
  "type": "cards",
  "cid": "msg-001",
  "cards": [/* lawyer recommendations */]
}
```

### 3. Test Standalone Lawyer Search (Optional)

**Note**: This endpoint is optional. Use it only for:
- Building a "Find a Lawyer" page
- Quick searches outside of chat
- Testing lawyer matching independently

**Endpoint**: `POST /api/v1/match`

**Sample Request**:
```json
{
  "facts": {
    "zip": "94105",
    "practice_areas": ["divorce", "child_custody"],
    "budget_range": "$$",
    "search_text": "experienced divorce lawyer"
  },
  "limit": 5
}
```

**Practice Areas** (use any combination):
- `divorce`
- `child_custody`
- `child_support`
- `property_division`
- `spousal_support`
- `domestic_violence`
- `adoption`
- `guardianship`
- `paternity`
- `juvenile`
- `restraining_orders`

**Budget Ranges**:
- `$` - Low budget
- `$$` - Medium budget
- `$$$` - High budget

### 4. Test User Profile

**Endpoint**: `GET /api/v1/profile/{user_id}`

Replace `{user_id}` with actual user ID (e.g., `test-user-123`)

### 5. WebSocket Testing in Postman

#### Prerequisites
- **Postman v8.5 or higher** (required for WebSocket support)

#### How to Test WebSocket
1. **Create WebSocket Request**
   - Click "New" → "WebSocket Request" (not regular HTTP request)
   - Or use the imported collection's "WebSocket Connection" request

2. **Connect**
   - URL: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`
   - Click "Connect"
   - You'll see: `{"type": "connection_established", "message": "Connected to Love & Law chat"}`

3. **Send Messages**
   - Type JSON messages in the message composer
   - Click "Send" or press Enter
   - Messages appear in the Messages tab

#### Sample WebSocket Flow:

1. **Connect and Authenticate** (optional in debug mode):
```json
{
  "type": "auth",
  "user_id": "test-user-123",
  "conversation_id": "conv-456"
}
```

2. **Send User Message**:
```json
{
  "type": "user_msg",
  "cid": "msg-001",
  "text": "I need help with child custody arrangements"
}
```

3. **Expected Responses**:
- `message_received` - Acknowledgment
- `ai_chunk` - Streaming AI response parts
- `ai_complete` - Response finished
- **`cards` - Lawyer recommendations (sent AUTOMATICALLY when appropriate)**
- `suggestions` - Suggested follow-up questions
- `reflection` - Emotional/journey insights

4. **Keep Connection Alive**:
```json
{
  "type": "heartbeat"
}
```

## Common Test Scenarios

### ⚠️ Key Point: Lawyer Matching is Automatic!
In all scenarios below, lawyer recommendations will be sent automatically via WebSocket when appropriate. You don't need to call the REST endpoint.

### Scenario 1: Divorce Consultation
```json
{
  "type": "user_msg",
  "cid": "msg-001",
  "text": "I'm thinking about getting divorced and don't know where to start"
}
```

### Scenario 2: Urgent Safety Issue
```json
{
  "type": "user_msg",
  "cid": "msg-002",
  "text": "My spouse is threatening me and I'm scared"
}
```
*Note: This triggers SafetyAgent for immediate crisis response*

### Scenario 3: Complex Custody Case
```json
{
  "type": "user_msg",
  "cid": "msg-003",
  "text": "My ex wants to move to another state with our children. I live in ZIP 94105."
}
```
*Note: Providing ZIP code will trigger automatic lawyer matching*

### Scenario 4: Financial Questions
```json
{
  "type": "user_msg",
  "cid": "msg-004",
  "text": "How is property divided in California divorces?"
}
```

## Authentication Notes

- **Development Mode**: Currently, the API is in debug mode with authentication bypassed
- **Production**: When enabled, add JWT token to the Authorization header:
  ```
  Authorization: Bearer <your-jwt-token>
  ```

## Troubleshooting

### Connection Issues
1. Check if the service is healthy using health endpoints
2. Verify WebSocket URL is correct
3. Ensure you're sending proper JSON format

### No Lawyer Cards Received in Chat
1. Make sure you provided a ZIP code in the conversation
2. Ensure the conversation has identified legal needs
3. Try mentioning "lawyer" or "attorney" explicitly
4. Check if user is in crisis mode (automatic matching disabled)

### Using REST Endpoint (if needed)
1. Verify ZIP code is valid
2. Check practice areas are from the allowed list
3. Try broader search terms

### WebSocket Disconnects
1. Implement heartbeat every 25 seconds
2. Handle reconnection logic in your client
3. Check for error messages in responses

## Rate Limits

- REST API: No current rate limits configured
- WebSocket: One connection per user
- Heartbeat required every 30 seconds

## Support

For issues or questions:
- Check the health endpoints first
- Review CloudWatch logs (if you have access)
- Contact the backend team with correlation IDs from responses

## Example Frontend Integration

### Primary Method: Handle Lawyer Cards via WebSocket

```javascript
// Main integration - lawyers matched automatically during chat
class LoveAndLawChat {
  handleMessage(data) {
    switch(data.type) {
      case 'ai_chunk':
        this.appendAIResponse(data.text);
        break;
        
      case 'cards':
        // Lawyers matched automatically!
        this.displayLawyerCards(data.cards);
        break;
        
      case 'suggestions':
        this.showSuggestions(data.questions);
        break;
    }
  }
  
  displayLawyerCards(cards) {
    // Display lawyer recommendations in your UI
    cards.forEach(lawyer => {
      console.log(`${lawyer.name} - ${lawyer.firm}`);
      console.log(`Match Score: ${lawyer.match_score}`);
      console.log(`Specialties: ${lawyer.practice_areas.join(', ')}`);
    });
  }
}
```

### Optional Method: Standalone Lawyer Search

```javascript
// Only if you need a separate "Find a Lawyer" page
async function searchLawyers(criteria) {
  const response = await fetch('https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/match', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // 'Authorization': 'Bearer ' + token // When auth is enabled
    },
    body: JSON.stringify({
      facts: criteria,
      limit: 5
    })
  });
  
  return await response.json();
}
```