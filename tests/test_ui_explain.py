"""tests/test_ui_explain.py -- the explainability endpoints behind the UI: estate-only
graph by default, ranked scored paths, and the non-destructive what-if."""
import os

import pytest
from fastapi.testclient import TestClient

from lib import graph, seed_taxonomy
from ui import app as ui_app


@pytest.fixture
def client():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    g = graph.connect()
    seed_taxonomy.load_all(g, "data/findings.json")
    yield TestClient(ui_app.app)
    graph.reset(g)


def test_graph_hides_taxonomy_by_default(client):
    body = client.get("/api/graph").json()
    assert len(body["nodes"]) == 21
    assert {n["data"]["type"] for n in body["nodes"]} == {"Asset", "Endpoint", "Finding", "Identity"}
    idor = next(n for n in body["nodes"] if n["data"]["id"] == "f:idor")["data"]["props"]
    assert idor["confidence"] == 0.85 and idor["fix"]
    assert len(client.get("/api/graph?taxonomy=true").json()["nodes"]) > 90


def test_paths_are_ranked_and_scored(client):
    scores = [p["score"] for p in client.get("/api/paths").json()["paths"]]
    assert scores == sorted(scores, reverse=True)
    assert round(scores[0], 2) == 12.75 and len(scores) == 6


def test_whatif_is_non_destructive_and_matches_deletion_proof(client):
    body = client.get("/api/whatif?finding=f:idor").json()
    assert len(body["remaining"]) == 2  # the two SSRF -> admin paths
    assert all("f:idor" not in path for path in body["remaining"])
    assert len(client.get("/api/paths").json()["paths"]) == 6  # graph untouched
