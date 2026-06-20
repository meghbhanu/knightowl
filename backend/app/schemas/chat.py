from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Message(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(..., max_length=2000) #input validation for message content length

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., max_items=10)
    session_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    label: Literal["CRITIQUE", "PLAN", "OPENING", "TIP"]
    tokens_used: int
    session_id: str

class MoveAnalysisRequest(BaseModel):
    san: str
    from_sq: str
    to_sq: str
    fen: str
    session_id: Optional[str] = None
    move_number: Optional[int] = None

class MoveAnalysisResponse(BaseModel):
    commentary: str
    tokens_used: int    
    session_id: str