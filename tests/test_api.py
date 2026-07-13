import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path so we can import dashboard and engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.app import app

client = TestClient(app)

def test_read_main():
    """Test if the main dashboard page loads successfully with 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Divine" in response.text
    assert "text/html" in response.headers["content-type"]

def test_api_health():
    """Test if the health check endpoint or mock is accessible."""
    # We do not have a dedicated /api/health endpoint in FastAPI right now,
    # the frontend handles it via models.json. But we can test if the UI serves properly.
    response = client.get("/")
    assert response.status_code == 200

def test_models_json():
    """Test if models.json is readable and valid."""
    import json
    models_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models.json")
    if os.path.exists(models_path):
        with open(models_path, "r") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        if "Groq" in data:
            assert isinstance(data["Groq"], list)

def test_chat_endpoint_mocked(mocker):
    """Test the /api/chat endpoint using a mocked engine to avoid API calls."""
    # Mock the engine.chat method so we don't actually hit external APIs in CI/CD
    mock_chat = mocker.patch("dashboard.app.engine.chat")
    
    # Define what the mocked engine should return
    mock_chat.return_value = {
        "success": True,
        "content": "Mocked response from Divine Engine",
        "model": "mock-model-7b",
        "provider": "MockProvider",
        "failover_occurred": False,
        "original_provider": None,
        "usage": {"total_tokens": 100}
    }

    payload = {
        "provider": "Groq",
        "model": "llama3-8b-8192",
        "prompt": "Hello Divine!",
        "history": [{"role": "user", "content": "Hello Divine!"}]
    }

    response = client.post("/api/chat", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["reply"] == "Mocked response from Divine Engine"
    assert data["model_used"] == "mock-model-7b"
