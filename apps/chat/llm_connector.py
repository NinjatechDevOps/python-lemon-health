import os
import logging
from typing import Dict, Any

from apps.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

# Get the LLM provider from environment variable or default to OpenAI
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")

# Initialize the LLM provider
try:
    llm_provider = get_llm_provider(LLM_PROVIDER)
    logger.info(f"Initialized LLM provider: {LLM_PROVIDER}")
except Exception as e:
    logger.error(f"Error initializing LLM provider: {str(e)}")
    # Fallback to OpenAI if specified provider fails
    llm_provider = get_llm_provider("openai")
    logger.info("Falling back to OpenAI LLM provider")


async def process_query(query: str, user) -> str:
    """
    Process a user query through the LLM and return the response
    
    Args:
        query: The user's query text
        user: The user object
        
    Returns:
        The LLM's response text
    """
    # Create a simple message format for the LLM
    messages = [
        {"role": "system", "content": f"You are a helpful health assistant named Lemon. The user is {user.first_name} {user.last_name}."},
        {"role": "user", "content": query}
    ]
    
    # Process the query through the LLM provider
    try:
        response = llm_provider.chat(messages)
        return response
    except Exception as e:
        logger.error(f"Error processing query with LLM: {str(e)}")
        return "I'm sorry, I encountered an error processing your request. Please try again later." 