"""tools.py — frozen graph-tool interface (BUILD_SPEC.md §8). Bodies land in issue #17 (C1)."""
from __future__ import annotations
from typing import TypedDict


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


def ingest_findings(path: str = "data/findings.json") -> dict:
    """Load a findings document (validated against docs/findings.schema.json) into the
    FalkorDB graph. Returns {"nodes": int, "edges": int, "skipped_attack_edges": int}."""
    raise NotImplementedError


def find_attack_paths(crown_jewel_id: str | None = None, limit: int = 10) -> list[AttackPath]:
    """Query 7a. Anonymous entry (Endpoint auth_required=false) -> crown-jewel Asset.
    If crown_jewel_id is None, consider all crown jewels. Sorted shortest-first."""
    raise NotImplementedError


def shortest_path(from_id: str, to_id: str) -> AttackPath | None:
    """Query 7b building block. Highest-value/shortest path between two nodes, or None."""
    raise NotImplementedError


def rank_by_reachability(crown_jewel_id: str | None = None) -> list[Remediation]:
    """Rank findings by how they sit on crown-jewel attack paths (7b score), each with a cited path."""
    raise NotImplementedError


def choke_points(crown_jewel_id: str | None = None) -> list[ChokePoint]:
    """Query 7c. Findings ranked by how many crown-jewel paths they sit on."""
    raise NotImplementedError
