"""schema.py — frozen CrownPath graph schema (BUILD_SPEC.md §6). Single source of truth."""

GRAPH_NAME = "crownpath"

# ---- node labels
NODE_LABELS = ["Asset", "Endpoint", "Finding", "Technique", "Identity"]

# ---- property enums (closed vocabularies)
ASSET_TYPES = ["host", "service", "webapp", "database"]
VULN_TYPES = ["xss", "sqli", "idor", "ssrf", "ssti", "lfi", "open_redirect",
              "csrf", "cors", "path_traversal", "rce", "info_disclosure",
              "auth_bypass", "mass_assignment", "deserialization", "file_upload"]
FINDING_STATUS = ["confirmed", "inconclusive", "refuted"]  # only 'confirmed' gets attack edges
TECHNIQUE_CAPABILITIES = ["session_theft", "rce", "data_read", "data_write",
                          "priv_esc", "auth_bypass", "ssrf_pivot"]
# identity privilege levels (role -> int)
PRIVILEGE = {"anonymous": 0, "user": 1, "admin": 3}

# ---- node property schemas: label -> {prop: (python_type, required_bool)}
NODE_PROPS = {
    "Asset":     {"id": (str, True), "name": (str, True), "type": (str, True),
                  "environment": (str, False), "is_crown_jewel": (bool, True), "value": (int, True)},
    "Endpoint":  {"id": (str, True), "url": (str, True), "method": (str, True),
                  "auth_required": (bool, True)},
    "Finding":   {"id": (str, True), "title": (str, True), "vuln_type": (str, True),
                  "cwe": (str, False), "cvss": (float, False), "confidence": (float, True),
                  "status": (str, True), "discovered_at": (str, False), "evidence": (str, False)},
    "Technique": {"id": (str, True), "name": (str, True), "cwe": (str, False),
                  "capability": (str, True)},
    "Identity":  {"id": (str, True), "role": (str, True), "privilege_level": (int, True)},
}

# ---- relationship types: (src_label, REL, dst_label)
EDGES = [
    ("Asset",     "EXPOSES",     "Endpoint"),
    ("Endpoint",  "HAS_FINDING", "Finding"),
    ("Finding",   "INSTANCE_OF", "Technique"),
    ("Finding",   "GRANTS",      "Identity"),
    ("Finding",   "LEADS_TO",    "Asset"),
    ("Technique", "CHAINS_TO",   "Technique"),
    ("Asset",     "CONNECTS_TO", "Asset"),
    ("Identity",  "CAN_ACCESS",  "Asset"),
]
REL_TYPES = sorted({r for _, r, _ in EDGES})

# edge set used by the attack-path traversal (query 7a), in order.
# NOTE (design decision locked by issue #10 spike, already made — do not second-guess):
# EXPOSES (Asset->Endpoint) IS included so a path that reaches an Asset can descend into
# that asset's Endpoints and their interior Findings (e.g. an IDOR on an internal
# authenticated endpoint). Without it, only the entry endpoint's finding could ever appear
# on a path and multi-finding chains would be impossible. INSTANCE_OF and CHAINS_TO are
# EXCLUDED from traversal (Technique nodes never reach an Asset; they are used for
# explanation, not reachability).
ATTACK_EDGES = ["EXPOSES", "HAS_FINDING", "LEADS_TO", "GRANTS", "CAN_ACCESS", "CONNECTS_TO"]

# properties that must be indexed (id on every label) — created by lib/graph.py (B1)
INDEXED = [(label, "id") for label in NODE_LABELS]


def validate_node(label, props):
    """Return a list of problem strings for (label, props); [] when valid."""
    problems = []

    if label not in NODE_PROPS:
        problems.append(f"unknown label: {label!r}")
        return problems

    schema = NODE_PROPS[label]

    for prop, (py_type, required) in schema.items():
        if prop not in props:
            if required:
                problems.append(f"{label}: missing required prop '{prop}'")
            continue
        value = props[prop]
        if py_type is bool:
            if not isinstance(value, bool):
                problems.append(
                    f"{label}.{prop}: expected bool, got {type(value).__name__}"
                )
        elif py_type is float:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                problems.append(
                    f"{label}.{prop}: expected float, got {type(value).__name__}"
                )
        elif py_type is int:
            if not isinstance(value, int) or isinstance(value, bool):
                problems.append(
                    f"{label}.{prop}: expected int, got {type(value).__name__}"
                )
        elif py_type is str:
            if not isinstance(value, str):
                problems.append(
                    f"{label}.{prop}: expected str, got {type(value).__name__}"
                )

    # closed-vocabulary enum checks
    enum_checks = {
        ("Asset", "type"): ASSET_TYPES,
        ("Finding", "vuln_type"): VULN_TYPES,
        ("Finding", "status"): FINDING_STATUS,
        ("Technique", "capability"): TECHNIQUE_CAPABILITIES,
        ("Identity", "role"): list(PRIVILEGE.keys()),
    }
    for (chk_label, chk_prop), allowed in enum_checks.items():
        if label == chk_label and chk_prop in props:
            if props[chk_prop] not in allowed:
                problems.append(
                    f"{label}.{chk_prop}: {props[chk_prop]!r} not in {allowed}"
                )

    return problems
