from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_of_birth = Column(Date)
    height = Column(Float)  # in cm
    height_unit = Column(String)  # "cm" or "ft/in"
    weight = Column(Float)  # in kg
    gender = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="profile")