import os
from stockfish import Stockfish

_stockfish = None
def get_stockfish() -> Stockfish | None:
    """
    Lazy singleton. Returns None if Stockfish binary not found 
    so the app degrades gracefully without it.
    """

    global _stockfish
    if _stockfish is not None:
        return _stockfish

    binary_path = os.getenv(
        "STOCKFISH_PATH",
        os.path.join(os.path.dirname(__file__), "../../engines/stockfish.exe")
    )

    if not os.path.exists(binary_path):
        print(f"WARNING: Stockfish binary not found at {binary_path}")
        return None
    
    try:
        _stockfish = Stockfish(
            path=binary_path,
            depth=15,           # how many moves ahead to calculate
            parameters={
                "Threads": 2,
                "Minimum Thinking Time": 30,
                "Skill Level": 20   # max strength
            }
        )
        return _stockfish
    except Exception as e:
        print(f"WARNING: Stockfish failed to initialise: {e}")
        return None
    
def evaluate_position(fen: str) -> dict:
    """
    Returns evaluation score and best move for a given FEN.
    Score is in centipawns from white's perspective:
      +100 = white is up ~1 pawn
      -300 = black is up ~3 pawns
    """
    sf = get_stockfish()
    if not sf:
        return {"score": None, "best_move": None, "mate_in": None}

    try:
        sf.set_fen_position(fen)
        evaluation = sf.get_evaluation()
        best_move = sf.get_best_move()

        score = None
        mate_in = None

        if evaluation["type"] == "cp":
            score = evaluation["value"]   # centipawns
        elif evaluation["type"] == "mate":
            mate_in = evaluation["value"]  # mate in N moves

        return {
            "score": score,
            "best_move": best_move,
            "mate_in": mate_in
        }
    except Exception as e:
        print(f"Stockfish evaluation error: {e}")
        return {"score": None, "best_move": None, "mate_in": None}

def classify_move(score_before: int | None, score_after: int | None, 
                  is_white_move: bool) -> str:
    """
    Classify move quality based on centipawn loss.
    Scores are always from white's perspective, so we
    flip the delta for black moves.
    """
    if score_before is None or score_after is None:
        return "played"

    # Delta from the moving player's perspective
    if is_white_move:
        delta = score_after - score_before  # positive = improvement for white
    else:
        delta = score_before - score_after  # positive = improvement for black

    if delta >= 50:
        return "brilliant"
    elif delta >= 0:
        return "good"
    elif delta >= -50:
        return "inaccuracy"
    elif delta >= -150:
        return "mistake"
    else:
        return "blunder"

def centipawns_to_display(score: int | None, mate_in: int | None) -> str:
    """Convert raw engine score to human-readable string."""
    if mate_in is not None:
        if mate_in > 0:
            return f"Mate in {mate_in}"
        else:
            return f"Mate in {abs(mate_in)} (for opponent)"
    if score is None:
        return "unknown"
    pawns = score / 100
    if pawns > 0:
        return f"+{pawns:.1f}"
    return f"{pawns:.1f}"    