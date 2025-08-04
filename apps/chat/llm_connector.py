import os
import logging
from typing import Dict, Any, List

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


async def process_query_with_prompt(
    user_message: str, 
    system_prompt: str, 
    conversation_history: List[Dict[str, str]],
    user,
    **kwargs
) -> str:
    """
    Process a user query with a specific prompt and conversation history
    
    Args:
        user_message: The user's message text
        system_prompt: The system prompt to use
        conversation_history: Previous messages in the conversation
        user: The user object
        **kwargs: Additional parameters to pass to the LLM (e.g., temperature, max_tokens)
        
    Returns:
        The LLM's response text
    """
    # Create messages array with system prompt and conversation history
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add conversation history if available
    if conversation_history:
        messages.extend(conversation_history)
    
    # Add the current user message
    messages.append({"role": "user", "content": user_message})
    
    # Process the query through the LLM provider with additional parameters
    try:
        response = llm_provider.chat(messages, **kwargs)
        return response
    except Exception as e:
        logger.error(f"Error processing query with LLM: {str(e)}")
        return "I'm sorry, I encountered an error processing your request. Please try again later." 