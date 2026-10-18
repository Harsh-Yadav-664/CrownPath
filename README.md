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

<!-- diagram filled by issue #26 (F1) -->

## Graph data model

<!-- filled by issue #4 (A4); mirrors docs/graph-model.md -->

## The Cypher queries / algorithms the product depends on

<!-- filled by issues #10 (7a), #16 (7b), #21 (7c) -->

## Setup

### Option A — Live demo

<!-- public URL filled by issues #25 (E3) / #26 (F1) -->

### Option B — Run locally with Docker

```bash
cp .env.local.example .env
pip install -r requirements.txt
make up
make seed
make demo
make ui
```

FalkorDB runs on port `6379` (server) and `3000` (browser UI).

### Option C — Point at your own FalkorDB

```bash
cp .env.example .env
# fill in FALKORDB_HOST / FALKORDB_PORT / FALKORDB_USERNAME / FALKORDB_PASSWORD / FALKORDB_SSL
python scripts/ping.py   # verify the connection
make seed && make demo
```

Our FalkorDB Cloud credentials are never shared. Judges run CrownPath either against their
own FalkorDB instance (Option C) or against local Docker (Option B).

<!-- filled by F1 -->

## Demo

<!-- video link + walkthrough filled by issues #27 (F2) / #26 (F1) -->

## Disclosure

> CrownPath is new work for Graph Hacks. Its FalkorDB graph layer, attack-path queries, agent, and explainability output were built during the event. It reuses, from our own prior open-source tool swiftPentest, the vulnerability taxonomy and the findings-data schema (see docs/REUSE.md). Built with Claude Code.

## License

MIT
