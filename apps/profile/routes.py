from typing import Any
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.deps import get_current_user
from apps.auth.models import User
from apps.core.config import settings
from apps.core.db import get_db
from apps.profile.models import Profile
from apps.profile.schemas import ProfileCreate, ProfileResponse, ProfileUpdate, ProfilePictureResponse
from apps.profile.services import ProfileService

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
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
        return {
            "id": 0,  # Use 0 as a placeholder ID
            "user_id": current_user.id,
            "date_of_birth": None,
            "height": None,
            "height_unit": "cm",
            "weight": None,
            "weight_unit": "kg",
            "gender": None,
            "profile_picture_url": None,
            "name": f"{current_user.first_name} {current_user.last_name}"
        }
    
    # Add name from user data
    response_data = ProfileResponse.model_validate(profile)
    response_data.name = f"{current_user.first_name} {current_user.last_name}"
    return response_data


@router.post("/", response_model=ProfileResponse)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new profile for the current user
    """
    # Check if profile already exists
    existing_profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists for this user"
        )
    
    # Create profile
    profile = await ProfileService.create_profile(db, profile_data, current_user.id)
    
    # Add name from user data
    response_data = ProfileResponse.model_validate(profile)
    response_data.name = f"{current_user.first_name} {current_user.last_name}"
    return response_data


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user's profile
    """
    # Get existing profile
    profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if not profile:
        # If profile doesn't exist, create it
        profile = await ProfileService.create_profile(db, ProfileCreate(**profile_data.model_dump()), current_user.id)
    else:
        # Update profile
        profile = await ProfileService.update_profile(db, profile, profile_data)
    
    # Add name from user data
    response_data = ProfileResponse.model_validate(profile)
    response_data.name = f"{current_user.first_name} {current_user.last_name}"
    return response_data


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete current user's profile
    """
    profile = await ProfileService.get_profile_by_user_id(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    await ProfileService.delete_profile(db, profile)


@router.post("/upload-picture", response_model=ProfilePictureResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Upload profile picture
    """
    # Check file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_IMAGE_SIZE / (1024 * 1024)}MB"
        )
    
    # Update profile picture
    success, message, updated_profile = await ProfileService.update_profile_picture(
        db=db,
        file=file,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    return {"profile_picture_url": updated_profile.profile_picture_url} 