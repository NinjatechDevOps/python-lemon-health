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
    chat_id: str
    prompt_id: int
    created_at: str
    updated_at: str

class ChatMessageResponse(BaseModel):
    id: int
    role: ChatRole
    content: str
    created_at: str

class ChatHistoryResponse(BaseModel):
    chat_id: str
    messages: List[ChatMessageResponse]
    title: str | None = None

class ChatRequest(BaseModel):
    chat_id: str
    prompt_id: str
    user_query: str
    streamed: Optional[bool] = False

class ChatResponse(BaseModel):
    chat_id: str
    user_query: str
    response: str
    streamed: Optional[bool] = False 