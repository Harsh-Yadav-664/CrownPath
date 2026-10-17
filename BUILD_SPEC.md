# CrownPath — Master Build Spec (read this fully before any action)

> This document is the single source of truth for building **CrownPath**, our submission for the FalkorDB "Graph Hacks" hackathon. It lives at the root of the submission repo. If you are a Claude Code session: read this document end to end before you touch anything, follow it exactly, and do not drift from it. When something here conflicts with your own idea, this document wins. When you are genuinely blocked or a rule here seems impossible, stop and leave a note in `docs/HANDOFF.md` rather than improvising.

---

## 0. Your operating contract (Claude Code: obey these)

- **Do not re-invent the idea.** The project, the graph model, and the winning insight are already decided (Sections 2, 6, 7). Your job is to build them, not to re-explore the problem space.
- **Do not go on web-research tangents.** You need exactly two reference sources: this spec, and the official FalkorDB docs (`https://docs.falkordb.com`) to verify Cypher syntax and algorithm names. Read the swiftPentest code **locally** from the fork folder (Section 3). Do not search the web for ideas, alternatives, or inspiration. Time spent researching is time not spent building.
- **Build the critical path first, then stop and verify it works end to end** before adding anything on top (Section 9). A small thing that runs beats a big thing that half-runs.
- **Reuse before you write** (Section 5). We are time-constrained and may hit model usage limits. Every helper you can legitimately lift from swiftPentest is time freed for the parts that win. But reuse only the parts Section 5 names, and only by copying files into the submission repo — never by building inside the fork.
- **Verify, don't assume.** Before relying on a FalkorDB algorithm name or Cypher feature, confirm it in the docs. Do not fabricate an API.
- **Leave buffer.** Treat the core build as done well before the deadline so there is room to debug and record the demo. Do not gold-plate; do not polish P2 work while P0 is unproven.
- **Disclose nothing false, hide nothing.** This is new work that reuses our own prior tool openly (Section 5). The README says so plainly.

---

## 1. Official references (authoritative — re-read if unsure, do not hallucinate rules)

- **Hackathon home:** https://www.wemakedevs.org/hackathons/falkordb
- **Rules (authoritative):** https://www.wemakedevs.org/hackathons/falkordb/rules
- **Schedule:** https://www.wemakedevs.org/hackathons/falkordb/schedule
- **Resources:** https://www.wemakedevs.org/hackathons/falkordb/resources
- **FalkorDB docs (verify all Cypher/algorithms here):** https://docs.falkordb.com
- **FalkorDB Cypher:** https://docs.falkordb.com/cypher · **Algorithms:** https://docs.falkordb.com/algorithms
- **FalkorDB on GitHub:** https://github.com/FalkorDB/FalkorDB · **GraphRAG-SDK:** https://github.com/FalkorDB/GraphRAG-SDK
- **Graphiti (optional memory layer):** https://github.com/getzep/graphiti
- **Our prior tool (reference only, not submitted):** https://github.com/swiftsaneai/swiftPentest

If any rule in Section 4 ever seems to conflict with what you're doing, the rules page above is the final word.

---

## 2. The idea (the logic, in depth)

**CrownPath is an attack-path triage agent.** It answers a question security teams actually have — *"with all these findings, what do we fix first, and why?"* — by reasoning over how vulnerabilities **chain**, not by sorting them by severity.

**The core logic:**
- A single finding is often low-value on its own. A reflected XSS, an IDOR, an SSRF — each alone might be "medium."
- But findings **chain**: `anonymous entry → XSS → stolen session → IDOR on /api/orders → admin API → customer database`. That chain is **critical**, and it only exists as a *path through connected data*. No severity-sorted list can see it.
- CrownPath models assets, endpoints, findings, techniques, and access as a **graph in FalkorDB**, then uses graph traversal and algorithms to find the **attack paths from an internet-facing entry point to a crown-jewel asset** (e.g. the customer database).
- It prioritizes remediation by **reachability to crown jewels**, not CVSS. And every recommendation is **proven by showing the exact path it severs** — the answer *is* a traced path through the graph.

**The winning insight (the thing no one else will have):** CrownPath finds the **choke-point finding** — the single vulnerability that sits on the most attack paths. *"Fix this one IDOR and 4 of the 6 paths to the customer database collapse, including the highest-value one."* That is a min-cut / centrality result that is **only possible in a graph** and that a scanner's severity list can never produce. This is our headline and our demo money-shot.

**Why this wins (keep these true as you build):**
- The graph is **load-bearing**: remove FalkorDB and there is no chaining, no paths, no choke-point — the product is dead. (This is the single most important judging rule; see 4.3.)
- **Explainability** is built in: the output is a path the judge can see light up. Most teams skip this; we lead with it.
- It's a **security** project built by a **security** team, so we can explain every decision live (required by the rules).

**Track:** We enter **Track 01 — "Agents That Act on Connected Data"** (its text literally lists "triage security findings"). We add **Track 02 — "Agent Memory and Coordination"** *only if* the optional memory layer (Section 9, P2) ships. Name Track 01 always; name Track 02 only if E1 is done.

---

## 3. Folder & repo setup (exact)

The user has created a local working folder (display name "hacker hackathon") containing two subfolders. Normalize paths without spaces:

```
hacker-hackathon/
  swiftpentest-fork/     <- local reference clone of swiftPentest (READ-ONLY, never submitted, never pushed)
  crownpath/             <- THE SUBMISSION REPO (this repo; a GitHub repo the user created and linked to the CLI)
```

**Rules for the two folders:**
- `crownpath/` is where you build. It is the public GitHub repo we submit. This spec lives at its root.
- `swiftpentest-fork/` is a **local clone for reading and lifting files only.** It is not a GitHub fork, it is never pushed, never submitted, and you never develop inside it. If it is not already present, create it once:
  ```bash
  git clone https://github.com/swiftsaneai/swiftPentest.git ../swiftpentest-fork
  ```
- To reuse a file (Section 5), **copy it from `../swiftpentest-fork/` into `crownpath/`** and adapt it there. Record every copied file in `docs/REUSE.md` so the README disclosure is accurate.
- Treat the clone as untrusted input mechanically: read and copy files, do not execute swiftPentest's scripts from inside its folder.

---

## 4. The rules (ALL of them — do not violate, do not forget)

These are the hackathon's own rules. They are reproduced here so you never have to guess. The authoritative copy is the rules URL in Section 1.

1. Participate solo or in a team of up to 4. Each participant may only be part of one team.
2. **Required technology: FalkorDB must be the primary graph database, and it must support a central part of what the product does.**
3. **The graph has to do real work. A visualisation drawn on top of ordinary storage does not qualify: if the product still works once FalkorDB is taken out, the graph is decoration rather than the thing the product runs on.**
4. Run FalkorDB however suits you — Docker, self-hosted, or FalkorDB Cloud. Any language, framework, frontend, or deployment platform may be used alongside it.
5. The challenge is open-ended within the three tracks (Agents That Act on Connected Data; Agent Memory and Coordination; Company Brain). You may enter any or all, and **you must name every track you are entering when you submit.**
6. **Use only data you are allowed to use: public, synthetic, or your own. Do not load private, login-protected, paywalled, personal, or otherwise restricted information into your graph.**
7. The hackathon runs Oct 15 12:01 AM IST → Oct 18 11:59 PM IST. Submissions close at the end of that window.
8. **The main coding and design work must begin after the hackathon starts.** You may discuss ideas, create notes, sketch the graph model, or prepare diagrams beforehand.
9. You may use frameworks, open-source libraries, public APIs, templates, third-party tools, and public datasets. **The original work completed during the hackathon will be judged.**
10. **Every submission must include:** a public source-code repository; a README with setup instructions **and your graph data model**; **the Cypher queries or graph algorithms the product depends on**; a demo video showing the working project; a live deployment (or complete local setup instructions if it can't be deployed); and the track you are entering.
11. **AI coding assistants are allowed, but their use must be disclosed.**
12. **Participants must understand the submitted code and be able to explain the graph model, the queries, the architecture, and the technical decisions.**
13. Projects entirely generated using AI without meaningful participant contribution, verification, or technical understanding may be rejected.
14. Prize pool $20,000. Best project per track wins: iPhone 18 Pro (Track 01), PS5 + GTA VI (Track 02), M6 Mac Mini (Track 03). Every member of a winning team gets the prize. Side prizes: best blog post (AirPods 5), top-50 teams (t-shirt).
15. IP developed during the hackathon belongs to the team. Agree on ownership internally before submitting.
16. Treat everyone with respect.
17. **Harassment, discrimination, plagiarism, or attempts to manipulate the judging process → disqualification.**
18. Failure to follow these rules or the WeMakeDevs Code of Conduct → disqualification.

**How these rules bind CrownPath (do not violate):**
- Rule 2 + 3 → FalkorDB is the spine. The graph does the reasoning. If you ever find yourself computing attack paths in Python instead of via Cypher/graph algorithms, stop — that would make the graph decoration.
- Rule 6 → demo data is **synthetic or from a vulnerable app we host ourselves** (e.g. OWASP Juice Shop / DVWA on localhost). Never scan or ingest a real third-party site's data.
- Rule 8 + 9 → new work in `crownpath/`, judged as new. swiftPentest reuse is limited to generic helpers and disclosed (Section 5).
- Rule 10 → the README must contain the graph data model and the actual Cypher queries. Build these into the README as you go; don't leave them for the end.
- Rule 11 + 12 + 13 → disclose Claude Code use in the README; keep the code understandable and documented so the team can explain it live.

---

## 5. swiftPentest reuse — exact boundary (reuse before you write)

swiftPentest is our own MIT-licensed multi-agent web-pentest tool. **It has no graph database and no FalkorDB** — its state is JSONL files and its "knowledge graph" is an in-memory Python matcher. It already works without any graph. Therefore it **cannot be the base** of CrownPath (that would fail Rule 3 by construction), and it is **not submitted**. But we lift specific, self-contained parts to save time.

**LIFT these (copy into `crownpath/`, adapt, and log in `docs/REUSE.md`):**
- **Vulnerability taxonomy + chaining knowledge** — swiftPentest's technique templates and "chains-with" edges: `config/knowledge/techniques.jsonl` (50 templates; keys `id, class, technique, precondition, signal, cwe, impact, base_p, tier, detect_cmd, refs`) and `config/knowledge/chains.jsonl` (24 edges; keys `from, to, gain, precondition, impact_multiplier, refs`). Chain endpoints are **weakness classes** (the `class` field, e.g. `xss`, `idor`, `ssrf`) plus outcome slugs that are not templates (e.g. `rce`, `session-theft`, `account-takeover`, `privilege-escalation`, `secret-exposure`); one key, `xss-reflected`, matches nothing and must be aliased to `xss`. Class aliases live in `config/classes.jsonl`; per-class fix text in `config/knowledge/remediation.tsv`. `lib/kb.py` only shows how the files are read — its chain walk is in-memory Python and is **not** ported (the graph does that work). These map almost directly onto CrownPath's `Technique` nodes and `CHAINS_TO` edges. **This is the highest-value reuse** and hard for other teams to match.
- **Findings schema** — the finding record is defined in `lib/finding.py` (`create_finding`: `id, class, asset, location, severity, cwe, cvss, confidence, provenance, impact, evidence_refs, reproduce, business_risk, note, ts`); `lib/sarif.py` is its SARIF 2.1.0 export. (`lib/surface.py` is the recon endpoint inventory, not the findings shape — reference only for the `Endpoint` fields `method, host, path`.) Use these to define CrownPath's ingest contract.
- **Synthetic findings generation** — its demo harness (`bin/demo_run.py`) runs detections against a localhost target it owns and produces findings, but it imports four other swiftPentest modules (`oracle`, `challenge`, `finding`, `sarif`), so it is reference only. The target itself, `bin/demo_target.py`, is stdlib-only and self-contained and may be copied. Use the same idea to generate CrownPath's demo `findings.json` (satisfies Rule 6).
- **Proof-discipline concept** — its control-contrast / confidence / retained-rejection idea. Port as `Finding.status` (confirmed | inconclusive | refuted) and `Finding.confidence`. Only `confirmed` findings get attack edges. This is our audit-trail story; reuse the *idea*, write the graph code fresh.

**DO NOT reuse (build fresh — this is the gradeable core and none of it exists in swiftPentest):**
- The entire FalkorDB graph layer: schema, loaders, the Section-7 Cypher queries, algorithm calls.
- The agent loop that queries the graph to decide.
- The MCP server exposing graph tools.
- The explainability output (the traced path as the citation).
- The choke-point analysis (Section 7c) — swiftPentest validates findings in isolation and never chains them into paths to crown jewels. **This cross-finding reasoning is the new value.**

**Do NOT lift** swiftPentest's tmux agent-teams harness, its 9 specialist agents, its hooks, or its DAG engine. They are built for autonomous pentesting, not for "reason over a graph and explain the path." Pulling them in adds complexity we don't want and muddies the new-work story. CrownPath needs **one** clean agent loop, not a pentest swarm.

**README disclosure line (required, Rule 11):** *"CrownPath is new work for Graph Hacks. Its FalkorDB graph layer, attack-path queries, agent, and explainability output were built during the event. It reuses, from our own prior open-source tool swiftPentest, the vulnerability taxonomy and the findings-data schema (see docs/REUSE.md). Built with Claude Code."*

---

## 6. The graph data model (FREEZE THIS FIRST — P0, blocks everything)

Implement as constants/schema in `lib/schema.py` and document in `README` + `docs/graph-model.md`.

**Node labels**
- `Asset {id, name, type, environment, is_crown_jewel, value}` — `type` ∈ host|service|webapp|database; `is_crown_jewel` bool; `value` int (business value).
- `Endpoint {id, url, method, auth_required}`
- `Finding {id, title, vuln_type, cwe, cvss, confidence, status, discovered_at, evidence}` — `vuln_type` ∈ xss|sqli|idor|ssrf|ssti|lfi|open_redirect|csrf|cors|path_traversal|…; `status` ∈ confirmed|inconclusive|refuted; only `confirmed` carry attack edges.
- `Technique {id, name, cwe, capability}` — `capability` ∈ session_theft|rce|data_read|data_write|priv_esc|auth_bypass|ssrf_pivot|…
- `Identity {id, role, privilege_level}` — anonymous(0), user(1), admin(3).

**Relationships (the edges are the product)**
- `(Asset)-[:EXPOSES]->(Endpoint)`
- `(Endpoint)-[:HAS_FINDING]->(Finding)`
- `(Finding)-[:INSTANCE_OF]->(Technique)`
- `(Finding)-[:GRANTS]->(Identity)` — a confirmed finding yields a privilege level
- `(Finding)-[:LEADS_TO]->(Asset)` — opens access to another asset
- `(Technique)-[:CHAINS_TO]->(Technique)` — precondition→postcondition chaining (taxonomy reuse loads here)
- `(Asset)-[:CONNECTS_TO]->(Asset)` — network reachability
- `(Identity)-[:CAN_ACCESS]->(Asset)`

Mark at least one `Asset {is_crown_jewel:true, value:…}` and one anonymous internet-facing `Endpoint {auth_required:false}` as the entry point.

---

## 7. The queries that ARE the product (verify syntax against FalkorDB docs)

**7a. Attack paths from an anonymous entry to a crown jewel** (multi-hop; breaks without the graph):
```cypher
MATCH path = (e:Endpoint {auth_required:false})
      -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->
      (j:Asset {is_crown_jewel:true})
RETURN path
ORDER BY length(path) ASC
LIMIT 10
```
Refine edge set/direction during the build; the invariant is multi-hop reachability from entry to crown jewel.

**Edge-set decision (made during Phase-1 planning, 2026-10-18):** `EXPOSES` (Asset→Endpoint) was added to the traversal set above. Reason: with the originally-listed set (`HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO`), the only edge pointing *into* a `Finding` is `Endpoint-[:HAS_FINDING]->Finding`, so once a path reached an `Asset` it could never descend into that asset's endpoints and their findings — an interior finding such as an IDOR on an internal authenticated endpoint could never lie on any path, and multi-finding chains (the whole premise, §2) would be impossible. Adding `EXPOSES` lets a path go `…→Asset-[:EXPOSES]→Endpoint-[:HAS_FINDING]→Finding→…`. `INSTANCE_OF` and `CHAINS_TO` remain excluded from traversal (a `Technique` node has no outgoing edge that reaches an `Asset`, so it is a dead branch for reachability; those edges serve explanation, not pathfinding). The spike issue confirms this live on the demo graph.

**7b. Shortest / highest-value path** — use FalkorDB's shortest-path support and score paths by `∏ finding.confidence × jewel.value ÷ length(path)` so ranking reflects *likelihood × impact*, not severity.

**7c. The choke-point finding (our headline).** Which single `Finding` lies on the most crown-jewel attack paths? Reliable method: enumerate paths (7a), count each Finding's occurrences, rank. Fancier: a centrality measure (betweenness / PageRank) over the attack subgraph — **verify the exact FalkorDB algorithm name in the docs before using it.** Output: *"Fix Finding X → sever N of M paths to <crown jewel>, incl. the highest-value one."*

**7a must work end to end before anything is built on top of it.** These three queries are what the judges grade; put them verbatim in the README (Rule 10).

**Verified FalkorDB syntax facts (from docs.falkordb.com, 2026-10-18 — do not re-research):**
- Variable-length syntax `-[:A|B|C*1..8]->` (multiple types `|`-separated, bounds `*min..max`), named paths `MATCH p = (...)`, `length(p)`, `nodes(p)`, `relationships(p)`, and list/predicate functions (`[n IN nodes(p) WHERE n.x | n.y]`, `all/any/none/single`, `reduce`, `size`) are all documented and supported. The `*1..8` bound and the specific `|` edge set in 7a are **not yet tested live** — that is what the spike issue proves.
- `shortestPath((a)-[*]->(b))` and `allShortestPaths(...)` exist but **require both endpoints bound first** (via `MATCH ... WITH a,b` or a `MATCH (a),(b)`) and **forbid property filters inside the pattern**, and the min edge count may only be 0 or 1. For weighted "highest-value" ranking (7b), prefer the procedure `algo.SPpaths` / `algo.SSpaths` (`CALL algo.SPpaths({sourceNode, targetNode, relTypes:[...], weightProp, costProp, maxCost, maxLen, relDirection:'outgoing', pathCount}) YIELD path, pathWeight, pathCost`). Note these take `weightProp`/`costProp` (minimised sums) — our score `∏confidence × value ÷ length` is not a simple edge-weight sum, so 7b computes the score in Cypher over enumerated 7a paths (or over `algo.SSpaths` output), not purely inside the procedure.
- For 7c, the centrality procedure is **`algo.betweenness({nodeLabels:[...], relationshipTypes:[...], samplingSize, samplingSeed}) YIELD node, score`** (set `samplingSeed` for reproducibility; default seed is time-based). `algo.pageRank` is the alternative. The **primary** 7c method stays the deterministic path-enumeration count (enumerate 7a paths, count each Finding's occurrences) — betweenness is a secondary cross-check only.
- Range index: `CREATE INDEX FOR (n:Label) ON (n.prop)` (no documented `IF NOT EXISTS`; guard by checking `CALL db.indexes()` or tolerating the error). Python client: `pip install FalkorDB`; `from falkordb import FalkorDB; db = FalkorDB(host='localhost', port=6379); g = db.select_graph('crownpath')`. Docker: `falkordb/falkordb:latest`, ports 6379 (server) + 3000 (browser UI).

---

## 8. Agent + architecture

- **Agent loop** (`agent/run.py`): takes a question ("what do we fix first / what's the real risk?"), calls graph tools, returns a **ranked remediation list where every item cites its attack path.** The decision must be justified by the path and the choke-point result, never by CVSS.
- **Graph tools exposed via MCP** (`mcp/server.py`): `ingest_findings`, `find_attack_paths(crown_jewel)`, `shortest_path(a,b)`, `rank_by_reachability`, `choke_points`. Exposing them over MCP directly hits Track 01's "tool selection through MCP" focus. FalkorDB does ship an official MCP server (`FalkorDB/FalkorDB-MCPServer`, per docs.falkordb.com/genai-tools/mcpserver), but it exposes generic Cypher/graph-management tools, not these domain tools, so we wrap our own thin one and mention the official server in the README as an alternative for raw Cypher access.
- **Explainability output** (`ui/`): minimal FastAPI + one static page (Cytoscape.js or vis-network) that highlights the traced path. **FalkorDB Browser (port 3000) is the acceptable fallback** for the demo if custom UI runs short.

---

## 9. Scope tiers (cut from the bottom; never polish a lower tier while a higher one is unproven)

**P0 — the winning demo (must have):** FalkorDB running; schema + findings loader; synthetic data loaded; query 7a working; the choke-point analysis (7c — the headline "fix X → sever N of M paths"); a basic agent loop returning a ranked, path-cited answer; the path shown (FalkorDB Browser is fine). A flawless short video of this beats anything half-built. *(7c is P0: it is the demo money-shot, and its primary method is a deterministic count over 7a paths — it depends only on 7a, not on the MCP server or custom UI.)*

**P1 — differentiators:** the MCP server; a small custom UI highlighting the path.

**P2 — bonus (only if P0+P1 are solid):** Graphiti-on-FalkorDB memory → adds **Track 02** ("remembers this asset regressed since last scan"); live deployment; recording against the self-hosted vulnerable app.

**Cut-first order when time tightens:** custom UI (use FalkorDB Browser) → Graphiti/Track-2 → live deploy (ship local-setup instructions + video instead). Never cut: 7a, the agent loop, the README graph model + queries, the demo video.

---

## 10. Build workflow — issues, models, and the freeze-first rule

**Model strategy:** The user generates the issues with **Opus** (strong decomposition) and the hard design artifacts (schema, the three queries, the choke-point method). Implementation issues are then coded by **Sonnet** sessions. This only works if issues are detailed enough that **Sonnet makes zero architecture decisions** — every issue must carry context, exact file paths, acceptance criteria, and its dependencies. If an issue would force a design choice, it's not ready; push the choice up to an Opus/P0 issue first. This also conserves the Opus budget against usage limits.

**Freeze-first rule (prevents multi-session collisions):** The first issues done, before anything fans out, must be the foundation (Epic A). Nothing else starts until the schema, the data contract, and the agent-tool interface are frozen and merged. Sessions hand off via `docs/HANDOFF.md` (what's done / next / broken) so the next session starts with full context. One module/file per issue; whoever's session is active owns merges.

**Issue hygiene:** every issue gets a priority label (`P0`/`P1`/`P2`), an area label (`area:graph|agent|mcp|ui|data|docs|demo`), explicit `depends-on`, and a short acceptance-criteria checklist. Order the backlog by dependency.

---

## 11. Issue backlog (expand each stub into a full GitHub issue)

**Epic A — Foundation (P0, serial, blocks everything)**
- A1 Repo scaffold: layout (Section 12), `requirements.txt`, `.gitignore`, `CLAUDE.md` distilling this spec.
- A2 Dockerized FalkorDB + `make up`; verify a trivial Cypher query returns.
- A3 README skeleton with the required sections (setup, graph data model, Cypher queries, demo, track, disclosure).
- A4 Freeze graph schema (Section 6) in `lib/schema.py` + `docs/graph-model.md`.
- A5 Freeze findings ingest contract → `docs/findings.schema.json`.
- A6 Freeze agent-tool interface stubs → `lib/tools.py`.
- A7 Write the fixed demo scenario → `docs/demo-scenario.md`.
- A8 `docs/REUSE.md` + `docs/HANDOFF.md` initialized.

**Epic B — Graph core (P0)**
- B1 `lib/graph.py`: FalkorDB connection + schema init (indexes on node ids).
- B2 `lib/ingest.py`: `findings.json` → nodes/edges; only `confirmed` findings get attack edges.
- B3 Seed `Technique` nodes + `CHAINS_TO` edges from the lifted taxonomy (Section 5).
- B4 Query 7a (entry → crown-jewel paths) in `lib/queries.py`; unit-tested on the demo graph.
- B5 Query 7b (shortest / highest-value) + scoring.
- B6 `data/gen_findings.py` synthetic generator (and/or import a self-generated `findings.json`).

**Epic C — Agent (P0→P1)**
- C1 Implement `lib/tools.py` behind the frozen interface (wrap B4/B5 and later 7c).
- C2 `agent/run.py`: question → graph tools → ranked remediation list, each item citing its path.
- C3 Prompt + output format: justification by path + choke-point, never CVSS.

**Epic D — Differentiators (P1)**
- D1 `mcp/server.py`: MCP server exposing the graph tools; agent consumes via MCP.
- D2 `lib/chokepoints.py`: query 7c; output "fix X → sever N of M paths."
- D3 `ui/`: minimal FastAPI + one page highlighting the path (Cytoscape/vis-network); FalkorDB Browser fallback.

**Epic E — Track-2 bonus + polish (P2)**
- E1 Graphiti-on-FalkorDB memory across scans (adds Track 02).
- E2 Run the generator against a self-hosted vulnerable app; capture a real demo `findings.json`.
- E3 Live deployment (or finalize local-setup instructions if skipped).

**Epic F — Submission (P0, human-owned at the end)**
- F1 README finalize: setup, graph data model, the Cypher queries/algorithms, architecture diagram, AI + reuse disclosure.
- F2 Demo video (≤3–4 min): problem → findings loaded → agent traces the path → choke-point recommendation → path lights up. Start recording the moment the P0 path works.
- F3 Blog post (AirPods side prize) drafted from this spec + the build.
- F4 Submit on WeMakeDevs: repo, README, video, deployment/local-setup, track(s) named.

---

## 12. Submission repo layout (`crownpath/`)

```
crownpath/
  BUILD_SPEC.md            this document
  CLAUDE.md                distilled build context for every session
  README.md                setup + graph data model + Cypher queries + track + disclosure
  requirements.txt
  docker-compose.yml       FalkorDB
  docs/
    graph-model.md         frozen schema
    findings.schema.json   frozen ingest contract
    demo-scenario.md       the fixed story the video shows
    REUSE.md               every file lifted from swiftPentest (for the disclosure)
    HANDOFF.md             updated at the end of each work session
  lib/
    schema.py  graph.py  ingest.py  queries.py  chokepoints.py  tools.py
  agent/
    run.py  prompts/
  mcp/
    server.py
  ui/                      minimal path-rendering page (optional)
  data/
    findings.json  gen_findings.py
  tests/                   unit tests for queries + ingest
```

---

## 13. Submission checklist (Rule 10 — nothing optional here)

- [ ] Public repo (`crownpath/`), clean history dated within the event.
- [ ] README: setup instructions, **graph data model**, **the exact Cypher queries / algorithms**, architecture, AI + swiftPentest-reuse disclosure.
- [ ] Demo video (≤3–4 min) showing the working product: findings → traced attack path → choke-point recommendation.
- [ ] Live deployment **or** complete local-setup instructions.
- [ ] Track(s) named: Track 01 (always); Track 02 only if E1 shipped.
- [ ] Blog post submitted (side prize).
- [ ] Team can explain the graph model, queries, and architecture live (Rule 12).

---

## 14. Anti-drift guardrails (Claude Code: DO / DON'T)

**DO:** build P0 first and prove it end to end; verify FalkorDB syntax in the docs; keep the graph as the thing that computes paths; put the Cypher in the README as you write it; update `HANDOFF.md` at the end of each session; copy reusable files from the fork and log them.

**DON'T:** don't fork or build inside `swiftpentest-fork/`; don't pull in swiftPentest's agent swarm/hooks/DAG; don't compute attack paths in Python instead of the graph; don't ingest real third-party data (synthetic / self-hosted only); don't web-research for ideas; don't gold-plate P2 while P0 is unproven; don't invent a FalkorDB API — verify it; don't leave the README graph-model/queries for the final hour.

**If blocked:** stop, write the blocker and your best option into `docs/HANDOFF.md`, and leave the decision for the human rather than improvising a design change.

*Note: the CLI has Claude-for-Chrome access available if a step genuinely needs a live browser (e.g. checking the deployed demo or the FalkorDB Browser view). Use it only for that — not for idea research.*
