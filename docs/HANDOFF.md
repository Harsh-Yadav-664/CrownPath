# Handoff log

Each work session appends a dated block: what's DONE, what's NEXT, what's BROKEN/blocked.
Newest block on top. (Issue #8 / A8 may expand this template; keep the newest-on-top rule.)

## 2026-10-18 — Issues #12, #14, #13 (Sonnet session, continued): B6/B3/B2
DONE:
  - #12 (B6): data/gen_findings.py — deterministic generator transcribing docs/demo-scenario.md
    exactly (4 assets/6 endpoints/3 identities/8 findings, connections=[admin→api],
    access=[user→api, admin→db]); two runs produce byte-identical data/findings.json; validates
    against docs/findings.schema.json.
  - #14 (B3): copied the 4 swiftPentest taxonomy files into data/taxonomy/ (verbatim), updated
    docs/REUSE.md rows from "pending" to landed. lib/seed_taxonomy.py seeds 77 Technique nodes
    (union of techniques.jsonl classes + classes.jsonl slugs + chains.jsonl from/to, xss-reflected
    aliased to xss) and all 24 CHAINS_TO edges, 0 auto-created (every chain endpoint already
    existed). All 8 demo technique_ids (xss, open-redirect, bfla, idor, ssrf, sqli,
    mass-assignment, csrf) confirmed present — tests/test_seed.py passes live.
  - #13 (B2): lib/ingest.py — MERGE-based loader, hard-fails on an unknown technique_id or a
    schema violation, skips GRANTS/LEADS_TO for non-confirmed findings. **Bug found + fixed
    during integration**: seed_taxonomy.load_all()'s original order called
    ingest(reset=True) AFTER seed(), so ingest's own reset wiped the just-seeded Technique/
    CHAINS_TO nodes before loading findings. Fixed: load_all now does
    reset→init_schema→seed→ingest(reset=False), resetting exactly once up front.
  - Full demo load verified live: seed_taxonomy.load_all(g, "data/findings.json") →
    21 nodes / 32 edges ingested, 0 skipped_attack_edges (f:csrf has no attack-edge FK at all in
    the frozen demo data, so the skip counter can't exceed 0 from it — see note below).
  - **Spec clarification (not a blocker, resolved in-session):** issue #13's acceptance checklist
    expected `skipped_attack_edges >= 1` on the demo graph, but the frozen demo-scenario (#7)
    gives the inconclusive `f:csrf` no `grants_identity_id`/`leads_to_asset_id` at all — there is
    nothing to skip. Verified the skip mechanism itself instead with a separate synthetic fixture
    in tests/test_ingest.py::test_ingest_skips_attack_edges_for_non_confirmed_findings (asserts
    skipped_attack_edges==2 when a non-confirmed finding DOES carry both FKs). Did not touch the
    frozen docs/demo-scenario.md or data/gen_findings.py.
  - 5/5 tests pass live against FalkorDB Cloud (tests/test_graph.py, test_seed.py, test_ingest.py
    ×3). Graph left reset (empty) after each test run.
NEXT: #15 (B4 query 7a in lib/queries.py), #16 (B5 query 7b), then Epic C (#17-19 agent).
BROKEN/blocked: none.

## 2026-10-18 — Issues #1–#8, #11 (Sonnet session): Epic A foundation + B1
DONE: all of Epic A closed:
  - #1 (A1): repo scaffold — §12 dirs created, requirements.txt pinned (pip install verified
    clean in a fresh venv), placeholder modules for lib/schema,ingest,queries,chokepoints,tools,
    agent/run, mcp/server, data/gen_findings, tests/__init__ — all import cleanly.
  - #2 (A2): docker-compose.yml + Makefile (real tabs, `make -n` verified) + .env.local.example
    (had to add a `!.env.local.example` negation to .gitignore so it isn't swallowed by `.env.*`).
  - #3 (A3): README.md skeleton, all 10 Rule-10 sections in order, disclosure text verbatim.
  - #4 (A4): lib/schema.py frozen constants + validate_node() (tested: good/unknown-label/
    missing-id/bad-bool/bad-enum all behave per spec); prepended the frozen node/edge/invariant
    docs to docs/graph-model.md ABOVE the existing "Verified live Cypher" section from #10 (kept
    that section intact — it was already filled for real, not a placeholder).
  - #5 (A5): docs/findings.schema.json (draft 2020-12) + data/findings.example.json — both
    validated live via `jsonschema.validate`.
  - #6 (A6): lib/tools.py frozen interface stubs (5 functions + 4 TypedDicts), all raise
    NotImplementedError, imports verified.
  - #7 (A7): docs/demo-scenario.md — full node/edge tables + the 6 enumerated paths + choke-point
    headline, transcribed verbatim from the issue (matches #10's live-verified set exactly).
  - #8 (A8): docs/REUSE.md created (docs/HANDOFF.md already existed from #10's session, already
    satisfied the template — left as-is).
  - #11 (B1): added `init_schema()` (5 id indexes, verified idempotent — ran twice, no error,
    `CALL db.indexes()` lists all 5) and `reset()` to the existing lib/graph.py (connect()/run()
    untouched); tests/test_graph.py passes live against FalkorDB Cloud.
  All verified live against the team's FalkorDB Cloud instance where applicable. No Claude
  attribution added anywhere; each issue closed via commit "Closes #N" and auto-closed on push.
NEXT: Epic B continues — #12 (B6 synthetic findings.json generator, should transcribe
  docs/demo-scenario.md exactly), #13 (B2 ingest.py), #14 (B3 seed_taxonomy.py — needs the
  swiftPentest taxonomy files copied per docs/REUSE.md, currently marked "pending"), #15 (B4
  query 7a in lib/queries.py), #16 (B5 query 7b).
BROKEN/blocked: none from this session. Note for whoever picks up #14: the REUSE.md rows for
  the taxonomy files are still "pending" — the actual copy from ../swiftpentest-fork hasn't
  happened yet.

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
