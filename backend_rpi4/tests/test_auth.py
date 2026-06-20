import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _reload_app_with_env(monkeypatch, access_mode, api_token="test-token"):
    """Reload config/validators/main with a forced ACCESS_MODE for this test.

    Needed because config.py reads ACCESS_MODE at import time.
    """
    monkeypatch.setenv("ACCESS_MODE", access_mode)
    monkeypatch.setenv("API_TOKEN", api_token)

    for mod in ("config", "utils.validators", "main"):
        sys.modules.pop(mod, None)

    main = importlib.import_module("main")
    return main.app


def test_public_mode_rejects_missing_token(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app_with_env(monkeypatch, "public")
    client = TestClient(app)

    response = client.get("/status")
    assert response.status_code == 401


def test_public_mode_accepts_valid_token(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app_with_env(monkeypatch, "public", api_token="secret-123")
    client = TestClient(app)

    response = client.get("/status", headers={"Authorization": "Bearer secret-123"})
    assert response.status_code == 200


def test_tailscale_mode_skips_token_check(monkeypatch):
    from fastapi.testclient import TestClient

    app = _reload_app_with_env(monkeypatch, "tailscale")
    client = TestClient(app)

    response = client.get("/status")
    assert response.status_code == 200
