#!/usr/bin/env python3
"""
Phase 0 migration — APPLY (to a staging folder, NOT the live apps).

Consumes migration/proposed_mapping.json (which you reviewed) and produces
re-keyed copies of FBA's data under:

    migration/migrated_fba_data/

It re-keys FBA records from student NAME to Repertiores student_id:
  - rows whose action == "map"  -> re-keyed to repertiores_student_id
  - rows whose action == "skip" -> dropped (and counted)
  - rows whose action == "create" -> NOT supported here (no live writes); the
    script stops and tells you, since creating a Repertiores learner is a
    write to the live roster and belongs in a deliberate later step.

NOTHING in fba_tracker📱/data or the Repertiores data dir is modified. Every
record kept kerps its original `student_name` alongside the new `student_id`
so the later code change can switch keys without losing the human label.

Run:  python3 migration/fba_identity_apply.py
"""

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
FBA_DATA = PROJECT / "fba_tracker\U0001F4F1" / "data"
MAPPING = Path(__file__).resolve().parent / "proposed_mapping.json"
OUT_DIR = Path(__file__).resolve().parent / "migrated_fba_data"


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def main():
    mapping = load_json(MAPPING, None)
    if mapping is None:
        sys.exit(f"Cannot find mapping: {MAPPING}\nRun fba_identity_dryrun.py first.")

    # validate every row is resolved
    unresolved = [m["fba_name"] for m in mapping if m["action"] not in ("map", "skip", "create")]
    if unresolved:
        sys.exit("These rows are still unresolved (action must be map/skip/create):\n  "
                 + "\n  ".join(unresolved))
    creates = [m["fba_name"] for m in mapping if m["action"] == "create"]
    if creates:
        sys.exit("These rows are marked 'create', which writes to the live Repertiores "
                 "roster and is not done by this staging script:\n  "
                 + "\n  ".join(creates)
                 + "\n\nResolve them to 'map' or 'skip', or run the (separate) roster step.")

    # name -> student_id for mapped rows; set of skipped names
    name_to_id = {m["fba_name"]: m["repertiores_student_id"] for m in mapping if m["action"] == "map"}
    skipped = {m["fba_name"] for m in mapping if m["action"] == "skip"}

    print("=" * 72)
    print("FBA -> Repertiores identity migration  ·  APPLY to staging folder")
    print("=" * 72)
    print(f"Source (read-only): {FBA_DATA}")
    print(f"Output (staging):   {OUT_DIR}")
    print()
    print("Resolved mapping:")
    for n, sid in name_to_id.items():
        print(f"  map  {n:<20} -> {sid}")
    for n in skipped:
        print(f"  skip {n:<20} -> (dropped)")
    print()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {"abc_entries": {}, "student_profiles": {}, "indirect_assessments": {}, "students": {}}

    # ---- abc_entries.json: add student_id, drop skipped ----
    abc = load_json(FBA_DATA / "abc_entries.json", [])
    out_abc, dropped, kept, unknown = [], 0, 0, []
    for e in abc:
        n = e.get("student_name")
        if n in skipped:
            dropped += 1
            continue
        if n in name_to_id:
            e2 = dict(e)
            e2["student_id"] = name_to_id[n]   # new canonical key, name retained
            out_abc.append(e2)
            kept += 1
        else:
            unknown.append(n)
    with open(OUT_DIR / "abc_entries.json", "w") as f:
        json.dump(out_abc, f, indent=2, ensure_ascii=False)
    report["abc_entries"] = {"kept": kept, "dropped_skipped": dropped, "unknown": unknown}

    # ---- student_profiles.json: re-key dict name -> student_id ----
    profiles = load_json(FBA_DATA / "student_profiles.json", {})
    out_prof, p_dropped, p_unknown = {}, 0, []
    for n, prof in profiles.items():
        if n in skipped:
            p_dropped += 1
            continue
        if n in name_to_id:
            p2 = dict(prof)
            p2["student_name"] = n            # retain human label inside the record
            out_prof[name_to_id[n]] = p2
        else:
            p_unknown.append(n)
    with open(OUT_DIR / "student_profiles.json", "w") as f:
        json.dump(out_prof, f, indent=2, ensure_ascii=False)
    report["student_profiles"] = {"kept": len(out_prof), "dropped_skipped": p_dropped, "unknown": p_unknown}

    # ---- indirect_assessments.json: re-key dict name -> student_id ----
    indirect = load_json(FBA_DATA / "indirect_assessments.json", {})
    out_ind, i_dropped, i_unknown = {}, 0, []
    for n, data in indirect.items():
        if n in skipped:
            i_dropped += 1
            continue
        if n in name_to_id:
            out_ind[name_to_id[n]] = data
        else:
            i_unknown.append(n)
    with open(OUT_DIR / "indirect_assessments.json", "w") as f:
        json.dump(out_ind, f, indent=2, ensure_ascii=False)
    report["indirect_assessments"] = {"kept": len(out_ind), "dropped_skipped": i_dropped, "unknown": i_unknown}

    # ---- students.json: list of migrated student_ids (FBA defers to Repertiores roster) ----
    migrated_ids = sorted(set(name_to_id.values()))
    with open(OUT_DIR / "students.json", "w") as f:
        json.dump(migrated_ids, f, indent=2, ensure_ascii=False)
    report["students"] = {"migrated_ids": migrated_ids}

    # ---- report ----
    with open(OUT_DIR / "_migration_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("Wrote staging files:")
    for name in ("students.json", "student_profiles.json", "abc_entries.json",
                 "indirect_assessments.json", "_migration_report.json"):
        print(f"  · {OUT_DIR / name}")
    print()
    print("Result:")
    print(f"  abc_entries:          kept {report['abc_entries']['kept']}, "
          f"dropped {report['abc_entries']['dropped_skipped']}")
    print(f"  student_profiles:     kept {report['student_profiles']['kept']}, "
          f"dropped {report['student_profiles']['dropped_skipped']}")
    print(f"  indirect_assessments: kept {report['indirect_assessments']['kept']}, "
          f"dropped {report['indirect_assessments']['dropped_skipped']}")
    print(f"  students:             {migrated_ids}")

    anomalies = (report["abc_entries"]["unknown"]
                 + report["student_profiles"]["unknown"]
                 + report["indirect_assessments"]["unknown"])
    if anomalies:
        print(f"\n  ⚠️ names in data but not in mapping (left out): {sorted(set(anomalies))}")

    print("\nLive FBA data and Repertiores data were NOT modified.")
    print("Inspect migration/migrated_fba_data/ before any swap-in (Phase 1).")


if __name__ == "__main__":
    main()
