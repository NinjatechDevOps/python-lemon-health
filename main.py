import logging
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Global handler for validation errors to ensure standardized response format
    """
    errors = exc.errors()
    error_messages = []
    
    # Extract the main error message for display
    main_message = "Validation error"
    
    for error in errors:
        msg = error.get("msg", "")
        error_type = error.get("type", "")
        
        # Clean up various error message patterns
        cleaned_msg = msg
        
        # Handle "Value error, " prefix (from custom validators)
        if msg.startswith("Value error, "):
            cleaned_msg = msg[13:]  # Remove "Value error, " (13 characters)
        
        # Handle "Assertion failed, " prefix
        elif msg.startswith("Assertion failed, "):
            cleaned_msg = msg[18:]  # Remove "Assertion failed, " (18 characters)
        
        # Handle field required errors
        elif error_type == "missing" or "field required" in msg.lower():
            field_name = error.get("loc", ["field"])[-1] if error.get("loc") else "field"
            cleaned_msg = f"{field_name.replace('_', ' ').title()} is required"
        
        # Handle string length errors
        elif "at least" in msg.lower() and "characters" in msg.lower():
            # Extract the meaningful part about character requirements
            if "ensure this value has at least" in msg.lower():
                cleaned_msg = msg.replace("ensure this value has", "Must have")
        elif "at most" in msg.lower() and "characters" in msg.lower():
            if "ensure this value has at most" in msg.lower():
                cleaned_msg = msg.replace("ensure this value has", "Must have")
        
        # Handle type errors
        elif error_type.startswith("type_error"):
            field_name = error.get("loc", ["field"])[-1] if error.get("loc") else "field"
            if error_type == "type_error.integer":
                cleaned_msg = f"{field_name.replace('_', ' ').title()} must be a number"
            elif error_type == "type_error.str":
                cleaned_msg = f"{field_name.replace('_', ' ').title()} must be text"
            elif error_type == "type_error.bool":
                cleaned_msg = f"{field_name.replace('_', ' ').title()} must be true or false"
            elif error_type == "type_error.none.not_allowed":
                cleaned_msg = f"{field_name.replace('_', ' ').title()} cannot be empty"
        
        # Handle value errors for constraints
        elif "ensure this value" in msg.lower():
            cleaned_msg = msg.replace("ensure this value", "Value must")
            
        error_messages.append({
            "loc": error.get("loc", []),
            "msg": cleaned_msg,
            "type": error.get("type", "")
        })
    
    # Use the first error's cleaned message as the main message
    if error_messages and error_messages[0]["msg"]:
        main_message = error_messages[0]["msg"]
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

# Updated: Adding direct routes for privacy policy and terms & conditions
@app.get("/privacy-policy", response_class=HTMLResponse, tags=["Legal"])
async def privacy_policy():
    """Serve the privacy policy HTML page"""
    try:
        with open(os.path.join(settings.STATIC_ROOT, "legal", "privacy-policy.html"), "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Privacy policy not found")

@app.get("/terms-conditions", response_class=HTMLResponse, tags=["Legal"])
async def terms_conditions():
    """Serve the terms & conditions HTML page"""
    try:
        with open(os.path.join(settings.STATIC_ROOT, "legal", "terms-conditions.html"), "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Terms & conditions not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)