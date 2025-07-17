import os
import base64
from pathlib import Path
from typing import Optional, Union, List
from groq import Groq
from app.llm.base import BaseLLMProvider
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-4-scout-17b-16e-instruct")  # Default to Llama 4 Scout which supports images

class GroqLLM(BaseLLMProvider):
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = GROQ_MODEL

    def _encode_image(self, image_path: str) -> str:
        """
        Encode a local image file to base64.
        
        Args:
            image_path (str): Path to the local image file
            
        Returns:
            str: Base64 encoded image with proper data URI prefix
        """
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        # Determine the image type from the file extension
        image_type = Path(image_path).suffix.lower().lstrip('.')
        if image_type == 'jpg':
            image_type = 'jpeg'
        
        # Return the complete data URI
        return f"data:image/{image_type};base64,{encoded_string}"

    def chat(self, prompt: str, **kwargs) -> str:
        """
        Generate text based on a prompt using Groq's chat completions API.
        
        Args:
            prompt (str): The text prompt to generate from
            **kwargs: Additional arguments like temperature, max_tokens, etc.
        
        Returns:
            str: The generated text
        """
        response = self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.0),
        )
        return response.choices[0].message.content

    def process_image(self, image: str, prompt: Optional[str] = None) -> str:
        """
        Process an image using Groq's multimodal capabilities.
        Supports both local image files and image URLs.
        
        Args:
            image (str): Either a local file path or a URL to the image
            prompt (Optional[str]): Optional text prompt to accompany the image
            
        Returns:
            str: The model's response about the image
            
        Raises:
            FileNotFoundError: If the local image file doesn't exist
            ValueError: If the image format is not supported
        """
        # Construct the message with both text and image content
        message_content = []
        
        if prompt:
            message_content.append({
                "type": "text",
                "text": prompt
            })

        # Check if the input is a URL or local file
        is_url = image.startswith(('http://', 'https://', 'data:image/'))
        
        if is_url:
            image_url = image
        else:
            # Verify the file exists
            if not os.path.exists(image):
                raise FileNotFoundError(f"Image file not found: {image}")
            
            # Check if the file has a valid image extension
            valid_extensions = {'.jpg', '.jpeg', '.png'}
            file_ext = Path(image).suffix.lower()
            if file_ext not in valid_extensions:
                raise ValueError(f"Unsupported image format. Supported formats: {valid_extensions}")
            
            # Encode the local file
            image_url = self._encode_image(image)
            
        message_content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })

        messages = [{
            "role": "user",
            "content": message_content
        }]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0,
        )
        
        return response.choices[0].message.content