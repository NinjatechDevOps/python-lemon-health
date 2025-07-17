from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.providers.base import AuthProvider, AuthProviderFactory

class EmailAuthProvider(AuthProvider):
    """
    Email-based authentication provider
    
    This provider handles authentication and registration using email and password.
    It supports:
    - Registration with email verification
    - Login with email and password
    - Password reset via email
    
    Note: This is a dummy implementation for future development.
    """
    
    async def authenticate(self, db: AsyncSession, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticate a user with email and password
        
        Args:
            db: Database session
            credentials: Dict containing 'email' and 'password'
            
        Returns:
            Dict with authentication result
        """
        # Dummy implementation
        pass
    
    async def register(self, db: AsyncSession, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user with email
        
        Args:
            db: Database session
            user_data: Dict containing user registration data including 'email' and 'password'
            
        Returns:
            Dict with registration result
        """
        # Dummy implementation
        pass
        
    async def send_verification_email(self, db: AsyncSession, email: str, user_id: int) -> Dict[str, Any]:
        """
        Send verification email to newly registered user
        
        Args:
            db: Database session
            email: User's email address
            user_id: User ID
            
        Returns:
            Dict with email sending result
        """
        # Dummy implementation
        pass
        
    async def verify_email(self, db: AsyncSession, token: str) -> Dict[str, Any]:
        """
        Verify email using verification token
        
        Args:
            db: Database session
            token: Verification token from email
            
        Returns:
            Dict with verification result
        """
        # Dummy implementation
        pass

# Register the provider (commented out until implementation is ready)
# AuthProviderFactory.register_provider("email", EmailAuthProvider) 