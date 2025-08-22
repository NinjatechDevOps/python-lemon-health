from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.db import get_db
from apps.core.config import settings
from apps.core.security import verify_token
from apps.auth.models import User
from apps.auth.utils import api_error_response
import logging
from apps.core.logging_config import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current user from the token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"success": False, "message": "Could not validate credentials", "data": {}}
    )
    
    try:
        payload = await verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    query = select(User).where(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Inactive user", "data": {}}
        )
    
    return user


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get the current user and verify that they have verified their mobile number
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "User not verified", "data": {}}
        )
    
    return current_user


async def get_current_mobile_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get the current user and ensure they are NOT an admin (for mobile app APIs)
    """
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False, 
                "message": "Admin users cannot access mobile application APIs. Please use the admin panel instead.", 
                "data": {}
            }
        )
    
    return current_user


async def get_current_mobile_verified_user(
    current_user: Annotated[User, Depends(get_current_mobile_user)]
) -> User:
    """
    Get the current mobile user and verify that they have verified their mobile number
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "User not verified", "data": {}}
        )
    
    return current_user 