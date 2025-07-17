"""
Authentication providers for the auth module.
"""

# Import all providers to register them
from apps.auth.providers.base import AuthProviderFactory
from apps.auth.providers.mobile import MobileAuthProvider

# Make sure all providers are registered
__all__ = ["AuthProviderFactory", "MobileAuthProvider"] 