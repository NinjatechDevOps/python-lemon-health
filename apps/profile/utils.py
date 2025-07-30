from datetime import datetime
from typing import Optional, Tuple

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
    print(f"DEBUG - Raw form data: date_of_birth={date_of_birth}, height={height}, height_unit={height_unit}, weight={weight}, gender={gender}")
    
    # Convert string values to appropriate types
    converted_data = {}
    errors = []
    
    # Convert date_of_birth string to date object
    if date_of_birth:
        try:
            # Parse the date string to datetime.date object
            parsed_date = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            converted_data["date_of_birth"] = parsed_date
            print(f"DEBUG - Converted date_of_birth: {parsed_date}")
        except ValueError as e:
            error_msg = f"Invalid date format: {date_of_birth}. Expected YYYY-MM-DD"
            print(f"DEBUG - Date conversion failed: {error_msg}")
            errors.append(error_msg)
    
    # Convert height string to float
    if height:
        try:
            height_value = float(height)
            converted_data["height"] = height_value
            print(f"DEBUG - Converted height: {height_value}")
        except ValueError as e:
            error_msg = f"Invalid height value: {height}. Must be a number"
            print(f"DEBUG - Height conversion failed: {error_msg}")
            errors.append(error_msg)
    
    # Convert weight string to float
    if weight:
        try:
            weight_value = float(weight)
            converted_data["weight"] = weight_value
            print(f"DEBUG - Converted weight: {weight_value}")
        except ValueError as e:
            error_msg = f"Invalid weight value: {weight}. Must be a number"
            print(f"DEBUG - Weight conversion failed: {error_msg}")
            errors.append(error_msg)
    
    # String fields that don't need conversion
    if height_unit:
        converted_data["height_unit"] = height_unit
        print(f"DEBUG - Height unit: {height_unit}")
    
    if gender:
        converted_data["gender"] = gender
        print(f"DEBUG - Gender: {gender}")
    
    print(f"DEBUG - Final converted data: {converted_data}")
    
    # Return error if any validation failed
    if errors:
        error_message = "; ".join(errors)
        return ProfileUpdate(**converted_data), error_message
    
    return ProfileUpdate(**converted_data), None 