"""lib/chokepoints.py — query 7c, the choke-point finding (BUILD_SPEC.md §7c/§2,
issue #21 / D2). This is the headline: "fix X -> sever N of M paths."

Primary method (authoritative, deterministic): enumerate 7a paths, count each
Finding's occurrences. Secondary method (cross-check, logged only, never
overrides the ranking): algo.betweenness over the attack subgraph.
"""
from lib import graph, queries

_BETWEENNESS_QUERY = """
CALL algo.betweenness({
  nodeLabels: ['Endpoint', 'Finding', 'Identity', 'Asset'],
  relationshipTypes: ['EXPOSES', 'HAS_FINDING', 'LEADS_TO', 'GRANTS', 'CAN_ACCESS', 'CONNECTS_TO'],
  samplingSeed: 42
})
YIELD node, score
WHERE 'Finding' IN labels(node)
RETURN node.id, score
"""


def _finding_titles(g, finding_ids):
    if not finding_ids:
        return {}
    result = graph.run(
        g, "MATCH (f:Finding) WHERE f.id IN $ids RETURN f.id, f.title", {"ids": list(finding_ids)}
    )
    return {row[0]: row[1] for row in result.result_set}


def betweenness_cross_check(g):
    """Secondary cross-check (logged only): {finding_id: betweenness_score} for every
    Finding reachable in the attack subgraph. Never overrides the deterministic
    ranking in choke_points() -- a corroborating signal only (BUILD_SPEC §7c)."""
    try:
        result = graph.run(g, _BETWEENNESS_QUERY)
    except Exception:
        return {}
    return {row[0]: row[1] for row in result.result_set}


def choke_points(g, crown_jewel_id=None):
    """Query 7c: findings ranked by how many crown-jewel paths they sit on.

    Primary, authoritative method: count each Finding's occurrence across all 7a
    paths (removing that finding removes exactly those paths). Tie-break: summed
    path score DESC. Returns list[ChokePoint] (lib/tools.py #6 shape)."""
    paths = queries.find_attack_paths(g, crown_jewel_id=crown_jewel_id, limit=None)
    total_paths = len(paths)

    if total_paths == 0:
        return []

    # score every path so the tie-break and severs_highest_value check have data
    for p in paths:
        p["score"] = queries.score_path(p)

    best_score = max(p["score"] for p in paths)
    best_scoring_findings = {
        fid for p in paths if p["score"] == best_score for fid in p["finding_ids"]
    }

    severed_count = {}
    summed_score = {}
    for p in paths:
        for fid in set(p["finding_ids"]):
            severed_count[fid] = severed_count.get(fid, 0) + 1
            summed_score[fid] = summed_score.get(fid, 0.0) + p["score"]

    titles = _finding_titles(g, severed_count.keys())

    ranked = sorted(
        severed_count.keys(),
        key=lambda fid: (-severed_count[fid], -summed_score[fid]),
    )

    choke_points_out = []
    for fid in ranked:
        severs_highest_value = fid in best_scoring_findings
        choke_points_out.append({
            "finding_id": fid,
            "title": titles.get(fid, fid),
            "paths_severed": severed_count[fid],
            "paths_total": total_paths,
            "severs_highest_value": severs_highest_value,
            "highest_value_path_score": best_score if severs_highest_value else 0.0,
        })

    return choke_points_out


def headline(cp, jewel_name):
    """'Fix <title> -> sever N of M paths to <jewel_name>, including the highest-value one.'
    Drops the 'including...' clause when severs_highest_value is False."""
    base = f"Fix {cp['title']} -> sever {cp['paths_severed']} of {cp['paths_total']} paths to {jewel_name}"
    if cp["severs_highest_value"]:
        return base + ", including the highest-value one."
    return base + "."
