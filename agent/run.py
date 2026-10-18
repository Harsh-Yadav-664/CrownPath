"""agent/run.py — question -> graph tools -> path-cited remediations (BUILD_SPEC.md
§8/§2, issue #18 / C2). Three ways to answer, in order of preference:
  1. Anthropic tool-use loop (ANTHROPIC_API_KEY set) -- run_with_llm().
  2. Any OpenAI-compatible provider via function calling (LLM_API_KEY/LLM_BASE_URL
     set) -- run_with_provider_llm(). Bridges the MCP tool schemas from
     crownpath_mcp/server.py (issue #20) into OpenAI function-calling format, so
     the agent still selects tools through the same schemas MCP exposes.
  3. --no-llm / no key at all: calls the tools directly and formats
     deterministically. Guarantees the P0 demo works offline.
Either way, agent/format.py (issue #19 / C3) renders the final answer; every
remediation cites a graph path, never CVSS.
"""
import argparse
import json
import os
import sys

from agent import format
from crownpath_mcp.server import TOOL_DEFS as MCP_TOOL_DEFS, TOOL_FUNCTIONS
from lib import tools

DEFAULT_QUESTION = "We have these findings. What should we fix first, and why?"
DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_LLM_MODEL = "gemini-2.5-flash"
MAX_TOOL_ITERATIONS = 8
SYSTEM_PROMPT_PATH = os.path.join("agent", "prompts", "system.md")
LAST_ANSWER_PATH = os.path.join("agent", "last_answer.json")


def _anthropic_tool_defs():
    """MCP_TOOL_DEFS (mcp.types.Tool) -> Anthropic's {name, description,
    input_schema} shape. Anthropic's shape is already a near-exact match."""
    return [
        {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
        for t in MCP_TOOL_DEFS
    ]


def _openai_tool_defs():
    """MCP_TOOL_DEFS (mcp.types.Tool) -> OpenAI-compatible function-calling shape:
    [{"type": "function", "function": {name, description, parameters}}, ...].
    Any OpenAI-compatible provider (Gemini, Groq, etc.) takes this same shape, so
    the agent selects tools through the schemas MCP exposes regardless of which
    provider answers."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            },
        }
        for t in MCP_TOOL_DEFS
    ]


def _graph_is_empty():
    g = tools._get_graph()
    from lib import graph
    result = graph.run(g, "MATCH (n) RETURN count(n)")
    return result.result_set[0][0] == 0


def _ensure_graph_loaded(findings_path="data/findings.json"):
    if _graph_is_empty():
        tools.ingest_findings(findings_path)


def run_no_llm(crown_jewel_id="asset:db", findings_path="data/findings.json"):
    """Deterministic fallback: no LLM, no network. Calls the tools directly and
    formats with agent/format.py. Guarantees the P0 demo works offline."""
    _ensure_graph_loaded(findings_path)

    remediations = tools.rank_by_reachability(crown_jewel_id)
    chokepoints = tools.choke_points(crown_jewel_id)

    answer = format.format_answer(remediations, chokepoints)

    _write_last_answer(remediations, chokepoints, answer)
    return answer


def _write_last_answer(remediations, chokepoints, answer_text):
    with open(LAST_ANSWER_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "remediations": remediations,
                "choke_points": chokepoints,
                "answer": answer_text,
            },
            f,
            indent=2,
        )


def run_with_llm(question, crown_jewel_id="asset:db", findings_path="data/findings.json"):
    """LLM tool-use loop via the Anthropic SDK. Requires ANTHROPIC_API_KEY."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ANTHROPIC_API_KEY is not set. Run with --no-llm for the deterministic "
            "offline path, or export ANTHROPIC_API_KEY to use the LLM tool-use loop."
        )
        sys.exit(1)

    model = os.environ.get("CROWNPATH_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    _ensure_graph_loaded(findings_path)

    messages = [{"role": "user", "content": question}]
    last_remediations = []
    last_chokepoints = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            tools=_anthropic_tool_defs(),
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            _write_last_answer(last_remediations, last_chokepoints, final_text)
            return final_text

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            fn = TOOL_FUNCTIONS[block.name]
            try:
                result = fn(**block.input)
            except Exception as exc:
                result = {"error": str(exc)}

            if block.name == "rank_by_reachability":
                last_remediations = result
            if block.name == "choke_points":
                last_chokepoints = result

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError(f"agent: exceeded {MAX_TOOL_ITERATIONS} tool-use iterations without a final answer")


def run_with_provider_llm(question, crown_jewel_id="asset:db", findings_path="data/findings.json", client=None):
    """Provider-agnostic LLM tool-use loop over any OpenAI-compatible chat API
    (Gemini, Groq, or anything else that speaks the OpenAI chat-completions
    shape). Configured via LLM_BASE_URL / LLM_MODEL / LLM_API_KEY (see
    .env.example for working Gemini and Groq defaults). Bridges the MCP tool
    schemas (crownpath_mcp/server.py, issue #20) into OpenAI function-calling
    format via _openai_tool_defs(), so the agent still selects tools through the
    same schemas MCP exposes, and dispatches calls through the same
    TOOL_FUNCTIONS the MCP server itself calls.

    `client` is injectable for testing (an object with a `.chat.completions.create`
    method matching the OpenAI SDK shape); when None, builds a real `openai.OpenAI`
    client from the LLM_* env vars.
    """
    if client is None:
        import openai

        base_url = os.environ.get("LLM_BASE_URL")
        api_key = os.environ.get("LLM_API_KEY")
        if not base_url or not api_key:
            print(
                "LLM_BASE_URL and LLM_API_KEY must both be set for the provider-agnostic "
                "LLM path. Run with --no-llm for the deterministic offline path, or set "
                "ANTHROPIC_API_KEY to use the Anthropic path instead. See .env.example "
                "for working Gemini/Groq defaults."
            )
            sys.exit(1)
        client = openai.OpenAI(base_url=base_url, api_key=api_key)

    model = os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL)

    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    _ensure_graph_loaded(findings_path)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    last_remediations = []
    last_chokepoints = []
    openai_tool_defs = _openai_tool_defs()

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=openai_tool_defs,
        )

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            final_text = message.content or ""
            _write_last_answer(last_remediations, last_chokepoints, final_text)
            return final_text

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            fn = TOOL_FUNCTIONS[tc.function.name]
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                result = fn(**args)
            except Exception as exc:
                result = {"error": str(exc)}

            if tc.function.name == "rank_by_reachability":
                last_remediations = result
            if tc.function.name == "choke_points":
                last_chokepoints = result

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    raise RuntimeError(f"agent: exceeded {MAX_TOOL_ITERATIONS} tool-use iterations without a final answer")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--crown-jewel", default="asset:db")
    parser.add_argument("--findings", default="data/findings.json")
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    if args.no_llm:
        answer = run_no_llm(args.crown_jewel, args.findings)
    elif os.environ.get("ANTHROPIC_API_KEY"):
        answer = run_with_llm(args.question, args.crown_jewel, args.findings)
    elif os.environ.get("LLM_API_KEY") and os.environ.get("LLM_BASE_URL"):
        answer = run_with_provider_llm(args.question, args.crown_jewel, args.findings)
    else:
        answer = run_no_llm(args.crown_jewel, args.findings)

    print(answer)


if __name__ == "__main__":
    main()
