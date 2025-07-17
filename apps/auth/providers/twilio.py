from typing import Tuple
import asyncio
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from apps.auth.services.otp import OTPProvider
from apps.core.config import settings

class TwilioOTPProvider(OTPProvider):
    """Twilio provider for OTP delivery"""
    
    def __init__(self):
        """Initialize Twilio client"""
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.phone_number = settings.TWILIO_PHONE_NUMBER
    
    async def send_otp(self, recipient: str, message: str) -> Tuple[bool, str]:
        """Send OTP via Twilio SMS"""
        try:
            # Run Twilio API call in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    body=message,
                    from_=self.phone_number,
                    to=recipient
                )
            )
            return True, "SMS sent successfully"
        except TwilioRestException as e:
            return False, f"Twilio error: {str(e)}"
        except Exception as e:
            return False, f"Error sending SMS: {str(e)}"

# Create an instance of the provider
twilio_provider = TwilioOTPProvider() 