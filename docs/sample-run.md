# Sample live run (issue #18)

Real transcript of the agent choosing graph tools through an LLM, against the FalkorDB Cloud
demo graph.

```
python -m agent.run --crown-jewel asset:db
```

Provider: **Gemini `gemini-2.5-flash`** via its OpenAI-compatible endpoint (`GEMINI_API_KEY`;
Groq `openai/gpt-oss-120b` is the fallback). Tools are the schemas exposed by
`crownpath_mcp/server.py`. Output, unedited:

```
## What to fix first
1. **Reflected XSS on /search** — Lies on a length-6 path from GET /search to Customer database (score 12.75).
   Path: ep:search → HAS_FINDING → (f:xss) → GRANTS → id:user → CAN_ACCESS → asset:api → EXPOSES → ep:orders → HAS_FINDING → (f:idor) → LEADS_TO → asset:db
2. **IDOR on /api/orders** — Lies on a length-6 path from GET /search to Customer database (score 12.75).
   Path: ep:search → HAS_FINDING → (f:xss) → GRANTS → id:user → CAN_ACCESS → asset:api → EXPOSES → ep:orders → HAS_FINDING → (f:idor) → LEADS_TO → asset:db
3. **Auth bypass on /login** — Lies on a length-6 path from POST /login to Customer database (score 9.92).
   Path: ep:login → HAS_FINDING → (f:authbypass) → GRANTS → id:user → CAN_ACCESS → asset:api → EXPOSES → ep:orders → HAS_FINDING → (f:idor) → LEADS_TO → asset:db
4. **Open redirect on /go** — Lies on a length-6 path from GET /go to Customer database (score 8.50).
   Path: ep:go → HAS_FINDING → (f:redirect) → GRANTS → id:user → CAN_ACCESS → asset:api → EXPOSES → ep:orders → HAS_FINDING → (f:idor) → LEADS_TO → asset:db
5. **SSRF on /metrics** — Lies on a length-6 path from GET /metrics to Customer database (score 7.08).
   Path: ep:metrics → HAS_FINDING → (f:ssrf) → LEADS_TO → asset:admin → CONNECTS_TO → asset:api → EXPOSES → ep:orders → HAS_FINDING → (f:idor) → LEADS_TO → asset:db

## Choke point
Fix **IDOR on /api/orders** → severs **4 of 6** paths to asset:db, including the highest-value one.
```

## Reliability notes (what was actually observed)

- **First 5 Gemini runs (before tuning):** all five failed or degraded. Two crashed printing the
  model's `→` on a Windows cp1252 console (fixed: stdout is reconfigured to UTF-8); three hit the
  free tier's `429 RateLimitError` and fell back to the deterministic answer, which the agent does
  by design. In one run the model got the choke point right (IDOR, 4 of 6) but **composed its own
  "Path:" line** without calling `rank_by_reachability` -- not a real graph path.
- **Fixes:** the system prompt now requires both `rank_by_reachability` and `choke_points`, with
  each `Path:` copied from the tool's `cited_path.steps`; and if the model skips a tool, the
  structured result in `agent/last_answer.json` is back-filled from the graph, so the UI never
  shows model-invented data.
- **After tuning, Gemini:** 3 of 3 runs reached the IDOR choke point with "4 of 6", real paths
  from the tool, no CVSS-led reasoning.
- **Groq (`openai/gpt-oss-120b`):** 4 of 5 runs answered live with the correct choke point and
  real paths (shorter lists than Gemini); 1 of 5 hit a rate limit and fell back to the
  deterministic answer. Neither provider's answer ever ranked by CVSS.
- Free-tier limits are the main operational risk, hence the chain: Gemini -> Groq ->
  deterministic -> (public endpoint only) recorded sample `data/sample_answer.json`.
