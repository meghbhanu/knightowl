import os
import re
import uuid
from anthropic import Anthropic
from app.services.prompt import get_system_prompt
from app.schemas.chat import Message

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_TOKENS = int(os.getenv("MAX_TOKENS_PER_RESPONSE", 400))
HISTORY_WINDOW = int(os.getenv("HISTORY_WINDOW", 6))

VALID_LABELS = {"CRITIQUE", "PLAN", "OPENING", "TIP"}

def get_client() -> Anthropic:
    """Lazy init - only called at request time, after load_doatenv() has run."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key not set.")
    return Anthropic(api_key=api_key)    

def trim_history(messages: list[Message]) -> list[Message]:
    """
    Sliding window: keep only the last HISTORY_WINDOW messages.
    Always preserve the most recent user message (it's the current question).
    This bounds our input token cost regardless of session length.
    """
    if len(messages) <= HISTORY_WINDOW:
        return messages
    return messages[-HISTORY_WINDOW:]

def parse_label(text: str) -> tuple[str, str]:
    """
    Extract the label from the model's response.
    The label must be one of the valid labels and appear at the start of the response.
    If no valid label is found, return "TIP" as a default.
    """
    match = re.match(r'^\[(CRITIQUE|PLAN|OPENING|TIP)\]\s*', text.strip())
    if match:
        label = match.group(1)
        clean = text[match.end():].strip()
        return label, clean
    return "TIP", text.strip()

def get_coaching_response(messages: list[Message]) -> dict:
    """
    Core AI proxy function.
    1. Trim history to control input tokens
    2. Call Anthropic with our locked system prompt
    3. Parse and return structured response
    """
    trimmed = trim_history(messages)

    # Convert our Pydantic models to Anthropic's expected dict format
    anthropic_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in trimmed
    ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=MAX_TOKENS,
        system=get_system_prompt(),
        messages=anthropic_messages
    )

    raw_text = response.content[0].text
    label, clean_reply = parse_label(raw_text)
    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    return {
        "reply": clean_reply,
        "label": label,
        "tokens_used": tokens_used,
        "session_id": str(uuid.uuid4())
    }