import redis
from datetime import datetime, timedelta
from typing import Optional

from apps.core.config import settings

# Create Redis connection pool
redis_client = redis.from_url(settings.REDIS_URL)

# Prefix for blacklisted tokens
TOKEN_BLACKLIST_PREFIX = "token:blacklist:"


async def add_token_to_blacklist(token: str, expires_delta: Optional[timedelta] = None) -> None:
    """
    Add a token to the blacklist with expiration time
    
    Args:
        token: The token to blacklist
        expires_delta: Optional expiration time delta, if not provided will use default
    """
    # Calculate expiration time (in seconds)
    if expires_delta:
        expire_seconds = int(expires_delta.total_seconds())
    else:
        # Default to 24 hours if no expiration provided
        expire_seconds = 24 * 60 * 60
    
    # Add token to blacklist with expiration
    redis_client.setex(f"{TOKEN_BLACKLIST_PREFIX}{token}", expire_seconds, "1")


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted
    
    Args:
        token: The token to check
        
    Returns:
        bool: True if token is blacklisted, False otherwise
    """
    return bool(redis_client.exists(f"{TOKEN_BLACKLIST_PREFIX}{token}")) 