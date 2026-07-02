import os
import re
import uuid
from anthropic import Anthropic
from app.services.prompt import get_system_prompt
from app.services.cache import get_cached_response, cache_response
from app.schemas.chat import Message
from app.services.stockfish_service import ( evaluate_position, classify_move, centipawns_to_display )

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
    client = get_client()
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
        "session_id": str(uuid.uuid4()),
        "from_cache": False
    }

def get_move_analysis(san: str, from_sq: str, to_sq: str, fen_before: str, 
                      fen_after: str, move_number: int) -> dict:
    """
    1. Evaluate position before and after the move with Stockfish
    2. Classify move quality based on centipawn change
    3. Feed engine data into Claude for one cohesive coaching response
    """
    client = get_client()

    eval_before = evaluate_position(fen_before)
    eval_after = evaluate_position(fen_after)

    is_white_move = move_number % 2 == 1
    move_quality = classify_move(
        eval_before["score"],
        eval_after["score"],
        is_white_move
        ,
        san,
        eval_before.get("best_move"),
        eval_before.get("top_moves")
    )

    score_display = centipawns_to_display(
        eval_after["score"],
        eval_after["mate_in"]
    )

    best_move = eval_before["best_move"]

    engine_context = ""
    if eval_before["score"] is not None and eval_after["score"] is not None:
        engine_context = f"""
Engine evaluation before move: {centipawns_to_display(eval_before["score"], eval_before["mate_in"])}
Engine evaluation after move:  {score_display}
Move classification:           {move_quality.upper()}
Engine's preferred move was:   {best_move or "unknown"}
"""
    elif eval_after["mate_in"] is not None:
        engine_context = f"""
Engine evaluation: {score_display}
Move classification: {move_quality.upper()}
"""
        
    prompt = f"""A chess student just played {san} (move {move_number}).
    {engine_context}
    Current position FEN: {fen_after}

    Give 3 short sentences (maximum 4) of coaching commentary. Each sentence should be concise (<= 22 words). Ensure the final sentence is complete and ends with a period. If you risk exceeding the token allowance, shorten earlier sentences so the last sentence is preserved.
    - Start with the move classification ({move_quality}) and what it means
    - Explain WHY the move is good or bad using the engine data if available
    - If it was a mistake or blunder, briefly mention what the engine preferred ({best_move}) and why
    - Name the chess concept involved (development, tactics, pawn structure, etc.)
    - Be encouraging but honest

    No labels, no questions, no markdown. Plain conversational text only."""

    cache_key_messages = [{"role": "user", "content": prompt}]
    cached = get_cached_response(cache_key_messages)
    if cached:
        cached["move_quality"] = move_quality
        cached["score_display"] = score_display
        return cached

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        system="""You are KnightOwl, a chess coach giving move commentary grounded in 
engine analysis. You have access to Stockfish evaluation data. Be direct and educational.
Plain text only — no markdown, no bullet points, no labels.""",
        messages=[{"role": "user", "content": prompt}]
    )

    commentary = response.content[0].text.strip()
    # If the model output was cut off (no terminating punctuation), ensure the final sentence ends cleanly.
    if commentary and commentary[-1] not in '.!?':
        commentary = commentary.rstrip() + '.'

    result = {
        "commentary": commentary,
        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
        "move_quality": move_quality,
        "score_display": score_display
    }

    cache_response(cache_key_messages, result)
    return result