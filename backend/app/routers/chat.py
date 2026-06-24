import os
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app.services.ai_service import get_coaching_response, get_move_analysis
from app.services.session_service import get_or_create_session, save_move, save_message
from app.schemas.chat import ChatRequest, ChatResponse, MoveAnalysisRequest, MoveAnalysisResponse

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["chat"])

MAX_CALLS = int(os.getenv("MAX_CALLS_PER_MINUTE", 20))

@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{MAX_CALLS}/minute")
async def chat(request: Request, body: ChatRequest, db: Session = Depends(get_db)):
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
        game_session = get_or_create_session(db, body.session_id)
        result = get_coaching_response(body.messages)
        result["session_id"] = game_session.id

        # Persist user message and AI response
        user_msg = body.messages[-1]
        save_message(db, game_session.id, "user", user_msg.content)
        save_message(db, game_session.id, "assistant",
                     result["reply"], result["label"], result["tokens_used"])

        return ChatResponse(**result)
    except Exception as e:
        # Never expose the raw Anthropic error (it may contain key info)
        raise HTTPException(status_code=500, detail="AI service temporarily unavailable. Please try again later.")

@router.post("/analyse", response_model=MoveAnalysisResponse)
@limiter.limit(f"{MAX_CALLS}/minute")
async def analyse_move(request: Request, body: MoveAnalysisRequest, db: Session = Depends(get_db)):
    """
    Lightweight automatic move commentary.
    Called on every move — separate from the chat endpoint.
    """
    try:
        game_session = get_or_create_session(db, body.session_id)
        result = get_move_analysis(
            body.san, body.from_sq, body.to_sq,
            body.fen_before, body.fen_after,
            body.move_number
        )

        if body.move_number:
            save_move(db, game_session.id, body.move_number,
                      body.san, body.from_sq, body.to_sq, body.fen_after)

        return MoveAnalysisResponse(
            commentary=result["commentary"],
            tokens_used=result["tokens_used"],
            session_id=game_session.id,
            move_quality=result.get("move_quality", "played"),
            score_display=result.get("score_display", "")
        )
    except Exception as e:
        import traceback
        traceback.print_exc()   
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "ok", "model": "claude-sonnet-4-6"}