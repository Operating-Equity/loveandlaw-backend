# Clerk Integration Guide for User Profiles

## Overview

The backend is already set up to receive and store email addresses from Clerk. The frontend just needs to pass the email when creating or updating user profiles.

## API Endpoints

### 1. Update User Profile with Email

**Endpoint**: `PUT /api/v1/profile/{user_id}`

**Request Body**:
```json
{
  "email": "user@example.com",  // From Clerk
  "name": "John Doe",           // Optional, from Clerk or user input
  "preferred_avatar": "avatar1", // Optional
  "legal_situation": {},        // Optional
  "current_goals": [],          // Optional
  "preferences": {}             // Optional
}
```

**Example with Clerk data**:
```javascript
// Frontend code example
const updateProfileWithClerkData = async (userId, clerkUser) => {
  const response = await fetch(`${API_URL}/api/v1/profile/${userId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      email: clerkUser.emailAddresses[0]?.emailAddress,
      name: clerkUser.fullName || clerkUser.firstName + ' ' + clerkUser.lastName
    })
  });
  
  return await response.json();
};
```

### 2. Get User Profile

**Endpoint**: `GET /api/v1/profile/{user_id}`

**Response**:
```json
{
  "profile": {
    "user_id": "user-123",
    "email": "user@example.com",  // Will be null if not set
    "name": "John Doe",
    "created_at": "2024-01-25T10:00:00Z",
    "updated_at": "2024-01-25T10:00:00Z",
    "saved_lawyers": ["lawyer-1", "lawyer-2"],
    "legal_situation": {},
    "milestones_completed": [],
    "preferences": {
      "communication_style": "empathetic",
      "language": "en",
      "timezone": "UTC"
    }
  }
}
```

## Integration Steps

### 1. On User Login/Signup (via Clerk)

When a user logs in or signs up through Clerk, immediately update their profile:

```javascript
// After successful Clerk authentication
const onClerkAuth = async (clerkUser) => {
  // Update backend profile with Clerk data
  await updateProfileWithClerkData(clerkUser.id, clerkUser);
};
```

### 2. Profile Page

When displaying the user profile, the email will now be available:

```javascript
const fetchUserProfile = async (userId) => {
  const response = await fetch(`${API_URL}/api/v1/profile/${userId}`, {
    headers: {
      'Authorization': `Bearer ${authToken}`
    }
  });
  
  const data = await response.json();
  // data.profile.email will contain the email from Clerk
  return data.profile;
};
```

### 3. Handling Missing Emails

If email is null in the response, it means the profile hasn't been updated with Clerk data yet:

```javascript
if (!profile.email && clerkUser.emailAddresses[0]) {
  // Update profile with email from Clerk
  await updateProfileWithClerkData(userId, clerkUser);
}
```

## Important Notes

1. **Email is Optional**: The backend doesn't require email, so profiles can exist without it
2. **Privacy**: Email is only visible to the profile owner or admin users
3. **No Password Storage**: The backend doesn't store passwords - authentication is handled by Clerk
4. **Idempotent Updates**: You can safely call the update endpoint multiple times with the same data

## Testing

You can test the integration using curl:

```bash
# Update profile with email
curl -X PUT http://localhost:8000/api/v1/profile/test-user-123 \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test User"}'

# Get profile to verify
curl http://localhost:8000/api/v1/profile/test-user-123
```

## Error Handling

The API will return appropriate HTTP status codes:
- 200: Success
- 403: Unauthorized (user trying to access another user's profile)
- 404: Profile not found
- 500: Server error

Handle these appropriately in your frontend code.