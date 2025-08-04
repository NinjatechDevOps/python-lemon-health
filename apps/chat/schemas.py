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

class DocumentType(str, Enum):
    PDF = "pdf"

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

# Document Upload Schemas
class DocumentUploadResponse(BaseModel):
    doc_id: str
    original_filename: str
    llm_generated_filename: Optional[str] = None
    file_size: int
    file_type: DocumentType
    uploaded_at: str
    analysis_status: str

class DocumentAnalysisResponse(BaseModel):
    analysis_id: str
    extracted_content: Optional[str] = None
    generated_tags: Optional[List[str]] = None
    analysis_status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

class DocumentResponse(BaseModel):
    doc_id: str
    original_filename: str
    llm_generated_filename: Optional[str] = None
    file_size: int
    file_type: DocumentType
    uploaded_at: str 
    analysis: Optional[DocumentAnalysisResponse] = None

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    pagination: PaginationInfo

class DocumentAnalysisRequest(BaseModel):
    doc_id: str 