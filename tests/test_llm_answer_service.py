import pytest
from fastapi.testclient import TestClient
from app.main import app


# def test_llm_answer_valid_input():
#     with TestClient(app) as client:
#         response = client.post(
#             "/api/v1/llm/answer",
#             json={
#                 "question": "¿Qué significa la fe?",
#                 "top_k": 3,
#                 "lang": "es",
#                 "mode": "explain",
#             },
#         )
#         assert response.status_code == 200
#         data = response.json()
#         assert "answer" in data
#         assert "context_used" in data
#         assert data["context_used"] > 0


def test_llm_answer_empty_question():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/llm/answer", json={"question": "  ", "top_k": 3, "lang": "es"}
        )
        assert response.status_code == 400
        assert "detail" in response.json()


def test_llm_answer_invalid_top_k():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/llm/answer",
            json={"question": "¿Qué es la fe?", "top_k": 0, "lang": "es"},
        )
        assert response.status_code == 422  # top_k must be >= 1

        response = client.post(
            "/api/v1/llm/answer",
            json={"question": "¿Qué es la fe?", "top_k": -1, "lang": "es"},
        )
        assert response.status_code == 422  # top_k must be >= 1


def test_llm_answer_invalid_lang():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/llm/answer",
            json={"question": "¿Qué es el evangelio?", "top_k": 3, "lang": "fr"},
        )
        assert response.status_code == 422  # lang must be 'en' or 'es'


def test_llm_answer_no_relevant_context():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/llm/answer",
            json={
                "question": "¿Cuál es el número atómico del Uranio?",
                "top_k": 3,
                "lang": "es",
            },
        )
        # 404 if no context; 200 if fallback applies
        assert response.status_code in [404, 200]
