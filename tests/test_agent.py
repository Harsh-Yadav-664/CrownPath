"""tests/test_agent.py — runs the --no-llm path (agent.run.run_no_llm) end to end
on the demo graph. Skips cleanly without a live FalkorDB server."""
import json
import os

import pytest

from agent import run as agent_run
from lib import tools


def _skip_if_no_db():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")


def test_run_no_llm_end_to_end():
    _skip_if_no_db()
    tools._g = None

    answer = agent_run.run_no_llm("asset:db", "data/findings.json")

    assert "## What to fix first" in answer
    assert "## Choke point" in answer
    assert "IDOR" in answer
    assert "4 of 6" in answer
    assert "cvss" not in answer.lower()

    assert os.path.exists(agent_run.LAST_ANSWER_PATH)
    with open(agent_run.LAST_ANSWER_PATH, "r", encoding="utf-8") as f:
        last = json.load(f)
    assert last["remediations"][0]["cited_path"]["steps"]
    assert last["choke_points"][0]["finding_id"] == "f:idor"
    assert last["answer"] == answer

    from lib import graph
    graph.reset(tools._get_graph())
