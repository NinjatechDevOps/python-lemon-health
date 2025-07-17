from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.auth.providers.base import AuthProvider, AuthProviderFactory
from apps.accounts.models import User, VerificationType
from apps.core.security import get_password_hash, verify_password
# Import otp_service after the class definition to avoid circular imports

class MobileAuthProvider(AuthProvider):
    """Mobile number-based authentication provider"""
    
    async def authenticate(self, db: AsyncSession, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a user with mobile number and password"""
        mobile_number = credentials.get("mobile_number")
        country_code = credentials.get("country_code")
        password = credentials.get("password")
        
        if not all([mobile_number, country_code, password]):
            return {"success": False, "message": "Missing required credentials"}
        
        # Find user by mobile number
        query = select(User).where(
            User.mobile_number == mobile_number,
            User.country_code == country_code
        )
        result = await db.execute(query)
        user = result.scalars().first()
        
        # Check if user exists and password is correct
        if not user or not verify_password(password, user.hashed_password):
            return {"success": False, "message": "Incorrect mobile number or password"}
        
        # Check if user is active
        if not user.is_active:
            return {"success": False, "message": "Inactive user"}
        
        return {
            "success": True,
            "user_id": user.id,
            "is_verified": user.is_verified,
            "require_verification": not user.is_verified
        }
    
    async def register(self, db: AsyncSession, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user with mobile number"""
        # Extract user data
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")
        mobile_number = user_data.get("mobile_number")
        country_code = user_data.get("country_code")
        email = user_data.get("email")
        password = user_data.get("password")
        
        if not all([first_name, mobile_number, country_code, password]):
            return {"success": False, "message": "Missing required fields"}
        
        # Check if user with this mobile number already exists
        query = select(User).where(
            User.mobile_number == mobile_number,
            User.country_code == country_code
        )
        result = await db.execute(query)
        existing_user = result.scalars().first()
        
        if existing_user:
            return {"success": False, "message": "User with this mobile number already exists"}
        
        try:
            # Create new user with unverified status
            user = User(
                first_name=first_name,
                last_name=last_name or "",
                mobile_number=mobile_number,
                country_code=country_code,
                email=email or None,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_verified=False
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Import here to avoid circular imports
            from apps.auth.services.otp import otp_service
            
            # Send verification code
            success, message = await otp_service.create_verification_code(
                db=db,
                verification_type=VerificationType.SIGNUP,
                recipient=user.mobile_number,
                country_code=user.country_code,
                user_id=user.id
            )
            
            return {
                "success": True,
                "user_id": user.id,
                "message": "User registered successfully. Please verify your mobile number.",
                "require_verification": True,
                "verification_sent": success
            }
        except Exception as e:
            # Rollback on error
            await db.rollback()
            return {"success": False, "message": f"Registration failed: {str(e)}"}

# Register the provider
AuthProviderFactory.register_provider("mobile", MobileAuthProvider) 