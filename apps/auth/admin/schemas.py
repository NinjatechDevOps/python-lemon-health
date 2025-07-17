from typing import Optional, List
from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """Base schema for role data"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Schema for role creation"""
    pass


class RoleUpdate(RoleBase):
    """Schema for role update"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)


class RoleResponse(RoleBase):
    """Schema for role response"""
    id: int
    
    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    """Base schema for permission data"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    """Schema for permission creation"""
    pass


class PermissionUpdate(PermissionBase):
    """Schema for permission update"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)


class PermissionResponse(PermissionBase):
    """Schema for permission response"""
    id: int
    
    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Schema for role with permissions"""
    permissions: List[PermissionResponse] = []


class UserAdminUpdate(BaseModel):
    """Schema for admin user update"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserWithRoles(BaseModel):
    """Schema for user with roles"""
    id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    mobile_number: str
    country_code: str
    is_active: bool
    is_verified: bool
    roles: List[RoleResponse] = []
    
    class Config:
        from_attributes = True


class RoleAssignment(BaseModel):
    """Schema for role assignment"""
    role_id: int


class PermissionAssignment(BaseModel):
    """Schema for permission assignment"""
    permission_id: int 