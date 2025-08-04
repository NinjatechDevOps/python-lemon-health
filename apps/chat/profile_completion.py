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
    
    # Queries that require complete profile data
    PROFILE_DEPENDENT_QUERIES = [
        'nutrition plan', 'diet plan', 'meal plan', 'calorie', 'macronutrient',
        'weight loss', 'weight gain', 'muscle gain', 'fitness plan', 'exercise plan',
        'workout plan', 'training plan', 'personalized', 'customized', 'tailored',
        'my plan', 'my nutrition', 'my diet', 'my exercise', 'my workout'
    ]
    
    # Queries that don't need profile data
    PROFILE_INDEPENDENT_QUERIES = [
        'benefits of', 'what is', 'how to cook', 'recipe', 'food guide',
        'vitamin', 'mineral', 'supplement', 'general', 'overview', 'information',
        'tips', 'advice', 'guide', 'explain', 'tell me about'
    ]
    
    @staticmethod
    def is_profile_required(user_query: str, prompt_type: str) -> bool:
        """
        Determine if profile data is required for the given query
        
        Args:
            user_query: User's query
            prompt_type: Type of prompt (nutrition, exercise, etc.)
            
        Returns:
            bool: True if profile data is required
        """
        query_lower = user_query.lower()
        
        # Check for profile-dependent keywords
        for keyword in ProfileCompletionService.PROFILE_DEPENDENT_QUERIES:
            if keyword in query_lower:
                return True
        
        # Check for profile-independent keywords
        for keyword in ProfileCompletionService.PROFILE_INDEPENDENT_QUERIES:
            if keyword in query_lower:
                return False
        
        # Default behavior based on prompt type
        if prompt_type in ['nutrition', 'exercise']:
            # For nutrition/exercise prompts, require profile unless explicitly general
            return True
        else:
            # For other prompts (documents, prescriptions, etc.), profile not required
            return False
    
    @staticmethod
    def get_required_fields_for_query(user_query: str, prompt_type: str) -> List[str]:
        """
        Get the specific profile fields required for the given query
        
        Args:
            user_query: User's query
            prompt_type: Type of prompt
            
        Returns:
            List[str]: Required profile fields
        """
        query_lower = user_query.lower()
        
        # Default required fields
        required_fields = ['date_of_birth', 'height', 'weight', 'gender']
        
        # Adjust based on query context
        if 'nutrition' in prompt_type or 'diet' in query_lower or 'meal' in query_lower:
            # Nutrition queries need all fields for accurate recommendations
            return required_fields
        elif 'exercise' in prompt_type or 'workout' in query_lower or 'fitness' in query_lower:
            # Exercise queries need age, gender, height, weight
            return required_fields
        elif 'weight' in query_lower:
            # Weight-related queries need height and weight
            return ['height', 'weight']
        elif 'age' in query_lower or 'years old' in query_lower:
            # Age-specific queries might only need age
            return ['date_of_birth']
        
        return required_fields
    
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
    async def check_profile_completeness_for_query(
        db: AsyncSession, 
        user_id: int, 
        user_query: str, 
        prompt_type: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if profile is complete for the specific query context
        
        Args:
            db: Database session
            user_id: User ID
            user_query: User's query
            prompt_type: Type of prompt
            
        Returns:
            Tuple[bool, List[str]]: (is_complete, missing_fields)
        """
        # First check if profile is required for this query
        if not ProfileCompletionService.is_profile_required(user_query, prompt_type):
            return True, []  # Profile not required, consider complete
        
        # Get required fields for this specific query
        required_fields = ProfileCompletionService.get_required_fields_for_query(user_query, prompt_type)
        
        result = await db.execute(select(Profile).where(Profile.user_id == user_id))
        profile = result.scalar_one_or_none()
        
        if not profile:
            return False, required_fields
        
        missing_fields = []
        for field in required_fields:
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
            user=user,
            temperature=0.3,  # Lower temperature for more consistent data extraction
            max_tokens=800    # Sufficient tokens for profile data
        )
        
        # Parse JSON response with improved error handling
        try:
            import json
            import re
            
            # Clean the response - remove any extra text before/after JSON
            response_clean = response.strip()
            
            # Try to find JSON object in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_clean, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                print(f"Extracted JSON string: {json_str}")
                extracted_data = json.loads(json_str)
            else:
                # If no JSON found, try to parse the entire response
                print(f"No JSON pattern found, trying to parse entire response: {response_clean}")
                extracted_data = json.loads(response_clean)
            
            # Clean and convert extracted data
            cleaned_data = ProfileCompletionService.clean_extracted_data(extracted_data)
            print(f"Cleaned extracted data: {cleaned_data}")
            
            return cleaned_data
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Raw LLM response: {response}")
            
            # Try to extract data manually if JSON parsing fails
            return ProfileCompletionService.extract_data_manually(response, missing_fields)
    
    @staticmethod
    def extract_data_manually(response: str, missing_fields: List[str]) -> Dict[str, Any]:
        """
        Manually extract profile data from LLM response when JSON parsing fails
        
        Args:
            response: LLM response string
            missing_fields: List of missing profile fields
            
        Returns:
            Dict containing extracted profile information
        """
        extracted_data = {}
        response_lower = response.lower()
        
        try:
            # Extract age/date_of_birth
            if 'date_of_birth' in missing_fields:
                age_match = re.search(r'(\d+)\s*(?:years?\s*old|y\.?o\.?)', response_lower)
                if age_match:
                    age = int(age_match.group(1))
                    current_year = datetime.now().year
                    current_month = datetime.now().month
                    current_day = datetime.now().day
                    
                    # More accurate age calculation
                    birth_year = current_year - age
                    # If birthday hasn't passed this year, subtract one more year
                    if current_month < 1 or (current_month == 1 and current_day < 1):
                        birth_year -= 1
                    
                    extracted_data['date_of_birth'] = f"{birth_year}-01-01"
            
            # Extract height - only if explicitly mentioned in user message
            if 'height' in missing_fields:
                height_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cm|centimeters?)', response_lower)
                if height_match:
                    extracted_data['height'] = float(height_match.group(1))
                    extracted_data['height_unit'] = 'cm'
                else:
                    # Check for feet
                    feet_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ft|feet?)', response_lower)
                    if feet_match:
                        extracted_data['height'] = float(feet_match.group(1))
                        extracted_data['height_unit'] = 'ft'
            
            # Extract weight - only if explicitly mentioned in user message
            if 'weight' in missing_fields:
                weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|kilograms?)', response_lower)
                if weight_match:
                    extracted_data['weight'] = float(weight_match.group(1))
                    extracted_data['weight_unit'] = 'kg'
            
            # Extract gender - only if explicitly mentioned in user message
            if 'gender' in missing_fields:
                # More specific gender extraction to avoid false positives
                gender_patterns = [
                    (r'\b(?:i am|i\'m)\s+(male)\b', 'Male'),
                    (r'\b(?:i am|i\'m)\s+(female)\b', 'Female'),
                    (r'\b(?:gender|sex)\s+(?:is\s+)?(male)\b', 'Male'),
                    (r'\b(?:gender|sex)\s+(?:is\s+)?(female)\b', 'Female'),
                    (r'\b(?:male)\s+(?:gender|sex)\b', 'Male'),
                    (r'\b(?:female)\s+(?:gender|sex)\b', 'Female'),
                    (r'\b(?:i\'m|i am)\s+(male)\b', 'Male'),
                    (r'\b(?:i\'m|i am)\s+(female)\b', 'Female'),
                ]
                
                for pattern, gender_value in gender_patterns:
                    match = re.search(pattern, response_lower)
                    if match:
                        extracted_data['gender'] = gender_value
                        break
                
                # Fallback to simple check if no pattern matched
                if 'gender' not in extracted_data:
                    if 'male' in response_lower and 'female' not in response_lower and 'other' not in response_lower:
                        extracted_data['gender'] = 'Male'
                    elif 'female' in response_lower and 'male' not in response_lower and 'other' not in response_lower:
                        extracted_data['gender'] = 'Female'
                    elif 'other' in response_lower and 'male' not in response_lower and 'female' not in response_lower:
                        extracted_data['gender'] = 'Other'
            
            print(f"Manually extracted data: {extracted_data}")
            return extracted_data
            
        except Exception as e:
            print(f"Error in manual extraction: {e}")
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
            user=user,
            temperature=0.5,  # Moderate temperature for friendly profile requests
            max_tokens=600    # Sufficient tokens for profile completion message
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
        user,
        prompt_type: str = None
    ) -> Tuple[str, bool, bool]:
        """
        Process user message with profile completion if needed
        
        Args:
            db: Database session
            user_id: User ID
            user_message: User's message
            conversation_history: Previous conversation messages
            user: User object
            prompt_type: Type of prompt (nutrition, exercise, etc.)
            
        Returns:
            Tuple[str, bool, bool]: (response_message, should_continue_with_llm, profile_was_updated)
        """
        print(f"Processing profile completion for user {user_id}")
        print(f"User message: {user_message}")
        print(f"Prompt type: {prompt_type}")
        
        # Check profile completeness for this specific query
        is_complete, missing_fields = await ProfileCompletionService.check_profile_completeness_for_query(
            db, user_id, user_message, prompt_type
        )
        
        print(f"Profile complete: {is_complete}")
        print(f"Missing fields: {missing_fields}")
        
        # Check if user is providing profile info (regardless of completeness)
        profile_keywords = ['age', 'years old', 'height', 'weight', 'kg', 'cm', 'male', 'female', 'other', 'gender']
        message_lower = user_message.lower()
        
        has_profile_info = any(keyword in message_lower for keyword in profile_keywords)
        print(f"User message contains profile info: {has_profile_info}")
        
        if has_profile_info:
            # User is providing profile info, try to extract and update
            print("Attempting to extract profile information")
            
            # If profile is complete, extract all fields that might be updated
            if is_complete:
                # For complete profiles, check for any profile-related fields
                all_fields = ['date_of_birth', 'height', 'weight', 'gender']
                extracted_data = await ProfileCompletionService.extract_profile_info(
                    user_message, conversation_history, all_fields, user
                )
            else:
                # For incomplete profiles, only extract missing fields
                extracted_data = await ProfileCompletionService.extract_profile_info(
                    user_message, conversation_history, missing_fields, user
                )
            
            print(f"Extracted data: {extracted_data}")
            
            if extracted_data:
                # Update profile with extracted data
                print("Updating profile with extracted data")
                success = await ProfileCompletionService.update_profile(db, user_id, extracted_data)
                if success:
                    print("Profile updated successfully")
                    return f"I've updated your profile with the information you provided: {', '.join(extracted_data.keys())}. Now let me help you with your request.", True, True
            
            # If extraction failed and profile is incomplete, generate LLM message asking for missing fields
            if not is_complete:
                print("Extraction failed, generating profile completion message")
                profile_message = await ProfileCompletionService.generate_profile_completion_message(
                    user_message, missing_fields, conversation_history, user
                )
                return profile_message, False, False
        
        # If profile is complete and no profile info provided, proceed with normal chat
        if is_complete:
            print("Profile is complete, proceeding with normal chat")
            return None, True, False
        
        # Profile is incomplete and user is not providing profile info, generate LLM message asking for missing fields
        print("User not providing profile info, generating profile completion message")
        profile_message = await ProfileCompletionService.generate_profile_completion_message(
            user_message, missing_fields, conversation_history, user
        )
        return profile_message, False, False 