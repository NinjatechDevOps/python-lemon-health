import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.accounts.routes import router as accounts_router
from apps.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Initialize FastAPI app
app = FastAPI(
    title="Lemon Health API",
    description="API for the Lemon Health mobile application",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(accounts_router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
# app.include_router(role_router, prefix="/api/roles", tags=["Roles"])

@app.get("/", tags=["Health Check"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "Lemon Health API",
        "version": "0.1.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)