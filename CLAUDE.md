# CLAUDE.md — build context for every CrownPath session

**Read `BUILD_SPEC.md` end to end before doing anything.** It is the single source of
truth; this file only distills the rules a coding session must never forget. When this
file and the spec disagree, the spec wins — fix this file.

## What CrownPath is
An attack-path triage agent that reasons over how vulnerabilities **chain** on a FalkorDB
graph, and finds the **choke-point finding** — the one fix that severs the most attack
paths to a crown-jewel asset. The graph is load-bearing: remove FalkorDB and the product
is dead (hackathon Rules 2 & 3). Track 01 always; Track 02 only if the memory layer (E1)
ships.

## Hard rules (do not violate)
- **Graph does the work.** Attack paths / choke-points are computed in Cypher / graph
  algorithms, never in Python. Verify FalkorDB syntax against docs.falkordb.com — never
  invent an API.
- **Synthetic / self-owned data only** (Rule 6). No real third-party data; loopback targets
  only for any live capture.
- **Reuse only what BUILD_SPEC §5 names**, by copying files into this repo and logging each
  in `docs/REUSE.md`. Never build inside `../swiftpentest-fork/`.
- **Build the full scope (P0 → P1 → P2).** We are going for first place in Track 01.
  Priorities are *sequencing order only* — do not pre-emptively cut, simplify, or lower a
  target. If something is blocked or slipping, STOP and flag it in `docs/HANDOFF.md` for the
  human to decide; never cut scope on your own.
- **Zero design decisions in implementation issues.** Each issue carries context, exact file
  paths, acceptance criteria, and dependencies. If an issue would force a design choice,
  stop and push the choice up rather than improvising.

## Database / environment
- The team's **dev database is FalkorDB Cloud** (instance "CrownPath"). This dev laptop
  cannot run Docker — **do not run docker or docker compose here.**
- Connection comes from env vars / a local `.env` (see `.env.example`):
  `FALKORDB_HOST/PORT/USERNAME/PASSWORD`, `FALKORDB_SSL` (verified: **false** for our Cloud
  instance), `CROWNPATH_GRAPH` (default `crownpath`). `lib/graph.py` reads these;
  `python scripts/ping.py` verifies the connection.
- **Never commit `.env`; never print or paste the password** into commits, issues, docs, or
  logs. `.env.example` (empty values) is the only committed template.
- Judges run it two ways (both must work): a **local Docker** path (`docker-compose.yml`,
  `make up` / `make seed` / `make demo`) and a **live deployment** (public URL in the
  README). A judge can point their own `.env` at their own FalkorDB — our Cloud credentials
  are never shared.

## Attribution (strict)
- **Never add any Claude / Claude Code attribution** to commits, PR descriptions, issue
  bodies, or issue comments: no `Co-Authored-By`, no "Generated with Claude Code", no
  Claude-session links. (`.claude/settings.json` disables these via the `attribution` key;
  also follow this rule by hand.)
- **Do keep** the README's AI-use disclosure required by Rule 11 (the paragraph in
  BUILD_SPEC §5). That is a product disclosure, not a commit trailer.
- Do **not** rewrite or force-push existing git history.

## Per-session habit
Update `docs/HANDOFF.md` at the end of each session (done / next / broken). One module/file
per issue; the active session owns its merge.
