# CrownPath MCP server

A thin stdio MCP server exposing CrownPath's five graph tools (`lib/tools.py`) so
an agent selects them through MCP (BUILD_SPEC.md §8, issue #20 / D1), directly
hitting Track 01's "tool selection through MCP" focus.

**Naming note:** this package is `crownpath_mcp/`, not `mcp/`. The original spec
(BUILD_SPEC.md §12) named it `mcp/server.py`, but that collides with the
third-party `mcp` Python SDK itself — see `docs/HANDOFF.md` for the full
writeup of the import collision this caused and why it was renamed.

## Tools exposed

| Tool | Mirrors |
|---|---|
| `ingest_findings` | `lib.tools.ingest_findings(path="data/findings.json")` |
| `find_attack_paths` | `lib.tools.find_attack_paths(crown_jewel_id=None, limit=10)` |
| `shortest_path` | `lib.tools.shortest_path(from_id, to_id)` |
| `rank_by_reachability` | `lib.tools.rank_by_reachability(crown_jewel_id=None)` |
| `choke_points` | `lib.tools.choke_points(crown_jewel_id=None)` |

Each tool's input schema mirrors its Python signature; each call returns the
result as JSON text content (the same plain-dict shapes `lib/tools.py` returns).

## Running it

```bash
python -m crownpath_mcp.server
```

This starts a stdio MCP server — it reads JSON-RPC requests from stdin and
writes responses to stdout, so it is meant to be launched by an MCP client, not
run interactively.

## Registering with an MCP client

Most MCP clients (Claude Desktop, etc.) take a JSON config naming the launch
command. From the repo root:

```json
{
  "mcpServers": {
    "crownpath": {
      "command": "python",
      "args": ["-m", "crownpath_mcp.server"],
      "cwd": "/absolute/path/to/crownpath",
      "env": {
        "FALKORDB_HOST": "...",
        "FALKORDB_PORT": "...",
        "FALKORDB_USERNAME": "...",
        "FALKORDB_PASSWORD": "...",
        "FALKORDB_SSL": "...",
        "CROWNPATH_GRAPH": "crownpath"
      }
    }
  }
}
```

(The server reads its FalkorDB connection from the environment the same way
`lib/graph.py` always does — point it at your own `.env` values, Cloud or local
Docker, same as any other entry point in this repo.)

## Alternative: the official FalkorDB MCP server

FalkorDB ships its own official MCP server
([`FalkorDB/FalkorDB-MCPServer`](https://github.com/FalkorDB/FalkorDB-MCPServer),
see docs.falkordb.com/genai-tools/mcpserver) exposing generic Cypher/graph-
management tools. It is a good option for raw Cypher access to the graph, but it
does not know about CrownPath's domain operations (attack-path traversal,
choke-point ranking, etc.) — that is what this thin wrapper over `lib/tools.py`
adds.
