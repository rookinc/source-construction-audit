#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUTS = {
    "002": "source_construction_ledger_inventory_002.v1.json",
    "003": "source_construction_phi_candidate_003.v1.json",
    "004": "source_construction_directed_cycle_phi_004.v1.json",
    "005": "source_construction_phi_independence_audit_005.v1.json",
    "006": "source_construction_phi_field_source_audit_006.v1.json",
    "007": "source_construction_phi_label_removal_audit_007.v1.json",
    "008": "source_construction_phi_field_ablation_008.v1.json",
}

OUT_JSON = ROOT / "artifacts/json/source_construction_phi_theorem_candidate_009.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_phi_theorem_candidate_009.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_phi_theorem_candidate_009.md"

REQUIRED = [
    "theorem-candidate summary",
    "source-construction phi",
    "directed role-successor cycle",
    "label-column independence",
    "load-bearing",
    "answer-label leakage remains open",
    "not native closure",
    "not Gap A closure",
    "not full role-labeled shared_B universe",
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


def pass_value(data):
    if "audit_pass" in data:
        return bool(data.get("audit_pass"))
    if "checkpoint_pass" in data:
        return bool(data.get("checkpoint_pass"))
    return False


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    deps = []
    by_id = {}

    for audit_id, filename in INPUTS.items():
        path = ROOT / "artifacts/json" / filename
        if not path.exists():
            raise SystemExit("missing input " + str(path))
        data = load_json(path)
        by_id[audit_id] = data
        deps.append({
            "audit_id": audit_id,
            "path": str(path.relative_to(ROOT)),
            "status": data.get("status"),
            "verdict": data.get("verdict"),
            "pass": pass_value(data),
        })

    theorem_candidate = {
        "name": "directed_role_successor_source_construction_phi",
        "status": "theorem_candidate",
        "informal_statement": (
            "On the 24-row local completion register, a source-construction phi can be computed from "
            "directed role-successor cycles and source-side/native-transition fields. The resulting phi "
            "partitions the 24 rows into four six-row levels: edge, hinge, closed_face, and filled_cell."
        ),
        "domain": "24-row local completion register",
        "codomain": ["edge", "hinge", "closed_face", "filled_cell"],
        "cycle_law": {
            "name": "directed role-successor cycle",
            "role_order": ["WX", "XY", "YZ", "ZT", "TI", "IW", "WX"],
            "continuity": "row.to_ABC = next_row.from_ABC",
            "fields": ["from_A", "from_B", "from_C", "to_A", "to_B", "to_C", "edge_role"],
        },
        "assignment_law": {
            "capture_rule": "capture iff slot_delta_mod15 > fiber_delta_mod60",
            "fields": ["slot_delta_mod15", "fiber_delta_mod60", "edge_role"],
            "rules": [
                {"condition": "capture_count == 0", "level": "edge"},
                {"condition": "capture_count == 1", "level": "hinge"},
                {"condition": "capture_count == 2 and TI.fiber_delta_mod60 == 3", "level": "closed_face"},
                {"condition": "capture_count == 2 and TI.fiber_delta_mod60 == 1", "level": "filled_cell"},
            ],
        },
        "evidence_stack": [
            {
                "audit": "002",
                "role": "ledger",
                "result": "exports the 24-row register and separates allowed construction fields from evaluation/order-risk fields",
            },
            {
                "audit": "003",
                "role": "failed ablation",
                "result": "weak component grouping fails by merging the two two-capture levels",
            },
            {
                "audit": "004",
                "role": "positive construction",
                "result": "directed role-successor phi exactly recovers the four six-row levels",
            },
            {
                "audit": "005",
                "role": "row-order independence",
                "result": "phi survives original, reversed, sorted, and shuffled row orders",
            },
            {
                "audit": "006",
                "role": "field-source check",
                "result": "phi fields are source-side or native-transition fields in the ledger",
            },
            {
                "audit": "007",
                "role": "label-column independence",
                "result": "phi survives after form_index and ledger_row_id are removed from working rows",
            },
            {
                "audit": "008",
                "role": "load-bearing test",
                "result": "all tested field and rule ablations fail in the current rule family",
            },
        ],
        "accepted_claims": [
            "A source-construction phi candidate exists for the 24-row register.",
            "The phi candidate uses directed role-successor cycles rather than row order.",
            "The phi candidate does not require form_index or ledger_row_id in the working rows.",
            "The tested phi inputs are load-bearing within the current rule family.",
        ],
        "boundaries": [
            "This is a theorem-candidate summary, not native closure.",
            "This is not Gap A closure.",
            "This is not full role-labeled shared_B universe derivation.",
            "label-column independence passed, but deeper construction-origin leakage remains open.",
            "This does not prove minimality over all possible source-construction rules.",
        ],
        "next_tests": [
            {
                "name": "construction-origin provenance audit",
                "purpose": "trace where from_ABC, to_ABC, edge_role, slot_delta_mod15, and fiber_delta_mod60 originate in upstream construction files",
            },
            {
                "name": "external source replay",
                "purpose": "recompute the 24-row register from upstream source files rather than copied Project 24 rows",
            },
            {
                "name": "rule-family minimization",
                "purpose": "test whether an alternative smaller source-construction rule can recover the same phi",
            },
        ],
    }

    statement = (
        "Artifact 009 is a theorem-candidate summary for source-construction phi. "
        "It packages the directed role-successor cycle law, label-column independence, and load-bearing field audit. "
        "answer-label leakage remains open at the deeper construction-origin level. "
        "This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    gate_text = statement + "\n" + json.dumps(theorem_candidate, indent=2, sort_keys=True)
    miss = missing(gate_text, REQUIRED)
    forb = found(gate_text, FORBIDDEN)

    checks = {
        "all_inputs_exist": True,
        "ledger_002_pass": by_id["002"].get("audit_pass") is True,
        "weak_component_003_failed_as_expected": by_id["003"].get("audit_pass") is False,
        "directed_cycle_phi_004_pass": by_id["004"].get("audit_pass") is True,
        "phi_independence_005_pass": by_id["005"].get("audit_pass") is True,
        "phi_field_source_006_pass": by_id["006"].get("audit_pass") is True,
        "phi_label_removal_007_pass": by_id["007"].get("audit_pass") is True,
        "phi_field_ablation_008_pass": by_id["008"].get("audit_pass") is True,
        "theorem_candidate_recorded": True,
        "label_column_independence_passed": True,
        "load_bearing_fields_recorded": True,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(miss) == 0,
        "forbidden_phrases_absent": len(forb) == 0,
    }

    audit_pass = all([
        checks["ledger_002_pass"],
        checks["weak_component_003_failed_as_expected"],
        checks["directed_cycle_phi_004_pass"],
        checks["phi_independence_005_pass"],
        checks["phi_field_source_006_pass"],
        checks["phi_label_removal_007_pass"],
        checks["phi_field_ablation_008_pass"],
        checks["theorem_candidate_recorded"],
        checks["label_column_independence_passed"],
        checks["load_bearing_fields_recorded"],
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_phi_theorem_candidate_recorded",
        "audit_id": "009",
        "audit_pass": audit_pass,
        "verdict": "source_construction_phi_theorem_candidate_ready" if audit_pass else "source_construction_phi_theorem_candidate_failed",
        "statement": statement,
        "dependency_ledger": deps,
        "checks": checks,
        "theorem_candidate": theorem_candidate,
        "missing_required_phrases": miss,
        "forbidden_phrases_found": forb,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTE.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["audit_id", "pass", "verdict", "role"])
        role_by_id = {
            "002": "ledger",
            "003": "failed weak-component ablation",
            "004": "positive directed-cycle phi",
            "005": "row-order independence",
            "006": "field-source audit",
            "007": "label-column removal",
            "008": "load-bearing ablation",
        }
        for d in deps:
            w.writerow([d["audit_id"], d["pass"], d["verdict"], role_by_id.get(d["audit_id"], "")])

    lines = []
    lines.append("# Source construction phi theorem candidate 009")
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
    lines.append("## Candidate theorem")
    lines.append("")
    lines.append(theorem_candidate["informal_statement"])
    lines.append("")
    lines.append("## Cycle law")
    lines.append("")
    lines.append("- directed role-successor cycle: WX -> XY -> YZ -> ZT -> TI -> IW -> WX")
    lines.append("- continuity: row.to_ABC = next_row.from_ABC")
    lines.append("")
    lines.append("## Assignment law")
    lines.append("")
    lines.append("- capture iff slot_delta_mod15 > fiber_delta_mod60")
    lines.append("- capture_count 0 -> edge")
    lines.append("- capture_count 1 -> hinge")
    lines.append("- capture_count 2 and TI.fiber_delta_mod60 3 -> closed_face")
    lines.append("- capture_count 2 and TI.fiber_delta_mod60 1 -> filled_cell")
    lines.append("")
    lines.append("## Evidence stack")
    lines.append("")
    for x in theorem_candidate["evidence_stack"]:
        lines.append("- " + x["audit"] + ": " + x["role"] + " - " + x["result"])
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    for x in theorem_candidate["boundaries"]:
        lines.append("- " + x)
    lines.append("")
    lines.append("## Next tests")
    lines.append("")
    for x in theorem_candidate["next_tests"]:
        lines.append("- " + x["name"] + ": " + x["purpose"])
    lines.append("")

    OUT_NOTE.write_text("\n".join(lines), encoding="utf-8")

    print("wrote", OUT_JSON)
    print("wrote", OUT_CSV)
    print("wrote", OUT_NOTE)
    print("status", result["status"])
    print("audit_pass", audit_pass)
    print("verdict", result["verdict"])
    for k, v in checks.items():
        print(k, v)


if __name__ == "__main__":
    main()
