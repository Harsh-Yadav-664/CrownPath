"""tests/test_queries_7b.py — asserts query 7b scoring/ranking on the frozen demo
graph. Skips cleanly without a live FalkorDB server."""
import os

import pytest

from lib import graph, queries, seed_taxonomy


def _connect_or_skip():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    try:
        return graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")


def test_rank_paths_is_deterministic_and_top_path_is_short_idor():
    g = _connect_or_skip()
    seed_taxonomy.load_all(g, "data/findings.json")

    ranked_once = queries.rank_paths(g, "asset:db")
    ranked_twice = queries.rank_paths(g, "asset:db")

    assert len(ranked_once) == 6
    for p in ranked_once:
        assert p["score"] > 0

    scores_once = [round(p["score"], 6) for p in ranked_once]
    scores_twice = [round(p["score"], 6) for p in ranked_twice]
    assert scores_once == scores_twice  # deterministic
    assert scores_once == sorted(scores_once, reverse=True)  # score DESC

    top = ranked_once[0]
    top_ids = [s["id"] for s in top["steps"] if s["kind"] == "node"]
    assert top["length"] == 6
    assert "f:idor" in top["finding_ids"]
    assert top_ids[0] in {"ep:search", "ep:go", "ep:login"}  # short user-session entries

    graph.reset(g)


def test_shortest_path_search_to_db():
    g = _connect_or_skip()
    seed_taxonomy.load_all(g, "data/findings.json")

    sp = queries.shortest_path(g, "ep:search", "asset:db")
    assert sp is not None
    assert sp["length"] == 6

    node_ids = [s["id"] for s in sp["steps"] if s["kind"] == "node"]
    assert node_ids == ["ep:search", "f:xss", "id:user", "asset:api", "ep:orders", "f:idor", "asset:db"]

    graph.reset(g)
