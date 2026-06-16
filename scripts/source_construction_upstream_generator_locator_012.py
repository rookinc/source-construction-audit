#!/usr/bin/env python3
import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent

IN_011 = ROOT / "artifacts/json/source_construction_source_schema_inspection_011.v1.json"

TARGET_BASENAME = "g60_native_overlay_generator_family_search_001.v1.json"
TARGET_STEM = "g60_native_overlay_generator_family_search_001"

OUT_JSON = ROOT / "artifacts/json/source_construction_upstream_generator_locator_012.v1.json"
OUT_CSV = ROOT / "artifacts/csv/source_construction_upstream_generator_locator_012.v1.csv"
OUT_NOTE = ROOT / "notes/source_construction_upstream_generator_locator_012.md"

TEXT_SUFFIXES = {
    ".py", ".sh", ".md", ".txt", ".tex", ".json", ".csv", ".yaml", ".yml"
}

SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".venv", "node_modules", "dist", "_repo_backups"
}

PHI_TERMS = [
    "edge_records",
    "edge_role",
    "from_A",
    "from_B",
    "from_C",
    "to_A",
    "to_B",
    "to_C",
    "slot_delta_mod15",
    "fiber_delta_mod60",
    "form_index",
]

REQUIRED = [
    "upstream generator locator",
    "source-construction phi",
    "edge_records",
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


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_text_candidate(path):
    return path.suffix in TEXT_SUFFIXES


def safe_read(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def rel(path):
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        try:
            return str(path.relative_to(WORKSPACE))
        except Exception:
            return str(path)


def walk_files(base):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def classify_path(path):
    s = str(path)
    if "/25-source-construction-audit/source/" in s:
        return "project25_imported_source_copy"
    if "/25-source-construction-audit/" in s:
        return "project25_artifact_or_script"
    if "/24-native-local-cell-provenance/" in s:
        return "project24_candidate_origin"
    return "workspace_other"


def line_hits(text, terms, limit=8):
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        if any(t in line for t in terms):
            out.append({"line": i, "text": line[:240]})
            if len(out) >= limit:
                break
    return out


def phrase_missing(text, phrases):
    return [p for p in phrases if p not in text]


def phrase_found(text, phrases):
    return [p for p in phrases if p in text]


def main():
    a011 = load_json(IN_011)

    exact_files = []
    text_refs = []
    phi_term_files = []

    for path in walk_files(WORKSPACE):
        if path.name == TARGET_BASENAME:
            exact_files.append({
                "path": rel(path),
                "absolute_path": str(path),
                "class": classify_path(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })

        if not is_text_candidate(path):
            continue

        text = safe_read(path)
        if not text:
            continue

        ref_terms = []
        if TARGET_BASENAME in text:
            ref_terms.append("target_basename")
        if TARGET_STEM in text:
            ref_terms.append("target_stem")

        if ref_terms:
            text_refs.append({
                "path": rel(path),
                "absolute_path": str(path),
                "class": classify_path(path),
                "suffix": path.suffix,
                "ref_terms": ref_terms,
                "hits": line_hits(text, [TARGET_BASENAME, TARGET_STEM], limit=12),
            })

        phi_hits = [t for t in PHI_TERMS if t in text]
        if len(phi_hits) >= 6:
            phi_term_files.append({
                "path": rel(path),
                "absolute_path": str(path),
                "class": classify_path(path),
                "suffix": path.suffix,
                "phi_hit_count": len(phi_hits),
                "phi_hits": phi_hits,
                "hits": line_hits(text, phi_hits, limit=10),
            })

    exact_outside_project25_copy = [
        x for x in exact_files
        if x["class"] != "project25_imported_source_copy"
    ]

    script_refs = [
        x for x in text_refs
        if x["suffix"] in [".py", ".sh"]
    ]

    project24_exact = [
        x for x in exact_files
        if x["class"] == "project24_candidate_origin"
    ]

    project24_script_refs = [
        x for x in script_refs
        if x["class"] == "project24_candidate_origin"
    ]

    project24_phi_term_files = [
        x for x in phi_term_files
        if x["class"] == "project24_candidate_origin"
    ]

    statement = (
        "Artifact 012 is an upstream generator locator for source-construction phi. "
        "It searches the workspace for the imported edge_records source file and likely generating references. "
        "source replay remains open because locating files and references is not the same as replaying edge_records from native construction. "
        "answer-label leakage remains open at the construction-origin level. "
        "This is not native closure, not full role-labeled shared_B universe derivation, and not Gap A closure."
    )

    missing = phrase_missing(statement, REQUIRED)
    forbidden = phrase_found(statement, FORBIDDEN)

    checks = {
        "input_011_pass": bool(a011.get("audit_pass")),
        "workspace_exists": WORKSPACE.exists(),
        "target_basename": TARGET_BASENAME,
        "exact_file_count": len(exact_files),
        "exact_file_count_positive": len(exact_files) > 0,
        "exact_outside_project25_copy_count": len(exact_outside_project25_copy),
        "project24_exact_file_count": len(project24_exact),
        "text_reference_count": len(text_refs),
        "script_reference_count": len(script_refs),
        "project24_script_reference_count": len(project24_script_refs),
        "project24_phi_term_file_count": len(project24_phi_term_files),
        "source_replay": False,
        "source_replay_remains_open": True,
        "answer_label_leakage_remains_open": True,
        "native_closure": False,
        "gap_a_closure": False,
        "required_phrases_present": len(missing) == 0,
        "forbidden_phrases_absent": len(forbidden) == 0,
    }

    if project24_script_refs:
        verdict = "project24_generator_reference_candidates_found"
    elif project24_exact:
        verdict = "project24_exact_source_file_found_without_generator_reference"
    elif exact_outside_project25_copy:
        verdict = "workspace_exact_source_file_found_outside_import_copy"
    else:
        verdict = "only_imported_source_copy_found"

    audit_pass = all([
        checks["input_011_pass"],
        checks["workspace_exists"],
        checks["exact_file_count_positive"],
        checks["source_replay"] is False,
        checks["source_replay_remains_open"],
        checks["answer_label_leakage_remains_open"],
        checks["native_closure"] is False,
        checks["gap_a_closure"] is False,
        checks["required_phrases_present"],
        checks["forbidden_phrases_absent"],
    ])

    result = {
        "status": "source_construction_upstream_generator_locator_recorded",
        "audit_id": "012",
        "audit_pass": audit_pass,
        "verdict": verdict if audit_pass else "upstream_generator_locator_failed",
        "statement": statement,
        "inputs": {
            "source_schema_inspection_011": str(IN_011.relative_to(ROOT)),
            "workspace": str(WORKSPACE),
            "target_basename": TARGET_BASENAME,
        },
        "checks": checks,
        "exact_files": exact_files,
        "exact_files_outside_project25_import_copy": exact_outside_project25_copy,
        "text_references": text_refs[:100],
        "script_references": script_refs[:100],
        "phi_term_files": sorted(phi_term_files, key=lambda x: (-x["phi_hit_count"], x["path"]))[:100],
        "project24_candidates": {
            "exact_files": project24_exact,
            "script_references": project24_script_refs,
            "phi_term_files": project24_phi_term_files[:50],
        },
        "boundary": {
            "locator_only": True,
            "source_replay": False,
            "source_replay_remains_open": True,
            "answer_label_leakage_remains_open": True,
            "native_closure": False,
            "gap_a_closure": False,
            "full_role_labeled_shared_B_universe_derived": False,
        },
        "missing_required_phrases": missing,
        "forbidden_phrases_found": forbidden,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOTE.parent.mkdir(parents=True, exist_ok=True)

    OUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "path", "class", "detail"])
        for x in exact_files:
            w.writerow(["exact_file", x["path"], x["class"], x["sha256"]])
        for x in script_refs:
            w.writerow(["script_reference", x["path"], x["class"], "|".join(x["ref_terms"])])
        for x in sorted(phi_term_files, key=lambda y: (-y["phi_hit_count"], y["path"]))[:50]:
            w.writerow(["phi_term_file", x["path"], x["class"], "|".join(x["phi_hits"])])

    lines = []
    lines.append("# Source construction upstream generator locator 012")
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
    lines.append("## Exact files")
    lines.append("")
    if exact_files:
        for x in exact_files:
            lines.append("- " + x["path"] + " [" + x["class"] + "]")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Script references")
    lines.append("")
    if script_refs:
        for x in script_refs[:25]:
            lines.append("- " + x["path"] + " [" + x["class"] + "] refs=" + ",".join(x["ref_terms"]))
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This is a locator only. It may identify candidate files or references, but it does not replay edge_records from deeper native construction. It does not prove native closure, does not close Gap A, and does not derive the full role-labeled shared_B universe. answer-label leakage remains open at the construction-origin level.")
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
