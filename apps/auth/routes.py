from datetime import datetime, timedelta
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Header
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
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
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
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "user_already_exists", app_language)
        if not message:
            message = AuthService.get_message_from_json("user_already_exists", app_language)
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message
        )
    # Check if user with this email already exists
    if user_in.email:
        existing_email_user = await AuthService.get_user_by_email(db, user_in.email)
        if existing_email_user:
            # Get translated message
            message = await AuthService.get_translation_by_keyword(db, "email_already_exists", app_language)
            if not message:
                message = AuthService.get_message_from_json("email_already_exists", app_language)
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=message
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
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "invalid_user_data", app_language)
        if not message:
            message = AuthService.get_message_from_json("invalid_user_data", app_language)
        return api_error_response(
            message=message,
            status_code=400,
            data={"errors": e.errors()}
        )
    # Always return 201 Created since the user account was created
    logger.info('User registered successfully.')
    # Get translated messages
    if otp_sent:
        message = await AuthService.get_translation_by_keyword(db, "user_registered_successfully", app_language)
        if not message:
            message = AuthService.get_message_from_json("user_registered_successfully", app_language)
    else:
        base_msg = await AuthService.get_translation_by_keyword(db, "user_registered_successfully", app_language)
        if not base_msg:
            base_msg = AuthService.get_message_from_json("user_registered_successfully", app_language)
        verify_msg = await AuthService.get_translation_by_keyword(db, "verification_code_not_sent", app_language)
        if not verify_msg:
            verify_msg = AuthService.get_message_from_json("verification_code_not_sent", app_language)
        # Just use the verification_code_not_sent message when OTP fails
        message = verify_msg
    
    return api_response(
        success=True,
        message=message,
        data=user_response
    )


@router.post("/login", response_model=BaseResponse)
async def login(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
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
            # Translate the message keyword
            translated_message = await AuthService.get_translation_by_keyword(db, result["message"], app_language)
            if not translated_message:
                translated_message = AuthService.get_message_from_json(result["message"], app_language)
            return api_response(
                success=False,
                message=translated_message,
                data={
                    "user": result["user"],
                    "otp_sent": otp_sent,
                    "otp_message": otp_message
                }
            )
        # # Otherwise, it's a simple error message (keyword)
        # Translate the error message keyword
        translated_message = await AuthService.get_translation_by_keyword(db, result, app_language)
        if not translated_message:
            translated_message = AuthService.get_message_from_json(result, app_language)
        return api_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=translated_message
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
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "invalid_token_data", app_language)
        if not message:
            message = AuthService.get_message_from_json("invalid_token_data", app_language)
        return api_error_response(
            message=message,
            status_code=400,
            data={"errors": e.errors()}
        )
    logger.info('User logged in successfully.')
    # Get translated message
    message = await AuthService.get_translation_by_keyword(db, "login_successful", app_language)
    if not message:
        message = AuthService.get_message_from_json("login_successful", app_language)
    return api_response(
        success=True,
        message=message,
        data=response_data
    )


@router.post("/verify", response_model=BaseResponse)
async def verify_code(
    verification_in: VerificationCodeSubmit,
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
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
        # Translate the error message keyword
        translated_message = await AuthService.get_translation_by_keyword(db, result, app_language)
        if not translated_message:
            translated_message = AuthService.get_message_from_json(result, app_language)
        # Include the code in the error response for debugging
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"{translated_message} (Code: {verification_in.code})"
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
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "verification_successful", app_language)
        if not message:
            message = AuthService.get_message_from_json("verification_successful", app_language)
        return api_response(
            success=True,
            message=message,
            data=response_data
        )
    
    elif verification_in.verification_type == VerificationTypeEnum.PASSWORD_RESET:
        logger.info('Password reset verification successful.')
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "password_reset_verification_successful", app_language)
        if not message:
            message = AuthService.get_message_from_json("password_reset_verification_successful", app_language)
        return api_response(
            success=True,
            message=message,
            data={
                "user_id": result["user_id"],
                "verification_type": "password_reset"
            }
        )
    
    # Get translated message
    message = await AuthService.get_translation_by_keyword(db, "invalid_verification_type", app_language)
    if not message:
        message = AuthService.get_message_from_json("invalid_verification_type", app_language)
    return api_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message
    )


@router.post("/resend-verification", response_model=BaseResponse)
async def resend_verification(
    verification_in: VerificationRequest,
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
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
            message=await AuthService.get_translation_by_keyword(db, "user_not_found", app_language) or AuthService.get_message_from_json("user_not_found", app_language)
        )
    
    # Map verification type enum to VerificationType model enum
    if verification_in.verification_type == VerificationTypeEnum.MOBILE_VERIFICATION:
        twilio_verification_type = VerificationType.SIGNUP
        # Check if user is already verified for mobile verification
        if user.is_verified:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=await AuthService.get_translation_by_keyword(db, "user_already_verified", app_language) or AuthService.get_message_from_json("user_already_verified", app_language)
            )
    elif verification_in.verification_type == VerificationTypeEnum.PASSWORD_RESET:
        twilio_verification_type = VerificationType.PASSWORD_RESET
    else:
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=await AuthService.get_translation_by_keyword(db, "invalid_verification_type", app_language) or AuthService.get_message_from_json("invalid_verification_type", app_language)
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
        message=await AuthService.get_translation_by_keyword(db, "verification_code_sent", app_language) or AuthService.get_message_from_json("verification_code_sent", app_language),
        data={
            "otp_sent": otp_sent,
            "otp_message": None if otp_sent else message,
            "verification_type": verification_in.verification_type.value
        }
    )


@router.post("/forgot-password", response_model=BaseResponse)
async def forgot_password(
    request_in: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
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
            message=await AuthService.get_translation_by_keyword(db, "user_not_found", app_language) or AuthService.get_message_from_json("user_not_found", app_language)
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
        message=await AuthService.get_translation_by_keyword(db, "password_reset_request_processed", app_language) or AuthService.get_message_from_json("password_reset_request_processed", app_language),
        data={
            "otp_sent": otp_sent,
            "otp_message": None if otp_sent else message,
            "verification_type": "password_reset"
        }
    )


@router.post("/reset-password", response_model=BaseResponse)
async def reset_password(
    reset_in: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
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
            message=await AuthService.get_translation_by_keyword(db, "user_not_found", app_language) or AuthService.get_message_from_json("user_not_found", app_language)
        )
    
    # Update password
    await AuthService.update_password(db, user, reset_in.new_password)
    logger.info('Password reset successfully.')
    return api_response(
        success=True,
        message=await AuthService.get_translation_by_keyword(db, "password_reset_successfully", app_language) or AuthService.get_message_from_json("password_reset_successfully", app_language),
        data={
            "user_id": user.id
        }
    )


@router.post("/refresh-token", response_model=BaseResponse)
async def refresh_token(
    token_data: RefreshToken,
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
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
        # Translate the error message keyword
        translated_message = await AuthService.get_translation_by_keyword(db, result, app_language)
        if not translated_message:
            translated_message = AuthService.get_message_from_json(result, app_language)
        return api_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=translated_message
        )
    
    try:
        token_response = Token(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type=result["token_type"]
        )
    except ValidationError as e:
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "invalid_token_data", app_language)
        if not message:
            message = AuthService.get_message_from_json("invalid_token_data", app_language)
        return api_error_response(
            message=message,
            status_code=400,
            data={"errors": e.errors()}
        )
    return api_response(
        success=True,
        message=await AuthService.get_translation_by_keyword(db, "token_refreshed_successfully", app_language) or AuthService.get_message_from_json("token_refreshed_successfully", app_language),
        data=token_response
    )


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_mobile_verified_user)],
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
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
            message=await AuthService.get_translation_by_keyword(db, "incorrect_current_password", app_language) or AuthService.get_message_from_json("incorrect_current_password", app_language)
        )
    
    # Update password
    await AuthService.update_password(db, current_user, password_data.new_password)
    logger.info('Password changed successfully.')   
    return api_response(
        success=True,
        message=await AuthService.get_translation_by_keyword(db, "password_changed_successfully", app_language) or AuthService.get_message_from_json("password_changed_successfully", app_language),
        data={
            "user_id": current_user.id
        }
    )

@router.post("/logout", response_model=BaseResponse)
async def logout(
    logout_data: LogoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
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
            message=await AuthService.get_translation_by_keyword(db, "failed_to_logout", app_language) or AuthService.get_message_from_json("failed_to_logout", app_language)
        )
    logger.info('User logged out successfully.')
    return api_response(
        success=True,
        message=await AuthService.get_translation_by_keyword(db, "logged_out_successfully", app_language) or AuthService.get_message_from_json("logged_out_successfully", app_language),
        data={
            "user_id": current_user.id
        }
    )

@router.delete("/me", response_model=BaseResponse)
async def delete_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
    """
    Soft delete the current authenticated user (set is_active=False)
    """
    logger.info(f"url : /me [DELETE]")
    logger.info(f"request by user_id : {current_user.id}")
    if not current_user.is_active:
        return api_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=await AuthService.get_translation_by_keyword(db, "user_already_inactive", app_language) or AuthService.get_message_from_json("user_already_inactive", app_language)
        )
    await AuthService.soft_delete_user(db, current_user)
    logger.info('User account deleted (soft delete).')
    return api_response(
        success=True,
        message=await AuthService.get_translation_by_keyword(db, "account_deleted_soft", app_language) or AuthService.get_message_from_json("account_deleted_soft", app_language),
        data={"user_id": current_user.id}
    )

@router.get("/translations", response_model=BaseResponse)
async def get_translations(
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Fetch all translations for both supported languages (en, es)
    
    Returns:
        JSON response containing translations for both languages: {"en": {...}, "es": {...}}
    """
    logger.info(f"url : /translations")
    
    # Get all translations for both languages
    translations_json = await AuthService.get_all_translations(db)
    
    if translations_json is None:
        logger.error("Failed to fetch translations from database")
        return api_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to fetch translations"
        )
    
    logger.info('All translations fetched successfully')
    return {
        "success":True,
        "message":"Translations fetched successfully",
        "data":translations_json
    }

