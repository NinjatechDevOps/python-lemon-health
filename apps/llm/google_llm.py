import os
from typing import Optional
from google.generativeai import GenerativeModel, configure
from apps.llm.base import BaseLLMProvider
from dotenv import load_dotenv
from PIL import Image
import requests
from io import BytesIO

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")

class GoogleLLM(BaseLLMProvider):
    def __init__(self):
        configure(api_key=GOOGLE_API_KEY)
        self.model = GenerativeModel(GOOGLE_MODEL)

    def _encode_image(self, image: str) -> Image.Image:
        """
        Load an image from either a URL or local file path.
        
        Args:
            image (str): Either a URL or local file path
            
        Returns:
            Image.Image: PIL Image object
            
        Raises:
            FileNotFoundError: If the local image file doesn't exist
            ValueError: If there's an error loading the image
        """
        is_url = image.startswith(('http://', 'https://'))
        
        try:
            if is_url:
                response = requests.get(image)
                return Image.open(BytesIO(response.content))
            else:
                if not os.path.exists(image):
                    raise FileNotFoundError(f"Image file not found: {image}")
                return Image.open(image)
        except Exception as e:
            raise ValueError(f"Error loading image: {str(e)}")

    def chat(self, prompt: str, **kwargs) -> str:
        """
        Generate text based on a prompt using Google's Gemini model.
        
        Args:
            prompt (str): The text prompt to generate from
            **kwargs: Additional arguments like temperature, max_tokens, etc.
        
        Returns:
            str: The generated text
        """
        response = self.model.generate_content(
            prompt,
            generation_config={
                "temperature": kwargs.get("temperature", 0.0),
                "max_output_tokens": kwargs.get("max_tokens", 2048),
            }
        )
        return response.text

    def process_image(self, image: str, prompt: Optional[str] = None) -> str:
        """
        Process an image using Google's Gemini model.
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
        try:
            image_data = self._encode_image(image)
            
            # Prepare the content
            if prompt:
                response = self.model.generate_content([prompt, image_data])
            else:
                response = self.model.generate_content(image_data)

            return response.text

        except Exception as e:
            raise ValueError(f"Error processing image: {str(e)}")
