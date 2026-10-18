# CrownPath demo scenario (frozen)

Frozen by issue #7 (A7). This is the single fixed scenario the generator (#12/B6) emits,
B4's unit test asserts against, and the demo video shows. Every node and edge is fully
enumerated below — no invention downstream.

## Narrative

A storefront web app is the internet-facing entry. Three anonymous web weaknesses
(reflected XSS, open redirect, auth bypass) each yield a logged-in *user* session. A user
can reach the internal Orders API, whose `/api/orders` endpoint has an IDOR that reads the
customer database directly. Separately, an unauthenticated `/metrics` SSRF on the API host
pivots to the Admin console, which reaches the database by SQLi, by a mass-assignment
privilege escalation to admin, and (via network) back to the Orders API. The IDOR is the
choke point.

## Nodes

### Assets

| id | name | type | environment | is_crown_jewel | value |
|---|---|---|---|---|---|
| `asset:web` | Storefront | webapp | prod | false | 20 |
| `asset:api` | Orders API | service | prod | false | 40 |
| `asset:admin` | Admin console | service | prod | false | 60 |
| `asset:db` | Customer database | database | prod | **true** | 100 |

### Identities

| id | role | privilege_level |
|---|---|---|
| `id:anon` | anonymous | 0 |
| `id:user` | user | 1 |
| `id:admin` | admin | 3 |

### Endpoints

| id | url | auth_required | note |
|---|---|---|---|
| `ep:search` | /search | false | entry |
| `ep:go` | /go | false | entry |
| `ep:login` | /login | false | entry |
| `ep:metrics` | /metrics | false | entry |
| `ep:orders` | /api/orders | true | |
| `ep:adminapi` | /admin | true | |

### Findings

| id | vuln_type | cwe | cvss | confidence | status |
|---|---|---|---|---|---|
| `f:xss` | xss | CWE-79 | 6.1 | 0.9 | confirmed |
| `f:redirect` | open_redirect | CWE-601 | 5.0 | 0.6 | confirmed |
| `f:authbypass` | auth_bypass | CWE-287 | 7.5 | 0.7 | confirmed |
| `f:idor` | idor | CWE-639 | 8.1 | 0.85 | confirmed |
| `f:ssrf` | ssrf | CWE-918 | 8.0 | 0.5 | confirmed |
| `f:sqli` | sqli | CWE-89 | 9.0 | 0.4 | confirmed |
| `f:massassign` | mass_assignment | CWE-915 | 6.5 | 0.6 | confirmed |
| `f:csrf` | csrf | CWE-352 | 4.0 | 0.3 | **inconclusive** |

`f:csrf` is `inconclusive` and deliberately has NO attack edges — it demonstrates the
proof-discipline rule (BUILD_SPEC §5): a confirmed-only gate on `GRANTS`/`LEADS_TO`. It is
still visible in the graph (a `Finding` node + `HAS_FINDING`/`INSTANCE_OF` edges) but never
appears in an attack path.

## Edges

### EXPOSES (`Asset`→`Endpoint`)
`asset:web`→`ep:search`, `asset:web`→`ep:go`, `asset:web`→`ep:login`,
`asset:api`→`ep:metrics`, `asset:api`→`ep:orders`, `asset:admin`→`ep:adminapi`.

### HAS_FINDING (`Endpoint`→`Finding`)
`ep:search`→`f:xss`, `ep:search`→`f:csrf`, `ep:go`→`f:redirect`, `ep:login`→`f:authbypass`,
`ep:orders`→`f:idor`, `ep:metrics`→`f:ssrf`, `ep:adminapi`→`f:sqli`,
`ep:adminapi`→`f:massassign`.

### INSTANCE_OF (`Finding`→`Technique`)
Each finding maps to its Technique by `vuln_type` → technique id, seeded by issue #14
(B3). The mapping itself is documented there; the FK is resolved during ingest (B2/B6) —
not spelled out again here to avoid duplicating the taxonomy's source of truth.

### GRANTS (`Finding`→`Identity`, confirmed only)
`f:xss`→`id:user`, `f:redirect`→`id:user`, `f:authbypass`→`id:user`,
`f:massassign`→`id:admin`.

### LEADS_TO (`Finding`→`Asset`, confirmed only)
`f:idor`→`asset:db`, `f:ssrf`→`asset:admin`, `f:sqli`→`asset:db`.

### CAN_ACCESS (`Identity`→`Asset`)
`id:user`→`asset:api`, `id:admin`→`asset:db`.

### CONNECTS_TO (`Asset`→`Asset`)
`asset:admin`→`asset:api` — exactly one edge. Deliberately **no** `asset:admin`→`asset:db`
and **no** `asset:api`→`asset:db` direct edge, so the IDOR is the only route from the API
to the DB.

## Enumerated attack paths (anonymous entry → `asset:db`, depth ≤ 8)

Six paths total; `f:idor` lies on four of them. Assert this exact set in B4's unit test:

1. `ep:search` → `f:xss` → `id:user` → `asset:api` → `ep:orders` → **`f:idor`** → `asset:db` (IDOR)
2. `ep:go` → `f:redirect` → `id:user` → `asset:api` → `ep:orders` → **`f:idor`** → `asset:db` (IDOR)
3. `ep:login` → `f:authbypass` → `id:user` → `asset:api` → `ep:orders` → **`f:idor`** → `asset:db` (IDOR)
4. `ep:metrics` → `f:ssrf` → `asset:admin` → `asset:api` → `ep:orders` → **`f:idor`** → `asset:db` (IDOR, via `CONNECTS_TO` admin→api)
5. `ep:metrics` → `f:ssrf` → `asset:admin` → `ep:adminapi` → `f:sqli` → `asset:db` (non-IDOR)
6. `ep:metrics` → `f:ssrf` → `asset:admin` → `ep:adminapi` → `f:massassign` → `id:admin` → `asset:db` (non-IDOR)

## Choke-point result (the money shot)

Removing/refuting `f:idor` severs paths 1–4 → **4 of 6** paths collapse, including the
three shortest, highest-value user-session paths. SQLi and mass-assignment (paths 5–6)
remain, so the DB is still reachable but only via the harder SSRF→admin chain.

**Headline:** *Fix f:idor (IDOR on /api/orders) → sever 4 of 6 paths to the Customer
database, including the highest-value one.*

## Note on exact counts

These six paths are hand-derived from the edge list under relationship-uniqueness + depth
≤ 8. Issue #10 (spike) and #15 (B4) confirm them against the live FalkorDB — **issue #10
has already run this live and confirmed the set holds exactly** (see
`docs/graph-model.md` → "Verified live Cypher"). If a future FalkorDB version's enumeration
ever differs (e.g. path-uniqueness semantics change), update this file and B4's expected
set to the live result and note it in `docs/HANDOFF.md` — the edge list above stays fixed;
only the asserted path set may be corrected.
