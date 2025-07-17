from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import random
import string
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from apps.accounts.models import VerificationCode, VerificationType
from apps.core.config import settings

class OTPProvider(ABC):
    """Base class for OTP delivery providers"""
    
    @abstractmethod
    async def send_otp(self, recipient: str, message: str) -> Tuple[bool, str]:
        """Send OTP to the recipient"""
        pass

class OTPService:
    """Service for handling OTP verification"""
    
    def __init__(self, provider: OTPProvider):
        """Initialize OTP service with a provider"""
        self.provider = provider
    
    def _generate_code(self, length: int = 6) -> str:
        """Generate a random verification code"""
        return ''.join(random.choices(string.digits, k=length))
    
    async def create_verification_code(
        self, 
        db: AsyncSession, 
        verification_type: VerificationType,
        recipient: str,
        country_code: str = None,
        user_id: int = None
    ) -> Tuple[bool, str]:
        """
        Create and send a verification code
        
        Args:
            db: Database session
            verification_type: Type of verification
            recipient: Recipient (mobile number or email)
            country_code: Country code (for mobile)
            user_id: User ID (optional)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Generate a code
            code = self._generate_code()
            
            # Calculate expiry time
            expires_at = datetime.utcnow() + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)
            
            # Invalidate previous codes
            if user_id:
                query = update(VerificationCode).where(
                    VerificationCode.user_id == user_id,
                    VerificationCode.verification_type == verification_type,
                    VerificationCode.is_used == False,
                    VerificationCode.expires_at > datetime.utcnow()
                ).values(is_used=True)
                await db.execute(query)
            else:
                query = update(VerificationCode).where(
                    VerificationCode.mobile_number == recipient,
                    VerificationCode.country_code == country_code,
                    VerificationCode.verification_type == verification_type,
                    VerificationCode.is_used == False,
                    VerificationCode.expires_at > datetime.utcnow()
                ).values(is_used=True)
                await db.execute(query)
            
            # Create verification code record
            verification_code = VerificationCode(
                user_id=user_id,
                code=code,
                verification_type=verification_type,
                expires_at=expires_at,
                mobile_number=None if user_id else recipient,
                country_code=None if user_id else country_code
            )
            
            db.add(verification_code)
            await db.commit()
            await db.refresh(verification_code)
            
            # Prepare message
            message = f"Your Lemon Health verification code is: {code}. Valid for 5 minutes."
            
            # Send OTP
            full_recipient = f"{country_code}{recipient}" if country_code else recipient
            success, send_message = await self.provider.send_otp(full_recipient, message)
            
            if success:
                return True, "Verification code sent successfully"
            else:
                return False, f"Failed to send verification code: {send_message}"
        except Exception as e:
            # Rollback on error
            await db.rollback()
            return False, f"Error creating verification code: {str(e)}"
    
    async def verify_code(
        self, 
        db: AsyncSession, 
        verification_type: VerificationType,
        recipient: str,
        code: str,
        country_code: str = None,
        user_id: int = None
    ) -> Tuple[bool, str]:
        """
        Verify a code sent to the user
        
        Args:
            db: Database session
            verification_type: Type of verification
            recipient: Recipient (mobile number or email)
            code: The verification code to verify
            country_code: Country code (for mobile)
            user_id: User ID (optional)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Query for verification code
            query = select(VerificationCode).where(
                VerificationCode.verification_type == verification_type,
                VerificationCode.code == code,
                VerificationCode.is_used == False,
                VerificationCode.expires_at > datetime.utcnow()
            )
            
            if user_id:
                # For existing users
                query = query.where(VerificationCode.user_id == user_id)
            else:
                # For new users or password reset
                query = query.where(
                    VerificationCode.mobile_number == recipient,
                    VerificationCode.country_code == country_code
                )
            
            result = await db.execute(query)
            verification_code = result.scalars().first()
            
            if not verification_code:
                return False, "Invalid or expired verification code"
            
            # Mark code as used
            verification_code.is_used = True
            await db.commit()
            
            return True, "Verification successful"
        except Exception as e:
            # Rollback on error
            await db.rollback()
            return False, f"Error verifying code: {str(e)}"

# Import here to avoid circular imports
from apps.auth.providers.twilio import twilio_provider

# Create an instance of the OTP service with the Twilio provider
otp_service = OTPService(twilio_provider) 