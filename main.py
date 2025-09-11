import logging
import os
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional
from apps.auth.routes import router as auth_router
from apps.profile.routes import router as profile_router
from apps.chat.routes import chat_router, document_router
from apps.admin_panel.routes import admin_router
from apps.core.config import settings
from apps.core.logging_config import setup_logging

# Setup logging based on environment
environment = settings.ENVIRONMENT
setup_logging(environment)

# Get logger for main application
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Lemon Health API",
    description="API for the Lemon Health mobile application",
    version="0.1.0",
    redirect_slashes=True,  # Automatically redirect /api/profile to /api/profile/
)

logger.info(f"Starting Lemon Health API in {environment} environment")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount media directory for serving static files
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

# Mount the static directory for serving the static files
app.mount("/static", StaticFiles(directory=settings.STATIC_ROOT), name="static")

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Global handler for HTTPExceptions to ensure standardized response format
    """
    # Check if the detail is already in our standardized format
    if isinstance(exc.detail, dict) and all(k in exc.detail for k in ["success", "message", "data"]):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, convert to standardized format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail) if not isinstance(exc.detail, dict) else exc.detail.get("message", "An error occurred"),
            "data": {} if not isinstance(exc.detail, dict) else exc.detail.get("data", {})
        }
    )

# Commented out: Old validation exception handler
# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     """
#     Global handler for validation errors to ensure standardized response format
#     """
#     errors = exc.errors()
#     error_messages = []
#     
#     # Extract the main error message for display
#     main_message = "Validation error"
#     
#     for error in errors:
#         msg = error.get("msg", "")
#         error_type = error.get("type", "")
#         
#         # Clean up various error message patterns
#         cleaned_msg = msg
#         print(error)
#         # Handle "Value error, " prefix (from custom validators)
#         if msg.startswith("Value error, "):
#             cleaned_msg = msg[13:]  # Remove "Value error, " (13 characters)
#         
#         # Handle "Assertion failed, " prefix
#         elif msg.startswith("Assertion failed, "):
#             cleaned_msg = msg[18:]  # Remove "Assertion failed, " (18 characters)
#         
#         # Handle field required errors
#         elif error_type == "missing" or "field required" in msg.lower():
#             field_name = error.get("loc", ["field"])[-1] if error.get("loc") else "field"
#             cleaned_msg = f"{field_name.replace('_', ' ').title()} is required"
#         
#         # Handle string length errors
#         elif "at least" in msg.lower() and "characters" in msg.lower():
#             # Extract the meaningful part about character requirements
#             if "ensure this value has at least" in msg.lower():
#                 cleaned_msg = msg.replace("ensure this value has", "Must have")
#         elif "at most" in msg.lower() and "characters" in msg.lower():
#             if "ensure this value has at most" in msg.lower():
#                 cleaned_msg = msg.replace("ensure this value has", "Must have")
#         
#         # Handle type errors
#         elif error_type.startswith("type_error"):
#             field_name = error.get("loc", ["field"])[-1] if error.get("loc") else "field"
#             if error_type == "type_error.integer":
#                 cleaned_msg = f"{field_name.replace('_', ' ').title()} must be a number"
#             elif error_type == "type_error.str":
#                 cleaned_msg = f"{field_name.replace('_', ' ').title()} must be text"
#             elif error_type == "type_error.bool":
#                 cleaned_msg = f"{field_name.replace('_', ' ').title()} must be true or false"
#             elif error_type == "type_error.none.not_allowed":
#                 cleaned_msg = f"{field_name.replace('_', ' ').title()} cannot be empty"
#         
#         # Handle value errors for constraints
#         elif "ensure this value" in msg.lower():
#             cleaned_msg = msg.replace("ensure this value", "Value must")
#             
#         error_messages.append({
#             "loc": error.get("loc", []),
#             "msg": cleaned_msg,
#             "type": error.get("type", "")
#         })
#     
#     # Use the first error's cleaned message as the main message
#     if error_messages and error_messages[0]["msg"]:
#         main_message = error_messages[0]["msg"]
#     logger.error(f"Validation error: {main_message}")
#     return JSONResponse(
#         status_code=422,
#         content={
#             "success": False,
#             "message": main_message,
#             "data": {"errors": error_messages}
#         }
#     )

# Updated: New validation exception handler that uses message keywords from database
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Global handler for validation errors to ensure standardized response format.
    Maps Pydantic validation errors to message keywords and fetches translations from database
    """
    from apps.auth.services import AuthService
    from apps.core.db import get_db
    from contextlib import asynccontextmanager
    
    # Extract language from request headers
    language = request.headers.get("App-Language", "en")
    if language not in ["en", "es"]:
        language = "en"
    
    errors = exc.errors()
    error_messages = []
    
    # Extract the main error message for display
    main_message_keyword = "validation_error"
    
    # Get database session
    async for db in get_db():
        for error in errors:
            msg = error.get("msg", "")
            error_type = error.get("type", "")
            field_name = error.get("loc", ["field"])[-1] if error.get("loc") else "field"
            
            # Clean up various error message patterns
            message_keyword = msg
            print(error)
            
            # Handle "Value error, " prefix (from custom validators)
            if msg.startswith("Value error, "):
                # Extract the keyword from the custom validator
                keyword = msg[13:]  # Remove "Value error, " (13 characters)
                # If it looks like a keyword (contains underscore, no spaces), keep it as is
                if "_" in keyword and " " not in keyword:
                    message_keyword = keyword
                else:
                    message_keyword = keyword
            
            # Handle "Assertion failed, " prefix
            elif msg.startswith("Assertion failed, "):
                message_keyword = msg[18:]  # Remove "Assertion failed, " (18 characters)
            
            # Handle field required errors
            elif error_type == "missing" or "field required" in msg.lower():
                message_keyword = "field_required"
            
            # Handle string length errors for mobile_number specifically
            elif error_type == "string_too_short" and field_name == "mobile_number":
                message_keyword = "mobile_number_count_error"
            elif error_type == "string_too_long" and field_name == "mobile_number":
                message_keyword = "mobile_number_count_error"
            
            # Handle string length errors for password fields
            elif error_type == "string_too_short" and field_name in ["password", "new_password", "current_password"]:
                message_keyword = "password_count_error"
            elif error_type == "string_too_long" and field_name in ["password", "new_password", "current_password"]:
                message_keyword = "password_count_error"
            
            # Handle string length errors for name fields
            elif error_type == "string_too_short" and field_name in ["first_name", "last_name"]:
                message_keyword = "name_too_short"
            elif error_type == "string_too_long" and field_name in ["first_name", "last_name"]:
                message_keyword = "name_too_long"
            
            # Handle string length errors for country_code
            elif error_type == "string_too_short" and field_name == "country_code":
                message_keyword = "country_code_specification_error"
            elif error_type == "string_too_long" and field_name == "country_code":
                message_keyword = "country_code_specification_error"
            
            # Handle string length errors for verification code
            elif error_type == "string_too_short" and field_name == "code":
                message_keyword = "verification_code_invalid"
            elif error_type == "string_too_long" and field_name == "code":
                message_keyword = "verification_code_invalid"
            
            # Handle generic string length errors
            elif error_type == "string_too_short":
                message_keyword = "string_too_short"
            elif error_type == "string_too_long":
                message_keyword = "string_too_long"
            
            # Handle type errors
            elif error_type.startswith("type_error"):
                if error_type == "type_error.integer":
                    message_keyword = "integer_parsing_error"
                elif error_type == "type_error.float":
                    message_keyword = "float_parsing_error"
                elif error_type == "type_error.str":
                    message_keyword = "type_error"
                elif error_type == "type_error.bool":
                    message_keyword = "boolean_parsing_error"
                elif error_type == "type_error.none.not_allowed":
                    message_keyword = "field_required"
                else:
                    message_keyword = "type_error"
            
            # Handle regex/pattern validation errors
            elif error_type == "string_pattern_mismatch":
                if field_name == "country_code":
                    message_keyword = "country_code_specification_error"
                elif field_name == "code":
                    message_keyword = "verification_code_invalid"
                else:
                    message_keyword = "pattern_mismatch"
            
            # Handle email validation errors
            elif error_type == "value_error.email":
                message_keyword = "email_format_invalid"
            
            # Handle enum validation errors
            elif error_type == "type_error.enum":
                message_keyword = "invalid_choice"
            
            # Handle value errors for constraints
            elif "ensure this value" in msg.lower():
                message_keyword = "value_error"
            
            # Default to value_error for any unhandled cases
            else:
                message_keyword = "value_error"
            
            # Get the actual translated message using the keyword from database
            translated_message = await AuthService.get_translation_by_keyword(db, message_keyword, language)
            
            # Fallback to JSON file if not found in database
            if not translated_message:
                translated_message = AuthService.get_message_from_json(message_keyword, language)
                
            error_messages.append({
                "loc": error.get("loc", []),
                "msg": translated_message,
                "type": error.get("type", "")
            })
        
        # Use the first error's message as the main message
        if error_messages and error_messages[0]["msg"]:
            main_message = error_messages[0]["msg"]
        else:
            # Get the translated message for validation_error from database
            main_message = await AuthService.get_translation_by_keyword(db, main_message_keyword, language)
            if not main_message:
                main_message = AuthService.get_message_from_json(main_message_keyword, language)
        
        break  # Exit the async for loop after processing
    
    logger.error(f"Validation error: {main_message}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": main_message,
            "data": {"errors": error_messages}
        }
    )

# Include API routes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile_router, prefix="/api/profile", tags=["User Profile"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(document_router, prefix="/api/documents", tags=["Documents"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])

@app.get("/", tags=["Health Check"])
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "message": "API is healthy and running",
        "data": {
            "status": "healthy",
            "app": "Lemon Health API",
            "version": "0.1.0"
        }
    }

@app.get("/privacy-policy", response_class=HTMLResponse, tags=["Legal"])
async def privacy_policy():
    """Serve the privacy policy HTML page"""
    try:
        with open(os.path.join(settings.STATIC_ROOT, "legal", "privacy-policy-en.html"), "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Privacy policy not found")

@app.get("/terms-conditions", response_class=HTMLResponse, tags=["Legal"])
async def terms_conditions():
    """Serve the terms & conditions HTML page"""
    try:
        with open(os.path.join(settings.STATIC_ROOT, "legal", "terms-conditions-en.html"), "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Terms & conditions not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)