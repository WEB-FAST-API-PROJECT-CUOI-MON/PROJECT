"""Test cho module Authentication/Authorization."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import _reset_state_for_tests
from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Mỗi test có quota rate-limit riêng, không bị ảnh hưởng bởi test khác."""
    _reset_state_for_tests()
    yield


def _data(r):
    """Mọi response API đều bọc trong envelope 6 trường chuẩn — lấy phần `data` thực sự."""
    return r.json()["data"]


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


def _login(email: str, password: str):
    return client.post("/auth/login", data={"username": email, "password": password})


def _register(email: str, password: str = "password123", full_name: str = "Người Test"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


# --- Register ---


def test_register_success():
    email = _unique_email()
    r = _register(email)
    assert r.status_code == 201
    body = _data(r)
    assert body["email"] == email
    assert body["role"] == "USER"
    assert body["is_active"] is True
    assert "password_hash" not in body
    assert "password" not in body


def test_register_duplicate_email():
    email = _unique_email()
    assert _register(email).status_code == 201
    r = _register(email)
    assert r.status_code == 400


def test_register_password_too_short():
    r = _register(_unique_email(), password="123")
    assert r.status_code == 422


# --- Login ---


def test_login_success_returns_access_and_refresh_token():
    r = _login("admin@example.com", "admin123")
    assert r.status_code == 200
    # /auth/login là token endpoint chuẩn OAuth2 -> không bọc envelope, đọc thẳng r.json()
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password():
    r = _login("admin@example.com", "wrong-password")
    assert r.status_code == 401


def test_login_inactive_account():
    r = _login("inactive@example.com", "inactive123")
    assert r.status_code == 403


def test_login_rate_limit_blocks_after_max_attempts():
    for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
        r = _login("admin@example.com", "wrong-password")
        assert r.status_code == 401
    r = _login("admin@example.com", "wrong-password")
    assert r.status_code == 429


# --- Current user ---


def test_get_current_user():
    token = _login("admin@example.com", "admin123").json()["access_token"]
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = _data(r)
    assert body["email"] == "admin@example.com"
    assert "password_hash" not in body


def test_get_current_user_without_token():
    r = client.get("/users/me")
    assert r.status_code == 401


def test_get_current_user_invalid_token():
    r = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
    assert "hết hạn" not in r.json()["message"]


def test_get_current_user_expired_token():
    expired = create_access_token({"sub": "admin@example.com"}, expires_delta=timedelta(seconds=-1))
    r = client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    assert "hết hạn" in r.json()["message"]


# --- Role guard / danh sách user ---


def test_list_users_requires_admin():
    token = _login("manager1@example.com", "manager123").json()["access_token"]
    r = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_list_users_as_admin_with_search_and_status_filter():
    token = _login("admin@example.com", "admin123").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.get("/users", params={"search": "worker1"}, headers=headers)
    assert r.status_code == 200
    emails = [u["email"] for u in _data(r)]
    assert "worker1@example.com" in emails

    r = client.get("/users", params={"is_active": False}, headers=headers)
    assert r.status_code == 200
    users = _data(r)
    emails = [u["email"] for u in users]
    assert "inactive@example.com" in emails
    assert all(u["is_active"] is False for u in users)


# --- Refresh token ---


def test_refresh_token_issues_new_access_token():
    tokens = _login("admin@example.com", "admin123").json()
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new_tokens = r.json()
    assert new_tokens["access_token"]

    r = client.get(
        "/users/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert r.status_code == 200


def test_refresh_rejects_access_token():
    tokens = _login("admin@example.com", "admin123").json()
    r = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401
