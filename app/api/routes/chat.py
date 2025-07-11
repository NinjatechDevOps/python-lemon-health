from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()

@router.post("/")
async def send_message():
    """Send a message to the chatbot"""
    return {"message": "Chat message endpoint"}

@router.get("/history")
async def get_chat_history():
    """Get chat history"""
    return {"message": "Chat history endpoint"}