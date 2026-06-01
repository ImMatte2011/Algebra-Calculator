from fastapi.testclient import TestClient
from rpi4.main import app


def test_solve_endpoint_returns_401_without_token():
    client = TestClient(app)
    response = client.post("/solve", json={"expr": "x^2"})
    assert response.status_code == 401


def test_solve_endpoint_returns_result_with_token(monkeypatch):
    from rpi4.config import CONFIG
    CONFIG["API_TOKEN"] = "test-token"

    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}
    response = client.post("/solve", json={"expr": "x^2"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["ok"] is True
