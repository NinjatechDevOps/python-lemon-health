from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()

@router.get("/me")
async def get_user_me():
    """Get current user information"""
    return {"message": "Current user endpoint"}

@router.put("/me")
async def update_user_me():
    """Update current user information"""
    return {"message": "Update user endpoint"}