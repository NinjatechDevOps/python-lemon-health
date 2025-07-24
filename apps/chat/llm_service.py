import os
import json
import logging
from typing import Dict, List, Any, Tuple, Optional

import httpx

from apps.chat.models import QueryType
from apps.profile.models import Profile

logger = logging.getLogger(__name__)

# This would be in the environment variables in production
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")


class LLMService:
    """Service for interacting with the language model"""
    
    @staticmethod
    async def classify_query(query: str) -> QueryType:
        """Classify the type of query"""
        query_lower = query.lower()
        
        # Simple rule-based classification
        if any(word in query_lower for word in ["nutrition", "diet", "food", "meal", "eat"]):
            return QueryType.NUTRITION
        elif any(word in query_lower for word in ["exercise", "workout", "fitness", "training"]):
            return QueryType.EXERCISE
        elif any(word in query_lower for word in ["document", "report", "test", "pdf"]):
            return QueryType.DOCUMENT
        elif any(word in query_lower for word in ["health", "medical", "doctor", "symptom"]):
            return QueryType.HEALTH
        else:
            return QueryType.GENERAL
    
    @staticmethod
    async def check_profile_requirements(query_type: QueryType, profile: Optional[Profile]) -> Tuple[bool, List[str]]:
        """Check if the profile has all required fields for the query type"""
        required_fields = []
        
        if query_type in [QueryType.NUTRITION, QueryType.EXERCISE]:
            # For nutrition and exercise plans, we need basic profile info
            if not profile:
                return False, ["height", "weight", "date_of_birth", "gender"]
            
            if not profile.height:
                required_fields.append("height")
            if not profile.weight:
                required_fields.append("weight")
            if not profile.date_of_birth:
                required_fields.append("date_of_birth")
            if not profile.gender:
                required_fields.append("gender")
        
        return len(required_fields) == 0, required_fields
    
    @staticmethod
    async def generate_response(
        query: str, 
        query_type: QueryType, 
        user_name: str,
        profile: Optional[Profile] = None
    ) -> str:
        """Generate a response using the language model"""
        try:
            # Prepare the system prompt based on query type
            system_prompt = "You are a helpful health assistant named Lemon."
            
            if query_type == QueryType.NUTRITION:
                system_prompt += " You specialize in providing personalized nutrition advice."
                if profile:
                    system_prompt += f" The user is {profile.user.full_name}, "
                    if profile.gender:
                        system_prompt += f"gender: {profile.gender}, "
                    if profile.date_of_birth:
                        system_prompt += f"date of birth: {profile.date_of_birth}, "
                    if profile.height:
                        system_prompt += f"height: {profile.height}{profile.height_unit or 'cm'}, "
                    if profile.weight:
                        system_prompt += f"weight: {profile.weight}{profile.weight_unit or 'kg'}, "
            
            elif query_type == QueryType.EXERCISE:
                system_prompt += " You specialize in providing personalized exercise recommendations."
                if profile:
                    system_prompt += f" The user is {profile.user.full_name}, "
                    if profile.gender:
                        system_prompt += f"gender: {profile.gender}, "
                    if profile.date_of_birth:
                        system_prompt += f"date of birth: {profile.date_of_birth}, "
                    if profile.height:
                        system_prompt += f"height: {profile.height}{profile.height_unit or 'cm'}, "
                    if profile.weight:
                        system_prompt += f"weight: {profile.weight}{profile.weight_unit or 'kg'}, "
            
            # Make API call to LLM
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}"
            }
            
            payload = {
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.7
            }
            
            # For development/testing, return mock responses
            if not LLM_API_KEY:
                logger.warning("No LLM API key set, returning mock response")
                return LLMService._get_mock_response(query_type, user_name)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    LLM_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    return response_data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM API error: {response.status_code} - {response.text}")
                    return "I'm sorry, I'm having trouble processing your request right now. Please try again later."
        
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again later."
    
    @staticmethod
    def _get_mock_response(query_type: QueryType, user_name: str) -> str:
        """Get a mock response for development/testing"""
        if query_type == QueryType.NUTRITION:
            return f"""To create a personalized nutrition plan, I need to know a few things about you. Please answer the following:

Basic Info

1. Your goal:
• Lose weight
• Gain muscle
• Maintain weight
• Improve energy/digestion/skin/etc.

2. Age:
3. Gender:
4. Height (cm or ft/in):
5. Weight (kg or lbs):
6. Activity level:"""
        
        elif query_type == QueryType.EXERCISE:
            return f"""Absolutely! Here's a mix of effective exercises depending on your goal — I'll list options for different fitness levels and types of goals.

🔥 If your goal is weight loss (fat burning):

🏃‍♂️ Cardio (3–5×/week):
• Brisk walking (30–45 mins)
• Jogging or running
• Cycling
• Jump rope (great for home)
• Dancing / Zumba
• Swimming

🧘 Low-impact option:
• Power yoga
• Pilates"""
        
        else:
            return f"Hello {user_name}! How can I help you with your health today?"

llm_service = LLMService() 