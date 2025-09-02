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
from apps.auth.schemas import VerificationTypeEnum
import logging
from apps.core.logging_config import get_logger

logger = get_logger(__name__)


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
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get a user by email"""
        query = select(User).where(User.email == email)
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
            Tuple of (user, otp_sent, message)
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
        otp_sent, message = await twilio_service.create_verification_code(
            db=db,
            verification_type=VerificationType.SIGNUP,
            mobile_number=user.mobile_number,
            country_code=user.country_code,
            user_id=user.id
        )
        
        return user, otp_sent, message
    
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
            Tuple of (success, token_data or error_message or user_data)
        """
        # Find user by mobile number
        user = await AuthService.get_user_by_mobile(db, mobile_number, country_code)
        
        # Check if user exists
        if not user:
            return False, "You're not registered yet. Please sign up to continue."
        
        # Check if user is active
        if not user.is_active:
            # return False, "Your account has been deactivated. Please contact support for assistance."
            return False, "We’ve suspended your account for violating our Terms of Use. If you believe this is a mistake, please contact us at info@lemonclinic.es or via WhatsApp at +34 665 903 865."
        
        # Check if user is admin - prevent admin users from logging into mobile app
        if user.is_admin:
            return False, "Admin users cannot access the mobile application. Please use the admin panel instead."
        
        # Check if password is correct
        if not verify_password(password, user.hashed_password):
            return False, "Incorrect password. Please check your password and try again."
        
        # Create user response data with datetime converted to ISO format strings
        user_data = {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "mobile_number": user.mobile_number,
            "country_code": user.country_code,
            "email": user.email,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        
        # Check if user is verified
        if not user.is_verified:
            return False, {
                "message": "Mobile number not verified. Please verify your mobile number first.",
                "user": user_data
            }
        
        # Generate access token
        access_token = create_access_token(
            subject=str(user.id),
            extra_data={"is_verified": user.is_verified, "is_admin": user.is_admin}
        )
        
        # Generate refresh token
        refresh_token = create_refresh_token(
            subject=str(user.id),
            extra_data={"is_admin": user.is_admin}
        )
        
        return True, {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_data
        }
    
    @staticmethod
    async def verify_code_and_user(
        db: AsyncSession,
        mobile_number: str,
        country_code: str,
        code: str,
        verification_type: VerificationTypeEnum = VerificationTypeEnum.MOBILE_VERIFICATION
    ) -> Tuple[bool, Any]:
        """
        Verify code and handle based on verification type
        
        Args:
            db: Database session
            mobile_number: User's mobile number
            country_code: User's country code
            code: Verification code
            verification_type: Type of verification (mobile_verification or password_reset)
            
        Returns:
            Tuple of (success, token_data or error_message)
        """
        # Find user by mobile number
        user = await AuthService.get_user_by_mobile(db, mobile_number, country_code)
        
        if not user:
            return False, "User not found"
        
        # Map verification type enum to VerificationType model enum
        if verification_type == VerificationTypeEnum.MOBILE_VERIFICATION:
            twilio_verification_type = VerificationType.SIGNUP
        elif verification_type == VerificationTypeEnum.PASSWORD_RESET:
            twilio_verification_type = VerificationType.PASSWORD_RESET
        else:
            return False, "Invalid verification type"
        
        # Verify code
        success, message = await twilio_service.verify_code(
            db=db,
            verification_type=twilio_verification_type,
            mobile_number=user.mobile_number,
            country_code=user.country_code,
            code=code,
            user_id=user.id
        )
        
        if not success:
            return False, message
        
        # Handle based on verification type
        if verification_type == VerificationTypeEnum.MOBILE_VERIFICATION:
            # Mark user as verified
            await AuthService.verify_user(db, user)
            
            # Create user response data with datetime converted to ISO format strings
            user_data = {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_number": user.mobile_number,
                "country_code": user.country_code,
                "email": user.email,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            
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
                "user": user_data
            }
        
        elif verification_type == VerificationTypeEnum.PASSWORD_RESET:
            # For password reset, just return success without tokens
            # The user will then call reset password endpoint
            return True, {
                "message": "Password reset verification successful",
                "user_id": user.id
            }
        
        return False, "Invalid verification type"
    
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
            logger.debug(f"Received refresh_token: {refresh_token}")
            # Verify the refresh token
            payload = await verify_token(refresh_token)
            logger.debug(f"Decoded payload: {payload}")

            # Check if it's actually a refresh token
            if payload.get("token_type") != "refresh":
                logger.debug(f"Not a refresh token, payload: {payload}")
                return False, "Invalid token type"

            # Get user ID from token
            user_id = payload.get("sub")
            if not user_id:
                logger.debug(f"No user_id in payload: {payload}")
                return False, "Invalid token"

            # Get user from database
            user = await AuthService.get_user_by_id(db, int(user_id))
            logger.debug(f"User from DB: {user}")

            if not user:
                logger.debug(f"User not found for user_id: {user_id}")
                return False, "User not found"

            # Check if user is active
            if not user.is_active:
                logger.debug(f"User is not active: {user_id}")
                return False, "Inactive user"

            # Generate new access token
            new_access_token = create_access_token(
                subject=str(user.id),
                extra_data={"is_verified": user.is_verified, "is_admin": user.is_admin}
            )

            # Generate new refresh token
            new_refresh_token = create_refresh_token(
                subject=str(user.id),
                extra_data={"is_admin": user.is_admin}
            )

            logger.debug(f"New tokens generated for user_id: {user_id}")
            return True, {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }

        except Exception as e:
            logger.error(f"Exception in refresh_token: {str(e)}")
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
            logger.error(f"Error blacklisting access token: {e}")
        
        # Blacklist refresh token if provided
        if refresh_token:
            try:
                # Use longer expiration for refresh token
                refresh_exp = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
                await add_token_to_blacklist(refresh_token, refresh_exp)
            except Exception as e:
                logger.error(f"Error blacklisting refresh token: {e}")
        
        return True

    @staticmethod
    async def soft_delete_user(db: AsyncSession, user: User) -> User:
        """Soft delete a user by setting is_active to False"""
        user.is_active = False
        await db.commit()
        await db.refresh(user)
        return user
