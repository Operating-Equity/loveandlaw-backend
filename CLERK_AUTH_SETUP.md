# Clerk Authentication Setup Guide

## Overview

The LoveAndLaw backend now supports Clerk authentication for JWT verification. This allows your frontend application using Clerk to authenticate with the backend API.

## Current Status

✅ **Clerk authentication module implemented** (`src/api/clerk_auth.py`)
✅ **Authentication middleware updated** to support both Clerk and standard JWT
✅ **Environment configuration added** for Clerk settings
✅ **Fallback to standard JWT** if Clerk authentication fails

## Configuration Steps

### 1. Update Environment Variables

Add the following to your `.env` file:

```env
# Enable Clerk Authentication
USE_CLERK_AUTH=True

# Your Clerk Publishable Key (from Clerk Dashboard)
CLERK_PUBLISHABLE_KEY=pk_test_your-key-here

# Your Clerk Secret Key (from Clerk Dashboard) 
CLERK_SECRET_KEY=sk_test_your-secret-key-here

# Your Clerk Frontend API domain (from Clerk Dashboard > API Keys)
# This is required for JWT verification
CLERK_FRONTEND_API=your-app.clerk.accounts.dev
```

### 2. Get Your Clerk Configuration

1. Log in to your [Clerk Dashboard](https://dashboard.clerk.com)
2. Navigate to **API Keys**
3. Copy the following values:
   - **Publishable Key** (starts with `pk_test_` or `pk_live_`)
   - **Secret Key** (starts with `sk_test_` or `sk_live_`)
   - **Frontend API** domain (e.g., `your-app.clerk.accounts.dev`)

### 3. Update Your Frontend

Ensure your frontend sends the Clerk JWT token in the Authorization header:

```javascript
// Example with fetch
const response = await fetch('https://your-api.com/api/v1/profile/user_id', {
  headers: {
    'Authorization': `Bearer ${await clerk.session.getToken()}`,
    'Content-Type': 'application/json'
  }
});

// Example with axios
const token = await clerk.session.getToken();
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
```

## How It Works

1. When a request comes in with a JWT token, the system first checks if Clerk authentication is enabled
2. If enabled, it attempts to verify the token using Clerk's JWKS endpoint
3. If Clerk verification succeeds, it extracts user information from the token
4. If Clerk verification fails, it falls back to standard JWT verification
5. In development mode with `DEBUG=True`, authentication can be bypassed

## User Data Extraction

When using Clerk authentication, the following user data is extracted from the JWT:

```python
{
    "user_id": "user_xxx",  # Clerk user ID
    "email": "user@example.com",
    "email_verified": true,
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "image_url": "https://...",
    "role": "user",  # Default role
    "scopes": ["read"],  # Default scopes
    "session_id": "sess_xxx",
    "organization_id": "org_xxx",  # If using organizations
    "organization_role": "member"  # If using organizations
}
```

## Testing

1. **Start the backend server**:
   ```bash
   source venv/bin/activate
   python -m uvicorn src.api.main:app --reload --port 8000
   ```

2. **Test without authentication** (development mode):
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. **Test with Clerk JWT**:
   ```bash
   # Get a token from your Clerk frontend first
   curl -H "Authorization: Bearer YOUR_CLERK_JWT_TOKEN" \
        http://localhost:8000/api/v1/profile/your_user_id
   ```

## Troubleshooting

### 401 Unauthorized Error

1. **Check Clerk configuration**:
   - Ensure `USE_CLERK_AUTH=True` in `.env`
   - Verify all Clerk keys are correctly set
   - Confirm `CLERK_FRONTEND_API` matches your Clerk dashboard

2. **Verify token format**:
   - Token should be sent as `Bearer <token>`
   - Token should be a valid Clerk JWT (not expired)

3. **Check JWKS endpoint**:
   ```bash
   # Test if JWKS is accessible
   curl https://your-app.clerk.accounts.dev/.well-known/jwks.json
   ```

### Invalid Host Error

If you see "Invalid host" error when fetching JWKS:
- Double-check your `CLERK_FRONTEND_API` value
- Ensure it matches exactly what's shown in Clerk Dashboard
- Remove any trailing slashes or special characters

### Development Mode

For quick testing without authentication:
- Set `ENVIRONMENT=development` and `DEBUG=True`
- Requests without tokens will use a default dev user

## Security Notes

1. **Never commit real Clerk keys** to version control
2. **Use environment variables** for all sensitive configuration
3. **Enable CORS** only for trusted origins in production
4. **Regularly rotate** your Clerk secret keys

## Next Steps

1. Update your frontend to send Clerk JWT tokens
2. Test the authentication flow end-to-end
3. Configure role-based access control if needed
4. Set up proper error handling for authentication failures