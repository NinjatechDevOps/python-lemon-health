from typing import Optional
from apps.core.config import settings

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