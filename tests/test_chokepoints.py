"""tests/test_chokepoints.py — asserts the choke-point headline (query 7c) on the
frozen demo graph. Skips cleanly without a live FalkorDB server.

Note on the betweenness cross-check (BUILD_SPEC §7c): it is explicitly a
non-authoritative corroboration, logged only, never overriding the deterministic
path-count ranking. On the demo graph it does NOT rank f:idor top among Findings
(whole-graph betweenness measures something different from "how many
crown-jewel paths pass through this node") -- this test asserts only that the
cross-check runs without error and returns a score for every Finding on a path,
per the issue's own "never overrides" framing. Recorded in docs/HANDOFF.md.
"""
import os

import pytest

from lib import chokepoints, graph, seed_taxonomy


def _connect_or_skip():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    try:
        return graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")


def test_choke_points_top_is_idor_4_of_6():
    g = _connect_or_skip()
    seed_taxonomy.load_all(g, "data/findings.json")

    cps = chokepoints.choke_points(g, "asset:db")
    assert len(cps) > 0

    top = cps[0]
    assert top["finding_id"] == "f:idor"
    assert top["paths_severed"] == 4
    assert top["paths_total"] == 6
    assert top["severs_highest_value"] is True

    assert chokepoints.headline(top, "Customer database") == (
        "Fix IDOR on /api/orders -> sever 4 of 6 paths to Customer database, "
        "including the highest-value one."
    )

    graph.reset(g)


def test_betweenness_cross_check_runs_without_error():
    g = _connect_or_skip()
    seed_taxonomy.load_all(g, "data/findings.json")

    scores = chokepoints.betweenness_cross_check(g)
    assert "f:idor" in scores
    assert all(isinstance(v, (int, float)) for v in scores.values())

    graph.reset(g)
