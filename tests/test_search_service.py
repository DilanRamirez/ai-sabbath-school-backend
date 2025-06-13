import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ping_status():
    # Use context manager so lifespan events fire (preload_index_and_metadata)
    with TestClient(app) as client:
        res = client.get("/api/v1/ping")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "ok"
        assert data["faiss_index_loaded"] is True
        assert data["metadata_loaded"] is True


def test_search_valid_query_returns_results():
    with TestClient(app) as client:
        response = client.get("/api/v1/search?q=gospel")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert "query" in data
        assert data["query"] == "gospel"
        assert all("score" in r and "normalized_score" in r for r in data["results"])


def test_search_empty_query():
    response = client.get("/api/v1/search?q=")
    assert response.status_code == 422  # FastAPI will validate missing required query


def test_search_invalid_type_filter():
    response = client.get("/api/v1/search?q=esperanza&type=invalid")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_search_top_k_too_high():
    response = client.get("/api/v1/search?q=fe&top_k=100")
    assert response.status_code == 422  # max is 20 as per route definition


def test_search_top_k_too_low():
    response = client.get("/api/v1/search?q=fe&top_k=0")
    assert response.status_code == 422  # min is 1 as per route definition


def test_search_with_type_lesson():
    response = client.get("/api/v1/search?q=gracia&type=lesson")
    assert response.status_code == 200
    data = response.json()
    assert all(
        r.get("type") == "lesson" or r.get("type") == "lesson-section"
        for r in data["results"]
    )


def test_search_with_type_book():
    response = client.get("/api/v1/search?q=vida&type=book")
    assert response.status_code == 200
    data = response.json()
    assert all(
        r.get("type") == "book" or r.get("type") == "book-section"
        for r in data["results"]
    )


# Additional edge case tests
def test_search_missing_query_param():
    # No 'q' parameter should yield a validation error (422)
    response = client.get("/api/v1/search")
    assert response.status_code == 422


def test_search_invalid_top_k_boundary_low():
    # top_k below minimum should 422
    response = client.get("/api/v1/search?q=test&top_k=0")
    assert response.status_code == 422


def test_search_invalid_top_k_boundary_high():
    # top_k above maximum (21) should 422
    response = client.get("/api/v1/search?q=test&top_k=21")
    assert response.status_code == 422


def test_search_invalid_type_fallback():
    # invalid type should fallback to 'all' and return results
    with TestClient(app) as client:
        response = client.get("/api/v1/search?q=test&type=notatype")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("results"), list)
        # should still include some results (if index has items)
        assert "results" in data


def test_search_index_not_loaded(monkeypatch):
    # Simulate the FAISS index not loaded in memory
    from app.indexing.search_service import IndexStore

    monkeypatch.setattr(IndexStore, "index", None)
    monkeypatch.setattr(IndexStore, "metadata", [])
    response = client.get("/api/v1/search?q=test")
    # When index is None, route returns a result list containing an error entry
    assert response.status_code == 200
    data = response.json()
    assert "results" in data and isinstance(data["results"], list)
    # Expect at least one result with an 'error' key indicating load failure
    assert any("error" in item for item in data["results"])


def test_search_empty_results():
    # FAISS always returns top_k nearest neighbors, even for nonsense queries
    with TestClient(app) as client:
        response = client.get("/api/v1/search?q=asdjflkjashdflkjashdf")
        assert response.status_code == 200
        data = response.json()
        # Default top_k is 5
        assert data.get("count") == 5
        results = data.get("results")
        assert isinstance(results, list) and len(results) == 5


def test_llm_missing_mode_field():
    # Omit the 'mode' field entirely
    response = client.post(
        "/api/v1/llm?lang=es",
        json={"text": "¿Qué significa la fe?"},
    )
    assert response.status_code == 422


def test_llm_invalid_lang_fallback():
    # Pass unsupported lang; should default to English or at least work
    response = client.post(
        "/api/v1/llm?lang=fr",
        json={"text": "test", "mode": "explain"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data


def test_llm_long_text():
    # Very long input should still be handled
    long_text = "a" * 10000
    response = client.post(
        "/api/v1/llm?lang=en",
        json={"text": long_text, "mode": "summarize"},
    )
    assert response.status_code == 200
    assert isinstance(response.json().get("result"), dict)
