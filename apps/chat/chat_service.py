import uuid
import math
import asyncio
import logging
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
from apps.chat.prompts import (
    DEFAULT_PROMPT_GUARDRAILS, DEFAULT_PROMPT_SYSTEM, QUERY_CLASSIFICATION_PROMPT, 
    DEFAULT_ALLOWED_PROMPT_TYPES, DEFAULT_PROMPT_TYPE, ENHANCED_QUERY_CLASSIFICATION_PROMPT
)
from apps.core.logging_config import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service for handling chat operations and conversation management"""
    
    # Default prompt types that are allowed (configurable for future expansion)
    DEFAULT_ALLOWED_PROMPT_TYPES = DEFAULT_ALLOWED_PROMPT_TYPES
    
    @staticmethod
    async def classify_query_with_llm(user_query: str, user, category: str = "nutrition and exercise", conversation_history: List[Dict[str, str]] = None) -> bool:
        """
        Use LLM to classify if user query is related to health and wellness areas
        Enhanced to detect profile completion queries
        
        Args:
            user_query: User's query string
            user: User object for LLM context
            category: The category to check relevance for
            conversation_history: Recent conversation history for context
        
        Returns:
            bool: True if query is related to health and wellness areas or is profile completion
        """
        try:
            # Use enhanced prompt from prompts.py
            enhanced_prompt = ENHANCED_QUERY_CLASSIFICATION_PROMPT.format(
                user_query=user_query,
                conversation_context=conversation_history[-2:] if conversation_history else "No recent context"
            )
            response = await process_query_with_prompt(
                user_message=user_query,
                system_prompt=enhanced_prompt,
                conversation_history=conversation_history[-2:] if conversation_history else [],  # Use recent context
                user=user,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=10     # Only need "ALLOWED" or "DENIED"
            )
            # Clean and check response
            response_clean = response.strip().upper()
            logger.debug(f"LLM Classification Response: '{response_clean}' for query: '{user_query}'")
            return response_clean == "ALLOWED"
        except Exception as e:
            logger.error(f"Error in LLM classification: {e}")
            # If LLM classification fails, default to allowing the query to be safe
            logger.warning("LLM classification failed, defaulting to ALLOWED for safety")
            return True

    @staticmethod
    def _fallback_query_classification(user_query: str, category: str = "nutrition and exercise") -> bool:
        """
        DEPRECATED: This method is no longer used. All classification is now done by LLM.
        Kept for backward compatibility but always returns True to be safe.
        
        Args:
            user_query: User's query string
            category: The category to check relevance for
            
        Returns:
            bool: Always returns True to prevent blocking legitimate queries
        """
        logger.debug("Using deprecated fallback classification - defaulting to ALLOWED for safety")
        return True
    
    @staticmethod
    async def get_default_prompts(db: AsyncSession) -> Tuple[Prompt, Prompt]:
        """
        Get nutrition and exercise prompts for default prompt functionality
        
        Args:
            db: Database session
            
        Returns:
            Tuple[Prompt, Prompt]: (nutrition_prompt, exercise_prompt)
        """
        # Use configurable allowed prompt types
        allowed_types = ChatService.DEFAULT_ALLOWED_PROMPT_TYPES
        
        result = await db.execute(
            select(Prompt).where(Prompt.prompt_type.in_(allowed_types))
        )
        prompts = result.scalars().all()
        
        # Create a dictionary to store prompts by type
        prompts_by_type = {}
        for prompt in prompts:
            prompts_by_type[prompt.prompt_type] = prompt
        
        # Check if all required prompts are found
        missing_prompts = []
        for prompt_type in allowed_types:
            if prompt_type not in prompts_by_type:
                missing_prompts.append(prompt_type)
        
        if missing_prompts:
            raise HTTPException(
                status_code=500,
                detail=f"Default prompts not found: {missing_prompts}. Available prompts: {[p.prompt_type for p in prompts]}"
            )
        
        # Return the first two prompts (nutrition and exercise for now)
        prompt_list = list(prompts_by_type.values())
        return prompt_list[0], prompt_list[1]  # nutrition, exercise
    
    @staticmethod
    async def create_default_conversation(
        conv_id: str,
        user_id: int,
        user_query: str,
        db: AsyncSession
    ) -> Tuple[Conversation, str]:
        """
        Create a conversation for default prompt functionality
        
        Args:
            conv_id: Conversation ID
            user_id: User ID
            user_query: User's query
            db: Database session
            
        Returns:
            Tuple[Conversation, str]: (conversation, system_prompt)
        """
        # Try to get default prompt from database first
        default_prompt = await ChatService.get_default_prompt_from_db(db)
        
        if default_prompt:
            # Use database-stored default prompt
            logger.debug(f"Using database-stored default prompt: {default_prompt.name}")
            
            # Create conversation with database default prompt
            title = user_query[:60] if user_query else "Default Chat"
            conversation = Conversation(
                conv_id=conv_id,
                user_id=user_id,
                prompt_id=default_prompt.id,
                title=title
            )
            conversation.prompt = default_prompt
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            
            # Use database system prompt with guardrails
            guardrails = DEFAULT_PROMPT_GUARDRAILS.format(user_query=user_query)
            system_prompt = f"{default_prompt.system_prompt}\n\n{guardrails}"
            
        else:
            # Fallback to hardcoded approach using nutrition prompt
            logger.debug(f"Using hardcoded default prompt approach")
            
            # Get nutrition and exercise prompts for fallback
            nutrition_prompt, exercise_prompt = await ChatService.get_default_prompts(db)
            
            # Use nutrition prompt as the base (since it's more comprehensive)
            base_prompt = nutrition_prompt
            
            # Create conversation with nutrition prompt
            title = user_query[:60] if user_query else "Default Chat"
            conversation = Conversation(
                conv_id=conv_id,
                user_id=user_id,
                prompt_id=base_prompt.id,
                title=title
            )
            conversation.prompt = base_prompt
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            
            # Create combined system prompt for default functionality
            guardrails = DEFAULT_PROMPT_GUARDRAILS.format(user_query=user_query)
            system_prompt = DEFAULT_PROMPT_SYSTEM.format(guardrails=guardrails)
        
        return conversation, system_prompt
    
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
        prompt_id: Optional[str], 
        user_query: str,
        db: AsyncSession,
        user: Optional[User] = None
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
            # Handle default prompt case (prompt_id is None, "default", or empty string)
            if prompt_id is None or prompt_id == "default" or prompt_id == "":
                # Use LLM to classify if query is related to nutrition or exercise
                if not await ChatService.classify_query_with_llm(user_query, user, category="nutrition and exercise"):
                    # Query is not related to nutrition/exercise, create denial response
                    raise HTTPException(
                        status_code=400,
                        detail="Query not related to Nutrition or Exercise. Please ask nutrition or exercise related questions."
                    )
                
                # Create default conversation
                conversation, system_prompt = await ChatService.create_default_conversation(
                    conv_id, user_id, user_query, db
                )
                # Store the custom system prompt for later use
                conversation._custom_system_prompt = system_prompt
                prompt = conversation._custom_system_prompt
                return conversation, prompt
            
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
            # For existing conversations, don't re-apply query classification
            # The guardrails will be applied in the chat processing methods
            prompt = conversation.prompt
        
        return conversation, prompt
    
    @staticmethod
    async def store_user_message(
        conversation_id: int, 
        user_id: int, 
        content: str, 
        db: AsyncSession,
        is_out_of_scope: bool = False
    ) -> ChatMessage:
        """Store user message in database"""
        user_msg = ChatMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            role=ChatRole.USER,
            content=content,
            is_out_of_scope=is_out_of_scope
        )
        db.add(user_msg)
        await db.commit()
        await db.refresh(user_msg)
        return user_msg
    
    @staticmethod
    async def get_conversation_history(conversation_id: int, db: AsyncSession, limit_messages: int = 4) -> List[Dict[str, str]]:
        """
        Get conversation history as list of message dicts with optional limiting
        
        Args:
            conversation_id: ID of the conversation
            db: Database session
            limit_messages: Maximum number of recent messages to return (default: 4 = 2 request-response pairs)
            
        Returns:
            List of message dictionaries
        """
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())  # Get most recent first
            .limit(limit_messages)
        )
        history = result.scalars().all()
        
        # Reverse to get chronological order and convert to dict format
        history_msgs = [
            {"role": m.role.value, "content": m.content}
            for m in reversed(history)  # Reverse to get chronological order
        ]
        return history_msgs
    
    @staticmethod
    async def store_assistant_message(
        conversation_id: int, 
        content: str, 
        db: AsyncSession,
        is_out_of_scope: bool = False
    ) -> ChatMessage:
        """Store assistant message in database"""
        assistant_msg = ChatMessage(
            conversation_id=conversation_id,
            user_id=None,
            role=ChatRole.ASSISTANT,
            content=content,
            is_out_of_scope=is_out_of_scope
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
            db=db,
            user=current_user # Pass current_user to get_or_create_conversation
        )
        
        # Store user message
        await ChatService.store_user_message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            content=chat_request.user_query,
            db=db
        )
        
        # Get conversation history (limited to reduce token usage)
        history_msgs = await ChatService.get_conversation_history(conversation.id, db, limit_messages=4)

        # CRITICAL FIX: Check profile completion FIRST, before guardrails
        # This ensures profile information is processed before being rejected by guardrails
        profile_response, should_continue_with_llm, profile_updated = await ProfileCompletionService.process_with_profile_completion(
            db=db,
            user_id=current_user.id,
            user_message=chat_request.user_query,
            conversation_history=history_msgs,
            user=current_user,
            prompt_type=chat_request.prompt_id if chat_request.prompt_id and chat_request.prompt_id != "" else "default"  # Use "default" for default prompts
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
                    prompt_id=chat_request.prompt_id,  # Include prompt_id in response
                    user_query=chat_request.user_query,
                    response=profile_response,
                    streamed=False
                )
            }

        # If profile was updated, return a confirmation and do NOT apply guardrails to this message
        if profile_updated:
            confirmation = profile_response or "Your profile has been updated. Now you can ask your nutrition question!"
            await ChatService.store_assistant_message(
                conversation_id=conversation.id,
                content=confirmation,
                db=db
            )
            return {
                "success": True,
                "message": "Profile updated",
                "data": ChatResponse(
                    conv_id=chat_request.conv_id,
                    prompt_id=chat_request.prompt_id,  # Include prompt_id in response
                    user_query=chat_request.user_query,
                    response=confirmation,
                    streamed=False
                )
            }

        # CRITICAL FIX: Apply dynamic category guardrails AFTER profile completion
        # This ensures profile information is processed before guardrails, but still protects against off-topic queries
        category = chat_request.prompt_id or "health and wellness"
        
        # Apply guardrails for all prompt types using dynamic LLM classification with conversation context
        logger.debug(f"Applying dynamic guardrails for category: {category}")
        is_allowed = await ChatService.classify_query_with_llm(
            chat_request.user_query, 
            current_user, 
            category=category,
            conversation_history=history_msgs  # Pass conversation history for context
        )
        if not is_allowed:
            logger.debug(f"Query rejected by dynamic guardrails for category: {category}")
            from apps.chat.prompts import DEFAULT_PROMPT_GUARDRAILS
            guardrails_prompt = DEFAULT_PROMPT_GUARDRAILS.format(user_query=chat_request.user_query)
            denial_response = await process_query_with_prompt(
                user_message=chat_request.user_query,
                system_prompt=guardrails_prompt,
                conversation_history=[],
                user=current_user,
                temperature=0.3,
                max_tokens=100
            )
            # Store assistant message as out-of-scope
            await ChatService.store_assistant_message(
                conversation_id=conversation.id,
                content=denial_response,
                db=db,
                is_out_of_scope=True
            )
            return {
                "success": True,
                "message": f"Query not related to Health and Wellness",
                "data": ChatResponse(
                    conv_id=chat_request.conv_id,
                    prompt_id=chat_request.prompt_id,  # Include prompt_id in response
                    user_query=chat_request.user_query,
                    response=denial_response,
                    streamed=False
                )
            }

        # Profile is complete or user provided profile info - proceed with LLM
        # Get system prompt and add profile context if available
        system_prompt = getattr(conversation, '_custom_system_prompt', None) or prompt.system_prompt
        
        # CRITICAL FIX: Apply dynamic guardrails for all conversations
        # This ensures all responses stay within health and wellness boundaries
        from apps.chat.prompts import DEFAULT_PROMPT_GUARDRAILS
        guardrails = DEFAULT_PROMPT_GUARDRAILS.format(user_query=chat_request.user_query)
        
        # If we have a custom system prompt (from default conversation), use it with guardrails
        if getattr(conversation, '_custom_system_prompt', None):
            system_prompt = f"{conversation._custom_system_prompt}\n\n{guardrails}"
        else:
            # For all prompts, add dynamic guardrails
            system_prompt = f"{system_prompt}\n\n{guardrails}"
        
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
                prompt_id=chat_request.prompt_id,  # Include prompt_id in response
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
            db=db,
            user=current_user # Pass current_user to get_or_create_conversation
        )
        
        # Store user message
        await ChatService.store_user_message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            content=chat_request.user_query,
            db=db
        )
        
        # Get conversation history (limited to reduce token usage)
        history_msgs = await ChatService.get_conversation_history(conversation.id, db, limit_messages=4)
        
        # CRITICAL FIX: Check profile completion FIRST, before guardrails
        # This ensures profile information is processed before being rejected by guardrails
        profile_response, should_continue_with_llm, profile_updated = await ProfileCompletionService.process_with_profile_completion(
            db=db,
            user_id=current_user.id,
            user_message=chat_request.user_query,
            conversation_history=history_msgs,
            user=current_user,
            prompt_type=chat_request.prompt_id if chat_request.prompt_id and chat_request.prompt_id != "" else "default"  # Use "default" for default prompts
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
        
        # CRITICAL FIX: Apply dynamic category guardrails AFTER profile completion
        # This ensures profile information is processed before guardrails, but still protects against off-topic queries
        category = chat_request.prompt_id or "health and wellness"
        
        # Apply guardrails for all prompt types using dynamic LLM classification with conversation context
        logger.debug(f"Applying dynamic guardrails for category: {category}")
        is_allowed = await ChatService.classify_query_with_llm(
            chat_request.user_query, 
            current_user, 
            category=category,
            conversation_history=history_msgs  # Pass conversation history for context
        )
        if not is_allowed:
            logger.debug(f"Query rejected by dynamic guardrails for category: {category}")
            from apps.chat.prompts import DEFAULT_PROMPT_GUARDRAILS
            guardrails_prompt = DEFAULT_PROMPT_GUARDRAILS.format(user_query=chat_request.user_query)
            denial_response = await process_query_with_prompt(
                user_message=chat_request.user_query,
                system_prompt=guardrails_prompt,
                conversation_history=[],
                user=current_user,
                temperature=0.3,
                max_tokens=100
            )
            # Store assistant message as out-of-scope
            await ChatService.store_assistant_message(
                conversation_id=conversation.id,
                content=denial_response,
                db=db,
                is_out_of_scope=True
            )
            async def denial_stream():
                yield denial_response
            return StreamingResponse(denial_stream(), media_type="text/plain")

        # Profile is complete or user provided profile info - proceed with LLM
        # Get system prompt and add profile context if available
        system_prompt = getattr(conversation, '_custom_system_prompt', None) or prompt.system_prompt
        
        # CRITICAL FIX: Apply dynamic guardrails for all conversations
        # This ensures all responses stay within health and wellness boundaries
        from apps.chat.prompts import DEFAULT_PROMPT_GUARDRAILS
        guardrails = DEFAULT_PROMPT_GUARDRAILS.format(user_query=chat_request.user_query)
        
        # If we have a custom system prompt (from default conversation), use it with guardrails
        if getattr(conversation, '_custom_system_prompt', None):
            system_prompt = f"{conversation._custom_system_prompt}\n\n{guardrails}"
        else:
            # For all prompts, add dynamic guardrails
            system_prompt = f"{system_prompt}\n\n{guardrails}"
        
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
    async def get_default_prompt_from_db(db: AsyncSession) -> Optional[Prompt]:
        """
        Get default prompt from database if it exists
        
        Args:
            db: Database session
            
        Returns:
            Optional[Prompt]: Default prompt from DB, or None if not found
        """
        try:
            result = await db.execute(
                select(Prompt).where(Prompt.prompt_type == DEFAULT_PROMPT_TYPE)
            )
            default_prompt = result.scalar_one_or_none()
            return default_prompt
        except Exception as e:
            logger.error(f"Error getting default prompt from DB: {e}")
            return None
    
    @staticmethod
    async def get_default_system_prompt(db: AsyncSession) -> str:
        """
        Get default system prompt - tries DB first, falls back to hardcoded
        
        Args:
            db: Database session
            
        Returns:
            str: Default system prompt
        """
        # Try to get default prompt from database
        default_prompt = await ChatService.get_default_prompt_from_db(db)
        
        if default_prompt and default_prompt.system_prompt:
            # Use database-stored default prompt
            logger.debug(f"Using database-stored default prompt: {default_prompt.name}")
            return default_prompt.system_prompt
        else:
            # Fallback to hardcoded default prompt
            logger.debug(f"Using hardcoded default prompt")
            return DEFAULT_PROMPT_SYSTEM
    
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
                created_at=str(m.created_at),
                is_out_of_scope=m.is_out_of_scope
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