import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_raw_ok():
    # basic smoke test: the happy path should at least return a structured payload
    payload = json.load(open("sample_dag.json"))
    r = client.post("/health/raw", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "overall" in data and "results" in data
    assert set(data["results"].keys())
