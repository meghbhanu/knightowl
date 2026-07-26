import os
import uuid
from sqlalchemy.orm import Session
from app.models.game import GameSession, Move, ChatMessage

SESSION_CALL_LIMIT = int(os.getenv("SESSION_CALL_LIMIT", 50))

def get_or_create_session(db: Session, session_id: str | None) -> GameSession:
    """
    If session_id is provided and exists, return it.
    Otherwise create a new session.
    """
    if session_id:
        session = db.query(GameSession).filter(GameSession.id == session_id).first()
        if session:
            return session

    new_session = GameSession(id=str(uuid.uuid4()), max_api_calls=SESSION_CALL_LIMIT)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

def check_session_budget(db: Session, session_id: str) -> tuple[bool, int]:
    """
    Returns (has_budget, calls_remaining).
    has_budget = False means the session is exhausted.
    """
    session = db.query(GameSession).filter(
        GameSession.id == session_id
    ).first()
    if not session:
        return True, SESSION_CALL_LIMIT

    remaining = session.max_api_calls - session.total_api_calls
    return remaining > 0, max(0, remaining)

def increment_session_usage(db: Session, session_id: str, tokens: int):
    session = db.query(GameSession).filter(
        GameSession.id == session_id
    ).first()
    if session:
        session.total_api_calls += 1
        session.total_tokens_used += tokens
        db.commit()

def save_move(db: Session, session_id: str, move_number: int,
              san: str, from_sq: str, to_sq: str, fen_after: str) -> Move:
    move = Move(
        session_id=session_id,
        move_number=move_number,
        san=san,
        from_square=from_sq,
        to_square=to_sq,
        fen_after=fen_after
    )
    db.add(move)
    db.commit()
    return move

def save_message(db: Session, session_id: str, role: str,
                 content: str, label: str | None = None,
                 tokens_used: int | None = None) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        label=label,
        tokens_used=tokens_used
    )
    db.add(message)
    db.commit()
    return message