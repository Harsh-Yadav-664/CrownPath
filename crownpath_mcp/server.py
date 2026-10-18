"""crownpath_mcp/server.py — MCP server exposing the graph tools over stdio
(BUILD_SPEC.md §8, issue #20 / D1).

**Package rename note (resolves a blocker flagged in docs/HANDOFF.md):** this
package was originally specified at `mcp/server.py` (BUILD_SPEC.md §12), but that
name collides with the third-party `mcp` SDK itself -- whenever the repo root is
on `sys.path` (the normal case for `python -m mcp.server`, pytest, or any script
run from repo root), `import mcp` resolved to OUR OWN package, never the SDK, so
`from mcp.server.stdio import stdio_server` failed with
`ModuleNotFoundError: No module named 'mcp.server.stdio'; 'mcp.server' is not a
package` (confirmed live). Renamed this package to `crownpath_mcp/` so `import
mcp` inside it reaches the real SDK. Entry point is now
`python -m crownpath_mcp.server` (was `python -m mcp.server`).

Exposes the five lib.tools functions (#6/#17): ingest_findings,
find_attack_paths, shortest_path, rank_by_reachability, choke_points -- plus a sixth,
whats_changed (P2 memory layer, issue #23 / Track 02). Each tool's
input schema mirrors its Python signature; each handler calls the matching
lib.tools function and returns the result as JSON text content.
"""
import asyncio
import json

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from lib import tools

SERVER_NAME = "crownpath"

TOOL_DEFS = [
    types.Tool(
        name="ingest_findings",
        description="Load a findings document into the FalkorDB graph.",
        inputSchema={
            "type": "object",
            "properties": {"path": {"type": "string", "default": "data/findings.json"}},
        },
    ),
    types.Tool(
        name="find_attack_paths",
        description="Find attack paths from an anonymous entry point to a crown-jewel asset.",
        inputSchema={
            "type": "object",
            "properties": {
                "crown_jewel_id": {"type": ["string", "null"]},
                "limit": {"type": "integer", "default": 10},
            },
        },
    ),
    types.Tool(
        name="shortest_path",
        description="Find the highest-value path between two arbitrary graph nodes.",
        inputSchema={
            "type": "object",
            "properties": {
                "from_id": {"type": "string"},
                "to_id": {"type": "string"},
            },
            "required": ["from_id", "to_id"],
        },
    ),
    types.Tool(
        name="rank_by_reachability",
        description="Rank findings by how they sit on crown-jewel attack paths, each citing a path.",
        inputSchema={
            "type": "object",
            "properties": {"crown_jewel_id": {"type": ["string", "null"]}},
        },
    ),
    types.Tool(
        name="choke_points",
        description=(
            "Find the choke-point finding: the single vulnerability that lies on "
            "the most crown-jewel attack paths."
        ),
        inputSchema={
            "type": "object",
            "properties": {"crown_jewel_id": {"type": ["string", "null"]}},
        },
    ),
    types.Tool(
        name="whats_changed",
        description=(
            "Memory across scans: diff two recorded scans (default scan-1 -> scan-2). "
            "Use ONLY when asked what changed or regressed between scans; not for "
            "'what to fix first'. Returns findings added/removed, assets that regressed "
            "(a newly confirmed finding opened new paths to the crown jewel), and the "
            "crown-jewel path count in each scan."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "since": {"type": "string", "default": "scan-1"},
                "until": {"type": "string", "default": "scan-2"},
                "crown_jewel_id": {"type": "string", "default": "asset:db"},
            },
        },
    ),
]

TOOL_FUNCTIONS = {
    "ingest_findings": tools.ingest_findings,
    "find_attack_paths": tools.find_attack_paths,
    "shortest_path": tools.shortest_path,
    "rank_by_reachability": tools.rank_by_reachability,
    "choke_points": tools.choke_points,
    "whats_changed": tools.whats_changed,
}

server = Server(SERVER_NAME)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOL_DEFS


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name not in TOOL_FUNCTIONS:
        raise ValueError(f"unknown tool: {name!r}")

    fn = TOOL_FUNCTIONS[name]
    result = fn(**arguments)
    return [types.TextContent(type="text", text=json.dumps(result))]


async def _main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
