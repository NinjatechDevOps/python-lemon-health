import random
import string
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from apps.core.config import settings
from apps.accounts.models import VerificationCode, VerificationType, User


class TwilioService:
    """Service for handling SMS verification with Twilio"""
    
    def __init__(self):
        """Initialize Twilio client"""
        # Debug: Print Twilio credentials
        print(f"DEBUG - TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID}")
        print(f"DEBUG - TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER}")
        
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.phone_number = settings.TWILIO_PHONE_NUMBER
    
    def _generate_verification_code(self, length: int = 6) -> str:
        """Generate a random verification code"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS message using Twilio"""
        try:
            # Debug: Print SMS parameters
            print(f"DEBUG - Sending SMS to: {to_phone}")
            print(f"DEBUG - From phone: {self.phone_number}")
            print(f"DEBUG - Message: {message}")
            
            self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_phone
            )
            return True
        except TwilioRestException as e:
            print(f"Twilio error: {e}")
            return False
    
    async def create_verification_code(
        self, 
        db: AsyncSession, 
        verification_type: VerificationType,
        mobile_number: str,
        country_code: str,
        user_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Create and send a verification code
        
        Args:
            db: Database session
            verification_type: Type of verification
            mobile_number: User's mobile number
            country_code: User's country code
            user_id: User ID (optional, for existing users)
            
        Returns:
            Tuple of (success, message)
        """
        # Invalidate previous verification codes for this user/mobile and type
        if user_id:
            # For existing users, invalidate by user_id
            query = select(VerificationCode).where(
                VerificationCode.user_id == user_id,
                VerificationCode.verification_type == verification_type,
                VerificationCode.is_used == False
            )
        else:
            # For new users, invalidate by mobile number
            query = select(VerificationCode).where(
                VerificationCode.mobile_number == mobile_number,
                VerificationCode.country_code == country_code,
                VerificationCode.verification_type == verification_type,
                VerificationCode.is_used == False
            )
            
        result = await db.execute(query)
        old_codes = result.scalars().all()
        
        # Mark all previous codes as used
        for old_code in old_codes:
            old_code.is_used = True
        
        # Generate a new code
        code = self._generate_verification_code()
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)
        
        # Create verification code record
        verification_code = VerificationCode(
            user_id=user_id,
            code=code,
            verification_type=verification_type,
            expires_at=expires_at,
            mobile_number=None if user_id else mobile_number,
            country_code=None if user_id else country_code
        )
        
        db.add(verification_code)
        await db.commit()
        await db.refresh(verification_code)
        
        # Send SMS
        full_phone = f"{country_code}{mobile_number}"
        message = f"Your Lemon Health verification code is: {code}. Valid for 5 minutes."
        
        if self.send_sms(full_phone, message):
            return True, "Verification code sent successfully"
        else:
            return False, "Failed to send verification code"
    
    async def verify_code(
        self, 
        db: AsyncSession, 
        verification_type: VerificationType,
        mobile_number: str,
        country_code: str,
        code: str,
        user_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Verify a code sent to the user
        
        Args:
            db: Database session
            verification_type: Type of verification
            mobile_number: User's mobile number
            country_code: User's country code
            code: The verification code to verify
            user_id: User ID (optional, for existing users)
            
        Returns:
            Tuple of (success, message)
        """
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
                VerificationCode.mobile_number == mobile_number,
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


# Create an instance of the service
twilio_service = TwilioService()
