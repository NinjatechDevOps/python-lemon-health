import os
from typing import List, Union
from pathlib import Path

from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Lemon Health"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # SECURITY
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 30000
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1576800 ## 3 years
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1100 ## 3 years
    
    # DATABASE
    DATABASE_URL: str
    
    # REDIS (for token blacklisting)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:8000"]
    
    # TWILIO
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str  
    TWILIO_VERIFY_SERVICE_SID: str
    VERIFICATION_CODE_EXPIRY_SECONDS: int = 300  # 5 minutes
    
    #llm privider and API key
    LLM_PROVIDER: str 
    OPENAI_API_KEY: str
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str
    
    # llm model
    OPENAI_MODEL: str
    GROQ_MODEL: str
    GOOGLE_MODEL: str
    
    # MEDIA STORAGE
    MEDIA_ROOT: str = str(Path("media").absolute())
    STATIC_ROOT: str = str(Path("static").absolute())
    MEDIA_URL: str = "/media/"
    STATIC_URL: str = "/static/"
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/jpg"]
    MAX_IMAGE_SIZE: int = 5 * 1024 * 1024  # 5MB
    DEFAULT_PROFILE_IMAGE: str = "/static/images/user.png"
    
    # BASE URL
    BE_BASE_URL: str = "http://localhost:8000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create media directory if it doesn't exist
        os.makedirs(self.MEDIA_ROOT, exist_ok=True)
        os.makedirs(os.path.join(self.MEDIA_ROOT, "profile_pictures"), exist_ok=True)

settings = Settings()
