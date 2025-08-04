from apps.auth.models import User
from apps.profile.models import Profile
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from apps.core.base import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

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
    icon_path: Mapped[str] = mapped_column(String(255), nullable=True)  # Path to icon image
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conv_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True)  # Renamed from chat_id, no default
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
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
    mid: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True, default=lambda: str(uuid.uuid4()))  # Message ID
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    role: Mapped[ChatRole] = mapped_column(PgEnum(ChatRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User")

# Document Upload Models
class DocumentType(str, Enum):
    PDF = "pdf"

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    doc_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    llm_generated_filename: Mapped[str] = mapped_column(String(255), nullable=True)  # LLM-generated descriptive filename
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)  # Unique filename on server
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Full path to file
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Size in bytes
    file_type: Mapped[DocumentType] = mapped_column(PgEnum(DocumentType), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationships
    user = relationship("User", backref="documents")
    analysis = relationship("DocumentAnalysis", back_populates="document", uselist=False, cascade="all, delete-orphan")

class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    extracted_content: Mapped[str] = mapped_column(Text, nullable=True)  # Raw extracted text
    generated_tags: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of tags
    analysis_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, failed
    error_message: Mapped[str] = mapped_column(Text, nullable=True)  # Error message if analysis failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Relationships
    document = relationship("Document", back_populates="analysis")
