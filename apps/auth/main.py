from fastapi import FastAPI
from typing import Dict, Any, Optional
from pydantic import BaseModel

from apps.core.config import settings as app_settings
# Import providers to ensure they are registered
import apps.auth.providers

class AuthConfig(BaseModel):
    # Default configuration
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 90
    DATABASE_URL: str
    # SMS configuration
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    # Auth providers
    ENABLE_MOBILE_AUTH: bool = True
    ENABLE_EMAIL_AUTH: bool = False
    ENABLE_GOOGLE_AUTH: bool = False
    # Admin features
    ENABLE_ADMIN_API: bool = False
    
    class Config:
        env_file = ".env"

class AuthModule:
    def __init__(self, app: FastAPI, config: Optional[Dict[str, Any]] = None):
        """Initialize the Auth Module with the given app and configuration"""
        self.app = app
        
        # Load configuration
        if config:
            self.config = AuthConfig(**config)
        else:
            # Use app settings as fallback
            self.config = AuthConfig(
                SECRET_KEY=app_settings.SECRET_KEY,
                DATABASE_URL=app_settings.DATABASE_URL,
                ACCESS_TOKEN_EXPIRE_MINUTES=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES,
                REFRESH_TOKEN_EXPIRE_DAYS=app_settings.REFRESH_TOKEN_EXPIRE_DAYS,
                TWILIO_ACCOUNT_SID=app_settings.TWILIO_ACCOUNT_SID,
                TWILIO_AUTH_TOKEN=app_settings.TWILIO_AUTH_TOKEN,
                TWILIO_PHONE_NUMBER=app_settings.TWILIO_PHONE_NUMBER
            )
        
        # Register routes
        self._register_routes()
        
        # Initialize database if needed
        self._init_database()
        
    def _register_routes(self):
        """Register all auth routes with the app"""
        from apps.accounts.routes import router as auth_router
        
        # Register the auth router
        self.app.include_router(
            auth_router,
            prefix="/api/auth",
            tags=["auth"]
        )
        
        # Register admin routes if enabled
        if self.config.ENABLE_ADMIN_API:
            try:
                from apps.auth.admin.routes import router as admin_router
                self.app.include_router(
                    admin_router,
                    prefix="/api/admin",
                    tags=["admin"]
                )
            except ImportError:
                # Admin routes not available, log a warning
                import logging
                logging.warning("Admin API enabled but admin routes not found. Skipping.")
        
    def _init_database(self):
        """Initialize database tables and default roles if needed"""
        # This would be implemented to create initial roles, admin user, etc.
        pass 