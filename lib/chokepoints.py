"""lib/chokepoints.py — query 7c, the choke-point finding (BUILD_SPEC.md §7c/§2,
issue #21 / D2). This is the headline: "fix X -> sever N of M paths."

Primary method (authoritative, deterministic): enumerate 7a paths and count each
Finding's occurrences -- all in Cypher. Secondary method (cross-check, logged only,
never overrides the ranking): algo.betweenness over the attack subgraph.
"""
from lib import graph

_EDGES = "EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO"

# 7a path enumeration + the 7b score per path, as the head of every 7c query.
_PATHS_ALL_JEWELS = f"""
MATCH path = (e:Endpoint {{auth_required:false}})
      -[:{_EDGES}*1..8]->
      (j:Asset {{is_crown_jewel:true}})
WITH path, reduce(c = 1.0, n IN nodes(path) |
       CASE WHEN 'Finding' IN labels(n) THEN c * n.confidence ELSE c END)
     * j.value / length(path) AS score
"""
_PATHS_ONE_JEWEL = _PATHS_ALL_JEWELS.replace(
    "{is_crown_jewel:true}", "{is_crown_jewel:true, id:$jid}"
)

# M (total paths) and the highest-value path score.
_TOTALS = "RETURN count(path), max(score)"

# N per finding: paths it sits on, ranked; summed score breaks ties.
_PER_FINDING = """
UNWIND [n IN nodes(path) WHERE 'Finding' IN labels(n)] AS f
RETURN f.id, count(path) AS severed, sum(score) AS summed, max(score) AS best_on_path
ORDER BY severed DESC, summed DESC
"""

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


def _cypher_params(crown_jewel_id):
    """(match clause, params): one crown jewel when an id is given, else all of them."""
    if crown_jewel_id is None:
        return _PATHS_ALL_JEWELS, {}
    return _PATHS_ONE_JEWEL, {"jid": crown_jewel_id}


def choke_points(g, crown_jewel_id=None):
    """Query 7c: findings ranked by how many crown-jewel paths they sit on.

    Primary, authoritative method, computed entirely in Cypher: enumerate the 7a
    paths, UNWIND each path's Finding nodes and count paths per Finding (removing that
    finding removes exactly those paths). Each path also carries its 7b score
    (prod(finding.confidence) * jewel.value / length, via reduce()), used for the
    tie-break (summed score DESC) and for severs_highest_value. Python only formats
    the rows into the ChokePoint shape (lib/tools.py #6)."""
    match, params = _cypher_params(crown_jewel_id)

    total_row = graph.run(g, match + _TOTALS, params).result_set[0]
    total_paths, best_score = total_row[0], total_row[1]
    if total_paths == 0:
        return []

    rows = graph.run(g, match + _PER_FINDING, params).result_set
    titles = _finding_titles(g, [row[0] for row in rows])

    choke_points_out = []
    for fid, severed, _summed, best_on_path in rows:
        severs_highest_value = abs(best_on_path - best_score) < 1e-9
        choke_points_out.append({
            "finding_id": fid,
            "title": titles.get(fid, fid),
            "paths_severed": severed,
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
