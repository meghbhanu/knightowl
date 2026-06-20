import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    final_fen = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, completed, abandoned

    moves = relationship("Move", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class Move(Base):
    __tablename__ = "moves"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("game_sessions.id"), nullable=False)
    move_number = Column(Integer, nullable=False)
    san = Column(String(10), nullable=False)   # e.g. "Nf3"
    from_square = Column(String(2), nullable=False)  # e.g. "g1"
    to_square = Column(String(2), nullable=False)    # e.g. "f3"
    fen_after = Column(Text, nullable=False)
    played_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("GameSession", back_populates="moves")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("game_sessions.id"), nullable=False)
    role = Column(String(10), nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    label = Column(String(10), nullable=True)   # CRITIQUE, PLAN, OPENING, TIP
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("GameSession", back_populates="messages")