"""tests/test_agent_provider.py — unit-tests agent.run.run_with_provider_llm with
a MOCKED OpenAI-compatible client (no network, no API key, no live LLM call --
see issue #18's comment for what still needs live verification with a real
Gemini/Groq key). Still needs a live FalkorDB (the graph tools really run); it
is only the LLM call itself that is mocked."""
import json
import os
from types import SimpleNamespace

import pytest

from agent import run as agent_run
from lib import tools


def _skip_if_no_db():
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")


class _FakeToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.function = SimpleNamespace(name=name, arguments=json.dumps(arguments))


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeResponse:
    def __init__(self, message):
        self.choices = [SimpleNamespace(message=message)]


class _FakeChatCompletions:
    """Returns a scripted sequence of responses, one per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=_FakeChatCompletions(responses))


def test_openai_tool_defs_bridge_mcp_schemas():
    defs = agent_run._openai_tool_defs()
    names = {d["function"]["name"] for d in defs}
    assert names == {
        "ingest_findings", "find_attack_paths", "shortest_path",
        "rank_by_reachability", "choke_points",
    }
    for d in defs:
        assert d["type"] == "function"
        assert "parameters" in d["function"]


def test_run_with_provider_llm_mocked_tool_call_then_final_answer():
    _skip_if_no_db()
    tools._g = None
    tools.ingest_findings("data/findings.json")

    # Turn 1: model asks for choke_points. Turn 2: model answers with final text.
    responses = [
        _FakeResponse(_FakeMessage(
            content=None,
            tool_calls=[_FakeToolCall("call_1", "choke_points", {"crown_jewel_id": "asset:db"})],
        )),
        _FakeResponse(_FakeMessage(content="Fix the IDOR first.", tool_calls=None)),
    ]
    client = _FakeClient(responses)

    answer = agent_run.run_with_provider_llm(
        "What should we fix first?", "asset:db", "data/findings.json", client=client
    )

    assert answer == "Fix the IDOR first."
    assert client.chat.completions.calls[0]["tools"] == agent_run._openai_tool_defs()

    # the tool call was actually dispatched to the real lib.tools.choke_points
    # (not mocked) and its result was fed back as a tool message
    second_call_messages = client.chat.completions.calls[1]["messages"]
    tool_message = next(m for m in second_call_messages if m.get("role") == "tool")
    result = json.loads(tool_message["content"])
    assert result[0]["finding_id"] == "f:idor"

    assert os.path.exists(agent_run.LAST_ANSWER_PATH)

    from lib import graph
    graph.reset(tools._get_graph())


def test_run_with_provider_llm_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        agent_run.run_with_provider_llm("question", "asset:db", "data/findings.json", client=None)
