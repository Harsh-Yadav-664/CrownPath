"""tests/test_mcp_server.py — drives crownpath_mcp/server.py through an
in-process MCP client session (mcp.shared.memory), verifying tool listing and a
tool call return the live demo-graph results. Skips cleanly without a live
FalkorDB server."""
import json
import os

import pytest


@pytest.mark.asyncio
async def test_mcp_server_lists_tools_and_calls_choke_points():
    import mcp.shared.memory as mem
    from crownpath_mcp.server import server
    from lib import graph, seed_taxonomy

    # lib.graph loads .env on import; check FALKORDB_HOST only after that import.
    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")

    try:
        g = graph.connect()
    except Exception as exc:
        pytest.skip(f"FalkorDB unreachable: {exc}")

    seed_taxonomy.load_all(g, "data/findings.json")

    async with mem.create_connected_server_and_client_session(server) as session:
        await session.initialize()

        tools_result = await session.list_tools()
        tool_names = {t.name for t in tools_result.tools}
        assert tool_names == {
            "ingest_findings", "find_attack_paths", "shortest_path",
            "rank_by_reachability", "choke_points",
        }

        result = await session.call_tool("choke_points", {"crown_jewel_id": "asset:db"})
        data = json.loads(result.content[0].text)
        assert data[0]["finding_id"] == "f:idor"
        assert data[0]["paths_severed"] == 4
        assert data[0]["paths_total"] == 6

        result2 = await session.call_tool("find_attack_paths", {"crown_jewel_id": "asset:db"})
        paths = json.loads(result2.content[0].text)
        assert len(paths) == 6

    graph.reset(g)
