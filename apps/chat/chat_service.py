import uuid
import math
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from apps.auth.models import User
from apps.chat.models import Prompt, Conversation, ChatMessage, ChatRole, PromptType
from apps.chat.schemas import (
    ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessageResponse,
    ChatHistoryListResponse, ConversationListItem, PaginationInfo
)
from apps.chat.llm_connector import process_query_with_prompt
from apps.chat.profile_completion import ProfileCompletionService
from apps.chat.utils import convert_icon_path_to_complete_url


class ChatService:
    """Service for handling chat operations and conversation management"""
    
    @staticmethod
    async def get_prompts(db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all available prompts from the database"""
        try:
            prompts = await db.execute(Prompt.__table__.select())
            prompt_objs = prompts.fetchall()
            prompt_list = [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "prompt_type": p.prompt_type,
                    "icon_path": convert_icon_path_to_complete_url(p.icon_path)
                }
                for p in prompt_objs
            ]
            return prompt_list
        except Exception as e:
            raise Exception(f"Error retrieving prompts: {str(e)}")
    
    @staticmethod
    async def validate_conversation_id(conv_id: str) -> None:
        """Validate conversation ID format"""
        try:
            uuid.UUID(conv_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid conv_id format. Must be a valid UUID."
            )
    
    @staticmethod
    async def get_or_create_conversation(
        conv_id: str, 
        user_id: int, 
        prompt_id: str, 
        user_query: str,
        db: AsyncSession
    ) -> Tuple[Conversation, Prompt]:
        """Get existing conversation or create new one"""
        # Try to get existing conversation (eagerly load prompt)
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.prompt))
            .where(Conversation.conv_id == conv_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            # Find prompt by prompt_type
            prompt_result = await db.execute(
                select(Prompt).where(Prompt.prompt_type == prompt_id)
            )
            prompt = prompt_result.scalar_one_or_none()
            if not prompt:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Prompt '{prompt_id}' not found. Available prompts: {[p.value for p in PromptType]}"
                )
            
            # Set title to first 60 chars of user_query
            title = user_query[:60] if user_query else "New Chat"
            conversation = Conversation(
                conv_id=conv_id,
                user_id=user_id,
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
        
        return conversation, prompt
    
    @staticmethod
    async def store_user_message(
        conversation_id: int, 
        user_id: int, 
        content: str, 
        db: AsyncSession
    ) -> ChatMessage:
        """Store user message in database"""
        user_msg = ChatMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role=ChatRole.USER,
            content=content
        )
        db.add(user_msg)
        await db.commit()
        await db.refresh(user_msg)
        return user_msg
    
    @staticmethod
    async def get_conversation_history(conversation_id: int, db: AsyncSession) -> List[Dict[str, str]]:
        """Get conversation history as list of message dicts"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
        )
        history = result.scalars().all()
        history_msgs = [
            {"role": m.role.value, "content": m.content}
            for m in history
        ]
        return history_msgs
    
    @staticmethod
    async def store_assistant_message(
        conversation_id: int, 
        content: str, 
        db: AsyncSession
    ) -> ChatMessage:
        """Store assistant message in database"""
        assistant_msg = ChatMessage(
            conversation_id=conversation_id,
            user_id=None,
            role=ChatRole.ASSISTANT,
            content=content
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)
        return assistant_msg
    
    @staticmethod
    async def process_chat_with_profile_completion(
        chat_request: ChatRequest,
        current_user: User,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process chat request with profile completion logic"""
        # Validate conv_id format
        await ChatService.validate_conversation_id(chat_request.conv_id)
        
        # Get or create conversation
        conversation, prompt = await ChatService.get_or_create_conversation(
            conv_id=chat_request.conv_id,
            user_id=current_user.id,
            prompt_id=chat_request.prompt_id,
            user_query=chat_request.user_query,
            db=db
        )
        
        # Store user message
        await ChatService.store_user_message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            content=chat_request.user_query,
            db=db
        )
        
        # Get conversation history
        history_msgs = await ChatService.get_conversation_history(conversation.id, db)
        
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
            await ChatService.store_assistant_message(
                conversation_id=conversation.id,
                content=profile_response,
                db=db
            )
            
            return {
                "success": True,
                "message": "Profile completion required",
                "data": ChatResponse(
                    conv_id=chat_request.conv_id,
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
        
        # Get the actual LLM response
        response = await process_query_with_prompt(
            user_message=chat_request.user_query,
            system_prompt=system_prompt,
            conversation_history=history_msgs,
            user=current_user,
            temperature=0.7,  # Balanced creativity for general chat
            max_tokens=1000   # Reasonable response length
        )
        
        # Store assistant message
        await ChatService.store_assistant_message(
            conversation_id=conversation.id,
            content=response,
            db=db
        )
        
        # If profile was updated, combine the responses
        final_response = response
        if profile_updated and profile_response:
            final_response = profile_response + "\n\n" + response
        
        return {
            "success": True,
            "message": "Query processed successfully",
            "data": ChatResponse(
                conv_id=chat_request.conv_id,
                user_query=chat_request.user_query,
                response=final_response,
                streamed=False
            )
        }
    
    @staticmethod
    async def process_streaming_chat(
        chat_request: ChatRequest,
        current_user: User,
        db: AsyncSession
    ) -> StreamingResponse:
        """Process streaming chat request"""
        # Validate conv_id format
        await ChatService.validate_conversation_id(chat_request.conv_id)
        
        # Get or create conversation
        conversation, prompt = await ChatService.get_or_create_conversation(
            conv_id=chat_request.conv_id,
            user_id=current_user.id,
            prompt_id=chat_request.prompt_id,
            user_query=chat_request.user_query,
            db=db
        )
        
        # Store user message
        await ChatService.store_user_message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            content=chat_request.user_query,
            db=db
        )
        
        # Get conversation history
        history_msgs = await ChatService.get_conversation_history(conversation.id, db)
        
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
            await ChatService.store_assistant_message(
                conversation_id=conversation.id,
                content=profile_response,
                db=db
            )
            
            async def profile_stream():
                yield profile_response
                
            return StreamingResponse(profile_stream(), media_type="text/plain")
        
        # Profile is complete or user provided profile info - proceed with LLM
        # Get system prompt and add profile context if available
        system_prompt = prompt.system_prompt
        
        # Add user profile context to the system prompt
        profile_context = await ProfileCompletionService.get_user_profile_context(db, current_user.id)
        if profile_context:
            system_prompt = f"{system_prompt}\n\nUser Profile Context: {profile_context}"
        
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
                    user=current_user,
                    temperature=0.7,  # Balanced creativity for general chat
                    max_tokens=1000   # Reasonable response length
                )
                
                # Store assistant message
                await ChatService.store_assistant_message(
                    conversation_id=conversation.id,
                    content=response,
                    db=db
                )
                
                # Simulate streaming (split by sentences)
                for chunk in response.split('.'):
                    if chunk.strip():
                        yield chunk.strip() + '.'
                        await asyncio.sleep(0.1)
            except Exception as e:
                yield f"Error: {str(e)}"
                
        return StreamingResponse(llm_stream(), media_type="text/plain")
    
    @staticmethod
    async def get_chat_history_by_conv_id(
        conv_id: str, 
        current_user: User, 
        db: AsyncSession
    ) -> ChatHistoryResponse:
        """Get chat history for a specific conversation ID"""
        # Validate conv_id as UUID
        try:
            uuid.UUID(str(conv_id))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid conv_id format. Must be a valid UUID."
            )
        
        # Get conversation
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.prompt))  # Eagerly load prompt relationship
            .where(Conversation.conv_id == conv_id, Conversation.user_id == current_user.id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"No conversation found for conv_id: {conv_id}"
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
                mid=m.mid,
                role=m.role,
                content=m.content,
                created_at=str(m.created_at)
            ) for m in messages
        ]
        
        return ChatHistoryResponse(
            conv_id=conv_id, 
            prompt_type=conversation.prompt.prompt_type,  # Added prompt type
            title=conversation.title,
            messages=msg_list,
        )
    
    @staticmethod
    async def get_user_chat_history_list(
        current_user: User,
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        prompt_type: Optional[PromptType] = None
    ) -> ChatHistoryListResponse:
        """Get paginated list of user's chat history"""
        # Build base query for conversations
        base_query = (
            select(Conversation)
            .options(selectinload(Conversation.prompt))
            .where(Conversation.user_id == current_user.id)
        )
        
        # Add search filter if provided
        if search:
            search_filter = Conversation.title.ilike(f"%{search}%")
            base_query = base_query.where(search_filter)
        
        # Add prompt type filter if provided
        if prompt_type:
            base_query = base_query.join(Prompt).where(Prompt.prompt_type == prompt_type)
        
        # Get total count for pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Calculate pagination info
        total_pages = math.ceil(total / per_page) if total > 0 else 0
        offset = (page - 1) * per_page
        
        # Get conversations with pagination
        conversations_query = (
            base_query
            .order_by(desc(Conversation.updated_at))
            .offset(offset)
            .limit(per_page)
        )
        
        conversations_result = await db.execute(conversations_query)
        conversations = conversations_result.scalars().all()
        
        # Build response data with conversation-level info only
        conversation_items = []
        for conv in conversations:
            # Get message count for this conversation
            msg_count_query = select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conv.id)
            msg_count_result = await db.execute(msg_count_query)
            message_count = msg_count_result.scalar()
            
            # Get last message preview (first 100 chars)
            last_msg_query = (
                select(ChatMessage.content)
                .where(ChatMessage.conversation_id == conv.id)
                .order_by(desc(ChatMessage.created_at))
                .limit(1)
            )
            last_msg_result = await db.execute(last_msg_query)
            last_message = last_msg_result.scalar()
            last_message_preview = None
            if last_message:
                last_message_preview = last_message[:100] + "..." if len(last_message) > 100 else last_message
            
            conversation_items.append(
                ConversationListItem(
                    conv_id=conv.conv_id,
                    title=conv.title,
                    prompt_type=conv.prompt.prompt_type,
                    message_count=message_count,
                    last_message_preview=last_message_preview,
                    created_at=str(conv.created_at),
                    updated_at=str(conv.updated_at)
                )
            )
        
        # Build pagination info
        pagination = PaginationInfo(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        return ChatHistoryListResponse(
            conversations=conversation_items,
            pagination=pagination
        ) 