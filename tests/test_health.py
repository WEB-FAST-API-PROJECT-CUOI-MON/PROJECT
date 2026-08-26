from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_STANDARD_KEYS = {"statusCode", "message", "data", "error", "path", "timestamp"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == _STANDARD_KEYS
    assert body["statusCode"] == 200
    assert body["error"] is None
    assert body["path"] == "/"
    assert "message" in body["data"]


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == _STANDARD_KEYS
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] == "ok"


def test_unified_error_format_404():
    response = client.get("/construction-sites/999999")
    assert response.status_code == 401  # chưa đăng nhập -> 401 trước khi tới 404
    body = response.json()
    assert set(body.keys()) == _STANDARD_KEYS
    assert body["statusCode"] == 401
    assert body["data"] is None
    assert body["error"] is not None
    assert "message" in body
    assert body["path"] == "/construction-sites/999999"
