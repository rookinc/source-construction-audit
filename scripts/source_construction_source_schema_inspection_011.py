#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

IN_010 = ROOT / "artifacts/json/source_construction_phi_source_provenance_inventory_010.v1.json"
IN_ROWS = ROOT / "artifacts/csv/source_construction_phi_label_removed_rows_007.v1.csv"
SOURCE_JSON = ROOT / "source/project24/g60_native_overlay_generator_family_search_001.v1.json"

OUT_JSON = ROOT / "artifacts/json/source_construction_source_schema_inspection_011.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_source_schema_inspection_011.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_source_schema_inspection_011.md"

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

RISK_FIELDS = [
    "form_index",
    "ledger_row_id",
]

REQUIRED = [
    "source schema inspection",
    "edge_records",
    "phi-ready layer",
    "source replay remains open",
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


def read_csv_rows(path):
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
    return v


def signature_from_mapping(row):
    sig = {}
    for f in PHI_FIELDS:
        sig[f] = as_int(row.get(f))
    return json.dumps(sig, sort_keys=True, separators=(",", ":"))


def walk(obj, path="$"):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + "[" + str(i) + "]")


def top_profile(data):
    rows = []
    if not isinstance(data, dict):
        return rows
    for k, v in data.items():
        if isinstance(v, list):
            kind = "list"
            size = len(v)
            sample_type = type(v[0]).__name__ if v else "empty"
        elif isinstance(v, dict):
            kind = "dict"
            size = len(v)
            sample_type = "dict"
        else:
            kind = type(v).__name__
            size = None
            sample_type = type(v).__name__
        rows.append({
            "path": "$." + str(k),
            "kind": kind,
            "size": size,
            "sample_type": sample_type,
        })
    return rows


def list_profiles(data, target_sigs):
    profiles = []

    for path, obj in walk(data):
        if not isinstance(obj, list):
            continue

        dict_items = [(i, x) for i, x in enumerate(obj) if isinstance(x, dict)]
        union_keys = sorted({k for _, x in dict_items for k in x.keys()})
        phi_hits = sorted(set(union_keys).intersection(PHI_FIELDS))
        risk_hits = sorted(set(union_keys).intersection(RISK_FIELDS))

        complete_records = []
        target_matches = 0
        exact_sigs = Counter()

        for i, item in dict_items:
            if all(f in item for f in PHI_FIELDS):
                sig = signature_from_mapping(item)
                complete_records.append({
                    "index": i,
                    "path": path + "[" + str(i) + "]",
                    "signature": sig,
                    "risk_fields_present": sorted(set(item.keys()).intersection(RISK_FIELDS)),
                })
                exact_sigs[sig] += 1
                if sig in target_sigs:
                    target_matches += 1

        profiles.append({
            "path": path,
            "list_count": len(obj),
            "dict_item_count": len(dict_items),
            "union_key_count": len(union_keys),
            "union_keys_top": union_keys[:80],
            "phi_field_hit_count": len(phi_hits),
            "phi_field_hits": phi_hits,
            "risk_field_hits": risk_hits,
            "complete_phi_record_count": len(complete_records),
            "target_signature_match_count": target_matches,
            "complete_records_top": complete_records[:20],
            "duplicate_complete_signature_count": sum(1 for _, n in exact_sigs.items() if n > 1),
        })

    profiles.sort(key=lambda x: (
        -x["complete_phi_record_count"],
        -x["phi_field_hit_count"],
        -x["dict_item_count"],
        x["path"],
    ))
    return profiles


def dict_complete_records(data, target_sigs):
    records = []
    for path, obj in walk(data):
        if not isinstance(obj, dict):
            continue
        if all(f in obj for f in PHI_FIELDS):
            sig = signature_from_mapping(obj)
            records.append({
                "path": path,
                "signature": sig,
                "matches_target": sig in target_sigs,
                "risk_fields_present": sorted(set(obj.keys()).intersection(RISK_FIELDS)),
            })
    return records


def summarize_scalar_fields(data):
    counts = Counter()
    paths = defaultdict(list)

    for path, obj in walk(data):
        if isinstance(obj, dict):
            for f in PHI_FIELDS + RISK_FIELDS:
                if f in obj:
                    counts[f] += 1
                    if len(paths[f]) < 10:
                        paths[f].append(path + "." + f)

    return {
        "counts": dict(sorted(counts.items())),
        "paths": {k: v for k, v in sorted(paths.items())},
    }


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    a010 = load_json(IN_010)
    source = load_json(SOURCE_JSON)
    target_rows = read_csv_rows(IN_ROWS)
    target_sigs = set(signature_from_mapping(r) for r in target_rows)

    top = top_profile(source)
    lists = list_profiles(source, target_sigs)
    complete = dict_complete_records(source, target_sigs)
    scalar = summarize_scalar_fields(source)

    edge_records = source.get("edge_records", [])
    edge_record_count = len(edge_records) if isinstance(edge_records, list) else 0
    edge_complete_count = 0
    edge_target_match_count = 0

    if isinstance(edge_records, list):
        for r in edge_records:
            if isinstance(r, dict) and all(f in r for f in PHI_FIELDS):
                edge_complete_count += 1
                if signature_from_mapping(r) in target_sigs:
                    edge_target_match_count += 1

    exact_outside_edge_records = [
        r for r in complete
        if not r["path"].startswith("$.edge_records[")
    ]

    phi_layers = [
        p for p in lists
        if p["phi_field_hit_count"] > 0 or p["complete_phi_record_count"] > 0
    ]

    full_target_layers = [
        p for p in lists
        if p["target_signature_match_count"] == len(target_sigs)
    ]

    non_edge_full_target_layers = [
        p for p in full_target_layers
        if p["path"] != "$.edge_records"
    ]

    edge_records_are_first_phi_ready_layer = (
        edge_record_count == 24
        and edge_complete_count == 24
        and edge_target_match_count == 24
        and len(exact_outside_edge_records) == 0
        and len(non_edge_full_target_layers) == 0
    )

    statement = (
        "Artifact 011 is a source schema inspection of the imported source file. "
        "It checks whether edge_records are the first available phi-ready layer for source-construction phi. "
        "The inspection supports that source replay remains open: the imported file exposes phi-ready edge_records, "
        "but does not itself prove how those edge_records are generated from deeper native construction. "
        "answer-label leakage remains open at the construction-origin level. "
        "This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    miss = missing(statement, REQUIRED)
    forb = found(statement, FORBIDDEN)

    checks = {
        "input_010_pass": bool(a010.get("audit_pass")),
        "source_json_exists": SOURCE_JSON.exists(),
        "target_signature_count": len(target_sigs),
        "target_signature_count_is_24": len(target_sigs) == 24,
        "edge_records_is_list": isinstance(edge_records, list),
        "edge_record_count": edge_record_count,
        "edge_record_count_is_24": edge_record_count == 24,
        "edge_complete_phi_record_count": edge_complete_count,
        "edge_complete_phi_record_count_is_24": edge_complete_count == 24,
        "edge_target_signature_match_count": edge_target_match_count,
        "edge_target_signature_match_count_is_24": edge_target_match_count == 24,
        "complete_phi_record_total_count": len(complete),
        "complete_phi_records_outside_edge_records_count": len(exact_outside_edge_records),
        "no_complete_phi_records_outside_edge_records": len(exact_outside_edge_records) == 0,
        "full_target_layers_count": len(full_target_layers),
        "non_edge_full_target_layers_count": len(non_edge_full_target_layers),
        "edge_records_are_first_phi_ready_layer_in_imported_file": edge_records_are_first_phi_ready_layer,
        "source_replay": False,
        "source_replay_remains_open": True,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(miss) == 0,
        "forbidden_phrases_absent": len(forb) == 0,
    }

    audit_pass = all([
        checks["input_010_pass"],
        checks["source_json_exists"],
        checks["target_signature_count_is_24"],
        checks["edge_records_is_list"],
        checks["edge_record_count_is_24"],
        checks["edge_complete_phi_record_count_is_24"],
        checks["edge_target_signature_match_count_is_24"],
        checks["source_replay"] is False,
        checks["source_replay_remains_open"],
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    if edge_records_are_first_phi_ready_layer:
        verdict = "edge_records_first_phi_ready_layer_in_imported_source"
    else:
        verdict = "source_schema_contains_additional_phi_ready_layers"

    result = {
        "status": "source_construction_source_schema_inspection_recorded",
        "audit_id": "011",
        "audit_pass": audit_pass,
        "verdict": verdict if audit_pass else "source_schema_inspection_failed",
        "statement": statement,
        "inputs": {
            "source_provenance_inventory_010": str(IN_010.relative_to(ROOT)),
            "label_removed_rows_007": str(IN_ROWS.relative_to(ROOT)),
            "source_json": str(SOURCE_JSON.relative_to(ROOT)),
        },
        "checks": checks,
        "top_level_profile": top,
        "list_profiles": lists,
        "phi_layers": phi_layers,
        "full_target_layers": full_target_layers,
        "non_edge_full_target_layers": non_edge_full_target_layers,
        "exact_phi_records_outside_edge_records_top": exact_outside_edge_records[:20],
        "scalar_field_summary": scalar,
        "boundary": {
            "schema_inspection_only": True,
            "edge_records_phi_ready": True,
            "source_replay": False,
            "source_replay_remains_open": True,
            "answer_label_leakage_remains_open": True,
            "native_closure": False,
            "gap_a_closure": False,
            "full_role_labeled_shared_B_universe_derived": False,
        },
        "missing_required_phrases": miss,
        "forbidden_phrases_found": forb,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTE.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "path",
            "list_count",
            "dict_item_count",
            "phi_field_hit_count",
            "phi_field_hits",
            "risk_field_hits",
            "complete_phi_record_count",
            "target_signature_match_count",
        ])
        for p in lists:
            w.writerow([
                p["path"],
                p["list_count"],
                p["dict_item_count"],
                p["phi_field_hit_count"],
                "|".join(p["phi_field_hits"]),
                "|".join(p["risk_field_hits"]),
                p["complete_phi_record_count"],
                p["target_signature_match_count"],
            ])

    lines = []
    lines.append("# Source construction source schema inspection 011")
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
    lines.append("## Phi-ready layers")
    lines.append("")
    if phi_layers:
        for p in phi_layers[:20]:
            lines.append("- " + p["path"] + ": phi_hits=" + str(p["phi_field_hit_count"]) + ", complete_phi_records=" + str(p["complete_phi_record_count"]) + ", target_matches=" + str(p["target_signature_match_count"]))
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if edge_records_are_first_phi_ready_layer:
        lines.append("The imported source file exposes `edge_records` as the first available phi-ready layer found by this inspection. No complete nine-field phi records were found outside `edge_records`.")
    else:
        lines.append("The imported source file contains additional phi-ready or target-matching layers. Inspect the JSON artifact before treating `edge_records` as first available.")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This is a source schema inspection only. It does not replay edge_records from deeper native construction. It does not prove native closure, does not close Gap A, and does not derive the full role-labeled shared_B universe. answer-label leakage remains open at the construction-origin level.")
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
