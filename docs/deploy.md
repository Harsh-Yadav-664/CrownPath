# Deploying CrownPath on Render (issue #25)

The live demo is the FastAPI + Cytoscape UI (`ui/app.py`) on Render's free web-service
tier, reading the same FalkorDB Cloud graph the team develops against. No secret is in
the repo: `render.yaml` declares every variable with `sync: false`, so values are typed
into the Render dashboard.

## What the deployment serves

| Endpoint | Purpose | Limits |
|---|---|---|
| `/` | the graph UI | none |
| `/api/graph`, `/api/paths`, `/api/chokepoints` | read-only graph queries (Cypher on FalkorDB) | none (no LLM involved) |
| `/api/agent` | the agent's answer ("what do we fix first?") | in-process sliding window, **6 requests/min per client IP** (`AGENT_RATE_LIMIT_PER_MIN`), 40 s timeout (`AGENT_TIMEOUT_SECONDS`) |

`/api/agent` never returns an error to a visitor. If the LLM call fails, times out, the
provider rate-limits us, the graph is unreachable, or the per-IP limit is hit, it returns
the recorded run in `data/sample_answer.json` with HTTP 200 and `"sample_response": true`;
the UI then shows a "Sample response" banner. With no LLM key configured at all it answers
live from the graph using the deterministic path (`agent.run.run_no_llm`).

`data/sample_answer.json` is regenerated with:

```bash
python -m agent.run --no-llm --crown-jewel asset:db
cp agent/last_answer.json data/sample_answer.json
```

## One-time deploy

1. Sign in at <https://dashboard.render.com> (GitHub login is easiest).
2. **New +** -> **Blueprint** (or **Web Service**) -> connect the GitHub repo.
   Render reads `render.yaml`; manual settings if needed: runtime Python, build
   `pip install -r requirements.txt`, start `uvicorn ui.app:app --host 0.0.0.0 --port $PORT`,
   instance type **Free**.
3. Fill in the environment variables (same values as your local `.env`):
   `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_USERNAME`, `FALKORDB_PASSWORD`,
   `FALKORDB_SSL` (`false` for our Cloud instance), `CROWNPATH_GRAPH` (`crownpath`),
   and the LLM trio `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`
   (or `ANTHROPIC_API_KEY` / `CROWNPATH_MODEL`). The LLM variables are optional; without
   them `/api/agent` uses the deterministic path.
4. **Create** and wait for the build. Copy the public `https://<name>.onrender.com` URL
   into README -> Setup -> Option A.
5. Seed the Cloud graph once, from any machine whose `.env` points at the same instance:

   ```bash
   python -m lib.seed_taxonomy --all
   ```

   The deployed app only reads the graph. **Do not run `pytest` with the production
   graph name** -- the tests call `graph.reset()`; use `CROWNPATH_GRAPH=crownpath_test`.

## Notes

- Free instances sleep after ~15 minutes idle; the first request afterwards takes about a
  minute to wake. Open the URL once before recording or submitting.
- Fallback host if Render's free tier is unavailable: Railway, same start command and
  variables.
