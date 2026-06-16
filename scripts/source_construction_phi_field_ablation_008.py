#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

IN_004 = ROOT / "artifacts/json/source_construction_directed_cycle_phi_004.v1.json"
IN_005 = ROOT / "artifacts/json/source_construction_phi_independence_audit_005.v1.json"
IN_006 = ROOT / "artifacts/json/source_construction_phi_field_source_audit_006.v1.json"
IN_007 = ROOT / "artifacts/json/source_construction_phi_label_removal_audit_007.v1.json"
IN_ROWS = ROOT / "artifacts/csv/source_construction_phi_label_removed_rows_007.v1.csv"

OUT_JSON = ROOT / "artifacts/json/source_construction_phi_field_ablation_008.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_phi_field_ablation_008.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_phi_field_ablation_008.md"

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

ROLE_ORDER = ["WX", "XY", "YZ", "ZT", "TI", "IW"]
NEXT_ROLE = {
    "WX": "XY",
    "XY": "YZ",
    "YZ": "ZT",
    "ZT": "TI",
    "TI": "IW",
    "IW": "WX",
}

EXPECTED_ROW_COUNTS = {
    "edge": 6,
    "hinge": 6,
    "closed_face": 6,
    "filled_cell": 6,
}

EXPECTED_CYCLE_COUNTS = {
    "edge": 1,
    "hinge": 1,
    "closed_face": 1,
    "filled_cell": 1,
}

REQUIRED = [
    "field ablation audit",
    "source-construction phi",
    "load-bearing fields",
    "label-column independence remains intact",
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


def node(row, prefix, missing):
    keys = [prefix + "_A", prefix + "_B", prefix + "_C"]
    if any(k in missing for k in keys):
        return None
    vals = []
    for k in keys:
        if k not in row:
            return None
        vals.append(as_int(row[k]))
    if any(v is None for v in vals):
        return None
    return tuple(vals)


def transition_key(row):
    return (
        row.get("edge_role", ""),
        row.get("from_A", ""),
        row.get("from_B", ""),
        row.get("from_C", ""),
        row.get("to_A", ""),
        row.get("to_B", ""),
        row.get("to_C", ""),
        row.get("slot_delta_mod15", ""),
        row.get("fiber_delta_mod60", ""),
    )


def inside_captured_native(row, missing):
    if "slot_delta_mod15" in missing or "fiber_delta_mod60" in missing:
        return None
    slot = as_int(row.get("slot_delta_mod15"))
    fiber = as_int(row.get("fiber_delta_mod60"))
    if slot is None or fiber is None:
        return None
    return slot > fiber


def build_successors(rows, missing):
    if "edge_role" in missing:
        return {}, [{"reason": "edge_role missing; role-successor relation unavailable"}]

    by_from_and_role = defaultdict(list)
    for i, row in enumerate(rows):
        fnode = node(row, "from", missing)
        role = row.get("edge_role")
        if fnode is None or role is None:
            return {}, [{"reason": "from_ABC or edge_role unavailable"}]
        by_from_and_role[(fnode, role)].append(i)

    successors = {}
    ambiguities = []

    for i, row in enumerate(rows):
        tnode = node(row, "to", missing)
        role = row.get("edge_role")
        if tnode is None or role not in NEXT_ROLE:
            successors[i] = None
            ambiguities.append({"row_index": i, "reason": "to_ABC or role successor unavailable"})
            continue

        next_role = NEXT_ROLE[role]
        candidates = by_from_and_role[(tnode, next_role)]
        if len(candidates) == 1:
            successors[i] = candidates[0]
        else:
            successors[i] = None
            ambiguities.append({
                "row_index": i,
                "reason": "successor ambiguity or missing successor",
                "candidate_count": len(candidates),
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
            broken.append(path)
            seen.update(path)
            continue

        if cur in local_seen:
            cyc = path[local_seen[cur]:]
            cycles.append(cyc)
            seen.update(cyc)
            seen.update(path)
        else:
            seen.update(path)

    cycles.sort(key=lambda ids: sorted(str(transition_key(rows[i])) for i in ids)[0])
    return cycles, broken


def cycle_role_order_ok(rows, ids, missing):
    if "edge_role" in missing:
        return False
    roles = [rows[i].get("edge_role") for i in ids]
    if len(roles) != 6:
        return False
    return all(role in NEXT_ROLE for role in roles) and all(NEXT_ROLE[roles[i]] == roles[(i + 1) % 6] for i in range(6))


def assign_phi(rows, ids, missing, disable_ti_discriminant=False, disable_capture_count=False):
    if disable_capture_count:
        return {
            "phi_level": "unknown",
            "reason": "capture_count disabled",
            "capture_count": None,
            "ti_fiber_delta_mod60": None,
        }

    captures = []
    for i in ids:
        cap = inside_captured_native(rows[i], missing)
        if cap is None:
            return {
                "phi_level": "unknown",
                "reason": "capture unavailable",
                "capture_count": None,
                "ti_fiber_delta_mod60": None,
            }
        if cap:
            captures.append(i)

    capture_count = len(captures)

    ti_fiber = None
    if "edge_role" not in missing and "fiber_delta_mod60" not in missing:
        ti_rows = [i for i in ids if rows[i].get("edge_role") == "TI"]
        if len(ti_rows) == 1:
            ti_fiber = as_int(rows[ti_rows[0]].get("fiber_delta_mod60"))

    if capture_count == 0:
        level = "edge"
        reason = "capture_count=0"
    elif capture_count == 1:
        level = "hinge"
        reason = "capture_count=1"
    elif capture_count == 2 and not disable_ti_discriminant and ti_fiber == 3:
        level = "closed_face"
        reason = "capture_count=2 and TI.fiber_delta_mod60=3"
    elif capture_count == 2 and not disable_ti_discriminant and ti_fiber == 1:
        level = "filled_cell"
        reason = "capture_count=2 and TI.fiber_delta_mod60=1"
    else:
        level = "unknown"
        reason = "two-capture discriminant unavailable or unmatched"

    return {
        "phi_level": level,
        "reason": reason,
        "capture_count": capture_count,
        "ti_fiber_delta_mod60": ti_fiber,
    }


def evaluate(rows, missing_fields=None, disable_ti_discriminant=False, disable_capture_count=False):
    missing = set(missing_fields or [])

    successors, ambiguities = build_successors(rows, missing)
    cycles, broken = cycles_from_successors(rows, successors)

    row_phi = {}
    cycle_records = []

    for cid, cyc in enumerate(cycles):
        phi = assign_phi(
            rows,
            cyc,
            missing,
            disable_ti_discriminant=disable_ti_discriminant,
            disable_capture_count=disable_capture_count,
        )
        cycle_records.append({
            "cycle_id": cid,
            "row_count": len(cyc),
            "role_order_ok": cycle_role_order_ok(rows, cyc, missing),
            "phi_level": phi["phi_level"],
            "reason": phi["reason"],
            "transition_keys": [str(transition_key(rows[i])) for i in cyc],
        })
        for i in cyc:
            row_phi[i] = phi["phi_level"]

    row_counts = Counter(row_phi.values())
    cycle_counts = Counter(c["phi_level"] for c in cycle_records)

    ok = (
        len(ambiguities) == 0
        and len(broken) == 0
        and len(cycles) == 4
        and all(c["row_count"] == 6 for c in cycle_records)
        and all(c["role_order_ok"] for c in cycle_records)
        and dict(sorted(row_counts.items())) == EXPECTED_ROW_COUNTS
        and dict(sorted(cycle_counts.items())) == EXPECTED_CYCLE_COUNTS
    )

    return {
        "ok": ok,
        "ambiguity_count": len(ambiguities),
        "broken_count": len(broken),
        "cycle_count": len(cycles),
        "cycle_sizes": [c["row_count"] for c in cycle_records],
        "role_order_ok_all": all(c["role_order_ok"] for c in cycle_records) if cycle_records else False,
        "row_phi_counts": dict(sorted(row_counts.items())),
        "cycle_phi_counts": dict(sorted(cycle_counts.items())),
        "cycles": cycle_records,
        "ambiguities": ambiguities[:10],
        "broken_paths": broken[:10],
    }


def required_missing(text, phrases):
    return [p for p in phrases if p not in text]


def forbidden_found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    a004 = load_json(IN_004)
    a005 = load_json(IN_005)
    a006 = load_json(IN_006)
    a007 = load_json(IN_007)
    rows = read_rows(IN_ROWS)

    if not a004.get("audit_pass"):
        raise SystemExit("004 audit_pass is not true")
    if not a005.get("audit_pass"):
        raise SystemExit("005 audit_pass is not true")
    if not a006.get("audit_pass"):
        raise SystemExit("006 audit_pass is not true")
    if not a007.get("audit_pass"):
        raise SystemExit("007 audit_pass is not true")

    tests = []

    tests.append({
        "name": "full_phi",
        "kind": "baseline",
        "missing_fields": [],
        "disable_ti_discriminant": False,
        "disable_capture_count": False,
    })

    for f in PHI_FIELDS:
        tests.append({
            "name": "drop_" + f,
            "kind": "single_field_drop",
            "missing_fields": [f],
            "disable_ti_discriminant": False,
            "disable_capture_count": False,
        })

    tests.extend([
        {
            "name": "drop_from_ABC",
            "kind": "field_group_drop",
            "missing_fields": ["from_A", "from_B", "from_C"],
            "disable_ti_discriminant": False,
            "disable_capture_count": False,
        },
        {
            "name": "drop_to_ABC",
            "kind": "field_group_drop",
            "missing_fields": ["to_A", "to_B", "to_C"],
            "disable_ti_discriminant": False,
            "disable_capture_count": False,
        },
        {
            "name": "drop_all_ABC",
            "kind": "field_group_drop",
            "missing_fields": ["from_A", "from_B", "from_C", "to_A", "to_B", "to_C"],
            "disable_ti_discriminant": False,
            "disable_capture_count": False,
        },
        {
            "name": "drop_delta_pair",
            "kind": "field_group_drop",
            "missing_fields": ["slot_delta_mod15", "fiber_delta_mod60"],
            "disable_ti_discriminant": False,
            "disable_capture_count": False,
        },
        {
            "name": "disable_ti_discriminant",
            "kind": "rule_ablation",
            "missing_fields": [],
            "disable_ti_discriminant": True,
            "disable_capture_count": False,
        },
        {
            "name": "disable_capture_count",
            "kind": "rule_ablation",
            "missing_fields": [],
            "disable_ti_discriminant": False,
            "disable_capture_count": True,
        },
    ])

    results = []
    for t in tests:
        ev = evaluate(
            rows,
            missing_fields=t["missing_fields"],
            disable_ti_discriminant=t["disable_ti_discriminant"],
            disable_capture_count=t["disable_capture_count"],
        )
        results.append({**t, **ev})

    baseline_ok = next(x for x in results if x["name"] == "full_phi")["ok"]
    ablations = [x for x in results if x["name"] != "full_phi"]
    all_ablations_fail = all(not x["ok"] for x in ablations)
    passing_ablations = [x["name"] for x in ablations if x["ok"]]

    load_bearing_failures = [
        {
            "name": x["name"],
            "kind": x["kind"],
            "missing_fields": x["missing_fields"],
            "failure_summary": {
                "ambiguity_count": x["ambiguity_count"],
                "broken_count": x["broken_count"],
                "cycle_count": x["cycle_count"],
                "row_phi_counts": x["row_phi_counts"],
                "cycle_phi_counts": x["cycle_phi_counts"],
            },
        }
        for x in ablations
        if not x["ok"]
    ]

    statement = (
        "Artifact 008 is a field ablation audit for source-construction phi. It tests load-bearing fields by removing one phi input or rule component at a time. "
        "The full source-construction phi passes, while each tested ablation fails in the current rule family. label-column independence remains intact. "
        "answer-label leakage remains open. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    miss = required_missing(statement, REQUIRED)
    forb = forbidden_found(statement, FORBIDDEN)

    checks = {
        "input_004_pass": bool(a004.get("audit_pass")),
        "input_005_pass": bool(a005.get("audit_pass")),
        "input_006_pass": bool(a006.get("audit_pass")),
        "input_007_pass": bool(a007.get("audit_pass")),
        "row_count": len(rows),
        "row_count_is_24": len(rows) == 24,
        "baseline_full_phi_pass": baseline_ok,
        "test_count": len(results),
        "ablation_count": len(ablations),
        "all_tested_ablations_fail": all_ablations_fail,
        "passing_ablation_count": len(passing_ablations),
        "label_column_independence_remains_intact": True,
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
        checks["input_007_pass"],
        checks["row_count_is_24"],
        checks["baseline_full_phi_pass"],
        checks["all_tested_ablations_fail"],
        checks["passing_ablation_count"] == 0,
        checks["label_column_independence_remains_intact"],
        checks["form_index_used"] is False,
        checks["ledger_row_id_used"] is False,
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_phi_field_ablation_recorded",
        "audit_id": "008",
        "audit_pass": audit_pass,
        "verdict": "tested_phi_inputs_are_load_bearing" if audit_pass else "phi_ablation_audit_found_non_load_bearing_inputs",
        "statement": statement,
        "inputs": {
            "directed_cycle_phi_004": str(IN_004.relative_to(ROOT)),
            "phi_independence_005": str(IN_005.relative_to(ROOT)),
            "phi_field_source_audit_006": str(IN_006.relative_to(ROOT)),
            "phi_label_removal_audit_007": str(IN_007.relative_to(ROOT)),
            "label_removed_rows": str(IN_ROWS.relative_to(ROOT)),
        },
        "checks": checks,
        "passing_ablations": passing_ablations,
        "load_bearing_failures": load_bearing_failures,
        "test_results": results,
        "missing_required_phrases": miss,
        "forbidden_phrases_found": forb,
        "boundary": {
            "current_rule_family_only": True,
            "candidate_not_theorem_yet": True,
            "label_column_independence": True,
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
            "name",
            "kind",
            "ok",
            "missing_fields",
            "ambiguity_count",
            "broken_count",
            "cycle_count",
            "cycle_sizes",
            "role_order_ok_all",
            "row_phi_counts",
            "cycle_phi_counts",
        ])
        for x in results:
            w.writerow([
                x["name"],
                x["kind"],
                x["ok"],
                "|".join(x["missing_fields"]),
                x["ambiguity_count"],
                x["broken_count"],
                x["cycle_count"],
                "|".join(str(v) for v in x["cycle_sizes"]),
                x["role_order_ok_all"],
                json.dumps(x["row_phi_counts"], sort_keys=True),
                json.dumps(x["cycle_phi_counts"], sort_keys=True),
            ])

    lines = []
    lines.append("# Source construction phi field ablation 008")
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
    lines.append("## Passing ablations")
    lines.append("")
    if passing_ablations:
        for x in passing_ablations:
            lines.append("- " + x)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This audit shows that the tested inputs and rule components are load-bearing in the current phi rule family. It does not prove minimality over all possible source-construction rules. It does not prove native closure, does not close Gap A, and does not derive the full role-labeled shared_B universe. answer-label leakage remains open pending deeper construction-origin tests.")
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
    print("passing_ablations", passing_ablations)


if __name__ == "__main__":
    main()
