# CrownPath

An attack-path triage agent that reasons over how vulnerabilities chain, on FalkorDB.

## What it does

CrownPath answers the question security teams actually have — "with all these findings,
what do we fix first, and why?" — by reasoning over how vulnerabilities **chain**, not by
sorting them by severity. A single finding is often low-value on its own, but findings
chain into attack paths — anonymous entry → XSS → stolen session → IDOR → admin API →
customer database — and that chain is critical, visible only as a path through connected
data. CrownPath models assets, endpoints, findings, techniques, and access as a graph in
FalkorDB, traverses it to find attack paths from an internet-facing entry point to a
crown-jewel asset, and prioritizes remediation by reachability rather than CVSS. Its
headline result is the **choke-point finding**: the single vulnerability that sits on the
most attack paths — "fix this one IDOR and 4 of the 6 paths to the customer database
collapse, including the highest-value one" — a result that only exists because the graph
computed it.

On the demo estate the answer is:

> Fix IDOR on /api/orders -> sever 4 of 6 paths to Customer database, including the highest-value one.

## Track(s)

Track 01 — Agents That Act on Connected Data.

Track 02 — Agent Memory and Coordination.

**Memory model (Track 02).** The graph remembers across scans. Every `Finding` carries
`first_seen`, `last_seen` and a `scans` list of scan ids; the agent's sixth tool,
`whats_changed(since, until)` (`lib/memory.py`), diffs two scans entirely in Cypher and
reports findings added/removed and **regressed assets** — e.g. "scan-2 added a confirmed IDOR
on Orders API, which opens 4 new paths to the customer database (2 → 6)". Per-scan path
membership reuses the 7a traversal with a filter on `scans`, so the graph decides which paths
existed when. We chose native graph memory over Graphiti because our findings are already
structured (no LLM extraction needed) and the numbers must be deterministic; see
`docs/HANDOFF.md`. Load the demo history with `python -m lib.memory --demo`.

## Architecture

```
 data/findings.json ──► lib/ingest.py ──►  ┌──────────────────────────────┐
 (synthetic, schema-    (validate, confirmed│  FalkorDB graph              │
  checked)               only get attack    │  Asset·Endpoint·Finding·     │
 lib/seed_taxonomy.py ─► edges)             │  Technique·Identity + 8 edges│
 (77 Techniques,                            │                              │
  24 CHAINS_TO)                             │  Cypher: 7a attack paths     │
                                            │          7b path scores      │
                                            │          7c choke points     │
                                            │          memory diff (E1)    │
                                            └──────────────┬───────────────┘
                                                           │
                lib/queries.py · lib/chokepoints.py · lib/memory.py
                                                           │
                                  lib/tools.py  (6 graph tools)
                                   │                        │
              crownpath_mcp/server.py (MCP, stdio)          │
                                   │                        │
                       agent/run.py  ◄──────────────────────┘
        (LLM tool-use loop: Anthropic or any OpenAI-compatible API,
         or --no-llm deterministic path)  ──► agent/format.py
                                   │
                    ui/app.py (FastAPI) + Cytoscape page
        /api/graph · /api/paths · /api/chokepoints · /api/changes · /api/agent
```

**FalkorDB is load-bearing.** There is no in-memory copy of the estate and no path logic
outside the database. Take FalkorDB away and there are no attack paths, no choke point, no
scan memory and no explainable path to show — the product has nothing left to compute. The
agent never ranks by CVSS; every recommendation cites the exact graph path it sits on.

## Graph data model

Frozen schema (`lib/schema.py`, `docs/graph-model.md`).

```
(Asset)-[:EXPOSES]->(Endpoint)-[:HAS_FINDING]->(Finding)-[:INSTANCE_OF]->(Technique)
                                                   │  │                       │
                                      [:GRANTS]────┘  └────[:LEADS_TO]        └─[:CHAINS_TO]─►(Technique)
                                          ▼                       ▼
                                     (Identity)─[:CAN_ACCESS]─►(Asset)◄─[:CONNECTS_TO]─(Asset)
```

| Node | Properties |
|---|---|
| `Asset` | `id, name, type (host\|service\|webapp\|database), environment, is_crown_jewel, value` |
| `Endpoint` | `id, url, method, auth_required` |
| `Finding` | `id, title, vuln_type, cwe, cvss, confidence, status (confirmed\|inconclusive\|refuted), discovered_at, evidence` (+ `first_seen, last_seen, scans` from the memory layer) |
| `Technique` | `id, name, cwe, capability` — 77 nodes seeded from the swiftPentest taxonomy |
| `Identity` | `id, role (anonymous\|user\|admin), privilege_level (0\|1\|3)` |

| Edge | Meaning |
|---|---|
| `(Asset)-[:EXPOSES]->(Endpoint)` | the asset serves this endpoint |
| `(Endpoint)-[:HAS_FINDING]->(Finding)` | a finding was discovered here |
| `(Finding)-[:INSTANCE_OF]->(Technique)` | the finding's attack technique |
| `(Finding)-[:GRANTS]->(Identity)` | a confirmed finding yields this privilege level |
| `(Finding)-[:LEADS_TO]->(Asset)` | a confirmed finding opens access to this asset |
| `(Technique)-[:CHAINS_TO]->(Technique)` | precondition → postcondition chaining (24 edges) |
| `(Asset)-[:CONNECTS_TO]->(Asset)` | network reachability |
| `(Identity)-[:CAN_ACCESS]->(Asset)` | what an identity at that privilege can reach |

**Invariants.** Only `confirmed` findings carry attack edges (`GRANTS`/`LEADS_TO`);
`inconclusive`/`refuted` findings stay in the graph for audit but never lie on a path. The
graph has at least one crown jewel (`Asset {is_crown_jewel:true}`) and one anonymous entry
(`Endpoint {auth_required:false}`). `INSTANCE_OF` and `CHAINS_TO` explain a finding but are not
traversed for reachability.

The demo estate (`docs/demo-scenario.md`, generated by `data/gen_findings.py`, all
synthetic): 4 assets, 6 endpoints, 3 identities, 8 findings (one deliberately `inconclusive`)
and exactly 6 anonymous-entry → customer-database paths.

## The Cypher queries / algorithms the product depends on

All three run against FalkorDB (verified live on FalkorDB graph module v4.22.0). Source of
truth: `lib/queries.py` (7a, 7b) and `lib/chokepoints.py` (7c); verification transcript in
`docs/graph-model.md`.

### 7a — attack paths from an anonymous entry to a crown jewel

```cypher
MATCH path = (e:Endpoint {auth_required:false})
      -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->
      (j:Asset {is_crown_jewel:true, id:$jid})
RETURN path
ORDER BY length(path) ASC
```

Returns exactly the 6 hand-derived paths on the demo graph. (No `LIMIT`: FalkorDB's `LIMIT`
does not correctly bound variable-length path enumeration — a limit at or below the true count
returned too few rows — so all paths are enumerated and the display list is sliced afterwards.)

### 7b — likelihood × impact scoring

`score = ∏ finding.confidence × crown_jewel.value ÷ length(path)`, so ranking reflects
likelihood × impact, never CVSS. It is evaluated in Cypher on the 7a paths (the head of every
7c query):

```cypher
WITH path, reduce(c = 1.0, n IN nodes(path) |
       CASE WHEN 'Finding' IN labels(n) THEN c * n.confidence ELSE c END)
     * j.value / length(path) AS score
```

`rank_by_reachability` applies the same formula (`queries.score_path`, a pure function) to
the paths 7a returns to order remediations; scores on the demo are 12.75, 9.92, 8.50, 7.08,
5.00, 4.00. A building-block query for arbitrary node pairs (`queries.shortest_path`) uses the
same traversal between two bound node ids.

### 7c — the choke-point finding (the headline)

Which single `Finding` lies on the most crown-jewel attack paths? Counted in Cypher: enumerate
the 7a paths, `UNWIND` each path's findings, count paths per finding (a finding on N paths,
removed, severs exactly those N):

```cypher
// head: 7a path enumeration + 7b score (above), then
RETURN count(path), max(score)                      // M paths, best score

UNWIND [n IN nodes(path) WHERE 'Finding' IN labels(n)] AS f
RETURN f.id, count(path) AS severed, sum(score) AS summed, max(score) AS best_on_path
ORDER BY severed DESC, summed DESC
```

Demo result: `f:idor` 4/6 (and on the highest-value path), `f:ssrf` 3/6, every other finding
1/6, `f:csrf` (inconclusive) 0/6. Proof by deletion: after
`MATCH (n {id:'f:idor'}) DETACH DELETE n`, 7a returns 2 paths — 4 severed.

Cross-check (logged, never overrides the ranking): FalkorDB's centrality algorithm.

```cypher
CALL algo.betweenness({
  nodeLabels: ['Endpoint', 'Finding', 'Identity', 'Asset'],
  relationshipTypes: ['EXPOSES', 'HAS_FINDING', 'LEADS_TO', 'GRANTS', 'CAN_ACCESS', 'CONNECTS_TO'],
  samplingSeed: 42
})
YIELD node, score
WHERE 'Finding' IN labels(node)
RETURN node.id, score
```

(Whole-graph betweenness measures a different thing — how often a node bridges *any* pair —
than "how many crown-jewel paths pass through it", so it does not rank `f:idor` first; the
path count is the authoritative method.)

### Memory — what changed between scans (Track 02)

`lib/memory.py` reuses 7a with a per-scan filter. Paths that exist in scan `$scan`:

```cypher
MATCH path = (e:Endpoint {auth_required:false})
      -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->
      (j:Asset {id:$jewel, is_crown_jewel:true})
WHERE all(n IN nodes(path) WHERE n.scans IS NULL OR $scan IN n.scans)
RETURN count(path)
```

Findings added between scans: `MATCH (f:Finding) WHERE $until IN f.scans AND NOT $since IN f.scans`.
Regressed assets: assets exposing a newly confirmed finding that lies on a crown-jewel path in
the later scan (`WHERE f IN nodes(path) AND all(...)`). Demo: scan-1 has 2 paths, scan-2 has 6;
`f:idor` is new and `asset:api` is flagged as regressed (+4 paths).

## Setup

Python 3.10+ (developed on 3.13). Every option below ends with the same three commands.

### Option A — Live demo

**Live URL: <https://crownpath-st2u.onrender.com/>** (Render free tier: the first request after idle can take about a minute to wake).
The page shows the graph, traces the 6 paths, highlights the choke point and has an
"Ask the agent" panel. The agent endpoint is rate-limited and falls back to a recorded sample
run, so it never shows an error.

### Option B — Run locally with Docker

Needs Docker, Python and GNU `make`. Without `make` (e.g. plain Windows) run the one-line command behind each target — they are listed in the `Makefile`.

```bash
git clone https://github.com/Harsh-Yadav-664/CrownPath && cd CrownPath
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
cp .env.local.example .env
pip install -r requirements.txt
make up          # docker compose up -d  (FalkorDB on 6379, browser UI on 3000)
python scripts/ping.py      # expect PING OK
make seed        # taxonomy + demo findings
make demo        # ranked, path-cited answer + the choke point (works with no LLM key)
make ui          # http://localhost:8000
```

Optional: `make memory` loads two dated scans (Track 02) so the "What changed?" button works.
The FalkorDB Browser at <http://localhost:3000> also lets you run the Cypher above by hand.

### Option C — Point at your own FalkorDB

```bash
cp .env.example .env
# fill in FALKORDB_HOST / FALKORDB_PORT / FALKORDB_USERNAME / FALKORDB_PASSWORD / FALKORDB_SSL
python scripts/ping.py   # verify the connection
make seed && make demo && make ui
```

Our FalkorDB Cloud credentials are never shared. Judges run CrownPath either against their
own FalkorDB instance (Option C) or against local Docker (Option B).

### Using a real LLM (optional)

By default `make demo` is deterministic. To let a model choose the graph tools itself, set one
of these in `.env` and run `python -m agent.run`:

- `ANTHROPIC_API_KEY` (model via `CROWNPATH_MODEL`), or
- free `GEMINI_API_KEY` (gemini-2.5-flash) and/or `GROQ_API_KEY` (openai/gpt-oss-120b): tried in
  that order, each falling back to the next on a rate limit or outage, then to the deterministic
  answer; or any OpenAI-compatible provider via `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`.

The model sees the same tool schemas the MCP server exposes (`python -m crownpath_mcp.server`).

### Tests

```bash
CROWNPATH_GRAPH=crownpath_test pytest -q   # tests reset the graph they run on; they default to crownpath_test
```

### Loopback capture (optional, Rule 6)

`python data/capture_findings.py` starts `data/demo_target.py` — our own intentionally weak
app, bound to 127.0.0.1 only — probes it with control/payload request pairs and writes
`data/findings.captured.json` (the scripts refuse any non-loopback host). Ingest it with
`python -m lib.seed_taxonomy --all --findings data/findings.captured.json`. The default demo
stays the synthetic `data/findings.json` so the numbers are deterministic.

## Demo

_Demo video link: added at submission._ Walkthrough: load the findings → the agent traces the
paths → the choke point is named ("fix the IDOR, sever 4 of 6") → click **Trace attack paths**
and **Show choke point** and watch the paths converge on the crown jewel and the severed ones dim.
The fixed scenario is `docs/demo-scenario.md`; a recorded agent run is in `docs/sample-run.md`
(and `data/sample_answer.json`).

## Disclosure

> CrownPath is new work for Graph Hacks. Its FalkorDB graph layer, attack-path queries, agent, and explainability output were built during the event. It reuses, from our own prior open-source tool swiftPentest, the vulnerability taxonomy and the findings-data schema (see docs/REUSE.md). Built with Claude Code.

## License

MIT — see [LICENSE](LICENSE).
