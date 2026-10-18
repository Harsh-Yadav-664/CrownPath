"""tests/test_tools.py — exercises each lib/tools.py function against the live
demo graph. Skips cleanly without a live FalkorDB server."""
import os

import pytest

from lib import tools


def _skip_if_no_db():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")


def test_ingest_find_shortest_rank_and_choke_points_gap():
    _skip_if_no_db()
    tools._g = None  # fresh singleton per test

    result = tools.ingest_findings("data/findings.json")
    assert result["nodes"] > 0
    assert result["edges"] > 0
    assert result["skipped_attack_edges"] == 0

    paths = tools.find_attack_paths("asset:db")
    assert len(paths) == 6
    for p in paths:
        assert p["crown_jewel_id"] == "asset:db"
        assert p["score"] == 0.0  # find_attack_paths does not score; rank_by_reachability does

    sp = tools.shortest_path("ep:search", "asset:db")
    assert sp is not None
    assert sp["length"] == 6

    remediations = tools.rank_by_reachability("asset:db")
    assert len(remediations) > 0
    ranks = [r["rank"] for r in remediations]
    assert ranks == sorted(ranks)
    for r in remediations:
        assert r["cited_path"]["steps"]  # non-empty cited path
        assert "cvss" not in r["reason"].lower()

    # choke_points: wired up by #21/D2 (lib/chokepoints.py)
    cps = tools.choke_points("asset:db")
    assert cps[0]["finding_id"] == "f:idor"
    assert cps[0]["paths_severed"] == 4
    assert cps[0]["paths_total"] == 6

    from lib import graph
    graph.reset(tools._get_graph())
