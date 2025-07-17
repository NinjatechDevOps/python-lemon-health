from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.providers.base import AuthProvider, AuthProviderFactory

class GoogleAuthProvider(AuthProvider):
    """
    Google OAuth2 authentication provider
    
    This provider handles authentication using Google OAuth2.
    It supports:
    - Login with Google account
    - Registration of new users via Google
    - Linking existing accounts with Google
    
    Note: This is a dummy implementation for future development.
    """
    
    async def authenticate(self, db: AsyncSession, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Authenticate a user with Google OAuth2
        
        Args:
            db: Database session
            credentials: Dict containing 'token' from Google OAuth flow
            
        Returns:
            Dict with authentication result
        """
        # Dummy implementation
        pass
    
    async def register(self, db: AsyncSession, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new user with Google OAuth2
        
        Args:
            db: Database session
            user_data: Dict containing user data from Google profile
            
        Returns:
            Dict with registration result
        """
        # Dummy implementation
        pass
        
    async def link_account(self, db: AsyncSession, user_id: int, google_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Link existing account with Google
        
        Args:
            db: Database session
            user_id: Existing user ID
            google_data: Google profile data
            
        Returns:
            Dict with linking result
        """
        # Dummy implementation
        pass
        
    async def get_user_info(self, token: str) -> Dict[str, Any]:
        """
        Get user info from Google API
        
        Args:
            token: Google OAuth token
            
        Returns:
            Dict with user information from Google
        """
        # Dummy implementation
        pass

# Register the provider (commented out until implementation is ready)
# AuthProviderFactory.register_provider("google", GoogleAuthProvider) 