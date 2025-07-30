from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from apps.core.db import get_db
from apps.auth.deps import get_current_verified_user
from apps.auth.models import User
from apps.chat.models import Prompt, Conversation, ChatMessage, ChatRole, PromptType
from apps.chat.schemas import (
    PromptListResponse, BaseResponse, ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessageResponse
)
from apps.chat.llm_connector import process_query_with_prompt
from apps.chat.profile_completion import ProfileCompletionService
import asyncio
import uuid

router = APIRouter()

@router.get("/prompts", response_model=BaseResponse[PromptListResponse])
async def get_prompts(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get a list of all available prompts from the database.
    This endpoint does not require authentication.
    """
    try:
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
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error retrieving prompts: {str(e)}",
                "data": None
            }
        )

@router.post("/", response_model=BaseResponse[ChatResponse])
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a user query and return a response from the LLM.
    Supports both streaming and non-streaming responses.
    Includes profile completion functionality.
    """
    try:
        # Validate chat_id format
        try:
            uuid.UUID(chat_request.chat_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid chat_id format. Must be a valid UUID."
            )
        
        # Try to get existing conversation (eagerly load prompt)
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.prompt))
            .where(Conversation.chat_id == chat_request.chat_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            # Find prompt by prompt_type
            prompt_result = await db.execute(
                select(Prompt).where(Prompt.prompt_type == chat_request.prompt_id)
            )
            prompt = prompt_result.scalar_one_or_none()
            if not prompt:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Prompt '{chat_request.prompt_id}' not found. Available prompts: {[p.value for p in PromptType]}"
                )
            
            # Set title to first 60 chars of user_query
            title = chat_request.user_query[:60] if chat_request.user_query else "New Chat"
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
        
        # Get conversation history
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at)
        )
        history = result.scalars().all()
        history_msgs = [
            {"role": m.role.value, "content": m.content}
            for m in history
        ]
        
        # Check profile completion and handle flow
        profile_response, should_continue_with_llm, profile_updated = await ProfileCompletionService.process_with_profile_completion(
            db=db,
            user_id=current_user.id,
            user_message=chat_request.user_query,
            conversation_history=history_msgs,
            user=current_user,
            prompt_type=chat_request.prompt_id
        )
        
        # If profile is incomplete and user is not providing profile info, return the profile completion message
        if not should_continue_with_llm:
            # Store the profile completion message
            assistant_msg = ChatMessage(
                conversation_id=conversation.id,
                user_id=None,
                role=ChatRole.ASSISTANT,
                content=profile_response
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            
            return {
                "success": True,
                "message": "Profile completion required",
                "data": ChatResponse(
                    chat_id=chat_request.chat_id,
                    user_query=chat_request.user_query,
                    response=profile_response,
                    streamed=False
                )
            }
        
        # Profile is complete or user provided profile info - proceed with LLM
        # Get system prompt and add profile context if available
        system_prompt = prompt.system_prompt
        
        # Add user profile context to the system prompt
        profile_context = await ProfileCompletionService.get_user_profile_context(db, current_user.id)
        if profile_context:
            system_prompt = f"{system_prompt}\n\nUser Profile Context: {profile_context}"
        
        # Streamed or non-streamed response
        if chat_request.streamed:
            async def llm_stream():
                try:
                    # If profile was updated, include that in the response
                    if profile_updated and profile_response:
                        yield profile_response + "\n\n"
                    
                    # Get the actual LLM response
                    response = await process_query_with_prompt(
                        user_message=chat_request.user_query,
                        system_prompt=system_prompt,
                        conversation_history=history_msgs,
                        user=current_user
                    )
                    
                    # Store assistant message
                    assistant_msg = ChatMessage(
                        conversation_id=conversation.id,
                        user_id=None,
                        role=ChatRole.ASSISTANT,
                        content=response
                    )
                    db.add(assistant_msg)
                    await db.commit()
                    await db.refresh(assistant_msg)
                    
                    # Simulate streaming (split by sentences)
                    for chunk in response.split('.'):
                        if chunk.strip():
                            yield chunk.strip() + '.'
                            await asyncio.sleep(0.1)
                except Exception as e:
                    yield f"Error: {str(e)}"
                    
            return StreamingResponse(llm_stream(), media_type="text/plain")
        else:
            # Get the actual LLM response
            response = await process_query_with_prompt(
                user_message=chat_request.user_query,
                system_prompt=system_prompt,
                conversation_history=history_msgs,
                user=current_user
            )
            
            # Store assistant message
            assistant_msg = ChatMessage(
                conversation_id=conversation.id,
                user_id=None,
                role=ChatRole.ASSISTANT,
                content=response
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            
            # If profile was updated, combine the responses
            final_response = response
            if profile_updated and profile_response:
                final_response = profile_response + "\n\n" + response
            
            return {
                "success": True,
                "message": "Query processed successfully",
                "data": ChatResponse(
                    chat_id=chat_request.chat_id,
                    user_query=chat_request.user_query,
                    response=final_response,
                    streamed=False
                )
            }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"An error occurred while processing your request: {str(e)}",
                "data": None
            }
        )

@router.get("/history/{chat_id}", response_model=BaseResponse[ChatHistoryResponse])
async def get_chat_history(
    chat_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_verified_user)
):
    """
    Get chat history for a specific chat_id.
    Only returns history for conversations owned by the current user.
    """
    try:
        # Validate chat_id as UUID
        try:
            uuid.UUID(str(chat_id))
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "Invalid chat_id format. Must be a valid UUID.",
                    "data": None
                }
            )
        
        # Get conversation
        result = await db.execute(
            select(Conversation)
            .where(Conversation.chat_id == chat_id, Conversation.user_id == current_user.id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"No conversation found for chat_id: {chat_id}",
                    "data": None
                }
            )
        
        # Get messages
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at)
        )
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
            "data": ChatHistoryResponse(
                chat_id=chat_id, 
                messages=msg_list, 
                title=conversation.title
            )
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"An error occurred while fetching chat history: {str(e)}",
                "data": None
            }
        )
