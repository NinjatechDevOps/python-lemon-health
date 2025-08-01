from typing import Optional, Generic, TypeVar, List
from enum import Enum
from pydantic import BaseModel

class PromptType(str, Enum):
    BOOKING = "booking"
    SHOP = "shop"
    NUTRITION = "nutrition"
    EXERCISE = "exercise"
    DOCUMENTS = "documents"
    PRESCRIPTIONS = "prescriptions"

class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class PromptResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    prompt_type: PromptType

class PromptListResponse(BaseModel):
    prompts: List[PromptResponse]

T = TypeVar('T')
class BaseResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

class ConversationResponse(BaseModel):
    conv_id: str  # Changed from chat_id
    prompt_id: int
    created_at: str
    updated_at: str

class ChatMessageResponse(BaseModel):
    id: int
    mid: str      # Message ID (UUID)
    role: ChatRole
    content: str
    created_at: str

class ChatHistoryResponse(BaseModel):
    conv_id: str  # Changed from chat_id
    prompt_type: PromptType  # Added prompt type
    title: str | None = None
    messages: List[ChatMessageResponse]
   

class ChatRequest(BaseModel):
    conv_id: str  # Changed from chat_id
    prompt_id: str
    user_query: str
    streamed: Optional[bool] = False

class ChatResponse(BaseModel):
    conv_id: str  # Changed from chat_id
    user_query: str
    response: str
    streamed: Optional[bool] = False

# Updated schemas for chat history list API - conversation list only
class ConversationListItem(BaseModel):
    conv_id: str  # Changed from chat_id
    title: Optional[str] = None
    prompt_type: PromptType
    message_count: int  # Number of messages in conversation
    last_message_preview: Optional[str] = None  # Preview of last message
    created_at: str
    updated_at: str

class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class ChatHistoryListResponse(BaseModel):
    conversations: List[ConversationListItem]
    pagination: PaginationInfo 