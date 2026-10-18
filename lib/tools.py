"""tools.py — frozen graph-tool interface (BUILD_SPEC.md §8). Bodies implemented in
issue #17 (C1), wrapping the Epic-B graph queries. No new query logic here."""
from __future__ import annotations
from typing import TypedDict

from lib import graph, queries, seed_taxonomy


class PathStep(TypedDict):
    kind: str          # "node" | "edge"
    label: str         # node label or relationship type
    id: str            # node id ("" for edges)
    display: str       # human label, e.g. "Finding: reflected XSS on /search"


class AttackPath(TypedDict):
    steps: list[PathStep]      # ordered entry -> ... -> crown jewel
    length: int                # number of edges
    score: float               # 7b score: prod(confidence) * jewel.value / length
    finding_ids: list[str]     # Finding node ids on this path (for choke-point counting)
    crown_jewel_id: str


class ChokePoint(TypedDict):
    finding_id: str
    title: str
    paths_severed: int         # N
    paths_total: int           # M
    severs_highest_value: bool
    highest_value_path_score: float


class Remediation(TypedDict):
    rank: int
    finding_id: str
    title: str
    reason: str                # justification by PATH, never CVSS
    cited_path: AttackPath


_g = None  # module-level lazy singleton graph handle


def _get_graph():
    global _g
    if _g is None:
        _g = graph.connect()
    return _g


def _public_path(path: dict) -> AttackPath:
    """Strip internal keys (e.g. _confidences, _jewel_value) so only the frozen
    AttackPath shape crosses the tool boundary."""
    return {
        "steps": path["steps"],
        "length": path["length"],
        "score": path["score"],
        "finding_ids": path["finding_ids"],
        "crown_jewel_id": path["crown_jewel_id"],
    }


def ingest_findings(path: str = "data/findings.json") -> dict:
    """Load a findings document (validated against docs/findings.schema.json) into the
    FalkorDB graph. Returns {"nodes": int, "edges": int, "skipped_attack_edges": int}."""
    g = _get_graph()
    result = seed_taxonomy.load_all(g, path)
    seed_r = result["seed"]
    ingest_r = result["ingest"]
    return {
        "nodes": seed_r["techniques"] + ingest_r["nodes"],
        "edges": seed_r["chains"] + ingest_r["edges"],
        "skipped_attack_edges": ingest_r["skipped_attack_edges"],
    }


def find_attack_paths(crown_jewel_id: str | None = None, limit: int = 10) -> list[AttackPath]:
    """Query 7a. Anonymous entry (Endpoint auth_required=false) -> crown-jewel Asset.
    If crown_jewel_id is None, consider all crown jewels. Sorted shortest-first."""
    g = _get_graph()
    paths = queries.find_attack_paths(g, crown_jewel_id=crown_jewel_id, limit=limit)
    return [_public_path(p) for p in paths]


def shortest_path(from_id: str, to_id: str) -> AttackPath | None:
    """Query 7b building block. Highest-value/shortest path between two nodes, or None."""
    g = _get_graph()
    path = queries.shortest_path(g, from_id, to_id)
    return _public_path(path) if path is not None else None


def rank_by_reachability(crown_jewel_id: str | None = None) -> list[Remediation]:
    """Rank findings by how they sit on crown-jewel attack paths (7b score), each with a cited path.

    One Remediation per distinct finding: ranked by the highest-scoring path that
    finding sits on (descending), citing that path."""
    g = _get_graph()
    paths = queries.rank_paths(g, crown_jewel_id=crown_jewel_id)

    best_path_by_finding = {}
    title_by_finding = {}
    for path in paths:
        for step in path["steps"]:
            if step["kind"] == "node" and step["label"] == "Finding":
                fid = step["id"]
                if fid not in best_path_by_finding or path["score"] > best_path_by_finding[fid]["score"]:
                    best_path_by_finding[fid] = path
                    title_by_finding[fid] = step["display"].removeprefix("Finding: ")

    ranked_findings = sorted(
        best_path_by_finding.items(), key=lambda kv: -kv[1]["score"]
    )

    remediations: list[Remediation] = []
    for rank, (fid, path) in enumerate(ranked_findings, start=1):
        entry_display = path["steps"][0]["display"]
        jewel_display = path["steps"][-1]["display"]
        reason = (
            f"Lies on a length-{path['length']} path from "
            f"{entry_display.split(': ', 1)[-1]} to {jewel_display.split(': ', 1)[-1]} "
            f"(score {path['score']:.2f})."
        )
        remediations.append({
            "rank": rank,
            "finding_id": fid,
            "title": title_by_finding[fid],
            "reason": reason,
            "cited_path": _public_path(path),
        })

    return remediations


def choke_points(crown_jewel_id: str | None = None) -> list[ChokePoint]:
    """Query 7c. Findings ranked by how many crown-jewel paths they sit on.

    Temporary gap (tracked by issue #21/D2): raises NotImplementedError with a
    clear message until lib/chokepoints.py lands its choke_points() function."""
    try:
        from lib import chokepoints  # local import: #21/D2 may not exist yet at import time
        fn = chokepoints.choke_points
    except AttributeError:
        raise NotImplementedError(
            "choke_points: lib/chokepoints.py has not implemented choke_points() yet "
            "(issue #21/D2). find_attack_paths()/rank_by_reachability() are available "
            "in the meantime."
        )

    g = _get_graph()
    return fn(g, crown_jewel_id=crown_jewel_id)


def whats_changed(since: str = "scan-1", until: str = "scan-2",
                  crown_jewel_id: str = "asset:db") -> dict:
    """6th tool (P2, issue #23 / Track 02): graph memory across scans. Diffs two
    recorded scans in Cypher: findings added/removed, assets that regressed (a newly
    confirmed finding opened new attack paths to the crown jewel), and the crown-jewel
    path count in each scan. Requires scans loaded via `python -m lib.memory --demo`."""
    from lib import memory
    g = _get_graph()
    return memory.whats_changed(g, since, until, crown_jewel_id)
