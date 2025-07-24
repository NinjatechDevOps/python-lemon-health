from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.core.base import Base


class QueryType(str, Enum):
    """Types of user queries"""
    NUTRITION = "nutrition"
    EXERCISE = "exercise"
    GENERAL = "general"
    HEALTH = "health"
    DOCUMENT = "document"


class ChatMessage(Base):
    """
    Model for storing chat messages between user and AI
    """
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)  # User's query
    response: Mapped[str] = mapped_column(Text, nullable=False)  # AI's response
    query_type: Mapped[QueryType] = mapped_column(nullable=False, default=QueryType.GENERAL)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="chat_messages")
    
    @property
    def short_query(self) -> str:
        """Return a shortened version of the query for display"""
        if len(self.query) <= 50:
            return self.query
        return self.query[:47] + "..."
