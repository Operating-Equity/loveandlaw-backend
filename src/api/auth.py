from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

# Lazy load Clerk auth if enabled
_clerk_auth = None

def get_clerk_auth():
    global _clerk_auth
    if settings.use_clerk_auth and settings.clerk_publishable_key:
        if _clerk_auth is None:
            from src.api.clerk_auth import ClerkAuth
            _clerk_auth = ClerkAuth(settings.clerk_publishable_key)
        return _clerk_auth
    return None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    # Development mode bypass
    if settings.environment == "development" and settings.debug:
        if not credentials:
            logger.warning("Auth bypassed in development mode")
            return {
                "user_id": "dev_user_123",
                "role": "admin",
                "scopes": ["read", "write", "admin"]
            }
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Check if we should use Clerk authentication
    clerk_auth = get_clerk_auth()
    if clerk_auth:
        try:
            # Verify token with Clerk
            payload = await clerk_auth.verify_token(token)
            user_data = clerk_auth.extract_user_data(payload)
            
            if not user_data.get("user_id"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.info(f"Clerk auth successful for user: {user_data['user_id']}")
            return user_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Clerk authentication error: {e}")
            # Fall back to standard JWT if Clerk fails
            logger.warning("Falling back to standard JWT authentication")
    
    # Standard JWT authentication
    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # In production, would fetch user from database
        return {
            "user_id": user_id,
            "role": payload.get("role", "user"),
            "scopes": payload.get("scopes", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None