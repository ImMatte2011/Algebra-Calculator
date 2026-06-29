import os
import sys
from pathlib import Path

# Tests run without Caddy/Tailscale, skip token check
os.environ.setdefault("ACCESS_MODE", "tailscale")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

try:
    from main import app
except ModuleNotFoundError:
    from rpi4.main import app


def test_status_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_solve_endpoint_returns_result():
    client = TestClient(app)
    response = client.post(
        "/solve",
        json={"expression": "x^2-1=0", "type": "equation", "action": None},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "1" in response.json()["result"]


def test_solve_endpoint_returns_400_on_invalid_expression():
    client = TestClient(app)
    response = client.post(
        "/solve",
        json={"expression": "x=", "type": "equation", "action": None},
    )
    assert response.status_code == 400


def test_solve_expression_simplify():
    client = TestClient(app)
    response = client.post(
        "/solve",
        json={"expression": "2*x+2*x", "type": "expression", "action": "simplify"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_solve_inequality():
    client = TestClient(app)
    response = client.post(
        "/solve",
        json={"expression": "x>1", "type": "inequality", "action": None},
    )
    assert response.status_code == 200
    assert "1" in response.json()["result"]