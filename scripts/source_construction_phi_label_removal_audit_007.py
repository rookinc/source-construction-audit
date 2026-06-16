#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

IN_004 = ROOT / "artifacts/json/source_construction_directed_cycle_phi_004.v1.json"
IN_005 = ROOT / "artifacts/json/source_construction_phi_independence_audit_005.v1.json"
IN_006 = ROOT / "artifacts/json/source_construction_phi_field_source_audit_006.v1.json"
IN_ROWS = ROOT / "artifacts/csv/source_construction_ledger_inventory_002_rows.v1.csv"

OUT_JSON = ROOT / "artifacts/json/source_construction_phi_label_removal_audit_007.v1.json"
OUT_STRIPPED = ROOT / "artifacts/csv/source_construction_phi_label_removed_rows_007.v1.csv"
OUT_ASSIGN = ROOT / "artifacts/csv/source_construction_phi_label_removal_audit_007.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_phi_label_removal_audit_007.md"

PHI_FIELDS = [
    "edge_role",
    "from_A",
    "from_B",
    "from_C",
    "to_A",
    "to_B",
    "to_C",
    "slot_delta_mod15",
    "fiber_delta_mod60",
]

REMOVED_FIELDS = [
    "form_index",
    "ledger_row_id",
]

ROLE_ORDER = ["WX", "XY", "YZ", "ZT", "TI", "IW"]
NEXT_ROLE = {
    "WX": "XY",
    "XY": "YZ",
    "YZ": "ZT",
    "ZT": "TI",
    "TI": "IW",
    "IW": "WX",
}

REQUIRED = [
    "label removal audit",
    "form_index removed from working rows",
    "ledger_row_id removed from working rows",
    "source-side transition signatures",
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


def transition_signature(row):
    return {
        "edge_role": row["edge_role"],
        "from_ABC": list(node(row, "from")),
        "to_ABC": list(node(row, "to")),
        "slot_delta_mod15": as_int(row["slot_delta_mod15"]),
        "fiber_delta_mod60": as_int(row["fiber_delta_mod60"]),
    }


def transition_key(row):
    sig = transition_signature(row)
    return json.dumps(sig, sort_keys=True, separators=(",", ":"))


def inside_captured_native(row):
    return as_int(row["slot_delta_mod15"]) > as_int(row["fiber_delta_mod60"])


def build_successors(rows):
    by_from_and_role = defaultdict(list)
    for i, row in enumerate(rows):
        by_from_and_role[(node(row, "from"), row["edge_role"])].append(i)

    successors = {}
    ambiguities = []
    for i, row in enumerate(rows):
        target = node(row, "to")
        next_role = NEXT_ROLE[row["edge_role"]]
        candidates = by_from_and_role[(target, next_role)]
        if len(candidates) == 1:
            successors[i] = candidates[0]
        else:
            successors[i] = None
            ambiguities.append({
                "transition_key": transition_key(row),
                "edge_role": row["edge_role"],
                "target": target,
                "next_role": next_role,
                "candidate_count": len(candidates),
                "candidate_keys": [transition_key(rows[j]) for j in candidates],
            })
    return successors, ambiguities


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
            broken.append([transition_key(rows[i]) for i in path])
            seen.update(path)
            continue

        if cur in local_seen:
            cyc = path[local_seen[cur]:]
            cycles.append(cyc)
            seen.update(cyc)
            seen.update(path)
        else:
            seen.update(path)

    cycles.sort(key=lambda ids: sorted(transition_key(rows[i]) for i in ids)[0])
    return cycles, broken


def assign_phi(rows, ids):
    captures = [i for i in ids if inside_captured_native(rows[i])]
    ti_rows = [i for i in ids if rows[i]["edge_role"] == "TI"]
    ti_fiber = as_int(rows[ti_rows[0]]["fiber_delta_mod60"]) if len(ti_rows) == 1 else None
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
        "ti_fiber_delta_mod60": ti_fiber,
    }


def cycle_role_order_ok(rows, ids):
    roles = [rows[i]["edge_role"] for i in ids]
    if len(roles) != 6:
        return False
    return all(NEXT_ROLE[roles[i]] == roles[(i + 1) % 6] for i in range(6))


def compute_phi(rows):
    successors, ambiguities = build_successors(rows)
    cycles, broken = cycles_from_successors(rows, successors)

    cycles_out = []
    row_phi_by_key = {}

    for cid, cyc in enumerate(cycles):
        phi = assign_phi(rows, cyc)
        keys = [transition_key(rows[i]) for i in cyc]
        role_seq = [rows[i]["edge_role"] for i in cyc]

        cycles_out.append({
            "cycle_id": cid,
            "phi_level": phi["phi_level"],
            "reason": phi["reason"],
            "transition_keys": sorted(keys),
            "role_sequence": role_seq,
            "role_order_ok": cycle_role_order_ok(rows, cyc),
            "row_count": len(cyc),
        })

        for i in cyc:
            row_phi_by_key[transition_key(rows[i])] = phi["phi_level"]

    return {
        "ambiguities": ambiguities,
        "broken": broken,
        "cycles": cycles_out,
        "row_phi_by_transition_key": row_phi_by_key,
    }


def strip_rows(rows):
    out = []
    for row in rows:
        out.append({k: row[k] for k in PHI_FIELDS})
    return out


def required_missing(text, phrases):
    return [p for p in phrases if p not in text]


def forbidden_found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    a004 = load_json(IN_004)
    a005 = load_json(IN_005)
    a006 = load_json(IN_006)
    full_rows = read_rows(IN_ROWS)

    if not a004.get("audit_pass"):
        raise SystemExit("004 audit_pass is not true")
    if not a005.get("audit_pass"):
        raise SystemExit("005 audit_pass is not true")
    if not a006.get("audit_pass"):
        raise SystemExit("006 audit_pass is not true")

    stripped_rows = strip_rows(full_rows)

    removed_absent = all(
        all(f not in row for f in REMOVED_FIELDS)
        for row in stripped_rows
    )

    baseline = compute_phi(stripped_rows)
    phi_counts = Counter(baseline["row_phi_by_transition_key"].values())
    cycle_counts = Counter(c["phi_level"] for c in baseline["cycles"])

    expected_phi_counts = {
        "closed_face": 6,
        "edge": 6,
        "filled_cell": 6,
        "hinge": 6,
    }

    expected_cycle_counts = {
        "closed_face": 1,
        "edge": 1,
        "filled_cell": 1,
        "hinge": 1,
    }

    statement = (
        "Artifact 007 is a label removal audit. It recomputes phi after form_index removed from working rows and "
        "ledger_row_id removed from working rows. The computation compares source-side transition signatures only. "
        "answer-label leakage remains open because this supports label-column independence but is not native closure, "
        "not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    miss = required_missing(statement, REQUIRED)
    forb = forbidden_found(statement, FORBIDDEN)

    checks = {
        "input_004_pass": bool(a004.get("audit_pass")),
        "input_005_pass": bool(a005.get("audit_pass")),
        "input_006_pass": bool(a006.get("audit_pass")),
        "row_count": len(stripped_rows),
        "row_count_is_24": len(stripped_rows) == 24,
        "removed_fields_absent_from_working_rows": removed_absent,
        "working_field_count": len(PHI_FIELDS),
        "working_fields_equal_phi_fields": sorted(stripped_rows[0].keys()) == sorted(PHI_FIELDS),
        "ambiguity_count": len(baseline["ambiguities"]),
        "ambiguity_count_is_0": len(baseline["ambiguities"]) == 0,
        "broken_path_count": len(baseline["broken"]),
        "broken_path_count_is_0": len(baseline["broken"]) == 0,
        "cycle_count": len(baseline["cycles"]),
        "cycle_count_is_4": len(baseline["cycles"]) == 4,
        "cycle_sizes_are_6": all(c["row_count"] == 6 for c in baseline["cycles"]),
        "role_order_ok_all": all(c["role_order_ok"] for c in baseline["cycles"]),
        "phi_cycle_counts_are_one_each": dict(sorted(cycle_counts.items())) == expected_cycle_counts,
        "phi_row_counts_are_six_each": dict(sorted(phi_counts.items())) == expected_phi_counts,
        "form_index_used": False,
        "ledger_row_id_used": False,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(miss) == 0,
        "forbidden_phrases_absent": len(forb) == 0,
    }

    audit_pass = all([
        checks["input_004_pass"],
        checks["input_005_pass"],
        checks["input_006_pass"],
        checks["row_count_is_24"],
        checks["removed_fields_absent_from_working_rows"],
        checks["working_fields_equal_phi_fields"],
        checks["ambiguity_count_is_0"],
        checks["broken_path_count_is_0"],
        checks["cycle_count_is_4"],
        checks["cycle_sizes_are_6"],
        checks["role_order_ok_all"],
        checks["phi_cycle_counts_are_one_each"],
        checks["phi_row_counts_are_six_each"],
        checks["form_index_used"] is False,
        checks["ledger_row_id_used"] is False,
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_phi_label_removal_audit_recorded",
        "audit_id": "007",
        "audit_pass": audit_pass,
        "verdict": "phi_survives_label_column_removal" if audit_pass else "phi_label_removal_failed",
        "statement": statement,
        "inputs": {
            "directed_cycle_phi_004": str(IN_004.relative_to(ROOT)),
            "phi_independence_005": str(IN_005.relative_to(ROOT)),
            "phi_field_source_audit_006": str(IN_006.relative_to(ROOT)),
            "source_rows": str(IN_ROWS.relative_to(ROOT)),
        },
        "removed_fields": REMOVED_FIELDS,
        "working_fields": PHI_FIELDS,
        "checks": checks,
        "phi_cycle_counts": dict(sorted(cycle_counts.items())),
        "phi_row_counts": dict(sorted(phi_counts.items())),
        "cycles": baseline["cycles"],
        "missing_required_phrases": miss,
        "forbidden_phrases_found": forb,
        "boundary": {
            "label_column_independence": True,
            "candidate_not_theorem_yet": True,
            "answer_label_leakage_remains_open": True,
            "native_closure": False,
            "gap_a_closure": False,
            "full_role_labeled_shared_B_universe_derived": False,
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_STRIPPED.parent.mkdir(parents=True, exist_ok=True)
    OUT_ASSIGN.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTE.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with OUT_STRIPPED.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PHI_FIELDS)
        w.writeheader()
        for row in stripped_rows:
            w.writerow(row)

    with OUT_ASSIGN.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transition_key", "phi_level"])
        for k, v in sorted(baseline["row_phi_by_transition_key"].items()):
            w.writerow([k, v])

    lines = []
    lines.append("# Source construction phi label removal audit 007")
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
    lines.append("## Removed fields")
    lines.append("")
    for f in REMOVED_FIELDS:
        lines.append("- " + f)
    lines.append("")
    lines.append("## Working fields")
    lines.append("")
    for f in PHI_FIELDS:
        lines.append("- " + f)
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This audit supports label-column independence for phi. It does not prove native closure, does not close Gap A, and does not derive the full role-labeled shared_B universe. answer-label leakage remains open pending deeper provenance and construction-origin tests.")
    lines.append("")

    OUT_NOTE.write_text("\n".join(lines), encoding="utf-8")

    print("wrote", OUT_JSON)
    print("wrote", OUT_STRIPPED)
    print("wrote", OUT_ASSIGN)
    print("wrote", OUT_NOTE)
    print("status", result["status"])
    print("audit_pass", audit_pass)
    print("verdict", result["verdict"])
    for k, v in checks.items():
        print(k, v)
    print("phi_cycle_counts", dict(sorted(cycle_counts.items())))
    print("phi_row_counts", dict(sorted(phi_counts.items())))


if __name__ == "__main__":
    main()
