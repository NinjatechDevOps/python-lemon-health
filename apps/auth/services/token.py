from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import jwt, JWTError

from apps.core.config import settings

class TokenService:
    """Service for managing authentication tokens"""
    
    @staticmethod
    def create_access_token(subject: str, extra_data: Optional[Dict[str, Any]] = None) -> str:
        """Create JWT access token"""
        to_encode = {"sub": subject, "token_type": "access"}
        if extra_data:
            to_encode.update(extra_data)
            
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(subject: str) -> str:
        """Create JWT refresh token with longer expiration"""
        to_encode = {"sub": subject, "token_type": "refresh"}
        
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify a token and return its payload"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return {"valid": True, "payload": payload}
        except JWTError:
            return {"valid": False, "payload": None}
    
    @staticmethod
    def get_token_data(token: str) -> Optional[Dict[str, Any]]:
        """Get data from a token"""
        result = TokenService.verify_token(token)
        if result["valid"]:
            return result["payload"]
        return None

# Create an instance of the service
token_service = TokenService() 