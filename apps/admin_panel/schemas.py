from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ValidationInfo, model_validator
from apps.core.phone_validator import validate_phone_number


class AdminLoginRequest(BaseModel):
    """Schema for admin login request"""
    mobile_number: str = Field(..., description="Admin mobile number")
    password: str = Field(..., description="Admin password")


class AdminLoginResponse(BaseModel):
    """Schema for admin login response"""
    success: bool
    message: str
    data: Optional[dict] = None


class AdminUserResponse(BaseModel):
    """Schema for admin user information"""
    id: int
    first_name: str
    last_name: str
    mobile_number: str
    email: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime
    country_code: Optional[str] = None



class AdminDashboardStats(BaseModel):
    """Schema for admin dashboard statistics"""
    total_users: int
    active_users: int
    verified_users: int
    admin_users: int
    users_created_today: int
    users_created_this_week: int
    users_created_this_month: int


class AdminCreateUserRequest(BaseModel):
    """Schema for creating user via admin"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    mobile_number: str = Field(..., min_length=7, max_length=15)
    country_code: str = Field(default="+91", max_length=10)
    password: str = Field(..., min_length=4,max_length=16)
    email: Optional[str] = Field(None, max_length=255)
    is_verified: bool = Field(..., description="Whether the user is verified (admin must explicitly set this)")
    
    # Commented out: Old Pydantic v1 style validator that wasn't working with v2
    # @validator('mobile_number')
    # def validate_mobile_number(cls, v, values):
    #     # Clean the mobile number (remove any non-digit characters)
    #     import re
    #     cleaned = re.sub(r'\D', '', v)
    #     if not cleaned:
    #         raise ValueError('Mobile number must contain digits')
    #     
    #     # Get country code if available
    #     country_code = values.get('country_code', '+91')
    #     
    #     # Validate using country-specific rules
    #     is_valid, error_msg = validate_phone_number(cleaned, country_code)
    #     if not is_valid:
    #         raise ValueError(error_msg)
    #     
    #     return cleaned
    
    # Updated: Using Pydantic v2 field_validator without depending on other fields during validation
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls, v):
        # Clean the mobile number (remove any non-digit characters)
        import re
        cleaned = re.sub(r'\D', '', v)
        if not cleaned:
            raise ValueError('Mobile number must contain digits')
        
        # For initial validation, just check basic length requirements
        # Country-specific validation will be done in model_validator
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError('Mobile number must be between 7 and 15 digits')
        
        return cleaned
    
    # Commented out: Old Pydantic v1 style validator
    # @validator('country_code')
    # def validate_country_code(cls, v):
    #     import re
    #     if not re.match(r'^\+[0-9]{1,4}$', v):
    #         raise ValueError('Country code must start with + followed by 1-4 digits')
    #     return v
    
    # Updated: Using Pydantic v2 field_validator
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v):
        import re
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('Country code must start with + followed by 1-4 digits')
        return v
    
    # Added: Model validator to validate mobile number with country code
    @model_validator(mode='after')
    def validate_mobile_with_country(self):
        """Validate mobile number against country-specific rules"""
        if self.mobile_number and self.country_code:
            is_valid, error_msg = validate_phone_number(self.mobile_number, self.country_code)
            if not is_valid:
                raise ValueError(f"Mobile number validation failed: {error_msg}")
        return self


class AdminUpdateUserRequest(BaseModel):
    """Schema for updating user via admin"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    mobile_number: Optional[str] = Field(None, min_length=7, max_length=15)
    country_code: Optional[str] = Field(None, max_length=10)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    
    # Commented out: Old Pydantic v1 style validator that wasn't working with v2
    # @validator('mobile_number')
    # def validate_mobile_number(cls, v, values):
    #     if v is None:
    #         return v
    #     
    #     # Clean the mobile number (remove any non-digit characters)
    #     import re
    #     cleaned = re.sub(r'\D', '', v)
    #     if not cleaned:
    #         raise ValueError('Mobile number must contain digits')
    #     
    #     # Get country code if available, otherwise use default
    #     country_code = values.get('country_code')
    #     if not country_code:
    #         # If country_code is not provided in update, we'll do basic validation
    #         if len(cleaned) < 7 or len(cleaned) > 15:
    #             raise ValueError('Mobile number must be between 7 and 15 digits')
    #         return cleaned
    #     
    #     # Validate using country-specific rules
    #     is_valid, error_msg = validate_phone_number(cleaned, country_code)
    #     if not is_valid:
    #         raise ValueError(error_msg)
    #     
    #     return cleaned
    
    # Updated: Using Pydantic v2 field_validator without depending on other fields during validation
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile_number(cls, v):
        if v is None:
            return v
        
        # Clean the mobile number (remove any non-digit characters)
        import re
        cleaned = re.sub(r'\D', '', v)
        if not cleaned:
            raise ValueError('Mobile number must contain digits')
        
        # For initial validation, just check basic length requirements
        # Country-specific validation will be done in model_validator
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError('Mobile number must be between 7 and 15 digits')
        
        return cleaned
    
    # Commented out: Old Pydantic v1 style validator
    # @validator('country_code')
    # def validate_country_code(cls, v):
    #     if v is None:
    #         return v
    #     
    #     import re
    #     if not re.match(r'^\+[0-9]{1,4}$', v):
    #         raise ValueError('Country code must start with + followed by 1-4 digits')
    #     return v
    
    # Updated: Using Pydantic v2 field_validator
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v):
        if v is None:
            return v
        
        import re
        if not re.match(r'^\+[0-9]{1,4}$', v):
            raise ValueError('Country code must start with + followed by 1-4 digits')
        return v
    
    # Added: Model validator to validate mobile number with country code
    @model_validator(mode='after')
    def validate_mobile_with_country(self):
        """Validate mobile number against country-specific rules"""
        if self.mobile_number and self.country_code:
            is_valid, error_msg = validate_phone_number(self.mobile_number, self.country_code)
            if not is_valid:
                raise ValueError(f"Mobile number validation failed: {error_msg}")
        return self


class AdminUserListResponse(BaseModel):
    """Schema for paginated user list response"""
    users: List[AdminUserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

# Admin Chat History Schemas
class AdminChatMessageResponse(BaseModel):
    """Schema for admin chat message response"""
    id: int
    mid: str
    role: str
    content: str
    created_at: str
    user_id: Optional[int] = None
    profile_picture_url : str

class AdminChatHistoryResponse(BaseModel):
    """Schema for admin chat history detail response"""
    conv_id: str
    user_id: int
    user_name: str
    user_mobile: str
    prompt_type: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    messages: List[AdminChatMessageResponse]

class AdminChatHistoryListItem(BaseModel):
    """Schema for admin chat history list item"""
    conv_id: str
    user_id: int
    user_name: str
    user_mobile: str
    prompt_type: str
    title: Optional[str] = None
    message_count: int
    last_message_preview: Optional[str] = None
    created_at: str
    updated_at: str
    profile_picture_url : str

class AdminChatHistoryListResponse(BaseModel):
    """Schema for admin chat history list response"""
    conversations: List[AdminChatHistoryListItem]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

# Out-of-scope message management schemas
class AdminOutOfScopeMessageResponse(BaseModel):
    """Schema for out-of-scope chat message response"""
    id: int
    mid: str
    conversation_id: int
    role: str
    content: str
    created_at: str
    user_id: Optional[int] = None
    conv_id: Optional[str] = None
    prompt_type: Optional[str] = None
    title: Optional[str] = None

class AdminUpdateOutOfScopeRequest(BaseModel):
    """Schema for updating is_out_of_scope flag"""
    is_out_of_scope: bool = Field(..., description="Whether the message is out of scope")

class AdminOutOfScopeListResponse(BaseModel):
    """Schema for out-of-scope messages list response"""
    messages: List[AdminOutOfScopeMessageResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool 


# Translation Management Schemas
class TranslationCreateRequest(BaseModel):
    """Schema for creating a translation"""
    keyword: str = Field(..., min_length=1, max_length=255, description="Unique keyword identifier")
    en: str = Field(..., min_length=1, description="English translation")
    es: str = Field(..., min_length=1, description="Spanish translation")
    is_deletable: Optional[bool] = Field(None, description="Whether the translation can be deleted")


class TranslationUpdateRequest(BaseModel):
    """Schema for updating a translation"""
    keyword: Optional[str] = Field(None, min_length=1, max_length=255, description="Unique keyword identifier")
    en: Optional[str] = Field(None, min_length=1, description="English translation")
    es: Optional[str] = Field(None, min_length=1, description="Spanish translation")
    is_deletable: Optional[bool] = Field(None, description="Whether the translation can be deleted")


class TranslationResponse(BaseModel):
    """Schema for translation response"""
    id: int
    keyword: str
    en: str
    es: str
    is_deleted: bool
    is_deletable: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None


class TranslationListResponse(BaseModel):
    """Schema for paginated translation list response"""
    translations: List[TranslationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool