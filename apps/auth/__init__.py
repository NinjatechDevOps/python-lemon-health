"""
Authentication module for Lemon Health API.
"""

# Import in the correct order to avoid circular imports
from apps.auth.services.token import token_service
from apps.auth.providers.registry import AuthProviderFactory
from apps.auth.providers.mobile import MobileAuthProvider
from apps.auth.services.otp import OTPService, otp_service

# Make sure all components are available
__all__ = [
    "AuthProviderFactory", 
    "MobileAuthProvider",
    "token_service",
    "OTPService",
    "otp_service"
] 