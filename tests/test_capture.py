"""tests/test_capture.py -- issue #24: loopback capture. Guards refuse non-loopback
targets (Rule 6); a real run validates against the schema and ingests through the
normal pipeline into at least one entry -> crown-jewel path."""
import json
import os
import subprocess
import sys

import pytest

from data import capture_findings, demo_target


def test_target_refuses_non_loopback_hosts():
    for host in ("0.0.0.0", "8.8.8.8", "example.com"):
        with pytest.raises(ValueError):
            demo_target.serve(host)


def test_capture_refuses_non_loopback_url():
    with pytest.raises(SystemExit):
        capture_findings.assert_loopback_url("http://example.com/")
    with pytest.raises(SystemExit):
        capture_findings.assert_loopback_url("http://203.0.113.9:8080")
    capture_findings.assert_loopback_url("http://127.0.0.1:8081")


def test_capture_cli_refuses_remote_target(tmp_path):
    result = subprocess.run(
        [sys.executable, "data/capture_findings.py", "--target", "http://example.com",
         "--out", str(tmp_path / "x.json")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "non-loopback" in result.stderr


def test_real_capture_is_schema_valid_and_confirms_findings(tmp_path):
    out = tmp_path / "captured.json"
    subprocess.run([sys.executable, "data/capture_findings.py", "--out", str(out)], check=True)
    doc = json.loads(out.read_text(encoding="utf-8"))
    status = {f["id"]: f["status"] for f in doc["findings"]}
    assert status == {"f:lab-xss": "confirmed", "f:lab-redirect": "confirmed",
                      "f:lab-git": "confirmed", "f:lab-sqli": "confirmed"}


def test_captured_file_ingests_and_yields_a_path(tmp_path):
    from lib import graph, queries, seed_taxonomy  # importing lib.graph loads .env

    if not os.environ.get("FALKORDB_HOST"):
        pytest.skip("FALKORDB_HOST not set; skipping live-DB test")

    out = tmp_path / "captured.json"
    subprocess.run([sys.executable, "data/capture_findings.py", "--out", str(out)], check=True)
    g = graph.connect()
    try:
        seed_taxonomy.load_all(g, str(out))
        paths = queries.find_attack_paths(g, crown_jewel_id="asset:lab-db")
        assert len(paths) >= 1
        assert any("f:lab-sqli" in p["finding_ids"] for p in paths)
    finally:
        graph.reset(g)
