import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

try:
    from main import app
except ModuleNotFoundError:
    from rpi4.main import app


def test_status_endpoint_returns_active_by_default():
    client = TestClient(app)
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"is_active": True}


def test_toggle_endpoint_updates_state():
    client = TestClient(app)
    response = client.post("/toggle", json={"active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    status_response = client.get("/status")
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    client.post("/toggle", json={"active": True})


def test_solve_endpoint_returns_result_when_active():
    client = TestClient(app)
    client.post("/toggle", json={"active": True})

    response = client.post(
        "/solve",
        json={"expression": "x^2-1=0", "type": "equation", "action": "solve"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "1" in response.json()["result"]


def test_solve_endpoint_rejects_when_inactive():
    client = TestClient(app)
    client.post("/toggle", json={"active": False})

    response = client.post(
        "/solve",
        json={"expression": "x^2-1=0", "type": "equation", "action": "solve"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Service is inactive"

    client.post("/toggle", json={"active": True})
