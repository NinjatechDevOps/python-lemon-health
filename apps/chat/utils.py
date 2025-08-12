import logging
from apps.core.logging_config import get_logger
from typing import Optional
from apps.core.config import settings

logger = get_logger(__name__)

def convert_icon_path_to_complete_url(icon_path: Optional[str]) -> Optional[str]:
    """
    Convert relative icon path to complete URL using BE_BASE_URL
    
    Args:
        icon_path: Relative path like "/static/prompts_icon/filename.png"
        
    Returns:
        Complete URL like "http://localhost:8000/static/prompts_icon/filename.png"
        or None if icon_path is None
    """
    if not icon_path:
        return None
    
    # Remove leading slash if present to avoid double slashes
    if icon_path.startswith('/'):
        icon_path = icon_path[1:]
    
    return f"{settings.BE_BASE_URL}/{icon_path}"

def convert_file_path_to_complete_url(file_path: Optional[str]) -> Optional[str]:
    """
    Convert file path to complete URL using BE_BASE_URL
    
    Args:
        file_path: Full file path like "/home/user/project/media/documents/user_id/filename.pdf"
        
    Returns:
        Complete URL like "http://localhost:8000/media/documents/user_id/filename.pdf"
        or None if file_path is None
    """
    if not file_path:
        return None
    
    # Extract the relative path from the media directory
    # file_path is like "/home/user/project/media/documents/user_id/filename.pdf"
    # We need to extract "documents/user_id/filename.pdf" part
    import os
    from apps.core.config import settings
    
    # Get the media root path
    media_root = settings.MEDIA_ROOT
    
    # Check if the file path contains the media root
    if media_root in file_path:
        # Extract the relative path from media root
        relative_path = file_path.split(media_root)[-1]
        # Remove leading slash if present
        if relative_path.startswith('/'):
            relative_path = relative_path[1:]
        
        return f"{settings.BE_BASE_URL}/media/{relative_path}"
    else:
        # Fallback: try to extract filename and construct path
        filename = os.path.basename(file_path)
        return f"{settings.BE_BASE_URL}/media/documents/{filename}" 