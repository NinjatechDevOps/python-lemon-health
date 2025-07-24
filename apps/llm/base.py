from abc import ABC, abstractmethod
from typing import Optional

class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """Send a chat prompt and return the response"""
        pass

    @abstractmethod
    def process_image(self, image: str, prompt: Optional[str] = None) -> str:
        """Process an image and return the response"""
        pass