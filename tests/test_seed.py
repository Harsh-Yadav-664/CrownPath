"""tests/test_seed.py — asserts Technique and CHAINS_TO counts after seeding the
taxonomy. Skips cleanly without a live FalkorDB server."""
import os

import pytest

from lib import graph, seed_taxonomy


def _connect_or_skip():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    try:
        return graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")


DEMO_TECHNIQUE_IDS = [
    "xss", "open-redirect", "bfla", "idor", "ssrf", "sqli", "mass-assignment", "csrf",
]


def test_seed_creates_techniques_and_chains():
    g = _connect_or_skip()
    graph.reset(g)
    graph.init_schema(g)

    result = seed_taxonomy.seed(g)
    assert result["chains"] == 24
    assert result["techniques"] > 0

    rows = graph.run(g, "MATCH (t:Technique) RETURN count(t)").result_set
    assert rows[0][0] == result["techniques"]

    rows = graph.run(g, "MATCH ()-[r:CHAINS_TO]->() RETURN count(r)").result_set
    assert rows[0][0] == 24

    rows = graph.run(
        g,
        "MATCH (t:Technique) WHERE t.id IN $ids RETURN t.id",
        {"ids": DEMO_TECHNIQUE_IDS},
    ).result_set
    found = {row[0] for row in rows}
    assert found == set(DEMO_TECHNIQUE_IDS)

    graph.reset(g)
