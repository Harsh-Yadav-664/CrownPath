"""lib/seed_taxonomy.py — seed Technique nodes + CHAINS_TO edges from the lifted
swiftPentest taxonomy (BUILD_SPEC.md §5, issue #14 / B3).

Reads data/taxonomy/{techniques.jsonl, classes.jsonl, chains.jsonl} (copied verbatim
from ../swiftpentest-fork; logged in docs/REUSE.md). remediation.tsv is also copied
there for the agent output (issue #19) but is not consumed here.

Canonical load order: init_schema(g) -> seed(g) -> lib.ingest.ingest(g, findings_path).
Use load_all(g) for that whole sequence in one call (resolves the #13 note about where
this convenience function lives, to avoid an import cycle with lib.ingest).
"""
import argparse
import json
import os

from lib import graph, schema

TAXONOMY_DIR = os.path.join("data", "taxonomy")
TECHNIQUES_PATH = os.path.join(TAXONOMY_DIR, "techniques.jsonl")
CLASSES_PATH = os.path.join(TAXONOMY_DIR, "classes.jsonl")
CHAINS_PATH = os.path.join(TAXONOMY_DIR, "chains.jsonl")

# one `from` value in chains.jsonl matches nothing in the taxonomy; alias it.
ALIASES = {"xss-reflected": "xss"}

# Technique.capability mapping (schema.TECHNIQUE_CAPABILITIES). Display/explanation
# only -- not used by query 7a. Any class/slug not listed below defaults to
# "data_read" (safe default).
CAPABILITY_BY_SLUG = {
    "xss": "session_theft",
    "idor": "data_read",
    "ssrf": "ssrf_pivot",
    "sqli": "data_read",
    "bfla": "auth_bypass",
    "mass-assignment": "priv_esc",
    "open-redirect": "session_theft",
    "csrf": "auth_bypass",
    "rce": "rce",
    "command-injection": "rce",
    "ssti": "rce",
    "file-upload": "rce",
    "deserialization": "rce",
    "session-theft": "session_theft",
    "account-takeover": "auth_bypass",
    "privilege-escalation": "priv_esc",
    "secret-exposure": "data_read",
    "mass-extraction": "data_read",
    "authz-bypass": "auth_bypass",
}
DEFAULT_CAPABILITY = "data_read"


def _read_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _alias(slug):
    return ALIASES.get(slug, slug)


def _display_name(slug):
    return slug.replace("-", " ").title()


def _capability(slug):
    return CAPABILITY_BY_SLUG.get(slug, DEFAULT_CAPABILITY)


def _load_taxonomy():
    techniques = _read_jsonl(TECHNIQUES_PATH)
    classes = _read_jsonl(CLASSES_PATH)
    chains = _read_jsonl(CHAINS_PATH)
    return techniques, classes, chains


def _build_technique_nodes(techniques, classes, chains):
    """Return {slug: {"id", "name", "cwe", "capability"}} for the union of:
    (a) every distinct `class` in techniques.jsonl, (b) every `slug` in
    classes.jsonl, (c) every from/to outcome slug in chains.jsonl (aliased)."""
    cwe_by_class = {}
    for t in techniques:
        cls = t["class"]
        if cls not in cwe_by_class:
            cwe_by_class[cls] = t.get("cwe", "")

    slugs = set(cwe_by_class.keys())
    slugs.update(c["slug"] for c in classes)
    for row in chains:
        slugs.add(_alias(row["from"]))
        slugs.add(_alias(row["to"]))

    nodes = {}
    for slug in slugs:
        nodes[slug] = {
            "id": slug,
            "name": _display_name(slug),
            "cwe": cwe_by_class.get(slug, ""),
            "capability": _capability(slug),
        }
    return nodes


def seed(g):
    """Seed Technique nodes + CHAINS_TO edges from data/taxonomy/*. Returns a dict
    of counts: {"techniques": int, "chains": int, "auto_created": int}."""
    techniques, classes, chains = _load_taxonomy()
    nodes = _build_technique_nodes(techniques, classes, chains)

    for node in nodes.values():
        graph.run(
            g,
            "MERGE (t:Technique {id:$id}) SET t.name=$name, t.cwe=$cwe, t.capability=$capability",
            node,
        )

    auto_created = 0
    for row in chains:
        src = _alias(row["from"])
        dst = _alias(row["to"])
        for slug in (src, dst):
            if slug not in nodes:
                node = {
                    "id": slug,
                    "name": _display_name(slug),
                    "cwe": "",
                    "capability": _capability(slug),
                }
                graph.run(
                    g,
                    "MERGE (t:Technique {id:$id}) SET t.name=$name, t.cwe=$cwe, t.capability=$capability",
                    node,
                )
                nodes[slug] = node
                auto_created += 1

        graph.run(
            g,
            """
            MATCH (a:Technique {id:$src}), (b:Technique {id:$dst})
            MERGE (a)-[r:CHAINS_TO]->(b)
            SET r.gain=$gain, r.multiplier=$multiplier
            """,
            {
                "src": src,
                "dst": dst,
                "gain": row.get("gain", ""),
                "multiplier": row.get("impact_multiplier", 1.0),
            },
        )

    return {
        "techniques": len(nodes),
        "chains": len(chains),
        "auto_created": auto_created,
    }


def load_all(g, findings_path="data/findings.json"):
    """Canonical load order: init_schema -> seed taxonomy -> ingest findings."""
    from lib import ingest  # local import: avoids an import cycle with lib.ingest

    graph.init_schema(g)
    seed_result = seed(g)
    ingest_result = ingest.ingest(g, findings_path)
    return {"seed": seed_result, "ingest": ingest_result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="run load_all (schema+taxonomy+findings)")
    parser.add_argument("--findings", default="data/findings.json")
    args = parser.parse_args()

    g = graph.connect()
    if args.all:
        result = load_all(g, args.findings)
    else:
        result = seed(g)
    print(result)


if __name__ == "__main__":
    main()
