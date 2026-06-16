#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

IN_LEDGER = ROOT / "artifacts/json/source_construction_ledger_inventory_002.v1.json"
IN_ROWS = ROOT / "artifacts/csv/source_construction_ledger_inventory_002_rows.v1.csv"

OUT_JSON = ROOT / "artifacts/json/source_construction_directed_cycle_phi_004.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_directed_cycle_phi_004_rows.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_directed_cycle_phi_004.md"

ROLE_ORDER = ["WX", "XY", "YZ", "ZT", "TI", "IW"]
NEXT_ROLE = {
    "WX": "XY",
    "XY": "YZ",
    "YZ": "ZT",
    "ZT": "TI",
    "TI": "IW",
    "IW": "WX",
}

LEVEL_TO_FORM = {
    "edge": 0,
    "hinge": 1,
    "closed_face": 2,
    "filled_cell": 3,
}

REQUIRED = [
    "directed role-successor cycle",
    "source-construction assignment",
    "phi",
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


def read_rows(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def as_int(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    if s.lstrip("-").isdigit():
        return int(s)
    return None


def node(row, prefix):
    return (
        as_int(row[prefix + "_A"]),
        as_int(row[prefix + "_B"]),
        as_int(row[prefix + "_C"]),
    )


def inside_captured_native(row):
    return as_int(row["slot_delta_mod15"]) > as_int(row["fiber_delta_mod60"])


def build_successors(rows):
    by_from_and_role = defaultdict(list)
    for i, row in enumerate(rows):
        by_from_and_role[(node(row, "from"), row["edge_role"])].append(i)

    successors = {}
    successor_ambiguities = []

    for i, row in enumerate(rows):
        target = node(row, "to")
        nr = NEXT_ROLE[row["edge_role"]]
        candidates = by_from_and_role[(target, nr)]
        if len(candidates) == 1:
            successors[i] = candidates[0]
        else:
            successors[i] = None
            successor_ambiguities.append({
                "row": as_int(row["ledger_row_id"]),
                "edge_role": row["edge_role"],
                "target_node": target,
                "next_role": nr,
                "candidate_rows": [as_int(rows[j]["ledger_row_id"]) for j in candidates],
            })

    return successors, successor_ambiguities


def cycles_from_successors(rows, successors):
    seen = set()
    cycles = []
    broken = []

    for start in range(len(rows)):
        if start in seen:
            continue

        local_seen = {}
        path = []
        cur = start

        while cur is not None and cur not in local_seen and cur not in seen:
            local_seen[cur] = len(path)
            path.append(cur)
            cur = successors.get(cur)

        if cur is None:
            broken.append([as_int(rows[i]["ledger_row_id"]) for i in path])
            seen.update(path)
            continue

        if cur in local_seen:
            cyc = path[local_seen[cur]:]
            cycles.append(cyc)
            seen.update(cyc)
            seen.update(path)
        else:
            seen.update(path)

    cycles.sort(key=lambda ids: min(as_int(rows[i]["ledger_row_id"]) for i in ids))
    return cycles, broken


def assign_phi(rows, ids):
    captures = [i for i in ids if inside_captured_native(rows[i])]
    ti_rows = [i for i in ids if rows[i]["edge_role"] == "TI"]

    ti_fiber = None
    if len(ti_rows) == 1:
        ti_fiber = as_int(rows[ti_rows[0]]["fiber_delta_mod60"])

    capture_count = len(captures)

    if capture_count == 0:
        level = "edge"
        reason = "capture_count=0"
    elif capture_count == 1:
        level = "hinge"
        reason = "capture_count=1"
    elif capture_count == 2 and ti_fiber == 3:
        level = "closed_face"
        reason = "capture_count=2 and TI.fiber_delta_mod60=3"
    elif capture_count == 2 and ti_fiber == 1:
        level = "filled_cell"
        reason = "capture_count=2 and TI.fiber_delta_mod60=1"
    else:
        level = "unknown"
        reason = "no rule matched"

    return {
        "phi_level": level,
        "reason": reason,
        "capture_count": capture_count,
        "capture_roles": [rows[i]["edge_role"] for i in captures],
        "capture_row_ids": [as_int(rows[i]["ledger_row_id"]) for i in captures],
        "ti_fiber_delta_mod60": ti_fiber,
    }


def role_counts(rows, ids):
    return dict(sorted(Counter(rows[i]["edge_role"] for i in ids).items()))


def form_counts(rows, ids):
    return dict(sorted(Counter(as_int(rows[i]["form_index"]) for i in ids).items()))


def cycle_role_order(rows, ids):
    return [rows[i]["edge_role"] for i in ids]


def cycle_is_role_successor_order(rows, ids):
    roles = cycle_role_order(rows, ids)
    if len(roles) != 6:
        return False
    return all(NEXT_ROLE[roles[i]] == roles[(i + 1) % len(roles)] for i in range(len(roles)))


def ids(rows, xs):
    return [as_int(rows[i]["ledger_row_id"]) for i in xs]


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    ledger = load_json(IN_LEDGER)
    rows = read_rows(IN_ROWS)

    if not ledger.get("audit_pass"):
        raise SystemExit("002 audit_pass is not true")

    successors, successor_ambiguities = build_successors(rows)
    cycles, broken_paths = cycles_from_successors(rows, successors)

    components = []
    row_assignment = {}

    for cid, cyc in enumerate(cycles):
        phi = assign_phi(rows, cyc)
        expected_form = LEVEL_TO_FORM.get(phi["phi_level"])
        forms = form_counts(rows, cyc)
        match = expected_form is not None and forms == {expected_form: len(cyc)}

        comp = {
            "component_id": cid,
            "source_row_ids": ids(rows, cyc),
            "edge_roles_in_directed_order": cycle_role_order(rows, cyc),
            "row_count": len(cyc),
            "role_counts": role_counts(rows, cyc),
            "has_all_six_roles_once": role_counts(rows, cyc) == {r: 1 for r in ROLE_ORDER},
            "role_successor_order_ok": cycle_is_role_successor_order(rows, cyc),
            "form_counts_for_evaluation_only": forms,
            "phi": phi,
            "expected_form_index_for_evaluation_only": expected_form,
            "phi_matches_form_index_partition": match,
        }
        components.append(comp)

        for i in cyc:
            row_assignment[i] = {
                "component_id": cid,
                "phi_level": phi["phi_level"],
                "expected_form_index": expected_form,
                "match": as_int(rows[i]["form_index"]) == expected_form,
            }

    phi_component_counts = Counter(c["phi"]["phi_level"] for c in components)
    phi_row_counts = Counter(row_assignment[i]["phi_level"] for i in range(len(rows)) if i in row_assignment)

    all_rows_assigned = len(row_assignment) == len(rows)
    all_rows_match = all(row_assignment[i]["match"] for i in range(len(rows))) if all_rows_assigned else False

    statement = (
        "Artifact 004 records a directed role-successor cycle source-construction assignment phi. "
        "Rows are grouped by native transition continuity row.to_ABC = next_row.from_ABC and role order WX->XY->YZ->ZT->TI->IW->WX, not by row order. "
        "phi is computed from slot_delta_mod15, fiber_delta_mod60, and edge_role. form_index is used only for evaluation. "
        "answer-label leakage remains open. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    missing_required = missing(statement, REQUIRED)
    forbidden_found = found(statement, FORBIDDEN)

    checks = {
        "ledger_002_pass": bool(ledger.get("audit_pass")),
        "row_count": len(rows),
        "row_count_is_24": len(rows) == 24,
        "successor_ambiguity_count": len(successor_ambiguities),
        "successor_ambiguity_count_is_0": len(successor_ambiguities) == 0,
        "broken_path_count": len(broken_paths),
        "broken_path_count_is_0": len(broken_paths) == 0,
        "directed_cycle_count": len(cycles),
        "directed_cycle_count_is_4": len(cycles) == 4,
        "cycle_sizes_are_6": all(len(c) == 6 for c in cycles),
        "each_cycle_has_all_six_roles_once": all(c["has_all_six_roles_once"] for c in components),
        "each_cycle_has_role_successor_order": all(c["role_successor_order_ok"] for c in components),
        "all_rows_assigned": all_rows_assigned,
        "phi_has_four_levels_once": dict(sorted(phi_component_counts.items())) == {"closed_face": 1, "edge": 1, "filled_cell": 1, "hinge": 1},
        "phi_row_partition_is_6_each": dict(sorted(phi_row_counts.items())) == {"closed_face": 6, "edge": 6, "filled_cell": 6, "hinge": 6},
        "phi_matches_form_index_partition": all_rows_match,
        "row_order_used_for_phi": False,
        "form_index_used_only_for_evaluation": True,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(missing_required) == 0,
        "forbidden_phrases_absent": len(forbidden_found) == 0,
    }

    audit_pass = all([
        checks["ledger_002_pass"],
        checks["row_count_is_24"],
        checks["successor_ambiguity_count_is_0"],
        checks["broken_path_count_is_0"],
        checks["directed_cycle_count_is_4"],
        checks["cycle_sizes_are_6"],
        checks["each_cycle_has_all_six_roles_once"],
        checks["each_cycle_has_role_successor_order"],
        checks["all_rows_assigned"],
        checks["phi_has_four_levels_once"],
        checks["phi_row_partition_is_6_each"],
        checks["phi_matches_form_index_partition"],
        checks["row_order_used_for_phi"] is False,
        checks["form_index_used_only_for_evaluation"],
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_directed_cycle_phi_recorded",
        "audit_id": "004",
        "audit_pass": audit_pass,
        "verdict": "directed_cycle_phi_exact_on_24_row_register" if audit_pass else "directed_cycle_phi_failed",
        "statement": statement,
        "inputs": {
            "ledger_json": str(IN_LEDGER.relative_to(ROOT)),
            "ledger_rows_csv": str(IN_ROWS.relative_to(ROOT)),
        },
        "construction_fields_used_for_phi": [
            "from_A", "from_B", "from_C",
            "to_A", "to_B", "to_C",
            "edge_role",
            "slot_delta_mod15",
            "fiber_delta_mod60",
        ],
        "evaluation_fields_not_used_for_phi": [
            "form_index",
            "ledger_row_id",
        ],
        "phi_rule": {
            "component_source": "directed role-successor cycles using row.to_ABC = next_row.from_ABC",
            "role_successor_cycle": ROLE_ORDER,
            "capture_rule": "capture iff slot_delta_mod15 > fiber_delta_mod60",
            "assignment": [
                {"condition": "capture_count == 0", "level": "edge"},
                {"condition": "capture_count == 1", "level": "hinge"},
                {"condition": "capture_count == 2 and TI.fiber_delta_mod60 == 3", "level": "closed_face"},
                {"condition": "capture_count == 2 and TI.fiber_delta_mod60 == 1", "level": "filled_cell"},
            ],
        },
        "checks": checks,
        "components": components,
        "successor_ambiguities": successor_ambiguities,
        "broken_paths": broken_paths,
        "missing_required_phrases": missing_required,
        "forbidden_phrases_found": forbidden_found,
        "boundary": {
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
            "ledger_row_id",
            "component_id",
            "edge_role",
            "from_ABC",
            "to_ABC",
            "slot_delta_mod15",
            "fiber_delta_mod60",
            "capture_native",
            "phi_level",
            "form_index_for_evaluation_only",
            "match",
        ])
        for i, row in enumerate(rows):
            a = row_assignment[i]
            w.writerow([
                row["ledger_row_id"],
                a["component_id"],
                row["edge_role"],
                node(row, "from"),
                node(row, "to"),
                row["slot_delta_mod15"],
                row["fiber_delta_mod60"],
                inside_captured_native(row),
                a["phi_level"],
                row["form_index"],
                a["match"],
            ])

    lines = []
    lines.append("# Source construction directed cycle phi 004")
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
    lines.append("## Phi rule")
    lines.append("")
    lines.append("- Group rows by directed role-successor cycle: WX -> XY -> YZ -> ZT -> TI -> IW -> WX.")
    lines.append("- Require native continuity: row.to_ABC equals next_row.from_ABC.")
    lines.append("- Compute capture_count using slot_delta_mod15 > fiber_delta_mod60.")
    lines.append("- capture_count 0 -> edge.")
    lines.append("- capture_count 1 -> hinge.")
    lines.append("- capture_count 2 with TI.fiber_delta_mod60 3 -> closed_face.")
    lines.append("- capture_count 2 with TI.fiber_delta_mod60 1 -> filled_cell.")
    lines.append("")
    lines.append("## Components")
    lines.append("")
    for c in components:
        lines.append(
            "- component "
            + str(c["component_id"])
            + ": rows="
            + str(c["source_row_ids"])
            + ", roles="
            + " ".join(c["edge_roles_in_directed_order"])
            + ", phi="
            + c["phi"]["phi_level"]
            + ", reason="
            + c["phi"]["reason"]
            + ", forms="
            + str(c["form_counts_for_evaluation_only"])
            + ", match="
            + str(c["phi_matches_form_index_partition"])
        )
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This is an exact source-construction assignment phi on the 24-row register, not native closure and not Gap A closure. form_index is used only for evaluation. answer-label leakage remains open until the source provenance and independence of the fields used by phi are audited more deeply.")
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
