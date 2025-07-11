"""
API routes package for Lemon Health
"""

from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.chat import router as chat_router

# Export all routers for easy import in main.py
__all__ = ["auth_router", "users_router", "profiles_router", "chat_router"]