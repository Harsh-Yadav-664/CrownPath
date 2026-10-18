"""lib/ingest.py — findings.json -> FalkorDB nodes/edges (BUILD_SPEC.md §5/§6,
issue #13 / B2). Enforces the proof-discipline rule: only `status=='confirmed'`
findings get the attack edges GRANTS/LEADS_TO.

Canonical load order: init_schema(g) -> seed taxonomy (lib.seed_taxonomy.seed) ->
ingest(g). This module assumes Techniques are already seeded; an unmatched
technique_id is a hard error (see docs/findings.schema.json).
"""
import argparse
import json

import jsonschema

from lib import graph

SCHEMA_PATH = "docs/findings.schema.json"


def _load_and_validate(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_doc = json.load(f)
    jsonschema.validate(data, schema_doc)
    return data


def ingest(g, path="data/findings.json", reset=True):
    """Load, validate, and ingest a findings document into the graph.

    Returns {"nodes": int, "edges": int, "skipped_attack_edges": int}."""
    data = _load_and_validate(path)

    if reset:
        graph.reset(g)

    nodes = 0
    edges = 0
    skipped_attack_edges = 0

    # ---- nodes
    for asset in data.get("assets", []):
        graph.run(
            g,
            "MERGE (n:Asset {id:$id}) SET n += $props",
            {"id": asset["id"], "props": asset},
        )
        nodes += 1

    for endpoint in data.get("endpoints", []):
        props = {k: v for k, v in endpoint.items() if k != "asset_id"}
        graph.run(
            g,
            "MERGE (n:Endpoint {id:$id}) SET n += $props",
            {"id": endpoint["id"], "props": props},
        )
        nodes += 1

    for identity in data.get("identities", []):
        graph.run(
            g,
            "MERGE (n:Identity {id:$id}) SET n += $props",
            {"id": identity["id"], "props": identity},
        )
        nodes += 1

    fk_fields = {"endpoint_id", "technique_id", "grants_identity_id", "leads_to_asset_id"}
    for finding in data.get("findings", []):
        props = {k: v for k, v in finding.items() if k not in fk_fields}
        graph.run(
            g,
            "MERGE (n:Finding {id:$id}) SET n += $props",
            {"id": finding["id"], "props": props},
        )
        nodes += 1

    # ---- structural edges
    for endpoint in data.get("endpoints", []):
        graph.run(
            g,
            """
            MATCH (a:Asset {id:$asset_id}), (e:Endpoint {id:$endpoint_id})
            MERGE (a)-[:EXPOSES]->(e)
            """,
            {"asset_id": endpoint["asset_id"], "endpoint_id": endpoint["id"]},
        )
        edges += 1

    for finding in data.get("findings", []):
        graph.run(
            g,
            """
            MATCH (e:Endpoint {id:$endpoint_id}), (f:Finding {id:$finding_id})
            MERGE (e)-[:HAS_FINDING]->(f)
            """,
            {"endpoint_id": finding["endpoint_id"], "finding_id": finding["id"]},
        )
        edges += 1

        technique_id = finding["technique_id"]
        result = graph.run(
            g,
            """
            MATCH (f:Finding {id:$finding_id}), (t:Technique {id:$technique_id})
            MERGE (f)-[:INSTANCE_OF]->(t)
            RETURN t.id
            """,
            {"finding_id": finding["id"], "technique_id": technique_id},
        )
        if not result.result_set:
            raise RuntimeError(
                f"ingest: finding {finding['id']!r} references technique_id "
                f"{technique_id!r} which does not exist in the graph. "
                f"Run lib.seed_taxonomy.seed(g) before ingest()."
            )
        edges += 1

    for conn in data.get("connections", []):
        graph.run(
            g,
            """
            MATCH (a:Asset {id:$from_id}), (b:Asset {id:$to_id})
            MERGE (a)-[:CONNECTS_TO]->(b)
            """,
            {"from_id": conn["from_asset_id"], "to_id": conn["to_asset_id"]},
        )
        edges += 1

    for acc in data.get("access", []):
        graph.run(
            g,
            """
            MATCH (i:Identity {id:$identity_id}), (a:Asset {id:$asset_id})
            MERGE (i)-[:CAN_ACCESS]->(a)
            """,
            {"identity_id": acc["identity_id"], "asset_id": acc["asset_id"]},
        )
        edges += 1

    # ---- attack edges: confirmed findings only
    for finding in data.get("findings", []):
        is_confirmed = finding.get("status") == "confirmed"

        grants_id = finding.get("grants_identity_id")
        if grants_id:
            if is_confirmed:
                graph.run(
                    g,
                    """
                    MATCH (f:Finding {id:$finding_id}), (i:Identity {id:$identity_id})
                    MERGE (f)-[:GRANTS]->(i)
                    """,
                    {"finding_id": finding["id"], "identity_id": grants_id},
                )
                edges += 1
            else:
                skipped_attack_edges += 1

        leads_to_id = finding.get("leads_to_asset_id")
        if leads_to_id:
            if is_confirmed:
                graph.run(
                    g,
                    """
                    MATCH (f:Finding {id:$finding_id}), (a:Asset {id:$asset_id})
                    MERGE (f)-[:LEADS_TO]->(a)
                    """,
                    {"finding_id": finding["id"], "asset_id": leads_to_id},
                )
                edges += 1
            else:
                skipped_attack_edges += 1

    return {"nodes": nodes, "edges": edges, "skipped_attack_edges": skipped_attack_edges}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default="data/findings.json")
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args()

    g = graph.connect()
    result = ingest(g, path=args.path, reset=not args.no_reset)
    print(result)


if __name__ == "__main__":
    main()
