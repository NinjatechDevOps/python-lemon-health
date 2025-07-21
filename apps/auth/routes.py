from datetime import datetime, timedelta
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from apps.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password, verify_token
from apps.core.db import get_db
from apps.auth.models import User, VerificationType
from apps.auth.schemas import (
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, Token, UserCreate, 
    UserLogin, UserResponse, VerificationCodeSubmit, VerificationRequest,
    RefreshToken
)
from apps.auth.services import AuthService
from apps.auth.twilio_service import twilio_service
from apps.auth.deps import get_current_verified_user

router = APIRouter()
user_router = APIRouter()


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
    existing_user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code
    )
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this mobile number already exists"
        )
    
    # Register user and send verification code
    user, success, message = await AuthService.register_user(
        db=db,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code,
        password=user_in.password,
        email=user_in.email
    )
    
    response = {
        "id": user.id,
        "success": success,
        "require_verification": True
    }
    
    if not success:
        # If SMS fails, still return success but with the error message
        response["message"] = message
        response["fallback"] = "If you don't receive the code, you can request a new one."
    else:
        response["message"] = "User registered successfully. Please verify your mobile number."
    
    return response


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
    success, result = await AuthService.login_user(
        db=db,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code,
        password=user_in.password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )
    
    return result


@router.post("/verify")
async def verify_code(verification_in: VerificationCodeSubmit, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Verify SMS code
    
    1. Find user by mobile number
    2. Verify code
    3. Mark user as verified
    4. Return success response
    """
    success, result = await AuthService.verify_code_and_user(
        db=db,
        mobile_number=verification_in.mobile_number,
        country_code=verification_in.country_code,
        code=verification_in.code
    )
    
    if not success:
        # Include the code in the error response for debugging
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{result} (Code: {verification_in.code})"
        )
    
    return result


@router.post("/resend-verification")
async def resend_verification(verification_in: VerificationRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Resend verification code
    
    1. Find user by mobile number
    2. Send new verification code
    3. Return success response
    """
    # Find user by mobile number
    user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=verification_in.mobile_number,
        country_code=verification_in.country_code
    )
    
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
        # Return 200 with error message instead of 500
        return {
            "success": False,
            "message": message,
            "fallback": "If you don't receive the code, please contact support."
        }
    
    return {"success": True, "message": "Verification code sent successfully"}


@router.post("/forgot-password")
async def forgot_password(request_in: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Request password reset
    
    1. Find user by mobile number
    2. Send verification code for password reset
    3. Return success response
    """
    # Find user by mobile number
    user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=request_in.mobile_number,
        country_code=request_in.country_code
    )
    
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
        # Return 200 with error message instead of 500
        # This is because the verification code was created in the database
        # but the SMS delivery failed
        return {
            "success": False,
            "message": message,
            "fallback": "If you don't receive the code, please contact support."
        }
    
    return {"success": True, "message": "Password reset code sent successfully"}


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
    user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=reset_in.mobile_number,
        country_code=reset_in.country_code
    )
    
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
    await AuthService.update_password(db, user, reset_in.new_password)
    
    return {"message": "Password reset successfully"}


@router.post("/refresh-token", response_model=Token)
async def refresh_token(token_data: RefreshToken, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Get a new access token using a refresh token
    
    1. Verify refresh token
    2. Generate new access token
    3. Return tokens
    """
    success, result = await AuthService.refresh_token(
        db=db,
        refresh_token=token_data.refresh_token
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result
        )
    
    return result


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
    await AuthService.update_password(db, current_user, password_data.new_password)
    
    return {"message": "Password changed successfully"}
