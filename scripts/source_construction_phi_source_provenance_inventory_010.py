#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

IN_009 = ROOT / "artifacts/json/source_construction_phi_theorem_candidate_009.v1.json"
IN_ROWS = ROOT / "artifacts/csv/source_construction_phi_label_removed_rows_007.v1.csv"
SOURCE_DIR = ROOT / "source"

OUT_JSON = ROOT / "artifacts/json/source_construction_phi_source_provenance_inventory_010.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_phi_source_provenance_inventory_010.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_phi_source_provenance_inventory_010.md"

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
    "source-provenance inventory",
    "source-construction phi",
    "source directory",
    "phi fields",
    "label fields are not used for matching",
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


def canonical_signature_from_row(row):
    sig = {}
    for f in PHI_FIELDS:
        sig[f] = as_int(row.get(f))
    return json.dumps(sig, sort_keys=True, separators=(",", ":"))


def scalarish(v):
    return isinstance(v, (str, int, float, bool)) or v is None


def walk(obj, path="$"):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + "[" + str(i) + "]")


def scan_json_file(path):
    data = load_json(path)

    field_counts = Counter()
    risk_counts = Counter()
    field_paths = defaultdict(list)
    candidate_records = []
    exact_records = []

    for obj_path, obj in walk(data):
        if not isinstance(obj, dict):
            continue

        keys = set(obj.keys())
        phi_hits = sorted(keys.intersection(PHI_FIELDS))
        risk_hits = sorted(keys.intersection(RISK_FIELDS))

        for f in phi_hits:
            field_counts[f] += 1
            if len(field_paths[f]) < 10:
                field_paths[f].append(obj_path + "." + f)

        for f in risk_hits:
            risk_counts[f] += 1

        if phi_hits:
            candidate_records.append({
                "path": obj_path,
                "hit_count": len(phi_hits),
                "fields": phi_hits,
                "risk_fields_present": risk_hits,
            })

        if all(f in obj for f in PHI_FIELDS):
            sig_row = {f: obj.get(f) for f in PHI_FIELDS}
            exact_records.append({
                "path": obj_path,
                "signature": canonical_signature_from_row(sig_row),
                "risk_fields_present": risk_hits,
            })

    return {
        "file": str(path.relative_to(ROOT)),
        "field_counts": dict(sorted(field_counts.items())),
        "risk_counts": dict(sorted(risk_counts.items())),
        "field_paths": {k: v for k, v in sorted(field_paths.items())},
        "candidate_record_count": len(candidate_records),
        "candidate_records_top": sorted(candidate_records, key=lambda x: (-x["hit_count"], x["path"]))[:25],
        "exact_record_count": len(exact_records),
        "exact_records": exact_records,
    }


def missing(text, phrases):
    return [p for p in phrases if p not in text]


def found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    a009 = load_json(IN_009)
    target_rows = read_csv_rows(IN_ROWS)
    target_sigs = [canonical_signature_from_row(r) for r in target_rows]
    target_sig_counts = Counter(target_sigs)

    json_files = sorted(SOURCE_DIR.rglob("*.json"))
    scans = []

    for path in json_files:
        try:
            scans.append(scan_json_file(path))
        except Exception as exc:
            scans.append({
                "file": str(path.relative_to(ROOT)),
                "error": repr(exc),
                "field_counts": {},
                "risk_counts": {},
                "field_paths": {},
                "candidate_record_count": 0,
                "candidate_records_top": [],
                "exact_record_count": 0,
                "exact_records": [],
            })

    field_file_hits = {f: [] for f in PHI_FIELDS}
    total_field_counts = Counter()
    total_risk_counts = Counter()
    all_exact = []

    for scan in scans:
        for f, n in scan.get("field_counts", {}).items():
            total_field_counts[f] += n
            if n > 0:
                field_file_hits[f].append(scan["file"])
        for f, n in scan.get("risk_counts", {}).items():
            total_risk_counts[f] += n
        for rec in scan.get("exact_records", []):
            all_exact.append({
                "file": scan["file"],
                **rec,
            })

    source_sig_counts = Counter(rec["signature"] for rec in all_exact)
    matched_sig_count = sum(1 for s in target_sig_counts if source_sig_counts.get(s, 0) > 0)
    missing_target_sigs = [s for s in target_sig_counts if source_sig_counts.get(s, 0) == 0]
    duplicate_source_sigs = {k: v for k, v in source_sig_counts.items() if v > 1}

    all_phi_fields_seen = all(total_field_counts.get(f, 0) > 0 for f in PHI_FIELDS)
    all_target_sigs_found = len(missing_target_sigs) == 0

    statement = (
        "Artifact 010 is a source-provenance inventory for source-construction phi. "
        "It scans the source directory for the phi fields and compares source-side signatures without using label fields. "
        "label fields are not used for matching. answer-label leakage remains open because this is an inventory, "
        "not a replay from native construction. This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    miss = missing(statement, REQUIRED)
    forb = found(statement, FORBIDDEN)

    checks = {
        "input_009_pass": bool(a009.get("audit_pass")),
        "source_directory_exists": SOURCE_DIR.exists(),
        "source_json_file_count": len(json_files),
        "source_json_file_count_positive": len(json_files) > 0,
        "target_row_count": len(target_rows),
        "target_row_count_is_24": len(target_rows) == 24,
        "phi_field_count": len(PHI_FIELDS),
        "all_phi_fields_seen_in_source": all_phi_fields_seen,
        "exact_nine_field_source_record_count": len(all_exact),
        "target_signature_count": len(target_sig_counts),
        "matched_target_signature_count": matched_sig_count,
        "all_target_signatures_found_in_exact_source_records": all_target_sigs_found,
        "label_fields_are_not_used_for_matching": True,
        "form_index_used_for_matching": False,
        "ledger_row_id_used_for_matching": False,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(miss) == 0,
        "forbidden_phrases_absent": len(forb) == 0,
    }

    audit_pass = all([
        checks["input_009_pass"],
        checks["source_directory_exists"],
        checks["source_json_file_count_positive"],
        checks["target_row_count_is_24"],
        checks["all_phi_fields_seen_in_source"],
        checks["label_fields_are_not_used_for_matching"],
        checks["form_index_used_for_matching"] is False,
        checks["ledger_row_id_used_for_matching"] is False,
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    verdict = "source_provenance_inventory_recorded"
    if all_target_sigs_found:
        verdict = "source_provenance_inventory_exact_signatures_found"

    result = {
        "status": "source_construction_phi_source_provenance_inventory_recorded",
        "audit_id": "010",
        "audit_pass": audit_pass,
        "verdict": verdict if audit_pass else "source_provenance_inventory_failed",
        "statement": statement,
        "inputs": {
            "theorem_candidate_009": str(IN_009.relative_to(ROOT)),
            "label_removed_rows_007": str(IN_ROWS.relative_to(ROOT)),
            "source_directory": str(SOURCE_DIR.relative_to(ROOT)),
        },
        "phi_fields": PHI_FIELDS,
        "risk_fields": RISK_FIELDS,
        "checks": checks,
        "field_file_hits": field_file_hits,
        "total_field_counts": dict(sorted(total_field_counts.items())),
        "total_risk_counts": dict(sorted(total_risk_counts.items())),
        "source_files": [str(p.relative_to(ROOT)) for p in json_files],
        "file_scans": scans,
        "exact_source_record_locations_top": all_exact[:50],
        "missing_target_signatures": missing_target_sigs[:20],
        "duplicate_source_signatures": duplicate_source_sigs,
        "boundary": {
            "inventory_only": True,
            "source_replay": False,
            "native_closure": False,
            "gap_a_closure": False,
            "answer_label_leakage_remains_open": True,
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
            "file",
            "field",
            "count",
            "field_seen",
            "example_paths",
        ])
        for scan in scans:
            for f in PHI_FIELDS:
                count = scan.get("field_counts", {}).get(f, 0)
                paths = scan.get("field_paths", {}).get(f, [])
                w.writerow([
                    scan["file"],
                    f,
                    count,
                    count > 0,
                    " | ".join(paths[:3]),
                ])

    lines = []
    lines.append("# Source construction phi source-provenance inventory 010")
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
    lines.append("## Field hits")
    lines.append("")
    for f in PHI_FIELDS:
        lines.append("- " + f + ": `" + str(total_field_counts.get(f, 0)) + "`")
    lines.append("")
    lines.append("## Source files")
    lines.append("")
    for p in json_files:
        lines.append("- " + str(p.relative_to(ROOT)))
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This is an inventory only. It locates phi fields and exact source-side signatures where present, but it does not replay the 24-row register from native construction. It does not prove native closure, does not close Gap A, and does not derive the full role-labeled shared_B universe. answer-label leakage remains open at the deeper construction-origin level.")
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
    print("total_field_counts", dict(sorted(total_field_counts.items())))
    print("total_risk_counts", dict(sorted(total_risk_counts.items())))


if __name__ == "__main__":
    main()
