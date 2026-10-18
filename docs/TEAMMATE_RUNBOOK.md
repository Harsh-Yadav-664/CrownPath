# Teammate runbook — finishing CrownPath for submission

You're picking this up after automated sessions finished Epic A (Foundation), Epic B
(Graph core), Epic C (Agent), and Epic D (Differentiators — MCP server + UI). Everything
in those epics is closed, committed, and verified live against FalkorDB Cloud.
`docs/HANDOFF.md` has the full session-by-session history if you want the detail; this
file is the condensed, click-by-click sequel for what's left: Epic E (P2 polish), Epic F
(submission), Epic G (safety checks). Read `BUILD_SPEC.md` once if you haven't — this
runbook assumes you have the project context, it just gives you the exact commands.

Work through the sections in order. Each ends with "Definition of done" — don't move on
until it's true. Commit after each issue, `git pull --rebase origin main` before every
push, push straight to main, no branches, **no Claude attribution anywhere** (CLAUDE.md
is strict about this — it's enforced by `.claude/settings.json` but also do it by hand if
you're not using Claude Code for this part).

---

## 0. One-time setup

### 0.1 `.env`

```bash
cp .env.example .env
```

Fill in the FalkorDB block from the team's FalkorDB Cloud instance (ask whoever has the
credentials — never put them in a commit, issue, or chat log that isn't already
access-controlled). Verify the connection:

```bash
pip install -r requirements.txt
python scripts/ping.py
```

Expect `PING OK`.

### 0.2 Get a free LLM key (for the LLM tool-use path)

Issue #18 built a provider-agnostic LLM path (`agent/run.py`'s `run_with_provider_llm`)
using an OpenAI-compatible chat API. It was **written and unit-tested with a mocked
client, but never run against a real model** (no key was available in that session) — see
the comment on #18 for exactly what it flagged as unverified. You're closing that gap.

Pick **Gemini** (preferred — generous free tier) or **Groq** (fast, also free):

**Gemini:**
1. Go to <https://aistudio.google.com/apikey>.
2. Sign in, click "Create API key", pick or create a Google Cloud project, copy the key.
3. In `.env`, uncomment and fill the Gemini block:
   ```
   LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   LLM_MODEL=gemini-2.5-flash
   LLM_API_KEY=<the key you just copied>
   ```
4. **Before you trust `gemini-2.5-flash`:** check
   <https://ai.google.dev/gemini-api/docs/openai> for the current model list and confirm
   that model (or whatever replaced it) still supports function/tool calling on the
   OpenAI-compatible endpoint. Google's model lineup moves fast; this was unverified
   against primary docs when written.

**Groq (if you'd rather use this, or Gemini's tool-calling turns out flaky):**
1. Go to <https://console.groq.com/keys>, sign in, create a key, copy it.
2. In `.env`:
   ```
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=openai/gpt-oss-120b
   LLM_API_KEY=<the key you just copied>
   ```
3. Check <https://console.groq.com/docs/models> for the current model list —
   `llama-3.3-70b-versatile` was a long-standing alternative but reports said Groq began
   deprecating it on the free tier in mid-2026. Confirm before falling back to it.

Leave `ANTHROPIC_API_KEY` unset unless you also have one and want to test that path too
(it takes priority over the generic LLM path if both are set — see `agent/run.py`'s
`main()`).

### 0.3 Definition of done
`python scripts/ping.py` prints `PING OK`, and `.env` has either an `ANTHROPIC_API_KEY`
or a working `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY` trio.

---

## 1. Verify the live LLM path (closes out #18)

This is the first thing to do with your new key — it validates the rest of the demo
actually works end to end with a real model, not just the deterministic fallback.

### 1.1 Run it 5 times

```bash
python -m agent.run --crown-jewel asset:db
```

(No `--no-llm` flag — this uses whichever provider you configured in `.env`.) Run it
**5 times** and for each run note:
- Did it reach a final answer within 8 tool-call iterations, or hit
  `RuntimeError: agent: exceeded 8 tool-use iterations`?
- Did the model actually call the graph tools, or try to answer from its own knowledge?
  (Check: the answer should name `f:idor` as the choke point with "4 of 6" — if those
  exact numbers aren't in the output, the model skipped the real tool calls.)
- Did it ever justify the answer by CVSS instead of the attack path? (It shouldn't —
  `agent/prompts/system.md` forbids this — but check.)

### 1.2 If it's not reliable, tune

Two places to adjust, in this order:
1. **Tool descriptions** — `MCP_TOOL_DEFS` in `crownpath_mcp/server.py` (both the
   Anthropic and the OpenAI-compatible paths bridge from these same definitions, so one
   edit fixes both — see `agent/run.py`'s `_anthropic_tool_defs()` /
   `_openai_tool_defs()`). If the model calls the wrong tool or passes malformed
   arguments, sharpen the `description` text or the `inputSchema` here.
2. **System prompt** — `agent/prompts/system.md`. If the model answers without calling
   tools at all, or reasons about CVSS first, tighten rule 1/3/4 there.

Re-run the 5 trials after each change until it's consistently reaching the right answer.

### 1.3 Save a real transcript

Once you have a clean run, save it:

```bash
python -m agent.run --crown-jewel asset:db > /tmp/run.txt
cat agent/last_answer.json
```

Write `docs/sample-run.md` with:
- The exact command you ran and which provider/model (from `.env`).
- The full printed answer (paste it in a fenced code block).
- A one-line note on how many of the 5 trials succeeded cleanly, and anything you had to
  tune in step 1.2.

This file is real evidence for the rules audit (#31, Rule 12 — the team can explain and
has verified the thing actually works) and useful if the video (§5 below) wants to show
LLM output instead of the `--no-llm` fallback.

### 1.4 Commit

```bash
git add .env.example agent/prompts/system.md crownpath_mcp/server.py docs/sample-run.md
git commit -m "Closes #18: verify live LLM tool-use path with a real provider key"
git pull --rebase origin main
git push origin main
```

(Only `git add` the files you actually changed — `agent/prompts/system.md` and
`crownpath_mcp/server.py` only if you tuned them. **Never `git add .env`** — it's
gitignored, but double-check `git status` doesn't show it before any commit.)

Then close #18:

```bash
gh issue close 18 --comment "Verified live with <Gemini|Groq> (<model>): 5/5 runs reached the correct choke-point answer (or: N/5, see docs/sample-run.md for what needed tuning). Transcript in docs/sample-run.md."
```

### 1.5 Definition of done
`docs/sample-run.md` exists with a real transcript; #18 is closed.

---

## 2. Live deployment on Render (#25)

**Deployment target is already decided — Render, free web-service tier.** Don't
re-evaluate; see the full rationale in issue #25 if you want it. Fallback is Railway if
Render's free tier is unavailable when you do this — record that choice in
`docs/HANDOFF.md` if you take it.

### 2.1 Write `render.yaml`

At the repo root:

```yaml
services:
  - type: web
    name: crownpath
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn ui.app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: FALKORDB_HOST
        sync: false
      - key: FALKORDB_PORT
        sync: false
      - key: FALKORDB_USERNAME
        sync: false
      - key: FALKORDB_PASSWORD
        sync: false
      - key: FALKORDB_SSL
        sync: false
      - key: CROWNPATH_GRAPH
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: LLM_BASE_URL
        sync: false
      - key: LLM_MODEL
        sync: false
      - key: LLM_API_KEY
        sync: false
```

`sync: false` means Render will prompt you to fill each value in its dashboard rather
than reading them from this file — so no secret ever lands in the repo.

### 2.2 Deploy (click-by-click)

1. Go to <https://dashboard.render.com>, sign in (GitHub login is easiest).
2. "New +" → "Web Service".
3. Connect the `Harsh-Yadav-664/CrownPath` GitHub repo (authorize Render if asked).
4. Render should auto-detect `render.yaml` and pre-fill the service. If not, set manually:
   Runtime "Python 3", Build Command `pip install -r requirements.txt`, Start Command
   `uvicorn ui.app:app --host 0.0.0.0 --port $PORT`.
5. Pick the **Free** instance type.
6. Under "Environment", add each env var from `render.yaml` with the team's real FalkorDB
   Cloud values (same ones in your local `.env`) plus your LLM key from §0.2.
7. Click "Create Web Service". Wait for the build+deploy to finish (watch the logs tab).
8. Once live, copy the public URL (`https://crownpath-<random>.onrender.com` or whatever
   Render assigns).

### 2.3 Seed the Cloud graph once

The deployed app reads the graph, it doesn't write the demo data on its own. Seed it once
from your machine, against the same Cloud instance the deployment uses:

```bash
python -m lib.seed_taxonomy --all
```

(Your local `.env` already points at the Cloud instance, so this writes straight there —
no separate Render job needed, unless you'd rather do it as a Render Shell command:
dashboard → your service → "Shell" tab → run the same command there.)

### 2.4 Hardening — never show a judge an error

Open `ui/app.py` and add:
- **Rate limiting** on `/api/paths`, `/api/chokepoints`, and any future agent/LLM-backed
  endpoint. A simple in-process token bucket per IP (no new dependency needed) is enough
  for a free-tier demo — a fixed cap like 20 requests/minute is plenty. The read-only
  `/api/graph` endpoint can stay unlimited.
- **Fallback on failure:** generate a pre-recorded sample once:
  ```bash
  python -m agent.run --no-llm --crown-jewel asset:db
  cp agent/last_answer.json data/sample_answer.json
  ```
  Then wire any endpoint that calls the LLM path to catch exceptions/timeouts and serve
  `data/sample_answer.json` instead, with a response field like
  `"sample_response": true` so the UI can show a small banner — always HTTP 200, never a
  5xx or a stack trace.

Test both: hit the rate limit deliberately (loop a request past the cap) and force a
failure (e.g. temporarily set a bad `LLM_API_KEY` in the Render dashboard) — confirm the
public page still renders cleanly both times, then restore the real key.

### 2.5 Write `docs/deploy.md`

Document exactly what you just did — the Render steps above, the env vars list, and the
one-time seed command — so this is repeatable if the service needs to be redeployed.

### 2.6 Update the README

Fill README §Setup "Option A — Live demo" with the real URL.

### 2.7 Commit

```bash
git add render.yaml docs/deploy.md ui/app.py data/sample_answer.json README.md
git commit -m "Closes #25: live deployment on Render (rate-limited, sample-answer fallback)"
git pull --rebase origin main
git push origin main
gh issue close 25 --comment "Deployed to <URL>. render.yaml + docs/deploy.md committed; rate limiting + recorded-sample fallback tested by forcing both a rate-limit hit and an LLM failure — page stayed clean both times."
```

### 2.8 Definition of done
Public URL loads the UI, shows the graph, traces the 6 paths, and shows the `4 of 6`
choke point, backed by FalkorDB Cloud — confirmed by opening the URL in a normal browser,
not just curl.

---

## 3. E1 — Graphiti/native memory, Track 02 (#23)

**P2, optional** — only do this if P0+P1 feel solid and you have time before the
deadline. If you skip it, Track 02 is simply not named at submission; that's a fine
outcome, not a failure (`BUILD_SPEC.md` §9: priorities are sequencing, not a cut list —
but this one is explicitly "ships if time allows" per its own issue).

1. Extend `data/gen_findings.py` with `--scenario regress`: emit `findings.scan1.json`
   (the current scenario minus `f:idor`) and `findings.scan2.json` (today's frozen
   scenario, unchanged).
2. Try Graphiti-on-FalkorDB first. **Timebox it to 1–2 hours.** If it's not working
   cleanly by then, switch to the native approach instead (tag each `Finding` with
   `first_seen`/`last_seen` scan ids, diff in Cypher) — this is pre-approved in the issue,
   you don't need to ask anyone, just record which one you picked and why in
   `docs/HANDOFF.md`.
3. `lib/memory.py`: `whats_changed(g, since, until) -> {added, removed, regressed}`.
   Expose it as a 6th tool in `lib/tools.py`-equivalent fashion and add it to
   `crownpath_mcp/server.py`'s `TOOL_DEFS`/`TOOL_FUNCTIONS` (both `agent/run.py`'s
   Anthropic and provider-agnostic paths already bridge from there automatically).
4. Verify: scan-2 vs scan-1 reports `f:idor` as newly added and `asset:api` as regressed
   (a new path to the crown jewel appeared).
5. If this ships: add a "Track 02 — Agent Memory and Coordination" section to the README,
   describing the memory model, and remember to name Track 02 at submission (#29).

Commit: `git commit -m "Closes #23: ..."`, same push sequence as above, close #23 (or
leave it open with a comment explaining why you descoped it, which is a legitimate
outcome here).

---

## 4. E2 — Loopback capture (#24)

**P2, optional**, same "only after P0+P1, don't let it eat submission time" caveat.

1. Copy `../swiftpentest-fork/bin/demo_target.py` → `data/demo_target.py` verbatim. Log
   the copy in `docs/REUSE.md` (follow the existing table format — there are already
   several rows there from earlier reuse, copy the pattern).
2. Write `data/capture_findings.py`: starts `demo_target.py` on `127.0.0.1` only (copy
   its loopback guard — **the script must refuse any non-loopback URL**, this is a Rule 6
   requirement, not optional), runs simple detections against it, and emits
   `data/findings.captured.json` in the `docs/findings.schema.json` shape.
3. Verify: `python -m jsonschema`-style validation (same pattern as
   `tests/test_format.py::test_remediation_map_and_technique_map_load` or just reuse the
   validation snippet from issue #5/#12) passes, and ingesting
   `data/findings.captured.json` through the normal pipeline
   (`seed_taxonomy.load_all(g, "data/findings.captured.json")`) yields at least one
   entry→asset path via `lib.queries.find_attack_paths`.
4. **This is an alternative dataset, not a replacement** — `data/findings.json` (the
   frozen demo) stays the default so the `4 of 6` money-shot numbers stay deterministic
   for the video and the live deploy.

Commit, close #24 the same way as above.

---

## 5. F1 — README finalize (#26)

By now §§1–4 have filled in most of what README.md still has as `<!-- filled by ... -->`
placeholders (from issue #3's skeleton). Go through `README.md` top to bottom and replace
every remaining placeholder:

- **Graph data model**: condense `docs/graph-model.md` into the README (the 5 node
  labels, the 8 edges, the confirmed-only invariant, the crown-jewel/entry rule). A small
  ASCII diagram is enough — don't need a polished image unless you have time.
- **The Cypher queries**: paste the three queries **verbatim** as they actually run —
  copy straight from `lib/queries.py` (7a, 7b) and `lib/chokepoints.py` (7c, including the
  `algo.betweenness` cross-check with `samplingSeed:42`). These must match the committed
  code exactly, not a paraphrase.
- **Architecture**: prose + a simple diagram —
  `findings.json → ingest → FalkorDB graph → lib/tools.py → crownpath_mcp/server.py (MCP) → agent/run.py → UI / path citation`.
  State plainly that FalkorDB is load-bearing (Rule 2/3 — remove it and there are no
  paths, no choke-points, the product is dead).
- **Setup**: Option A now has the real Render URL (§2.6 above should have already done
  this — double check). Option B and C should already be accurate from issue #3's
  skeleton; just remove the `<!-- filled by F1 -->` marker.
- **Disclosure**: already correct from #3 — just confirm the `docs/REUSE.md` link works
  and the "Built with Claude Code" line is still there.
- **LICENSE**: add an MIT `LICENSE` file at repo root (use the standard MIT template,
  copyright line "Copyright (c) 2026 CrownPath team" or your actual names).
- **Track(s)**: Track 01 always; add Track 02 only if §3 (E1/#23) shipped.

Definition of done: `grep -n "filled by" README.md` returns nothing.

Commit: `git commit -m "Closes #26: README finalize — model, queries, architecture, disclosure, LICENSE"`.

---

## 6. G1 — Fresh-clone verification on a Docker machine (#30)

**Must be done on a machine that is NOT the primary dev laptop and that actually has
Docker** (the dev laptop this project was built on has no Docker/WSL — this whole issue
exists because nobody has run the local-Docker path end to end yet).

1. On that machine, clone into a **brand new empty folder** — no leftover `.env`, no
   pre-existing venv:
   ```bash
   git clone https://github.com/Harsh-Yadav-664/CrownPath
   cd CrownPath
   ```
2. Follow README §Setup "Option B" **exactly as written, verbatim** — do not improvise
   around anything that breaks:
   ```bash
   cp .env.local.example .env
   make up
   pip install -r requirements.txt
   python scripts/ping.py        # expect: PING OK, against localhost:6379, ssl=false
   make seed
   make demo                     # or: make demo -- with --no-llm if no ANTHROPIC_API_KEY
   make ui
   ```
3. Confirm `make demo` prints the ranked, path-cited list and the `4 of 6` IDOR choke
   point; confirm `make ui` serves the page and the path-highlight buttons work (open
   `http://localhost:8000` in a browser).
4. **Anything that breaks: fix the repo or the README, not your local setup.** Common
   candidates to watch for: a requirements.txt pin that doesn't resolve on this machine's
   Python version, a port clash on 6379/3000 with something else already running, a
   missing step in the README. After each fix, delete the clone and redo the whole
   sequence from a fresh empty folder until it passes clean start to finish.
5. Append a dated block to `docs/HANDOFF.md`: OS, Docker version, Python version, pass/fail,
   and every fix you made.

Commit any repo/README fixes, push, close #30 with a comment summarizing the environment
and that it passed clean.

---

## 7. G2 — Pre-submission rules audit (#31)

Do this after §§1–6 (it audits the near-final repo). Create `docs/rules-audit.md`: a
table with one row per rule, columns `Rule | Requirement (short) | Evidence (file/section/URL) | Status (pass/gap) | Action`.

Use `BUILD_SPEC.md` §4 as the source of the 18 rules (it reproduces them verbatim) and
§4's "How these rules bind CrownPath" subsection as a head start on the evidence mapping.
Concretely, for each rule point at something real in the repo:

- **Rule 2/3** (FalkorDB primary, graph does real work): README Cypher-queries section +
  `lib/queries.py`/`lib/chokepoints.py` (7a/7c computed in Cypher, never Python).
- **Rule 6** (allowed data only): `data/findings.json` synthetic via `data/gen_findings.py`;
  any capture (§4/#24) is loopback-only with the guard confirmed.
- **Rule 8/9** (work during event, new work judged): `git log` dates fall inside Oct
  15–18; `docs/REUSE.md` discloses the limited swiftPentest reuse.
- **Rule 10** (required deliverables): public repo, README sections, video link (§8),
  live URL (§2) + local setup (§6), track(s) named.
- **Rule 11** (AI disclosure): README disclosure paragraph.
- **Rule 12/13** (team understands, not pure-AI): architecture section, `docs/sample-run.md`
  (§1) as evidence the team actually ran and verified it, not just generated it.
- Rules 1, 4, 5, 7, 14–18: one-line notes (team size, FalkorDB run method, tracks named,
  timing, conduct, IP, etc.) — these are mostly process facts, not code evidence.

Also spot-check (per the issue): #15/#16/#21 compute paths/choke-points in Cypher not
Python; #24's loopback guard is real; the README has the queries verbatim and both run
paths; the disclosure paragraph wasn't accidentally dropped during §5's README edit.

Fix any gap you find before marking it "pass". No open "gap" rows allowed when you're
done — either fixed, or the row explicitly says why it doesn't apply.

Commit, close #31.

---

## 8. F2 — Demo video (#27)

**Human-owned — record this yourself, it's the single most-judged artifact alongside the
README.** ≤3–4 minutes, these six beats (from the issue, don't skip any):

1. **Problem (20s):** a pile of findings; severity sort can't see the chain. Ask: "what
   do we fix first, and why?"
2. **Findings loaded (30s):** show the graph loading (`python -m lib.seed_taxonomy --all`
   or the agent auto-loading on first run) in the custom UI — ideally the live deployment
   (§2) so the video shows the public URL.
3. **Agent traces the path (60–90s):** run `python -m agent.run --crown-jewel asset:db`
   with your real LLM key if §1 confirmed it's reliable (more impressive than `--no-llm`
   for a demo video), show the ranked, path-cited list — call out that every item is
   justified by the attack path, not CVSS.
4. **Choke-point recommendation (40s):** the money shot — read out or show on screen:
   *"Fix f:idor (IDOR on /api/orders) → sever 4 of 6 paths to the Customer database,
   including the highest-value one."*
5. **Path lights up (20s):** click "Trace attack paths" then "Show choke point" in the UI,
   show the highlighted paths converging and the severed ones dimming.
6. **Close (10s):** name Track 01 (and Track 02 if §3/#23 shipped); one line on FalkorDB
   being load-bearing — remove it and there's no graph, no paths, no choke-point.

Use the frozen demo graph (`data/findings.json`, untouched) so the counts are exactly "4
of 6" every take — don't record against `data/findings.captured.json` (§4) for the main
demo, that one's a bonus/alternative, not the scripted story.

Upload (YouTube unlisted or similar), add the link to README §Demo, close #27.

---

## 9. F3 — Blog post (#28, side prize, optional)

**P2, do this last, only if time remains after the P0 submission items above are done.**
`docs/blog.md`, ~800–1200 words: problem → insight (graph reachability beats CVSS
sorting) → walk the demo with the real queries and the `4 of 6` result (screenshot from
the UI) → why FalkorDB is load-bearing → the same honest disclosure paragraph as the
README → links to the repo and the video. Submit per the hackathon's blog-post
instructions for the AirPods side prize.

---

## 10. F4 — Submit (#29)

**Blocked by #30 and #31 — do not attempt until both are closed.** Final checklist
(mirrors `BUILD_SPEC.md` §13 and the issue's own checklist — verify every line is
actually true, don't just skim it):

- [ ] Public repo, clean history dated within the event window.
- [ ] README: setup (both options), graph data model, exact Cypher queries, architecture,
      disclosure — all real, no placeholders (§5 done).
- [ ] Demo video link in the README (§8 done).
- [ ] Live deployment URL **and** complete local-setup instructions, both present (§2, §6).
- [ ] Fresh-clone verification passed (§6/#30 closed) and rules audit has no open gaps
      (§7/#31 closed).
- [ ] Track(s) named: Track 01 always; Track 02 only if §3/#23 shipped.
- [ ] Blog post submitted if you did §9.
- [ ] Team can actually explain the graph model, the three queries, and the architecture
      live — not just "the AI wrote it." `docs/sample-run.md` (§1) and `docs/HANDOFF.md`'s
      session history are your evidence trail if anyone asks what you personally verified.
- [ ] No credentials anywhere in the repo or its history; no Claude attribution in any
      commit, PR, or issue.

Submit via the WeMakeDevs hackathon form at
<https://www.wemakedevs.org/hackathons/falkordb> with the repo link, README, video link,
deployment URL + local-setup note, and the track(s) you're naming. Deadline: **Oct 18
2026, 23:59 IST** — don't cut it close.

Append a final block to `docs/HANDOFF.md` noting the submission is done, the time, and
the track(s) named. Close #29.

---

## If you get stuck

Don't improvise around something that seems like a design decision (a new field, a
changed query, a different deployment host) — that's exactly the kind of call
`CLAUDE.md`/`BUILD_SPEC.md` want flagged, not worked around. Write the blocker into
`docs/HANDOFF.md` (there's a running log there of past blockers and how they were
resolved — the `#20` MCP-naming-collision entry is a good example of the format) and
make the call yourself as the human, since that's explicitly your job per the spec's own
"If blocked: stop, write the blocker... and leave the decision for the human" rule.
