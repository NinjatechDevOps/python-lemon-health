import os
from typing import List, Union

from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Lemon Health"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # SECURITY
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30000
    REFRESH_TOKEN_EXPIRE_DAYS: int = 90
    
    # DATABASE
    DATABASE_URL: str
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:8000"]
    
    # TWILIO
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str  
    
    # Setting these as optional with default values
    TWILIO_VERIFY_SERVICE_SID: str
    
    # VERIFICATION
    VERIFICATION_CODE_EXPIRY_SECONDS: int = 300  # 5 minutes
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )

settings = Settings()
