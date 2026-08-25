from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_unified_error_format_404():
    response = client.get("/construction-sites/999999")
    assert response.status_code == 401  # chưa đăng nhập -> 401 trước khi tới 404
    body = response.json()
    assert "error" in body
    assert body["error"]["status_code"] == 401
    assert "message" in body["error"]
