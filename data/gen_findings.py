"""data/gen_findings.py — deterministic synthetic demo findings.json.

Standalone script (no FalkorDB dependency) that transcribes the frozen demo
scenario (docs/demo-scenario.md, issue #7) into a findings.json document that
validates against docs/findings.schema.json (issue #5). Rule 6: synthetic data
we own. Re-running produces byte-identical output.

Usage:
    python data/gen_findings.py [--out data/findings.json]
    python data/gen_findings.py --scenario regress   # issue #23: two dated scans
        writes data/findings.scan1.json (the demo minus f:idor) and
        data/findings.scan2.json (identical to the frozen demo) for lib/memory.py.
"""
import argparse
import json
import os

# Fixed vuln_type -> Technique.id mapping. These are the swiftPentest `class`
# slugs the taxonomy seed (issue #14) uses as Technique.id. If #14 keys
# Technique.id differently, update this one constant to match.
TECHNIQUE_ID_BY_VULN_TYPE = {
    "xss": "xss",
    "open_redirect": "open-redirect",
    "auth_bypass": "bfla",
    "idor": "idor",
    "ssrf": "ssrf",
    "sqli": "sqli",
    "mass_assignment": "mass-assignment",
    "csrf": "csrf",
}

ASSETS = [
    {"id": "asset:web", "name": "Storefront", "type": "webapp", "environment": "prod",
     "is_crown_jewel": False, "value": 20},
    {"id": "asset:api", "name": "Orders API", "type": "service", "environment": "prod",
     "is_crown_jewel": False, "value": 40},
    {"id": "asset:admin", "name": "Admin console", "type": "service", "environment": "prod",
     "is_crown_jewel": False, "value": 60},
    {"id": "asset:db", "name": "Customer database", "type": "database", "environment": "prod",
     "is_crown_jewel": True, "value": 100},
]

IDENTITIES = [
    {"id": "id:anon", "role": "anonymous", "privilege_level": 0},
    {"id": "id:user", "role": "user", "privilege_level": 1},
    {"id": "id:admin", "role": "admin", "privilege_level": 3},
]

ENDPOINTS = [
    {"id": "ep:search", "asset_id": "asset:web", "url": "/search", "method": "GET", "auth_required": False},
    {"id": "ep:go", "asset_id": "asset:web", "url": "/go", "method": "GET", "auth_required": False},
    {"id": "ep:login", "asset_id": "asset:web", "url": "/login", "method": "POST", "auth_required": False},
    {"id": "ep:metrics", "asset_id": "asset:api", "url": "/metrics", "method": "GET", "auth_required": False},
    {"id": "ep:orders", "asset_id": "asset:api", "url": "/api/orders", "method": "GET", "auth_required": True},
    {"id": "ep:adminapi", "asset_id": "asset:admin", "url": "/admin", "method": "GET", "auth_required": True},
]

# (id, title, vuln_type, cwe, cvss, confidence, status, endpoint_id, grants_identity_id, leads_to_asset_id)
_FINDING_ROWS = [
    ("f:xss", "Reflected XSS on /search", "xss", "CWE-79", 6.1, 0.9, "confirmed",
     "ep:search", "id:user", None),
    ("f:redirect", "Open redirect on /go", "open_redirect", "CWE-601", 5.0, 0.6, "confirmed",
     "ep:go", "id:user", None),
    ("f:authbypass", "Auth bypass on /login", "auth_bypass", "CWE-287", 7.5, 0.7, "confirmed",
     "ep:login", "id:user", None),
    ("f:idor", "IDOR on /api/orders", "idor", "CWE-639", 8.1, 0.85, "confirmed",
     "ep:orders", None, "asset:db"),
    ("f:ssrf", "SSRF on /metrics", "ssrf", "CWE-918", 8.0, 0.5, "confirmed",
     "ep:metrics", None, "asset:admin"),
    ("f:sqli", "SQLi on /admin", "sqli", "CWE-89", 9.0, 0.4, "confirmed",
     "ep:adminapi", None, "asset:db"),
    ("f:massassign", "Mass assignment on /admin", "mass_assignment", "CWE-915", 6.5, 0.6, "confirmed",
     "ep:adminapi", "id:admin", None),
    ("f:csrf", "CSRF on /search", "csrf", "CWE-352", 4.0, 0.3, "inconclusive",
     "ep:search", None, None),
]

CONNECTIONS = [
    {"from_asset_id": "asset:admin", "to_asset_id": "asset:api"},
]

ACCESS = [
    {"identity_id": "id:user", "asset_id": "asset:api"},
    {"identity_id": "id:admin", "asset_id": "asset:db"},
]


def build_findings():
    findings = []
    for (fid, title, vuln_type, cwe, cvss, confidence, status, endpoint_id,
         grants_identity_id, leads_to_asset_id) in _FINDING_ROWS:
        finding = {
            "id": fid,
            "title": title,
            "vuln_type": vuln_type,
            "cwe": cwe,
            "cvss": cvss,
            "confidence": confidence,
            "status": status,
            "endpoint_id": endpoint_id,
            "technique_id": TECHNIQUE_ID_BY_VULN_TYPE[vuln_type],
        }
        if grants_identity_id is not None:
            finding["grants_identity_id"] = grants_identity_id
        if leads_to_asset_id is not None:
            finding["leads_to_asset_id"] = leads_to_asset_id
        findings.append(finding)
    return findings


def build_document():
    return {
        "assets": ASSETS,
        "endpoints": ENDPOINTS,
        "identities": IDENTITIES,
        "findings": build_findings(),
        "connections": CONNECTIONS,
        "access": ACCESS,
    }


# Finding the earlier scan had not yet discovered (issue #23): scan 2 adds it, which
# opens four new paths to the crown jewel through asset:api.
REGRESSION_FINDING_ID = "f:idor"


def _write(doc, out):
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"wrote {out}")


def build_regress_documents():
    """(scan1, scan2): scan2 is the frozen demo; scan1 is the same estate before
    REGRESSION_FINDING_ID was found."""
    scan2 = build_document()
    scan1 = build_document()
    scan1["findings"] = [f for f in scan1["findings"] if f["id"] != REGRESSION_FINDING_ID]
    return scan1, scan2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join("data", "findings.json"))
    parser.add_argument("--scenario", choices=["demo", "regress"], default="demo")
    args = parser.parse_args()

    if args.scenario == "regress":
        scan1, scan2 = build_regress_documents()
        _write(scan1, os.path.join("data", "findings.scan1.json"))
        _write(scan2, os.path.join("data", "findings.scan2.json"))
        return

    _write(build_document(), args.out)


if __name__ == "__main__":
    main()
