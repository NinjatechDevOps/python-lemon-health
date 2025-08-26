import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from apps.auth.models import User
from apps.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from apps.admin_panel.schemas import AdminCreateUserRequest, AdminUpdateUserRequest
from apps.chat.models import Conversation, ChatMessage, Prompt
from apps.core.logging_config import get_logger
from apps.profile.models import Profile
from apps.profile.utils import convert_relative_to_complete_url

logger = get_logger(__name__)


class AdminService:
    """Service for admin operations"""
    
    @staticmethod
    async def authenticate_admin(
        db: AsyncSession, 
        mobile_number: str, 
        password: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Authenticate admin user
        Returns:
            Tuple[bool, Optional[Dict]]: (success, result_data)
        """
        try:
            # Find user by mobile number
            result = await db.execute(
                select(User).where(User.mobile_number == mobile_number)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False, {"message": "You're not registered yet. Please sign up to continue."}
            
            # Check if user is admin
            if not user.is_admin:
                return False, {"message": "Access denied. Admin privileges required."}
            
            # Check if user is active
            if not user.is_active:
                return False, {"message": "Account is deactivated"}
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                return False, {"message": "Looks like you've entered an incorrect password. Please try again."}
            
            # Generate tokens
            access_token = create_access_token(
                subject=str(user.id),
                extra_data={"is_admin": user.is_admin}
            )
            refresh_token = create_refresh_token(
                subject=str(user.id),
                extra_data={"is_admin": user.is_admin}
            )
            
            return True, {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "mobile_number": user.mobile_number,
                    "email": user.email,
                    "is_admin": user.is_admin
                }
            }
            
        except Exception as e:
            return False, {"message": f"Authentication error: {str(e)}"}
    
    @staticmethod
    async def log_admin_activity(
        db: AsyncSession,
        admin_user_id: int,
        action: str,
        target_user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log admin activity for audit purposes (now uses logger)
        """
        try:
            logger.info(f"Admin Activity: {action} by admin {admin_user_id} on user {target_user_id}")
            if details:
                logger.info(f"Details: {details}")
        except Exception as e:
            logger.error(f"Error logging admin activity: {e}")
    
    @staticmethod
    async def get_dashboard_stats(
        db: AsyncSession,
        duration: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get dashboard statistics with optional date filtering
        """
        try:
            # Calculate date filters based on duration or custom range
            date_filter = None
            if duration or start_date or end_date:
                if duration == "today":
                    today = datetime.utcnow().date()
                    date_filter = func.date(User.created_at) == today
                elif duration == "week":
                    week_ago = datetime.utcnow() - timedelta(days=7)
                    date_filter = User.created_at >= week_ago
                elif duration == "month":
                    month_ago = datetime.utcnow() - timedelta(days=30)
                    date_filter = User.created_at >= month_ago
                elif duration == "custom" and start_date and end_date:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                        date_filter = (User.created_at >= start_dt) & (User.created_at < end_dt)
                    except ValueError:
                        pass
            
            # Build base query with date filter if present
            base_query = select(User)
            if date_filter:
                base_query = base_query.where(date_filter)
            
            # Total users (with date filter if applied)
            total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
            total_users = total_result.scalar()
            
            # Active users (with date filter if applied)
            active_query = base_query.where(User.is_active == True)
            active_result = await db.execute(select(func.count()).select_from(active_query.subquery()))
            active_users = active_result.scalar()
            
            # Verified users (with date filter if applied)
            verified_query = base_query.where(User.is_verified == True)
            verified_result = await db.execute(select(func.count()).select_from(verified_query.subquery()))
            verified_users = verified_result.scalar()
            
            # Admin users (with date filter if applied)
            admin_query = base_query.where(User.is_admin == True)
            admin_result = await db.execute(select(func.count()).select_from(admin_query.subquery()))
            admin_users = admin_result.scalar()
            
            # Users created in filtered period
            if date_filter:
                users_created_today = total_users
                users_created_this_week = total_users
                users_created_this_month = total_users
            else:
                # Calculate users created today, this week, this month (all-time)
                today = datetime.utcnow().date()
                today_result = await db.execute(
                    select(func.count(User.id)).where(func.date(User.created_at) == today)
                )
                users_created_today = today_result.scalar()
                
                week_ago = datetime.utcnow() - timedelta(days=7)
                week_result = await db.execute(
                    select(func.count(User.id)).where(User.created_at >= week_ago))
                users_created_this_week = week_result.scalar()
                
                month_ago = datetime.utcnow() - timedelta(days=30)
                month_result = await db.execute(
                    select(func.count(User.id)).where(User.created_at >= month_ago))
                users_created_this_month = month_result.scalar()
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "verified_users": verified_users,
                "admin_users": admin_users,
                "users_created_today": users_created_today,
                "users_created_this_week": users_created_this_week,
                "users_created_this_month": users_created_this_month
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "verified_users": 0,
                "admin_users": 0,
                "users_created_today": 0,
                "users_created_this_week": 0,
                "users_created_this_month": 0
            }
    
    @staticmethod
    async def get_users_list(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """
        Get paginated list of users with optional filtering
        """
        try:
            # Build base query
            base_query = select(User)
            
            # Add date filters if provided
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                    date_filter = (User.created_at >= start_dt) & (User.created_at < end_dt)
                    base_query = base_query.where(date_filter)
                except ValueError:
                    pass
            
            # Add search filter
            if search:
                search_filter = (
                    User.first_name.ilike(f"%{search}%") |
                    User.last_name.ilike(f"%{search}%") |
                    User.mobile_number.ilike(f"%{search}%") |
                    User.email.ilike(f"%{search}%")
                )
                base_query = base_query.where(search_filter)
            
            # Add status filters
            if is_active is not None:
                base_query = base_query.where(User.is_active == is_active)
            
            if is_verified is not None:
                base_query = base_query.where(User.is_verified == is_verified)
            base_query = base_query.where(User.is_admin == False)
            # Get total count
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Get paginated results
            offset = (page - 1) * per_page
            users_query = (
                base_query
                .order_by(desc(User.created_at))
                .offset(offset)
                .limit(per_page)
            )
            
            users_result = await db.execute(users_query)
            users = users_result.scalars().all()
            
            return users, total
            
        except Exception as e:
            logger.error(f"Error getting users list: {e}")
            return [], 0
    
    @staticmethod
    async def create_user(
        db: AsyncSession,
        user_data: AdminCreateUserRequest,
        admin_user_id: int
    ) -> Tuple[bool, Optional[User], str]:
        """
        Create a new user via admin
        Returns:
            Tuple[bool, Optional[User], str]: (success, user, message)
        """
        try:
            # Check if mobile number already exists
            existing_user = await db.execute(
                select(User).where(User.mobile_number == user_data.mobile_number)
            )
            if existing_user.scalar_one_or_none():
                return False, None, "Mobile number already exists"
            
            # Check if email already exists (if provided)
            if user_data.email:
                existing_email = await db.execute(
                    select(User).where(User.email == user_data.email)
                )
                if existing_email.scalar_one_or_none():
                    return False, None, "Email already exists"
            
            # Create new user
            hashed_password = get_password_hash(user_data.password)
            
            new_user = User(
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                mobile_number=user_data.mobile_number,
                country_code=user_data.country_code,
                hashed_password=hashed_password,
                email=user_data.email,
                is_verified=user_data.is_verified,
                is_active=True,
                is_admin=False
            )
            
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            return True, new_user, "User created successfully"
            
        except Exception as e:
            await db.rollback()
            return False, None, f"Error creating user: {str(e)}"
    
    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: int,
        user_data: AdminUpdateUserRequest,
        admin_user_id: int
    ) -> Tuple[bool, Optional[User], str]:
        """
        Update user via admin
        Returns:
            Tuple[bool, Optional[User], str]: (success, user, message)
        """
        try:
            # Get user
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                return False, None, "User not found"
            
            # Check for duplicate mobile number (if being updated)
            if user_data.mobile_number and user_data.mobile_number != user.mobile_number:
                existing_user = await db.execute(
                    select(User).where(User.mobile_number == user_data.mobile_number)
                )
                if existing_user.scalar_one_or_none():
                    return False, None, "Mobile number already exists"
            
            # Check for duplicate email (if being updated)
            if user_data.email and user_data.email != user.email:
                existing_email = await db.execute(
                    select(User).where(User.email == user_data.email)
                )
                if existing_email.scalar_one_or_none():
                    return False, None, "Email already exists"
            
            # Update user fields if provided
            if user_data.first_name is not None:
                user.first_name = user_data.first_name
            if user_data.last_name is not None:
                user.last_name = user_data.last_name
            if user_data.mobile_number is not None:
                user.mobile_number = user_data.mobile_number
            if user_data.country_code is not None:
                user.country_code = user_data.country_code
            if user_data.email is not None:
                user.email = user_data.email
            if user_data.is_active is not None:
                user.is_active = user_data.is_active
            if user_data.is_verified is not None:
                user.is_verified = user_data.is_verified
            
            await db.commit()
            await db.refresh(user)
            
            return True, user, "User updated successfully"
            
        except Exception as e:
            await db.rollback()
            return False, None, f"Error updating user: {str(e)}"
    
    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: int
    ) -> Optional[User]:
        """
        Get user by ID
        """
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    # Admin Chat History Methods
    @staticmethod
    async def get_admin_chat_history_list(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        user_id: Optional[int] = None,
        prompt_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of all chat conversations for admin
        """
        try:
            # Build base query with user and prompt info
            base_query = (
                select(Conversation, User, Profile,Prompt)
                .join(User, Conversation.user_id == User.id)
                .join(Profile, Profile.user_id == User.id)
                .join(Prompt, Conversation.prompt_id == Prompt.id)
            )
            
            # Add date filters if provided
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                    date_filter = (Conversation.created_at >= start_dt) & (Conversation.created_at < end_dt)
                    base_query = base_query.where(date_filter)
                except ValueError:
                    pass
            
            # Add search filter
            if search:
                search_filter = (
                    Conversation.title.ilike(f"%{search}%") |
                    User.first_name.ilike(f"%{search}%") |
                    User.last_name.ilike(f"%{search}%") |
                    User.mobile_number.ilike(f"%{search}%")
                )
                base_query = base_query.where(search_filter)
            
            # Add user filter
            if user_id:
                base_query = base_query.where(Conversation.user_id == user_id and Profile.user_id == user_id)
            
            # Add prompt type filter
            if prompt_type:
                base_query = base_query.where(Prompt.prompt_type == prompt_type)
            
            # Get total count
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Get paginated results
            offset = (page - 1) * per_page
            conversations_query = (
                base_query
                .order_by(desc(Conversation.updated_at))
                .offset(offset)
                .limit(per_page)
            )
            
            conversations_result = await db.execute(conversations_query)
            conversations = conversations_result.all()
            # Build response data
            conversation_items = []
            for conv, user, profile,prompt in conversations:
                # Get message count and last message preview
                message_count_result = await db.execute(
                    select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conv.id)
                )
                message_count = message_count_result.scalar()
                
                # Get last message preview
                last_message_result = await db.execute(
                    select(ChatMessage.content)
                    .where(ChatMessage.conversation_id == conv.id)
                    .order_by(desc(ChatMessage.created_at))
                    .limit(1)
                )
                last_message = last_message_result.scalar_one_or_none()
                last_message_preview = last_message[:100] + "..." if last_message and len(last_message) > 100 else last_message
                
                conversation_items.append({
                    "conv_id": conv.conv_id,
                    "user_id": user.id,
                    "user_name": f"{user.first_name} {user.last_name}".strip(),
                    "user_mobile": user.mobile_number,
                    "prompt_type": prompt.prompt_type.value,
                    "title": conv.title,
                    "message_count": message_count,
                    "last_message_preview": last_message_preview,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "profile_picture_url":convert_relative_to_complete_url(profile.profile_picture_url)
                })
            
            return conversation_items, total
            
        except Exception as e:
            logger.error(f"Error getting admin chat history list: {e}")
            return [], 0
    
    @staticmethod
    async def get_admin_chat_history_detail(
        db: AsyncSession,
        conv_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed chat history for a specific conversation
        """
        try:
            # Get conversation with user and prompt info
            result = await db.execute(
                select(Conversation, User, Profile,Prompt)
                .join(User, Conversation.user_id == User.id)
                .join(Profile,Profile.user_id == Conversation.user_id)
                .join(Prompt, Conversation.prompt_id == Prompt.id)
                .where(Conversation.conv_id == conv_id)
            )
            conversation_data = result.first()
            if not conversation_data:
                return None
            
            conv, user, profile, prompt = conversation_data
            
            # Get all messages for this conversation
            messages_result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conv.id)
                .order_by(ChatMessage.created_at)
            )
            messages = messages_result.scalars().all()
            
            # Build messages response
            messages_response = []
            for msg in messages:
                messages_response.append({
                    "id": msg.id,
                    "mid": msg.mid,
                    "role": msg.role.value,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "user_id": msg.user_id,
                    "profile_picture_url":convert_relative_to_complete_url(profile.profile_picture_url) if msg.user_id else ""
                })
            return {
                "conv_id": conv.conv_id,
                "user_id": user.id,
                "user_name": f"{user.first_name} {user.last_name}".strip(),
                "user_mobile": user.mobile_number,
                "prompt_type": prompt.prompt_type.value,
                "title": conv.title,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "messages": messages_response,
            }
            
        except Exception as e:
            logger.error(f"Error getting admin chat history detail: {e}")
            return None

    @staticmethod
    async def get_out_of_scope_messages(
        db: AsyncSession,
        user_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> List[Dict[str, Any]]:
        """Return out-of-scope user messages, optionally filtered by conversation owner user_id, with user profile info."""
        try:
            offset = (page - 1) * per_page
            from apps.profile.models import Profile
            from apps.profile.utils import convert_relative_to_complete_url
            query = (
                select(
                    ChatMessage.id,
                    ChatMessage.mid,
                    ChatMessage.conversation_id,
                    ChatMessage.role,
                    ChatMessage.content,
                    ChatMessage.created_at,
                    ChatMessage.user_id,
                    ChatMessage.is_out_of_scope,
                    Conversation.conv_id,
                    Prompt.prompt_type,
                    Conversation.title,
                    User.first_name,
                    User.last_name,
                    Profile.profile_picture_url
                )
                .join(Conversation, ChatMessage.conversation_id == Conversation.id)
                .join(Prompt, Conversation.prompt_id == Prompt.id)
                .outerjoin(User, ChatMessage.user_id == User.id)
                .outerjoin(Profile, User.id == Profile.user_id)
                .where(ChatMessage.is_out_of_scope == True)
                .where(ChatMessage.role == "user")
            )
            if user_id:
                query = query.where(Conversation.user_id == user_id)
            query = query.order_by(desc(ChatMessage.created_at)).offset(offset).limit(per_page)
            result = await db.execute(query)
            messages = result.all()
            messages_list = []
            for msg in messages:
                messages_list.append({
                    "id": msg.id,
                    "mid": msg.mid,
                    "conversation_id": msg.conversation_id,
                    "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "user_id": msg.user_id,
                    "conv_id": msg.conv_id,
                    "prompt_type": msg.prompt_type.value if hasattr(msg.prompt_type, 'value') else str(msg.prompt_type),
                    "title": msg.title,
                    "first_name": msg.first_name,
                    "last_name": msg.last_name,
                    "profile_picture_url": convert_relative_to_complete_url(msg.profile_picture_url) if msg.profile_picture_url else None,
                    "is_out_of_scope": msg.is_out_of_scope
                })
            return messages_list
        except Exception as e:
            logger.error(f"Error getting out-of-scope messages: {e}")
            return []

    @staticmethod
    async def get_out_of_scope_messages_count(
        db: AsyncSession,
        user_id: Optional[int] = None
    ) -> int:
        """Get total count of out-of-scope user messages"""
        try:
            query = (
                select(func.count(ChatMessage.id))
                .join(Conversation, ChatMessage.conversation_id == Conversation.id)
                .where(ChatMessage.is_out_of_scope == True)
                .where(ChatMessage.role == "user")
            )
            if user_id:
                query = query.where(Conversation.user_id == user_id)
            result = await db.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting out-of-scope messages count: {e}")
            return 0

    @staticmethod
    async def update_out_of_scope_flag(
        db: AsyncSession,
        mid: str,
        is_out_of_scope: bool,
        acting_user: User
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Update is_out_of_scope for a message by mid. Only admin or owner allowed."""
        try:
            # Find the message
            result = await db.execute(
                select(ChatMessage).where(ChatMessage.mid == mid)
            )
            message = result.scalar_one_or_none()
            
            if not message:
                return False, None, "Message not found"
            
            # Get conversation to check ownership
            conv_result = await db.execute(
                select(Conversation).where(Conversation.id == message.conversation_id)
            )
            conversation = conv_result.scalar_one_or_none()
            
            if not conversation:
                return False, None, "Conversation not found"
            
            # Check authorization: only admin or message owner can update
            if not acting_user.is_admin and conversation.user_id != acting_user.id:
                return False, None, "Access denied. Only admin or message owner can update this flag"
            
            # Update the flag
            message.is_out_of_scope = is_out_of_scope
            await db.commit()
            await db.refresh(message)
            
            # Get updated message data with conversation info
            updated_result = await db.execute(
                select(
                    ChatMessage.id,
                    ChatMessage.mid,
                    ChatMessage.conversation_id,
                    ChatMessage.role,
                    ChatMessage.content,
                    ChatMessage.created_at,
                    ChatMessage.user_id,
                    ChatMessage.is_out_of_scope,
                    Conversation.conv_id,
                    Prompt.prompt_type,
                    Conversation.title
                )
                .join(Conversation, ChatMessage.conversation_id == Conversation.id)
                .join(Prompt, Conversation.prompt_id == Prompt.id)
                .where(ChatMessage.mid == mid)
            )
            updated_msg = updated_result.first()
            
            if updated_msg:
                return True, {
                    "id": updated_msg.id,
                    "mid": updated_msg.mid,
                    "conversation_id": updated_msg.conversation_id,
                    "role": updated_msg.role.value if hasattr(updated_msg.role, 'value') else str(updated_msg.role),
                    "content": updated_msg.content,
                    "created_at": updated_msg.created_at.isoformat(),
                    "user_id": updated_msg.user_id,
                    "is_out_of_scope": updated_msg.is_out_of_scope,
                    "conv_id": updated_msg.conv_id,
                    "prompt_type": updated_msg.prompt_type.value if hasattr(updated_msg.prompt_type, 'value') else str(updated_msg.prompt_type),
                    "title": updated_msg.title
                }, "Message updated successfully"
            
            return False, None, "Failed to retrieve updated message"
            
        except Exception as e:
            logger.error(f"Error updating out-of-scope flag: {e}")
            return False, None, f"Error updating message: {str(e)}" 