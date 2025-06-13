import httpx
import json
from typing import Dict, Any, Optional
from datetime import datetime
from jose import jwt, JWTError
from fastapi import HTTPException, status
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives import serialization
import base64

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ClerkAuth:
    def __init__(self, clerk_publishable_key: str):
        self.clerk_publishable_key = clerk_publishable_key
        self.clerk_secret_key = settings.clerk_secret_key if hasattr(settings, 'clerk_secret_key') else None
        
        # Use frontend API from settings if provided, otherwise extract from key
        if hasattr(settings, 'clerk_frontend_api') and settings.clerk_frontend_api:
            frontend_api = settings.clerk_frontend_api
        else:
            frontend_api = self._extract_frontend_api()
            
        self.jwks_url = f"https://{frontend_api}/.well-known/jwks.json"
        self._jwks_cache = None
        self._jwks_cache_time = None
        self.cache_duration = 3600  # 1 hour
        
    def _extract_frontend_api(self) -> str:
        """Extract frontend API from publishable key"""
        # Modern Clerk publishable keys encode the frontend API in base64
        # Format: pk_test_{base64_encoded_frontend_api}
        if not (self.clerk_publishable_key.startswith('pk_test_') or 
                self.clerk_publishable_key.startswith('pk_live_')):
            raise ValueError("Invalid Clerk publishable key format")
        
        try:
            # Extract the encoded part after pk_test_ or pk_live_
            key_parts = self.clerk_publishable_key.split('_', 2)
            if len(key_parts) < 3:
                raise ValueError("Invalid Clerk publishable key format")
            
            encoded_api = key_parts[2]
            
            # For newer Clerk keys, the frontend API might be base64 encoded
            # Try to decode it
            import base64
            try:
                # Add padding if needed
                padding = 4 - (len(encoded_api) % 4)
                if padding != 4:
                    encoded_api += '=' * padding
                
                decoded = base64.b64decode(encoded_api).decode('utf-8')
                # Remove any trailing special characters
                decoded = decoded.rstrip('$')
                # The decoded value might be the frontend API directly
                if decoded.endswith('.clerk.accounts.dev') or '.clerk.' in decoded:
                    return decoded
            except:
                pass
            
            # If base64 decoding didn't work, the key might contain the domain directly
            # Format could be: pk_test_friendly-termite-22.clerk.accounts.dev$
            # Remove any trailing $ or special characters
            domain = encoded_api.rstrip('$')
            
            # Check if it's already a full domain
            if domain.endswith('.clerk.accounts.dev'):
                return domain
            elif '.clerk.accounts.dev' in domain:
                # Extract the full domain
                return domain.split('$')[0] if '$' in domain else domain
            else:
                # Try to extract subdomain and construct the full domain
                # Format: friendly-termite-22 -> friendly-termite-22.clerk.accounts.dev
                subdomain = domain.split('.')[0]
                return f"{subdomain}.clerk.accounts.dev"
                
        except Exception as e:
            logger.error(f"Error extracting frontend API: {e}")
            raise ValueError(f"Could not extract frontend API from Clerk publishable key: {e}")
    
    async def get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Clerk"""
        # Check cache
        if self._jwks_cache and self._jwks_cache_time:
            if (datetime.utcnow() - self._jwks_cache_time).total_seconds() < self.cache_duration:
                return self._jwks_cache
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                jwks = response.json()
                
                # Cache the response
                self._jwks_cache = jwks
                self._jwks_cache_time = datetime.utcnow()
                
                return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Clerk: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch authentication keys"
            )
    
    def _decode_value(self, val: str) -> int:
        """Decode base64url encoded value to int"""
        # Add padding if needed
        padding = 4 - (len(val) % 4)
        if padding != 4:
            val += '=' * padding
        
        decoded = base64.urlsafe_b64decode(val)
        return int.from_bytes(decoded, 'big')
    
    def _get_rsa_public_key(self, jwk: Dict[str, Any]):
        """Convert JWK to RSA public key"""
        n = self._decode_value(jwk['n'])
        e = self._decode_value(jwk['e'])
        
        public_numbers = RSAPublicNumbers(e, n)
        public_key = public_numbers.public_key(default_backend())
        
        return public_key
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Clerk JWT token"""
        try:
            # First decode without verification to get the kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')
            
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
            
            # Get JWKS
            jwks = await self.get_jwks()
            
            # Find the key with matching kid
            key = None
            for jwk in jwks.get('keys', []):
                if jwk.get('kid') == kid:
                    key = jwk
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token key"
                )
            
            # Convert JWK to PEM
            public_key = self._get_rsa_public_key(key)
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Verify and decode the token
            payload = jwt.decode(
                token,
                pem,
                algorithms=['RS256'],
                options={"verify_aud": False}  # Clerk uses azp instead of aud
            )
            
            # Verify token is not expired
            if 'exp' in payload:
                exp = datetime.fromtimestamp(payload['exp'])
                if exp < datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired"
                    )
            
            return payload
            
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    def extract_user_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user data from Clerk JWT payload"""
        return {
            "user_id": payload.get("sub"),  # Clerk user ID
            "email": payload.get("email"),
            "email_verified": payload.get("email_verified", False),
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "full_name": payload.get("name"),
            "image_url": payload.get("image_url"),
            "role": payload.get("role", "user"),  # Default to user role
            "scopes": payload.get("scopes", ["read"]),  # Default scopes
            "session_id": payload.get("sid"),
            "organization_id": payload.get("org_id"),
            "organization_role": payload.get("org_role"),
        }