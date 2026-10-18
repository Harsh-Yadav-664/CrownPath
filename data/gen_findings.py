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
    python data/gen_findings.py --scenario large [--out data/findings.large.json]
        a larger synthetic estate (20 assets, three tiers, three crown jewels). It is
        an extra dataset: the frozen demo above is unchanged and stays the default.
        Load it into its own graph: `make seed-large`.
"""
import argparse
import datetime
import json
import os
import random

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


# ---------------------------------------------------------------------------------
# --scenario large: the whole Acme Shop estate, three tiers, three crown jewels.
# Topology is written out by hand so every chain is explainable; the seeded RNG only
# sets discovered_at, so the output is still byte-identical on every run.
#   internet-facing: storefront, mobile-gw, partner-api, cms, support, staging, backups
#   application:     orders, payments, catalog, sso, admin, reporting, ci, jumphost
#   data:            customer-db*, card-vault*, secrets*, orders-db, warehouse  (* crown jewel)
# Intended answers (checked by tests/test_large_scenario.py): 7 paths to the customer
# database, 5 to the card vault (all through the deserialization bug), 2 to the cloud
# secrets manager. The highest-CVSS findings (staging RCE 9.8, CMS upload 8.8) are on no path.
LARGE_SEED = 20261018
LARGE_SCAN_START = datetime.datetime(2026, 10, 14, 9, 0, tzinfo=datetime.timezone.utc)

LARGE_TECHNIQUE_IDS = {
    "f:sf-stuffing": "account-takeover", "f:sf-git": "exposed-git", "f:mg-jwt": "jwt",
    "f:cms-ssrf": "cloud-metadata-creds", "f:cms-upload": "insecure-file-upload",
    "f:pay-deser": "insecure-deserialization", "f:cat-debug": "information-disclosure",
    "f:ci-secrets": "secret-exposure", "f:jh-cmdi": "os-command-injection",
    "f:bk-public": "cloud-storage-exposure", "f:stg-cve": "known-cve",
    "f:cat-traversal": "path-traversal", "f:mg-cors": "cors",
}

# (id, name, type, environment, is_crown_jewel, value)
_LARGE_ASSET_ROWS = [
    ("asset:storefront", "Storefront", "webapp", "prod", False, 20),
    ("asset:mobile-gw", "Mobile API gateway", "service", "prod", False, 30),
    ("asset:partner-api", "Partner API", "service", "prod", False, 30),
    ("asset:cms", "Marketing CMS", "webapp", "prod", False, 15),
    ("asset:support", "Support portal", "webapp", "prod", False, 25),
    ("asset:staging", "Staging storefront", "webapp", "staging", False, 10),
    ("asset:backups", "Backup storage", "host", "prod", False, 55),
    ("asset:orders", "Orders service", "service", "prod", False, 40),
    ("asset:payments", "Payments service", "service", "prod", False, 60),
    ("asset:catalog", "Catalog service", "service", "prod", False, 20),
    ("asset:sso", "Identity provider (SSO)", "service", "prod", False, 70),
    ("asset:admin", "Admin console", "service", "prod", False, 60),
    ("asset:reporting", "Reporting service", "service", "prod", False, 35),
    ("asset:ci", "CI/CD server", "host", "corp", False, 65),
    ("asset:jumphost", "Ops jump host", "host", "corp", False, 50),
    ("asset:customer-db", "Customer database", "database", "prod", True, 100),
    ("asset:card-vault", "Payment card vault", "database", "prod", True, 95),
    ("asset:secrets", "Cloud secrets manager", "service", "prod", True, 90),
    ("asset:orders-db", "Orders database", "database", "prod", False, 50),
    ("asset:warehouse", "Analytics warehouse", "database", "prod", False, 45),
]

LARGE_IDENTITIES = [
    {"id": "id:anon", "role": "anonymous", "privilege_level": 0},
    {"id": "id:customer", "role": "user", "privilege_level": 1},
    {"id": "id:support-agent", "role": "user", "privilege_level": 1},
    {"id": "id:admin", "role": "admin", "privilege_level": 3},
    {"id": "id:ci-bot", "role": "admin", "privilege_level": 3},
    {"id": "id:cloud-admin", "role": "admin", "privilege_level": 3},
]

# (id, asset_id, url, method, auth_required)
_LARGE_ENDPOINT_ROWS = [
    ("ep:sf-search", "asset:storefront", "/search", "GET", False),
    ("ep:sf-login", "asset:storefront", "/login", "POST", False),
    ("ep:sf-git", "asset:storefront", "/.git/config", "GET", False),
    ("ep:sf-account", "asset:storefront", "/account", "GET", True),
    ("ep:mg-token", "asset:mobile-gw", "/v2/auth/token", "POST", False),
    ("ep:mg-profile", "asset:mobile-gw", "/v2/profile", "GET", True),
    ("ep:pa-webhook", "asset:partner-api", "/v1/webhooks/test", "POST", False),
    ("ep:pa-catalog", "asset:partner-api", "/v1/catalog", "GET", True),
    ("ep:cms-preview", "asset:cms", "/cms/preview", "GET", False),
    ("ep:cms-media", "asset:cms", "/cms/media", "POST", True),
    ("ep:sp-tickets", "asset:support", "/support/tickets", "POST", False),
    ("ep:sp-inbox", "asset:support", "/support/inbox", "GET", True),
    ("ep:stg-app", "asset:staging", "/", "GET", False),
    ("ep:bk-bucket", "asset:backups", "/backups/", "GET", False),
    ("ep:or-orders", "asset:orders", "/api/orders/{id}", "GET", True),
    ("ep:or-export", "asset:orders", "/api/orders/export", "GET", True),
    ("ep:pay-jobs", "asset:payments", "/internal/jobs", "POST", True),
    ("ep:pay-refunds", "asset:payments", "/api/refunds", "POST", True),
    ("ep:cat-debug", "asset:catalog", "/api/catalog/debug", "GET", True),
    ("ep:cat-files", "asset:catalog", "/api/catalog/files", "GET", True),
    ("ep:sso-users", "asset:sso", "/sso/users/me", "PATCH", True),
    ("ep:ad-users", "asset:admin", "/admin/users", "GET", True),
    ("ep:rp-export", "asset:reporting", "/reports/export", "GET", True),
    ("ep:ci-logs", "asset:ci", "/ci/pipelines/logs", "GET", True),
    ("ep:jh-console", "asset:jumphost", "/ops/console", "POST", True),
]

# (id, title, vuln_type, cwe, cvss, confidence, status, endpoint_id, grants, leads_to, evidence)
_LARGE_FINDING_ROWS = [
    ("f:sf-xss", "Reflected XSS on /search", "xss", "CWE-79", 6.1, 0.9, "confirmed",
     "ep:sf-search", "id:customer", None, "The q parameter is echoed unescaped into the results heading."),
    ("f:sf-stuffing", "Credential stuffing on /login (no rate limit or lockout)", "auth_bypass", "CWE-307",
     6.5, 0.75, "confirmed", "ep:sf-login", "id:customer", None,
     "500 failed logins in a minute were accepted with no lockout, CAPTCHA or delay."),
    ("f:sf-git", "Exposed .git/config with a CI deploy token", "info_disclosure", "CWE-538", 7.5, 0.95,
     "confirmed", "ep:sf-git", "id:ci-bot", None,
     "/.git/config is served and its remote URL embeds a CI deploy token."),
    ("f:mg-jwt", "JWT with alg 'none' accepted on /v2/auth/token", "auth_bypass", "CWE-347", 8.2, 0.8,
     "confirmed", "ep:mg-token", "id:customer", None,
     "An unsigned token with alg=none was accepted as a valid customer session."),
    ("f:mg-cors", "Reflected Origin with credentials on /v2/profile", "cors", "CWE-942", 5.4, 0.4,
     "inconclusive", "ep:mg-profile", None, None,
     "Origin is reflected with Allow-Credentials: true; a cross-site read was not reproduced."),
    ("f:pa-ssrf", "SSRF in the webhook tester /v1/webhooks/test", "ssrf", "CWE-918", 8.6, 0.65, "confirmed",
     "ep:pa-webhook", None, "asset:payments", "The tester fetched an internal Payments service URL and returned its body."),
    ("f:cms-ssrf", "SSRF to cloud metadata via /cms/preview", "ssrf", "CWE-918", 7.7, 0.55, "confirmed",
     "ep:cms-preview", "id:cloud-admin", None,
     "The preview URL fetched the instance metadata service, exposing role credentials."),
    ("f:cms-upload", "Unrestricted file upload on /cms/media", "file_upload", "CWE-434", 8.8, 0.6,
     "confirmed", "ep:cms-media", None, "asset:cms", "A .php file uploaded by an editor account executed on the CMS host."),
    ("f:sp-xss", "Stored XSS in support ticket body", "xss", "CWE-79", 5.4, 0.75, "confirmed",
     "ep:sp-tickets", "id:support-agent", None,
     "Script in an anonymous ticket ran in the agent inbox and read the agent session."),
    ("f:sp-csrf", "CSRF on /support/inbox", "csrf", "CWE-352", 4.3, 0.3, "inconclusive",
     "ep:sp-inbox", None, None, "No CSRF token on inbox actions; SameSite cookies may already block it."),
    ("f:stg-cve", "Known RCE in the outdated web framework on staging", "rce", "CWE-94", 9.8, 0.9,
     "confirmed", "ep:stg-app", None, "asset:staging",
     "The framework version banner matches a public RCE advisory; the probe executed `id`."),
    ("f:bk-public", "Publicly listable backup bucket", "info_disclosure", "CWE-200", 7.5, 0.35,
     "inconclusive", "ep:bk-bucket", None, "asset:customer-db",
     "The bucket listing is public; whether the dump files are readable was not verified."),
    ("f:or-idor", "IDOR on /api/orders/{id}", "idor", "CWE-639", 8.1, 0.85, "confirmed",
     "ep:or-orders", None, "asset:customer-db",
     "Changing the order id returned another customer's name, address and order history."),
    ("f:or-sqli", "SQL injection in /api/orders/export", "sqli", "CWE-89", 8.6, 0.5, "confirmed",
     "ep:or-export", None, "asset:orders-db", "A time-based payload in the date filter delayed the response by 5 s."),
    ("f:pay-deser", "Insecure deserialization on /internal/jobs", "deserialization", "CWE-502", 9.8, 0.6,
     "confirmed", "ep:pay-jobs", None, "asset:card-vault",
     "A crafted serialized job object triggered an outbound callback from the Payments service."),
    ("f:cat-debug", "Stack traces from /api/catalog/debug", "info_disclosure", "CWE-209", 5.3, 0.9,
     "confirmed", "ep:cat-debug", None, None, "The debug route returns full stack traces with library versions."),
    ("f:cat-traversal", "Path traversal on /api/catalog/files", "path_traversal", "CWE-22", 7.5, 0.2,
     "refuted", "ep:cat-files", None, None, "../ sequences are normalised before the file lookup; no file outside the root was read."),
    ("f:sso-massassign", "Role field writable on PATCH /sso/users/me", "mass_assignment", "CWE-915", 8.1, 0.55,
     "confirmed", "ep:sso-users", "id:admin", None,
     "Adding \"role\": \"admin\" to the profile update made the session an admin."),
    ("f:ad-sqli", "SQL injection on /admin/users", "sqli", "CWE-89", 9.1, 0.45, "confirmed",
     "ep:ad-users", None, "asset:customer-db", "A boolean payload in the search parameter changed the row count."),
    ("f:rp-sqli", "SQL injection on /reports/export", "sqli", "CWE-89", 8.8, 0.5, "confirmed",
     "ep:rp-export", None, "asset:warehouse", "An error-based payload in the report filter leaked the warehouse schema."),
    ("f:ci-secrets", "Cloud credentials printed in CI pipeline logs", "info_disclosure", "CWE-532", 7.5, 0.8,
     "confirmed", "ep:ci-logs", "id:cloud-admin", None, "A deploy job echoes cloud access keys into build logs readable by any CI user."),
    ("f:jh-cmdi", "OS command injection in /ops/console", "rce", "CWE-78", 9.0, 0.5, "confirmed",
     "ep:jh-console", None, "asset:backups", "The host field is passed to a shell; `;id` ran on the jump host."),
]

LARGE_CONNECTIONS = [
    {"from_asset_id": "asset:orders", "to_asset_id": "asset:payments"},
    {"from_asset_id": "asset:admin", "to_asset_id": "asset:payments"},
    {"from_asset_id": "asset:admin", "to_asset_id": "asset:jumphost"},
]

LARGE_ACCESS = [
    {"identity_id": "id:customer", "asset_id": "asset:orders"},
    {"identity_id": "id:customer", "asset_id": "asset:catalog"},
    {"identity_id": "id:customer", "asset_id": "asset:sso"},
    {"identity_id": "id:support-agent", "asset_id": "asset:admin"},
    {"identity_id": "id:admin", "asset_id": "asset:customer-db"},
    {"identity_id": "id:admin", "asset_id": "asset:reporting"},
    {"identity_id": "id:admin", "asset_id": "asset:ci"},
    {"identity_id": "id:ci-bot", "asset_id": "asset:ci"},
    {"identity_id": "id:cloud-admin", "asset_id": "asset:secrets"},
    {"identity_id": "id:cloud-admin", "asset_id": "asset:backups"},
]


def build_large_document():
    rng = random.Random(LARGE_SEED)
    findings = []
    for (fid, title, vuln_type, cwe, cvss, confidence, status, endpoint_id,
         grants, leads_to, evidence) in _LARGE_FINDING_ROWS:
        found = LARGE_SCAN_START + datetime.timedelta(minutes=rng.randrange(0, 3 * 24 * 60))
        finding = {
            "id": fid, "title": title, "vuln_type": vuln_type, "cwe": cwe, "cvss": cvss,
            "confidence": confidence, "status": status, "endpoint_id": endpoint_id,
            "technique_id": LARGE_TECHNIQUE_IDS.get(fid, TECHNIQUE_ID_BY_VULN_TYPE.get(vuln_type)),
            "discovered_at": found.strftime("%Y-%m-%dT%H:%M:%SZ"), "evidence": evidence,
        }
        if grants is not None:
            finding["grants_identity_id"] = grants
        if leads_to is not None:
            finding["leads_to_asset_id"] = leads_to
        findings.append(finding)
    return {
        "assets": [
            {"id": a, "name": n, "type": t, "environment": e, "is_crown_jewel": j, "value": v}
            for a, n, t, e, j, v in _LARGE_ASSET_ROWS
        ],
        "endpoints": [
            {"id": e, "asset_id": a, "url": u, "method": m, "auth_required": auth}
            for e, a, u, m, auth in _LARGE_ENDPOINT_ROWS
        ],
        "identities": LARGE_IDENTITIES,
        "findings": findings,
        "connections": LARGE_CONNECTIONS,
        "access": LARGE_ACCESS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    parser.add_argument("--scenario", choices=["demo", "regress", "large"], default="demo")
    args = parser.parse_args()

    if args.scenario == "regress":
        scan1, scan2 = build_regress_documents()
        _write(scan1, os.path.join("data", "findings.scan1.json"))
        _write(scan2, os.path.join("data", "findings.scan2.json"))
        return

    if args.scenario == "large":
        _write(build_large_document(), args.out or os.path.join("data", "findings.large.json"))
        return

    _write(build_document(), args.out or os.path.join("data", "findings.json"))


if __name__ == "__main__":
    main()
