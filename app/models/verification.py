from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class VerificationType(str, Enum):
    """Types of verification"""
    SIGNUP = "signup"
    PASSWORD_RESET = "password_reset"
    LOGIN = "login"


class VerificationCode(Base):
    """
    Model for storing verification codes sent to users
    """
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), nullable=False)  # The verification code
    verification_type = Column(SQLEnum(VerificationType), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # For password reset when user doesn't exist yet
    mobile_number = Column(String(20), nullable=True)
    country_code = Column(String(10), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="verification_codes")
    
    @property
    def is_expired(self) -> bool:
        """Check if code is expired"""
        return datetime.utcnow() > self.expires_at 