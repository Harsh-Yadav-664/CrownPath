# Demo video shot list (≤ 3–4 min) — issue #27

Record with the live deployment URL (or `uvicorn ui.app:app` locally against the seeded graph).
Open the page once beforehand (free Render instances sleep). Use the frozen demo data so the
numbers are always "4 of 6".

1. **Problem (0:00–0:20)** — "A scanner hands us eight findings sorted by CVSS. What do we fix
   first, and why?" Show `data/findings.json` or the severity list briefly.
2. **Graph loaded (0:20–0:50)** — open the UI: the graph of assets, endpoints, findings and
   identities from FalkorDB. Name the five node types.
3. **Agent traces the paths (0:50–2:00)** — click **Ask the agent** (or run
   `python -m agent.run --crown-jewel asset:db`). Point out that each item cites a path and that
   nothing is ordered by CVSS. Click **Trace attack paths**: six paths converge on the customer
   database.
4. **Choke point (2:00–2:40)** — click **Show choke point**. Read the headline: "Fix IDOR on
   /api/orders → sever 4 of 6 paths, including the highest-value one." Show the 7c Cypher from the
   README (`UNWIND … count(path)`), and mention the deletion proof (2 paths remain).
5. **Memory (2:40–3:10)** — click **What changed?**: "scan-2 added an IDOR; Orders API regressed;
   paths 2 → 6" (Track 02).
6. **Close (3:10–3:30)** — Tracks 01 and 02; FalkorDB is load-bearing — without it there are no
   paths, no choke point, no memory. Mention the AI-use disclosure and that the data is synthetic.
