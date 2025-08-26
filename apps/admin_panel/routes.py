from typing import Dict, Any, Optional, Tuple, List
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.core.db import get_db
from apps.auth.models import User
from apps.admin_panel.deps import get_current_admin_user, get_admin_request_info
from apps.admin_panel.schemas import (
    AdminLoginRequest, AdminLoginResponse, AdminUserResponse, 
    AdminCreateUserRequest, AdminUpdateUserRequest,
    AdminChatHistoryListResponse
)
from apps.admin_panel.services import AdminService
from apps.core.logging_config import get_logger

logger = get_logger(__name__)

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
        logger.error(f"Login error: {str(e)}")
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
        logger.error(f"Error retrieving dashboard stats: {str(e)}")
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
                country_code=user.country_code,
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
        logger.error(f"Error retrieving users: {str(e)}")
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
            country_code=user.country_code,
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
        logger.error(f"Error retrieving user details: {str(e)}")
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
            country_code=user.country_code,
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
        logger.error(f"Error creating user: {str(e)}")
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
            country_code=user.country_code,
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
        logger.error(f"Error updating user: {str(e)}")
        return {
            "success": False,
            "message": f"Error updating user: {str(e)}",
            "data": None
        }

# Admin Chat History Routes
@admin_router.get("/chat/history")
async def get_admin_chat_history_list(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Number of conversations per page (max 100)"),
    search: Optional[str] = Query(None, description="Search conversations by title, user name, or mobile"),
    user_id: Optional[int] = Query(None, description="Filter by specific user ID"),
    prompt_type: Optional[str] = Query(None, description="Filter by prompt type (nutrition, exercise, etc.)"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get paginated list of all chat conversations for admin
    
    Admin can view all chat conversations with search and filter capabilities.
    """
    try:
        conversations, total = await AdminService.get_admin_chat_history_list(
            db=db,
            page=page,
            per_page=per_page,
            search=search,
            user_id=user_id,
            prompt_type=prompt_type,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        # Convert to proper schema format
        from apps.admin_panel.schemas import AdminChatHistoryListItem
        
        conversation_items = []
        for conv in conversations:
            conversation_items.append(AdminChatHistoryListItem(
                conv_id=conv["conv_id"],
                user_id=conv["user_id"],
                user_name=conv["user_name"],
                user_mobile=conv["user_mobile"],
                prompt_type=conv["prompt_type"],
                title=conv["title"],
                message_count=conv["message_count"],
                last_message_preview=conv["last_message_preview"],
                created_at=conv["created_at"],
                updated_at=conv["updated_at"],
                profile_picture_url = conv['profile_picture_url']
            ))
        
        response_data = AdminChatHistoryListResponse(
            conversations=conversation_items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        return {
            "success": True,
            "message": "Chat history list retrieved successfully",
            "data": response_data
        }
        
    except Exception as e:
        logger.error(f"Error retrieving chat history list: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving chat history list: {str(e)}",
            "data": None
        }


@admin_router.get("/chat/history/{conv_id}")
async def get_admin_chat_history_detail(
    conv_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed chat history for a specific conversation
    
    Admin can view complete conversation details including all messages.
    """
    try:
        conversation_detail = await AdminService.get_admin_chat_history_detail(
            db=db,
            conv_id=conv_id
        )
        
        if not conversation_detail:
            return {
                "success": False,
                "message": f"Conversation with ID {conv_id} not found",
                "data": None
            }
        
        # Convert to proper schema format
        from apps.admin_panel.schemas import AdminChatMessageResponse, AdminChatHistoryResponse
        
        messages_response = []
        for msg in conversation_detail["messages"]:
            messages_response.append(AdminChatMessageResponse(
                id=msg["id"],
                mid=msg["mid"],
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"],
                user_id=msg["user_id"],
                profile_picture_url = msg['profile_picture_url']
            ))
        
        response_data = AdminChatHistoryResponse(
            conv_id=conversation_detail["conv_id"],
            user_id=conversation_detail["user_id"],
            user_name=conversation_detail["user_name"],
            user_mobile=conversation_detail["user_mobile"],
            prompt_type=conversation_detail["prompt_type"],
            title=conversation_detail["title"],
            created_at=conversation_detail["created_at"],
            updated_at=conversation_detail["updated_at"],
            messages=messages_response
        )
        
        return {
            "success": True,
            "message": "Chat history detail retrieved successfully",
            "data": response_data
        }
        
    except Exception as e:
        logger.error(f"Error retrieving chat history detail: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving chat history detail: {str(e)}",
            "data": None
        }

@admin_router.get("/chat-messages/out-of-scope")
async def list_out_of_scope_messages(
    user_id: Optional[int] = Query(None, description="Filter by conversation owner user ID"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Number of messages per page (max 100)"),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get all out-of-scope chat messages with pagination.
    
    Returns messages where is_out_of_scope = True.
    Optionally filter by user_id to see messages from specific users.
    """
    try:
        # Get out-of-scope messages
        messages = await AdminService.get_out_of_scope_messages(
            db=db,
            user_id=user_id,
            page=page,
            per_page=per_page
        )
        
        # Get total count for pagination
        total_count = await AdminService.get_out_of_scope_messages_count(
            db=db,
            user_id=user_id
        )
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        # Convert to response format
        messages_response = []
        for msg in messages:
            messages_response.append({
            "id": msg["id"],
            "mid": msg["mid"],
            "conversation_id": msg["conversation_id"],
            "role": msg["role"],
            "content": msg["content"],
            "created_at": msg["created_at"],
            "user_id": msg["user_id"],
            "conv_id": msg["conv_id"],
            "prompt_type": msg["prompt_type"],
            "title": msg["title"],
            "first_name": msg.get("first_name"),
            "last_name": msg.get("last_name"),
            "profile_picture_url": msg.get("profile_picture_url"),
            "is_out_of_scope": msg["is_out_of_scope"]
        })
                
        response_data = {
            "messages": messages_response,
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
        
        return {
            "success": True,
            "message": "Out-of-scope messages retrieved successfully",
            "data": response_data
        }
        
    except Exception as e:
        logger.error(f"Error retrieving out-of-scope messages: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving out-of-scope messages: {str(e)}",
            "data": None
        }

@admin_router.patch("/chat-messages/{mid}/out-of-scope")
async def update_out_of_scope_message(
    mid: str,
    req: Dict[str, Any],
    current_user: User = Depends(get_current_admin_user),  
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update the is_out_of_scope flag for a specific message.
    
    Only the message owner or an admin can update this flag.
    Requires valid mid and is_out_of_scope boolean in request body.
    """
    try:
        # Validate request body
        if "is_out_of_scope" not in req:
            return {
                "success": False,
                "message": "Missing required field: is_out_of_scope",
                "data": None
            }
        
        is_out_of_scope = req["is_out_of_scope"]
        if not isinstance(is_out_of_scope, bool):
            return {
                "success": False,
                "message": "is_out_of_scope must be a boolean value",
                "data": None
            }
        
        # Update the flag
        success, updated_message, message = await AdminService.update_out_of_scope_flag(
            db=db,
            mid=mid,
            is_out_of_scope=is_out_of_scope,
            acting_user=current_user
        )
        
        if not success:
            return {
                "success": False,
                "message": message,
                "data": None
            }
        
        return {
            "success": True,
            "message": message,
            "data": updated_message
        }
        
    except Exception as e:
        logger.error(f"Error updating out-of-scope flag: {str(e)}")
        return {
            "success": False,
            "message": f"Error updating out-of-scope flag: {str(e)}",
            "data": None
        } 