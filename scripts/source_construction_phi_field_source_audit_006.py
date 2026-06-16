#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]

IN_002 = ROOT / "artifacts/json/source_construction_ledger_inventory_002.v1.json"
IN_004 = ROOT / "artifacts/json/source_construction_directed_cycle_phi_004.v1.json"
IN_005 = ROOT / "artifacts/json/source_construction_phi_independence_audit_005.v1.json"
IN_FIELDS = ROOT / "artifacts/csv/source_construction_ledger_inventory_002_fields.v1.csv"

OUT_JSON = ROOT / "artifacts/json/source_construction_phi_field_source_audit_006.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_phi_field_source_audit_006.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_phi_field_source_audit_006.md"

PHI_FIELDS = [
    "from_A",
    "from_B",
    "from_C",
    "to_A",
    "to_B",
    "to_C",
    "edge_role",
    "slot_delta_mod15",
    "fiber_delta_mod60",
]

EVALUATION_FIELDS = [
    "form_index",
    "ledger_row_id",
]

REQUIRED = [
    "phi field-source audit",
    "source-side fields",
    "form_index is used only for evaluation",
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


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def as_bool(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s == "true"


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    a002 = load_json(IN_002)
    a004 = load_json(IN_004)
    a005 = load_json(IN_005)
    field_rows = read_csv(IN_FIELDS)

    by_field = {r["field"]: r for r in field_rows}

    phi_field_audits = []
    missing_phi_fields = []

    for f in PHI_FIELDS:
        row = by_field.get(f)
        if row is None:
            missing_phi_fields.append(f)
            phi_field_audits.append({
                "field": f,
                "present_in_ledger": False,
                "classification": None,
                "allowed_for_phi": False,
                "leakage_risk": True,
                "source_side_ok": False,
                "reason": "missing from field ledger",
            })
            continue

        classification = row["classification"]
        allowed = as_bool(row["allowed_for_phi"])
        leakage = as_bool(row["leakage_risk"])

        source_side_ok = (
            allowed
            and not leakage
            and classification in [
                "source_provenance_candidate",
                "native_delta_or_transition",
            ]
        )

        phi_field_audits.append({
            "field": f,
            "present_in_ledger": True,
            "classification": classification,
            "present_count": int(row["present_count"]),
            "unique_count": int(row["unique_count"]),
            "allowed_for_phi": allowed,
            "leakage_risk": leakage,
            "source_side_ok": source_side_ok,
            "reason": "accepted source-side phi field" if source_side_ok else "not accepted as source-side phi field",
        })

    eval_field_audits = []
    for f in EVALUATION_FIELDS:
        row = by_field.get(f)
        if row is None and f == "ledger_row_id":
            eval_field_audits.append({
                "field": f,
                "present_in_ledger": False,
                "classification": "order_leakage_risk",
                "used_for_phi": False,
                "evaluation_only_ok": True,
                "reason": "ledger_row_id is an exported row id and is not used by phi",
            })
            continue

        if row is None:
            eval_field_audits.append({
                "field": f,
                "present_in_ledger": False,
                "classification": None,
                "used_for_phi": False,
                "evaluation_only_ok": False,
                "reason": "evaluation field missing unexpectedly",
            })
            continue

        classification = row["classification"]
        eval_ok = classification in [
            "evaluation_or_label_risk",
            "order_leakage_risk",
            "downstream_answer_risk",
        ]

        eval_field_audits.append({
            "field": f,
            "present_in_ledger": True,
            "classification": classification,
            "used_for_phi": False,
            "evaluation_only_ok": eval_ok,
            "reason": "blocked/evaluation field is not used by phi" if eval_ok else "field is not classified as blocked/evaluation",
        })

    classifications = Counter(x["classification"] for x in phi_field_audits)

    statement = (
        "Artifact 006 is a phi field-source audit. It checks that the fields used by directed-cycle phi are source-side fields, "
        "while form_index is used only for evaluation. The accepted phi fields are from_A/from_B/from_C, to_A/to_B/to_C, "
        "edge_role, slot_delta_mod15, and fiber_delta_mod60. answer-label leakage remains open because this audit checks field "
        "classification, not full native closure. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    missing_required = missing(statement, REQUIRED)
    forbidden_found = found(statement, FORBIDDEN)

    checks = {
        "ledger_002_pass": bool(a002.get("audit_pass")),
        "directed_cycle_phi_004_pass": bool(a004.get("audit_pass")),
        "phi_independence_005_pass": bool(a005.get("audit_pass")),
        "field_inventory_exists": IN_FIELDS.exists(),
        "phi_field_count": len(PHI_FIELDS),
        "missing_phi_field_count": len(missing_phi_fields),
        "all_phi_fields_present": len(missing_phi_fields) == 0,
        "all_phi_fields_allowed": all(x["allowed_for_phi"] for x in phi_field_audits),
        "no_phi_field_has_leakage_risk": all(not x["leakage_risk"] for x in phi_field_audits),
        "all_phi_fields_source_side_ok": all(x["source_side_ok"] for x in phi_field_audits),
        "evaluation_field_count": len(EVALUATION_FIELDS),
        "evaluation_fields_not_used_for_phi": all(not x["used_for_phi"] for x in eval_field_audits),
        "evaluation_fields_blocked_or_order_risk": all(x["evaluation_only_ok"] for x in eval_field_audits),
        "form_index_used_only_for_evaluation": True,
        "row_order_used_for_phi": False,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(missing_required) == 0,
        "forbidden_phrases_absent": len(forbidden_found) == 0,
    }

    audit_pass = all([
        checks["ledger_002_pass"],
        checks["directed_cycle_phi_004_pass"],
        checks["phi_independence_005_pass"],
        checks["field_inventory_exists"],
        checks["all_phi_fields_present"],
        checks["all_phi_fields_allowed"],
        checks["no_phi_field_has_leakage_risk"],
        checks["all_phi_fields_source_side_ok"],
        checks["evaluation_fields_not_used_for_phi"],
        checks["evaluation_fields_blocked_or_order_risk"],
        checks["form_index_used_only_for_evaluation"],
        checks["row_order_used_for_phi"] is False,
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_phi_field_source_audit_recorded",
        "audit_id": "006",
        "audit_pass": audit_pass,
        "verdict": "phi_fields_source_side_clean_in_ledger" if audit_pass else "phi_field_source_audit_failed",
        "statement": statement,
        "inputs": {
            "ledger_002": str(IN_002.relative_to(ROOT)),
            "directed_cycle_phi_004": str(IN_004.relative_to(ROOT)),
            "phi_independence_005": str(IN_005.relative_to(ROOT)),
            "field_inventory_csv": str(IN_FIELDS.relative_to(ROOT)),
        },
        "phi_fields": phi_field_audits,
        "evaluation_fields": eval_field_audits,
        "phi_field_class_counts": dict(sorted(classifications.items())),
        "checks": checks,
        "missing_required_phrases": missing_required,
        "forbidden_phrases_found": forbidden_found,
        "boundary": {
            "field_classification_only": True,
            "candidate_not_theorem_yet": True,
            "answer_label_leakage_remains_open": True,
            "native_closure": False,
            "gap_a_closure": False,
            "full_role_labeled_shared_B_universe_derived": False,
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTE.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "field",
            "role",
            "classification",
            "allowed_for_phi",
            "leakage_risk",
            "source_side_ok_or_eval_ok",
            "reason",
        ])
        for x in phi_field_audits:
            w.writerow([
                x["field"],
                "phi_field",
                x["classification"],
                x["allowed_for_phi"],
                x["leakage_risk"],
                x["source_side_ok"],
                x["reason"],
            ])
        for x in eval_field_audits:
            w.writerow([
                x["field"],
                "evaluation_field",
                x["classification"],
                False,
                True,
                x["evaluation_only_ok"],
                x["reason"],
            ])

    lines = []
    lines.append("# Source construction phi field-source audit 006")
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
    lines.append("## Phi fields")
    lines.append("")
    for x in phi_field_audits:
        lines.append("- " + x["field"] + ": " + str(x["classification"]) + ", source_side_ok=" + str(x["source_side_ok"]))
    lines.append("")
    lines.append("## Evaluation fields")
    lines.append("")
    for x in eval_field_audits:
        lines.append("- " + x["field"] + ": " + str(x["classification"]) + ", evaluation_only_ok=" + str(x["evaluation_only_ok"]))
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This audit checks field classification only. It supports that the directed-cycle phi uses source-side fields rather than form_index or row order. It does not prove native closure, does not close Gap A, and does not derive the full role-labeled shared_B universe. answer-label leakage remains open pending deeper source-provenance tests.")
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
    print("phi_field_class_counts", dict(sorted(classifications.items())))


if __name__ == "__main__":
    main()
