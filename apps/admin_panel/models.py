from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from apps.core.db import Base


class Translation(Base):
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    keyword = Column(String, nullable=False, index=True)
    en = Column(String, nullable=False)
    es = Column(String, nullable=False)
    is_deleted = Column(Boolean, default=False)
    is_deletable = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user who created this translation
    creator = relationship("User", foreign_keys=[created_by])

