from datetime import datetime
from typing import Optional, Generic, TypeVar, List, Dict, Any, Union

from pydantic import BaseModel, Field

from apps.chat.models import QueryType


class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message"""
    query: str


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    id: int
    query: str
    response: str
    query_type: QueryType
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatHistoryItem(BaseModel):
    """Schema for chat history item"""
    id: int
    query: str
    query_type: QueryType
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response"""
    messages: List[ChatHistoryItem]


# Base response model for standardized API responses
T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """Base response model with standardized format"""
    success: bool
    message: str
    data: Optional[T] = None


# Specific response models for nutrition and exercise
class NutritionPlanResponse(BaseModel):
    """Schema for nutrition plan response"""
    plan: str
    recommendations: List[str]
    daily_calories: Optional[int] = None
    macros: Optional[Dict[str, Any]] = None


class ExercisePlanResponse(BaseModel):
    """Schema for exercise plan response"""
    plan: str
    recommendations: List[str]
    weekly_schedule: Optional[List[Dict[str, Any]]] = None


class UserQueryResponse(BaseModel):
    """Schema for general user query response"""
    response: str
    requires_profile_completion: bool = False
    required_fields: Optional[List[str]] = None 


class ChatRequest(BaseModel):
    """Schema for chat request"""
    query: str


class ChatResponse(BaseModel):
    """Schema for chat response"""
    response: str 