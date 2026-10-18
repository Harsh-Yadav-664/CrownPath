"""data/capture_findings.py -- capture findings from a REAL run against our own
loopback target (BUILD_SPEC.md §9 P2, issue #24 / E2). Written fresh for CrownPath;
only the control-contrast *idea* comes from swiftPentest (docs/REUSE.md).

It starts data/demo_target.py on 127.0.0.1, probes each endpoint with a control
request and a payload request, and only marks a finding `confirmed` when the payload
behaves differently from the control (otherwise `inconclusive`). The result is written
as data/findings.captured.json in the docs/findings.schema.json shape, so the normal
pipeline ingests it unchanged:

    python data/capture_findings.py
    python -m lib.seed_taxonomy --all --findings data/findings.captured.json

It is an ALTERNATIVE dataset; data/findings.json stays the default demo so the
"4 of 6" numbers remain deterministic.

Rule 6 guard: every request goes through `_get`, which refuses any URL whose host is
not loopback -- the script can never touch a third-party host.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from urllib.parse import quote, urlparse

import jsonschema

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demo_target  # noqa: E402  (stdlib-only sibling module)

OUT_PATH = os.path.join("data", "findings.captured.json")
SCHEMA_PATH = os.path.join("docs", "findings.schema.json")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # never follow: an open-redirect probe must not leave loopback


_opener = urllib.request.build_opener(_NoRedirect)


def assert_loopback_url(url):
    host = urlparse(url).hostname or ""
    if not demo_target.is_loopback_host(host):
        raise SystemExit(f"capture_findings refuses non-loopback target {url!r} (Rule 6)")


def _get(url):
    """(status, headers, body). Loopback only; redirects are not followed."""
    assert_loopback_url(url)
    try:
        with _opener.open(url, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read().decode("utf-8", "replace")


# --- detections: each returns (status, confidence, evidence) -------------------

def detect_xss(base):
    token = uuid.uuid4().hex[:8]
    control = f"cp{token}"
    payload = f"<b id=cp{token}>"
    _, _, control_body = _get(f"{base}/search?q={quote(control)}")
    _, _, payload_body = _get(f"{base}/search?q={quote(payload)}")
    if control in control_body and payload in payload_body:
        return "confirmed", 0.9, f"payload {payload!r} reflected unescaped in /search (control reflected as text)"
    if control in control_body:
        return "refuted", 0.8, "payload was reflected HTML-encoded"
    return "inconclusive", 0.3, "control value not reflected"


def detect_open_redirect(base):
    target = "http://cp-redirect-check.invalid/x"  # never contacted: redirects aren't followed
    status, headers, _ = _get(f"{base}/go?next={quote(target)}")
    control_status, control_headers, _ = _get(f"{base}/go?next=/")
    if status in (301, 302, 303, 307, 308) and headers.get("Location") == target \
            and control_headers.get("Location") == "/":
        return "confirmed", 0.85, f"/go redirected to attacker-chosen absolute URL (HTTP {status})"
    return "inconclusive", 0.3, f"no off-site redirect observed (HTTP {status})"


def detect_git_exposure(base):
    status, _, body = _get(f"{base}/.git/HEAD")
    _, _, control_body = _get(f"{base}/.git/cp-{uuid.uuid4().hex[:6]}")
    if status == 200 and body.startswith("ref:") and not control_body.startswith("ref:"):
        return "confirmed", 0.95, "/.git/HEAD served repository metadata"
    return "inconclusive", 0.2, f"/.git/HEAD returned HTTP {status}"


def detect_sqli(base):
    c_status, _, c_body = _get(f"{base}/item?id=1")
    p_status, _, p_body = _get(f"{base}/item?id={quote(chr(39))}")
    if c_status == 200 and p_status >= 500 and "sql" in p_body.lower():
        return "confirmed", 0.8, "a single quote in id= produced a SQL error that the control (id=1) did not"
    return "inconclusive", 0.3, f"no SQL error signal (control HTTP {c_status}, payload HTTP {p_status})"


# --- the (modelled) estate the findings are attached to -------------------------

def build_document(base):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    results = {
        "xss": detect_xss(base),
        "redirect": detect_open_redirect(base),
        "git": detect_git_exposure(base),
        "sqli": detect_sqli(base),
    }

    def finding(key, fid, title, vuln_type, cwe, cvss, endpoint_id, technique_id, **links):
        status, confidence, evidence = results[key]
        return {
            "id": fid, "title": title, "vuln_type": vuln_type, "cwe": cwe, "cvss": cvss,
            "confidence": confidence, "status": status, "evidence": evidence,
            "discovered_at": now, "endpoint_id": endpoint_id, "technique_id": technique_id,
            **links,
        }

    return {
        "assets": [
            {"id": "asset:lab-web", "name": "Lab shop", "type": "webapp",
             "environment": "loopback", "is_crown_jewel": False, "value": 30},
            # Modelled, not probed: the lab shop's backing store. The SQLi finding is the
            # (real, observed) way into it.
            {"id": "asset:lab-db", "name": "Lab customer store", "type": "database",
             "environment": "loopback", "is_crown_jewel": True, "value": 100},
        ],
        "endpoints": [
            {"id": "ep:lab-search", "asset_id": "asset:lab-web", "url": "/search", "method": "GET", "auth_required": False},
            {"id": "ep:lab-go", "asset_id": "asset:lab-web", "url": "/go", "method": "GET", "auth_required": False},
            {"id": "ep:lab-git", "asset_id": "asset:lab-web", "url": "/.git/HEAD", "method": "GET", "auth_required": False},
            {"id": "ep:lab-item", "asset_id": "asset:lab-web", "url": "/item", "method": "GET", "auth_required": False},
        ],
        "identities": [
            {"id": "id:anon", "role": "anonymous", "privilege_level": 0},
            {"id": "id:user", "role": "user", "privilege_level": 1},
        ],
        "findings": [
            finding("xss", "f:lab-xss", "Reflected XSS on /search", "xss", "CWE-79", 6.1,
                    "ep:lab-search", "xss", grants_identity_id="id:user"),
            finding("redirect", "f:lab-redirect", "Open redirect on /go", "open_redirect", "CWE-601", 5.0,
                    "ep:lab-go", "open-redirect"),
            finding("git", "f:lab-git", "Exposed /.git/HEAD", "info_disclosure", "CWE-538", 5.3,
                    "ep:lab-git", "source-exposure"),
            finding("sqli", "f:lab-sqli", "SQL injection on /item", "sqli", "CWE-89", 9.0,
                    "ep:lab-item", "sqli", leads_to_asset_id="asset:lab-db"),
        ],
        "connections": [],
        # Modelled trust: a stolen lab-user session can read the lab store.
        "access": [{"identity_id": "id:user", "asset_id": "asset:lab-db"}],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=OUT_PATH)
    parser.add_argument("--target", help="existing loopback base URL; default starts data/demo_target.py")
    args = parser.parse_args()

    server = None
    if args.target:
        assert_loopback_url(args.target)
        base = args.target.rstrip("/")
    else:
        server, base = demo_target.serve()

    try:
        doc = build_document(base)
    finally:
        if server:
            server.shutdown()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        jsonschema.validate(doc, json.load(f))
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write("\n")

    counts = {}
    for item in doc["findings"]:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(f"wrote {args.out} from {base}: {counts}")


if __name__ == "__main__":
    main()
