import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_all_lessons_success():
    response = client.get("/api/v1/lessons")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_lesson_success():
    response = client.get("/api/v1/lessons/2025/Q2/lesson-08")
    assert response.status_code == 200
    data = response.json()
    assert "lesson" in data


def test_get_lesson_not_found():
    response = client.get("/api/v1/lessons/2025/Q2/nonexistent")
    assert response.status_code == 404


def test_get_lesson_metadata_success():
    response = client.get("/api/v1/lessons/2025/Q2/lesson-08/metadata")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_get_lesson_metadata_not_found():
    response = client.get("/api/v1/lessons/2025/Q2/nonexistent/metadata")
    assert response.status_code == 404


def test_get_lesson_pdf_success():
    response = client.get("/api/v1/lessons/2025/Q2/lesson-08/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_get_lesson_pdf_not_found():
    response = client.get("/api/v1/lessons/2025/Q2/nonexistent/pdf")
    assert response.status_code == 404


# Tests for malformed input (400 Bad Request)


def test_get_lesson_bad_request():
    # Malformed year
    response = client.get("/api/v1/lessons/abcd/Q2/lesson-08")
    assert response.status_code == 400 or response.status_code == 404
    # Malformed quarter
    response = client.get("/api/v1/lessons/2025/quarter2/lesson-08")
    assert response.status_code == 400 or response.status_code == 404


def test_get_lesson_metadata_bad_request():
    response = client.get("/api/v1/lessons/abcd/Q2/lesson-08/metadata")
    assert response.status_code == 400 or response.status_code == 404


def test_get_lesson_pdf_bad_request():
    response = client.get("/api/v1/lessons/2025/quarter2/lesson-08/pdf")
    assert response.status_code == 400 or response.status_code == 404
