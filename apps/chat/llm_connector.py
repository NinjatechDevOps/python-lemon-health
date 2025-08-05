import os
import logging
from typing import Dict, Any, List

from apps.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

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
        # Run the synchronous LLM call in a thread pool to avoid blocking
        import asyncio
        import concurrent.futures
        import functools
        
        # Create a thread-safe wrapper for the LLM call
        def safe_llm_call(messages, **kwargs):
            try:
                provider = get_llm_provider_instance()
                return provider.chat(messages, **kwargs)
            except Exception as e:
                logger.error(f"Error in LLM call: {str(e)}")
                return "I'm sorry, I encountered an error processing your request. Please try again later."
        
        # Use ThreadPoolExecutor with proper error handling and retry
        max_retries = 2
        for attempt in range(max_retries):
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    loop = asyncio.get_event_loop()
                    # Use functools.partial to properly pass arguments
                    future = loop.run_in_executor(
                        executor, 
                        functools.partial(safe_llm_call, messages, **kwargs)
                    )
                    response = await asyncio.wait_for(future, timeout=30.0)  # 30 second timeout
                return response
            except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                if attempt == max_retries - 1:  # Last attempt
                    raise
                logger.warning(f"LLM call attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(0.5)  # Brief delay before retry
    except asyncio.CancelledError:
        logger.error("LLM request was cancelled")
        return "I'm sorry, the request was cancelled. Please try again."
    except asyncio.TimeoutError:
        logger.error("LLM request timed out")
        return "I'm sorry, the request timed out. Please try again."
    except Exception as e:
        logger.error(f"Error processing query with LLM: {str(e)}")
        return "I'm sorry, I encountered an error processing your request. Please try again later." 