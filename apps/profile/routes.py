from typing import Any, Optional
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from apps.auth.deps import get_current_user
from apps.auth.models import User
from apps.core.config import settings
from apps.core.db import get_db
from apps.profile.models import Profile
from apps.profile.schemas import ProfileCreate, ProfileResponse, ProfileUpdate, ProfilePictureResponse, BaseResponse
from apps.profile.services import ProfileService
from apps.profile.utils import api_response, api_error_response

router = APIRouter()


@router.get("/me", response_model=BaseResponse[ProfileResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user's profile
    """
    profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if not profile:
        # Instead of 404, return a default empty profile with user info
        return api_response(
            success=True,
            message="No profile found. Returning default profile.",
            data=ProfileResponse(
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
        )
    # Add first_name and last_name from user data
    try:
        response_data = ProfileResponse.model_validate(profile)
    except ValidationError as e:
        return api_error_response(status_code=400, message=f"Invalid profile data: {e}")
    response_data.first_name = current_user.first_name
    response_data.last_name = current_user.last_name
    return api_response(
        success=True,
        message="Profile fetched successfully",
        data=response_data
    )


@router.put("/", response_model=BaseResponse[ProfileResponse])
async def update_profile(
    date_of_birth: Optional[str] = Form(None),
    height: Optional[float] = Form(None),
    height_unit: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    gender: Optional[str] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user's profile (fields + optional image)
    """
    # Build the ProfileUpdate Pydantic model
    profile_data = ProfileUpdate(
        date_of_birth=date_of_birth,
        height=height,
        height_unit=height_unit,
        weight=weight,
        gender=gender,
    )
    # Get existing profile
    profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if not profile:
        # If profile doesn't exist, create it
        profile = await ProfileService.create_profile(db, profile_data, current_user.id)
        msg = "Profile created successfully"
    else:
        # Handle profile picture
        if profile_picture:
            success, message, updated_profile = await ProfileService.update_profile_picture(
                db=db, file=profile_picture, user_id=current_user.id
            )
            if not success:
                return api_error_response(status_code=400, message=message)
            profile_data.profile_picture_url = updated_profile.profile_picture_url
        profile = await ProfileService.update_profile(db, profile, profile_data)
        msg = "Profile updated successfully"
    # Add name from user data
    try:
        response_data = ProfileResponse.model_validate(profile)
    except ValidationError as e:
        return api_error_response(status_code=400, message=f"Invalid profile data: {e}")
    response_data.first_name = current_user.first_name
    response_data.last_name = current_user.last_name
    return api_response(
        success=True,
        message=msg,
        data=response_data
    )


@router.delete("/", response_model=dict)
async def delete_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete current user's profile
    """
    profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if not profile:
        return api_error_response(status_code=404, message="Profile not found")
    await ProfileService.delete_profile(db, profile)
    return api_response(success=True, message="Profile deleted successfully", data={})


# Remove the /upload-picture endpoint entirely 