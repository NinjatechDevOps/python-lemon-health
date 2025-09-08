import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from apps.auth.deps import get_current_mobile_user
from apps.auth.models import User
from apps.core.db import get_db
from apps.profile.schemas import ProfileResponse, BaseResponse
from apps.profile.services import ProfileService
from apps.profile.utils import api_response, api_error_response, convert_form_data_to_profile_update, convert_relative_to_complete_url
from apps.core.logging_config import get_logger
from apps.auth.services import AuthService

logger = get_logger(__name__)

router = APIRouter()


@router.get("/me", response_model=BaseResponse[ProfileResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_mobile_user),
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
    """
    Get current user's profile
    """
    logger.info(f"url : /me [GET]")
    logger.info(f"request by user_id : {current_user.id}")
    profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if not profile:
        # Instead of 404, return a default empty profile with user info
        default_response = ProfileResponse(
            user_id=current_user.id,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            date_of_birth=None,
            height=None,
            height_unit="cm",
            weight=None,
            weight_unit="kg",
            gender=None,
            profile_picture_url=None
        )
        # Convert None to default image URL
        default_response.profile_picture_url = convert_relative_to_complete_url(None)
        logger.warning("No profile found. Returning default profile.")
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "profile_not_found_default", app_language)
        if not message:
            message = AuthService.get_message_from_json("profile_not_found_default", app_language)
        return api_response(
            success=True,
            message=message,
            data=default_response
        )
    # Add first_name and last_name from user data
    try:
        response_data = ProfileResponse.model_validate(profile)
    except ValidationError as e:
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "invalid_profile_data", app_language)
        if not message:
            message = AuthService.get_message_from_json("invalid_profile_data", app_language)
        return api_error_response(status_code=400, message=message)
    response_data.first_name = current_user.first_name
    response_data.last_name = current_user.last_name
    
    # Convert relative URL to complete URL
    response_data.profile_picture_url = convert_relative_to_complete_url(response_data.profile_picture_url)
    logger.info("Profile fetched successfully.")
    # Get translated message
    message = await AuthService.get_translation_by_keyword(db, "profile_fetched_successfully", app_language)
    if not message:
        message = AuthService.get_message_from_json("profile_fetched_successfully", app_language)
    return api_response(
        success=True,
        message=message,
        data=response_data
    )


@router.post("/", response_model=BaseResponse[ProfileResponse])
async def update_profile(
    date_of_birth: Optional[str] = Form(None),
    height: Optional[str] = Form(None),
    height_unit: Optional[str] = Form(None),
    weight: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_mobile_user),
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Any:
    """
    Update current user's profile (fields + optional image) - Form Data Version
    Partial update using PATCH method
    Supports file upload for profile pictures
    """
    logger.info(f"url : /  for update profile [POST]")
    logger.info(f"request by user_id : {current_user.id}")
    try:
        # Convert form data to ProfileUpdate with proper type conversion
        profile_data, error_message = convert_form_data_to_profile_update(
            date_of_birth=date_of_birth,
            height=height,
            height_unit=height_unit,
            weight=weight,
            gender=gender
        )
        
        # Check for validation errors
        if error_message or profile_data is None:
            # For validation errors from form data conversion, use the error message as-is
            # since it might contain specific validation details
            return api_error_response(status_code=400, message=error_message)
        logger.info(f"Profile data created: {profile_data.model_dump()}")
        
        # Get existing profile
        profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
        if not profile:
            # If profile doesn't exist, create it
            profile = await ProfileService.create_profile(db, profile_data, current_user.id)
            msg = "profile_created_successfully"
            logger.info(f"Profile created: {profile.id}")
            if profile_picture:
                success, message, updated_profile = await ProfileService.update_profile_picture(
                    db=db, file=profile_picture, user_id=current_user.id
                )
                if not success:
                    # Translate the error message keyword from ProfileService
                    translated_message = await AuthService.get_translation_by_keyword(db, message, app_language)
                    if not translated_message:
                        translated_message = AuthService.get_message_from_json(message, app_language)
                    return api_error_response(status_code=400, message=translated_message)
                profile_data.profile_picture_url = updated_profile.profile_picture_url
        else:
            # Handle profile picture
            if profile_picture:
                success, message, updated_profile = await ProfileService.update_profile_picture(
                    db=db, file=profile_picture, user_id=current_user.id
                )
                if not success:
                    # Translate the error message keyword from ProfileService
                    translated_message = await AuthService.get_translation_by_keyword(db, message, app_language)
                    if not translated_message:
                        translated_message = AuthService.get_message_from_json(message, app_language)
                    return api_error_response(status_code=400, message=translated_message)
                profile_data.profile_picture_url = updated_profile.profile_picture_url
            profile = await ProfileService.update_profile(db, profile, profile_data)
            msg = "profile_updated_successfully"
            logger.info(f"Profile updated: {profile.id}")
        
        # Add name from user data
        try:
            response_data = ProfileResponse.model_validate(profile)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            # Get translated message
            message = await AuthService.get_translation_by_keyword(db, "invalid_profile_data", app_language)
            if not message:
                message = AuthService.get_message_from_json("invalid_profile_data", app_language)
            return api_error_response(status_code=400, message=message)
        response_data.first_name = current_user.first_name
        response_data.last_name = current_user.last_name
        
        # Convert relative URL to complete URL
        response_data.profile_picture_url = convert_relative_to_complete_url(response_data.profile_picture_url)
        
        logger.info(f"Final response data: {response_data.model_dump()}")
        # Translate the success message
        translated_message = await AuthService.get_translation_by_keyword(db, msg, app_language)
        if not translated_message:
            translated_message = AuthService.get_message_from_json(msg, app_language)
        return api_response(
            success=True,
            message=translated_message,
            data=response_data
        )
    except ValidationError as e:
        # Handle Pydantic validation errors with 400 status
        logger.error(f"Pydantic validation error: {e}")
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "validation_error", app_language)
        if not message:
            message = AuthService.get_message_from_json("validation_error", app_language)
        return api_error_response(status_code=400, message=message)
    except Exception as e:
        logger.error(f"Unexpected error in update_profile: {str(e)}")
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "internal_server_error", app_language)
        if not message:
            message = AuthService.get_message_from_json("internal_server_error", app_language)
        return api_error_response(status_code=500, message=message)


@router.delete("/", response_model=dict)
async def delete_profile(
    current_user: User = Depends(get_current_mobile_user),
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> dict:
    """
    Delete current user's profile
    """
    logger.info(f"url : /  for delete profile [DELETE]")
    logger.info(f"request by user_id : {current_user.id}")
    profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if not profile:
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "profile_not_found", app_language)
        if not message:
            message = AuthService.get_message_from_json("profile_not_found", app_language)
        return api_error_response(status_code=404, message=message)
    
    await ProfileService.delete_profile(db, profile)
    logger.info("Profile deleted successfully.")
    # Get translated message
    message = await AuthService.get_translation_by_keyword(db, "profile_deleted_successfully", app_language)
    if not message:
        message = AuthService.get_message_from_json("profile_deleted_successfully", app_language)
    return api_response(success=True, message=message, data={})

