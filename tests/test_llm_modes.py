import pytest
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


@pytest.mark.parametrize("mode", ["explain", "reflect", "apply", "summarize", "ask"])
def test_llm_modes_valid(mode):
    response = client.post(
        f"/api/v1/llm?lang=es",
        json={
            "text": "¿Qué significa tener fe en medio de la prueba?",
            "mode": mode,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert isinstance(data["result"], dict)
    assert len(data["result"]) > 0


def test_llm_mode_ask_custom_question():
    response = client.post(
        f"/api/v1/llm?lang=es",
        json={
            "text": "¿Cuál es el mensaje principal del libro de Apocalipsis?",
            "mode": "ask",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert isinstance(data["result"], dict)
    assert len(data["result"]) > 0


def test_llm_missing_text():
    response = client.post("/api/v1/llm", json={"mode": "reflect"})
    assert response.status_code == 422


def test_llm_invalid_mode():
    response = client.post(
        "/api/v1/llm",
        json={"text": "Este es un texto de prueba", "mode": "meditate"},
    )
    assert response.status_code == 422


def test_llm_empty_text():
    response = client.post("/api/v1/llm", json={"text": "   ", "mode": "apply"})
    assert response.status_code in [400, 422]
