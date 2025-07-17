"""
Registry for authentication providers.
This file explicitly registers all available authentication providers.
"""

from apps.auth.providers.base import AuthProviderFactory
from apps.auth.providers.mobile import MobileAuthProvider

# Register all providers
AuthProviderFactory.register_provider("mobile", MobileAuthProvider)

# Export the factory
__all__ = ["AuthProviderFactory"] 