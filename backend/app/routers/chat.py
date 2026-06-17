import os
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.ai_service import get_coaching_response
from app.schemas.chat import Message, ChatRequest, ChatResponse

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["chat"])

MAX_CALLS = int(os.getenv("MAX_CALLS_PER_MINUTE", 20))

@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{MAX_CALLS}/minute")
async def chat(request: Request, body: ChatRequest):
    """
    Main coaching endpoint.
    Accepts conversation history, returns AI coaching response    
    Rate limited per IP to control API spend.
    """
    if not body.messages:
        raise HTTPException(status_code=400, detail="Message history cannot be empty.")

    #Ensure last message is from user
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user.")

    try:
        result = get_coaching_response(body.messages)
        return ChatResponse(**result)
    except Exception as e:
        # Never expose the raw Anthropic error (it may contain key info)
        raise HTTPException(status_code=500, detail="AI service temporarily unavailable. Please try again later.")

@router.get("/health")
async def health_check():
    return {"status": "ok", "model": "claude-sonnet-4-6"}