import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError
from app.main import app
from app.database import normalize_database_url

client = TestClient(app)

with patch('app.database.create_engine'), \
     patch('app.database.SessionLocal'), \
     patch('app.redis_client.get_redis'):
    from app.main import app

def mock_ai_response():
    return {
        "reply": "Consider controlling the center with your pawns. What square do you want to dominate?",
        "label": "TIP",
        "tokens_used": 85,
        "session_id": "test-session-123",
        "from_cache": False
    }

def mock_analysis_response():
    return {
        "commentary": "Good developing move, controlling the center.",
        "tokens_used": 60,
        "move_quality": "good",
        "score_display": "+0.3"
    }

def test_normalize_database_url_rewrites_local_postgres_host():
    original = "postgresql://knightowl:knightowl_dev@postgres:5432/knightowl"
    with patch.dict("os.environ", {"DOCKER_CONTAINER": "0"}, clear=False):
        normalized = normalize_database_url(original)
    assert normalized == "postgresql://knightowl:knightowl_dev@localhost:5432/knightowl"

def test_analyse_handles_missing_database():
    with patch("app.routers.chat.get_or_create_session", side_effect=OperationalError("stmt", None, Exception("db down"))), \
         patch("app.routers.chat.get_move_analysis", return_value={"commentary": "test", "tokens_used": 1}):
        response = client.post("/api/v1/analyse", json={
            "san": "Nf3",
            "from_sq": "g1",
            "to_sq": "f3",
            "fen_before": "start",
            "fen_after": "end",
            "move_number": 1,
            "session_id": None
        })
    assert response.status_code == 200
    data = response.json()
    assert data["commentary"] == "test"
    assert data["session_id"] is not None


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_chat_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200

def test_chat_success():
    with patch("app.routers.chat.get_coaching_response",
               return_value=mock_coaching_response()), \
         patch("app.routers.chat.get_or_create_session",
               return_value=MagicMock(id="test-session-123")), \
         patch("app.routers.chat.save_message"):
        response = client.post("/api/v1/chat", json={
            "messages": [{"role": "user", "content": "Is e4 a good opening?"}]
        })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["label"] in ["CRITIQUE", "PLAN", "OPENING", "TIP"]

def test_analyse_success():
    with patch("app.routers.chat.get_move_analysis",
               return_value=mock_analysis_response()), \
         patch("app.routers.chat.get_or_create_session",
               return_value=MagicMock(id="test-session-123")), \
         patch("app.routers.chat.save_move"):
        response = client.post("/api/v1/analyse", json={
            "san": "e4",
            "from_sq": "e2",
            "to_sq": "e4",
            "fen_before": "rnbqkbnr/pppppppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",
            "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            "move_number": 1
        })
    assert response.status_code == 200
    data = response.json()
    assert "commentary" in data
    assert "move_quality" in data

def test_chat_rejects_empty_messages():
    response = client.post("/api/v1/chat", json={"messages": []})
    assert response.status_code == 400

def test_chat_rejects_non_user_last_message():
    response = client.post("/api/v1/chat", json={
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
    })
    assert response.status_code == 400

def test_trim_history():
    from app.services.ai_service import trim_history
    from app.schemas.chat import Message
    
    msgs = [Message(role="user" if i % 2 == 0 else "assistant", content=f"msg {i}") 
            for i in range(10)]
    trimmed = trim_history(msgs)
    assert len(trimmed) <= 6