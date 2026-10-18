# CrownPath graph model

> The full frozen schema (node labels, properties, enums, the 8 edges, invariants) is
> authored by issue #4 (A4). This file currently holds the **live-verified Cypher** from the
> issue #10 spike so later Epic-B issues build only on syntax proven against the real database.

## Verified live Cypher

**Verified:** 2026-10-18 against the team's **FalkorDB Cloud** instance (graph module
**v4.22.0**, enterprise; client `falkordb-py` 1.8.0; `ssl=false`). Loaded the exact
demo-scenario graph (`docs/demo-scenario.md`, issue #7) into a scratch graph
`crownpath_spike`, ran the queries, then deleted the scratch graph. Reproduce with
`python scripts/spike_7a.py`.

### 7a — attack paths from an anonymous entry to a crown jewel (WORKS AS SPEC'D)
The BUILD_SPEC §7 query runs unchanged (with the `EXPOSES` edge already in the set). Exact
form used:

```cypher
MATCH path = (e:Endpoint {auth_required:false})
      -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->
      (j:Asset {is_crown_jewel:true})
RETURN [n IN nodes(path) | coalesce(n.id, n.name)] AS hops, length(path) AS len
ORDER BY len ASC
```

**Result: exactly 6 paths** from anonymous entries to `asset:db`, matching the hand-derived
set in `docs/demo-scenario.md` verbatim:

| # | len | path | IDOR? |
|---|-----|------|-------|
| 1 | 5 | ep:metrics → f:ssrf → asset:admin → ep:adminapi → f:sqli → asset:db | — |
| 2 | 6 | ep:search → f:xss → id:user → asset:api → ep:orders → **f:idor** → asset:db | ✓ |
| 3 | 6 | ep:go → f:redirect → id:user → asset:api → ep:orders → **f:idor** → asset:db | ✓ |
| 4 | 6 | ep:login → f:authbypass → id:user → asset:api → ep:orders → **f:idor** → asset:db | ✓ |
| 5 | 6 | ep:metrics → f:ssrf → asset:admin → asset:api → ep:orders → **f:idor** → asset:db | ✓ |
| 6 | 6 | ep:metrics → f:ssrf → asset:admin → ep:adminapi → f:massassign → id:admin → asset:db | — |

The inconclusive `f:csrf` (no attack edges) appears on **0** paths, as intended.

### 7b — path scoring (`∏ confidence × jewel.value ÷ length`)
Scored in Python/Cypher over the enumerated 7a paths (not a native weighted-path call — the
score is not a simple edge-weight sum). Highest-scoring path is the shortest, highest-confidence
user-session IDOR path:

```
score=12.75 len=6  ep:search → f:xss → id:user → asset:api → ep:orders → f:idor → asset:db
score= 9.92 len=6  ep:login  → f:authbypass → … → f:idor → asset:db
score= 8.50 len=6  ep:go     → f:redirect   → … → f:idor → asset:db
score= 7.08 len=6  ep:metrics→ f:ssrf → asset:admin → asset:api → … → f:idor → asset:db
score= 5.00 len=6  ep:metrics→ f:ssrf → asset:admin → ep:adminapi → f:massassign → id:admin → asset:db
score= 4.00 len=5  ep:metrics→ f:ssrf → asset:admin → ep:adminapi → f:sqli → asset:db
```

### 7c — choke-point (count each Finding's occurrence across the 7a paths)
```
f:idor: 4/6    f:ssrf: 3/6    f:sqli/f:xss/f:redirect/f:authbypass/f:massassign: 1/6
```
**`f:idor` is the choke point: on 4 of 6 paths.** Proven by deletion: after
`MATCH (n {id:'f:idor'}) DETACH DELETE n`, re-running 7a returns **2 paths** (4 severed),
exactly the two SSRF→admin paths (SQLi and mass-assignment). Headline holds verbatim:
*"Fix f:idor (IDOR on /api/orders) → sever 4 of 6 paths to the Customer database, including
the highest-value one."*

### ⚠️ Known limitation found live — do NOT use Cypher `LIMIT` to cap variable-length paths
`… ORDER BY len ASC LIMIT 3` returned **only 2 rows**, not 3. FalkorDB's `LIMIT` does not
correctly constrain variable-length path enumeration (consistent with the docs' "LIMIT
doesn't constrain eager operations" note). **Correctness rule for Epic B:** enumerate all
paths, then slice/limit in Python. A `LIMIT` larger than the true path count (e.g. the demo's
6 paths with `LIMIT 10`) is harmless for display, but any cap at or below the real count
undercounts — never rely on it. `lib/queries.py` (#15) and `lib/chokepoints.py` (#21) must
collect-then-slice.
