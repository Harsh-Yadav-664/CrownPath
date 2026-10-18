# Demo video script (~3 min, 6 beats) — issue #27

One idea, said six ways: **fix one finding, sever 4 of 6 attack paths to the customer database.**
Every number below is what the frozen demo produces, so it is the same on every take.

## Before you record

- Open https://crownpath-v9kt.onrender.com/ two minutes early (the free instance sleeps). It must show
  the hero "8 findings. Sort them by CVSS and you fix the wrong thing." If it still shows the older
  page, the deploy hasn't picked up main yet (see `docs/HANDOFF.md`); record locally with `make ui`
  -> http://localhost:8000 instead.
- The live graph must hold the frozen demo: `python -m lib.memory --demo` (as in `docs/deploy.md`).
  Never run `pytest` against the live graph name.
- Browser at 100% zoom, about 1440x900, no other tabs. Have a Git Bash terminal open in the repo.
- Pre-load the beat-6 graph once so the take doesn't wait on it (it uses its own graph, never the live one):
  `CROWNPATH_GRAPH=crownpath_captured python -m lib.seed_taxonomy --all --findings data/findings.captured.json`
- Button labels below match `ui/static/index.html` as of commit `48812ea` (v3 UI). "Source & queries" is now a link to the repo, not a button.

## The six beats

### 1. The problem (0:00–0:25)
**On screen:** terminal, run:
```bash
python -c "import json; [print(f['cvss'], f['title']) for f in sorted(json.load(open('data/findings.json'))['findings'], key=lambda f: -f['cvss'])]"
```
The list starts `9.0 SQLi on /admin`.
**Say:** "A scanner just handed us eight findings for Acme Shop, sorted by severity. The obvious move is to fix the SQL injection at the top, a nine point oh. But the question that matters is different: which single fix actually protects the customer database?"

### 2. The answer, up front (0:25–0:50)
**On screen:** the CrownPath page, top of the hero. Don't click yet.
**Say:** "CrownPath loads the same findings into a FalkorDB graph and traces every route an anonymous attacker could chain to the customer database. It found six routes, and one fix kills four of them."

### 3. Show me the fix (0:50–1:25)
**Do:** click **Show me the fix**. Let the answer card settle; point at "4 of 6" and the grey CVSS line under the bar.
**Say:** "The fix is the IDOR on the orders API. It sits on four of the six attack paths, including the highest-value one. The SQL injection that CVSS ranked first sits on just one."

### 4. Simulate fix (1:25–1:55)
**Do:** click **Simulate fix** in the answer card. Wait for "Simulated in FalkorDB: 4 of 6 paths severed, 2 remain". Scroll down so the graph shows the IDOR turned green and the two surviving routes in red.
**Say:** "We don't have to take that on trust. Simulate fix asks FalkorDB to re-run the attack-path query with the IDOR removed. Four paths are cut, two remain, and the stored graph is never touched."

### 5. The graph is the evidence (1:55–2:35)
**Do:** click **Trace all 6 attack paths**, then click **Path #1** in "Every attack path, ranked". The Why panel walks the path step by step and ends with the score.
**Say:** "Here's the evidence. The attacker starts at the top with no login, and red lines are attack paths. Path one: a reflected XSS steals a customer session, that session reaches the orders API, and the IDOR reads the database. Each path is scored by confidence times business value over its length, twelve point seven five here, and CVSS never enters the score."

### 6. It works on captured real-app data too (2:35–3:05)
**Do:** terminal, run:
```bash
CROWNPATH_GRAPH=crownpath_captured python -m agent.run --no-llm --crown-jewel asset:lab-db
```
It ends with "Fix SQL injection on /item -> severs 1 of 2 paths to Lab customer store".
**Say:** "And it's not tuned to one toy dataset. We probed our own deliberately vulnerable app on localhost, captured four confirmed findings with their evidence, and the same graph queries found two attack paths to its customer store and put the SQL injection first. Take FalkorDB away and none of this exists: no paths, no choke point, no answer."

## Optional extra (only if you're under 3:00)

Click **What changed since the last scan?**. Say: "The graph also remembers scans: the IDOR arrived in scan two and opened four new paths to the database." This is the Track 02 memory story. It only works if the graph was loaded with `python -m lib.memory --demo`, which records both scans. As of 2026-10-18 evening the live graph had **no** scan history (the button says "No regressions ... 6 -> 6"), so reload it first or skip this beat.
