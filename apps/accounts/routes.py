from datetime import datetime, timedelta
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from apps.core.db import get_db
from apps.accounts.models import User, VerificationType
from apps.accounts.schemas import (
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, Token, UserCreate, 
    UserLogin, UserResponse, VerificationCodeSubmit, VerificationRequest,
    RefreshToken
)
from apps.accounts.deps import get_current_verified_user
from apps.auth.providers.base import AuthProviderFactory
from apps.auth.services.token import token_service
# Import otp_service where needed to avoid circular imports

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Register a new user
    
    1. Validate user input
    2. Check if user with mobile number already exists
    3. Create user with unverified status
    4. Send verification code
    5. Return success response
    """
    # Get the mobile auth provider
    provider = AuthProviderFactory.get_provider("mobile")
    
    # Register the user
    result = await provider.register(db, user_in.dict())
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return {
        "id": result["user_id"],
        "message": result["message"],
        "require_verification": result["require_verification"]
    }


@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Login with mobile number and password
    
    1. Find user by mobile number
    2. Verify password
    3. Check if user is verified
    4. Generate access token
    5. Return token
    """
    # Get the mobile auth provider
    provider = AuthProviderFactory.get_provider("mobile")
    
    # Authenticate the user
    result = await provider.authenticate(db, user_in.dict())
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    
    # Check if user is verified
    if not result["is_verified"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mobile number not verified. Please verify your mobile number first."
        )
    
    # Generate tokens
    access_token = token_service.create_access_token(
        subject=str(result["user_id"]),
        extra_data={"is_verified": result["is_verified"]}
    )
    
    # Generate refresh token
    refresh_token = token_service.create_refresh_token(
        subject=str(result["user_id"])
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": result["user_id"]
    }


@router.post("/verify")
async def verify_code(verification_in: VerificationCodeSubmit, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Verify SMS code
    
    1. Find user by mobile number
    2. Verify code
    3. Mark user as verified
    4. Return success response
    """
    # Find user by mobile number
    query = select(User).where(
        User.mobile_number == verification_in.mobile_number,
        User.country_code == verification_in.country_code
    )
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Import here to avoid circular imports
    from apps.auth.services.otp import otp_service
    
    # Verify code
    success, message = await otp_service.verify_code(
        db=db,
        verification_type=VerificationType.SIGNUP,
        recipient=user.mobile_number,
        country_code=user.country_code,
        code=verification_in.code,
        user_id=user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Mark user as verified
    user.is_verified = True
    await db.commit()
    
    # Generate access token
    access_token = token_service.create_access_token(
        subject=str(user.id),
        extra_data={"is_verified": user.is_verified}
    )
    
    # Generate refresh token
    refresh_token = token_service.create_refresh_token(
        subject=str(user.id)
    )
    
    return {
        "message": "Verification successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.id
    }


@router.post("/resend-verification")
async def resend_verification(verification_in: VerificationRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Resend verification code
    
    1. Find user by mobile number
    2. Send new verification code
    3. Return success response
    """
    # Find user by mobile number
    query = select(User).where(
        User.mobile_number == verification_in.mobile_number,
        User.country_code == verification_in.country_code
    )
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already verified
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified"
        )
    
    # Import here to avoid circular imports
    from apps.auth.services.otp import otp_service
    
    # Send verification code
    success, message = await otp_service.create_verification_code(
        db=db,
        verification_type=VerificationType.SIGNUP,
        recipient=user.mobile_number,
        country_code=user.country_code,
        user_id=user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )
    
    return {"message": "Verification code sent successfully"}


@router.post("/forgot-password")
async def forgot_password(request_in: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Request password reset
    
    1. Find user by mobile number
    2. Send verification code for password reset
    3. Return success response
    """
    # Find user by mobile number
    query = select(User).where(
        User.mobile_number == request_in.mobile_number,
        User.country_code == request_in.country_code
    )
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Import here to avoid circular imports
    from apps.auth.services.otp import otp_service
    
    # Send verification code
    success, message = await otp_service.create_verification_code(
        db=db,
        verification_type=VerificationType.PASSWORD_RESET,
        recipient=user.mobile_number,
        country_code=user.country_code,
        user_id=user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )
    
    return {"message": "Password reset code sent successfully"}


@router.post("/reset-password")
async def reset_password(reset_in: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Reset password with verification code
    
    1. Find user by mobile number
    2. Verify code
    3. Update password
    4. Return success response
    """
    # Find user by mobile number
    query = select(User).where(
        User.mobile_number == reset_in.mobile_number,
        User.country_code == reset_in.country_code
    )
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Import here to avoid circular imports
    from apps.auth.services.otp import otp_service
    
    # Verify code
    success, message = await otp_service.verify_code(
        db=db,
        verification_type=VerificationType.PASSWORD_RESET,
        recipient=user.mobile_number,
        country_code=user.country_code,
        code=reset_in.code,
        user_id=user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Update password
    from apps.core.security import get_password_hash
    user.hashed_password = get_password_hash(reset_in.new_password)
    await db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/refresh-token", response_model=Token)
async def refresh_token(refresh_token_in: RefreshToken, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Refresh access token using refresh token
    
    1. Verify refresh token
    2. Generate new access token
    3. Return new tokens
    """
    # Verify refresh token
    token_data = token_service.get_token_data(refresh_token_in.refresh_token)
    
    if not token_data or token_data.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user from token
    user_id = token_data.get("sub")
    query = select(User).where(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Generate new tokens
    access_token = token_service.create_access_token(
        subject=str(user.id),
        extra_data={"is_verified": user.is_verified}
    )
    
    new_refresh_token = token_service.create_refresh_token(
        subject=str(user.id)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user_id": user.id
    }


@router.post("/change-password")
async def change_password(
    change_password_in: ChangePasswordRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change password for authenticated user
    
    1. Verify current password
    2. Update password
    3. Return success response
    """
    # Verify current password
    from apps.core.security import verify_password, get_password_hash
    if not verify_password(change_password_in.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(change_password_in.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_verified_user)) -> Any:
    """
    Get information about the current user
    """
    # Return all required fields for UserResponse
    return {
        "id": current_user.id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "mobile_number": current_user.mobile_number,
        "country_code": current_user.country_code,
        "email": current_user.email,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }


@router.get("/providers")
async def get_auth_providers() -> Any:
    """
    Get available authentication providers
    """
    return {
        "providers": AuthProviderFactory.get_available_providers()
    }
