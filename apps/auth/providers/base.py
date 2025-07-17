from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type
from sqlalchemy.ext.asyncio import AsyncSession

class AuthProvider(ABC):
    """Base class for authentication providers"""
    
    @abstractmethod
    async def authenticate(self, db: AsyncSession, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a user with the given credentials"""
        pass
    
    @abstractmethod
    async def register(self, db: AsyncSession, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user"""
        pass

class AuthProviderFactory:
    """Factory for creating authentication providers"""
    _providers: Dict[str, Type[AuthProvider]] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider: Type[AuthProvider]):
        """Register a new authentication provider"""
        cls._providers[name] = provider
    
    @classmethod
    def get_provider(cls, name: str) -> AuthProvider:
        """Get an authentication provider by name"""
        if name not in cls._providers:
            raise ValueError(f"Auth provider '{name}' not found")
        
        return cls._providers[name]()
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get a list of available authentication providers"""
        return list(cls._providers.keys()) 