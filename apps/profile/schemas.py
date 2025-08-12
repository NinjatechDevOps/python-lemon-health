import logging
from apps.core.logging_config import get_logger

logger = get_logger(__name__)

from datetime import date
from typing import Optional, Generic, TypeVar

from pydantic import BaseModel, Field, validator, model_validator
import re

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

class ProfileBase(BaseModel):
    """Base schema for profile data"""
    date_of_birth: Optional[date] = Field(
        None, 
        description="Date of birth in ISO format (YYYY-MM-DD)"
    )
    height: Optional[float] = Field(
        None, 
        description="Height in cm (50-250) or feet (2-8)"
    )
    height_unit: Optional[str] = Field(
        None, 
        description="Height unit (cm or ft/in)"
    )
    weight: Optional[float] = Field(
        None, 
        ge=20, 
        le=500, 
        description="Weight in kg (20-500) or lbs (44.1-1102.3)"
    )
    weight_unit: Optional[str] = Field(
        None,
        description="Weight unit (kg or lbs)"
    )
    gender: Optional[str] = Field(
        None,
        description="Gender (Male, Female, or Other)"
    )
    profile_picture_url: Optional[str] = Field(
        None,
        description="URL to the profile picture"
    )

    @model_validator(mode='after')
    def validate_height_with_unit(self):
        logger.debug(f"Model validator called with data: {self.model_dump()}")
        height = self.height
        height_unit = self.height_unit or 'cm'
        
        if height is not None:
            logger.debug(f"Validating height={height} with unit={height_unit}")
            if height_unit == 'cm':
                if height < 50 or height > 250:
                    logger.error(f"CM validation failed: {height} not in range [50, 250]")
                    raise ValueError('Height must be between 50 and 250 cm')
                else:
                    logger.debug(f"CM validation passed: {height}")
            elif height_unit == 'ft/in':
                if height < 2 or height > 8:
                    logger.error(f"Feet validation failed: {height} not in range [2, 8]")
                    raise ValueError('Height must be between 2 and 8 feet')
                else:
                    logger.debug(f"Feet validation passed: {height}")
            else:
                # Default to cm validation if no unit specified
                if height < 50 or height > 250:
                    logger.error(f"Default CM validation failed: {height} not in range [50, 250]")
                    raise ValueError('Height must be between 50 and 250 cm')
                else:
                    logger.debug(f"Default CM validation passed: {height}")
        return self

    @validator('weight')
    def validate_weight(cls, v, values):
        if v is not None:
            weight_unit = values.get('weight_unit', 'kg')
            if weight_unit == 'kg' and (v < 20 or v > 500):
                raise ValueError('Weight must be between 20 and 500 kg')
            elif weight_unit == 'lbs' and (v < 44.1 or v > 1102.3):
                raise ValueError('Weight must be between 44.1 and 1102.3 lbs')
        return v

    @validator('height_unit')
    def validate_height_unit(cls, v):
        if v and v not in ['cm', 'ft/in']:
            raise ValueError('Height unit must be either "cm" or "ft/in"')
        return v
        
    @validator('weight_unit')
    def validate_weight_unit(cls, v):
        if v and v not in ['kg', 'lbs']:
            raise ValueError('Weight unit must be either "kg" or "lbs"')
        return v
        
    @validator('gender')
    def validate_gender(cls, v):
        if v and v not in ['Male', 'Female', 'Other']:
            raise ValueError('Gender must be either "Male", "Female", or "Other"')
        return v
        
    @validator('profile_picture_url')
    def validate_profile_picture_url(cls, v):
        if v and not re.match(r'^/media/profile_pictures/.*\.(jpg|jpeg|png)$', v):
            raise ValueError('Invalid profile picture URL format')
        return v

class ProfileCreate(ProfileBase):
    """Schema for creating a profile"""
    pass

class ProfileUpdate(ProfileBase):
    """Schema for updating a profile"""
    pass

class ProfilePictureResponse(BaseModel):
    """Schema for profile picture upload response"""
    profile_picture_url: str = Field(..., description="URL to the uploaded profile picture")

class ProfileResponse(ProfileBase):
    """Schema for profile response"""
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    class Config:
        from_attributes = True 