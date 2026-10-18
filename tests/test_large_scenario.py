"""tests/test_large_scenario.py -- the optional larger estate (`--scenario large`) is
deterministic and valid, and adding it left the frozen demo byte-identical."""
import json
import os
import subprocess
import sys

import jsonschema
import pytest

from data import gen_findings
from lib import seed_taxonomy

LARGE = os.path.join("data", "findings.large.json")


def _generate(tmp_path, *args):
    out = tmp_path / "out.json"
    subprocess.run([sys.executable, "data/gen_findings.py", *args, "--out", str(out)],
                   check=True, capture_output=True)
    return out.read_bytes()


def test_demo_output_is_still_byte_identical(tmp_path):
    with open(os.path.join("data", "findings.json"), "rb") as f:
        assert _generate(tmp_path) == f.read()


def test_large_is_deterministic_and_matches_the_committed_file(tmp_path):
    with open(LARGE, "rb") as f:
        committed = f.read()
    assert _generate(tmp_path, "--scenario", "large") == committed
    assert _generate(tmp_path, "--scenario", "large") == committed


def test_large_is_schema_valid_with_known_techniques():
    with open(LARGE, encoding="utf-8") as f:
        doc = json.load(f)
    with open(os.path.join("docs", "findings.schema.json"), encoding="utf-8") as f:
        jsonschema.validate(doc, json.load(f))
    techniques = set(seed_taxonomy._build_technique_nodes(*seed_taxonomy._load_taxonomy()))
    assert {f["technique_id"] for f in doc["findings"]} <= techniques
    assert len(doc["assets"]) == 20
    assert [a["id"] for a in doc["assets"] if a["is_crown_jewel"]] == \
        ["asset:customer-db", "asset:card-vault", "asset:secrets"]
    assert doc == gen_findings.build_large_document()


def test_large_paths_and_choke_points_in_falkordb():
    from lib import graph, queries, tools  # importing lib.graph loads .env

    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")
    g = graph.connect()
    try:
        seed_taxonomy.load_all(g, LARGE)
        tools._g = None
        expected = {"asset:customer-db": (7, "f:or-idor", 3),
                    "asset:card-vault": (5, "f:pay-deser", 5),
                    "asset:secrets": (2, "f:cms-ssrf", 1)}
        for jewel, (n_paths, top, severed) in expected.items():
            assert len(queries.find_attack_paths(g, crown_jewel_id=jewel)) == n_paths
            best = tools.choke_points(crown_jewel_id=jewel)[0]
            assert (best["finding_id"], best["paths_severed"]) == (top, severed)
        on_paths = {fid for j in expected for p in queries.find_attack_paths(g, crown_jewel_id=j)
                    for fid in p["finding_ids"]}
        assert "f:stg-cve" not in on_paths and "f:cms-upload" not in on_paths  # top CVSS, no path
    finally:
        graph.reset(g)
        tools._g = None
