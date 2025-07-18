import os
import uuid
import shutil
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from apps.core.config import settings
from apps.profile.models import Profile
from apps.profile.schemas import ProfileCreate, ProfileUpdate


class ProfileService:
    """Service for profile operations"""
    
    @staticmethod
    async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Optional[Profile]:
        """Get a profile by user ID"""
        result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        return result.scalars().first()
    
    @staticmethod
    async def create_profile(db: AsyncSession, profile_data: ProfileCreate, user_id: int) -> Profile:
        """Create a new profile"""
        db_profile = Profile(user_id=user_id, **profile_data.model_dump(exclude_unset=True))
        db.add(db_profile)
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    
    @staticmethod
    async def update_profile(
        db: AsyncSession, 
        db_profile: Profile, 
        profile_data: ProfileUpdate
    ) -> Profile:
        """Update an existing profile"""
        update_data = profile_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_profile, field, value)
        
        await db.commit()
        await db.refresh(db_profile)
        return db_profile
    
    @staticmethod
    async def delete_profile(db: AsyncSession, db_profile: Profile) -> None:
        """Delete a profile"""
        await db.delete(db_profile)
        await db.commit()
    
    @staticmethod
    async def save_profile_picture(file: UploadFile, user_id: int) -> Tuple[bool, str]:
        """
        Save profile picture to local storage
        
        Args:
            file: The uploaded file
            user_id: User ID
            
        Returns:
            Tuple of (success, file_url or error_message)
        """
        # Validate file type
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            return False, f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        filename = f"{user_id}_{uuid.uuid4().hex}{file_ext}"
        
        # Create file path
        file_path = os.path.join(settings.MEDIA_ROOT, "profile_pictures", filename)
        file_url = f"/media/profile_pictures/{filename}"
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return True, file_url
        except Exception as e:
            return False, f"Error saving file: {str(e)}"
    
    @staticmethod
    async def update_profile_picture(
        db: AsyncSession,
        file: UploadFile,
        user_id: int
    ) -> Tuple[bool, str, Optional[Profile]]:
        """
        Update profile picture
        
        Args:
            db: Database session
            file: The uploaded file
            user_id: User ID
            
        Returns:
            Tuple of (success, message, updated_profile or None)
        """
        # Save file
        success, result = await ProfileService.save_profile_picture(file, user_id)
        if not success:
            return False, result, None
        
        # Get profile
        profile = await ProfileService.get_profile_by_user_id(db, user_id)
        
        # If profile exists, update it
        if profile:
            # Delete old profile picture if exists
            if profile.profile_picture_url:
                old_filename = profile.profile_picture_url.split('/')[-1]
                old_path = os.path.join(settings.MEDIA_ROOT, "profile_pictures", old_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Update profile
            profile.profile_picture_url = result
            await db.commit()
            await db.refresh(profile)
            return True, "Profile picture updated successfully", profile
        
        # Create new profile with picture
        profile_data = ProfileCreate(profile_picture_url=result)
        profile = await ProfileService.create_profile(db, profile_data, user_id)
        return True, "Profile picture added successfully", profile 