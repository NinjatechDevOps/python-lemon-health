from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from apps.core.db import get_db
from apps.auth.models import User
from apps.admin_panel.deps import get_current_admin_user, get_admin_request_info
from apps.admin_panel.schemas import (
    AdminLoginRequest, AdminLoginResponse, AdminUserResponse, 
    AdminCreateUserRequest, AdminUpdateUserRequest
)
from apps.admin_panel.services import AdminService

# Create admin router
admin_router = APIRouter(tags=["Admin"])


@admin_router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    login_data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin login endpoint
    
    Authenticates admin users with mobile number and password.
    Returns JWT tokens for subsequent API calls.
    """
    try:
        success, result = await AdminService.authenticate_admin(
            db=db,
            mobile_number=login_data.mobile_number,
            password=login_data.password
        )
        
        if not success:
            return {
                "success": False,
                "message": result.get("message", "Authentication failed"),
                "data": None
            }
        
        # Structure response with tokens nested inside token object
        token_data = {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"]
        }
        
        return {
            "success": True,
            "message": "Admin login successful",
            "data": {
                "token": token_data,
                "user": result["user"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Login error: {str(e)}",
            "data": None
        }


@admin_router.get("/dashboard/stats")
async def get_dashboard_stats(
    duration: Optional[str] = Query(None, description="Duration filter: today, week, month, custom"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)"),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get admin dashboard statistics
    
    Returns key metrics like total users, active users, etc.
    """
    try:
        stats = await AdminService.get_dashboard_stats(
            db=db,
            duration=duration,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "message": "Dashboard stats retrieved successfully",
            "data": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving dashboard stats: {str(e)}",
            "data": None
        }


@admin_router.get("/users")
async def get_users_list(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Number of users per page (max 100)"),
    search: Optional[str] = Query(None, description="Search users by name, mobile, email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get paginated list of users with optional filtering and search
    
    Admin can view all users with search and filter capabilities.
    """
    try:
        users, total = await AdminService.get_users_list(
            db=db,
            page=page,
            per_page=per_page,
            search=search,
            is_active=is_active,
            is_verified=is_verified,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate pagination infoand same if admin creating any users via admin Web UI then no need to verify just set true.


        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        # Convert users to response format
        user_responses = []
        for user in users:
            user_responses.append(AdminUserResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                mobile_number=user.mobile_number,
                email=user.email,
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_admin=user.is_admin,
                created_at=user.created_at
            ))
        
        return {
            "success": True,
            "message": "Users retrieved successfully",
            "data": {
                "users": user_responses,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving users: {str(e)}",
            "data": None
        }


@admin_router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific user
    """
    try:
        user = await AdminService.get_user_by_id(db, user_id)
        
        if not user:
            return {
                "success": False,
                "message": f"User with ID {user_id} not found",
                "data": None
            }
        
        user_response = AdminUserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            mobile_number=user.mobile_number,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
        
        return {
            "success": True,
            "message": "User details retrieved successfully",
            "data": user_response
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving user details: {str(e)}",
            "data": None
        }


@admin_router.post("/users")
async def create_user(
    user_data: AdminCreateUserRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new user via admin
    
    Admin can create new user accounts with all necessary information.
    """
    try:
        # Get request info for logging
        request_info = await get_admin_request_info(request)
        
        success, user, message = await AdminService.create_user(
            db=db,
            user_data=user_data,
            admin_user_id=current_admin.id
        )
        
        if not success:
            return {
                "success": False,
                "message": message,
                "data": None
            }
        
        # Log admin activity
        await AdminService.log_admin_activity(
            db=db,
            admin_user_id=current_admin.id,
            action="user_created",
            target_user_id=user.id,
            details={
                "admin_user_id": current_admin.id,
                "created_user_id": user.id,
                "user_data": {
                    "first_name": user_data.first_name,
                    "last_name": user_data.last_name,
                    "mobile_number": user_data.mobile_number,
                    "email": user_data.email,
                    "is_verified": user_data.is_verified
                }
            },
            ip_address=request_info.get("ip_address"),
            user_agent=request_info.get("user_agent")
        )
        
        user_response = AdminUserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            mobile_number=user.mobile_number,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
        
        return {
            "success": True,
            "message": message,
            "data": user_response
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating user: {str(e)}",
            "data": None
        }


@admin_router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: AdminUpdateUserRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update user information via admin
    
    Admin can update user details including status and verification.
    """
    try:
        # Get request info for logging
        request_info = await get_admin_request_info(request)
        
        success, user, message = await AdminService.update_user(
            db=db,
            user_id=user_id,
            user_data=user_data,
            admin_user_id=current_admin.id
        )
        
        if not success:
            return {
                "success": False,
                "message": message,
                "data": None
            }
        
        # Log admin activity
        await AdminService.log_admin_activity(
            db=db,
            admin_user_id=current_admin.id,
            action="user_updated",
            target_user_id=user_id,
            details={
                "admin_user_id": current_admin.id,
                "updated_user_id": user_id,
                "updated_fields": user_data.model_dump(exclude_unset=True)
            },
            ip_address=request_info.get("ip_address"),
            user_agent=request_info.get("user_agent")
        )
        
        user_response = AdminUserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            mobile_number=user.mobile_number,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
        
        return {
            "success": True,
            "message": message,
            "data": user_response
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating user: {str(e)}",
            "data": None
        } 