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
    RefreshToken, LogoutRequest, BaseResponse, VerificationTypeEnum
)
from apps.auth.services import AuthService
from apps.auth.twilio_service import twilio_service
from apps.auth.deps import get_current_mobile_verified_user, get_current_user
from apps.auth.utils import api_response, api_error_response
import logging
from apps.core.logging_config import get_logger

logger = get_logger(__name__)

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
    logger.info(f"url : /register")
    logger.info(f"request : {user_in}")
    existing_user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code
    )
    if existing_user:
        logger.warning(f"User with mobile {user_in.country_code}{user_in.mobile_number} already exists.")
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Looks like you already have an account. Please log in."
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
    logger.info('User registered successfully.')
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
    logger.info(f"url : /login")
    logger.info(f"request : {user_in}")
    success, result = await AuthService.login_user(
        db=db,
        mobile_number=user_in.mobile_number,
        country_code=user_in.country_code,
        password=user_in.password
    )
    
    if not success:
        # If user is unverified, resend OTP and return 200 with user object and OTP status
        if isinstance(result, dict) and "message" in result and "user" in result:
            user = await AuthService.get_user_by_mobile(db, user_in.mobile_number, user_in.country_code)
            otp_sent, otp_message = False, "Could not send OTP"
            if user:
                otp_sent, otp_message = await twilio_service.create_verification_code(
                    db=db,
                    verification_type=VerificationType.SIGNUP,
                    mobile_number=user.mobile_number,
                    country_code=user.country_code,
                    user_id=user.id
                )
            return api_response(
                success=False,
                message=result["message"],
                data={
                    "user": result["user"],
                    "otp_sent": otp_sent,
                    "otp_message": otp_message
                }
            )
        # # Otherwise, it's a simple error message
        # return api_error_response(
        #     status_code=status.HTTP_401_UNAUTHORIZED,
        #     message=result
        # )
        return api_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=result
        )
    
    try:
        token_response = Token(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"]
        )
        
        # Include user data in the response
        response_data = {
            "token": token_response.model_dump(),  # Use model_dump() for Pydantic v2 compatibility
            "user": result["user"]
        }
    except ValidationError as e:
        return api_error_response(
            message="Invalid token data",
            status_code=400,
            data={"errors": e.errors()}
        )
    logger.info('User logged in successfully.')
    return api_response(
        success=True,
        message="Login successful",
        data=response_data
    )


@router.post("/verify", response_model=BaseResponse)
async def verify_code(verification_in: VerificationCodeSubmit, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Verify SMS code for mobile verification or password reset
    
    1. Find user by mobile number
    2. Verify code based on verification type
    3. Handle based on verification type:
       - Mobile verification: Mark user as verified and return tokens
       - Password reset: Return success (user will then call reset password)
    4. Return appropriate response
    """
    logger.info(f"url : /verify")
    logger.info(f"request : {verification_in}")
    success, result = await AuthService.verify_code_and_user(
        db=db,
        mobile_number=verification_in.mobile_number,
        country_code=verification_in.country_code,
        code=verification_in.code,
        verification_type=verification_in.verification_type
    )
    
    if not success:
        logger.warning(f"Verification failed for mobile {verification_in.country_code}{verification_in.mobile_number}. Reason: {result}")
        # Include the code in the error response for debugging
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"{result} (Code: {verification_in.code})"
        )
    
    # Handle different verification types
    if verification_in.verification_type == VerificationTypeEnum.MOBILE_VERIFICATION:
        try:
            token_response = Token(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                token_type=result["token_type"]
            )
            
            # Include user data in the response
            response_data = {
                "token": token_response.model_dump(),  # Use model_dump() for Pydantic v2 compatibility
                "user": result["user"]
            }
        except ValidationError as e:
            logger.error(f"Token validation error: {e.errors()}")
            return api_error_response(
                message="Invalid token data",
                status_code=400,
                data={"errors": e.errors()}
            )
        logger.info('Password reset verification successful.')
        return api_response(
            success=True,
            message="Verification successful",
            data=response_data
        )
    
    elif verification_in.verification_type == VerificationTypeEnum.PASSWORD_RESET:
        logger.info('Password reset verification successful.')
        return api_response(
            success=True,
            message="Password reset verification successful. You can now reset your password.",
            data={
                "user_id": result["user_id"],
                "verification_type": "password_reset"
            }
        )
    
    return api_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Invalid verification type"
    )


@router.post("/resend-verification", response_model=BaseResponse)
async def resend_verification(verification_in: VerificationRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Resend verification code for mobile verification or password reset
    
    1. Find user by mobile number
    2. Send new verification code based on verification type
    3. Return success response
    """
    # Find user by mobile number
    logger.info(f"url : /resend-verification")
    logger.info(f"request : {verification_in}")
    user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=verification_in.mobile_number,
        country_code=verification_in.country_code
    )
    
    if not user:
        logger.warning(f"User with mobile {verification_in.country_code}{verification_in.mobile_number} not found for resending verification.")
        return api_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )
    
    # Map verification type enum to VerificationType model enum
    if verification_in.verification_type == VerificationTypeEnum.MOBILE_VERIFICATION:
        twilio_verification_type = VerificationType.SIGNUP
        # Check if user is already verified for mobile verification
        if user.is_verified:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="User is already verified"
            )
    elif verification_in.verification_type == VerificationTypeEnum.PASSWORD_RESET:
        twilio_verification_type = VerificationType.PASSWORD_RESET
    else:
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid verification type"
        )
    
    # Send verification code
    otp_sent, message = await twilio_service.create_verification_code(
        db=db,
        verification_type=twilio_verification_type,
        mobile_number=user.mobile_number,
        country_code=user.country_code,
        user_id=user.id
    )
    logger.info('Verification code resent successfully.')
    # Always return 200 OK since the request was processed
    return api_response(
        success=True,
        message="Verification code request processed",
        data={
            "otp_sent": otp_sent,
            "otp_message": None if otp_sent else message,
            "verification_type": verification_in.verification_type.value
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
    logger.info(f"url : /forgot-password")
    logger.info(f"request : {request_in}")
    user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=request_in.mobile_number,
        country_code=request_in.country_code
    )
    
    if not user:
        logger.warning(f"User with mobile {request_in.country_code}{request_in.mobile_number} not found for password reset.")
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
    logger.info('Password reset verification code sent successfully.')
    # Always return 200 OK since the request was processed
    return api_response(
        success=True,
        message="Password reset request processed",
        data={
            "otp_sent": otp_sent,
            "otp_message": None if otp_sent else message,
            "verification_type": "password_reset"
        }
    )


@router.post("/reset-password", response_model=BaseResponse)
async def reset_password(reset_in: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Reset password (after OTP verification)
    
    1. Find user by mobile number
    2. Update password (OTP verification already done in verify endpoint)
    3. Return success response
    """
    # Find user by mobile number
    logger.info(f"url : /reset-password")
    logger.info(f"request : {reset_in}")    

    user = await AuthService.get_user_by_mobile(
        db=db,
        mobile_number=reset_in.mobile_number,
        country_code=reset_in.country_code
    )
    
    if not user:
        logger.warning(f"User with mobile {reset_in.country_code}{reset_in.mobile_number} not found for password reset.")   
        return api_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )
    
    # Update password
    await AuthService.update_password(db, user, reset_in.new_password)
    logger.info('Password reset successfully.')
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
    current_user: Annotated[User, Depends(get_current_mobile_verified_user)],
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change password for authenticated user
    
    1. Verify current password
    2. Update password
    3. Return success response
    """
    # Verify current password
    logger.info(f"url : /change-password")
    logger.info(f"request : {password_data}")
    if not verify_password(password_data.current_password, current_user.hashed_password):
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Incorrect current password"
        )
    
    # Update password
    await AuthService.update_password(db, current_user, password_data.new_password)
    logger.info('Password changed successfully.')   
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
    logger.info(f"url : /logout")
    logger.info(f"request : {logout_data}") 
    success = await AuthService.logout_user(
        access_token=logout_data.access_token,
        refresh_token=logout_data.refresh_token
    )
    
    if not success:
        return api_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to logout"
        )
    logger.info('User logged out successfully.')
    return api_response(
        success=True,
        message="Successfully logged out",
        data={
            "user_id": current_user.id
        }
    )

@router.delete("/me", response_model=BaseResponse)
async def delete_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Soft delete the current authenticated user (set is_active=False)
    """
    logger.info(f"url : /me [DELETE]")
    logger.info(f"request by user_id : {current_user.id}")
    if not current_user.is_active:
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="User is already inactive."
        )
    await AuthService.soft_delete_user(db, current_user)
    logger.info('User account deleted (soft delete).')
    return api_response(
        success=True,
        message="User account deleted (soft delete).",
        data={"user_id": current_user.id}
    )

