#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

IN_SEED = ROOT / "artifacts/json/project25_seed_from_project24_handoff_001.v1.json"
IN_SOURCE = ROOT / "source/project24/g60_native_overlay_generator_family_search_001.v1.json"

OUT_JSON = ROOT / "artifacts/json/source_construction_ledger_inventory_002.v1.json"
OUT_FIELDS = ROOT / "artifacts/csv/source_construction_ledger_inventory_002_fields.v1.csv"
OUT_ROWS = ROOT / "artifacts/csv/source_construction_ledger_inventory_002_rows.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_ledger_inventory_002.md"

LABEL_TOKENS = [
    "form_index",
    "formindex",
    "form",
    "state",
    "selected",
    "answer",
    "target",
    "label",
    "candidate",
    "rank",
    "completion",
    "c_row",
    "crow",
]

ORDER_TOKENS = [
    "record_index",
    "_record_index",
    "row_index",
    "rowid",
    "row_id",
    "index",
    "ordinal",
    "position",
    "order",
]

DOWNSTREAM_TOKENS = [
    "expected",
    "observed",
    "actual",
    "project22",
    "project23",
    "selected",
    "diagonal",
    "readout",
]

REQUIRED = [
    "source construction ledger inventory",
    "allowed construction fields",
    "evaluation fields",
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


def as_int(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v.strip())
    return None


def scalar(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        iv = as_int(v)
        return iv if iv is not None else v
    if isinstance(v, str) and len(v) <= 100:
        iv = as_int(v)
        return iv if iv is not None else v
    return None


def flatten(obj, prefix=""):
    out = {}
    if not isinstance(obj, dict):
        return out
    for k, v in obj.items():
        key = prefix + str(k)
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        elif isinstance(v, (list, tuple)):
            vals = [as_int(x) for x in v]
            vals = [x for x in vals if x is not None]
            if vals and len(vals) == len(v) and len(vals) <= 60:
                out[key + ".__len"] = len(vals)
                out[key + ".__sum"] = sum(vals)
                out[key + ".__min"] = min(vals)
                out[key + ".__max"] = max(vals)
                out[key + ".__range"] = max(vals) - min(vals)
                out[key + ".__set"] = "|".join(str(x) for x in sorted(set(vals)))
        else:
            sv = scalar(v)
            if sv is not None:
                out[key] = sv
    return out


def find_edge_records(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("edge_records"), list):
            xs = obj["edge_records"]
            if all(isinstance(x, dict) for x in xs):
                return xs, ["edge_records"]
        for k, v in obj.items():
            found, path = find_edge_records(v)
            if found is not None:
                return found, [k] + path
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found, path = find_edge_records(v)
            if found is not None:
                return found, [i] + path
    return None, []


def get_suffix(features, name):
    if name in features:
        return features[name]
    hits = [v for k, v in features.items() if k.endswith("." + name)]
    if len(hits) == 1:
        return hits[0]
    return None


def has_token(name, tokens):
    n = name.lower()
    return any(t in n for t in tokens)


def classify_field(name):
    if has_token(name, LABEL_TOKENS):
        return "evaluation_or_label_risk"
    if has_token(name, ORDER_TOKENS):
        return "order_leakage_risk"
    if has_token(name, DOWNSTREAM_TOKENS):
        return "downstream_answer_risk"
    if name.startswith("derived."):
        return "derived_arithmetic"
    if "delta" in name.lower():
        return "native_delta_or_transition"
    return "source_provenance_candidate"


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    seed = load_json(IN_SEED)
    source = load_json(IN_SOURCE)

    records, path = find_edge_records(source)
    if not records:
        raise SystemExit("edge_records not found")

    rows = []
    for i, rec in enumerate(records):
        f = flatten(rec)
        from_c = as_int(get_suffix(f, "from_C"))
        to_c = as_int(get_suffix(f, "to_C"))
        slot = as_int(get_suffix(f, "slot_delta_mod15"))
        fiber = as_int(get_suffix(f, "fiber_delta_mod60"))

        if from_c is not None and to_c is not None:
            f["derived.C_delta_mod15"] = (to_c - from_c) % 15
            f["derived.C_transition"] = str(from_c) + "->" + str(to_c)
            for m in [2, 3, 4, 5, 6]:
                f["derived.C_delta_mod15_mod_" + str(m)] = ((to_c - from_c) % 15) % m

        if slot is not None and fiber is not None:
            f["derived.boundary_gap"] = slot - fiber
            f["derived.boundary_gap_sign"] = "neg" if slot - fiber < 0 else ("zero" if slot - fiber == 0 else "pos")
            f["derived.inside_captured"] = "yes" if slot - fiber > 0 else "no"

        form_index = as_int(get_suffix(f, "form_index"))
        rows.append({
            "ledger_row_id": i,
            "form_index_for_evaluation_only": form_index,
            "features": f,
        })

    all_fields = sorted({k for r in rows for k in r["features"].keys()})
    field_rows = []
    for field in all_fields:
        vals = [r["features"].get(field) for r in rows]
        present_count = sum(v is not None for v in vals)
        uniq = sorted(set(str(v) for v in vals if v is not None))
        kind = classify_field(field)
        field_rows.append({
            "field": field,
            "classification": kind,
            "present_count": present_count,
            "unique_count": len(uniq),
            "sample_values": uniq[:20],
            "allowed_for_phi": kind in [
                "source_provenance_candidate",
                "native_delta_or_transition",
                "derived_arithmetic",
            ],
            "leakage_risk": kind in [
                "evaluation_or_label_risk",
                "order_leakage_risk",
                "downstream_answer_risk",
            ],
        })

    class_counts = Counter(x["classification"] for x in field_rows)
    allowed_fields = [x["field"] for x in field_rows if x["allowed_for_phi"]]
    blocked_fields = [x["field"] for x in field_rows if x["leakage_risk"]]

    compact_fields = [
        "edge_role",
        "from_A",
        "from_B",
        "from_C",
        "from_slot",
        "from_fiber",
        "to_A",
        "to_B",
        "to_C",
        "to_slot",
        "to_fiber",
        "slot_delta_mod15",
        "fiber_delta_mod60",
        "derived.C_delta_mod15",
        "derived.boundary_gap",
        "derived.boundary_gap_sign",
        "derived.inside_captured",
        "form_index",
    ]

    statement = (
        "Artifact 002 is a source construction ledger inventory. It exports the 24-row register, "
        "classifies allowed construction fields and evaluation fields, and preserves that answer-label leakage remains open. "
        "This is not native closure and not Gap A closure."
    )

    gate_text = statement + "\nallowed construction fields\nevaluation fields\nanswer-label leakage remains open\n"
    missing_required = missing(gate_text, REQUIRED)
    forbidden_found = found(gate_text, FORBIDDEN)

    checks = {
        "seed_001_pass": bool(seed.get("audit_pass")),
        "source_exists": IN_SOURCE.exists(),
        "edge_records_found": True,
        "row_count": len(rows),
        "row_count_is_24": len(rows) == 24,
        "field_count": len(field_rows),
        "allowed_field_count": len(allowed_fields),
        "blocked_field_count": len(blocked_fields),
        "required_phrases_present": len(missing_required) == 0,
        "forbidden_phrases_absent": len(forbidden_found) == 0,
    }

    audit_pass = all([
        checks["seed_001_pass"],
        checks["source_exists"],
        checks["edge_records_found"],
        checks["row_count_is_24"],
        checks["allowed_field_count"] > 0,
        checks["blocked_field_count"] > 0,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_ledger_inventory_recorded",
        "audit_id": "002",
        "audit_pass": audit_pass,
        "verdict": "source_construction_ledger_ready" if audit_pass else "source_construction_ledger_failed",
        "statement": statement,
        "inputs": {
            "project25_seed_001": str(IN_SEED.relative_to(ROOT)),
            "edge_records_source": str(IN_SOURCE.relative_to(ROOT)),
            "edge_records_path": path,
        },
        "checks": checks,
        "field_class_counts": dict(sorted(class_counts.items())),
        "allowed_fields_for_phi": allowed_fields,
        "blocked_fields_for_phi": blocked_fields,
        "compact_register_fields": compact_fields,
        "field_inventory": field_rows,
        "missing_required_phrases": missing_required,
        "forbidden_phrases_found": forbidden_found,
        "boundary": {
            "form_index_for_evaluation_only": True,
            "answer_label_leakage_remains_open": True,
            "native_four_form_partition_proven": False,
            "native_closure": False,
            "gap_a_closure": False,
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_FIELDS.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROWS.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTE.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with OUT_FIELDS.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["field", "classification", "present_count", "unique_count", "allowed_for_phi", "leakage_risk", "sample_values"])
        for x in field_rows:
            w.writerow([
                x["field"],
                x["classification"],
                x["present_count"],
                x["unique_count"],
                x["allowed_for_phi"],
                x["leakage_risk"],
                "|".join(x["sample_values"]),
            ])

    with OUT_ROWS.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        header = ["ledger_row_id"] + compact_fields
        w.writerow(header)
        for r in rows:
            fts = r["features"]
            w.writerow([r["ledger_row_id"]] + [fts.get(k, "") for k in compact_fields])

    lines = []
    lines.append("# Source construction ledger inventory 002")
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
    lines.append("## Field class counts")
    lines.append("")
    for k, v in sorted(class_counts.items()):
        lines.append("- " + k + ": `" + str(v) + "`")
    lines.append("")
    lines.append("## Outputs")
    lines.append("")
    lines.append("- field inventory CSV: `" + str(OUT_FIELDS.relative_to(ROOT)) + "`")
    lines.append("- 24-row register CSV: `" + str(OUT_ROWS.relative_to(ROOT)) + "`")
    lines.append("- ledger JSON: `" + str(OUT_JSON.relative_to(ROOT)) + "`")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("form_index is for evaluation only. The source construction audit must derive phi without form_index, row order, target labels, or downstream answer labels. answer-label leakage remains open. This is not native closure and not Gap A closure.")
    lines.append("")

    OUT_NOTE.write_text("\n".join(lines), encoding="utf-8")

    print("wrote", OUT_JSON)
    print("wrote", OUT_FIELDS)
    print("wrote", OUT_ROWS)
    print("wrote", OUT_NOTE)
    print("status", result["status"])
    print("audit_pass", audit_pass)
    print("verdict", result["verdict"])
    for k, v in checks.items():
        print(k, v)
    print("field_class_counts", dict(sorted(class_counts.items())))
    print("allowed_field_count", len(allowed_fields))
    print("blocked_field_count", len(blocked_fields))


if __name__ == "__main__":
    main()
