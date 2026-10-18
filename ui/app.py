"""ui/app.py — minimal FastAPI backend for the path-rendering UI (BUILD_SPEC.md
§8/§9, issue #22 / D3). The PRIMARY demo visual: no localhost:3000 FalkorDB
browser exists for the Cloud dev DB, and this same page is served by the live
deployment (#25/E3). Reads the graph through lib.graph (.env connection), so it
works against FalkorDB Cloud or any FalkorDB a judge points it at.

Run: uvicorn ui.app:app --port 8000
"""
import collections
import concurrent.futures
import json
import os
import re
import threading
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent import format as agent_format
from agent import run as agent_run
from lib import graph, queries, tools

load_dotenv()

app = FastAPI(title="CrownPath")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _public_attack_path(path):
    """Strip internal keys before the path crosses the HTTP boundary."""
    return {
        "steps": path["steps"],
        "length": path["length"],
        "score": path["score"],
        "finding_ids": path["finding_ids"],
        "crown_jewel_id": path["crown_jewel_id"],
    }


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/graph")
def get_graph(taxonomy: bool = False):
    """The demo graph as Cytoscape elements: {nodes, edges}. By default only the estate
    (Asset, Endpoint, Finding, Identity); `taxonomy=true` adds the 77 Technique nodes
    and INSTANCE_OF / CHAINS_TO edges. Each node carries its properties (`props`) so
    the page can explain it; findings also carry their technique and fix text."""
    g = tools._get_graph()

    where = "" if taxonomy else "WHERE NOT n:Technique "
    node_rows = graph.run(
        g,
        f"MATCH (n) {where}RETURN labels(n)[0] AS label, n.id AS id, properties(n) AS props",
    ).result_set

    technique_of = dict(
        graph.run(g, "MATCH (f:Finding)-[:INSTANCE_OF]->(t:Technique) RETURN f.id, t.id").result_set
    )
    fixes = agent_format._load_remediation_map()

    nodes = []
    for label, node_id, props in node_rows:
        display = props.get("name") or props.get("title") or props.get("url") or props.get("role") or node_id
        if label == "Endpoint":
            display = f"{props.get('method', '')} {props.get('url', node_id)}".strip()
        props = {k: v for k, v in props.items() if k not in ("scans",)}
        if label == "Finding":
            props["technique"] = technique_of.get(node_id)
            props["fix"] = fixes.get(technique_of.get(node_id))
        nodes.append({"data": {"id": node_id, "label": display, "type": label, "props": props}})

    edge_where = "" if taxonomy else "WHERE NOT a:Technique AND NOT b:Technique "
    edge_rows = graph.run(
        g,
        f"""
        MATCH (a)-[r]->(b)
        {edge_where}RETURN a.id AS source, b.id AS target, type(r) AS label
        """,
    ).result_set
    edges = [
        {"data": {"source": source, "target": target, "label": label}}
        for source, target, label in edge_rows
    ]

    return {"nodes": nodes, "edges": edges}


@app.get("/api/whatif")
def get_whatif(finding: str, crown_jewel: str = "asset:db"):
    """What if `finding` were fixed? FalkorDB re-runs 7a with that finding excluded and
    returns the paths that remain (non-destructive)."""
    from lib import chokepoints as cp_module

    g = tools._get_graph()
    remaining = cp_module.paths_after_fix(g, finding, crown_jewel)
    return {"finding": finding, "crown_jewel": crown_jewel, "remaining": remaining}


@app.get("/api/paths")
def get_paths(crown_jewel: str = "asset:db"):
    # 7a enumeration + 7b score, ranked best-first (likelihood x impact).
    paths = queries.rank_paths(tools._get_graph(), crown_jewel_id=crown_jewel, limit=None)
    return {"paths": [_public_attack_path(p) for p in paths], "crown_jewel": crown_jewel}


@app.get("/api/chokepoints")
def get_chokepoints(crown_jewel: str = "asset:db"):
    from lib import chokepoints as cp_module

    choke_points = tools.choke_points(crown_jewel_id=crown_jewel)
    headline = None
    if choke_points:
        g = tools._get_graph()
        jewel_row = graph.run(g, "MATCH (a:Asset {id:$id}) RETURN a.name", {"id": crown_jewel}).result_set
        jewel_name = jewel_row[0][0] if jewel_row else crown_jewel
        headline = cp_module.headline(choke_points[0], jewel_name)

    return {"choke_points": choke_points, "headline": headline, "crown_jewel": crown_jewel}


@app.get("/api/changes")
def get_changes(since: str = "scan-1", until: str = "scan-2", crown_jewel: str = "asset:db"):
    """Track 02 memory: what changed between two recorded scans (lib/memory.py).
    Always HTTP 200; `available: false` when the graph holds no recorded scans."""
    from lib import memory

    try:
        change = tools.whats_changed(since, until, crown_jewel)
    except Exception as exc:
        return {"available": False, "reason": type(exc).__name__}
    if not change["paths"]["until"]:
        return {"available": False, "reason": "no scans recorded"}
    return {"available": True, "headline": memory.headline(change), **change}


# --- /api/target, /api/scope: "what was tested" ----------------------------------
TARGET_DOC_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "target.md")


def _plain(markdown):
    """Markdown -> plain text for UIs that don't render markdown."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown)
    text = re.sub(r"(\*\*|__|`)", "", text)
    return re.sub(r"^\s*[-*]\s+", "- ", text, flags=re.M).strip()


def _target_about():
    """docs/target.md parsed into {name, description, markdown, sections}: the H1 is the
    target name, the first paragraph its one-line description, each H2 a section."""
    with open(TARGET_DOC_PATH, "r", encoding="utf-8") as f:
        markdown = f.read()
    name, description, sections, current = None, None, [], None
    for block in re.split(r"\n\s*\n", markdown.strip()):
        block = block.strip()
        if block.startswith("# ") and name is None:
            name = block[2:].strip()
        elif block.startswith("## "):
            current = {"heading": block[3:].strip(), "markdown": ""}
            sections.append(current)
        elif current is not None:
            current["markdown"] = (current["markdown"] + "\n\n" + block).strip()
        elif description is None:
            description = _plain(block)
    for s in sections:
        s["text"] = _plain(s["markdown"])
    return {"name": name, "description": description, "markdown": markdown, "sections": sections}


@app.get("/api/target")
def get_target():
    """The plain-English description of the tested estate (docs/target.md)."""
    return _target_about()


@app.get("/api/scope")
def get_scope():
    """What was tested, read live from the graph: assets (with their endpoints), crown
    jewels, identities and every finding with its type/CWE/CVSS/confidence/status/
    evidence. `target` carries the docs/target.md text."""
    g = tools._get_graph()

    endpoints = [
        {"id": eid, "asset_id": aid, "path": url, "method": method, "auth_required": auth}
        for eid, aid, url, method, auth in graph.run(
            g,
            "MATCH (a:Asset)-[:EXPOSES]->(e:Endpoint) "
            "RETURN e.id, a.id, e.url, e.method, e.auth_required ORDER BY a.id, e.url, e.id",
        ).result_set
    ]
    by_asset = collections.defaultdict(list)
    for e in endpoints:
        by_asset[e["asset_id"]].append(e["id"])

    assets = [
        {"id": aid, "name": name, "type": atype, "environment": env,
         "is_crown_jewel": bool(jewel), "value": value, "endpoint_ids": by_asset.get(aid, [])}
        for aid, name, atype, env, jewel, value in graph.run(
            g,
            "MATCH (a:Asset) RETURN a.id, a.name, a.type, a.environment, a.is_crown_jewel, a.value "
            "ORDER BY a.is_crown_jewel DESC, a.value DESC, a.id",
        ).result_set
    ]

    identities = [
        {"id": iid, "role": role, "privilege_level": level}
        for iid, role, level in graph.run(
            g, "MATCH (i:Identity) RETURN i.id, i.role, i.privilege_level ORDER BY i.privilege_level, i.id"
        ).result_set
    ]

    findings = [
        {"id": fid, "title": title, "type": vtype, "technique_id": tid, "cwe": cwe, "cvss": cvss,
         "confidence": conf, "status": status, "evidence": evidence,
         "endpoint_id": eid, "endpoint": f"{method} {url}" if url else None, "asset_id": aid}
        for fid, title, vtype, tid, cwe, cvss, conf, status, evidence, eid, url, method, aid in graph.run(
            g,
            """
            MATCH (f:Finding)
            OPTIONAL MATCH (e:Endpoint)-[:HAS_FINDING]->(f)
            OPTIONAL MATCH (a:Asset)-[:EXPOSES]->(e)
            OPTIONAL MATCH (f)-[:INSTANCE_OF]->(t:Technique)
            RETURN f.id, f.title, f.vuln_type, t.id, f.cwe, f.cvss, f.confidence, f.status,
                   f.evidence, e.id, e.url, e.method, a.id
            ORDER BY a.id, e.url, f.id
            """,
        ).result_set
    ]

    jewels = [{"id": a["id"], "name": a["name"], "value": a["value"]} for a in assets if a["is_crown_jewel"]]
    return {
        "target": _target_about(),
        "graph": graph.graph_name(),
        "crown_jewels": jewels,
        "assets": assets,
        "endpoints": endpoints,
        "identities": identities,
        "findings": findings,
        "counts": {
            "assets": len(assets),
            "endpoints": len(endpoints),
            "anonymous_entry_points": sum(1 for e in endpoints if not e["auth_required"]),
            "identities": len(identities),
            "findings": len(findings),
            "confirmed_findings": sum(1 for f in findings if f["status"] == "confirmed"),
            "crown_jewels": len(jewels),
        },
    }


# --- /api/agent: the public agent endpoint (issue #25 / E3) --------------------
# Never shows a judge an error: if the LLM call fails, times out, the graph is
# unreachable, or the per-IP rate limit is hit, the recorded sample run
# (data/sample_answer.json, generated by `python -m agent.run --no-llm`) is
# returned with HTTP 200 and "sample_response": true so the UI can show a banner.
SAMPLE_ANSWER_PATH = os.path.join("data", "sample_answer.json")
AGENT_RATE_LIMIT = int(os.environ.get("AGENT_RATE_LIMIT_PER_MIN", "6"))
AGENT_TIMEOUT_SECONDS = float(os.environ.get("AGENT_TIMEOUT_SECONDS", "45"))

# In-process sliding-window limiter, keyed by client IP (no extra dependency).
_hits = collections.defaultdict(collections.deque)
_hits_lock = threading.Lock()
# agent.run writes agent/last_answer.json; serialise so concurrent callers can't
# read each other's output.
_agent_lock = threading.Lock()
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)


def _client_ip(request: Request):
    # Render terminates TLS behind a proxy and puts the real client first.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip, limit=None, window=60.0):
    limit = AGENT_RATE_LIMIT if limit is None else limit
    now = time.monotonic()
    with _hits_lock:
        q = _hits[ip]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        return False


def _sample_answer(reason):
    with open(SAMPLE_ANSWER_PATH, "r", encoding="utf-8") as f:
        sample = json.load(f)
    return {**sample, "sample_response": True, "source": "sample", "reason": reason}


LLM_BUDGET_SECONDS = float(os.environ.get("AGENT_LLM_BUDGET_SECONDS", "25"))


def _deterministic(crown_jewel):
    """Answer straight from the graph (no LLM, no shared file): the same tools and
    formatter as `agent.run --no-llm`."""
    agent_run._ensure_graph_loaded()
    remediations = tools.rank_by_reachability(crown_jewel)
    chokepoints = tools.choke_points(crown_jewel)
    return {
        "remediations": remediations,
        "choke_points": chokepoints,
        "answer": agent_format.format_answer(remediations, chokepoints),
        "sample_response": False,
        "source": "deterministic",
    }


def _llm(question, crown_jewel):
    """LLM answer: Anthropic if keyed, else the Gemini -> Groq chain. Reads back the
    structured result agent.run wrote (serialised: it shares agent/last_answer.json)."""
    with _agent_lock:
        if os.environ.get("ANTHROPIC_API_KEY"):
            answer = agent_run.run_with_llm(question, crown_jewel)
        else:
            answer, _provider = agent_run.run_with_provider_chain(question, crown_jewel)
        with open(agent_run.LAST_ANSWER_PATH, "r", encoding="utf-8") as f:
            structured = json.load(f)
    structured["answer"] = answer
    return {**structured, "sample_response": False, "source": "llm"}


def _run_agent(question, crown_jewel):
    """LLM within a time budget; if it fails, is rate-limited or is too slow, answer
    deterministically from the graph (the abandoned LLM attempt is left to finish
    on its own thread and never blocks this request)."""
    if os.environ.get("ANTHROPIC_API_KEY") or agent_run.provider_chain():
        future = _executor.submit(_llm, question, crown_jewel)
        try:
            return future.result(timeout=LLM_BUDGET_SECONDS)
        except (Exception, SystemExit):
            pass
    return _deterministic(crown_jewel)


@app.get("/api/agent")
def ask_agent(request: Request, question: str = agent_run.DEFAULT_QUESTION,
              crown_jewel: str = "asset:db"):
    if _rate_limited(_client_ip(request)):
        return _sample_answer("rate limit reached")
    future = _executor.submit(_run_agent, question, crown_jewel)
    try:
        return future.result(timeout=AGENT_TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError:
        return _sample_answer("agent timed out")
    except (Exception, SystemExit) as exc:
        return _sample_answer(f"agent unavailable ({type(exc).__name__})")
