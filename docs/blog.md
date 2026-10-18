# Fix one IDOR, sever four of six attack paths: reasoning over a FalkorDB graph

Every security team has the same pile: a scanner report with hundreds of findings sorted by
CVSS. The question that matters is different — *what do we fix first, and why?* — and a
severity-sorted list cannot answer it, because risk is not a property of a single finding. It
is a property of **paths**.

A reflected XSS is "medium". An IDOR on an internal orders endpoint is "high" but sits behind a
login. Chained, they are the whole story: anonymous visitor → XSS → stolen session → IDOR →
customer database. That chain only exists as a path through connected data. That is a graph
problem, so we built CrownPath on FalkorDB for the Graph Hacks hackathon.

## The model

Five node types — `Asset`, `Endpoint`, `Finding`, `Technique`, `Identity` — and eight edges.
The ones that matter for reasoning are `EXPOSES`, `HAS_FINDING`, `GRANTS` (a confirmed finding
yields a privilege level), `LEADS_TO` (it opens another asset), `CAN_ACCESS` and `CONNECTS_TO`.
One rule keeps it honest: **only `confirmed` findings carry attack edges**. Inconclusive and
refuted findings stay in the graph as an audit trail but can never be part of a path.

The demo estate is synthetic: a storefront, an orders API, an admin console and a customer
database (the crown jewel), with eight findings. The `Technique` nodes and `CHAINS_TO` edges
come from the vulnerability taxonomy of our own earlier open-source tool, swiftPentest, and are
disclosed in the repo.

## The three queries

**Attack paths.** One variable-length match finds every route from an anonymous endpoint to
the crown jewel:

```cypher
MATCH path = (e:Endpoint {auth_required:false})
      -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->
      (j:Asset {is_crown_jewel:true})
RETURN path ORDER BY length(path)
```

It returns exactly six paths.

**Scoring.** Each path is scored `∏ confidence × jewel value ÷ length` — likelihood times
impact, not CVSS — using `reduce()` over the path's nodes.

**The choke point.** Unwind the findings on every path and count paths per finding:

```cypher
UNWIND [n IN nodes(path) WHERE 'Finding' IN labels(n)] AS f
RETURN f.id, count(path) AS severed
ORDER BY severed DESC
```

`f:idor` sits on four of the six paths, including the highest-value one. Delete it from the
graph and re-run the first query: two paths remain. The headline writes itself — *fix the IDOR
on /api/orders and four of six paths to the customer database collapse.* A scanner's severity
list cannot say that, because the number only exists as a property of the graph.

We also cross-checked with FalkorDB's `algo.betweenness`. It does not rank the IDOR first, and
that is instructive: betweenness measures how often a node bridges *any* two nodes, not how many
*crown-jewel* paths run through it. The path count is the authoritative method and betweenness
is a logged sanity check.

One thing we learned the hard way: Cypher `LIMIT` does not reliably bound variable-length
path enumeration (a `LIMIT` below the true count returned too few rows), so we enumerate all
paths and slice for display afterwards.

## The agent and the explanation

An agent wraps the graph as six tools, exposed over MCP. It can run with Anthropic or any
OpenAI-compatible model, or fully deterministically with no key. Every recommendation cites the
exact path it sits on, and the UI (FastAPI + Cytoscape) lights that path up, so the judge sees
the answer instead of taking our word for it. The public endpoint is rate-limited and falls back
to a recorded run so it never shows an error.

## Memory across scans

For the memory track, findings carry `first_seen`, `last_seen` and the list of scans they
appeared in. `whats_changed(scan-1, scan-2)` runs entirely in Cypher: scan-2 added a confirmed
IDOR, the Orders API **regressed**, and the number of crown-jewel paths went from 2 to 6. We
considered Graphiti but our findings are already structured, so LLM entity extraction would add
nondeterminism and nothing else.

## Honesty notes

The data is synthetic (plus a capture from our own app on loopback, which refuses any other
host). AI assistance, including Claude Code, was used and is disclosed in the README; we
verified the work ourselves — live runs against FalkorDB Cloud, a fresh-clone run on local
Docker, and tests that reset and rebuild the graph.

Code, queries and setup: the CrownPath repository linked from the submission.
