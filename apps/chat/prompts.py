"""
Chat Prompts Module

This module contains all the prompts used in the chat functionality,
excluding the six stored prompts (Booking, Shop, Nutrition, Exercise, Documents, Prescriptions).
"""

# Profile Completion Prompts
PROFILE_EXTRACTION_PROMPT = """You are a profile completion assistant. Extract the following missing profile information from the user's message: {missing_fields}.

Extraction rules:
- date_of_birth: Extract as YYYY-MM-DD format. If only age is mentioned, calculate birth year as (current year - age). Current year is {current_year}.
- height: Extract as number (assume cm if no unit specified)
- height_unit: Extract as 'cm' or 'ft' based on the unit mentioned or default to 'cm'
- weight: Extract as number (assume kg if no unit specified)  
- weight_unit: Extract as 'kg' only (default to 'kg' if no unit specified)
- gender: Extract as 'male', 'female', or 'other' (lowercase)

Return ONLY a JSON object with the extracted fields. If a field cannot be extracted, set it to null.4


Example response:
{{"date_of_birth": "1990-05-15", "height": 175, "height_unit": "cm", "weight": 70, "weight_unit": "kg", "gender": "male"}}"""

PROFILE_COMPLETION_MESSAGE_PROMPT = """You are a helpful health and nutrition assistant. The user has requested a nutrition plan, but their profile is incomplete. 

Missing profile information: {missing_fields}

Your task is to politely ask the user to provide the missing information so you can create a personalized nutrition plan. 

Guidelines:
1. Be friendly and professional
2. Explain why you need this information (for personalized recommendations)
3. Ask for the missing fields in a clear, structured way
4. Mention that this will help create a better, personalized plan
5. Keep the response conversational and helpful

The user's original request was: "{user_message}"

Respond as if you're having a natural conversation with the user."""

# Field mapping for profile completion messages
PROFILE_FIELD_MAPPING = {
    'date_of_birth': 'Age',
    'height': 'Height (cm or ft)',
    'weight': 'Weight (kg)',
    'gender': 'Gender'
}

# Profile completion message template (for reference)
PROFILE_COMPLETION_TEMPLATE = """To create a personalized nutrition plan, I need to know a few things about you. Please answer the following:

**Basic Info:**
1. Your goal: Lose weight / Gain muscle / Maintain weight / Improve energy/digestion/skin/etc.
2. Age:
3. Gender:
4. Height (cm or ft):
5. Weight (kg):
6. Activity level:

Please provide the missing information so I can create a personalized plan for you."""

# Future Prompts (for upcoming features)
DOCUMENT_ANALYSIS_PROMPT = """You are a health document analysis assistant. Analyze the provided document and extract relevant health information.

Guidelines:
1. Identify key health metrics, medications, conditions, and recommendations
2. Summarize the document in a clear, structured format
3. Highlight any important warnings or follow-up requirements
4. Provide actionable insights based on the document content

Document content: {document_content}

Please provide a comprehensive analysis of this health document."""

EXERCISE_RECOMMENDATION_PROMPT = """You are a fitness and exercise recommendation assistant. Based on the user's profile and goals, provide personalized exercise recommendations.

User Profile: {user_profile}
User Goal: {user_goal}

Guidelines:
1. Consider the user's current fitness level and any limitations
2. Provide a balanced mix of cardio, strength, and flexibility exercises
3. Include specific exercises with sets, reps, and duration
4. Offer modifications for different fitness levels
5. Include safety tips and proper form guidance

Please provide a comprehensive exercise plan tailored to the user's needs."""

NUTRITION_ANALYSIS_PROMPT = """You are a nutrition analysis assistant. Analyze the provided food diary or meal plan and provide nutritional insights.

Food Diary: {food_diary}

Guidelines:
1. Calculate estimated macronutrients (protein, carbs, fats)
2. Identify nutritional gaps or excesses
3. Suggest improvements for better balance
4. Consider the user's health goals and dietary restrictions
5. Provide practical recommendations for meal planning

Please provide a detailed nutritional analysis and recommendations.""" 