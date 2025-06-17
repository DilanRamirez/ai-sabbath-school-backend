# tests/conftest.py
import pytest
from app.core.security import get_current_user, TokenData
from fastapi.testclient import TestClient
from app.main import app
import app.core.security as security
import app.api.v1.auth as auth_module


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def override_get_current_user():
    return TokenData(sub="testuser", roles=["user"])


app.dependency_overrides[get_current_user] = override_get_current_user
# Bypass JWT signing in tests
security.create_access_token = lambda data: "testtoken"
auth_module.create_access_token = lambda data: "testtoken"
