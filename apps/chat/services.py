from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models import User
from apps.profile.models import Profile
from apps.profile.services import ProfileService
from apps.chat.models import ChatMessage, QueryType
from apps.chat.llm_service import llm_service

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling chat operations"""
    
    @staticmethod
    async def process_user_query(
        db: AsyncSession,
        user: User,
        query: str
    ) -> Dict[str, Any]:
        """
        Process a user query and return a response
        
        Steps:
        1. Classify the query type
        2. Check if profile data is needed
        3. If profile data is missing, return a response asking for it
        4. Otherwise, generate a response using the LLM
        5. Save the chat message
        """
        # Step 1: Classify the query
        query_type = await llm_service.classify_query(query)
        
        # Step 2: Get user profile
        profile = await ProfileService.get_profile_by_user_id(db, user.id)
        
        # Step 3: Check if profile data is needed
        profile_complete, missing_fields = await llm_service.check_profile_requirements(query_type, profile)
        
        # Step 4: Generate response
        if not profile_complete:
            # Profile data is missing, return a response asking for it
            response = await llm_service.generate_response(query, query_type, user.first_name)
            
            # Save chat message
            chat_message = ChatMessage(
                user_id=user.id,
                query=query,
                response=response,
                query_type=query_type
            )
            db.add(chat_message)
            await db.commit()
            await db.refresh(chat_message)
            
            return {
                "response": response,
                "requires_profile_completion": True,
                "required_fields": missing_fields,
                "message_id": chat_message.id,
                "query_type": query_type
            }
        else:
            # Profile data is complete, generate a response
            response = await llm_service.generate_response(
                query=query,
                query_type=query_type,
                user_name=user.first_name,
                profile=profile
            )
            
            # Save chat message
            chat_message = ChatMessage(
                user_id=user.id,
                query=query,
                response=response,
                query_type=query_type
            )
            db.add(chat_message)
            await db.commit()
            await db.refresh(chat_message)
            
            return {
                "response": response,
                "requires_profile_completion": False,
                "message_id": chat_message.id,
                "query_type": query_type
            }
    
    @staticmethod
    async def update_profile_and_process_query(
        db: AsyncSession,
        user: User,
        profile_data: Dict[str, Any],
        original_query: str,
        query_type: QueryType
    ) -> Dict[str, Any]:
        """
        Update user profile with provided data and then process the original query
        
        Steps:
        1. Get or create user profile
        2. Update profile with provided data
        3. Process the original query with the updated profile
        """
        # Step 1: Get or create user profile
        profile = await ProfileService.get_profile_by_user_id(db, user.id)
        if not profile:
            # Create a new profile with the provided data
            from apps.profile.schemas import ProfileCreate
            profile_create = ProfileCreate(**profile_data)
            profile = await ProfileService.create_profile(db, profile_create, user.id)
        else:
            # Update existing profile
            from apps.profile.schemas import ProfileUpdate
            profile_update = ProfileUpdate(**profile_data)
            profile = await ProfileService.update_profile(db, profile, profile_update)
        
        # Step 3: Generate response with updated profile
        response = await llm_service.generate_response(
            query=original_query,
            query_type=query_type,
            user_name=user.first_name,
            profile=profile
        )
        
        # Save chat message
        chat_message = ChatMessage(
            user_id=user.id,
            query=original_query,
            response=response,
            query_type=query_type
        )
        db.add(chat_message)
        await db.commit()
        await db.refresh(chat_message)
        
        return {
            "response": response,
            "requires_profile_completion": False,
            "message_id": chat_message.id,
            "query_type": query_type
        }
    
    @staticmethod
    async def get_chat_history(
        db: AsyncSession,
        user_id: int,
        limit: int = 20,
        skip: int = 0
    ) -> List[ChatMessage]:
        """Get chat history for a user"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(desc(ChatMessage.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_chat_message(
        db: AsyncSession,
        message_id: int,
        user_id: int
    ) -> Optional[ChatMessage]:
        """Get a specific chat message"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.id == message_id, ChatMessage.user_id == user_id)
        )
        return result.scalars().first()


chat_service = ChatService()
