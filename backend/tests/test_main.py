from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_missing_demo_and_text_returns_400():
    r = client.post("/analyze", json={})
    assert r.status_code == 400


def test_blank_opportunity_text_returns_400():
    r = client.post("/analyze", json={"opportunity_text": "   "})
    assert r.status_code == 400


def test_demo_falls_back_to_fixture_without_llm_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    r = client.post("/analyze", json={"demo": "tecnomania"})
    assert r.status_code == 200
    assert r.json()["company_name"] == "Tecnomania S.L.U."


def test_pasted_text_returns_503_without_llm_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    r = client.post(
        "/analyze", json={"opportunity_text": "Some real opportunity text about a client."}
    )
    assert r.status_code == 503
    assert "GROQ_API_KEY" in r.json()["detail"]


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
