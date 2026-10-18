"""tests/test_memory.py -- issue #23: two scans load with distinct ids, and
whats_changed reports f:idor as newly added and asset:api as regressed."""
import os

import pytest

from lib import graph, memory


@pytest.fixture
def g():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    try:
        handle = graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")
    yield handle
    graph.reset(handle)


def test_whats_changed_reports_idor_added_and_api_regressed(g):
    memory.load_demo_scans(g)
    change = memory.whats_changed(g, "scan-1", "scan-2")

    assert [f["finding_id"] for f in change["added"]] == ["f:idor"]
    assert change["removed"] == []
    assert change["regressed"] == [
        {"asset_id": "asset:api", "asset_name": "Orders API",
         "finding_id": "f:idor", "new_paths": 4}
    ]
    assert change["paths"] == {"since": 2, "until": 6}


def test_reversed_diff_reports_removal_not_regression(g):
    memory.load_demo_scans(g)
    change = memory.whats_changed(g, "scan-2", "scan-1")

    assert [f["finding_id"] for f in change["removed"]] == ["f:idor"]
    assert change["added"] == []
    assert change["regressed"] == []


def test_record_scan_is_idempotent(g):
    memory.load_demo_scans(g)
    memory.record_scan(g, "scan-2", memory.SCAN2_PATH)
    rows = graph.run(g, "MATCH (f:Finding {id:'f:idor'}) RETURN f.scans, f.first_seen").result_set
    assert rows == [[["scan-2"], "scan-2"]]
