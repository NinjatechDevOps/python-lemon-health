import logging
from datetime import datetime
from typing import Optional, Tuple
from apps.core.config import settings
from apps.core.logging_config import get_logger
from pydantic import ValidationError

logger = get_logger(__name__)

def api_response(success: bool, message: str, data: dict = None):
    return {
        "success": success,
        "message": message,
        "data": data or {}
    }

def api_error_response(message: str, status_code: int = 400, data: dict = None):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "data": data or {}
        }
    )

def convert_form_data_to_profile_update(
    date_of_birth: Optional[str] = None,
    height: Optional[str] = None,
    height_unit: Optional[str] = None,
    weight: Optional[str] = None,
    gender: Optional[str] = None
) -> Tuple[object, Optional[str]]:
    """
    Convert form data strings to ProfileUpdate object with proper type conversion
    Returns: (ProfileUpdate object, error_message or None)
    """
    from apps.profile.schemas import ProfileUpdate
    
    # Debug logging
    logger.debug(f"Raw form data: date_of_birth={date_of_birth}, height={height}, height_unit={height_unit}, weight={weight}, gender={gender}")
    
    # Convert string values to appropriate types
    converted_data = {}
    errors = []
    
    # Convert date_of_birth string to date object
    if date_of_birth:
        try:
            # Parse the date string to datetime.date object
            parsed_date = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            converted_data["date_of_birth"] = parsed_date
            logger.debug(f"Converted date_of_birth: {parsed_date}")
        except ValueError as e:
            error_msg = f"Invalid date format: {date_of_birth}. Expected YYYY-MM-DD"
            logger.error(f"Date conversion failed: {error_msg}")
            errors.append(error_msg)
    
    # Convert height string to float
    if height:
        try:
            height_value = float(height)
            converted_data["height"] = height_value
            logger.debug(f"Converted height: {height_value}")
        except ValueError as e:
            error_msg = f"Invalid height value: {height}. Must be a number"
            logger.error(f"Height conversion failed: {error_msg}")
            errors.append(error_msg)
    
    # Convert weight string to float
    if weight:
        try:
            weight_value = float(weight)
            converted_data["weight"] = weight_value
            logger.debug(f"Converted weight: {weight_value}")
        except ValueError as e:
            error_msg = f"Invalid weight value: {weight}. Must be a number"
            logger.error(f"Weight conversion failed: {error_msg}")
            errors.append(error_msg)
    
    # String fields that don't need conversion
    if height_unit:
        converted_data["height_unit"] = height_unit
        logger.debug(f"Height unit: {height_unit}")
    
    if gender:
        converted_data["gender"] = gender
        logger.debug(f"Gender: {gender}")
    
    logger.debug(f"Final converted data: {converted_data}")
    
    # Return error if any validation failed
    if errors:
        error_message = "; ".join(errors)
        # Commented out: This was creating ProfileUpdate even with errors
        # return ProfileUpdate(**converted_data), error_message
        
        # Updated: Return None for profile_data when there are conversion errors
        return None, error_message
    
    # Updated: Wrap ProfileUpdate creation in try-catch to handle validation errors
    try:
        profile_update = ProfileUpdate(**converted_data)
        return profile_update, None
    except ValidationError as e:
        logger.error(f"ProfileUpdate validation failed: {e}")
        # Commented out: Full validation error with technical details
        # return None, str(e)
        
        # Updated: Extract only the meaningful error message
        # Get the first error's message from the validation errors
        first_error = e.errors()[0]
        if 'ctx' in first_error and 'error' in first_error['ctx']:
            # For custom validators that use ValueError
            error_msg = str(first_error['ctx']['error'])
            # Remove "ValueError: " prefix if present
            if error_msg.startswith("ValueError: "):
                error_msg = error_msg.replace("ValueError: ", "")
            return None, error_msg
        elif 'msg' in first_error:
            # For standard Pydantic errors
            return None, first_error['msg']
        else:
            # Fallback to simple error message
            return None, "Validation error: Please check your input values" 




def convert_relative_to_complete_url(relative_url: Optional[str]) -> Optional[str]:
    """
    Convert relative profile picture URL to complete URL using BE_BASE_URL
    
    Args:
        relative_url: Relative URL like "/media/profile_pictures/filename.jpg"
        
    Returns:
        Complete URL like "http://localhost:8000/media/profile_pictures/filename.jpg"
        or default image URL if relative_url is None
    """
    if not relative_url:
        # Return default profile image URL
        default_image = settings.DEFAULT_PROFILE_IMAGE
        if default_image.startswith('/'):
            default_image = default_image[1:]
        return f"{settings.BE_BASE_URL}/{default_image}"
    
    # Remove leading slash if present to avoid double slashes
    if relative_url.startswith('/'):
        relative_url = relative_url[1:]
    
    return f"{settings.BE_BASE_URL}/{relative_url}"