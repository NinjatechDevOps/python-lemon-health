from datetime import date
from typing import Optional, Generic, TypeVar

from pydantic import BaseModel, Field, validator

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

class ProfileBase(BaseModel):
    """Base schema for profile data"""
    date_of_birth: Optional[date] = None
    height: Optional[float] = None
    height_unit: Optional[str] = Field(None, description="Height unit (cm or ft/in)")
    weight: Optional[float] = Field(None, description="Weight unit (kg)")
    gender: Optional[str] = None
    profile_picture_url: Optional[str] = None

    @validator('height_unit')
    def validate_height_unit(cls, v):
        if v and v not in ['cm', 'ft/in']:
            raise ValueError('Height unit must be either "cm" or "ft/in"')
        return v
        
    @validator('gender')
    def validate_gender(cls, v):
        if v and v not in ['Male', 'Female', 'Other']:
            raise ValueError('Gender must be either "Male", "Female", or "Other"')
        return v

class ProfileCreate(ProfileBase):
    """Schema for creating a profile"""
    pass

class ProfileUpdate(ProfileBase):
    """Schema for updating a profile"""
    pass

class ProfilePictureResponse(BaseModel):
    """Schema for profile picture upload response"""
    profile_picture_url: str

class ProfileResponse(ProfileBase):
    """Schema for profile response"""
    id: int
    user_id: int
    # Include user name from auth data
    name: Optional[str] = None

    class Config:
        from_attributes = True 