"""tests/test_ui_agent.py -- /api/agent never errors (issue #25): rate limit and
agent failure both fall back to the recorded sample with HTTP 200. No network."""
from fastapi.testclient import TestClient

from ui import app as ui_app


def _client():
    ui_app._hits.clear()
    return TestClient(ui_app.app)


def test_rate_limit_serves_sample(monkeypatch):
    monkeypatch.setattr(ui_app, "AGENT_RATE_LIMIT", 0)
    res = _client().get("/api/agent")
    body = res.json()
    assert res.status_code == 200
    assert body["sample_response"] is True
    assert "rate limit" in body["reason"]
    assert "f:idor" in {c["finding_id"] for c in body["choke_points"]}


def test_agent_failure_serves_sample(monkeypatch):
    def boom(question, crown_jewel):
        raise RuntimeError("provider down")

    monkeypatch.setattr(ui_app, "_run_agent", boom)
    res = _client().get("/api/agent")
    body = res.json()
    assert res.status_code == 200
    assert body["sample_response"] is True
    assert body["answer"]
    assert "RuntimeError" in body["reason"]


def test_agent_exit_serves_sample(monkeypatch):
    def exits(question, crown_jewel):
        raise SystemExit(1)  # agent.run exits when a key is missing

    monkeypatch.setattr(ui_app, "_run_agent", exits)
    body = _client().get("/api/agent").json()
    assert body["sample_response"] is True
