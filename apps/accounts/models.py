from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.base import Base

# Import the table directly instead of the module to avoid circular imports
from apps.auth.models.rbac import user_role


class VerificationType(Enum):
    SIGNUP = "signup"
    PASSWORD_RESET = "password_reset"


class User(Base):
    """
    User model for storing user authentication information
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False, default="+91")  # Default to India
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional email field (not used for primary authentication)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    
    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="user", uselist=False)
    verification_codes: Mapped[List["VerificationCode"]] = relationship("VerificationCode", back_populates="user", cascade="all, delete-orphan")
    # Use string reference to avoid circular imports
    roles: Mapped[List["apps.auth.models.rbac.Role"]] = relationship("apps.auth.models.rbac.Role", secondary=user_role, back_populates="users")

    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_phone_number(self) -> str:
        """Get full phone number with country code"""
        return f"{self.country_code}{self.mobile_number}"


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


class Profile(Base):
    """
    Profile model for storing additional user information
    """
    __tablename__ = "profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in cm
    height_unit: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "cm" or "ft/in"
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in kg
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")
