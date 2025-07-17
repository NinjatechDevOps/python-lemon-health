import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the config first
from apps.core.config import settings

# Then import the auth module
from apps.auth.main import AuthModule

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Configure specific loggers
if settings.ENVIRONMENT == "production":
    # Reduce verbosity in production
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("twilio.http_client").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)

# Initialize FastAPI app
app = FastAPI(
    title="Lemon Health API",
    description="API for the Lemon Health mobile application",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Auth Module
auth_module = AuthModule(app, {
    # Required configuration
    "SECRET_KEY": settings.SECRET_KEY,
    "DATABASE_URL": settings.DATABASE_URL,
    "ACCESS_TOKEN_EXPIRE_MINUTES": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    "REFRESH_TOKEN_EXPIRE_DAYS": settings.REFRESH_TOKEN_EXPIRE_DAYS,
    # Twilio configuration
    "TWILIO_ACCOUNT_SID": settings.TWILIO_ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": settings.TWILIO_AUTH_TOKEN,
    "TWILIO_PHONE_NUMBER": settings.TWILIO_PHONE_NUMBER,
    # Auth providers
    "ENABLE_MOBILE_AUTH": True
})

@app.get("/", tags=["Health Check"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "Lemon Health API",
        "version": "0.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
