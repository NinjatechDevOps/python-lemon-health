from typing import Dict, Any
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.deps import get_current_verified_user
from apps.auth.models import User
from apps.core.db import get_db
from apps.chat.llm_connector import process_query
from apps.chat.schemas import ChatRequest, ChatResponse, BaseResponse

router = APIRouter()


@router.post("/", response_model=BaseResponse[ChatResponse])
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Process a user query and return a response from the LLM
    """
    # Pass the query to the LLM service
    response = await process_query(chat_request.query, current_user)
    
    # Return the response
    return {
        "success": True,
        "message": "Query processed successfully",
        "data": ChatResponse(response=response)
    }


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the chat service
    """
    return {
        "success": True,
        "message": "Chat service is healthy",
        "data": {
            "status": "ok",
            "version": "1.0.0"
        }
    }
