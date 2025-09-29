"""JWT token validation and Azure AD integration."""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import requests

import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
)

from mavik_common.errors import (
    JWTValidationError,
    AuthenticationError,
    AuthorizationError,
)

logger = logging.getLogger(__name__)


class JWTValidator:
    """JWT token validator with Azure AD integration."""
    
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        jwt_secret_key: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        azure_ad_cache_ttl: int = 3600,
    ):
        """Initialize JWT validator.
        
        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD client ID  
            client_secret: Azure AD client secret
            jwt_secret_key: Optional JWT signing key for custom tokens
            jwt_algorithm: JWT signing algorithm
            azure_ad_cache_ttl: Cache TTL for Azure AD keys in seconds
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.azure_ad_cache_ttl = azure_ad_cache_ttl
        
        # Azure AD endpoints
        self.azure_ad_base_url = f"https://login.microsoftonline.com/{tenant_id}"
        self.azure_ad_jwks_url = f"{self.azure_ad_base_url}/discovery/v2.0/keys"
        self.azure_ad_token_url = f"{self.azure_ad_base_url}/oauth2/v2.0/token"
        
        # Cache for Azure AD public keys
        self._azure_keys_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
    
    def validate_token(self, token: str, audience: Optional[str] = None) -> Dict[str, Any]:
        """Validate JWT token and return claims.
        
        Args:
            token: JWT token string
            audience: Expected audience (defaults to client_id)
            
        Returns:
            Decoded token claims
            
        Raises:
            JWTValidationError: If token validation fails
            AuthenticationError: If token is invalid or expired
        """
        try:
            # Remove Bearer prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Try to decode header to determine issuer
            unverified_header = jwt.get_unverified_header(token)
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            
            issuer = unverified_payload.get("iss", "")
            
            # Determine validation method based on issuer
            if "login.microsoftonline.com" in issuer:
                return self._validate_azure_ad_token(token, unverified_header, audience)
            elif self.jwt_secret_key:
                return self._validate_custom_token(token, audience)
            else:
                raise JWTValidationError("Cannot validate token: unknown issuer and no custom secret")
                
        except ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except InvalidSignatureError:
            raise AuthenticationError("Invalid token signature")
        except DecodeError:
            raise AuthenticationError("Token decode error")
        except InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise JWTValidationError(f"Token validation failed: {e}")
    
    def _validate_azure_ad_token(
        self, 
        token: str, 
        header: Dict[str, Any], 
        audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate Azure AD token using JWKS."""
        try:
            # Get Azure AD public keys
            public_keys = self._get_azure_ad_keys()
            
            # Find the key used to sign this token
            key_id = header.get("kid")
            if not key_id:
                raise JWTValidationError("Token header missing 'kid' field")
            
            public_key = None
            for key_data in public_keys.get("keys", []):
                if key_data.get("kid") == key_id:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
                    break
            
            if not public_key:
                raise JWTValidationError(f"Public key not found for kid: {key_id}")
            
            # Validate token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=audience or self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
            )
            
            logger.info(f"Successfully validated Azure AD token for user: {payload.get('preferred_username')}")
            return payload
            
        except Exception as e:
            logger.error(f"Azure AD token validation error: {e}")
            raise
    
    def _validate_custom_token(self, token: str, audience: Optional[str] = None) -> Dict[str, Any]:
        """Validate custom JWT token using secret key."""
        if not self.jwt_secret_key:
            raise JWTValidationError("JWT secret key not configured")
        
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm],
                audience=audience,
            )
            
            logger.info(f"Successfully validated custom token for user: {payload.get('sub')}")
            return payload
            
        except Exception as e:
            logger.error(f"Custom token validation error: {e}")
            raise
    
    def _get_azure_ad_keys(self) -> Dict[str, Any]:
        """Get Azure AD public keys with caching."""
        now = datetime.now(timezone.utc)
        
        # Check cache
        if (self._azure_keys_cache and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self.azure_ad_cache_ttl):
            return self._azure_keys_cache
        
        try:
            logger.debug(f"Fetching Azure AD keys from: {self.azure_ad_jwks_url}")
            
            response = requests.get(
                self.azure_ad_jwks_url,
                timeout=10,
                headers={"User-Agent": "Mavik-Authorizer/1.0"},
            )
            response.raise_for_status()
            
            keys_data = response.json()
            
            # Update cache
            self._azure_keys_cache = keys_data
            self._cache_timestamp = now
            
            logger.debug(f"Cached {len(keys_data.get('keys', []))} Azure AD keys")
            return keys_data
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Azure AD keys: {e}")
            raise JWTValidationError(f"Cannot fetch Azure AD keys: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Azure AD: {e}")
            raise JWTValidationError(f"Invalid Azure AD keys response: {e}")
    
    def create_custom_token(
        self,
        user_id: str,
        email: str,
        roles: List[str],
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_in_hours: int = 24,
    ) -> str:
        """Create a custom JWT token for development/testing.
        
        Args:
            user_id: User identifier
            email: User email
            roles: List of user roles
            additional_claims: Additional claims to include
            expires_in_hours: Token expiration in hours
            
        Returns:
            Signed JWT token
            
        Raises:
            JWTValidationError: If token creation fails
        """
        if not self.jwt_secret_key:
            raise JWTValidationError("JWT secret key not configured")
        
        try:
            now = datetime.now(timezone.utc)
            
            payload = {
                "sub": user_id,
                "email": email,
                "preferred_username": email,
                "roles": roles,
                "iat": now,
                "exp": now.timestamp() + (expires_in_hours * 3600),
                "iss": "mavik-authorizer",
                "aud": self.client_id,
            }
            
            if additional_claims:
                payload.update(additional_claims)
            
            token = jwt.encode(
                payload,
                self.jwt_secret_key,
                algorithm=self.jwt_algorithm,
            )
            
            logger.info(f"Created custom token for user: {email}")
            return token
            
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise JWTValidationError(f"Failed to create token: {e}")
    
    def get_user_info_from_azure(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Azure AD using access token.
        
        Args:
            access_token: Azure AD access token
            
        Returns:
            User information dictionary
            
        Raises:
            AuthenticationError: If user info retrieval fails
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers,
                timeout=10,
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid or expired access token")
            
            response.raise_for_status()
            user_info = response.json()
            
            logger.info(f"Retrieved user info for: {user_info.get('userPrincipalName')}")
            return user_info
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user info from Azure: {e}")
            raise AuthenticationError(f"Cannot retrieve user info: {e}")
    
    def refresh_token_cache(self) -> None:
        """Force refresh of Azure AD keys cache."""
        self._azure_keys_cache = None
        self._cache_timestamp = None
        logger.info("Azure AD keys cache cleared")