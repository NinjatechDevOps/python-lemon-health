from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()

@router.get("/me")
async def get_profile_me():
    """Get current user profile"""
    return {"message": "Get profile endpoint"}

@router.put("/me")
async def update_profile_me():
    """Update user profile"""
    return {"message": "Update profile endpoint"}