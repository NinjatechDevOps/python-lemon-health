import os
import asyncio
import logging
from typing import Dict, Any, List, Optional

from apps.llm.factory import get_llm_provider
from apps.auth.models import User
from apps.core.logging_config import get_logger

logger = get_logger(__name__)

# Get the LLM provider from environment variable or default to OpenAI
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")

# Initialize the LLM provider as a singleton
_llm_provider = None

def get_llm_provider_instance():
    """Get or create the LLM provider instance (singleton pattern)"""
    global _llm_provider
    if _llm_provider is None:
        try:
            _llm_provider = get_llm_provider(LLM_PROVIDER)
            logger.info(f"Initialized LLM provider: {LLM_PROVIDER}")
        except Exception as e:
            logger.error(f"Error initializing LLM provider: {str(e)}")
            # Fallback to OpenAI if specified provider fails
            _llm_provider = get_llm_provider("openai")
            logger.info("Falling back to OpenAI LLM provider")
    return _llm_provider


async def process_query_with_prompt(
    user_message: str, 
    system_prompt: str, 
    conversation_history: List[Dict[str, str]],
    user: User,
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
        # Run the synchronous LLM call in a thread pool to avoid blocking
        import concurrent.futures
        import functools
        
        # Get LLM provider instance
        llm_provider = get_llm_provider_instance()
        
        # Prepare messages for LLM
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        
        logger.debug(f"Processing query with {len(messages)} messages")
        
        # Call LLM with timeout and retry logic
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Use thread pool executor to run synchronous LLM call
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = loop.run_in_executor(
                        executor,
                        functools.partial(
                            llm_provider.chat,
                            messages=messages,
                            **kwargs
                        )
                    )
                    
                    # Wait for response with timeout
                    response = await asyncio.wait_for(future, timeout=30.0)
                    return response
                    
            except asyncio.TimeoutError:
                logger.warning(f"LLM request timed out on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("LLM request failed after all retries")
                    raise Exception("LLM request timed out after multiple attempts")
                    
            except Exception as e:
                logger.error(f"LLM request failed on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("LLM request failed after all retries")
                    raise e
                    
    except Exception as e:
        logger.error(f"Error in process_query_with_prompt: {e}")
        raise e 