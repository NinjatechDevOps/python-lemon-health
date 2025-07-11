from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """
    User model for storing user authentication information
    """
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    mobile_number = Column(String(20), unique=True, index=True, nullable=False)
    country_code = Column(String(10), nullable=False, default="+91")  # Default to India
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional email field (not used for primary authentication)
    email = Column(String(255), unique=True, index=True, nullable=True)
    
    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)

    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_phone_number(self) -> str:
        """Get full phone number with country code"""
        return f"{self.country_code}{self.mobile_number}"
