"""spike_7a.py — throwaway: prove 7a/7b/7c against FalkorDB Cloud on a scratch graph.

Loads the exact demo-scenario graph (docs/demo-scenario.md), runs query 7a, scores
paths (7b), counts choke points (7c), prints findings, then DELETES the scratch graph.
Not part of the product — issue #10 only. Run: python scripts/spike_7a.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()
from falkordb import FalkorDB

SCRATCH = "crownpath_spike"

NODES = [
    # assets
    ("Asset", "asset:web",   {"name": "Storefront", "type": "webapp", "environment": "prod", "is_crown_jewel": False, "value": 20}),
    ("Asset", "asset:api",   {"name": "Orders API", "type": "service", "is_crown_jewel": False, "value": 40}),
    ("Asset", "asset:admin", {"name": "Admin console", "type": "service", "is_crown_jewel": False, "value": 60}),
    ("Asset", "asset:db",    {"name": "Customer database", "type": "database", "is_crown_jewel": True, "value": 100}),
    # identities
    ("Identity", "id:anon",  {"role": "anonymous", "privilege_level": 0}),
    ("Identity", "id:user",  {"role": "user", "privilege_level": 1}),
    ("Identity", "id:admin", {"role": "admin", "privilege_level": 3}),
    # endpoints
    ("Endpoint", "ep:search",   {"url": "/search", "method": "GET", "auth_required": False}),
    ("Endpoint", "ep:go",       {"url": "/go", "method": "GET", "auth_required": False}),
    ("Endpoint", "ep:login",    {"url": "/login", "method": "POST", "auth_required": False}),
    ("Endpoint", "ep:metrics",  {"url": "/metrics", "method": "GET", "auth_required": False}),
    ("Endpoint", "ep:orders",   {"url": "/api/orders", "method": "GET", "auth_required": True}),
    ("Endpoint", "ep:adminapi", {"url": "/admin", "method": "GET", "auth_required": True}),
    # findings (confirmed unless noted)
    ("Finding", "f:xss",        {"title": "Reflected XSS", "vuln_type": "xss", "cwe": "CWE-79", "cvss": 6.1, "confidence": 0.9, "status": "confirmed"}),
    ("Finding", "f:redirect",   {"title": "Open redirect", "vuln_type": "open_redirect", "cwe": "CWE-601", "cvss": 5.0, "confidence": 0.6, "status": "confirmed"}),
    ("Finding", "f:authbypass", {"title": "Auth bypass", "vuln_type": "auth_bypass", "cwe": "CWE-287", "cvss": 7.5, "confidence": 0.7, "status": "confirmed"}),
    ("Finding", "f:idor",       {"title": "IDOR on /api/orders", "vuln_type": "idor", "cwe": "CWE-639", "cvss": 8.1, "confidence": 0.85, "status": "confirmed"}),
    ("Finding", "f:ssrf",       {"title": "SSRF on /metrics", "vuln_type": "ssrf", "cwe": "CWE-918", "cvss": 8.0, "confidence": 0.5, "status": "confirmed"}),
    ("Finding", "f:sqli",       {"title": "SQLi on /admin", "vuln_type": "sqli", "cwe": "CWE-89", "cvss": 9.0, "confidence": 0.4, "status": "confirmed"}),
    ("Finding", "f:massassign", {"title": "Mass assignment", "vuln_type": "mass_assignment", "cwe": "CWE-915", "cvss": 6.5, "confidence": 0.6, "status": "confirmed"}),
    ("Finding", "f:csrf",       {"title": "CSRF", "vuln_type": "csrf", "cwe": "CWE-352", "cvss": 4.0, "confidence": 0.3, "status": "inconclusive"}),
]

EDGES = [
    # EXPOSES
    ("asset:web", "EXPOSES", "ep:search"), ("asset:web", "EXPOSES", "ep:go"), ("asset:web", "EXPOSES", "ep:login"),
    ("asset:api", "EXPOSES", "ep:metrics"), ("asset:api", "EXPOSES", "ep:orders"), ("asset:admin", "EXPOSES", "ep:adminapi"),
    # HAS_FINDING
    ("ep:search", "HAS_FINDING", "f:xss"), ("ep:search", "HAS_FINDING", "f:csrf"),
    ("ep:go", "HAS_FINDING", "f:redirect"), ("ep:login", "HAS_FINDING", "f:authbypass"),
    ("ep:orders", "HAS_FINDING", "f:idor"), ("ep:metrics", "HAS_FINDING", "f:ssrf"),
    ("ep:adminapi", "HAS_FINDING", "f:sqli"), ("ep:adminapi", "HAS_FINDING", "f:massassign"),
    # GRANTS (confirmed only)
    ("f:xss", "GRANTS", "id:user"), ("f:redirect", "GRANTS", "id:user"),
    ("f:authbypass", "GRANTS", "id:user"), ("f:massassign", "GRANTS", "id:admin"),
    # LEADS_TO (confirmed only)
    ("f:idor", "LEADS_TO", "asset:db"), ("f:ssrf", "LEADS_TO", "asset:admin"), ("f:sqli", "LEADS_TO", "asset:db"),
    # CAN_ACCESS
    ("id:user", "CAN_ACCESS", "asset:api"), ("id:admin", "CAN_ACCESS", "asset:db"),
    # CONNECTS_TO
    ("asset:admin", "CONNECTS_TO", "asset:api"),
]

Q7A = (
    "MATCH path = (e:Endpoint {auth_required:false})"
    "-[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->"
    "(j:Asset {is_crown_jewel:true}) "
    "RETURN [n IN nodes(path) | coalesce(n.id, n.name)] AS hops, length(path) AS len "
    "ORDER BY len ASC"
)


def load(g):
    for label, nid, props in NODES:
        sets = ", ".join(f"n.{k}=${k}" for k in props)
        g.query(f"MERGE (n:{label} {{id:$id}}) SET {sets}", {"id": nid, **props})
    for a, rel, b in EDGES:
        g.query(f"MATCH (x {{id:$a}}),(y {{id:$b}}) MERGE (x)-[:{rel}]->(y)", {"a": a, "b": b})


def main():
    host = os.environ.get("FALKORDB_HOST")
    port = int(os.environ.get("FALKORDB_PORT", "6379"))
    db = FalkorDB(host=host, port=port,
                  username=os.environ.get("FALKORDB_USERNAME") or None,
                  password=os.environ.get("FALKORDB_PASSWORD") or None,
                  ssl=str(os.environ.get("FALKORDB_SSL", "")).lower() in ("1", "true", "yes", "on"),
                  socket_connect_timeout=15, socket_timeout=30)
    g = db.select_graph(SCRATCH)
    try:
        g.query("MATCH (n) DETACH DELETE n")  # clean start if re-run
    except Exception:
        pass
    load(g)
    print("loaded nodes/edges\n")

    # ---- 7a
    res = g.query(Q7A)
    paths = [(row[0], row[1]) for row in res.result_set]
    print(f"=== 7a: {len(paths)} path(s) entry->crown jewel ===")
    for hops, ln in paths:
        mark = "IDOR" if "f:idor" in hops else "    "
        print(f"  [{mark}] len={ln}  " + " -> ".join(hops))

    # ---- 7c: choke-point count (primary deterministic method)
    from collections import Counter
    fc = Counter()
    for hops, _ in paths:
        for n in hops:
            if n.startswith("f:"):
                fc[n] += 1
    M = len(paths)
    print(f"\n=== 7c: finding occurrence across {M} paths ===")
    for fid, c in fc.most_common():
        print(f"  {fid}: on {c}/{M} paths")
    top = fc.most_common(1)[0] if fc else ("<none>", 0)
    print(f"  CHOKE POINT -> {top[0]} severs {top[1]} of {M}")

    # ---- 7b: score = prod(confidence on path) * jewel.value / length
    conf = {nid: props["confidence"] for label, nid, props in NODES if label == "Finding"}
    jewelval = 100
    print("\n=== 7b: path scores (prod(conf)*jewelValue/len) ===")
    scored = []
    for hops, ln in paths:
        p = 1.0
        for n in hops:
            if n in conf:
                p *= conf[n]
        score = p * jewelval / ln
        scored.append((score, ln, hops))
    for score, ln, hops in sorted(scored, reverse=True):
        print(f"  score={score:6.2f} len={ln}  " + " -> ".join(hops))

    # ---- choke-point proof: remove f:idor, recount
    g.query("MATCH (n {id:'f:idor'}) DETACH DELETE n")
    res2 = g.query(Q7A)
    rem = len(res2.result_set)
    print(f"\n=== choke-point proof: after removing f:idor, {rem} path(s) remain (severed {M - rem}) ===")

    # ---- LIMIT safety check
    res3 = g.query(Q7A + " LIMIT 3")
    print(f"\n=== LIMIT 3 returns {len(res3.result_set)} rows (expect 3) ===")

    # get server version
    try:
        v = db.connection.execute_command("INFO", "server")
        import re
        m = re.search(rb"redis_version:([^\r\n]+)", v if isinstance(v, bytes) else str(v).encode())
        print("\nserver redis_version:", m.group(1).decode() if m else "?")
    except Exception as e:
        print("version lookup failed:", e)
    print("MODULE LIST:", end=" ")
    try:
        print(db.connection.execute_command("MODULE", "LIST"))
    except Exception as e:
        print("n/a", e)


if __name__ == "__main__":
    main()
