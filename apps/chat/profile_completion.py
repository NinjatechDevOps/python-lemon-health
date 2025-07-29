import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.profile.models import Profile
from apps.chat.llm_connector import process_query_with_prompt
from apps.chat.prompts import (
    PROFILE_EXTRACTION_PROMPT,
    PROFILE_COMPLETION_MESSAGE_PROMPT,
    PROFILE_FIELD_MAPPING
)


class ProfileCompletionService:
    """Service for handling profile completion during chat conversations"""
    
    REQUIRED_FIELDS = ['date_of_birth', 'height', 'weight', 'gender']
    
    @staticmethod
    async def check_profile_completeness(db: AsyncSession, user_id: int) -> Tuple[bool, List[str]]:
        """
        Check if user profile is complete and return missing fields
        
        Returns:
            Tuple[bool, List[str]]: (is_complete, missing_fields)
        """
        result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        
        if not profile:
            return False, ProfileCompletionService.REQUIRED_FIELDS
        
        missing_fields = []
        for field in ProfileCompletionService.REQUIRED_FIELDS:
            value = getattr(profile, field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields
    
    @staticmethod
    def convert_date_string(date_str: str) -> Optional[date]:
        """Convert date string to datetime.date object"""
        try:
            if isinstance(date_str, str):
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def clean_extracted_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and convert extracted data to proper types"""
        cleaned_data = {}
        
        for field, value in extracted_data.items():
            if value is not None and value != "" and value != "null":
                if field == 'date_of_birth':
                    # Convert date string to date object
                    date_obj = ProfileCompletionService.convert_date_string(value)
                    if date_obj:
                        cleaned_data[field] = date_obj
                elif field in ['height', 'weight']:
                    # Convert to float
                    try:
                        cleaned_data[field] = float(value)
                    except (ValueError, TypeError):
                        pass
                elif field == 'gender':
                    # Ensure gender is properly capitalized for schema validation
                    if isinstance(value, str):
                        gender_lower = value.lower()
                        if gender_lower == 'male':
                            cleaned_data[field] = 'Male'
                        elif gender_lower == 'female':
                            cleaned_data[field] = 'Female'
                        elif gender_lower == 'other':
                            cleaned_data[field] = 'Other'
                elif field in ['height_unit', 'weight_unit']:
                    # Ensure units are properly formatted - only standard formats
                    if isinstance(value, str):
                        unit_lower = value.lower()
                        if field == 'height_unit':
                            if unit_lower in ['cm', 'centimeters', 'centimeter']:
                                cleaned_data[field] = 'cm'
                            elif unit_lower in ['ft', 'feet', 'foot']:
                                cleaned_data[field] = 'ft'
                        elif field == 'weight_unit':
                            if unit_lower in ['kg', 'kilograms', 'kilogram']:
                                cleaned_data[field] = 'kg'
        
        return cleaned_data
    
    @staticmethod
    async def extract_profile_info(
        user_message: str, 
        conversation_history: List[Dict[str, str]], 
        missing_fields: List[str],
        user
    ) -> Dict[str, Any]:
        """
        Extract profile information from user message using LLM
        
        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            missing_fields: List of missing profile fields
            user: User object
            
        Returns:
            Dict containing extracted profile information
        """
        # Get current year dynamically
        current_year = datetime.now().year
        
        # Use prompt from prompts module with current year
        system_prompt = PROFILE_EXTRACTION_PROMPT.format(
            missing_fields=', '.join(missing_fields),
            current_year=current_year
        )

        # Process with LLM
        response = await process_query_with_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user=user
        )
        
        # Parse JSON response
        try:
            import json
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                extracted_data = json.loads(json_match.group())
            else:
                extracted_data = json.loads(response)
            
            # Clean and convert extracted data
            cleaned_data = ProfileCompletionService.clean_extracted_data(extracted_data)
            
            return cleaned_data
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            return {}
    
    @staticmethod
    async def update_profile(db: AsyncSession, user_id: int, profile_data: Dict[str, Any]) -> bool:
        """
        Update user profile with extracted data
        
        Args:
            db: Database session
            user_id: User ID
            profile_data: Dictionary of profile fields to update
            
        Returns:
            bool: True if update successful
        """
        try:
            result = await db.execute(select(Profile).where(Profile.user_id == user_id))
            profile = result.scalar_one_or_none()
            
            if not profile:
                # Create new profile
                profile = Profile(user_id=user_id)
                db.add(profile)
            
            # Update fields with proper type conversion
            for field, value in profile_data.items():
                if hasattr(profile, field) and value is not None:
                    setattr(profile, field, value)
            
            await db.commit()
            await db.refresh(profile)
            return True
            
        except Exception as e:
            print(f"Error updating profile: {e}")
            await db.rollback()
            return False
    
    @staticmethod
    async def generate_profile_completion_message(
        user_message: str,
        missing_fields: List[str],
        conversation_history: List[Dict[str, str]],
        user
    ) -> str:
        """
        Generate a profile completion message using LLM
        
        Args:
            user_message: Current user message
            missing_fields: List of missing profile fields
            conversation_history: Previous conversation messages
            user: User object
            
        Returns:
            str: LLM-generated message asking for missing profile information
        """
        # Use field mapping from prompts module
        missing_field_names = [PROFILE_FIELD_MAPPING.get(field, field) for field in missing_fields]
        
        # Use prompt from prompts module
        system_prompt = PROFILE_COMPLETION_MESSAGE_PROMPT.format(
            missing_fields=', '.join(missing_field_names),
            user_message=user_message
        )

        # Process with LLM to generate the profile completion message
        response = await process_query_with_prompt(
            user_message=user_message,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user=user
        )
        
        return response
    
    @staticmethod
    async def get_user_profile_context(db: AsyncSession, user_id: int) -> str:
        """
        Get user's profile data as context string for LLM
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            str: Profile context string
        """
        result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        
        if not profile:
            return ""
        
        context_parts = []
        if profile.date_of_birth:
            age = (datetime.now().date() - profile.date_of_birth).days // 365
            context_parts.append(f"Age: {age} years old")
        if profile.gender:
            context_parts.append(f"Gender: {profile.gender}")
        if profile.height:
            height_unit = profile.height_unit or "cm"
            context_parts.append(f"Height: {profile.height}{height_unit}")
        if profile.weight:
            weight_unit = profile.weight_unit or "kg"
            context_parts.append(f"Weight: {profile.weight}{weight_unit}")
        
        return f"User Profile: {', '.join(context_parts)}" if context_parts else ""
    
    @staticmethod
    async def process_with_profile_completion(
        db: AsyncSession,
        user_id: int,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        user
    ) -> Tuple[str, bool, bool]:
        """
        Process user message with profile completion if needed
        
        Args:
            db: Database session
            user_id: User ID
            user_message: User's message
            conversation_history: Previous conversation messages
            user: User object
            
        Returns:
            Tuple[str, bool, bool]: (response_message, should_continue_with_llm, profile_was_updated)
        """
        # Check profile completeness
        is_complete, missing_fields = await ProfileCompletionService.check_profile_completeness(db, user_id)
        
        if is_complete:
            # Profile is complete, proceed with normal chat
            return None, True, False
        
        # Profile is incomplete - check if user is providing profile info
        # Look for profile-related keywords in the message
        profile_keywords = ['age', 'years old', 'height', 'weight', 'kg', 'cm', 'male', 'female', 'other', 'gender']
        message_lower = user_message.lower()
        
        has_profile_info = any(keyword in message_lower for keyword in profile_keywords)
        
        if has_profile_info:
            # User is providing profile info, try to extract and update
            extracted_data = await ProfileCompletionService.extract_profile_info(
                user_message, conversation_history, missing_fields, user
            )
            
            if extracted_data:
                # Update profile with extracted data
                success = await ProfileCompletionService.update_profile(db, user_id, extracted_data)
                if success:
                    return f"I've updated your profile with the information you provided: {', '.join(extracted_data.keys())}. Now let me help you with your request.", True, True
            
            # If extraction failed, generate LLM message asking for missing fields
            profile_message = await ProfileCompletionService.generate_profile_completion_message(
                user_message, missing_fields, conversation_history, user
            )
            return profile_message, False, False
        else:
            # User is not providing profile info, generate LLM message asking for missing fields
            profile_message = await ProfileCompletionService.generate_profile_completion_message(
                user_message, missing_fields, conversation_history, user
            )
            return profile_message, False, False 