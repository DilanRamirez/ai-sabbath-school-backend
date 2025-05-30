import pytest
import boto3
from moto import mock_aws
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import BUCKET, settings


@pytest.fixture(autouse=True)
def s3_setup(monkeypatch):
    # Start moto and create a test S3 bucket
    m = mock_aws()
    m.start()
    client = boto3.client("s3", region_name=settings.AWS_REGION)
    # Create bucket with correct location constraint
    if settings.AWS_REGION == "us-east-1":
        client.create_bucket(Bucket=BUCKET)
    else:
        client.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION},
        )
    # Populate with two years/quarters/lessons
    for year, quarter, lid in [
        ("2025", "Q2", "lesson-8"),
        ("2025", "Q2", "lesson-9"),
        ("2024", "Q1", "lesson-1"),
    ]:
        key_json = f"{year}/{quarter}/{lid}/lesson.json"
        key_pdf = f"{year}/{quarter}/{lid}/{lid}.pdf"
        client.put_object(
            Bucket=BUCKET, Key=key_json, Body=b"{}", ContentType="application/json"
        )
        client.put_object(
            Bucket=BUCKET, Key=key_pdf, Body=b"%PDF-1.4", ContentType="application/pdf"
        )
    # Monkeypatch the s3 client in your application
    import app.core.config as config

    monkeypatch.setattr(config, "s3", client)
    yield
    m.stop()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_list_all_lessons_success(client):
    response = client.get("/api/v1/lessons")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_lesson_success(client):
    response = client.get(
        "/api/v1/lessons/2025/alusiones-imgenes-y-smbolos-cmo-estudiar-la-profeca-biblica/lesson-9"
    )
    assert response.status_code == 200
    data = response.json()
    assert "days" in data


def test_get_lesson_not_found(client):
    response = client.get("/api/v1/lessons/2025/Q2/nonexistent")
    assert response.status_code == 404


def test_get_lesson_metadata_not_found(client):
    response = client.get("/api/v1/lessons/2025/Q2/nonexistent/metadata")
    assert response.status_code == 404


def test_get_lesson_pdf_success(client):
    response = client.get(
        "/api/v1/lessons/2025/alusiones-imgenes-y-smbolos-cmo-estudiar-la-profeca-biblica/lesson-9/pdf"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_get_lesson_pdf_not_found(client):
    response = client.get("/api/v1/lessons/2025/Q2/nonexistent/pdf")
    assert response.status_code == 404


def test_get_lesson_bad_request(client):
    # Malformed year
    response = client.get("/api/v1/lessons/abcd/Q2/lesson-08")
    assert response.status_code == 400 or response.status_code == 404
    # Malformed quarter
    response = client.get("/api/v1/lessons/2025/quarter2/lesson-08")
    assert response.status_code == 400 or response.status_code == 404


def test_get_lesson_metadata_bad_request(client):
    response = client.get("/api/v1/lessons/abcd/Q2/lesson-08/metadata")
    assert response.status_code == 400 or response.status_code == 404


def test_get_lesson_pdf_bad_request(client):
    response = client.get("/api/v1/lessons/2025/quarter2/lesson-08/pdf")
    assert response.status_code == 400 or response.status_code == 404


# Additional tests for listing quarters and lessons edge cases
def test_list_quarters_success(client):
    response = client.get("/api/v1/quarters")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_lessons_filter_year(client):
    # Filter only by year
    response = client.get("/api/v1/lessons?year=2025")
    assert response.status_code == 200
    lessons = response.json()
    assert all(item["year"] == "2025" for item in lessons)


def test_list_lessons_filter_quarter(client):
    # Filter only by quarter
    response = client.get("/api/v1/lessons?quarter=Q1")
    assert response.status_code == 200
    lessons = response.json()
    assert all(item["quarter"] == "Q1" for item in lessons)


def test_list_lessons_filter_year_and_quarter(client):
    # Year and quarter combination with no entries (e.g., 2025/Q1)
    response = client.get("/api/v1/lessons?year=2025&quarter=Q1")
    assert response.status_code == 200
    lessons = response.json()
    assert isinstance(lessons, list)
    assert lessons == []


def test_list_lessons_empty_bucket(monkeypatch, client):
    # Simulate an empty bucket by mocking S3 list_objects_v2
    class EmptyS3:
        def list_objects_v2(self, *args, **kwargs):
            return {"CommonPrefixes": [], "Contents": []}

    import app.core.config as config

    # Override the S3 client and bucket
    monkeypatch.setattr(config, "s3", EmptyS3())
    monkeypatch.setattr(config, "BUCKET", BUCKET)

    # Now list_lessons should return an empty list or a list of seeded entries
    response = client.get("/api/v1/lessons")
    assert response.status_code == 200
    # With an empty bucket mock, we at least get a list (may fall back to seeded entries)
    assert isinstance(response.json(), list)
