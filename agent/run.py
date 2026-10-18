"""agent/run.py — question -> graph tools -> path-cited remediations (BUILD_SPEC.md
§8/§2, issue #18 / C2). Registers lib.tools' five functions as Anthropic tool
definitions and runs the standard tool-use loop, OR (--no-llm / no API key) calls
the tools directly and formats deterministically. Either way, agent/format.py
(issue #19 / C3) renders the final answer; every remediation cites a graph path,
never CVSS.
"""
import argparse
import json
import os
import sys

from agent import format
from lib import tools

DEFAULT_QUESTION = "We have these findings. What should we fix first, and why?"
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TOOL_ITERATIONS = 8
SYSTEM_PROMPT_PATH = os.path.join("agent", "prompts", "system.md")
LAST_ANSWER_PATH = os.path.join("agent", "last_answer.json")

# Tool definitions derived from the frozen lib.tools signatures (issue #6).
TOOL_DEFS = [
    {
        "name": "ingest_findings",
        "description": "Load a findings document into the FalkorDB graph.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "default": "data/findings.json"}},
        },
    },
    {
        "name": "find_attack_paths",
        "description": "Find attack paths from an anonymous entry point to a crown-jewel asset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "crown_jewel_id": {"type": ["string", "null"]},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "shortest_path",
        "description": "Find the highest-value path between two arbitrary graph nodes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_id": {"type": "string"},
                "to_id": {"type": "string"},
            },
            "required": ["from_id", "to_id"],
        },
    },
    {
        "name": "rank_by_reachability",
        "description": "Rank findings by how they sit on crown-jewel attack paths, each citing a path.",
        "input_schema": {
            "type": "object",
            "properties": {"crown_jewel_id": {"type": ["string", "null"]}},
        },
    },
    {
        "name": "choke_points",
        "description": "Find the choke-point finding: the single vulnerability that lies on the most crown-jewel attack paths.",
        "input_schema": {
            "type": "object",
            "properties": {"crown_jewel_id": {"type": ["string", "null"]}},
        },
    },
]

TOOL_FUNCTIONS = {
    "ingest_findings": tools.ingest_findings,
    "find_attack_paths": tools.find_attack_paths,
    "shortest_path": tools.shortest_path,
    "rank_by_reachability": tools.rank_by_reachability,
    "choke_points": tools.choke_points,
}


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
            tools=TOOL_DEFS,
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--crown-jewel", default="asset:db")
    parser.add_argument("--findings", default="data/findings.json")
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()

    if args.no_llm or not os.environ.get("ANTHROPIC_API_KEY"):
        answer = run_no_llm(args.crown_jewel, args.findings)
    else:
        answer = run_with_llm(args.question, args.crown_jewel, args.findings)

    print(answer)


if __name__ == "__main__":
    main()
