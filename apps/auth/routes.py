from datetime import datetime, timedelta
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
from pydantic import ValidationError

from apps.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password, verify_token
from apps.core.db import get_db
from apps.auth.models import User, VerificationType
from apps.auth.schemas import (
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, Token, UserCreate, 
    UserLogin, UserResponse, VerificationCodeSubmit, VerificationRequest,
    RefreshToken, LogoutRequest, BaseResponse
)
from apps.auth.services import AuthService
from apps.auth.twilio_service import twilio_service
from apps.auth.deps import get_current_verified_user, get_current_user
from apps.auth.utils import api_response, api_error_response

router = APIRouter()
user_router = APIRouter()


@router.post("/register", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Register a new user
    
    1. Validate user input
    2. Check if user with mobile number already exists
    3. Create user with unverified status
    4. Send verification code
    5. Return success response
    """
    # Check if user with this mobile number and country code already exists
    existing_user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code
    )
    if existing_user:
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User with this mobile number and country code already exists"
        )
    # Check if user with this email already exists
    if user_in.email:
        existing_email_user = await AuthService.get_user_by_email(db, user_in.email)
        if existing_email_user:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="User with this email already exists"
            )
    # Register user and send verification code
    user, otp_sent, message = await AuthService.register_user(
        db=db,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code,
        password=user_in.password,
        email=user_in.email
    )
    
    try:
        user_response = UserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            mobile_number=user.mobile_number,
            country_code=user.country_code,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at
        )
    except ValidationError as e:
        return api_error_response(
            message="Invalid user data",
            status_code=400,
            data={"errors": e.errors()}
        )
    # Always return 201 Created since the user account was created
    return api_response(
        success=True,
        message="User registered successfully. " + ("Please verify your mobile number." if otp_sent else "Verification code could not be sent. Please use the resend option."),
        data=user_response
    )


@router.post("/login", response_model=BaseResponse)
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
        return api_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=result
        )
    
    try:
        token_response = Token(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"]
        )
    except ValidationError as e:
        return api_error_response(
            message="Invalid token data",
            status_code=400,
            data={"errors": e.errors()}
        )
    return api_response(
        success=True,
        message="Login successful",
        data=token_response
    )


@router.post("/verify", response_model=BaseResponse)
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
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"{result} (Code: {verification_in.code})"
        )
    
    try:
        token_response = Token(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"]
        )
    except ValidationError as e:
        return api_error_response(
            message="Invalid token data",
            status_code=400,
            data={"errors": e.errors()}
        )
    return api_response(
        success=True,
        message="Verification successful",
        data=token_response
    )


@router.post("/resend-verification", response_model=BaseResponse)
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
        return api_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )
    
    # Check if user is already verified
    if user.is_verified:
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is already verified"
        )
    
    # Send verification code
    otp_sent, message = await twilio_service.create_verification_code(
        db=db,
        verification_type=VerificationType.SIGNUP,
        mobile_number=user.mobile_number,
        country_code=user.country_code,
        user_id=user.id
    )
    
    # Always return 200 OK since the request was processed
    return api_response(
        success=True,
        message="Verification code request processed",
        data={
            "otp_sent": otp_sent,
            "otp_message": None if otp_sent else message
        }
    )


@router.post("/forgot-password", response_model=BaseResponse)
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
        return api_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )
    
    # Send verification code
    otp_sent, message = await twilio_service.create_verification_code(
        db=db,
        verification_type=VerificationType.PASSWORD_RESET,
        mobile_number=user.mobile_number,
        country_code=user.country_code,
        user_id=user.id
    )
    
    # Always return 200 OK since the request was processed
    return api_response(
        success=True,
        message="Password reset request processed",
        data={
            "otp_sent": otp_sent,
            "otp_message": None if otp_sent else message
        }
    )


@router.post("/reset-password", response_model=BaseResponse)
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
        return api_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
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
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message
        )
    
    # Update password
    await AuthService.update_password(db, user, reset_in.new_password)
    
    return api_response(
        success=True,
        message="Password reset successfully",
        data={
            "user_id": user.id
        }
    )


@router.post("/refresh-token", response_model=BaseResponse)
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
        return api_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=result
        )
    
    try:
        token_response = Token(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"]
        )
    except ValidationError as e:
        return api_error_response(
            message="Invalid token data",
            status_code=400,
            data={"errors": e.errors()}
        )
    return api_response(
        success=True,
        message="Token refreshed successfully",
        data=token_response
    )


@router.post("/change-password", response_model=BaseResponse)
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
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Incorrect current password"
        )
    
    # Update password
    await AuthService.update_password(db, current_user, password_data.new_password)
    
    return api_response(
        success=True,
        message="Password changed successfully",
        data={
            "user_id": current_user.id
        }
    )

@router.post("/logout", response_model=BaseResponse)
async def logout(
    logout_data: LogoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """
    Logout a user by invalidating their tokens
    
    1. Add access token to blacklist
    2. Add refresh token to blacklist if provided
    3. Return success response
    """
    success = await AuthService.logout_user(
        access_token=logout_data.access_token,
        refresh_token=logout_data.refresh_token
    )
    
    if not success:
        return api_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to logout"
        )
    
    return api_response(
        success=True,
        message="Successfully logged out",
        data={
            "user_id": current_user.id
        }
    )

