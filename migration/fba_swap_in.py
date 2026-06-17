#!/usr/bin/env python3
"""
Phase 1b-A — re-stage FBA data keyed by Repertiores NAME (+ student_id), and
optionally swap it into FBA's LIVE data dir.

Why name-keyed (not id-keyed): FBA's whole UI keys records by the student NAME
(students.json is a list of names; every tab filters by student_name). Making
FBA's working name == Repertiores' display name ("Christian A") shares identity
with ZERO code churn, while stamping student_id onto every record provides the
robust cross-app link for the Phase 3 handoff.

Default run = DRY (writes only to migration/migrated_fba_data_v2/).
Pass --apply to back up FBA's live data and swap the migrated files in.

  python3 migration/fba_swap_in.py            # dry: stage v2 only
  python3 migration/fba_swap_in.py --apply    # back up live + swap in
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
FBA_DATA = PROJECT / "fba_tracker\U0001F4F1" / "data"
MAPPING = Path(__file__).resolve().parent / "proposed_mapping.json"
OUT_DIR = Path(__file__).resolve().parent / "migrated_fba_data_v2"

REP_LIVE = Path.home() / "Library" / "Application Support" / "Repertiores" / "data"
REP_WS = PROJECT / "Repertiores" / "data"
REP_DATA = REP_LIVE if (REP_LIVE / "students.json").exists() else REP_WS

APPLY = "--apply" in sys.argv


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def main():
    mapping = load(MAPPING, None)
    if mapping is None:
        sys.exit("Run fba_identity_dryrun.py first — no proposed_mapping.json.")

    rep_students = load(REP_DATA / "students.json", [])
    rep_name_by_id = {s["id"]: s.get("name", "") for s in rep_students}

    # Build per-FBA-name resolution from the reviewed mapping.
    #   mapped row -> (repertiores_id, repertiores_name)
    id_by_fba = {}
    name_by_fba = {}     # fba_name -> repertiores display name (the new key)
    skipped = set()
    for m in mapping:
        fn = m["fba_name"]
        if m["action"] == "map":
            sid = m["repertiores_student_id"]
            id_by_fba[fn] = sid
            name_by_fba[fn] = rep_name_by_id.get(sid) or m.get("repertiores_name") or fn
        elif m["action"] == "skip":
            skipped.add(fn)
        else:
            sys.exit(f"Row '{fn}' has unresolved action '{m['action']}' — fix the mapping first.")

    print("=" * 72)
    print(f"Phase 1b-A  ·  re-stage FBA data keyed by Repertiores name  "
          f"({'APPLY' if APPLY else 'DRY'})")
    print("=" * 72)
    print(f"FBA live data:    {FBA_DATA}")
    print(f"Repertiores data: {REP_DATA}")
    print(f"Staging output:   {OUT_DIR}")
    print()
    for fn in id_by_fba:
        print(f"  map  '{fn}'  ->  name='{name_by_fba[fn]}'  student_id={id_by_fba[fn]}")
    for fn in sorted(skipped):
        print(f"  skip '{fn}'  ->  (dropped)")
    print()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- students.json : list of Repertiores display names ----
    students_out = sorted(set(name_by_fba.values()))
    with open(OUT_DIR / "students.json", "w") as f:
        json.dump(students_out, f, indent=2, ensure_ascii=False)

    # ---- abc_entries.json : rewrite student_name -> Repertiores name, stamp id ----
    abc = load(FBA_DATA / "abc_entries.json", [])
    abc_out, kept, dropped = [], 0, 0
    for e in abc:
        fn = e.get("student_name")
        if fn in skipped or fn not in name_by_fba:
            dropped += 1
            continue
        e2 = dict(e)
        e2["student_name_original"] = fn               # provenance
        e2["student_name"] = name_by_fba[fn]           # new working key (Repertiores name)
        e2["student_id"] = id_by_fba[fn]               # cross-app link
        abc_out.append(e2)
        kept += 1
    with open(OUT_DIR / "abc_entries.json", "w") as f:
        json.dump(abc_out, f, indent=2, ensure_ascii=False)

    # ---- student_profiles.json : re-key name -> Repertiores name, stamp id ----
    profiles = load(FBA_DATA / "student_profiles.json", {})
    prof_out, p_dropped = {}, 0
    for fn, prof in profiles.items():
        if fn in skipped or fn not in name_by_fba:
            p_dropped += 1
            continue
        p2 = dict(prof)
        p2["student_id"] = id_by_fba[fn]
        p2["student_name_original"] = fn
        prof_out[name_by_fba[fn]] = p2
    with open(OUT_DIR / "student_profiles.json", "w") as f:
        json.dump(prof_out, f, indent=2, ensure_ascii=False)

    # ---- indirect_assessments.json : re-key name -> Repertiores name ----
    indirect = load(FBA_DATA / "indirect_assessments.json", {})
    ind_out, i_dropped = {}, 0
    for fn, data in indirect.items():
        if fn in skipped or fn not in name_by_fba:
            i_dropped += 1
            continue
        ind_out[name_by_fba[fn]] = data
    with open(OUT_DIR / "indirect_assessments.json", "w") as f:
        json.dump(ind_out, f, indent=2, ensure_ascii=False)

    print("Staged (name-keyed, id-stamped):")
    print(f"  students.json:        {students_out}")
    print(f"  abc_entries.json:     kept {kept}, dropped {dropped}")
    print(f"  student_profiles:     kept {len(prof_out)}, dropped {p_dropped}")
    print(f"  indirect_assessments: kept {len(ind_out)}, dropped {i_dropped}")
    print()

    if not APPLY:
        print("DRY run — FBA live data untouched. Re-run with --apply to swap in.")
        return

    # ---- APPLY: back up live FBA data, then swap migrated files in ----
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = FBA_DATA / "backups" / f"pre_phase1b_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    targets = ["students.json", "abc_entries.json",
               "student_profiles.json", "indirect_assessments.json"]
    for name in targets:
        live = FBA_DATA / name
        if live.exists():
            shutil.copy2(live, backup_dir / name)
    print(f"Backed up live FBA data -> {backup_dir}")

    for name in targets:
        shutil.copy2(OUT_DIR / name, FBA_DATA / name)
        print(f"  swapped in: {name}")
    print("\nLive FBA data now keyed by Repertiores name with student_id stamped.")
    print(f"Originals preserved in: {backup_dir}")


if __name__ == "__main__":
    main()
