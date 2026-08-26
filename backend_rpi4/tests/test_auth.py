import importlib
import sys


def _reload_app(monkeypatch, access_mode, api_token="test-token"):
    monkeypatch.setenv("ACCESS_MODE", access_mode)
    monkeypatch.setenv("API_TOKEN", api_token)

    for mod in (
        "backend_rpi4.config",
        "backend_rpi4.utils.validators",
        "backend_rpi4.main",
    ):
        sys.modules.pop(mod, None)

    return importlib.import_module("backend_rpi4.main").app


def test_public_mode_rejects_missing_token(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app(monkeypatch, "public")
    response = TestClient(app).get("/status")

    assert response.status_code == 401


def test_public_mode_rejects_wrong_token(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app(monkeypatch, "public", api_token="correct")
    response = TestClient(app).get(
        "/status", headers={"Authorization": "Bearer wrong"}
    )

    assert response.status_code == 401


def test_public_mode_accepts_valid_token(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app(monkeypatch, "public", api_token="secret-123")
    response = TestClient(app).get(
        "/status", headers={"Authorization": "Bearer secret-123"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tailscale_mode_skips_token_check(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app(monkeypatch, "tailscale")
    response = TestClient(app).get("/status")

    assert response.status_code == 200


def test_public_mode_solve_requires_token(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app(monkeypatch, "public", api_token="mytoken")

    # without token
    r = TestClient(app).post(
        "/solve",
        json={"expression": "x+1=0", "type": "equation"},
    )
    assert r.status_code == 401

    # with correct token
    r = TestClient(app).post(
        "/solve",
        json={"expression": "x+1=0", "type": "equation"},
        headers={"Authorization": "Bearer mytoken"},
    )
    assert r.status_code == 200