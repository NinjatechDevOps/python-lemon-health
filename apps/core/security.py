from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from apps.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(subject: str, extra_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Create JWT access token
    """
    to_encode = {"sub": subject}
    if extra_data:
        to_encode.update(extra_data)
        
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """
    Create JWT refresh token with longer expiration
    """
    to_encode = {"sub": subject, "token_type": "refresh"}
    
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a token and return its payload
    
    Raises:
        JWTError: If token is invalid or blacklisted
    """
    # First decode the token to validate it
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    # Check if token is blacklisted
    from apps.core.redis import is_token_blacklisted
    if await is_token_blacklisted(token):
        raise JWTError("Token has been invalidated")
    
    return payload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed password
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password
    """
    return pwd_context.hash(password) 