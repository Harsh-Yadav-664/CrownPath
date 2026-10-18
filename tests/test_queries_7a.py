"""tests/test_queries_7a.py — asserts find_attack_paths against the frozen demo
scenario (docs/demo-scenario.md). Skips cleanly without a live FalkorDB server."""
import os

import pytest

from lib import graph, queries, seed_taxonomy

EXPECTED_PATHS = {
    ("ep:search", "f:xss", "id:user", "asset:api", "ep:orders", "f:idor", "asset:db"),
    ("ep:go", "f:redirect", "id:user", "asset:api", "ep:orders", "f:idor", "asset:db"),
    ("ep:login", "f:authbypass", "id:user", "asset:api", "ep:orders", "f:idor", "asset:db"),
    ("ep:metrics", "f:ssrf", "asset:admin", "asset:api", "ep:orders", "f:idor", "asset:db"),
    ("ep:metrics", "f:ssrf", "asset:admin", "ep:adminapi", "f:sqli", "asset:db"),
    ("ep:metrics", "f:ssrf", "asset:admin", "ep:adminapi", "f:massassign", "id:admin", "asset:db"),
}

ANON_ENTRIES = {"ep:search", "ep:go", "ep:login", "ep:metrics"}


def _connect_or_skip():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    try:
        return graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")


def test_find_attack_paths_matches_frozen_demo_scenario():
    g = _connect_or_skip()
    seed_taxonomy.load_all(g, "data/findings.json")

    paths = queries.find_attack_paths(g, "asset:db")
    assert len(paths) == 6

    actual = set()
    for p in paths:
        node_ids = tuple(s["id"] for s in p["steps"] if s["kind"] == "node")
        assert node_ids[-1] == "asset:db"
        assert node_ids[0] in ANON_ENTRIES
        actual.add(node_ids)

    assert actual == EXPECTED_PATHS

    idor_count = sum(1 for p in paths if "f:idor" in p["finding_ids"])
    assert idor_count == 4

    csrf_count = sum(1 for p in paths if "f:csrf" in p["finding_ids"])
    assert csrf_count == 0

    graph.reset(g)
