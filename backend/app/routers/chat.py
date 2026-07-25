import os
import uuid
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.database import get_db
from app.services.ai_service import get_coaching_response, get_move_analysis
from app.services.session_service import (
    get_or_create_session, check_session_budget,
    increment_session_usage, save_move, save_message
)
from app.services.cache import check_global_budget
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

    global_ok, _ = check_global_budget()
    if not global_ok:
        raise HTTPException(
            status_code=429,
            detail="Daily coaching limit reached. Please try again tomorrow."
        )

    try:
        game_session = get_or_create_session(db, body.session_id)
        has_budget, calls_remaining = check_session_budget(db, game_session.id)
        if not has_budget:
            raise HTTPException(
                status_code=429,
                detail=f"Session limit reached. Click 'New game' to start a fresh session."
            )
    except OperationalError:
        fallback_session_id = body.session_id or str(uuid.uuid4())
        result = get_coaching_response(body.messages)
        result["session_id"] = fallback_session_id
        return ChatResponse(**result)

    try:
        result = get_coaching_response(body.messages)
        result["session_id"] = game_session.id

        # Persist user message and AI response
        user_msg = body.messages[-1]
        save_message(db, game_session.id, "user", user_msg.content)
        save_message(db, game_session.id, "assistant",
                     result["reply"], result["label"], result["tokens_used"])
        increment_session_usage(db, game_session.id, result["tokens_used"])

        _, remaining_after = check_session_budget(db, game_session.id)

        return ChatResponse(
            reply=result["reply"],
            label=result["label"],
            tokens_used=result["tokens_used"],
            session_id=game_session.id,
            calls_remaining=remaining_after
        )
    except OperationalError:
        fallback_session_id = body.session_id or str(uuid.uuid4())
        result = get_coaching_response(body.messages)
        result["session_id"] = fallback_session_id
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

    global_ok, _ = check_global_budget()
    if not global_ok:
        raise HTTPException(
            status_code=429,
            detail="Daily coaching limit reached. Please try again tomorrow."
        )

    try:
        game_session = get_or_create_session(db, body.session_id)
        has_budget, calls_remaining = check_session_budget(db, game_session.id)
        if not has_budget:
            raise HTTPException(
                status_code=429,
                detail="Session limit reached. Click 'New game' to start a fresh session."
            )
    except OperationalError:
        fallback_session_id = body.session_id or str(uuid.uuid4())
        result = get_move_analysis(
            body.san, body.from_sq, body.to_sq,
            body.fen_before, body.fen_after,
            body.move_number
        )
        return MoveAnalysisResponse(
            commentary=result["commentary"],
            tokens_used=result["tokens_used"],
            session_id=fallback_session_id,
            move_quality=result.get("move_quality", "played"),
            score_display=result.get("score_display", ""),
            calls_remaining=50
        )

    try:
        result = get_move_analysis(
            body.san, body.from_sq, body.to_sq,
            body.fen_before, body.fen_after,
            body.move_number
        )

        if body.move_number:
            save_move(db, game_session.id, body.move_number,
                      body.san, body.from_sq, body.to_sq, body.fen_after)

        increment_session_usage(db, game_session.id, result["tokens_used"])
        _, remaining_after = check_session_budget(db, game_session.id)

        return MoveAnalysisResponse(
            commentary=result["commentary"],
            tokens_used=result["tokens_used"],
            session_id=game_session.id,
            move_quality=result.get("move_quality", "played"),
            score_display=result.get("score_display", ""),
            calls_remaining=remaining_after
        )
    except OperationalError:
        fallback_session_id = body.session_id or str(uuid.uuid4())
        result = get_move_analysis(
            body.san, body.from_sq, body.to_sq,
            body.fen_before, body.fen_after,
            body.move_number
        )
        return MoveAnalysisResponse(
            commentary=result["commentary"],
            tokens_used=result["tokens_used"],
            session_id=fallback_session_id,
            move_quality=result.get("move_quality", "played"),
            score_display=result.get("score_display", "")
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/session/{session_id}/budget")
async def get_session_budget(session_id: str, db: Session = Depends(get_db)):
    """Frontend calls this on load to restore session state."""
    has_budget, calls_remaining = check_session_budget(db, session_id)
    return {
        "session_id": session_id,
        "calls_remaining": calls_remaining,
        "has_budget": has_budget
    }

@router.get("/health")
async def health_check():
    return {"status": "ok", "model": "claude-sonnet-4-6"}