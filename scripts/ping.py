"""ping.py — verify the FalkorDB connection with a trivial query.

Usage:  python scripts/ping.py
Reads connection settings from the environment / .env via lib.graph.
Tries the configured FALKORDB_SSL first; if that fails, probes the other mode and
tells you which one worked (so .env can be set correctly). Never prints the password.
Exits 0 on success, non-zero on failure.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import graph


def _try(ssl):
    g = graph.connect(ssl=ssl, connect_timeout=15)
    res = graph.run(g, "RETURN 1 AS ok")
    assert res.result_set and res.result_set[0][0] == 1, res.result_set
    graph.run(g, "CREATE (:Ping {ok:1})")
    cnt = graph.run(g, "MATCH (p:Ping) RETURN count(p)").result_set[0][0]
    graph.run(g, "MATCH (p:Ping) DELETE p")
    return cnt


def main():
    host = os.environ.get("FALKORDB_HOST", "<unset>")
    name = graph.graph_name()
    configured = graph._as_bool(os.environ.get("FALKORDB_SSL"), default=False)
    print(f"connecting to {host} (graph '{name}') ...", flush=True)
    order = [configured, not configured]
    last_err = None
    for ssl in order:
        try:
            print(f"  attempt ssl={ssl} ...", flush=True)
            cnt = _try(ssl)
            print(f"  OK with ssl={ssl}; probe round-trip count={cnt} (cleaned up)", flush=True)
            if ssl != configured:
                print(f"  NOTE: set FALKORDB_SSL={'true' if ssl else 'false'} in .env", flush=True)
            print("PING OK", flush=True)
            return 0
        except Exception as e:  # noqa: BLE001 — report and try the other mode
            last_err = e
            print(f"  failed ssl={ssl}: {type(e).__name__}: {e}", flush=True)
    print(f"PING FAILED: {type(last_err).__name__}: {last_err}", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
