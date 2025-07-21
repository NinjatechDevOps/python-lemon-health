from datetime import datetime
from typing import Optional

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
    password: str = Field(..., min_length=8, max_length=16, description="Password must be 8-16 characters")
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('Mobile number must contain digits')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError('Password must be between 8 and 16 characters')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for char in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    mobile_number: str = Field(..., min_length=5, max_length=15)
    country_code: str = Field("+34", min_length=2, max_length=5)  # Default to Spain (+34)
    password: str = Field(..., min_length=1)
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('Mobile number must contain digits')
        return v


class VerificationRequest(BaseModel):
    """Schema for verification code request"""
    mobile_number: str = Field(..., min_length=5, max_length=15)
    country_code: str = Field("+34", min_length=2, max_length=5)  # Default to Spain (+34)
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('Mobile number must contain digits')
        return v


class VerificationCodeSubmit(BaseModel):
    """Schema for submitting verification code"""
    mobile_number: str = Field(..., min_length=5, max_length=15)
    country_code: str = Field("+34", min_length=2, max_length=5)  # Default to Spain (+34)
    code: str = Field(..., min_length=6, max_length=6)
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('Mobile number must contain digits')
        return v


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    mobile_number: str = Field(..., min_length=5, max_length=15)
    country_code: str = Field("+34", min_length=2, max_length=5)  # Default to Spain (+34)
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('Mobile number must contain digits')
        return v


class ResetPasswordRequest(BaseModel):
    """Schema for password reset"""
    mobile_number: str = Field(..., min_length=5, max_length=15)
    country_code: str = Field("+34", min_length=2, max_length=5)  # Default to Spain (+34)
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=16, description="Password must be 8-16 characters")
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('Mobile number must contain digits')
        return v
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError('Password must be between 8 and 16 characters')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for char in v):
            raise ValueError('Password must contain at least one special character')
        return v


class ChangePasswordRequest(BaseModel):
    """Schema for changing password (for authenticated users)"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=16, description="Password must be 8-16 characters")
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError('Password must be between 8 and 16 characters')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for char in v):
            raise ValueError('Password must contain at least one special character')
        return v


class Token(BaseModel):
    """Schema for JWT token"""
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class RefreshToken(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


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


class LogoutRequest(BaseModel):
    """Schema for logout request"""
    access_token: str
    refresh_token: Optional[str] = None 