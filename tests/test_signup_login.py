# tests/test_auth_routes.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from uuid import uuid4

client = TestClient(app)


@pytest.fixture
def user_payload():
    return {
        "name": "Test User",
        "email": f"testuser-{uuid4()}@example.com",
        "password": "TestPass123!",
        "role": "student",
    }


def test_signup_success(user_payload):
    response = client.post("/api/v1/auth/signup", json=user_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "user_id" in data


def test_login_success(user_payload):
    # First signup
    signup_response = client.post("/api/v1/auth/signup", json=user_payload)
    assert signup_response.status_code == 200

    # Then login
    login_data = {"email": user_payload["email"], "password": user_payload["password"]}
    login_response = client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200
    login_json = login_response.json()
    assert "access_token" in login_json
    assert login_json["token_type"] == "bearer"
    assert "user" in login_json
    assert login_json["user"]["role"] == user_payload["role"]


def test_signup_duplicate_email(user_payload):
    # First signup
    response1 = client.post("/api/v1/auth/signup", json=user_payload)
    assert response1.status_code == 200

    # Second signup with the same email should fail
    response2 = client.post("/api/v1/auth/signup", json=user_payload)
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"


def test_login_wrong_password(user_payload):
    # First signup
    response = client.post("/api/v1/auth/signup", json=user_payload)
    assert response.status_code == 200

    # Try logging in with incorrect password
    login_data = {"email": user_payload["email"], "password": "WrongPassword123!"}
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_nonexistent_email():
    login_data = {"email": "nonexistent@example.com", "password": "DoesNotMatter123!"}
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_signup_missing_fields():
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "missing@example.com",
            "password": "Test123!",
            # missing 'name' and 'role'
        },
    )
    assert response.status_code == 422  # Unprocessable Entity
