import re
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.profile.models import Profile
from apps.chat.llm_connector import process_query_with_prompt
from apps.chat.prompts import (
    PROFILE_EXTRACTION_PROMPT,
    PROFILE_COMPLETION_MESSAGE_PROMPT,
    PROFILE_FIELD_MAPPING,
    PROFILE_INFO_DETECTION_PROMPT
)
from apps.core.logging_config import get_logger

logger = get_logger(__name__)


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
        # CRITICAL FIX: Use dynamic LLM-based classification instead of static keywords
        # This ensures any query can be properly classified without relying on predefined keywords
        
        # For now, we'll use a simple heuristic approach that can be enhanced with LLM later
        # The main goal is to avoid static keyword lists
        
        query_lower = user_query.lower()
        
        # Check for profile-dependent patterns (more flexible than static keywords)
        profile_dependent_patterns = [
            r'\bweight\s*loss\b',
            r'\bweight\s*gain\b', 
            r'\blose\s*weight\b',
            r'\bgain\s*weight\b',
            r'\bmy\s*(?:nutrition|diet|exercise|workout|plan)\b',
            r'\bpersonalized\b',
            r'\bcustomized\b',
            r'\btailored\b',
            r'\bmy\s*(?:age|height|weight|gender)\b',
            r'\bI\s*(?:am|want|need)\s*(?:to\s*)?(?:lose|gain|build)\b',
            r'\bcreate\s*(?:a|an)\s*(?:diet|nutrition|exercise|workout|fitness)\s*plan\b',
            r'\bplan\s*for\s*(?:me|my)\b',
            r'\brecommend\s*(?:a|an)\s*(?:diet|nutrition|exercise|workout)\b',
            r'\bsuggest\s*(?:a|an)\s*(?:diet|nutrition|exercise|workout)\b'
        ]
        
        import re
        for pattern in profile_dependent_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Found profile-dependent pattern: {pattern}")
                return True
        
        # Check for profile-independent patterns (general information requests)
        profile_independent_patterns = [
            r'\bbenefits\s*of\b',
            r'\bwhat\s*is\b',
            r'\bhow\s*to\s*cook\b',
            r'\brecipe\b',
            r'\bfood\s*guide\b',
            r'\bvitamin\b',
            r'\bmineral\b',
            r'\bsupplement\b',
            r'\bgeneral\b',
            r'\boverview\b',
            r'\binformation\b',
            r'\btips\b',
            r'\badvice\b',
            r'\bguide\b',
            r'\bexplain\b',
            r'\btell\s*me\s*about\b',
            r'\bwhat\s*are\s*(?:good|best)\s*sources\b',
            r'\bwhat\s*are\s*(?:the\s*)?benefits\b',
            r'\bhow\s*does\b',
            r'\bwhy\s*is\b',
            r'\bwhen\s*should\b',
            r'\bwhere\s*can\b'
        ]
        
        for pattern in profile_independent_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Found profile-independent pattern: {pattern}")
                return False
        
        # Default behavior based on prompt type
        if prompt_type in ['nutrition', 'exercise', 'default']:
            # For nutrition/exercise/default prompts, require profile unless explicitly general
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
        """Clean and convert extracted data to proper types with validation"""
        cleaned_data = {}
        
        for field, value in extracted_data.items():
            if value is not None and value != "" and value != "null":
                if field == 'date_of_birth':
                    # Handle both string and datetime.date objects
                    if isinstance(value, str):
                        # Convert date string to date object
                        date_obj = ProfileCompletionService.convert_date_string(value)
                        if date_obj:
                            cleaned_data[field] = date_obj
                    elif isinstance(value, date):
                        # Already a date object, use as is
                        cleaned_data[field] = value
                    else:
                        logger.debug(f"Invalid date_of_birth value type: {type(value)}, value: {value}")
                elif field == 'height':
                    # Convert to float and validate range
                    try:
                        if isinstance(value, str):
                            height_val = float(value)
                        elif isinstance(value, (int, float)):
                            height_val = float(value)
                        else:
                            logger.debug(f"Invalid height value type: {type(value)}, value: {value}")
                            continue

                        if extracted_data['height_unit'] is not None and extracted_data['height_unit'].lower() in ['cm', 'centimeters', 'centimeter'] and 100 <= height_val <= 250:  # Reasonable height range
                            cleaned_data[field] = height_val
                        elif extracted_data['height_unit'] is not None and extracted_data['height_unit'].lower() in ['ft', 'feet', 'foot','ft/in']:
                            cleaned_data[field] = height_val # Reasonable height range in feet
                        else:
                            logger.debug(f"Invalid height value: {height_val}, skipping")
                    except (ValueError, TypeError):
                        logger.debug(f"Could not convert height value: {value}")
                elif field == 'weight':
                    # Convert to float and validate range
                    try:
                        if isinstance(value, str):
                            weight_val = float(value)
                        elif isinstance(value, (int, float)):
                            weight_val = float(value)
                        else:
                            logger.debug(f"Invalid weight value type: {type(value)}, value: {value}")
                            continue
                            
                        if 20 <= weight_val <= 300:  # Reasonable weight range
                            cleaned_data[field] = weight_val
                        else:
                            logger.debug(f"Invalid weight value: {weight_val}, skipping")
                    except (ValueError, TypeError):
                        logger.debug(f"Could not convert weight value: {value}")
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
                            elif unit_lower in ['ft', 'feet', 'foot','ft/in']:
                                # cleaned_data[field] = 'ft'
                                cleaned_data[field] = 'ft/in'
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
                logger.debug(f"Extracted JSON string: {json_str}")
                extracted_data = json.loads(json_str)
            else:
                # If no JSON found, try to parse the entire response
                logger.debug(f"No JSON pattern found, trying to parse entire response: {response_clean}")
                extracted_data = json.loads(response_clean)
            
            # Clean and convert extracted data
            cleaned_data = ProfileCompletionService.clean_extracted_data(extracted_data)
            logger.debug(f"Cleaned extracted data: {cleaned_data}")
            
            return cleaned_data
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.debug(f"Raw LLM response: {response}")
            
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
            
            logger.debug(f"Manually extracted data: {extracted_data}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error in manual extraction: {e}")
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
            logger.error(f"Error updating profile: {e}")
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
    ) -> Tuple[str, bool, bool, str]:
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
            Tuple[str, bool, bool, str]: (response_message, should_continue_with_llm, profile_was_updated, original_query_to_process)
        """
        logger.info(f"Processing profile completion for user {user_id}")
        logger.info(f"User message: {user_message}")
        logger.info(f"Prompt type: {prompt_type}")
        
        # Check profile completeness for this specific query
        is_complete, missing_fields = await ProfileCompletionService.check_profile_completeness_for_query(
            db, user_id, user_message, prompt_type
        )
        
        logger.info(f"Profile complete: {is_complete}")
        logger.info(f"Missing fields: {missing_fields}")
        logger.info(f"Profile required for query: {ProfileCompletionService.is_profile_required(user_message, prompt_type)}")
        logger.info(f"Query contains 'weight loss': {'weight loss' in user_message.lower()}")
        
        # CRITICAL FIX: Use dynamic LLM-based detection instead of static patterns
        # This provides better accuracy and handles edge cases
        has_profile_info = await ProfileCompletionService.detect_profile_info_dynamically(
            user_message, conversation_history, user
        )
        
        logger.info(f"User message contains profile info (dynamic detection): {has_profile_info}")
        logger.info(f"Message: {user_message}")
        
        # Check if there was a previous query that needs to be addressed after profile completion
        original_query = None
        if has_profile_info and conversation_history:
            # Look for a recent user message that was asking for something that required profile
            # This will be the query to continue with after profile update
            # for msg in reversed(conversation_history[-4:]):  # Check last 4 messages
            #     if msg.get('role') == 'assistant' and any(field in msg.get('content', '').lower() for field in ['age', 'height', 'weight', 'gender', 'profile']):
            #         # Found a message asking for profile info, get the user's original query before that
            #         for original_msg in reversed(conversation_history[:-1]):
            #             if original_msg.get('role') == 'user' and not ProfileCompletionService.detect_profile_info_statically(original_msg.get('content', '')):
            #                 original_query = original_msg.get('content')
            #                 logger.info(f"Found original query to process after profile completion: {original_query}")
            #                 break

            for i in range(len(conversation_history) - 1, -1, -1):
                msg = conversation_history[i]
                if msg.get('role') == 'user':
                    # Check if this was a real query (not just profile info)
                    if not ProfileCompletionService.detect_profile_info_statically(msg.get('content', '')):
                        original_query = msg.get('content')
                        logger.info(f"Found original query to process after profile completion: {original_query}")
                        break
                    # Also check if there's an assistant message asking for profile before this
                    elif i > 0 and conversation_history[i-1].get('role') == 'assistant':
                        assistant_msg = conversation_history[i-1].get('content', '').lower()
                        if any(field in assistant_msg for field in ['age', 'height', 'weight', 'gender', 'profile', 'personalized']):
                            # Look for the user query before the assistant's profile request
                            for j in range(i-2, -1, -1):
                                if conversation_history[j].get('role') == 'user':
                                    if not ProfileCompletionService.detect_profile_info_statically(conversation_history[j].get('content', '')):
                                        original_query = conversation_history[j].get('content')
                                        logger.info(f"Found original query before profile request: {original_query}")
                                        break
                            break
        
        if has_profile_info:
            # User is providing profile info, try to extract and update
            logger.info("Attempting to extract profile information")
            
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
            
            logger.debug(f"Extracted data: {extracted_data}")
            
            if extracted_data:
                # Data is already cleaned in extract_profile_info, use directly
                logger.debug(f"Using extracted data directly: {extracted_data}")
                
                # Update profile with extracted data
                logger.info("Updating profile with extracted data")
                success = await ProfileCompletionService.update_profile(db, user_id, extracted_data)
                if success:
                    logger.info("Profile updated successfully")
                    updated_fields = list(extracted_data.keys())
                    
                    # Check if profile is now complete after the update
                    is_now_complete, remaining_fields = await ProfileCompletionService.check_profile_completeness_for_query(
                        db, user_id, original_query or user_message, prompt_type
                    )
                    
                    if is_now_complete and original_query:
                        # Profile is now complete and we have an original query to process
                        # Return a brief confirmation and process the original query
                        confirmation = "Thank you for providing your profile information. Let me now help you with your request about: " + original_query[:50] + "..."
                        return confirmation, True, True, original_query
                    elif is_now_complete:
                        # Profile is complete but no specific query to process
                        # Still return True to continue with LLM to provide a helpful response
                        return "Your profile has been updated successfully.", True, True, None
                    else:
                        # Profile still incomplete, ask for remaining fields
                        logger.info(f"Profile still incomplete after update. Remaining fields: {remaining_fields}")
                        # If we have an original query, include it in the context
                        query_context = original_query or user_message
                        profile_message = await ProfileCompletionService.generate_profile_completion_message(
                            query_context, remaining_fields, conversation_history, user
                        )
                        return profile_message, False, False, None
                else:
                    logger.error("Failed to update profile")
            else:
                logger.info("No data extracted from user message")
            
            # If extraction failed and profile is incomplete, generate LLM message asking for missing fields
            if not is_complete:
                logger.info("Extraction failed, generating profile completion message")
                profile_message = await ProfileCompletionService.generate_profile_completion_message(
                    user_message, missing_fields, conversation_history, user
                )
                return profile_message, False, False, None
        
        # If profile is complete and no profile info provided, proceed with normal chat
        if is_complete:
            logger.info("Profile is complete, proceeding with normal chat")
            return None, True, False, None
        
        # Profile is incomplete and user is not providing profile info, generate LLM message asking for missing fields
        logger.info("User not providing profile info, generating profile completion message")
        logger.info(f"Missing fields to request: {missing_fields}")
        profile_message = await ProfileCompletionService.generate_profile_completion_message(
            user_message, missing_fields, conversation_history, user
        )
        logger.debug(f"Generated profile completion message: {profile_message}")
        return profile_message, False, False, None 

    @staticmethod
    async def detect_profile_info_dynamically(user_message: str, conversation_history: List[Dict[str, str]], user) -> bool:
        """
        Use LLM to dynamically detect if user is providing profile information
        """
        try:
            detection_prompt = PROFILE_INFO_DETECTION_PROMPT.format(
                user_message=user_message,
                conversation_context=conversation_history[-2:] if conversation_history else "No recent context"
            )
            response = await process_query_with_prompt(
                user_message=user_message,
                system_prompt=detection_prompt,
                conversation_history=conversation_history[-2:] if conversation_history else [],
                user=user,
                temperature=0.1,  # Low temperature for consistent detection
                max_tokens=5      # Only need YES or NO
            )
            response_clean = response.strip().upper()
            logger.debug(f"DEBUG: Profile info detection response: '{response_clean}' for message: '{user_message}'")
            return response_clean == "YES"
        except Exception as e:
            logger.debug(f"DEBUG: Error in dynamic profile info detection: {e}")
            # Fallback to static pattern matching if LLM fails
            return ProfileCompletionService.detect_profile_info_statically(user_message)
    
    @staticmethod
    def is_acknowledgment_message(user_message: str) -> bool:
        """
        Check if the message is just an acknowledgment without meaningful content
        
        Args:
            user_message: User's message
            
        Returns:
            bool: True if it's an acknowledgment message
        """
        message_lower = user_message.lower().strip()
        
        # Common acknowledgment patterns
        acknowledgment_patterns = [
            r'^(thanks?|thank\s+you)',
            r'^(ok|okay|alright|sure|yes|yeah|yep)',
            r'^(got\s+it|understood|noted)',
            r'^(thanks?\s+for\s+sharing)',
            r'^(appreciate\s+it)',
            r'^(cool|great|good|nice|awesome)',
            r'^(perfect|excellent)',
        ]
        
        import re
        for pattern in acknowledgment_patterns:
            if re.match(pattern, message_lower):
                return True
        
        # Also check for very short messages (less than 15 chars) that might be acknowledgments
        if len(message_lower) < 15 and not any(char.isdigit() for char in message_lower):
            return True
            
        return False
    
    @staticmethod
    def detect_profile_info_statically(user_message: str) -> bool:
        """
        Fallback static pattern matching for profile information detection
        
        Args:
            user_message: User's message
            
        Returns:
            bool: True if user is providing profile information
        """
        # First check if it's just an acknowledgment
        if ProfileCompletionService.is_acknowledgment_message(user_message):
            return False
            
        message_lower = user_message.lower()
        
        # Check for explicit profile information patterns
        # profile_patterns = [
        #     r'\b\d+\s*(?:years?\s*old|y\.?o\.?)\b',  # age patterns
        #     r'\b\d+\s*(?:kg|kilograms?)\b',  # weight patterns
        #     r'\b\d+\s*(?:cm|centimeters?|ft|feet?)\b',  # height patterns
        #     r'\b(male|female|other)\b',  # gender patterns
        #     r'\bI\s+(?:am|weight|height|measure)\b',  # "I am/weight/height" patterns
        #     r'\bmy\s+(?:age|weight|height|gender)\b',  # "my age/weight/height" patterns
        # ]
        profile_patterns = [
            # ---- Age patterns ----
            r'\b\d+\s*(?:years?\s*old|yrs?|y\.?o\.?)\b',  # "25 years old", "25 yrs", "25 y.o."
            r'\b(?:age\s*(is|=)?\s*)?\d+\b',  # "age 25", "age is 25"
            r'\bI\s*am\s*\d+\b',  # "I am 25"
            r"\bI'm\s*\d+\b",  # "I'm 25"

            # ---- Weight patterns ----
            r'\b\d+\s*(?:kg|kilograms?|kgs?)\b',  # "70 kg", "70kgs"
            r'\b\d+\s*(?:pounds?|lbs?)\b',  # "150 lb", "150 lbs", "150 pounds"
            r'\b(?:weight\s*(is|=)?\s*)?\d+\b',  # "weight 67", "weight is 67"
            r'\bI\s*(?:weigh|weight)\s*\d+\b',  # "I weigh 67", "I weight 67"

            # ---- Height patterns ----
            r'\b\d+\s*(?:cm|centimeters?|cms?)\b',  # "170 cm", "170 cms"
            r'\b\d+\s*(?:m|meters?)\b',  # "1.75 m"
            r'\b\d+(\.\d+)?\s*(?:ft|feet|foot)\b',  # "5.8 ft", "5 feet"
            r'\b\d+[\'′]\s*\d*(?:\"|in|inch|inches)?\b',  # "5'7\"", "5′7", "5' 7 in"
            r'\b(?:height\s*(is|=)?\s*)?\d+(\.\d+)?\b',  # "height 165", "height is 165"
            r'\bI\s*(?:am|stand)\s*\d+(\.\d+)?\b',  # "I am 5.9", "I stand 6"

            # ---- Gender patterns ----
            r'\b(male|female|other|man|woman|girl|boy)\b',  # gender variations
            r'\b(?:gender\s*(is|=)?\s*)(male|female|other)\b',  # "gender is male"
            r'\bI\s*am\s*(male|female|other)\b',  # "I am male"
            r"\bI'm\s*(male|female|other)\b",  # "I'm female"

            # ---- Generic patterns ----
            r'\bI\s+(?:am|weigh|weight|height|stand|measure)\b',  # generic starters
            r'\bmy\s+(?:age|weight|height|gender)\b',  # "my age/weight..."
        ]

        import re
        for pattern in profile_patterns:
            if re.search(pattern, message_lower):
                logger.debug(f"DEBUG: Found static profile pattern: {pattern}")
                return True
        
        return False 