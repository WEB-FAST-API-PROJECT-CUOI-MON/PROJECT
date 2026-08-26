"""Test cho module Công trình (Construction Sites)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import _reset_state_for_tests
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _reset_state_for_tests()
    yield


def _data(r):
    """Mọi response API đều bọc trong envelope 6 trường chuẩn — lấy phần `data` thực sự."""
    return r.json()["data"]


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


def _register_and_login(password: str = "password123") -> tuple[dict, dict]:
    """Đăng ký + đăng nhập một user mới, trả về (headers, user_json)."""
    email = _unique_email()
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": "Người Test"},
    )
    assert r.status_code == 201
    user = _data(r)

    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200
    # /auth/login là token endpoint chuẩn OAuth2 -> không bọc envelope, đọc thẳng r.json()
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def _create_site(headers: dict, name: str = "Công trình test", description: str | None = None):
    return client.post(
        "/construction-sites",
        json={"name": name, "description": description},
        headers=headers,
    )


# --- Tạo công trình ---


def test_create_site_success_and_becomes_owner():
    headers, user = _register_and_login()
    r = _create_site(headers, name="Chung cư ABC")
    assert r.status_code == 201
    body = _data(r)
    assert body["name"] == "Chung cư ABC"
    assert body["owner_id"] == user["id"]

    r = client.get(f"/construction-sites/{body['id']}/members", headers=headers)
    assert r.status_code == 200
    members = _data(r)
    assert len(members) == 1
    assert members[0]["role"] == "OWNER"
    assert members[0]["user_id"] == user["id"]


def test_create_site_requires_auth():
    r = client.post("/construction-sites", json={"name": "X"})
    assert r.status_code == 401


def test_create_site_name_blank_rejected():
    headers, _ = _register_and_login()
    r = _create_site(headers, name="")
    assert r.status_code == 422


def test_create_site_name_too_long_rejected():
    headers, _ = _register_and_login()
    r = _create_site(headers, name="a" * 151)
    assert r.status_code == 422


# --- Danh sách / chi tiết công trình ---


def test_list_sites_only_returns_owner_or_member():
    owner_headers, _ = _register_and_login()
    other_headers, _ = _register_and_login()

    r = _create_site(owner_headers, name="Riêng của owner")
    site_id = _data(r)["id"]

    r = client.get("/construction-sites", headers=owner_headers)
    assert site_id in [s["id"] for s in _data(r)]

    r = client.get("/construction-sites", headers=other_headers)
    assert site_id not in [s["id"] for s in _data(r)]


def test_list_sites_search_by_name():
    headers, _ = _register_and_login()
    unique_name = f"Kho bãi {uuid.uuid4().hex[:8]}"
    _create_site(headers, name=unique_name)
    _create_site(headers, name="Công trình khác")

    r = client.get("/construction-sites", params={"search": unique_name[:10]}, headers=headers)
    assert r.status_code == 200
    names = [s["name"] for s in _data(r)]
    assert unique_name in names
    assert "Công trình khác" not in names


def test_get_site_requires_membership():
    owner_headers, _ = _register_and_login()
    other_headers, _ = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    r = client.get(f"/construction-sites/{site_id}", headers=other_headers)
    assert r.status_code == 403


def test_get_site_not_found():
    headers, _ = _register_and_login()
    r = client.get("/construction-sites/999999999", headers=headers)
    assert r.status_code == 404


# --- Cập nhật / xóa công trình ---


def test_update_site_owner_only():
    owner_headers, _ = _register_and_login()
    other_headers, other_user = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    # thêm other_user làm MEMBER (không phải owner)
    client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": other_user["id"], "role": "MEMBER"},
        headers=owner_headers,
    )

    r = client.patch(f"/construction-sites/{site_id}", json={"name": "Tên mới"}, headers=other_headers)
    assert r.status_code == 403

    r = client.patch(f"/construction-sites/{site_id}", json={"name": "Tên mới"}, headers=owner_headers)
    assert r.status_code == 200
    assert _data(r)["name"] == "Tên mới"


def test_update_site_via_put_same_as_patch():
    owner_headers, _ = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    r = client.put(f"/construction-sites/{site_id}", json={"name": "Tên qua PUT"}, headers=owner_headers)
    assert r.status_code == 200
    assert _data(r)["name"] == "Tên qua PUT"


def test_delete_site_soft_delete_hides_it():
    owner_headers, _ = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    r = client.delete(f"/construction-sites/{site_id}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r) is None

    r = client.get(f"/construction-sites/{site_id}", headers=owner_headers)
    assert r.status_code == 404

    r = client.get("/construction-sites", headers=owner_headers)
    assert site_id not in [s["id"] for s in _data(r)]


def test_delete_site_non_owner_forbidden():
    owner_headers, _ = _register_and_login()
    other_headers, other_user = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": other_user["id"], "role": "MEMBER"},
        headers=owner_headers,
    )

    r = client.delete(f"/construction-sites/{site_id}", headers=other_headers)
    assert r.status_code == 403


# --- Thành viên công trình ---


def test_add_member_success_and_duplicate_rejected():
    owner_headers, _ = _register_and_login()
    _, other_user = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    r = client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": other_user["id"], "role": "MEMBER"},
        headers=owner_headers,
    )
    assert r.status_code == 201
    assert _data(r)["user_id"] == other_user["id"]

    r = client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": other_user["id"], "role": "MEMBER"},
        headers=owner_headers,
    )
    assert r.status_code == 400


def test_add_member_user_not_found():
    owner_headers, _ = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    r = client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": 999999999, "role": "MEMBER"},
        headers=owner_headers,
    )
    assert r.status_code == 404


def test_add_member_non_owner_forbidden():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    _, third_user = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": member_user["id"], "role": "MEMBER"},
        headers=owner_headers,
    )

    r = client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": third_user["id"], "role": "MEMBER"},
        headers=member_headers,
    )
    assert r.status_code == 403


def test_remove_member_success():
    owner_headers, _ = _register_and_login()
    _, member_user = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": member_user["id"], "role": "MEMBER"},
        headers=owner_headers,
    )

    r = client.delete(f"/construction-sites/{site_id}/members/{member_user['id']}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r) is None

    r = client.get(f"/construction-sites/{site_id}/members", headers=owner_headers)
    assert member_user["id"] not in [m["user_id"] for m in _data(r)]


def test_remove_member_not_found():
    owner_headers, _ = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    r = client.delete(f"/construction-sites/{site_id}/members/999999999", headers=owner_headers)
    assert r.status_code == 404


def test_cannot_remove_last_owner():
    owner_headers, owner_user = _register_and_login()
    site_id = _data(_create_site(owner_headers))["id"]

    r = client.delete(f"/construction-sites/{site_id}/members/{owner_user['id']}", headers=owner_headers)
    assert r.status_code == 400
