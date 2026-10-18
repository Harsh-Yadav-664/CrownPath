# Handoff log

Each work session appends a dated block: what's DONE, what's NEXT, what's BROKEN/blocked.
Newest block on top. (Issue #8 / A8 may expand this template; keep the newest-on-top rule.)

## 2026-10-18 — Issues #21, #19, #18 (Sonnet session, continued): D2/C3/C2 — Epic C done
DONE:
  - #21 (D2): lib/chokepoints.py — `choke_points(g, crown_jewel_id)` (primary, deterministic:
    path-occurrence count) + `betweenness_cross_check(g)` (secondary, logged only) + `headline()`.
    Confirmed live: f:idor top, 4/6, severs_highest_value=True, headline string matches exactly.
    **Note on the betweenness cross-check:** on the demo graph it does NOT rank f:idor top among
    Findings (whole-graph betweenness is a different signal from "how many crown-jewel paths
    pass through this node" — f:idor is 5th of 8 Findings by betweenness, f:ssrf is highest).
    This matches the issue's own "never overrides, corroboration only" framing, so
    tests/test_chokepoints.py asserts only that the cross-check runs and returns scores, not
    that it agrees with the path-count ranking. Wired `lib.tools.choke_points` end-to-end (no
    code change needed there — it already delegated dynamically); the #17 temporary-gap
    try/except is now dead code on the happy path but left in place as a defensive guard.
  - #19 (C3): agent/prompts/system.md (forbids CVSS-first justification, mandates
    path+choke-point reasoning, exact output format) + agent/format.py
    (`format_answer(remediations, chokepoints)`). Pulls fix text from data/taxonomy/remediation.tsv
    keyed by technique_id (read from data/findings.json, since Remediation/ChokePoint TypedDicts
    don't carry vuln_type — kept the frozen #6 shapes untouched). Renders arrow-chain paths.
    Switched all arrows/dashes to ASCII (`->`, `--`) instead of Unicode (`→`/`—`) after
    hitting `UnicodeEncodeError` printing to a Windows cp1252 console — do the same in any new
    console-facing text in this repo. Confirmed output names IDOR as choke point with "4 of 6".
  - #18 (C2): agent/run.py — `run_no_llm()` (deterministic, calls tools.rank_by_reachability +
    tools.choke_points + format.format_answer directly) and `run_with_llm()` (Anthropic tool-use
    loop, 5 tools registered from the #6 signatures, max 8 iterations, default model
    `claude-sonnet-5-5` overridable via `CROWNPATH_MODEL`). CLI verified live:
    `python -m agent.run --no-llm --crown-jewel asset:db` prints the full ranked list + choke
    point and writes agent/last_answer.json (gitignored — regenerated output, not source).
    **Not verified: the LLM path** — no `ANTHROPIC_API_KEY` available in this session/environment.
    The tool-use loop follows the standard Anthropic SDK pattern (register tools -> execute ->
    feed tool_result back -> loop until stop_reason != "tool_use") but has not been run against
    a live model. Whoever has a key should smoke-test `python -m agent.run` (no flags) once.
  - 14/14 tests pass live against FalkorDB Cloud.
NEXT: Epic C is done. Epic D remaining: #20 (D1 MCP server, P1), #22 (D3 UI, P1). Epic E (P2):
  #23 (Graphiti memory/Track 02), #24 (loopback capture), #25 (live deployment). Epic F
  (submission, P0, mostly human-owned): #26 (README finalize — can now cite the real 7a/7b/7c
  queries and the agent output), #27 (demo video), #28 (blog post), #29 (submit). Epic G: #30
  (fresh-clone, teammate-owned), #31 (rules audit).
BROKEN/blocked: LLM tool-use path in agent/run.py is implemented but unverified — needs a real
  ANTHROPIC_API_KEY smoke test (flagged above, not a stop-the-line blocker since --no-llm is the
  committed P0 path per the issue's own fallback requirement).

## 2026-10-18 — Issues #15, #16, #17 (Sonnet session, continued): B4/B5/C1
DONE:
  - #15 (B4): lib/queries.py `find_attack_paths(g, crown_jewel_id, limit)` using the exact
    verified 7a Cypher from docs/graph-model.md. Projects FalkorDB `Path` objects (inspected
    live: `falkordb.path.Path` with `.nodes()`/`.edges()`, node `.labels`/`.properties`, edge
    `.relation`/`.properties`) into the frozen AttackPath/PathStep shape. Confirmed live: exactly
    6 paths, f:idor on 4/6, f:csrf on 0/6 — matches docs/demo-scenario.md exactly.
    tests/test_queries_7a.py asserts the full path-id-sequence set.
  - #16 (B5): added `score_path`, `shortest_path`, `rank_paths` to lib/queries.py. Scores match
    the #10 spike's recorded values exactly (12.75, 9.92, 8.50, 7.08, 5.00, 4.00). Used internal
    `_confidences`/`_jewel_value` keys on the AttackPath dict (documented as not part of the
    public TypedDict) so score_path stays a pure function with no second graph round-trip.
    `rank_paths` enumerates ALL paths before sorting (no pre-score truncation) then slices to
    `limit`. tests/test_queries_7b.py passes.
  - #17 (C1): implemented all 5 lib/tools.py functions behind the frozen #6 interface (lazy
    singleton graph handle via `_get_graph()`). `rank_by_reachability` groups by finding
    (best-scoring path each sits on) and writes a path-derived `reason` string — verified no
    "cvss" substring appears in any reason. `choke_points` cleanly raises `NotImplementedError`
    with a message naming #21/D2 (the one allowed temporary gap per the issue) until
    lib/chokepoints.py lands. tests/test_tools.py passes; 9/9 tests green overall.
NEXT: #21 (D2 choke-points, P0 headline) should go next — it unblocks the real choke_points()
  body in lib/tools.py and is this project's money-shot. Then #18/#19 (C2/C3 agent loop +
  formatter) can cite it. #20 (D1 MCP server) and #22 (D3 UI) are P1, after.
BROKEN/blocked: none.

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
