# tests/test_cms_service.py
import pytest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.cms_service import (
    load_lesson_by_path,
    load_metadata_by_path,
    get_lesson_pdf_path,
    list_all_lessons,
)

client = TestClient(app)


def test_load_lesson_success():
    lesson = load_lesson_by_path("2025", "Q2", "lesson-08")
    assert "days" in lesson
    assert "title" in lesson


def test_load_metadata_success():
    metadata = load_metadata_by_path("2025", "Q2", "lesson-08")
    assert "title" in metadata


def test_list_all_lessons_returns_list():
    lessons = list_all_lessons()
    assert isinstance(lessons, list)
    assert "year" in lessons[0]
    assert "quarter" in lessons[0]
    assert "lesson_id" in lessons[0]
    assert "metadata" in lessons[0]


def test_get_lesson_pdf_path_valid():
    pdf_path = get_lesson_pdf_path("2025", "Q2", "lesson-08")
    assert pdf_path.name.endswith(".pdf")
    assert pdf_path.exists()


def test_load_lesson_invalid_path():
    with pytest.raises(FileNotFoundError):
        load_lesson_by_path("2099", "Q9", "nonexistent")


def test_metadata_missing_file():
    with pytest.raises(FileNotFoundError):
        load_metadata_by_path("2025", "Q2", "missing-lesson")


def test_invalid_pdf_path():
    with pytest.raises(FileNotFoundError):
        get_lesson_pdf_path("2025", "Q2", "missing-lesson")


# ---- API TESTS ----


def test_api_get_lesson_success():
    res = client.get("/api/v1/lessons/2025/Q2/lesson-08")
    assert res.status_code == 200
    assert "days" in res.json()


def test_api_get_metadata_success():
    res = client.get("/api/v1/lessons/2025/Q2/lesson-08/metadata")
    assert res.status_code == 200
    assert "title" in res.json()


def test_api_get_lesson_not_found():
    res = client.get("/api/v1/lessons/2025/Q2/fake-lesson")
    assert res.status_code == 404
    assert res.json()["detail"] == "Lesson not found"


def test_api_get_metadata_not_found():
    res = client.get("/api/v1/lessons/2025/Q2/fake-lesson/metadata")
    assert res.status_code == 404
    assert res.json()["detail"] == "Metadata not found"


def test_api_get_pdf_not_found():
    res = client.get("/api/v1/lessons/2025/Q2/fake-lesson/pdf")
    assert res.status_code == 404
    assert res.json()["detail"] == "PDF file not found"


def test_api_list_all_lessons():
    res = client.get("/api/v1/lessons")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert "year" in res.json()[0]
