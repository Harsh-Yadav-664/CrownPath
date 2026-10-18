"""tests/test_format.py — asserts agent/format.py renders the ranked list, the
arrow-chain path, remediation text from the lifted taxonomy, and the choke-point
headline. Skips cleanly without a live FalkorDB server."""
import os

import pytest

from agent import format
from lib import tools


def _skip_if_no_db():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")


def test_format_answer_demo_graph():
    _skip_if_no_db()
    tools._g = None

    tools.ingest_findings("data/findings.json")
    remediations = tools.rank_by_reachability("asset:db")
    chokepoints = tools.choke_points("asset:db")

    output = format.format_answer(remediations, chokepoints)

    assert "## What to fix first" in output
    assert "## Choke point" in output
    assert "IDOR on /api/orders" in output
    assert "4 of 6" in output
    assert "including the highest-value one" in output
    assert "cvss" not in output.lower()
    # arrow-chain path rendering present
    assert "->" in output
    # remediation text pulled from data/taxonomy/remediation.tsv
    assert "object-level authorization" in output

    from lib import graph
    graph.reset(tools._get_graph())


def test_remediation_map_and_technique_map_load():
    remediation_map = format._load_remediation_map()
    assert remediation_map["idor"].startswith("Enforce object-level authorization")
    assert "csrf" not in remediation_map  # no row for csrf in remediation.tsv

    technique_map = format._load_finding_technique_map()
    assert technique_map["f:idor"] == "idor"
    assert technique_map["f:csrf"] == "csrf"
