from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_and_health():
    r = client.get("/")
    assert r.status_code == 200
    assert "disclaimer" in r.json()
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"
