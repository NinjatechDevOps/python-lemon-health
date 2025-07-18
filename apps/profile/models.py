from datetime import datetime
from typing import Optional, ForwardRef

from sqlalchemy import ForeignKey, Integer, String, Float, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.base import Base

# Forward reference to User model
UserRef = ForwardRef("User")


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
    weight_unit: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="kg")  # "kg" or "lbs"
    gender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    profile_picture_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # URL to profile picture
    
    # Relationships
    user: Mapped[UserRef] = relationship("User", back_populates="profile") 