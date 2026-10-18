# Handoff log

Each work session appends a dated block: what's DONE, what's NEXT, what's BROKEN/blocked.
Newest block on top. (Issue #8 / A8 may expand this template; keep the newest-on-top rule.)

## 2026-10-18 — Issue #10: live query spike (Opus)
DONE: ran 7a/7b/7c against FalkorDB Cloud (graph module v4.22.0, enterprise; falkordb-py 1.8.0;
  ssl=false) on scratch graph `crownpath_spike`, loaded from the frozen demo scenario.
  - **7a works unchanged** → exactly **6 paths** anonymous-entry→`asset:db`, matching the
    hand-derived set in docs/demo-scenario.md verbatim.
  - **7c**: `f:idor` is the choke point, on **4 of 6** paths; delete-proof → 2 paths remain
    (4 severed). Headline holds.
  - **7b**: scoring over enumerated paths ranks the three short user-session IDOR paths top
    (max 12.75). Exact transcript in docs/graph-model.md → "Verified live Cypher".
  - Scratch graph deleted; real `crownpath` graph untouched (empty, from the ping probe).
  - BUILD_SPEC §7 unchanged except a verified-live note; demo-scenario path set needs NO
    correction — it held exactly.
CAVEAT (important): Cypher `LIMIT` does not correctly bound variable-length path enumeration
  (`LIMIT 3` returned 2 rows). Epic-B code (lib/queries.py #15, lib/chokepoints.py #21) must
  enumerate all paths then slice in Python — never cap at/below the true count in Cypher. This
  is recorded in docs/graph-model.md and BUILD_SPEC §7.
NEXT: Epic B can start — #11 (B1 schema init), #12/#14 (data+taxonomy), #13 (ingest), #15 (7a
  in lib/queries.py), #16 (7b), #21 (7c). The spike unblocks all of them.
BROKEN/blocked: none. `scripts/spike_7a.py` is kept as reproducible evidence (throwaway, not
  product code).

## 2026-10-18 — Phase 1 (Opus): planning, scaffolding, DB connection
DONE: repo scaffolded; FalkorDB syntax verified against docs; spec paths fixed; schema/contract/
  tool-interface/demo-scenario frozen; all issues created; FalkorDB Cloud connection verified via
  scripts/ping.py (ssl=false); .env/.env.example/CLAUDE.md/.claude/settings.json/lib/graph.py landed.
NEXT: issue #10 (prove 7a live) — DONE above.
BROKEN/blocked: dev laptop has no Docker/WSL; the team uses FalkorDB Cloud (the local Docker path
  exists only for judges and is verified by #30 on a teammate's machine).
