import random
import string
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from apps.core.config import settings
from apps.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password, verify_token
from apps.auth.models import User, VerificationType
from apps.auth.twilio_service import twilio_service


class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    async def get_user_by_mobile(
        db: AsyncSession, 
        mobile_number: str, 
        country_code: str
    ) -> Optional[User]:
        """Get a user by mobile number and country code"""
        query = select(User).where(
            User.mobile_number == mobile_number,
            User.country_code == country_code
        )
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_user(
        db: AsyncSession,
        first_name: str,
        last_name: str,
        mobile_number: str,
        country_code: str,
        password: str,
        email: Optional[str] = None
    ) -> User:
        """Create a new user"""
        user = User(
            first_name=first_name,
            last_name=last_name,
            mobile_number=mobile_number,
            country_code=country_code,
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_verified=False
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def verify_user(db: AsyncSession, user: User) -> User:
        """Mark a user as verified"""
        user.is_verified = True
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def update_password(db: AsyncSession, user: User, new_password: str) -> User:
        """Update a user's password"""
        user.hashed_password = get_password_hash(new_password)
        await db.commit()
        await db.refresh(user)
        return user
    
    @staticmethod
    async def register_user(
        db: AsyncSession,
        first_name: str,
        last_name: str,
        mobile_number: str,
        country_code: str,
        password: str,
        email: Optional[str] = None
    ) -> Tuple[User, bool, str]:
        """
        Register a new user
        
        Args:
            db: Database session
            first_name: User's first name
            last_name: User's last name
            mobile_number: User's mobile number
            country_code: User's country code
            password: User's password
            email: User's email (optional)
            
        Returns:
            Tuple of (user, success, message)
        """
        # Create new user with unverified status
        user = User(
            first_name=first_name,
            last_name=last_name,
            mobile_number=mobile_number,
            country_code=country_code,
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_verified=False
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Send verification code
        success, message = await twilio_service.create_verification_code(
            db=db,
            verification_type=VerificationType.SIGNUP,
            mobile_number=user.mobile_number,
            country_code=user.country_code,
            user_id=user.id
        )
        
        return user, success, message
    
    @staticmethod
    async def login_user(
        db: AsyncSession,
        mobile_number: str,
        country_code: str,
        password: str
    ) -> Tuple[bool, Any]:
        """
        Login a user
        
        Returns:
            Tuple of (success, token_data or error_message)
        """
        # Find user by mobile number
        user = await AuthService.get_user_by_mobile(db, mobile_number, country_code)
        
        # Check if user exists and password is correct
        if not user or not verify_password(password, user.hashed_password):
            return False, "Incorrect mobile number or password"
        
        # Check if user is active
        if not user.is_active:
            return False, "Inactive user"
        
        # Check if user is verified
        if not user.is_verified:
            return False, "Mobile number not verified. Please verify your mobile number first."
        
        # Generate access token
        access_token = create_access_token(
            subject=str(user.id),
            extra_data={"is_verified": user.is_verified}
        )
        
        # Generate refresh token
        refresh_token = create_refresh_token(
            subject=str(user.id)
        )
        
        return True, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id
        }
    
    @staticmethod
    async def verify_code_and_user(
        db: AsyncSession,
        mobile_number: str,
        country_code: str,
        code: str
    ) -> Tuple[bool, Any]:
        """
        Verify code and mark user as verified
        
        Returns:
            Tuple of (success, token_data or error_message)
        """
        # Find user by mobile number
        user = await AuthService.get_user_by_mobile(db, mobile_number, country_code)
        
        if not user:
            return False, "User not found"
        
        # Verify code
        success, message = await twilio_service.verify_code(
            db=db,
            verification_type=VerificationType.SIGNUP,
            mobile_number=user.mobile_number,
            country_code=user.country_code,
            code=code,
            user_id=user.id  # Pass the user_id explicitly
        )
        
        if not success:
            return False, message
        
        # Mark user as verified
        await AuthService.verify_user(db, user)
        
        # Generate access token
        access_token = create_access_token(
            subject=str(user.id),
            extra_data={"is_verified": user.is_verified}
        )
        
        # Generate refresh token
        refresh_token = create_refresh_token(
            subject=str(user.id)
        )
        
        return True, {
            "message": "Verification successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id
        }
    
    @staticmethod
    async def refresh_token(
        db: AsyncSession,
        refresh_token: str
    ) -> Tuple[bool, Any]:
        """
        Get new tokens using a refresh token
        
        Returns:
            Tuple of (success, token_data or error_message)
        """
        from apps.core.security import verify_token
        
        try:
            # Verify the refresh token
            payload = verify_token(refresh_token)
            
            # Check if it's actually a refresh token
            if payload.get("token_type") != "refresh":
                return False, "Invalid token type"
            
            # Get user ID from token
            user_id = payload.get("sub")
            if not user_id:
                return False, "Invalid token"
            
            # Get user from database
            user = await AuthService.get_user_by_id(db, int(user_id))
            
            if not user:
                return False, "User not found"
            
            # Check if user is active
            if not user.is_active:
                return False, "Inactive user"
            
            # Generate new access token
            new_access_token = create_access_token(
                subject=str(user.id),
                extra_data={"is_verified": user.is_verified}
            )
            
            # Generate new refresh token
            new_refresh_token = create_refresh_token(
                subject=str(user.id)
            )
            
            return True, {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
            
        except JWTError:
            return False, "Invalid refresh token"

    @staticmethod
    async def logout_user(access_token: str, refresh_token: Optional[str] = None) -> bool:
        """
        Logout a user by blacklisting their tokens
        
        Args:
            access_token: The access token to blacklist
            refresh_token: The refresh token to blacklist (optional)
            
        Returns:
            bool: True if successful
        """
        from datetime import timedelta
        from apps.core.redis import add_token_to_blacklist
        
        # Calculate remaining time for access token
        try:
            from apps.core.security import jwt
            payload = jwt.decode(
                access_token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            exp = payload.get("exp")
            if exp:
                # Calculate remaining time
                exp_datetime = datetime.fromtimestamp(exp)
                remaining = exp_datetime - datetime.utcnow()
                if remaining.total_seconds() > 0:
                    # Add to blacklist with remaining time
                    await add_token_to_blacklist(access_token, remaining)
        except Exception as e:
            print(f"Error blacklisting access token: {e}")
        
        # Blacklist refresh token if provided
        if refresh_token:
            try:
                # Use longer expiration for refresh token
                refresh_exp = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
                await add_token_to_blacklist(refresh_token, refresh_exp)
            except Exception as e:
                print(f"Error blacklisting refresh token: {e}")
        
        return True
