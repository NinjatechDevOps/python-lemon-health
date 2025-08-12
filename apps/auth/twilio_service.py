# import random
# import string
# from datetime import datetime, timedelta
# from typing import Optional, Tuple

# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from twilio.rest import Client
# from twilio.base.exceptions import TwilioRestException

# from apps.core.config import settings
# from apps.auth.models import VerificationCode, VerificationType


# class TwilioService:
#     """Service for handling SMS verification with Twilio"""
    
#     def __init__(self):
#         """Initialize Twilio client"""
#         # Debug: Print Twilio credentials
#         logger.debug(f"DEBUG - TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID}")
#         logger.debug(f"DEBUG - TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER}")
        
#         self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
#         self.phone_number = settings.TWILIO_PHONE_NUMBER
    
#     def _generate_verification_code(self, length: int = 6) -> str:
#         """Generate a random verification code"""
#         return ''.join(random.choices(string.digits, k=length))
    
#     def send_sms(self, to_phone: str, message: str) -> tuple[bool, str]:
#         """
#         Send SMS message using Twilio
        
#         Args:
#             to_phone: Recipient's phone number
#             message: Message content
            
#         Returns:
#             Tuple of (success, message)
#         """
#         try:
#             # Debug: Print SMS parameters
#             logger.debug(f"DEBUG - Sending SMS to: {to_phone}")
#             logger.debug(f"DEBUG - From phone: {self.phone_number}")
#             logger.debug(f"DEBUG - Message: {message}")
            
#             self.client.messages.create(
#                 body=message,
#                 from_=self.phone_number,
#                 to=to_phone
#             )
#             return True, "SMS sent successfully"
#         except TwilioRestException as e:
#             error_code = getattr(e, 'code', None)
#             error_msg = str(e)
            
#             # Handle specific Twilio error codes
#             if error_code == 20003:
#                 logger.error(f"Twilio authentication error: {error_msg}")
#                 return False, "Verification code created but SMS delivery failed. You can request a new code."
#             elif error_code == 21211:
#                 logger.error(f"Invalid phone number: {error_msg}")
#                 return False, "Invalid phone number format. Please check your number and try again."
#             elif error_code == 21608:
#                 logger.error(f"Unverified phone number: {error_msg}")
#                 return False, "This phone number is not verified with our SMS service. Please contact support."
#             elif error_code == 21610:
#                 logger.error(f"Message body too long: {error_msg}")
#                 return False, "Verification code created but SMS delivery failed. You can request a new code."
#             else:
#                 logger.error(f"Twilio error {error_code}: {error_msg}")
#                 return False, "Verification code created but SMS delivery failed. You can request a new code."
#         except Exception as e:
#             logger.error(f"Unexpected error sending SMS: {str(e)}")
#             return False, "Verification code created but SMS delivery failed. You can request a new code."
    
#     async def create_verification_code(
#         self, 
#         db: AsyncSession, 
#         verification_type: VerificationType,
#         mobile_number: str,
#         country_code: str,
#         user_id: Optional[int] = None
#     ) -> Tuple[bool, str]:
#         """
#         Create and send a verification code
        
#         Args:
#             db: Database session
#             verification_type: Type of verification
#             mobile_number: User's mobile number
#             country_code: User's country code
#             user_id: User ID (optional, for existing users)
            
#         Returns:
#             Tuple of (success, message)
#         """
#         # Invalidate previous verification codes for this user/mobile and type
#         if user_id:
#             # For existing users, invalidate by user_id
#             query = select(VerificationCode).where(
#                 VerificationCode.user_id == user_id,
#                 VerificationCode.verification_type == verification_type,
#                 VerificationCode.is_used == False
#             )
#         else:
#             # For new users, invalidate by mobile number
#             query = select(VerificationCode).where(
#                 VerificationCode.mobile_number == mobile_number,
#                 VerificationCode.country_code == country_code,
#                 VerificationCode.verification_type == verification_type,
#                 VerificationCode.is_used == False
#             )
            
#         result = await db.execute(query)
#         old_codes = result.scalars().all()
        
#         # Mark all previous codes as used
#         for old_code in old_codes:
#             old_code.is_used = True
        
#         # Generate a new code
#         code = self._generate_verification_code()
        
#         # Calculate expiry time
#         expires_at = datetime.utcnow() + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)
        
#         # Create verification code record
#         verification_code = VerificationCode(
#             user_id=user_id,
#             code=code,
#             verification_type=verification_type,
#             expires_at=expires_at,
#             # Always store mobile_number and country_code regardless of whether user_id is provided
#             # This ensures we can verify by either method
#             mobile_number=mobile_number,
#             country_code=country_code
#         )
        
#         # Debug: Print verification code details
#         logger.debug(f"DEBUG - Creating verification code: type={verification_type}, code={code}, user_id={user_id}, mobile={mobile_number}")
        
#         db.add(verification_code)
#         await db.commit()
#         await db.refresh(verification_code)
        
#         # Send SMS
#         full_phone = f"{country_code}{mobile_number}"
#         message = f"Your Lemon Health verification code is: {code}. Valid for 5 minutes."
        
#         success, error_message = self.send_sms(full_phone, message)
#         if success:
#             return True, "Verification code sent successfully"
#         else:
#             # Even if SMS fails, we've created the code in the database
#             # This allows for alternative delivery or manual verification in development
#             return False, error_message
    
#     async def verify_code(
#         self, 
#         db: AsyncSession, 
#         verification_type: VerificationType,
#         mobile_number: str,
#         country_code: str,
#         code: str,
#         user_id: Optional[int] = None
#     ) -> Tuple[bool, str]:
#         """
#         Verify a code sent to the user
        
#         Args:
#             db: Database session
#             verification_type: Type of verification
#             mobile_number: User's mobile number
#             country_code: User's country code
#             code: The verification code to verify
#             user_id: User ID (optional, for existing users)
            
#         Returns:
#             Tuple of (success, message)
#         """
#         # Query for verification code
#         query = select(VerificationCode).where(
#             VerificationCode.verification_type == verification_type,
#             VerificationCode.code == code,
#             VerificationCode.is_used == False,
#             VerificationCode.expires_at > datetime.utcnow()
#         )
        
#         if user_id:
#             # For existing users
#             query = query.where(VerificationCode.user_id == user_id)
#         else:
#             # For new users or password reset
#             query = query.where(
#                 VerificationCode.mobile_number == mobile_number,
#                 VerificationCode.country_code == country_code
#             )
        
#         # Debug: Print query parameters
#         logger.debug(f"DEBUG - Verification query params: type={verification_type}, code={code}, user_id={user_id}, mobile={mobile_number}, country={country_code}")
        
#         result = await db.execute(query)
#         verification_code = result.scalars().first()
        
#         if not verification_code:
#             logger.warning(f"DEBUG - No verification code found for: type={verification_type}, code={code}, user_id={user_id}")
#             return False, "Invalid or expired verification code"
        
#         # Debug: Print found verification code details
#         logger.debug(f"DEBUG - Found verification code: id={verification_code.id}, user_id={verification_code.user_id}, mobile={verification_code.mobile_number}")
        
#         # Mark code as used
#         verification_code.is_used = True
#         await db.commit()
        
#         return True, "Verification successful"


# # Create an instance of the service
# twilio_service = TwilioService() 



"""

Wriet complete code of twilio service by bypassing the twilio service and send the sms to the user with static code 

"""



import random
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging
from apps.core.logging_config import get_logger

logger = get_logger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.config import settings
from apps.auth.models import VerificationCode, VerificationType


class TwilioService:
    """Mocked Service for handling SMS verification without real Twilio calls"""

    def __init__(self):
        """Mocked Twilio client init"""
        logger.info(f"MOCK - TWILIO_ACCOUNT_SID: {settings.TWILIO_ACCOUNT_SID}")
        logger.info(f"MOCK - TWILIO_PHONE_NUMBER: {settings.TWILIO_PHONE_NUMBER}")
        self.phone_number = settings.TWILIO_PHONE_NUMBER

    def _generate_verification_code(self, length: int = 6) -> str:
        """Return static verification code for testing"""
        return "123456"  # Static code for testing

    def send_sms(self, to_phone: str, message: str) -> tuple[bool, str]:
        """
        Mock sending SMS message by logging instead of real Twilio call
        """
        logger.info(f"MOCK - Pretending to send SMS to: {to_phone}")
        logger.info(f"MOCK - From phone: {self.phone_number}")
        logger.info(f"MOCK - Message: {message}")
        return True, "MOCK SMS sent successfully"

    async def create_verification_code(
        self,
        db: AsyncSession,
        verification_type: VerificationType,
        mobile_number: str,
        country_code: str,
        user_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Create and mock-send a static verification code
        """
        if user_id:
            query = select(VerificationCode).where(
                VerificationCode.user_id == user_id,
                VerificationCode.verification_type == verification_type,
                VerificationCode.is_used == False
            )
        else:
            query = select(VerificationCode).where(
                VerificationCode.mobile_number == mobile_number,
                VerificationCode.country_code == country_code,
                VerificationCode.verification_type == verification_type,
                VerificationCode.is_used == False
            )

        result = await db.execute(query)
        old_codes = result.scalars().all()

        for old_code in old_codes:
            old_code.is_used = True

        code = self._generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(seconds=settings.VERIFICATION_CODE_EXPIRY_SECONDS)

        verification_code = VerificationCode(
            user_id=user_id,
            code=code,
            verification_type=verification_type,
            expires_at=expires_at,
            mobile_number=mobile_number,
            country_code=country_code
        )

        logger.info(f"MOCK - Creating static verification code: type={verification_type}, code={code}, user_id={user_id}, mobile={mobile_number}")

        db.add(verification_code)
        await db.commit()
        await db.refresh(verification_code)

        full_phone = f"{country_code}{mobile_number}"
        message = f"Your Lemon Health verification code is: {code}. Valid for 5 minutes."

        success, error_message = self.send_sms(full_phone, message)
        if success:
            return True, "Verification code sent successfully"
        else:
            return False, error_message

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
        Verify a static code (123456) from database
        """
        query = select(VerificationCode).where(
            VerificationCode.verification_type == verification_type,
            VerificationCode.code == code,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.utcnow()
        )

        if user_id:
            query = query.where(VerificationCode.user_id == user_id)
        else:
            query = query.where(
                VerificationCode.mobile_number == mobile_number,
                VerificationCode.country_code == country_code
            )

        logger.info(f"MOCK - Verifying static code: type={verification_type}, code={code}, user_id={user_id}, mobile={mobile_number}")

        result = await db.execute(query)
        verification_code = result.scalars().first()

        if not verification_code:
            logger.warning(f"MOCK - No static verification code match found")
            return False, "Invalid or expired verification code"

        logger.info(f"MOCK - Static code matched: id={verification_code.id}, user_id={verification_code.user_id}")

        verification_code.is_used = True
        await db.commit()

        return True, "Verification successful"


# Create a mock instance of the service
twilio_service = TwilioService()
