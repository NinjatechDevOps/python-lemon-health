from datetime import datetime, timedelta
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from apps.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password, verify_token
from apps.core.db import get_db
from apps.accounts.models import User, VerificationType
from apps.accounts.schemas import (
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, Token, UserCreate, 
    UserLogin, UserResponse, VerificationCodeSubmit, VerificationRequest,
    RefreshToken
)
from apps.accounts.services import twilio_service
from apps.accounts.deps import get_current_verified_user

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
    # Check if user with this mobile number already exists
    query = select(User).where(
        User.mobile_number == user_in.mobile_number,
        User.country_code == user_in.country_code
    )
    result = await db.execute(query)
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this mobile number already exists"
        )
    
    # Create new user with unverified status
    user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
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
    
    if not success:
        # If SMS fails, still return success but with a warning
        return {
            "id": user.id,
            "message": "User registered successfully but verification SMS could not be sent. Please try requesting a new code.",
            "require_verification": True
        }
    
    return {
        "id": user.id,
        "message": "User registered successfully. Please verify your mobile number.",
        "require_verification": True
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
    # Find user by mobile number
    query = select(User).where(
        User.mobile_number == user_in.mobile_number,
        User.country_code == user_in.country_code
    )
    result = await db.execute(query)
    user = result.scalars().first()
    
    # Check if user exists and password is correct
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect mobile number or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Check if user is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mobile number not verified. Please verify your mobile number first."
        )
    
    # Generate access token
    access_token = create_access_token(
        subject=str(user.id),
        extra_data={"is_verified": user.is_verified}
    )
    
    # Generate refresh token
    refresh_token = create_refresh_token(
        subject=str(user.id)
    )
    
    # # If user is not verified, return a specific message but still allow login
    # if not user.is_verified:
    #     return {
    #         "access_token": access_token,
    #         "refresh_token": refresh_token,
    #         "token_type": "bearer",
    #         "user_id": user.id,
    #         "message": "Please verify your mobile number to login and access all features.",
    #         "require_verification": True
    #     }
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.id
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
    
    # Verify code
    success, message = await twilio_service.verify_code(
        db=db,
        verification_type=VerificationType.SIGNUP,
        mobile_number=user.mobile_number,
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
    access_token = create_access_token(
        subject=str(user.id),
        extra_data={"is_verified": user.is_verified}
    )
    
    # Generate refresh token
    refresh_token = create_refresh_token(
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
    
    # Send verification code
    success, message = await twilio_service.create_verification_code(
        db=db,
        verification_type=VerificationType.SIGNUP,
        mobile_number=user.mobile_number,
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
    
    # Send verification code
    success, message = await twilio_service.create_verification_code(
        db=db,
        verification_type=VerificationType.PASSWORD_RESET,
        mobile_number=user.mobile_number,
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
    
    # Verify code
    success, message = await twilio_service.verify_code(
        db=db,
        verification_type=VerificationType.PASSWORD_RESET,
        mobile_number=user.mobile_number,
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
    user.hashed_password = get_password_hash(reset_in.new_password)
    await db.commit()
    
    return {"message": "Password reset successfully"}


@router.post("/refresh-token", response_model=Token)
async def refresh_token(token_data: RefreshToken, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Get a new access token using a refresh token
    
    1. Verify refresh token
    2. Generate new access token
    3. Return tokens
    """
    try:
        # Verify the refresh token
        payload = verify_token(token_data.refresh_token)
        
        # Check if it's actually a refresh token
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
        
        # Get user from database
        query = select(User).where(User.id == int(user_id))
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Generate new access token
        access_token = create_access_token(
            subject=str(user.id),
            extra_data={"is_verified": user.is_verified}
        )
        
        # Generate new refresh token
        new_refresh_token = create_refresh_token(
            subject=str(user.id)
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_verified_user)],
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change password for authenticated user
    
    1. Verify current password
    2. Update password
    3. Return success response
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}
