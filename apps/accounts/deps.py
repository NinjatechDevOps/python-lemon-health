from typing import Annotated, List, Optional

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.db import get_db
from apps.core.config import settings
from apps.core.security import verify_token
from apps.accounts.models import User
from apps.auth.models.rbac import Role, Permission

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
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
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
            detail="User not verified"
        )
    
    return current_user


async def get_user_permissions(
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """
    Get the permissions for the current user
    """
    permissions = set()
    
    # Get all roles for the user
    for role in current_user.roles:
        # Get all permissions for each role
        for permission in role.permissions:
            permissions.add(permission.name)
    
    return list(permissions)


def has_permission(required_permission: str):
    """
    Dependency to check if the user has the required permission
    """
    async def _has_permission(
        permissions: List[str] = Depends(get_user_permissions)
    ) -> bool:
        if required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission} required"
            )
        return True
    
    return _has_permission


def has_role(required_role: str):
    """
    Dependency to check if the user has the required role
    """
    async def _has_role(
        current_user: User = Depends(get_current_verified_user),
        db: AsyncSession = Depends(get_db)
    ) -> bool:
        # Check if the user has the required role
        for role in current_user.roles:
            if role.name == required_role:
                return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {required_role} required"
        )
    
    return _has_role 