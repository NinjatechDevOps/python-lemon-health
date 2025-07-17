from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class UserBase(BaseModel):
    """Base user schema with common attributes"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    mobile_number: str = Field(..., min_length=5, max_length=15)
    country_code: str = Field("+34", min_length=2, max_length=5)  # Default to Spain (+34)
    email: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    terms_accepted: bool = Field(...)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('Mobile number must contain digits')
        return v
    
    @validator('terms_accepted')
    def validate_terms_accepted(cls, v):
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    mobile_number: str
    country_code: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    first_name: str
    last_name: str
    mobile_number: str
    country_code: str
    email: Optional[str] = None
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class VerificationRequest(BaseModel):
    """Schema for requesting verification code"""
    mobile_number: str
    country_code: str


class VerificationCodeSubmit(VerificationRequest):
    """Schema for submitting verification code"""
    code: str


class ForgotPasswordRequest(VerificationRequest):
    """Schema for requesting password reset"""
    pass


class ResetPasswordRequest(VerificationCodeSubmit):
    """Schema for resetting password"""
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    refresh_token: str
    token_type: str
    user_id: Optional[int] = None
    message: Optional[str] = None
    require_verification: Optional[bool] = None


class RefreshToken(BaseModel):
    """Schema for refresh token"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Schema for changing password"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class ProfileBase(BaseModel):
    """Base profile schema"""
    date_of_birth: Optional[datetime] = None
    height: Optional[float] = None
    height_unit: Optional[str] = None
    weight: Optional[float] = None
    gender: Optional[str] = None


class ProfileCreate(ProfileBase):
    """Schema for profile creation"""
    pass


class ProfileUpdate(ProfileBase):
    """Schema for profile update"""
    pass


class ProfileResponse(ProfileBase):
    """Schema for profile response"""
    id: int
    user_id: int
    
    class Config:
        from_attributes = True 