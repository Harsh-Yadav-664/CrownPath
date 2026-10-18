"""graph.py — FalkorDB connection (reads credentials from the environment / .env).

Phase-1 scope: connect() + a thin run() so scripts/ping.py can verify the dev
database (FalkorDB Cloud). Issue B1 (#11) extends this module with init_schema(),
reset(), and id indexes; it must keep connect() reading the same env vars.

Env vars (see .env.example), loaded from a local .env if python-dotenv is present:
  FALKORDB_HOST, FALKORDB_PORT, FALKORDB_USERNAME, FALKORDB_PASSWORD
  FALKORDB_SSL      "true"/"false" (Cloud = true; local Docker = false)
  CROWNPATH_GRAPH   graph name (default "crownpath")
"""
import os

try:  # optional: load .env for local dev. Never required in production (host env vars).
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from falkordb import FalkorDB

from lib import schema


def _as_bool(val, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def graph_name():
    return os.environ.get("CROWNPATH_GRAPH", "crownpath")


def connect(ssl=None, connect_timeout=15):
    """Connect using FALKORDB_* env vars and return the selected graph handle.

    `ssl` overrides FALKORDB_SSL when given (used by the ping probe to try both).
    `connect_timeout` bounds the TCP/TLS handshake so a bad host fails fast instead
    of hanging. Raises a clear error if FALKORDB_HOST is missing so misconfiguration
    fails loudly rather than silently hitting localhost."""
    host = os.environ.get("FALKORDB_HOST")
    if not host:
        raise RuntimeError(
            "FALKORDB_HOST is not set. Copy .env.example to .env and fill in the "
            "FalkorDB Cloud (or local Docker) connection values."
        )
    port = int(os.environ.get("FALKORDB_PORT", "6379"))
    username = os.environ.get("FALKORDB_USERNAME") or None
    password = os.environ.get("FALKORDB_PASSWORD") or None
    use_ssl = _as_bool(os.environ.get("FALKORDB_SSL"), default=False) if ssl is None else ssl

    db = FalkorDB(
        host=host, port=port, username=username, password=password, ssl=use_ssl,
        socket_connect_timeout=connect_timeout, socket_timeout=connect_timeout,
    )
    return db.select_graph(graph_name())


def run(g, cypher, params=None):
    """Thin wrapper over g.query so every caller goes through one place."""
    return g.query(cypher, params or {})


def init_schema(g):
    """Create a range index on id for every node label in schema.INDEXED.

    Uses `CREATE INDEX FOR (n:Label) ON (n.id)` (verified syntax, BUILD_SPEC §7).
    FalkorDB has no documented `IF NOT EXISTS`, so each create is wrapped and an
    'already indexed' error is swallowed. Idempotent: safe to call twice."""
    for label, prop in schema.INDEXED:
        try:
            run(g, f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
        except Exception as exc:
            msg = str(exc).lower()
            if "already indexed" in msg or "already exists" in msg:
                continue
            raise


def reset(g):
    """Delete all nodes/edges in the graph. Does NOT drop indexes."""
    run(g, "MATCH (n) DETACH DELETE n")
