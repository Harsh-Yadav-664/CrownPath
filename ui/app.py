"""ui/app.py — minimal FastAPI backend for the path-rendering UI (BUILD_SPEC.md
§8/§9, issue #22 / D3). The PRIMARY demo visual: no localhost:3000 FalkorDB
browser exists for the Cloud dev DB, and this same page is served by the live
deployment (#25/E3). Reads the graph through lib.graph (.env connection), so it
works against FalkorDB Cloud or any FalkorDB a judge points it at.

Run: uvicorn ui.app:app --port 8000
"""
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lib import graph, tools

app = FastAPI(title="CrownPath")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _public_attack_path(path):
    """Strip internal keys before the path crosses the HTTP boundary."""
    return {
        "steps": path["steps"],
        "length": path["length"],
        "score": path["score"],
        "finding_ids": path["finding_ids"],
        "crown_jewel_id": path["crown_jewel_id"],
    }


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/graph")
def get_graph():
    """The full demo graph as Cytoscape elements: {nodes, edges}."""
    g = tools._get_graph()

    node_rows = graph.run(
        g, "MATCH (n) RETURN labels(n)[0] AS label, n.id AS id, properties(n) AS props"
    ).result_set
    nodes = []
    for label, node_id, props in node_rows:
        display = props.get("name") or props.get("title") or props.get("url") or node_id
        nodes.append({"data": {"id": node_id, "label": display, "type": label}})

    edge_rows = graph.run(
        g,
        """
        MATCH (a)-[r]->(b)
        RETURN a.id AS source, b.id AS target, type(r) AS label
        """,
    ).result_set
    edges = [
        {"data": {"source": source, "target": target, "label": label}}
        for source, target, label in edge_rows
    ]

    return {"nodes": nodes, "edges": edges}


@app.get("/api/paths")
def get_paths(crown_jewel: str = "asset:db"):
    paths = tools.find_attack_paths(crown_jewel_id=crown_jewel)
    return {"paths": [_public_attack_path(p) for p in paths], "crown_jewel": crown_jewel}


@app.get("/api/chokepoints")
def get_chokepoints(crown_jewel: str = "asset:db"):
    from lib import chokepoints as cp_module

    choke_points = tools.choke_points(crown_jewel_id=crown_jewel)
    headline = None
    if choke_points:
        g = tools._get_graph()
        jewel_row = graph.run(g, "MATCH (a:Asset {id:$id}) RETURN a.name", {"id": crown_jewel}).result_set
        jewel_name = jewel_row[0][0] if jewel_row else crown_jewel
        headline = cp_module.headline(choke_points[0], jewel_name)

    return {"choke_points": choke_points, "headline": headline, "crown_jewel": crown_jewel}
