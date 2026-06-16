#!/usr/bin/env python3
import csv
import json
import random
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

IN_004 = ROOT / "artifacts/json/source_construction_directed_cycle_phi_004.v1.json"
IN_ROWS = ROOT / "artifacts/csv/source_construction_ledger_inventory_002_rows.v1.csv"

OUT_JSON = ROOT / "artifacts/json/source_construction_phi_independence_audit_005.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_phi_independence_audit_005.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_phi_independence_audit_005.md"

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
    "phi independence audit",
    "row order shuffled",
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
                "ledger_row_id": as_int(row["ledger_row_id"]),
                "edge_role": row["edge_role"],
                "target": target,
                "next_role": next_role,
                "candidate_ledger_row_ids": [as_int(rows[j]["ledger_row_id"]) for j in candidates],
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
        "ti_fiber_delta_mod60": ti_fiber,
    }


def role_counts(rows, ids):
    return dict(sorted(Counter(rows[i]["edge_role"] for i in ids).items()))


def cycle_role_order_ok(rows, ids):
    roles = [rows[i]["edge_role"] for i in ids]
    if len(roles) != 6:
        return False
    return all(NEXT_ROLE[roles[i]] == roles[(i + 1) % 6] for i in range(6))


def evaluate_rows(rows):
    successors, ambiguities = build_successors(rows)
    cycles, broken = cycles_from_successors(rows, successors)

    row_phi = {}
    cycle_records = []

    for cid, cyc in enumerate(cycles):
        phi = assign_phi(rows, cyc)
        expected_form = LEVEL_TO_FORM.get(phi["phi_level"])
        ledger_ids = [as_int(rows[i]["ledger_row_id"]) for i in cyc]
        roles = [rows[i]["edge_role"] for i in cyc]
        forms = dict(sorted(Counter(as_int(rows[i]["form_index"]) for i in cyc).items()))

        cycle_records.append({
            "cycle_id": cid,
            "ledger_row_ids": ledger_ids,
            "roles": roles,
            "role_counts": role_counts(rows, cyc),
            "role_order_ok": cycle_role_order_ok(rows, cyc),
            "phi_level": phi["phi_level"],
            "phi_reason": phi["reason"],
            "expected_form_for_evaluation_only": expected_form,
            "form_counts_for_evaluation_only": forms,
        })

        for i in cyc:
            rid = as_int(rows[i]["ledger_row_id"])
            row_phi[rid] = {
                "phi_level": phi["phi_level"],
                "expected_form_for_evaluation_only": expected_form,
                "actual_form_for_evaluation_only": as_int(rows[i]["form_index"]),
                "match": as_int(rows[i]["form_index"]) == expected_form,
            }

    return {
        "ambiguities": ambiguities,
        "broken": broken,
        "cycles": cycle_records,
        "row_phi": row_phi,
    }


def canonical_phi_map(row_phi):
    return {str(k): v["phi_level"] for k, v in sorted(row_phi.items())}


def canonical_cycle_sets(cycles):
    return sorted([
        {
            "phi_level": c["phi_level"],
            "ledger_row_ids": sorted(c["ledger_row_ids"]),
        }
        for c in cycles
    ], key=lambda x: (x["phi_level"], x["ledger_row_ids"]))


def permutation_suite(rows):
    suites = []

    suites.append(("original", list(rows)))
    suites.append(("reverse", list(reversed(rows))))
    suites.append(("sort_by_role", sorted(rows, key=lambda r: (r["edge_role"], as_int(r["ledger_row_id"])))))
    suites.append(("sort_by_fiber", sorted(rows, key=lambda r: (as_int(r["fiber_delta_mod60"]), as_int(r["ledger_row_id"])))))
    suites.append(("sort_by_from_C", sorted(rows, key=lambda r: (as_int(r["from_C"]), as_int(r["ledger_row_id"])))))
    suites.append(("sort_by_to_C", sorted(rows, key=lambda r: (as_int(r["to_C"]), as_int(r["ledger_row_id"])))))

    for seed in range(20):
        xs = list(rows)
        random.Random(seed).shuffle(xs)
        suites.append(("shuffle_seed_" + str(seed), xs))

    return suites


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    a004 = load_json(IN_004)
    rows = read_rows(IN_ROWS)

    if not a004.get("audit_pass"):
        raise SystemExit("004 audit_pass is not true")

    baseline_eval = evaluate_rows(rows)
    baseline_phi = canonical_phi_map(baseline_eval["row_phi"])
    baseline_cycles = canonical_cycle_sets(baseline_eval["cycles"])

    permutation_results = []
    all_ok = True

    for name, perm_rows in permutation_suite(rows):
        ev = evaluate_rows(perm_rows)
        phi_map = canonical_phi_map(ev["row_phi"])
        cycle_sets = canonical_cycle_sets(ev["cycles"])

        checks = {
            "ambiguity_count": len(ev["ambiguities"]),
            "broken_count": len(ev["broken"]),
            "cycle_count": len(ev["cycles"]),
            "cycle_sizes_are_6": all(len(c["ledger_row_ids"]) == 6 for c in ev["cycles"]),
            "role_order_ok_all": all(c["role_order_ok"] for c in ev["cycles"]),
            "phi_map_matches_baseline": phi_map == baseline_phi,
            "cycle_sets_match_baseline": cycle_sets == baseline_cycles,
            "all_rows_match_form_index_for_evaluation_only": all(v["match"] for v in ev["row_phi"].values()),
        }

        ok = (
            checks["ambiguity_count"] == 0
            and checks["broken_count"] == 0
            and checks["cycle_count"] == 4
            and checks["cycle_sizes_are_6"]
            and checks["role_order_ok_all"]
            and checks["phi_map_matches_baseline"]
            and checks["cycle_sets_match_baseline"]
            and checks["all_rows_match_form_index_for_evaluation_only"]
        )

        if not ok:
            all_ok = False

        permutation_results.append({
            "permutation": name,
            "ok": ok,
            "checks": checks,
        })

    statement = (
        "Artifact 005 is a phi independence audit. It verifies that the directed role-successor phi survives when row order shuffled. "
        "The computation uses native transition continuity and role successor order, while form_index is used only for evaluation. "
        "answer-label leakage remains open. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    missing_required = missing(statement, REQUIRED)
    forbidden_found = found(statement, FORBIDDEN)

    checks = {
        "input_004_pass": bool(a004.get("audit_pass")),
        "row_count": len(rows),
        "row_count_is_24": len(rows) == 24,
        "permutation_count": len(permutation_results),
        "all_permutations_ok": all_ok,
        "baseline_cycle_count": len(baseline_eval["cycles"]),
        "baseline_cycle_count_is_4": len(baseline_eval["cycles"]) == 4,
        "baseline_phi_has_24_rows": len(baseline_phi) == 24,
        "form_index_used_only_for_evaluation": True,
        "row_order_used_for_phi": False,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(missing_required) == 0,
        "forbidden_phrases_absent": len(forbidden_found) == 0,
    }

    audit_pass = all([
        checks["input_004_pass"],
        checks["row_count_is_24"],
        checks["permutation_count"] >= 20,
        checks["all_permutations_ok"],
        checks["baseline_cycle_count_is_4"],
        checks["baseline_phi_has_24_rows"],
        checks["form_index_used_only_for_evaluation"],
        checks["row_order_used_for_phi"] is False,
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_phi_independence_audit_recorded",
        "audit_id": "005",
        "audit_pass": audit_pass,
        "verdict": "phi_row_order_independence_passed" if audit_pass else "phi_row_order_independence_failed",
        "statement": statement,
        "inputs": {
            "directed_cycle_phi_004": str(IN_004.relative_to(ROOT)),
            "rows_csv": str(IN_ROWS.relative_to(ROOT)),
        },
        "baseline_phi_by_ledger_row_id": baseline_phi,
        "baseline_cycle_sets": baseline_cycles,
        "checks": checks,
        "permutation_results": permutation_results,
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
            "permutation",
            "ok",
            "ambiguity_count",
            "broken_count",
            "cycle_count",
            "cycle_sizes_are_6",
            "role_order_ok_all",
            "phi_map_matches_baseline",
            "cycle_sets_match_baseline",
            "all_rows_match_form_index_for_evaluation_only",
        ])
        for x in permutation_results:
            c = x["checks"]
            w.writerow([
                x["permutation"],
                x["ok"],
                c["ambiguity_count"],
                c["broken_count"],
                c["cycle_count"],
                c["cycle_sizes_are_6"],
                c["role_order_ok_all"],
                c["phi_map_matches_baseline"],
                c["cycle_sets_match_baseline"],
                c["all_rows_match_form_index_for_evaluation_only"],
            ])

    lines = []
    lines.append("# Source construction phi independence audit 005")
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
    lines.append("## What was attacked")
    lines.append("")
    lines.append("- original row order")
    lines.append("- reverse row order")
    lines.append("- role-sorted order")
    lines.append("- fiber-sorted order")
    lines.append("- from_C and to_C sorted orders")
    lines.append("- 20 deterministic random shuffles")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This proves row-order independence in the tested permutations, not native closure and not Gap A closure. form_index is used only for evaluation. answer-label leakage remains open because the source provenance of the fields used by phi still needs deeper audit.")
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
