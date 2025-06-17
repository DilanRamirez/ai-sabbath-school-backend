# tests/test_auth_routes.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import app.core.security as security

# Bypass JWT signing in tests
from app.main import app
from uuid import uuid4

client = TestClient(app)


security.create_access_token = lambda data: "testtoken"


@pytest.fixture
def user_payload():
    return {
        "name": "Test User",
        "email": f"testuser-{uuid4()}@example.com",
        "password": "TestPass123!",
        "role": "student",
    }


@patch("app.api.v1.auth.table.put_item", return_value={})
@patch("app.api.v1.auth.table.scan", return_value={"Items": []})
def test_signup_success(mock_scan, mock_put, user_payload):
    response = client.post("/api/v1/auth/signup", json=user_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "user" in data


@patch("app.api.v1.auth.table.put_item", return_value={})
@patch("app.api.v1.auth.table.scan")
def test_login_success(mock_scan, mock_put, user_payload):
    from app.api.v1.auth import hash_password

    # Mock signup (no-op due to patching)
    client.post("/api/v1/auth/signup", json=user_payload)

    # Mock scan for login to return a user with hashed password
    mock_scan.return_value = {
        "Items": [
            {
                "user_id": "mock-user-id",
                "email": user_payload["email"],
                "hashed_password": hash_password(user_payload["password"]),
                "role": user_payload["role"],
                "name": user_payload["name"],
            }
        ]
    }

    login_data = {"email": user_payload["email"], "password": user_payload["password"]}
    login_response = client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200
    login_json = login_response.json()
    assert "access_token" in login_json
    assert login_json["token_type"] == "bearer"
    assert "user" in login_json
    assert login_json["user"]["role"] == user_payload["role"]


@patch("app.api.v1.auth.table.put_item", return_value={})
@patch("app.api.v1.auth.table.scan", return_value={"Items": []})
def test_signup_duplicate_email(mock_scan, mock_put, user_payload):
    # First signup
    response1 = client.post("/api/v1/auth/signup", json=user_payload)
    assert response1.status_code == 200

    # Modify mock_scan to simulate email already registered
    mock_scan.return_value = {"Items": [user_payload]}

    # Second signup with the same email should fail
    response2 = client.post("/api/v1/auth/signup", json=user_payload)
    assert response2.status_code == 400
    assert response2.json()["detail"] == "Email already registered"


@patch("app.api.v1.auth.table.put_item", return_value={})
@patch("app.api.v1.auth.table.scan", return_value={"Items": []})
def test_login_wrong_password(mock_scan, mock_put, user_payload):
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
