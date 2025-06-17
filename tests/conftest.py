# tests/conftest.py
import pytest
from app.core.security import get_current_user, TokenData
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def override_get_current_user():
    return TokenData(sub="testuser", roles=["user"])


app.dependency_overrides[get_current_user] = override_get_current_user
