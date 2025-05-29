import json
import io
import pytest
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient
from app.main import app
import app.core.config as config
from app.core.config import settings, BUCKET

# Autouse fixture to mock S3 for all import tests


@pytest.fixture(autouse=True)
def s3_import_setup(monkeypatch):
    # Start moto mock
    m = mock_aws()
    m.start()
    _region = settings.AWS_REGION or "us-east-1"
    client = boto3.client("s3", region_name=_region)
    # Create bucket with proper location constraint
    if _region == "us-east-1":
        client.create_bucket(Bucket=BUCKET)
    else:
        client.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": _region},
        )
    # Monkeypatch the app's S3 client
    monkeypatch.setattr(config, "s3", client)
    monkeypatch.setattr(config, "BUCKET", BUCKET)
    yield
    m.stop()


@pytest.fixture
def client():
    return TestClient(app)


def test_import_lesson_success(client):
    # Prepare a valid JSON and a fake PDF file
    year, quarter, lesson_id = "2025", "Q2", "lesson-08"
    lesson_payload = {"id": lesson_id, "title": "Test Lesson"}
    lesson_data = json.dumps(lesson_payload)
    pdf_bytes = b"%PDF-1.4\n%Fake PDF content"
    files = {
        "lesson_data": (None, lesson_data, "application/json"),
        "pdf": ("lesson.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
    }
    response = client.post(
        f"/api/v1/lessons/{year}/{quarter}/{lesson_id}/import", files=files
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert lesson_id in data["message"]


def test_import_lesson_invalid_json(client):
    # Invalid JSON string should produce 400
    year, quarter, lesson_id = "2025", "Q2", "lesson-09"
    invalid_json = "not a valid json"
    pdf_bytes = b"%PDF-1.4\n%Fake PDF content"
    files = {
        "lesson_data": (None, invalid_json, "application/json"),
        "pdf": ("lesson.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
    }
    response = client.post(
        f"/api/v1/lessons/{year}/{quarter}/{lesson_id}/import", files=files
    )
    assert response.status_code == 400
    err = response.json()
    assert "Invalid lesson JSON" in err["detail"]


def test_import_lesson_missing_pdf(client):
    # Missing PDF should produce 422
    year, quarter, lesson_id = "2025", "Q2", "lesson-10"
    lesson_payload = {"id": lesson_id, "title": "Another Lesson"}
    lesson_data = json.dumps(lesson_payload)
    files = {
        "lesson_data": (None, lesson_data, "application/json"),
        # no 'pdf' field
    }
    response = client.post(
        f"/api/v1/lessons/{year}/{quarter}/{lesson_id}/import", files=files
    )
    assert response.status_code == 422


def test_import_lesson_missing_json(client):
    # Missing lesson_data should produce 422
    year, quarter, lesson_id = "2025", "Q2", "lesson-11"
    pdf_bytes = b"%PDF-1.4\n%Fake PDF content"
    files = {
        "pdf": ("lesson.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
    }
    response = client.post(
        f"/api/v1/lessons/{year}/{quarter}/{lesson_id}/import", files=files
    )
    assert response.status_code == 422
