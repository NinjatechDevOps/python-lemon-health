from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


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
    mobile_number: str = Field(..., min_length=10, max_length=20)
    country_code: str = Field(default="+91", max_length=10)
    password: str = Field(..., min_length=6)
    email: Optional[str] = Field(None, max_length=255)
    is_verified: bool = Field(..., description="Whether the user is verified (admin must explicitly set this)")


class AdminUpdateUserRequest(BaseModel):
    """Schema for updating user via admin"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    mobile_number: Optional[str] = Field(None, min_length=10, max_length=20)
    country_code: Optional[str] = Field(None, max_length=10)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


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

class AdminChatHistoryListResponse(BaseModel):
    """Schema for admin chat history list response"""
    conversations: List[AdminChatHistoryListItem]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool 