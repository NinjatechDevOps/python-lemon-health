import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from apps.auth.models import User
from apps.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from apps.admin_panel.schemas import AdminCreateUserRequest, AdminUpdateUserRequest


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
                return False, {"message": "Invalid mobile number or password"}
            
            # Check if user is admin
            if not user.is_admin:
                return False, {"message": "Access denied. Admin privileges required."}
            
            # Check if user is active
            if not user.is_active:
                return False, {"message": "Account is deactivated"}
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                return False, {"message": "Invalid mobile number or password"}
            
            # Generate tokens
            access_token = create_access_token(subject=str(user.id))
            refresh_token = create_refresh_token(subject=str(user.id))
            
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
        Log admin activity for audit purposes (MVP - just print for now)
        """
        try:
            # For MVP, just print the activity
            print(f"Admin Activity: {action} by admin {admin_user_id} on user {target_user_id}")
            if details:
                print(f"Details: {details}")
        except Exception as e:
            print(f"Error logging admin activity: {e}")
    
    @staticmethod
    async def get_dashboard_stats(
        db: AsyncSession,
        duration: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get dashboard statistics
        """
        try:
            # Calculate date filters
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
                        # Invalid date format, ignore filter
                        pass
            
            # Build base query with date filter
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
                users_created_today = total_users  # In filtered period
                users_created_this_week = total_users  # In filtered period
                users_created_this_month = total_users  # In filtered period
            else:
                # Default calculations (all-time)
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
            print(f"Error getting dashboard stats: {e}")
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
            
            # Add date filters
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                    date_filter = (User.created_at >= start_dt) & (User.created_at < end_dt)
                    base_query = base_query.where(date_filter)
                except ValueError:
                    # Invalid date format, ignore filter
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
            print(f"Error getting users list: {e}")
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
            
            # Tax ID validation removed - not needed for MVP
            
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
            
            # Tax ID validation removed - not needed for MVP
            
            # Update user fields
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
            # Tax ID update removed - not needed for MVP
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
            print(f"Error getting user by ID: {e}")
            return None 