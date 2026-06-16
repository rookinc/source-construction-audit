#!/usr/bin/env python3
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
P24 = PARENT / "24-native-local-cell-provenance"

SRC_HANDOFF = P24 / "artifacts/json/local_completion_grammar_handoff_070.v1.json"
SRC_EDGE_RECORDS = P24 / "source/upstream_station_provenance/18-g900-kernel-admission/artifacts/json/g60_native_overlay_generator_family_search_001.v1.json"

OUT_HANDOFF = ROOT / "source/project24/local_completion_grammar_handoff_070.v1.json"
OUT_EDGE_RECORDS = ROOT / "source/project24/g60_native_overlay_generator_family_search_001.v1.json"
OUT_JSON = ROOT / "artifacts/json/project25_seed_from_project24_handoff_001.v1.json"
OUT_NOTE = ROOT / "notes/project25_seed_from_project24_handoff_001.md"

REQUIRED = [
    "source construction audit",
    "Project 24 handoff",
    "local completion grammar",
    "native four-form partition",
    "answer-label leakage remains open",
    "not native closure",
    "not Gap A closure",
]

FORBIDDEN = [
    "Gap A is closed",
    "native closure achieved",
    "answer-label leakage ruled out",
    "completion ladder proven natively",
    "full shared_B universe derived",
    "cosmology is derived",
    "ontology is proven",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    if not SRC_HANDOFF.exists():
        raise SystemExit("missing Project 24 handoff: " + str(SRC_HANDOFF))
    if not SRC_EDGE_RECORDS.exists():
        raise SystemExit("missing Project 24 edge records source: " + str(SRC_EDGE_RECORDS))

    handoff = load_json(SRC_HANDOFF)
    grammar = handoff.get("grammar", {})

    OUT_HANDOFF.parent.mkdir(parents=True, exist_ok=True)
    OUT_EDGE_RECORDS.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTE.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SRC_HANDOFF, OUT_HANDOFF)
    shutil.copy2(SRC_EDGE_RECORDS, OUT_EDGE_RECORDS)

    statement = (
        "Artifact 001 seeds the Project 25 source construction audit from the Project 24 handoff. "
        "The imported local completion grammar defines the starting boundary: the native four-form partition remains open, "
        "answer-label leakage remains open, this is not native closure, and this is not Gap A closure."
    )

    target = {
        "project": "25-source-construction-audit",
        "status": "seeded_from_project24_handoff",
        "primary_question": "What source-construction law groups the 24 edge records into four six-row forms?",
        "primary_target": "source construction provenance -> native four-form partition candidate",
        "starting_boundary": {
            "native_four_form_partition_proven": False,
            "answer_label_leakage_resolved": False,
            "native_closure": False,
            "gap_a_closure": False,
        },
        "imported_sources": {
            "project24_handoff": str(OUT_HANDOFF.relative_to(ROOT)),
            "g60_native_overlay_edge_records": str(OUT_EDGE_RECORDS.relative_to(ROOT)),
        },
        "inherited_grammar_axes": grammar.get("grammar_axes", {}),
        "inherited_open_frontiers": grammar.get("open_frontiers", []),
        "next_audit_recommendation": {
            "id": "002",
            "name": "source construction ledger inventory",
            "purpose": "Inspect construction provenance fields and separate source fields from labels, order fields, and downstream answer fields.",
        },
    }

    gate_text = statement + "\n" + json.dumps(target, indent=2, sort_keys=True)
    missing_required = missing(gate_text, REQUIRED)
    forbidden_found = found(gate_text, FORBIDDEN)

    checks = {
        "project24_handoff_exists": SRC_HANDOFF.exists(),
        "edge_records_source_exists": SRC_EDGE_RECORDS.exists(),
        "handoff_imported": OUT_HANDOFF.exists(),
        "edge_records_imported": OUT_EDGE_RECORDS.exists(),
        "handoff_audit_pass": bool(handoff.get("audit_pass")),
        "required_phrases_present": len(missing_required) == 0,
        "forbidden_phrases_absent": len(forbidden_found) == 0,
    }

    audit_pass = all(checks.values())

    result = {
        "status": "project25_seed_from_project24_handoff_recorded",
        "audit_id": "001",
        "audit_pass": audit_pass,
        "verdict": "project25_seed_ready" if audit_pass else "project25_seed_phrase_gate_failed",
        "statement": statement,
        "checks": checks,
        "target": target,
        "missing_required_phrases": missing_required,
        "forbidden_phrases_found": forbidden_found,
    }

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = []
    lines.append("# Project 25 seed from Project 24 handoff 001")
    lines.append("")
    lines.append("Status: " + result["status"])
    lines.append("")
    lines.append("## Result")
    lines.append("")
    lines.append("- audit_pass: `" + str(audit_pass) + "`")
    lines.append("- verdict: `" + result["verdict"] + "`")
    for k, v in checks.items():
        lines.append("- " + k + ": `" + str(v) + "`")
    lines.append("")
    lines.append("## Statement")
    lines.append("")
    lines.append(statement)
    lines.append("")
    lines.append("## Primary question")
    lines.append("")
    lines.append(target["primary_question"])
    lines.append("")
    lines.append("## Imported sources")
    lines.append("")
    for k, v in target["imported_sources"].items():
        lines.append("- " + k + ": `" + v + "`")
    lines.append("")
    lines.append("## Next audit")
    lines.append("")
    lines.append("- " + target["next_audit_recommendation"]["name"] + ": " + target["next_audit_recommendation"]["purpose"])
    lines.append("")

    OUT_NOTE.write_text("\n".join(lines), encoding="utf-8")

    print("wrote", OUT_JSON)
    print("wrote", OUT_NOTE)
    print("copied", OUT_HANDOFF)
    print("copied", OUT_EDGE_RECORDS)
    print("status", result["status"])
    print("audit_pass", audit_pass)
    print("verdict", result["verdict"])
    for k, v in checks.items():
        print(k, v)


if __name__ == "__main__":
    main()
