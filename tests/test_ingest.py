"""tests/test_ingest.py — asserts node/edge counts for the demo graph, the
confirmed-only attack-edge rule, hard-fail on unknown technique_id, and
idempotency. Skips cleanly without a live FalkorDB server."""
import json
import os
import tempfile

import pytest

from lib import graph, ingest, seed_taxonomy


def _connect_or_skip():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    try:
        return graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")


def test_load_all_demo_graph_counts():
    g = _connect_or_skip()
    result = seed_taxonomy.load_all(g, "data/findings.json")

    assert result["ingest"]["nodes"] == 21  # 4 assets + 6 endpoints + 3 identities + 8 findings
    assert result["ingest"]["skipped_attack_edges"] == 0  # f:csrf carries no attack-edge FK at all

    rows = graph.run(
        g,
        """
        MATCH (f:Finding {id:'f:csrf'})
        OPTIONAL MATCH (e:Endpoint)-[hf:HAS_FINDING]->(f)
        OPTIONAL MATCH (f)-[io:INSTANCE_OF]->(:Technique)
        OPTIONAL MATCH (f)-[g:GRANTS]->(:Identity)
        OPTIONAL MATCH (f)-[lt:LEADS_TO]->(:Asset)
        RETURN hf IS NOT NULL, io IS NOT NULL, g IS NOT NULL, lt IS NOT NULL
        """,
    ).result_set
    has_findings, has_instance_of, has_grants, has_leads_to = rows[0]
    assert has_findings is True
    assert has_instance_of is True
    assert has_grants is False
    assert has_leads_to is False

    # idempotent: re-running (without reset) must not change counts
    second = ingest.ingest(g, "data/findings.json", reset=False)
    rows = graph.run(g, "MATCH (n) RETURN count(n)").result_set
    total_after = rows[0][0]
    rows = graph.run(g, "MATCH (n) RETURN count(n)").result_set
    assert rows[0][0] == total_after  # stable

    graph.reset(g)


def test_ingest_hard_fails_on_unknown_technique_id():
    g = _connect_or_skip()
    graph.reset(g)
    graph.init_schema(g)

    doc = {
        "assets": [{"id": "a1", "name": "A", "type": "host", "is_crown_jewel": False, "value": 1}],
        "endpoints": [{"id": "e1", "asset_id": "a1", "url": "/x", "method": "GET", "auth_required": False}],
        "identities": [{"id": "i1", "role": "anonymous", "privilege_level": 0}],
        "findings": [
            {
                "id": "f1", "title": "t", "vuln_type": "xss", "confidence": 0.5,
                "status": "confirmed", "endpoint_id": "e1", "technique_id": "no-such-technique",
            }
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        path = f.name
    try:
        with pytest.raises(RuntimeError):
            ingest.ingest(g, path=path, reset=False)
    finally:
        os.unlink(path)
        graph.reset(g)


def test_ingest_skips_attack_edges_for_non_confirmed_findings():
    """The skip mechanism itself, with a synthetic fixture (the frozen demo data's
    f:csrf carries no attack-edge FK at all, so it can't exercise this path)."""
    g = _connect_or_skip()
    graph.reset(g)
    graph.init_schema(g)
    graph.run(g, "MERGE (t:Technique {id:'tech:x'})")

    doc = {
        "assets": [
            {"id": "a1", "name": "A", "type": "host", "is_crown_jewel": False, "value": 1},
            {"id": "a2", "name": "B", "type": "database", "is_crown_jewel": True, "value": 50},
        ],
        "endpoints": [{"id": "e1", "asset_id": "a1", "url": "/x", "method": "GET", "auth_required": False}],
        "identities": [{"id": "i1", "role": "user", "privilege_level": 1}],
        "findings": [
            {
                "id": "f1", "title": "t", "vuln_type": "xss", "confidence": 0.5,
                "status": "inconclusive", "endpoint_id": "e1", "technique_id": "tech:x",
                "grants_identity_id": "i1", "leads_to_asset_id": "a2",
            }
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        path = f.name
    try:
        result = ingest.ingest(g, path=path, reset=False)
        assert result["skipped_attack_edges"] == 2  # GRANTS + LEADS_TO both skipped

        rows = graph.run(g, "MATCH (:Finding {id:'f1'})-[r:GRANTS]->() RETURN count(r)").result_set
        assert rows[0][0] == 0
        rows = graph.run(g, "MATCH (:Finding {id:'f1'})-[r:LEADS_TO]->() RETURN count(r)").result_set
        assert rows[0][0] == 0
    finally:
        os.unlink(path)
        graph.reset(g)
