from pydantic import BaseModel, Field
from typing import List, Literal

class Message(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(..., max_length=500) #input validation for message content length

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., max_items=10)
    session_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    label: Literal["CRITIQUE", "PLAN", "OPENING", "TIP"]
    tokens_used: int
    session_id: str