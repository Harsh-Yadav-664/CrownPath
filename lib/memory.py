"""lib/memory.py -- graph memory across scans (BUILD_SPEC.md §9 P2, issue #23 / E1,
Track 02 "Agent Memory and Coordination").

Approach: NATIVE, not Graphiti (decision recorded in docs/HANDOFF.md). Our findings
are already structured, so there is nothing for Graphiti's LLM entity extraction to
do, and it would add an embedder dependency and nondeterminism to a demo whose
numbers must be exact. Memory is kept in the graph itself:

    (:Finding {first_seen, last_seen, scans:[scan ids], first_seen_at, last_seen_at})

`record_scan` stamps every finding present in a scan. `whats_changed` then diffs two
scans entirely in Cypher: findings added / removed, and *regressed assets* -- assets
exposing a newly confirmed finding that opens new attack paths to the crown jewel.
Path membership per scan reuses the 7a traversal with a filter on `n.scans`, so the
graph (not Python) decides which paths exist in which scan.

Limits: only Finding membership is versioned. Assets, endpoints and CONNECTS_TO /
CAN_ACCESS edges are shared across scans (they are the estate; findings are the state).

CLI (resets the graph, then loads scan 1 -> scan 2):  python -m lib.memory --demo
"""
import argparse
import datetime
import json

from lib import graph, ingest, seed_taxonomy

SCAN1_PATH = "data/findings.scan1.json"
SCAN2_PATH = "data/findings.scan2.json"

# Same edge set as query 7a (docs/graph-model.md), with a per-scan membership filter.
_SCAN_PATHS = """
MATCH path = (e:Endpoint {auth_required:false})
      -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->
      (j:Asset {id:$jewel, is_crown_jewel:true})
WHERE all(n IN nodes(path) WHERE n.scans IS NULL OR $scan IN n.scans)
"""

_DIFF_FINDINGS = """
MATCH (f:Finding)
WHERE $present IN f.scans AND NOT $absent IN f.scans
OPTIONAL MATCH (a:Asset)-[:EXPOSES]->(:Endpoint)-[:HAS_FINDING]->(f)
RETURN f.id, f.title, f.status, a.id
ORDER BY f.id
"""

_REGRESSED = """
MATCH (a:Asset)-[:EXPOSES]->(:Endpoint)-[:HAS_FINDING]->(f:Finding)
WHERE $until IN f.scans AND NOT $since IN f.scans AND f.status = 'confirmed'
WITH a, f
MATCH path = (e:Endpoint {auth_required:false})
      -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->
      (j:Asset {id:$jewel, is_crown_jewel:true})
WHERE f IN nodes(path)
  AND all(n IN nodes(path) WHERE n.scans IS NULL OR $until IN n.scans)
RETURN a.id, a.name, f.id, count(path)
ORDER BY count(path) DESC, f.id
"""


def record_scan(g, scan_id, path, scanned_at=None):
    """Stamp every finding in the findings document at `path` as seen in `scan_id`.
    Idempotent: re-recording the same scan id changes nothing."""
    scanned_at = scanned_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(path, "r", encoding="utf-8") as f:
        finding_ids = [x["id"] for x in json.load(f).get("findings", [])]
    graph.run(
        g,
        """
        UNWIND $ids AS fid
        MATCH (f:Finding {id:fid})
        SET f.first_seen = coalesce(f.first_seen, $scan),
            f.first_seen_at = coalesce(f.first_seen_at, $at),
            f.last_seen = $scan,
            f.last_seen_at = $at,
            f.scans = CASE WHEN f.scans IS NULL THEN [$scan]
                           WHEN $scan IN f.scans THEN f.scans
                           ELSE f.scans + [$scan] END
        """,
        {"ids": finding_ids, "scan": scan_id, "at": scanned_at},
    )
    return len(finding_ids)


def load_scan(g, scan_id, path, scanned_at=None):
    """Ingest a findings document additively (reset=False) and stamp it as a scan."""
    result = ingest.ingest(g, path, reset=False)
    result["findings_stamped"] = record_scan(g, scan_id, path, scanned_at)
    return result


def load_demo_scans(g):
    """Reset the graph, seed the taxonomy, then load scan-1 and scan-2. Scan-2 is
    the frozen demo, so the final graph answers the headline queries identically
    (f:idor severs 4 of 6)."""
    graph.reset(g)
    graph.init_schema(g)
    seeded = seed_taxonomy.seed(g)
    scan1 = load_scan(g, "scan-1", SCAN1_PATH, "2026-10-15T09:00:00+00:00")
    scan2 = load_scan(g, "scan-2", SCAN2_PATH, "2026-10-17T09:00:00+00:00")
    return {"seed": seeded, "scan-1": scan1, "scan-2": scan2}


def whats_changed(g, since, until, crown_jewel_id="asset:db"):
    """Diff two scans. Returns
        {"since", "until",
         "added":     [{finding_id, title, status, asset_id}],   # in `until`, not `since`
         "removed":   [{finding_id, title, status, asset_id}],   # in `since`, not `until`
         "regressed": [{asset_id, asset_name, finding_id, new_paths}],
         "paths": {"since": int, "until": int}}                  # crown-jewel paths
    `regressed` lists assets that expose a newly *confirmed* finding that lies on at
    least one crown-jewel attack path in `until` (a path that did not exist before)."""

    def _findings(present, absent):
        rows = graph.run(
            g, _DIFF_FINDINGS, {"present": present, "absent": absent}
        ).result_set
        return [
            {"finding_id": fid, "title": title, "status": status, "asset_id": asset_id}
            for fid, title, status, asset_id in rows
        ]

    def _path_count(scan):
        return graph.run(
            g, _SCAN_PATHS + "RETURN count(path)", {"jewel": crown_jewel_id, "scan": scan}
        ).result_set[0][0]

    regressed_rows = graph.run(
        g, _REGRESSED, {"since": since, "until": until, "jewel": crown_jewel_id}
    ).result_set

    return {
        "since": since,
        "until": until,
        "added": _findings(until, since),
        "removed": _findings(since, until),
        "regressed": [
            {"asset_id": aid, "asset_name": name, "finding_id": fid, "new_paths": n}
            for aid, name, fid, n in regressed_rows
        ],
        "paths": {"since": _path_count(since), "until": _path_count(until)},
    }


def headline(change):
    """One-line statement for the agent / UI."""
    if not change["regressed"]:
        return f"No regressions between {change['since']} and {change['until']}."
    top = change["regressed"][0]
    return (
        f"{top['asset_name']} ({top['asset_id']}) regressed since {change['since']}: "
        f"newly confirmed {top['finding_id']} opens {top['new_paths']} new path(s) to the "
        f"crown jewel ({change['paths']['since']} -> {change['paths']['until']} paths in total)."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="reset + load scan-1 and scan-2")
    parser.add_argument("--since", default="scan-1")
    parser.add_argument("--until", default="scan-2")
    args = parser.parse_args()

    g = graph.connect()
    if args.demo:
        print(load_demo_scans(g))
    change = whats_changed(g, args.since, args.until)
    print(json.dumps(change, indent=2))
    print(headline(change))


if __name__ == "__main__":
    main()
