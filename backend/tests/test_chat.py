import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def mock_ai_response():
    return {
        "reply": "Consider controlling the center with your pawns. What square do you want to dominate?",
        "label": "TIP",
        "tokens_used": 85,
        "session_id": "test-session-123"
    }

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_chat_endpoint_success():
    with patch("app.routers.chat.get_coaching_response", return_value=mock_ai_response()):
        response = client.post("/api/v1/chat", json={
            "messages": [{"role": "user", "content": "Is e4 a good opening move?"}]
        })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["label"] in ["CRITIQUE", "PLAN", "OPENING", "TIP"]

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