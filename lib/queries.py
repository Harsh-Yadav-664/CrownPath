"""lib/queries.py — the queries that ARE the product (BUILD_SPEC.md §7).

Issue #15 (B4) adds find_attack_paths (7a); issue #16 (B5) adds the 7b scorer to
this same file. Uses the EXACT verified Cypher recorded in docs/graph-model.md ->
"Verified live Cypher" (issue #10 spike). Returns the frozen AttackPath shape
from lib/tools.py (issue #6).

Known limitation (recorded in docs/graph-model.md and BUILD_SPEC §7): FalkorDB's
`LIMIT` does not correctly bound variable-length path enumeration, so this module
always enumerates all paths with Cypher ORDER BY only, then slices in Python.
"""
from lib import graph

# verified traversal edge set (schema.ATTACK_EDGES), issue #10 spike confirmed this
# form live, exactly as recorded in docs/graph-model.md.
_ATTACK_EDGE_PATTERN = "EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO"

_7A_ALL_JEWELS = f"""
MATCH path = (e:Endpoint {{auth_required:false}})
      -[:{_ATTACK_EDGE_PATTERN}*1..8]->
      (j:Asset {{is_crown_jewel:true}})
RETURN path
ORDER BY length(path) ASC
"""

_7A_ONE_JEWEL = f"""
MATCH path = (e:Endpoint {{auth_required:false}})
      -[:{_ATTACK_EDGE_PATTERN}*1..8]->
      (j:Asset {{is_crown_jewel:true, id:$jid}})
RETURN path
ORDER BY length(path) ASC
"""


def _node_display(node):
    label = node.labels[0] if node.labels else "Node"
    props = node.properties
    if label == "Finding":
        return f"Finding: {props.get('title', props.get('id'))}"
    if label == "Asset":
        return f"Asset: {props.get('name', props.get('id'))}"
    if label == "Endpoint":
        return f"Endpoint: {props.get('method', '')} {props.get('url', props.get('id'))}".strip()
    if label == "Identity":
        return f"Identity: {props.get('role', props.get('id'))}"
    if label == "Technique":
        return f"Technique: {props.get('name', props.get('id'))}"
    return f"{label}: {props.get('id', '')}"


def _path_to_attack_path(path, crown_jewel_id):
    steps = []
    nodes = path.nodes()
    edges = path.edges()
    finding_ids = []

    for i, node in enumerate(nodes):
        label = node.labels[0] if node.labels else ""
        node_id = node.properties.get("id", "")
        steps.append({
            "kind": "node",
            "label": label,
            "id": node_id,
            "display": _node_display(node),
        })
        if label == "Finding":
            finding_ids.append(node_id)
        if i < len(edges):
            edge = edges[i]
            steps.append({
                "kind": "edge",
                "label": edge.relation,
                "id": "",
                "display": edge.relation,
            })

    return {
        "steps": steps,
        "length": path.edge_count(),
        "score": 0.0,  # filled by issue #16's 7b scorer
        "finding_ids": finding_ids,
        "crown_jewel_id": crown_jewel_id,
    }


def find_attack_paths(g, crown_jewel_id=None, limit=10):
    """Query 7a: anonymous-entry -> crown-jewel attack paths, shortest-first.

    Always enumerates all matching paths in Cypher (ORDER BY only, no LIMIT --
    see module docstring) then slices to `limit` in Python."""
    if crown_jewel_id is None:
        result = graph.run(g, _7A_ALL_JEWELS)
    else:
        result = graph.run(g, _7A_ONE_JEWEL, {"jid": crown_jewel_id})

    attack_paths = []
    for row in result.result_set:
        path = row[0]
        jid = crown_jewel_id
        if jid is None:
            # last node in the path is the crown jewel
            jid = path.nodes()[-1].properties.get("id", "")
        attack_paths.append(_path_to_attack_path(path, jid))

    return attack_paths[:limit]
