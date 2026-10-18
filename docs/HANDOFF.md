# Handoff log

Each work session appends a dated block: what's DONE, what's NEXT, what's BROKEN/blocked.
Newest block on top. (Issue #8 / A8 may expand this template; keep the newest-on-top rule.)

## 2026-10-18 (evening) — teammate session: setup, #25 prep, #23 (Sonnet session, user harshiit-rana)
Setup verified on a fresh Windows venv: `make ping` equivalent (`python scripts/ping.py`) OK,
UI serves, 6 paths + "fix IDOR, sever 4 of 6" confirmed.
**Access note:** `harshiit-rana` has READ-only access to `Harsh-Yadav-664/CrownPath`, so work is
pushed to the fork `harshiit-rana/CrownPath` (remote `fork`) until write access is granted;
`origin` is still the upstream for `pull --rebase`.

DONE:
  - **Fresh-install bug fixed (#30 class):** `pip install -r requirements.txt` on a clean venv
    resolved pydantic 2.14, which removed `eval_type_backport` that `mcp==1.2.0` imports ->
    `ImportError` collecting tests/test_agent*.py. Pinned `pydantic==2.11.9`,
    `pydantic-settings==2.11.0` in requirements.txt.
  - **Test safety:** every test calls `graph.reset()`; running pytest used to empty the graph the
    live demo reads. Added tests/conftest.py defaulting `CROWNPATH_GRAPH=crownpath_test`.
  - **#25 prep (Render deploy itself still needs a human account):** render.yaml,
    docs/deploy.md, `/api/agent` in ui/app.py (in-process per-IP limit 6/min, 40 s timeout,
    always HTTP 200; falls back to data/sample_answer.json with `sample_response: true` and a UI
    banner), tests/test_ui_agent.py. Verified: normal, rate-limited and bad-LLM-key paths.
  - **#23 (Track 02) -- decision: NATIVE memory, not Graphiti.** Reason: our findings are
    already structured, so Graphiti's LLM entity extraction has nothing to add, and it would
    bring an embedder dependency plus nondeterminism into a demo whose numbers (4 of 6) must be
    exact. Implemented in Cypher: Finding gets `first_seen/last_seen/scans[]`;
    `lib/memory.py` `whats_changed(since, until)` diffs scans (added/removed/regressed + per-scan
    path counts). Verified live: scan-1 has 2 crown-jewel paths, scan-2 has 6; `f:idor` added;
    `asset:api` regressed (+4 paths). 6th tool `whats_changed` added to lib/tools.py and
    crownpath_mcp/server.py; `/api/changes` + "What changed?" button in the UI. The live graph is
    loaded with `python -m lib.memory --demo` (scan-2 == the frozen demo, so 4-of-6 is unchanged).
BLOCKED / needs a human: #18 needs LLM_API_KEY in .env (owner will paste); Render account +
  env vars (#25); push access to upstream; #24 needs `bin/demo_target.py` from swiftPentest
  (clone was blocked by the tool's permission classifier).

## 2026-10-18 — #20 resolved, #18 provider-agnostic path, TEAMMATE_RUNBOOK.md (Sonnet session)
Picked up directly from the #20 blocker flagged in the previous session's entry below.
Human gave an explicit 3-part instruction: resolve #20 with the rename option, add
provider-agnostic LLM code for #18 (unrun, mocked tests only), write a runbook for a
teammate to finish the rest. Did exactly those three, in order, then stopped per
instruction — did not continue into Epic E/F/G work itself.

DONE:
  - **#20 (D1 MCP server) — blocker resolved, issue closed.** Renamed the package
    `mcp/` -> `crownpath_mcp/` (`git mv`), which was the human-authorized fix for the
    import collision with the third-party `mcp` SDK documented in the blocker entry
    below. Built `crownpath_mcp/server.py`: a stdio MCP server (`mcp.server.Server`,
    `stdio_server()`) exposing the same 5 `lib.tools` functions as MCP tools
    (`TOOL_DEFS`/`TOOL_FUNCTIONS`). Updated every reference to the old path:
    `BUILD_SPEC.md` §8, the D1 backlog bullet, and §12's repo-layout tree (added a note
    pointing back to this file); added `crownpath_mcp/README.md` documenting the rename
    and the tools table. Added `pytest-asyncio==0.25.2` to requirements.txt.
    Verified live (not just unit-tested): direct import confirms `import mcp` now
    resolves to the real SDK (`site-packages/mcp/__init__.py`), not our own code;
    `tests/test_mcp_server.py` drives the server through an in-process MCP client
    session (`mcp.shared.memory.create_connected_server_and_client_session`) and
    confirms `list_tools()` returns all 5 names and `call_tool("choke_points", ...)`
    returns the live `f:idor`/4-of-6 result against FalkorDB Cloud; a raw
    `python -m crownpath_mcp.server` stdio smoke test exits clean on EOF. Full suite:
    15/15 passed. Committed as `6c4e995` ("Closes #20: ..."), pushed; commented on #20
    with the verification detail; auto-closed by the commit.
  - **#18 (C2 agent) — provider-agnostic LLM path added, left OPEN (as instructed).**
    `agent/run.py` gained `run_with_provider_llm()`: a tool-use loop over any
    OpenAI-compatible chat API, configured via `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`.
    Refactored so BOTH the existing Anthropic path (`run_with_llm`) and the new one
    bridge their tool schemas from the single source of truth,
    `crownpath_mcp.server.MCP_TOOL_DEFS` (via new `_anthropic_tool_defs()` /
    `_openai_tool_defs()` converters) and dispatch through
    `crownpath_mcp.server.TOOL_FUNCTIONS` — one schema edit now fixes tool selection
    for every path, agent/run.py no longer carries its own duplicate TOOL_DEFS. `main()`
    now tries, in order: `ANTHROPIC_API_KEY` -> `LLM_API_KEY`+`LLM_BASE_URL` ->
    `--no-llm` deterministic fallback (unchanged, still the committed P0 path). Added
    `openai==2.3.0` to requirements.txt (already installed locally; confirmed on PyPI).
    Unit-tested with a MOCKED OpenAI-compatible client (`tests/test_agent_provider.py`,
    3 tests, no network) — the mock stands in only for the LLM call itself; the tool
    calls it triggers (e.g. `choke_points`) run for real against the live FalkorDB demo
    graph, confirming the bridge actually dispatches correctly. Full suite after this
    change: 18/18 passed.
    **Research caveat (why #18 stays open):** could not fully confirm current
    OpenAI-compatible model IDs for Gemini or Groq against primary docs in this session
    — WebSearch kept returning third-party/secondary sources. Put best-effort defaults
    in `.env.example` with explicit "verify before relying on this" notes:
    Gemini `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`,
    `LLM_MODEL=gemini-2.5-flash`; Groq `LLM_BASE_URL=https://api.groq.com/openai/v1`,
    `LLM_MODEL=openai/gpt-oss-120b` (chosen over `llama-3.3-70b-versatile` because
    secondary sources reported Groq deprecating that model on the free tier in
    mid-2026 — unconfirmed firsthand). **The provider-agnostic path was never run
    against a real provider** — no API key available in this environment. Commented on
    #18 with the exact gap (model-ID currency, a real end-to-end run, and the
    never-run-either Anthropic path) for whoever picks it up with a key — see
    `docs/TEAMMATE_RUNBOOK.md` §§0-1 for the exact steps. Committed as `f23857a`
    ("Re #18: ..." — deliberately not "Closes", issue left open), pushed.
  - **`docs/TEAMMATE_RUNBOOK.md` written** (`605e81c`): click-by-click steps for a human
    teammate to finish everything left — `.env`/LLM-key setup, verifying the live LLM
    path with 5 runs + saving `docs/sample-run.md`, the Render deploy (#25, including
    `render.yaml`, rate-limiting, and the recorded-sample fallback so a judge never sees
    an error), #23 (Graphiti/native memory, Track 02, with the 1-2hr Graphiti timebox
    called out), #24 (loopback capture, with the Rule-6 loopback-only guard called out),
    #26 (README finalize checklist), #30 (fresh-clone-on-Docker verification — flagged
    as needing a machine other than the primary dev laptop, which has no Docker), #31
    (rules audit table structure + what to spot-check), #27 (demo video beat sheet),
    #28 (optional blog post), #29 (final submission checklist + deadline). Ends with a
    reminder not to improvise around blockers and to log them here the same way #20 was.
NEXT: Everything in `docs/TEAMMATE_RUNBOOK.md`, in the order it's written there — start
  with §0/§1 (get a real LLM key, verify the live path, close out #18 for real) since
  that's the one actual gap left from P0/P1, then the Render deploy (§2/#25), then the
  optional P2 items (§3 #23, §4 #24) only if time allows, then README finalize (§5/#26),
  fresh-clone check (§6/#30), rules audit (§7/#31), video (§8/#27), optional blog (§9/#28),
  and finally submit (§10/#29) before Oct 18 2026 23:59 IST.
BROKEN/blocked: none now — #20's blocker is resolved. #18 is intentionally left open
  (not broken, just not yet live-verified) with the gap documented on the issue and in
  `docs/TEAMMATE_RUNBOOK.md` §1.

## 2026-10-18 — Issue #22 (Sonnet session, continued): D3 UI — Epic D at 2/3 (D1 blocked)
DONE: ui/app.py (FastAPI: `/`, `/api/graph`, `/api/paths`, `/api/chokepoints`, all reading
  the live graph through `lib.graph`/`lib.tools` — works against FalkorDB Cloud, no hardcoded
  localhost) + ui/static/index.html (Cytoscape.js 3.28.1 pinned from cdnjs, dark theme, node
  colour by label, crown jewel emphasised). Verified live end-to-end:
  - `uvicorn ui.app:app --port 8000` serves the page; graph loads (98 nodes incl. the full
    taxonomy — demo entities plus all 77 Techniques, since `/api/graph` returns everything).
  - "Trace attack paths" verified via screenshot: highlights all 6 paths in red converging on
    the gold crown-jewel node, headline "6 attack path(s) to the crown jewel".
  - "Show choke point" verified via direct JS execution (`await showChokePoint()`) against the
    live page: dims all 154 elements, highlights f:idor, headline text exactly
    "Fix IDOR on /api/orders -> sever 4 of 6 paths to Customer database, including the
    highest-value one." Every sub-step (fetch, addClass, closedNeighborhood) also verified
    individually, all instant. **Could not get a passing screenshot after this specific
    interaction** — `Page.captureScreenshot` timed out 3x across 2 fresh tabs after the choke-
    point classes were applied, even though direct JS calls returned correctly and the function
    itself completed. Reads as a CDP/extension quirk capturing Cytoscape's canvas after many
    class changes, not a functional bug (every underlying operation independently verified
    correct and fast) — but flagging since it was never visually confirmed by screenshot.
    Whoever records the demo video (#27) should sanity-check this interaction renders smoothly
    in a normal browser before relying on it.
  - **Environment note:** installing `mcp==1.2.0` (while investigating #20's blocker) upgraded
    `starlette` to 1.8.0 globally and broke the pre-existing `fastapi` 0.118.2 install
    (`TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'`). Fixed by
    reinstalling `starlette>=0.40.0,<0.49.0` (landed on 0.48.0). This was a global-environment
    side effect of probing #20, not a requirements.txt change — worth a clean-venv re-check
    before the demo if anyone else also installs the `mcp` SDK locally.
  - Did not build mcp/README.md or the CROWNPATH_USE_MCP wiring (those are #20's scope, blocked
    — see below).
NEXT: #20 needs a human decision (see blocker below) before D1 can proceed. Epic E (#23-25, P2)
  and Epic F (#26-29, mostly human-owned) remain.
BROKEN/blocked: #20 blocked (see entry below). UI choke-point screenshot unverified visually
  (see note above) despite functional verification.

## 2026-10-18 — BLOCKER on #20 (D1 MCP server) — stopped, flagging for a human decision
**Problem:** BUILD_SPEC.md §12 freezes the submission layout with our own package at
`crownpath/mcp/` (containing `mcp/server.py`), and separately requires the third-party `mcp`
Python SDK (requirements.txt, `mcp==1.2.0`) for issue #20. These two things have the SAME
import name and collide:
- Whenever the repo root is on `sys.path` (the normal case for `python -m mcp.server`, for
  `pytest` run from the repo root, or for any script executed from repo root — confirmed live:
  `sys.path[0] == ''` resolves to the repo root), `import mcp` resolves to OUR OWN
  `crownpath/mcp/__init__.py`, never to the installed SDK.
- Confirmed live: `python -c "import mcp.server; print(mcp.server.__file__)"` from the repo
  root prints `crownpath/mcp/server.py` (our own file), not the SDK.
- Therefore `mcp/server.py` cannot do `from mcp.server.stdio import stdio_server` (the
  issue's own prescribed SDK usage) — confirmed live: `ModuleNotFoundError: No module named
  'mcp.server.stdio'; 'mcp.server' is not a package`, because `mcp.server` resolves to itself
  (the very file being written), not the SDK's `server` subpackage.
This is not a coding bug I can fix inside #20's scope without changing the frozen §12 layout
or the package name `mcp` either for our own code or by renaming the dependency (not possible
for a third-party package) — i.e. it is a design/architecture decision, not an implementation
detail, per CLAUDE.md's "zero design decisions in implementation issues" rule.
**Options for the human to decide** (not choosing one myself):
1. Rename our local package from `mcp/` to something else (e.g. `mcp_server/`), update §12 and
   all existing imports (none yet reference `crownpath.mcp` from outside, since #20 is the
   first thing that would import it) — cleanest fix, but changes the frozen submission layout.
2. Keep `mcp/server.py` as the file path (matches §12's reference literally) but have it import
   the SDK via `importlib` tricks or by temporarily removing the repo root from `sys.path`
   before importing the SDK, then restoring it — fragile, easy to get subtly wrong, avoided on
   purpose rather than improvised.
3. Drop the MCP server (it's P1, not P0 — "Never cut" in §9 does not list it) and rely on direct
   `lib.tools` import for the agent, documenting in the README that MCP tool-exposure was
   descoped due to a naming collision discovered during the build. Conflicts with "do not
   pre-emptively cut" in §9/§14, so needs explicit human sign-off, not mine.
**Did NOT do:** did not rename `mcp/__init__.py`/`mcp/server.py` or restructure the layout; did
not implement any part of #20 beyond this investigation. Issue #20 is left OPEN.
NEXT (once a human picks an option above): re-attempt #20 with that decision; #22 (D3 UI, P1)
has no such conflict and can proceed independently in the meantime.

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
