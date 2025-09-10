from datetime import datetime
from enum import Enum
from typing import Optional, List, ForwardRef

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.base import Base

# Forward reference to Profile model
ProfileRef = ForwardRef("Profile")


class User(Base):
    """
    User model for storing user authentication information
    """
    __tablename__ = "users"
    # __table_args__ = (
    #     UniqueConstraint('country_code', 'mobile_number', name='uq_country_mobile'),
    # )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False, default="+91")  # Default to India
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Soft delete flag - when True, user is considered deleted
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional email field (not used for primary authentication)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    
    # Relationships
    profile: Mapped[ProfileRef] = relationship("Profile", back_populates="user", uselist=False)
    verification_codes: Mapped[List["VerificationCode"]] = relationship("VerificationCode", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_phone_number(self) -> str:
        """Get full phone number with country code"""
        return f"{self.country_code}{self.mobile_number}"


class VerificationType(str, Enum):
    """Types of verification"""
    SIGNUP = "signup"
    PASSWORD_RESET = "password_reset"
    LOGIN = "login"


class VerificationCode(Base):
    """
    Model for storing verification codes sent to users
    """
    __tablename__ = "verification_codes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)  # The verification code
    verification_type: Mapped[VerificationType] = mapped_column(nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # For password reset when user doesn't exist yet
    mobile_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="verification_codes")
    
    @property
    def is_expired(self) -> bool:
        """Check if code is expired"""
        return datetime.utcnow() > self.expires_at
