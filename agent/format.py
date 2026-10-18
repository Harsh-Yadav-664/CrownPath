"""agent/format.py — output formatter (BUILD_SPEC.md §2/§8, issue #19 / C3).
Renders the ranked, path-cited remediation list + the choke-point headline.
Shared by the LLM path and the --no-llm path (agent/run.py, issue #18).
"""
import json
import os

REMEDIATION_TSV_PATH = os.path.join("data", "taxonomy", "remediation.tsv")
FINDINGS_PATH = os.path.join("data", "findings.json")


def _load_remediation_map(path=REMEDIATION_TSV_PATH):
    """{class_slug: remediation text} from the lifted remediation.tsv (#14).
    Comment lines (starting with '#') are skipped."""
    remediation = {}
    if not os.path.exists(path):
        return remediation
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                remediation[parts[0]] = parts[1]
    return remediation


def _load_finding_technique_map(path=FINDINGS_PATH):
    """{finding_id: technique_id} read from the findings document (the technique_id
    is the taxonomy class slug remediation.tsv is keyed by)."""
    mapping = {}
    if not os.path.exists(path):
        return mapping
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for finding in data.get("findings", []):
        mapping[finding["id"]] = finding.get("technique_id")
    return mapping


def _arrow_chain_with_edges(cited_path):
    """Render steps as `node -> (edge) -> node -> ...`, matching the format in the
    issue: `ep:search -> (XSS) -> user session -> Orders API -> /api/orders -> (IDOR) -> Customer database`."""
    parts = []
    for step in cited_path["steps"]:
        if step["kind"] == "node":
            parts.append(step["id"] or step["display"])
        else:
            parts.append(f"({step['label']})")
    return " -> ".join(parts)


def format_answer(remediations, chokepoints):
    """format_answer(remediations: list[Remediation], chokepoints: list[ChokePoint]) -> str"""
    remediation_map = _load_remediation_map()
    technique_map = _load_finding_technique_map()

    lines = ["## What to fix first", ""]
    for rem in remediations:
        lines.append(f"{rem['rank']}. **{rem['title']}** -- {rem['reason']}")
        lines.append(f"   Path: {_arrow_chain_with_edges(rem['cited_path'])}")

        technique_id = technique_map.get(rem["finding_id"])
        fix_text = remediation_map.get(technique_id) if technique_id else None
        if fix_text:
            lines.append(f"   {fix_text}")
        lines.append("")

    lines.append("## Choke point")
    if chokepoints:
        top = chokepoints[0]
        jewel_name = None
        if remediations:
            jewel_display = remediations[0]["cited_path"]["steps"][-1]["display"]
            jewel_name = jewel_display.split(": ", 1)[-1]
        jewel_name = jewel_name or "the crown jewel"

        headline = (
            f"Fix **{top['title']}** -> severs **{top['paths_severed']} of "
            f"{top['paths_total']}** paths to {jewel_name}"
        )
        if top.get("severs_highest_value"):
            headline += ", including the highest-value one."
        else:
            headline += "."
        lines.append(headline)
    else:
        lines.append("No choke-point data available.")

    return "\n".join(lines)
