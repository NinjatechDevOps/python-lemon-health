from apps.auth.models import User
from apps.profile.models import Profile
from datetime import datetime
from enum import Enum
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from apps.core.base import Base
from sqlalchemy.dialects.postgresql import UUID

class PromptType(str, Enum):
    BOOKING = "booking"
    SHOP = "shop"
    NUTRITION = "nutrition"
    EXERCISE = "exercise"
    DOCUMENTS = "documents"
    PRESCRIPTIONS = "prescriptions"

class Prompt(Base):
    __tablename__ = "prompts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    prompt_type: Mapped[PromptType] = mapped_column(PgEnum(PromptType), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=True)  # New title field
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    user = relationship("User", backref="conversations")
    prompt = relationship("Prompt")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    role: Mapped[ChatRole] = mapped_column(PgEnum(ChatRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User")
