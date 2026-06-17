#!/usr/bin/env python3
"""
Phase 0 migration — DRY RUN ONLY.

Maps FBA Tracker's name-keyed student data onto Repertiores' id+name student
roster, so FBA records can later be re-keyed by Repertiores `student_id`.

This script WRITES NOTHING to either app's data. It:
  1. Loads Repertiores students (the source of truth for ids).
  2. Loads every FBA name-keyed store and counts each student's footprint.
  3. Proposes a name -> student_id mapping with a confidence/status per student.
  4. Prints a review table and writes ONE editable artifact:
       migration/proposed_mapping.json
     (an artifact you review/edit by hand; nothing reads it yet).

Run:  python3 migration/fba_identity_dryrun.py
"""

import json
import os
import sys
import difflib
from pathlib import Path

# ---- locations -------------------------------------------------------------

PROJECT = Path(__file__).resolve().parent.parent
FBA_DATA = PROJECT / "fba_tracker\U0001F4F1" / "data"   # fba_tracker📱/data

# Repertiores' live data dir is the source of truth for student ids.
REPERTIORES_LIVE = Path.home() / "Library" / "Application Support" / "Repertiores" / "data"
REPERTIORES_WS = PROJECT / "Repertiores" / "data"
REPERTIORES_DATA = REPERTIORES_LIVE if (REPERTIORES_LIVE / "students.json").exists() else REPERTIORES_WS

OUT = Path(__file__).resolve().parent / "proposed_mapping.json"

# ---- helpers ---------------------------------------------------------------

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        print(f"  !! {path} is not valid JSON: {e}", file=sys.stderr)
        return default

def norm(name):
    return " ".join((name or "").lower().split())

def first_last_initial(name):
    """('christian arias') -> ('christian', 'a'); ('joe ott') -> ('joe', 'o')."""
    toks = norm(name).split()
    if not toks:
        return ("", "")
    return (toks[0], toks[-1][0] if toks[-1] else "")

def match_repertiores(fba_name, rep_students):
    """Return (status, student_id, rep_name, score, reason)."""
    fn = norm(fba_name)
    # 1) exact (normalized) name match
    for s in rep_students:
        if norm(s.get("name")) == fn:
            return ("exact", s["id"], s["name"], 1.0, "normalized names identical")
    # 2) first-name + last-initial match (handles "Christian Arias" -> "Christian A")
    f_first, f_init = first_last_initial(fba_name)
    fli_hits = []
    for s in rep_students:
        r_first, r_init = first_last_initial(s.get("name"))
        # treat a Repertiores name whose last token is a single char as "First L" form
        r_toks = norm(s.get("name")).split()
        rep_is_abbrev = len(r_toks) >= 2 and len(r_toks[-1]) == 1
        if f_first and f_first == r_first and (
            (rep_is_abbrev and f_init == r_init) or f_init == r_init
        ):
            fli_hits.append(s)
    if len(fli_hits) == 1:
        s = fli_hits[0]
        return ("fuzzy", s["id"], s["name"], 0.7,
                "first name + last initial match — CONFIRM by hand")
    if len(fli_hits) > 1:
        return ("ambiguous", None, None, 0.0,
                "multiple first-name+initial candidates: "
                + ", ".join(f'{s["name"]}({s["id"]})' for s in fli_hits))
    # 3) loose ratio fallback (report only, never auto-accept)
    best, best_r = None, 0.0
    for s in rep_students:
        r = difflib.SequenceMatcher(None, fn, norm(s.get("name"))).ratio()
        if r > best_r:
            best, best_r = s, r
    if best and best_r >= 0.6:
        return ("weak", None, None, round(best_r, 2),
                f'closest is "{best["name"]}" ({best["id"]}) @ ratio {best_r:.2f} — likely NOT same')
    return ("none", None, None, 0.0, "no Repertiores learner matches — needs new student or skip")

# ---- gather ----------------------------------------------------------------

def main():
    print("=" * 72)
    print("FBA -> Repertiores identity migration  ·  DRY RUN (writes nothing to apps)")
    print("=" * 72)
    print(f"FBA data:         {FBA_DATA}")
    print(f"Repertiores data: {REPERTIORES_DATA}"
          f"{'  [LIVE]' if REPERTIORES_DATA == REPERTIORES_LIVE else '  [workspace copy]'}")
    print()

    rep_students = load_json(REPERTIORES_DATA / "students.json", [])
    print(f"Repertiores roster ({len(rep_students)} learners):")
    for s in rep_students:
        print(f"  · {s['id']:<12} {s.get('name','')}")
    print()

    fba_names = load_json(FBA_DATA / "students.json", [])
    profiles = load_json(FBA_DATA / "student_profiles.json", {})
    abc = load_json(FBA_DATA / "abc_entries.json", [])
    indirect = load_json(FBA_DATA / "indirect_assessments.json", {})

    # footprint counts per FBA name
    abc_counts = {}
    for e in abc:
        n = e.get("student_name")
        abc_counts[n] = abc_counts.get(n, 0) + 1

    # union of every name that appears anywhere in FBA data
    all_fba = list(dict.fromkeys(
        list(fba_names)
        + list(profiles.keys())
        + list(abc_counts.keys())
        + list(indirect.keys())
    ))

    proposal = []
    print("Per-student proposal:")
    print("-" * 72)
    for name in all_fba:
        status, sid, rep_name, score, reason = match_repertiores(name, rep_students)
        foot = {
            "profile": name in profiles,
            "abc_entries": abc_counts.get(name, 0),
            "indirect_assessment": name in indirect,
        }
        foot_str = (
            ("profile " if foot["profile"] else "")
            + (f"abc×{foot['abc_entries']} " if foot["abc_entries"] else "")
            + ("indirect" if foot["indirect_assessment"] else "")
        ).strip() or "(no data)"

        tag = {
            "exact": "✅ AUTO",
            "fuzzy": "⚠️  CONFIRM",
            "ambiguous": "❓ RESOLVE",
            "weak": "❓ REVIEW",
            "none": "➕ NEW/SKIP",
        }[status]

        print(f"  {tag:<12} FBA “{name}”")
        print(f"               data: {foot_str}")
        if sid:
            print(f"               → {sid}  ({rep_name})   [{reason}]")
        else:
            print(f"               → (unmapped)   [{reason}]")
        print()

        proposal.append({
            "fba_name": name,
            "status": status,
            "match_score": score,
            "reason": reason,
            "footprint": foot,
            # fill these in by hand for CONFIRM / RESOLVE / NEW rows before any write step:
            "repertiores_student_id": sid,        # null = unresolved
            "repertiores_name": rep_name,
            "action": ("map" if status == "exact" else "REVIEW"),  # map | create | skip | REVIEW
        })

    # ---- summary ----
    counts = {}
    for p in proposal:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    print("-" * 72)
    print("Summary: " + "  ".join(f"{k}={v}" for k, v in counts.items()))
    needs = [p["fba_name"] for p in proposal if p["action"] == "REVIEW"]
    if needs:
        print(f"\n{len(needs)} student(s) need your decision before a write step:")
        for n in needs:
            print(f"  · {n}")

    with open(OUT, "w") as f:
        json.dump(proposal, f, indent=2, ensure_ascii=False)
    print(f"\nProposed mapping written for your review (edit by hand):\n  {OUT}")
    print("Nothing in either app was modified.")

if __name__ == "__main__":
    main()
