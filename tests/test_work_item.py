"""Test cho module Hạng mục thi công (Work Items) và Đội thi công (Teams)."""

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


def _create_site(headers: dict, name: str = "Công trình test"):
    r = client.post("/construction-sites", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return _data(r)["id"]


def _add_member(owner_headers: dict, site_id: int, user_id: int, role: str = "MEMBER"):
    r = client.post(
        f"/construction-sites/{site_id}/members",
        json={"user_id": user_id, "role": role},
        headers=owner_headers,
    )
    assert r.status_code == 201


def _create_team(owner_headers: dict, site_id: int, name: str = "Tổ đội 1"):
    r = client.post(f"/construction-sites/{site_id}/teams", json={"name": name}, headers=owner_headers)
    assert r.status_code == 201
    return _data(r)["id"]


def _add_team_member(owner_headers: dict, team_id: int, user_id: int):
    r = client.post(f"/teams/{team_id}/members", json={"user_id": user_id}, headers=owner_headers)
    assert r.status_code == 201


def _create_work_item(headers: dict, site_id: int, title: str = "Đổ móng", **kwargs):
    payload = {"title": title, **kwargs}
    return client.post(f"/construction-sites/{site_id}/work-items", json=payload, headers=headers)


# --- Team ---


def test_create_team_owner_only():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])

    r = client.post(f"/construction-sites/{site_id}/teams", json={"name": "Tổ Nề"}, headers=member_headers)
    assert r.status_code == 403

    r = client.post(f"/construction-sites/{site_id}/teams", json={"name": "Tổ Nề"}, headers=owner_headers)
    assert r.status_code == 201
    assert _data(r)["name"] == "Tổ Nề"


def test_add_team_member_requires_site_membership():
    owner_headers, _ = _register_and_login()
    _, outsider = _register_and_login()
    site_id = _create_site(owner_headers)
    team_id = _create_team(owner_headers, site_id)

    r = client.post(f"/teams/{team_id}/members", json={"user_id": outsider["id"]}, headers=owner_headers)
    assert r.status_code == 400


def test_team_list_requires_site_membership():
    owner_headers, _ = _register_and_login()
    other_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    _create_team(owner_headers, site_id)

    r = client.get(f"/construction-sites/{site_id}/teams", headers=other_headers)
    assert r.status_code == 403


def test_get_team_detail_requires_membership():
    owner_headers, _ = _register_and_login()
    other_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    team_id = _create_team(owner_headers, site_id)

    r = client.get(f"/teams/{team_id}", headers=other_headers)
    assert r.status_code == 403

    r = client.get(f"/teams/{team_id}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r)["id"] == team_id


def test_get_team_not_found():
    headers, _ = _register_and_login()
    r = client.get("/teams/999999999", headers=headers)
    assert r.status_code == 404


def test_update_team_owner_only():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    team_id = _create_team(owner_headers, site_id, name="Tổ cũ")

    r = client.patch(f"/teams/{team_id}", json={"name": "Tổ mới"}, headers=member_headers)
    assert r.status_code == 403

    r = client.patch(f"/teams/{team_id}", json={"name": "Tổ mới"}, headers=owner_headers)
    assert r.status_code == 200
    assert _data(r)["name"] == "Tổ mới"


def test_list_team_members():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    team_id = _create_team(owner_headers, site_id)
    _add_team_member(owner_headers, team_id, member_user["id"])

    r = client.get(f"/teams/{team_id}/members", headers=owner_headers)
    assert r.status_code == 200
    body = _data(r)
    assert len(body) == 1
    assert body[0]["user_id"] == member_user["id"]

    r = client.get(f"/teams/{team_id}/members", headers=member_headers)
    assert r.status_code == 200


def test_add_team_member_duplicate_rejected():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    team_id = _create_team(owner_headers, site_id)
    _add_team_member(owner_headers, team_id, member_user["id"])

    r = client.post(f"/teams/{team_id}/members", json={"user_id": member_user["id"]}, headers=owner_headers)
    assert r.status_code == 400


def test_remove_team_member_owner_only_and_not_found():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    team_id = _create_team(owner_headers, site_id)
    _add_team_member(owner_headers, team_id, member_user["id"])

    r = client.delete(f"/teams/{team_id}/members/{member_user['id']}", headers=member_headers)
    assert r.status_code == 403

    r = client.delete(f"/teams/{team_id}/members/{member_user['id']}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r) is None

    r = client.delete(f"/teams/{team_id}/members/{member_user['id']}", headers=owner_headers)
    assert r.status_code == 404


def test_delete_team_owner_only_and_unassigns_work_items():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    team_id = _create_team(owner_headers, site_id)
    item_id = _data(_create_work_item(owner_headers, site_id, assignee_team_id=team_id))["id"]

    r = client.delete(f"/teams/{team_id}", headers=member_headers)
    assert r.status_code == 403

    r = client.delete(f"/teams/{team_id}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r) is None

    r = client.get(f"/teams/{team_id}", headers=owner_headers)
    assert r.status_code == 404

    # Hạng mục đang giao cho đội bị xóa -> assignee_team_id phải về null, không lỗi 500
    r = client.get(f"/work-items/{item_id}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r)["assignee_team_id"] is None


# --- Tạo hạng mục thi công ---


def test_create_work_item_by_any_member():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])

    r = _create_work_item(member_headers, site_id, title="Đào móng", priority="HIGH")
    assert r.status_code == 201
    body = _data(r)
    assert body["title"] == "Đào móng"
    assert body["status"] == "TODO"
    assert body["site_id"] == site_id


def test_create_work_item_requires_membership():
    owner_headers, _ = _register_and_login()
    outsider_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)

    r = _create_work_item(outsider_headers, site_id)
    assert r.status_code == 403


def test_create_work_item_assignee_team_must_belong_to_site():
    owner_headers, _ = _register_and_login()
    other_owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    other_site_id = _create_site(other_owner_headers)
    foreign_team_id = _create_team(other_owner_headers, other_site_id)

    r = _create_work_item(owner_headers, site_id, assignee_team_id=foreign_team_id)
    assert r.status_code == 400


def test_create_work_item_with_valid_assignee_team():
    owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    team_id = _create_team(owner_headers, site_id)

    r = _create_work_item(owner_headers, site_id, assignee_team_id=team_id)
    assert r.status_code == 201
    body = _data(r)
    assert body["assignee_team_id"] == team_id
    assert body["assignee_team"]["id"] == team_id


# --- Danh sách / chi tiết ---


def test_list_work_items_scoped_to_site():
    owner_headers, _ = _register_and_login()
    site1 = _create_site(owner_headers, "Công trình A")
    site2 = _create_site(owner_headers, "Công trình B")
    _create_work_item(owner_headers, site1, title="Việc A")
    _create_work_item(owner_headers, site2, title="Việc B")

    r = client.get(f"/construction-sites/{site1}/work-items", headers=owner_headers)
    assert r.status_code == 200
    body = _data(r)
    titles = [i["title"] for i in body["items"]]
    assert "Việc A" in titles
    assert "Việc B" not in titles


def test_list_work_items_requires_membership():
    owner_headers, _ = _register_and_login()
    other_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)

    r = client.get(f"/construction-sites/{site_id}/work-items", headers=other_headers)
    assert r.status_code == 403


def test_list_work_items_filter_and_search():
    owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    _create_work_item(owner_headers, site_id, title="Đổ móng", priority="HIGH")
    r2 = _create_work_item(owner_headers, site_id, title="Xây tường", priority="LOW")
    item2_id = _data(r2)["id"]
    client.patch(f"/work-items/{item2_id}", json={"status": "DONE"}, headers=owner_headers)

    r = client.get(
        f"/construction-sites/{site_id}/work-items",
        params={"priority": "HIGH"},
        headers=owner_headers,
    )
    assert r.status_code == 200
    assert all(i["priority"] == "HIGH" for i in _data(r)["items"])

    r = client.get(
        f"/construction-sites/{site_id}/work-items",
        params={"status": "DONE"},
        headers=owner_headers,
    )
    assert [i["title"] for i in _data(r)["items"]] == ["Xây tường"]

    r = client.get(
        f"/construction-sites/{site_id}/work-items",
        params={"search": "móng"},
        headers=owner_headers,
    )
    assert [i["title"] for i in _data(r)["items"]] == ["Đổ móng"]


def test_list_work_items_pagination():
    owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    for i in range(5):
        _create_work_item(owner_headers, site_id, title=f"Việc {i}")

    r = client.get(
        f"/construction-sites/{site_id}/work-items",
        params={"page": 1, "size": 2},
        headers=owner_headers,
    )
    body = _data(r)
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["size"] == 2


def test_get_work_item_detail_requires_membership():
    owner_headers, _ = _register_and_login()
    other_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.get(f"/work-items/{item_id}", headers=other_headers)
    assert r.status_code == 403

    r = client.get(f"/work-items/{item_id}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r)["id"] == item_id


def test_get_work_item_not_found():
    headers, _ = _register_and_login()
    r = client.get("/work-items/999999999", headers=headers)
    assert r.status_code == 404


# --- Cập nhật / xóa: permission matrix owner/member/assignee ---


def test_update_work_item_owner_can_edit_any_field():
    owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    item_id = _data(_create_work_item(owner_headers, site_id, title="Việc cũ"))["id"]

    r = client.patch(
        f"/work-items/{item_id}",
        json={"title": "Việc mới", "priority": "HIGH", "status": "IN_PROGRESS"},
        headers=owner_headers,
    )
    assert r.status_code == 200
    body = _data(r)
    assert body["title"] == "Việc mới"
    assert body["priority"] == "HIGH"
    assert body["status"] == "IN_PROGRESS"


def test_update_work_item_does_not_overwrite_unset_fields():
    owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    item_id = _data(
        _create_work_item(owner_headers, site_id, title="Việc A", description="Mô tả gốc", priority="HIGH")
    )["id"]

    r = client.patch(f"/work-items/{item_id}", json={"status": "IN_PROGRESS"}, headers=owner_headers)
    assert r.status_code == 200
    body = _data(r)
    assert body["status"] == "IN_PROGRESS"
    assert body["description"] == "Mô tả gốc"
    assert body["priority"] == "HIGH"
    assert body["title"] == "Việc A"


def test_update_work_item_assignee_team_member_can_only_update_status_description():
    owner_headers, _ = _register_and_login()
    worker_headers, worker_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, worker_user["id"])
    team_id = _create_team(owner_headers, site_id)
    _add_team_member(owner_headers, team_id, worker_user["id"])
    item_id = _data(_create_work_item(owner_headers, site_id, assignee_team_id=team_id))["id"]

    # assignee được sửa status/description
    r = client.patch(
        f"/work-items/{item_id}",
        json={"status": "IN_PROGRESS", "description": "Đang thi công"},
        headers=worker_headers,
    )
    assert r.status_code == 200
    assert _data(r)["status"] == "IN_PROGRESS"

    # assignee không được sửa title/priority/assignee_team_id
    r = client.patch(f"/work-items/{item_id}", json={"title": "Đổi tên"}, headers=worker_headers)
    assert r.status_code == 403

    r = client.patch(f"/work-items/{item_id}", json={"priority": "LOW"}, headers=worker_headers)
    assert r.status_code == 403


def test_update_work_item_unrelated_member_forbidden():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.patch(f"/work-items/{item_id}", json={"status": "DONE"}, headers=member_headers)
    assert r.status_code == 403


def test_update_work_item_non_member_forbidden():
    owner_headers, _ = _register_and_login()
    outsider_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.patch(f"/work-items/{item_id}", json={"status": "DONE"}, headers=outsider_headers)
    assert r.status_code == 403


def test_delete_work_item_owner_only():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.delete(f"/work-items/{item_id}", headers=member_headers)
    assert r.status_code == 403

    r = client.delete(f"/work-items/{item_id}", headers=owner_headers)
    assert r.status_code == 200
    assert _data(r) is None

    r = client.get(f"/work-items/{item_id}", headers=owner_headers)
    assert r.status_code == 404


# --- Comment ---


def test_comment_create_and_list_requires_membership():
    owner_headers, _ = _register_and_login()
    member_headers, member_user = _register_and_login()
    outsider_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    _add_member(owner_headers, site_id, member_user["id"])
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.post(f"/work-items/{item_id}/comments", json={"content": "Đã kiểm tra hiện trường"}, headers=member_headers)
    assert r.status_code == 201
    assert _data(r)["content"] == "Đã kiểm tra hiện trường"

    r = client.post(f"/work-items/{item_id}/comments", json={"content": "spam"}, headers=outsider_headers)
    assert r.status_code == 403

    r = client.get(f"/work-items/{item_id}/comments", headers=owner_headers)
    assert r.status_code == 200
    assert len(_data(r)) == 1

    r = client.get(f"/work-items/{item_id}/comments", headers=outsider_headers)
    assert r.status_code == 403


# --- Attachment ---


def test_upload_attachment_rejects_invalid_type():
    owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.post(
        f"/work-items/{item_id}/attachments",
        files={"file": ("malware.exe", b"MZ...", "application/x-msdownload")},
        headers=owner_headers,
    )
    assert r.status_code == 400


def test_upload_attachment_success_and_list():
    owner_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.post(
        f"/work-items/{item_id}/attachments",
        files={"file": ("nghiem_thu.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        headers=owner_headers,
    )
    assert r.status_code == 201
    body = _data(r)
    assert body["file_name"] == "nghiem_thu.pdf"
    assert body["content_type"] == "application/pdf"

    r = client.get(f"/work-items/{item_id}/attachments", headers=owner_headers)
    assert r.status_code == 200
    assert len(_data(r)) == 1


def test_upload_attachment_requires_membership():
    owner_headers, _ = _register_and_login()
    outsider_headers, _ = _register_and_login()
    site_id = _create_site(owner_headers)
    item_id = _data(_create_work_item(owner_headers, site_id))["id"]

    r = client.post(
        f"/work-items/{item_id}/attachments",
        files={"file": ("photo.png", b"\x89PNG fake", "image/png")},
        headers=outsider_headers,
    )
    assert r.status_code == 403
