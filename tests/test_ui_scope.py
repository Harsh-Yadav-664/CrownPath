"""tests/test_ui_scope.py -- "what was tested": /api/target serves docs/target.md, and
/api/scope reads the estate (assets, endpoints, crown jewel, findings) live from the graph."""
import os

import pytest
from fastapi.testclient import TestClient

from lib import graph, seed_taxonomy
from ui import app as ui_app


def test_target_text_parses_docs_target_md():
    body = TestClient(ui_app.app).get("/api/target").json()
    assert body["name"] == "Acme Shop"
    assert "synthetic" in body["description"]
    headings = [s["heading"] for s in body["sections"]]
    assert headings[:3] == ["What it is", "Why these findings", "Why synthetic (Rule 6)"]
    assert all(s["text"] and "**" not in s["text"] for s in body["sections"])


@pytest.fixture
def client():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    g = graph.connect()
    seed_taxonomy.load_all(g, "data/findings.json")
    yield TestClient(ui_app.app)
    graph.reset(g)


def test_scope_reads_the_demo_estate_from_the_graph(client):
    body = client.get("/api/scope").json()
    assert body["target"]["name"] == "Acme Shop"
    assert body["counts"] == {"assets": 4, "endpoints": 6, "anonymous_entry_points": 4, "identities": 3,
                              "findings": 8, "confirmed_findings": 7, "crown_jewels": 1}
    assert body["crown_jewels"] == [{"id": "asset:db", "name": "Customer database", "value": 100}]
    assert body["assets"][0]["id"] == "asset:db"

    orders = next(e for e in body["endpoints"] if e["id"] == "ep:orders")
    assert orders == {"id": "ep:orders", "asset_id": "asset:api", "path": "/api/orders",
                      "method": "GET", "auth_required": True}

    idor = next(f for f in body["findings"] if f["id"] == "f:idor")
    assert (idor["type"], idor["cwe"], idor["cvss"], idor["confidence"], idor["status"]) == \
        ("idor", "CWE-639", 8.1, 0.85, "confirmed")
    assert idor["endpoint"] == "GET /api/orders" and idor["asset_id"] == "asset:api"
    assert "evidence" in idor  # null for the synthetic demo; captured findings carry it
    assert next(f for f in body["findings"] if f["id"] == "f:csrf")["status"] == "inconclusive"
