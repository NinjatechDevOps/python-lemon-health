from datetime import datetime
from typing import Optional, Generic, TypeVar
from enum import Enum

from pydantic import BaseModel, Field, validator, EmailStr
import re

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None


class VerificationTypeEnum(str, Enum):
    """Enum for verification types"""
    MOBILE_VERIFICATION = "mobile_verification"
    PASSWORD_RESET = "password_reset"


class UserBase(BaseModel):
    """Base user schema with common attributes"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    mobile_number: str = Field(
        ..., 
        min_length=7, 
        max_length=15, 
        description="mobile_number_count_error"
    )
    country_code: str = Field(
        "+34", 
        min_length=2, 
        max_length=5,
        pattern=r"^\+[0-9]{1,4}$",
        description="country_code_specification_error"
    )  # Default to Spain (+34)
    email: Optional[EmailStr] = None

    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('mobile_digit_error')
        if not re.match(r'^[0-9]{7,15}$', v):
            raise ValueError('mobile_number_count_error')
        return v

    @validator('country_code')
    def validate_country_code(cls, v):
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('country_code_specification_error')
        return v


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=16, description="password_count_error")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError('password_length_error')
        if not any(char.isupper() for char in v):
            raise ValueError('password_uppercase_required')
        if not any(char.islower() for char in v):
            raise ValueError('password_lowercase_required')
        if not any(char.isdigit() for char in v):
            raise ValueError('password_number_required')
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for char in v):
            raise ValueError('password_special_char_required')
        return v


class UserLogin(BaseModel):
    """Schema for user login"""
    mobile_number: str = Field(
        ..., 
        min_length=7, 
        max_length=15, 
        description="mobile_number_count_error"
    )
    country_code: str = Field(
        "+34", 
        min_length=2, 
        max_length=5,
        pattern=r"^\+[0-9]{1,4}$",
        description="country_code_specification_error"
    )  # Default to Spain (+34)
    password: str = Field(..., min_length=1)
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('mobile_digit_error')
        if not re.match(r'^[0-9]{7,15}$', v):
            raise ValueError('mobile_number_count_error')
        return v

    @validator('country_code')
    def validate_country_code(cls, v):
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('country_code_specification_error')
        return v


class VerificationRequest(BaseModel):
    """Schema for verification code request"""
    mobile_number: str = Field(
        ..., 
        min_length=7, 
        max_length=15, 
        description="mobile_number_count_error"
    )
    country_code: str = Field(
        "+34", 
        min_length=2, 
        max_length=5,
        pattern=r"^\+[0-9]{1,4}$",
        description="country_code_specification_error"
    )  # Default to Spain (+34)
    verification_type: VerificationTypeEnum = Field(
        default=VerificationTypeEnum.MOBILE_VERIFICATION,
        description="verification_type_error"
    )
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('mobile_digit_error')
        if not re.match(r'^[0-9]{7,15}$', v):
            raise ValueError('mobile_number_count_error')
        return v

    @validator('country_code')
    def validate_country_code(cls, v):
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('country_code_specification_error')
        return v


class VerificationCodeSubmit(BaseModel):
    """Schema for submitting verification code"""
    mobile_number: str = Field(
        ..., 
        min_length=7, 
        max_length=15, 
        description="mobile_number_count_error"
    )
    country_code: str = Field(
        "+34", 
        min_length=2, 
        max_length=5,
        pattern=r"^\+[0-9]{1,4}$",
        description="country_code_specification_error"
    )  # Default to Spain (+34)
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$", description="verification_code_invalid")
    verification_type: VerificationTypeEnum = Field(
        default=VerificationTypeEnum.MOBILE_VERIFICATION,
        description="verification_type_error"
    )
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('mobile_digit_error')
        if not re.match(r'^[0-9]{7,15}$', v):
            raise ValueError('mobile_number_count_error')
        return v

    @validator('country_code')
    def validate_country_code(cls, v):
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('country_code_specification_error')
        return v

    @validator('code')
    def validate_code(cls, v):
        if not re.match(r'^[0-9]{6}$', v):
            raise ValueError('verification_code_invalid')
        return v


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    mobile_number: str = Field(
        ..., 
        min_length=7, 
        max_length=15, 
        description="mobile_number_count_error"
    )
    country_code: str = Field(
        "+34", 
        min_length=2, 
        max_length=5,
        pattern=r"^\+[0-9]{1,4}$",
        description="country_code_specification_error"
    )  # Default to Spain (+34)
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('mobile_digit_error')
        if not re.match(r'^[0-9]{7,15}$', v):
            raise ValueError('mobile_number_count_error')
        return v

    @validator('country_code')
    def validate_country_code(cls, v):
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('country_code_specification_error')
        return v


class ResetPasswordRequest(BaseModel):
    """Schema for password reset (after OTP verification)"""
    mobile_number: str = Field(
        ..., 
        min_length=7, 
        max_length=15, 
        description="mobile_number_count_error"
    )
    country_code: str = Field(
        "+34", 
        min_length=2, 
        max_length=5,
        pattern=r"^\+[0-9]{1,4}$",
        description="country_code_specification_error"
    )  # Default to Spain (+34)
    new_password: str = Field(..., min_length=8, max_length=16, description="password_count_error")
    
    @validator('mobile_number')
    def validate_mobile_number(cls, v):
        # Remove any spaces or special characters
        v = ''.join(filter(str.isdigit, v))
        if not v:
            raise ValueError('mobile_digit_error')
        if not re.match(r'^[0-9]{7,15}$', v):
            raise ValueError('mobile_number_count_error')
        return v

    @validator('country_code')
    def validate_country_code(cls, v):
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('country_code_specification_error')
        return v
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError('password_length_error')
        if not any(char.isupper() for char in v):
            raise ValueError('password_uppercase_required')
        if not any(char.islower() for char in v):
            raise ValueError('password_lowercase_required')
        if not any(char.isdigit() for char in v):
            raise ValueError('password_number_required')
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for char in v):
            raise ValueError('password_special_char_required')
        return v


class ChangePasswordRequest(BaseModel):
    """Schema for changing password (for authenticated users)"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=16, description="password_count_error")
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 16:
            raise ValueError('password_length_error')
        if not any(char.isupper() for char in v):
            raise ValueError('password_uppercase_required')
        if not any(char.islower() for char in v):
            raise ValueError('password_lowercase_required')
        if not any(char.isdigit() for char in v):
            raise ValueError('password_number_required')
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for char in v):
            raise ValueError('password_special_char_required')
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