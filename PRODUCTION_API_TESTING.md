# Production API Testing Guide

## Deployment Status ✅

The LoveAndLaw backend has been successfully deployed to AWS. Here are the production endpoints:

- **REST API**: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
- **WebSocket**: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`

## Authentication

Most API endpoints require JWT authentication. In production, JWT tokens are validated using a secret key stored in AWS Secrets Manager.

### Getting a Valid JWT Token

For production testing, you have several options:

1. **Use the Authentication Endpoint** (when implemented):
   ```bash
   POST /api/v1/auth/login
   {
     "username": "your-username",
     "password": "your-password"
   }
   ```

2. **Generate a Test Token** (for development):
   ```python
   from jose import jwt
   from datetime import datetime, timedelta
   
   secret_key = "your-jwt-secret-from-aws-secrets"
   payload = {
       "sub": "user-id",
       "role": "user",  # or "admin"
       "exp": datetime.utcnow() + timedelta(hours=1)
   }
   token = jwt.encode(payload, secret_key, algorithm="HS256")
   ```

3. **Use AWS Secrets Manager** to retrieve the JWT secret:
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id loveandlaw-production-secrets \
     --query SecretString \
     --output text | jq -r '.JWT_SECRET_KEY'
   ```

## Testing Endpoints

### 1. Health Check (No Auth Required)

```bash
curl https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/health
```

Expected Response:
```json
{
  "status": "healthy",
  "service": "Love & Law Backend",
  "version": "1.0.0",
  "environment": "production"
}
```

### 2. Create Lawyer (Admin Only)

```bash
curl -X POST https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/lawyers \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith, Esq.",
    "firm": "Smith Family Law",
    "city": "Philadelphia",
    "state": "PA",
    "zip": "19104",
    "practice_areas": ["Divorce", "Child Custody"],
    "budget_range": "$$",
    "active": true
  }'
```

### 3. Match Lawyers

```bash
curl -X POST https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/match \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "facts": {
      "zip": "19104",
      "practice_areas": ["divorce"],
      "budget_range": "$$"
    },
    "limit": 5
  }'
```

### 4. Get Conversations

```bash
curl https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production/api/v1/conversations \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. WebSocket Connection

```javascript
// JavaScript example
const ws = new WebSocket('wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production');

ws.onopen = () => {
  console.log('Connected');
  
  // Send authentication
  ws.send(JSON.stringify({
    action: "sendMessage",
    data: {
      type: "auth",
      user_id: "your-user-id",
      token: "YOUR_JWT_TOKEN"
    }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  // Send a message after auth
  if (data.type === 'auth_success') {
    ws.send(JSON.stringify({
      action: "sendMessage",
      data: {
        type: "user_msg",
        cid: "unique-id",
        text: "I need help with a divorce"
      }
    }));
  }
};
```

## Using Postman

1. Import the collection: `loveandlaw-postman-collection.json`
2. Set environment variables:
   - `base_url`: `https://j73lfhja1d.execute-api.us-east-1.amazonaws.com/production`
   - `ws_url`: `wss://vduwddf9yg.execute-api.us-east-1.amazonaws.com/production`
   - `auth_token`: Your JWT token

## Common Issues

### 401 Unauthorized
- **Cause**: Missing or invalid JWT token
- **Solution**: Ensure you're including a valid `Authorization: Bearer TOKEN` header

### 403 Forbidden
- **Cause**: Insufficient permissions (e.g., trying to create a lawyer without admin role)
- **Solution**: Use a token with appropriate role/permissions

### WebSocket Connection Issues
- **Cause**: The WebSocket expects specific message format with `action` field
- **Solution**: Always wrap messages in the correct format:
  ```json
  {
    "action": "sendMessage",
    "data": {
      "type": "user_msg",
      "cid": "unique-id",
      "text": "Your message"
    }
  }
  ```

## Monitoring

- **CloudWatch Logs**: Check ECS task logs for errors
- **API Gateway Logs**: Monitor request/response logs
- **ECS Console**: View task health and metrics

## Next Steps

1. Implement proper user registration/login endpoints
2. Set up API key management for different clients
3. Configure rate limiting and throttling
4. Add comprehensive logging and monitoring
5. Set up automated health checks and alerts