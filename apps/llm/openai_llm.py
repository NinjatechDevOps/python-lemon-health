import os
import logging
from typing import List, Dict, Any, Optional

import openai
from openai import OpenAI

from apps.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class OpenAILLM(BaseLLMProvider):
    """OpenAI LLM provider implementation"""
    
    def __init__(self):
        """Initialize the OpenAI client"""
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set, OpenAI LLM will not work properly")
    
    def chat(self, messages: list[dict], **kwargs) -> str:
        """
        Send a chat prompt to OpenAI and return the response
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional arguments for the OpenAI API
            
        Returns:
            The text response from the model
        """
        try:
            if not self.api_key:
                return "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable."
            
            # Set default parameters
            temperature = kwargs.get("temperature", 0.5)
            max_tokens = kwargs.get("max_tokens", 1000)
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract and return the response text
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return f"Error processing your request: {str(e)}"
    
    def process_image(self, image: str, prompt: Optional[str] = None) -> str:
        """
        Process an image using OpenAI's vision capabilities
        
        Args:
            image: Base64 encoded image or URL to image
            prompt: Optional prompt to provide context for image analysis
            
        Returns:
            The text response from the model
        """
        try:
            if not self.api_key:
                return "OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable."
            
            # Prepare the messages
            messages = []
            
            # Add system message if provided
            if prompt:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image}
                        }
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": image}
                        }
                    ]
                })
            
            # Make the API call using a vision-capable model
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o which has vision capabilities
                messages=messages,
                max_tokens=1000
            )
            
            # Extract and return the response text
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error processing image with OpenAI: {str(e)}")
            return f"Error processing your image: {str(e)}" 