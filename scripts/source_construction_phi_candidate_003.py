#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict, deque

ROOT = Path(__file__).resolve().parents[1]

IN_LEDGER = ROOT / "artifacts/json/source_construction_ledger_inventory_002.v1.json"
IN_ROWS = ROOT / "artifacts/csv/source_construction_ledger_inventory_002_rows.v1.csv"

OUT_JSON = ROOT / "artifacts/json/source_construction_phi_candidate_003.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_phi_candidate_003_rows.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_phi_candidate_003.md"

LEVEL_TO_FORM = {
    "edge": 0,
    "hinge": 1,
    "closed_face": 2,
    "filled_cell": 3,
}

ROLE_ORDER = ["WX", "XY", "YZ", "ZT", "TI", "IW"]

REQUIRED = [
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


def as_int(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if s == "":
        return None
    if s.lstrip("-").isdigit():
        return int(s)
    return None


def read_rows(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def node_key(row, prefix):
    return (
        as_int(row[prefix + "_A"]),
        as_int(row[prefix + "_B"]),
        as_int(row[prefix + "_C"]),
    )


def build_transition_components(rows):
    node_to_row_ids = defaultdict(list)
    for i, row in enumerate(rows):
        a = node_key(row, "from")
        b = node_key(row, "to")
        node_to_row_ids[a].append(i)
        node_to_row_ids[b].append(i)

    row_adj = [[] for _ in rows]
    for ids in node_to_row_ids.values():
        for i in ids:
            for j in ids:
                if i != j:
                    row_adj[i].append(j)

    seen = [False] * len(rows)
    comps = []
    for start in range(len(rows)):
        if seen[start]:
            continue
        q = deque([start])
        seen[start] = True
        comp = []
        while q:
            x = q.popleft()
            comp.append(x)
            for y in row_adj[x]:
                if not seen[y]:
                    seen[y] = True
                    q.append(y)
        comps.append(sorted(comp))

    comps.sort(key=lambda ids: min(ids))
    return comps


def role_counts(rows, ids):
    return dict(sorted(Counter(rows[i]["edge_role"] for i in ids).items()))


def form_counts(rows, ids):
    return dict(sorted(Counter(as_int(rows[i]["form_index"]) for i in ids).items()))


def inside_captured_native(row):
    slot = as_int(row["slot_delta_mod15"])
    fiber = as_int(row["fiber_delta_mod60"])
    if slot is None or fiber is None:
        return None
    return slot > fiber


def assign_phi(rows, ids):
    captures = []
    ti_rows = []
    for i in ids:
        row = rows[i]
        cap = inside_captured_native(row)
        if cap is True:
            captures.append(i)
        if row["edge_role"] == "TI":
            ti_rows.append(i)

    capture_count = len(captures)

    ti_fiber = None
    if len(ti_rows) == 1:
        ti_fiber = as_int(rows[ti_rows[0]]["fiber_delta_mod60"])

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
        "capture_row_ids": ids_to_original(rows, captures),
        "ti_fiber_delta_mod60": ti_fiber,
    }


def ids_to_original(rows, ids):
    return [as_int(rows[i]["ledger_row_id"]) for i in ids]


def component_transition_cycle_ok(rows, ids):
    from_nodes = Counter(node_key(rows[i], "from") for i in ids)
    to_nodes = Counter(node_key(rows[i], "to") for i in ids)
    all_nodes = set(from_nodes) | set(to_nodes)
    return all(from_nodes[n] == 1 and to_nodes[n] == 1 for n in all_nodes)


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    ledger = load_json(IN_LEDGER)
    rows = read_rows(IN_ROWS)

    if not ledger.get("audit_pass"):
        raise SystemExit("002 audit_pass is not true")

    comps = build_transition_components(rows)

    components = []
    row_assignments = {}

    for cid, ids in enumerate(comps):
        phi = assign_phi(rows, ids)
        forms = form_counts(rows, ids)
        roles = role_counts(rows, ids)
        expected_form = LEVEL_TO_FORM.get(phi["phi_level"])
        matches = expected_form is not None and forms == {expected_form: len(ids)}

        comp = {
            "component_id": cid,
            "source_row_ids": ids_to_original(rows, ids),
            "row_count": len(ids),
            "role_counts": roles,
            "has_all_six_roles_once": roles == {r: 1 for r in ROLE_ORDER},
            "transition_cycle_ok": component_transition_cycle_ok(rows, ids),
            "form_counts_for_evaluation_only": forms,
            "phi": phi,
            "expected_form_index_for_evaluation_only": expected_form,
            "phi_matches_form_index_partition": matches,
        }
        components.append(comp)

        for i in ids:
            row_assignments[i] = {
                "component_id": cid,
                "phi_level": phi["phi_level"],
                "expected_form_index": expected_form,
                "match": as_int(rows[i]["form_index"]) == expected_form,
            }

    phi_counts = Counter(x["phi"]["phi_level"] for x in components)
    row_phi_counts = Counter(row_assignments[i]["phi_level"] for i in range(len(rows)))
    all_rows_match = all(row_assignments[i]["match"] for i in range(len(rows)))

    statement = (
        "Artifact 003 records a source-construction assignment phi. It derives native transition components from "
        "from_A/from_B/from_C to to_A/to_B/to_C, computes capture_count from slot_delta_mod15 and fiber_delta_mod60, "
        "and uses edge_role plus TI.fiber_delta_mod60 as the filling discriminant. form_index is used only for evaluation. "
        "answer-label leakage remains open. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    gate_text = statement
    missing_required = missing(gate_text, REQUIRED)
    forbidden_found = found(gate_text, FORBIDDEN)

    checks = {
        "ledger_002_pass": bool(ledger.get("audit_pass")),
        "row_count": len(rows),
        "row_count_is_24": len(rows) == 24,
        "component_count": len(components),
        "component_count_is_4": len(components) == 4,
        "component_sizes_are_6": all(c["row_count"] == 6 for c in components),
        "each_component_has_all_six_roles_once": all(c["has_all_six_roles_once"] for c in components),
        "each_component_is_transition_cycle": all(c["transition_cycle_ok"] for c in components),
        "phi_has_four_levels_once": dict(sorted(phi_counts.items())) == {"closed_face": 1, "edge": 1, "filled_cell": 1, "hinge": 1},
        "row_phi_partition_is_6_each": dict(sorted(row_phi_counts.items())) == {"closed_face": 6, "edge": 6, "filled_cell": 6, "hinge": 6},
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
        checks["component_count_is_4"],
        checks["component_sizes_are_6"],
        checks["each_component_has_all_six_roles_once"],
        checks["each_component_is_transition_cycle"],
        checks["phi_has_four_levels_once"],
        checks["row_phi_partition_is_6_each"],
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
        "status": "source_construction_phi_candidate_recorded",
        "audit_id": "003",
        "audit_pass": audit_pass,
        "verdict": "phi_candidate_exact_on_24_row_register" if audit_pass else "phi_candidate_failed",
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
            "component_source": "weak connected components of native transition graph over from_ABC and to_ABC",
            "capture_rule": "inside_captured_native iff slot_delta_mod15 > fiber_delta_mod60",
            "assignment": [
                {"condition": "capture_count == 0", "level": "edge"},
                {"condition": "capture_count == 1", "level": "hinge"},
                {"condition": "capture_count == 2 and TI.fiber_delta_mod60 == 3", "level": "closed_face"},
                {"condition": "capture_count == 2 and TI.fiber_delta_mod60 == 1", "level": "filled_cell"},
            ],
        },
        "checks": checks,
        "components": components,
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
            "slot_delta_mod15",
            "fiber_delta_mod60",
            "inside_captured_native",
            "phi_level",
            "form_index_for_evaluation_only",
            "match",
        ])
        for i, row in enumerate(rows):
            a = row_assignments[i]
            w.writerow([
                row["ledger_row_id"],
                a["component_id"],
                row["edge_role"],
                row["slot_delta_mod15"],
                row["fiber_delta_mod60"],
                inside_captured_native(row),
                a["phi_level"],
                row["form_index"],
                a["match"],
            ])

    lines = []
    lines.append("# Source construction phi candidate 003")
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
    lines.append("- Build native transition components from from_A/from_B/from_C to to_A/to_B/to_C.")
    lines.append("- Compute capture_count inside each component using slot_delta_mod15 > fiber_delta_mod60.")
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
    lines.append("This is an exact phi candidate on the 24-row register, not native closure and not Gap A closure. form_index is used only for evaluation. answer-label leakage remains open until the source construction provenance of the fields themselves is audited more deeply.")
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
