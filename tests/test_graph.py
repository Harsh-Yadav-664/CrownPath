"""tests/test_graph.py — connects via .env, inits schema, resets, runs a smoke query.

Skips (does not fail) when FALKORDB_HOST is unset or the server is unreachable, so
CI/clean clones without a live DB still pass the rest of the suite."""
import os

import pytest

from lib import graph


def _connect_or_skip():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    try:
        return graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")


def test_connect_init_schema_reset_smoke_query():
    g = _connect_or_skip()

    graph.init_schema(g)
    graph.init_schema(g)  # idempotent: must not raise the second time

    graph.reset(g)

    result = graph.run(g, "RETURN 1")
    rows = result.result_set
    assert rows == [[1]]
