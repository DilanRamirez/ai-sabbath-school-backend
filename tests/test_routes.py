import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    # Stub out the LLM call to prevent external API requests
    def fake_generate_llm_response(text, mode, context=None, lang="es"):
        return {"stub": True, "mode": mode, "text": text}

    monkeypatch.setattr(
        "app.services.llm_service.generate_llm_response", fake_generate_llm_response
    )


client = TestClient(app)


# ---- LLM Prompts ----
def test_llm_explain_valid(client):
    res = client.post(
        # spell-checker: disable-line
        "/api/v1/llm?lang=en",
        json={"text": "Isaías 53:5", "mode": "explain"},
    )
    assert res.status_code == 200
    assert "result" in res.json()
    assert isinstance(res.json()["result"], dict)


def test_llm_invalid_mode(client):
    res = client.post(
        "/api/v1/llm?lang=en", json={"text": "Something", "mode": "nonsense"}
    )
    assert res.status_code == 422  # FastAPI validation fails


def test_llm_missing_fields(client):
    res = client.post("/api/v1/llm", json={})
    assert res.status_code == 422
