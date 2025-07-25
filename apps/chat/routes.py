from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from apps.core.db import get_db
from apps.auth.deps import get_current_verified_user
from apps.auth.models import User
from apps.chat.models import Prompt, Conversation, ChatMessage, ChatRole
from apps.chat.schemas import (
    PromptListResponse, BaseResponse, ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessageResponse
)
from apps.chat.llm_connector import process_query_with_prompt
import asyncio
import uuid

router = APIRouter()

@router.get("/prompts", response_model=BaseResponse[PromptListResponse])
async def get_prompts(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    prompts = await db.execute(Prompt.__table__.select())
    prompt_objs = prompts.fetchall()
    prompt_list = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "prompt_type": p.prompt_type
        }
        for p in prompt_objs
    ]
    return {
        "success": True,
        "message": "Prompts retrieved successfully",
        "data": PromptListResponse(prompts=prompt_list)
    }

@router.post("/", response_model=BaseResponse[ChatResponse])
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    # Try to get existing conversation (eagerly load prompt)
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.prompt))
        .where(Conversation.chat_id == chat_request.chat_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        # Find prompt
        prompt_result = await db.execute(select(Prompt).where(Prompt.prompt_type == chat_request.prompt_id))
        prompt = prompt_result.scalar_one_or_none()
        if not prompt:
            raise HTTPException(status_code=400, detail=f"Prompt '{chat_request.prompt_id}' not found.")
        # Set title to first 60 chars of user_query
        title = chat_request.user_query[:60]
        conversation = Conversation(
            chat_id=chat_request.chat_id,
            user_id=current_user.id,
            prompt_id=prompt.id,
            title=title
        )
        # Assign prompt directly for later use
        conversation.prompt = prompt
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    else:
        prompt = conversation.prompt
    # Store user message
    user_msg = ChatMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role=ChatRole.USER,
        content=chat_request.user_query
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)
    # Get system prompt
    system_prompt = prompt.system_prompt
    # Get conversation history
    result = await db.execute(select(ChatMessage).where(ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.created_at))
    history = result.scalars().all()
    history_msgs = [
        {"role": m.role.value, "content": m.content}
        for m in history
    ]
    # Streamed or non-streamed response
    if chat_request.streamed:
        async def llm_stream():
            response = await process_query_with_prompt(
                user_message=chat_request.user_query,
                system_prompt=system_prompt,
                conversation_history=history_msgs,
                user=current_user
            )
            assistant_msg = ChatMessage(
                conversation_id=conversation.id,
                user_id=None,
                role=ChatRole.ASSISTANT,
                content=response
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            for chunk in response.split('.'):
                if chunk.strip():
                    yield chunk.strip() + '.'
                    await asyncio.sleep(0.1)
        return StreamingResponse(llm_stream(), media_type="text/plain")
    else:
        response = await process_query_with_prompt(
            user_message=chat_request.user_query,
            system_prompt=system_prompt,
            conversation_history=history_msgs,
            user=current_user
        )
        assistant_msg = ChatMessage(
            conversation_id=conversation.id,
            user_id=None,
            role=ChatRole.ASSISTANT,
            content=response
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)
        return {
            "success": True,
            "message": "Query processed successfully",
            "data": ChatResponse(
                chat_id=chat_request.chat_id,
                user_query=chat_request.user_query,
                response=response,
                streamed=False
            )
        }

@router.get("/history/{chat_id}", response_model=BaseResponse[ChatHistoryResponse])
async def get_chat_history(chat_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_verified_user)):
    # Validate chat_id as UUID
    try:
        uuid.UUID(str(chat_id))
    except Exception:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Invalid chat_id format. Must be a valid UUID.",
                "data": None
            }
        )
    try:
        result = await db.execute(select(Conversation).where(Conversation.chat_id == chat_id, Conversation.user_id == current_user.id))
        conversation = result.scalar_one_or_none()
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "Conversation not found.",
                    "data": None
                }
            )
        result = await db.execute(select(ChatMessage).where(ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.created_at))
        messages = result.scalars().all()
        msg_list = [
            ChatMessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=str(m.created_at)
            ) for m in messages
        ]
        return {
            "success": True,
            "message": "Chat history fetched successfully",
            "data": ChatHistoryResponse(chat_id=chat_id, messages=msg_list, title=conversation.title)
        }
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An error occurred while fetching chat history.",
                "data": None
            }
        )
