from fastapi.testclient import TestClient

import app.main as main
from app.llm.fake import FakeBackend


class _Hit:
    def __init__(self, id, score, fields):
        self.id, self.score, self.fields = id, score, fields


client = TestClient(main.app)


def test_health_reports_backend():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "llm_backend" in r.json()


def test_match_returns_contract_shape(monkeypatch):
    hits = [
        _Hit("KA-01093", 0.40, {"title": "Pothole", "description": "road hole",
                                "classification": "submittable"}),
        _Hit("KA-01036", 0.91, {"title": "Heat or Hot Water", "description": "no heat",
                                "classification": "submittable"}),
    ]
    monkeypatch.setattr(main, "_retriever", lambda text: hits)
    monkeypatch.setattr(main, "_backend", FakeBackend())

    r = client.post("/api/match", json={"text": "no heat in my apartment"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["candidates"]) == 2
    assert body["picked_ka"] == "KA-01036"
    assert body["reasoning"]
    assert body["emergency"] is False


def test_match_rejects_empty_text():
    r = client.post("/api/match", json={"text": "   "})
    assert r.status_code == 422


def test_submit_returns_sr_number_for_mapped_ka():
    # KA-01036 is in the real data/311-mapping.json
    r = client.post("/api/submit", json={
        "ka": "KA-01036", "description": "no heat", "address": "1 Broadway",
        "borough": "MANHATTAN",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "mock-submitted"
    assert body["sr_number"].startswith("311-MOCK-")
    assert body["payload"]["agency"]


def test_submit_rejects_unmapped_ka():
    r = client.post("/api/submit", json={"ka": "KA-00000", "description": "x"})
    assert r.status_code == 422
