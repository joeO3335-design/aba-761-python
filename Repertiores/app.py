"""Cold Probe Data Tracker.

Collects first-trial, unprompted probe data (Y / N / NR) for targets in
skill-acquisition programs. Scaffold for a larger ABA data system.
"""
from __future__ import annotations

import html
import io
import json
import math
import os
import shutil
import uuid
from datetime import date, datetime
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── Config ───────────────────────────────────────────────────────────────────
DEV_MODE = True

# Single data store shared by both `streamlit run` (dev) and the packaged .app:
#   ~/Library/Application Support/Repertiores/data
# so there is one source of truth instead of two copies that drift apart. The
# desktop launcher sets REPERTIORES_DATA_DIR to this same path; the env var
# overrides the default, which is handy for pointing tests at a scratch dir.
def _default_data_dir() -> str:
    support = os.path.join(
        os.path.expanduser("~"),
        "Library", "Application Support", "Repertiores",
    )
    return os.path.join(support, "data")


DATA_DIR = os.environ.get("REPERTIORES_DATA_DIR") or _default_data_dir()
STUDENTS_FILE = os.path.join(DATA_DIR, "students.json")
TARGETS_FILE = os.path.join(DATA_DIR, "targets.json")
PROBES_FILE = os.path.join(DATA_DIR, "probes.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
MASTERY_EVENTS_FILE = os.path.join(DATA_DIR, "mastery_events.json")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.json")
BEHAVIORS_FILE = os.path.join(DATA_DIR, "behaviors.json")
BEHAVIOR_RECORDS_FILE = os.path.join(DATA_DIR, "behavior_records.json")
TARGET_BANK_FILE = os.path.join(DATA_DIR, "target_bank.json")
INTERVENTION_BANK_FILE = os.path.join(DATA_DIR, "intervention_bank.json")
PHASES_FILE = os.path.join(DATA_DIR, "phases.json")
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")
# Per-save automatic snapshots of every data file live in a subfolder so they
# don't interfere with the targets "undo" feature, which scans BACKUPS_DIR only.
AUTO_BACKUPS_DIR = os.path.join(BACKUPS_DIR, "auto")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)
os.makedirs(AUTO_BACKUPS_DIR, exist_ok=True)

# How many automatic snapshots to keep per data file.
MAX_AUTO_BACKUPS = 15

# Data files whose on-disk copy failed to parse this process and could not be
# recovered from a backup. Saving to these is blocked so a corrupt file is never
# silently overwritten with empty/partial data. Populated by _load.
_QUARANTINED: set[str] = set()
# path -> human-readable message about a load problem (recovered or quarantined),
# surfaced as a banner in main().
_LOAD_ERRORS: dict[str, str] = {}

# Snapshot retention: keep at most this many backups of targets.json.
MAX_TARGET_BACKUPS = 20
# An "undoable" deletion is one whose backup is no older than this many seconds.
UNDO_WINDOW_SECONDS = 30 * 60  # 30 minutes

DOMAINS = [
    "Mand", "Tact", "Echoic", "Listener", "Intraverbal",
    "Imitation", "Visual Performance", "Receptive ID", "Expressive ID",
    "Academics", "Social", "Self-Help", "Play", "Other",
]
STATUSES = ["Planned", "In Acquisition", "Mastered", "Maintenance", "On Hold"]
RESPONSES = ["Y", "N", "NR", "PO", "NP"]
RESPONSE_LABEL = {
    "Y": "Yes (independent)",
    "N": "No / incorrect",
    "NR": "No response",
    "PO": "Probed out",
    "NP": "Not probed",
}
DEFAULT_MASTERY_N = 3

OPERANT_BUTTON_CLASS = {
    "Echoic": "opbtn-yellow",
    "Imitation": "opbtn-purple",
    "Intraverbal": "opbtn-blue",
    "Tact": "opbtn-green",
    "Receptive ID": "opbtn-red",
}

# Mastery-grid display order — VB-MAPP-shaped subset first, then the rest.
VB_MAPP_DOMAIN_ORDER = [
    "Mand", "Tact", "Listener", "Visual Performance",
    "Imitation", "Echoic", "Intraverbal",
    "Receptive ID", "Expressive ID",
    "Play", "Social", "Self-Help", "Academics", "Other",
]
GRID_STATUS_COLORS = {
    "Mastered":       "#2e7d32",
    "Maintenance":    "#558b2f",
    "In Acquisition": "#ef6c00",
    "On Hold":        "#9e9e9e",
    "Planned":        "#90a4ae",
}

# ── Storage helpers ──────────────────────────────────────────────────────────
def _backup_file(path: str) -> None:
    """Copy ``path`` into the auto-backup folder, pruning to MAX_AUTO_BACKUPS.

    Called by _save before each write so every data file has rolling history
    (not just targets.json). Failures are non-fatal — a backup miss must never
    block the actual save.
    """
    if not os.path.exists(path):
        return
    stem = os.path.splitext(os.path.basename(path))[0]
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    try:
        shutil.copy2(path, os.path.join(AUTO_BACKUPS_DIR, f"{stem}.{ts}.json"))
    except Exception:
        return
    prefix = stem + "."
    backups = sorted(
        f for f in os.listdir(AUTO_BACKUPS_DIR)
        if f.startswith(prefix) and f.endswith(".json")
    )
    while len(backups) > MAX_AUTO_BACKUPS:
        try:
            os.remove(os.path.join(AUTO_BACKUPS_DIR, backups.pop(0)))
        except Exception:
            break


def _recover_or_quarantine(path: str, err: Exception) -> list[dict[str, Any]]:
    """Handle a data file that exists but won't parse.

    Preserves the corrupt copy, tries to recover the newest parseable backup,
    and — if nothing is recoverable — quarantines the path so _save refuses to
    overwrite it. Returns the recovered rows, or [] if none.
    """
    name = os.path.basename(path)
    stem = os.path.splitext(name)[0]
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    msg = getattr(err, "msg", str(err))
    # 1) Preserve the corrupt file (".corrupt" so it's never a recovery source).
    try:
        shutil.copy2(path, os.path.join(AUTO_BACKUPS_DIR, f"{stem}.{ts}.corrupt"))
    except Exception:
        pass
    # 2) Try the newest parseable backup from the auto folder or BACKUPS_DIR.
    candidates: list[tuple[float, str]] = []
    for d in (AUTO_BACKUPS_DIR, BACKUPS_DIR):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith(stem + ".") and f.endswith(".json"):
                fp = os.path.join(d, f)
                try:
                    candidates.append((os.path.getmtime(fp), fp))
                except Exception:
                    pass
    for _, fp in sorted(candidates, reverse=True):
        try:
            with open(fp) as f:
                data = json.load(f)
        except Exception:
            continue
        _QUARANTINED.discard(path)
        _LOAD_ERRORS[path] = (
            f"was unreadable ({msg}); recovered from backup "
            f"{os.path.basename(fp)}. The corrupt copy was saved as "
            f"{stem}.{ts}.corrupt in data/backups/auto/."
        )
        return data
    # 3) Nothing recoverable — block writes so we don't clobber it.
    _QUARANTINED.add(path)
    _LOAD_ERRORS[path] = (
        f"is corrupt ({msg}) and no usable backup was found. Saving to this "
        f"file is blocked to prevent data loss; the corrupt copy is preserved "
        f"as {stem}.{ts}.corrupt in data/backups/auto/."
    )
    return []


def _load(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        # The file exists but is corrupt. Do NOT silently return [] — a later
        # _save would then overwrite recoverable data with nothing.
        return _recover_or_quarantine(path, e)
    # Clean parse — clear any prior problem flags for this file.
    _QUARANTINED.discard(path)
    _LOAD_ERRORS.pop(path, None)
    return data


def _save(path: str, rows: list[dict[str, Any]]) -> None:
    """Atomically write ``rows`` to ``path`` (temp file + os.replace), then
    snapshot the committed copy. Refuses to write a quarantined file.

    The snapshot is taken *after* the write so each backup holds the last
    successfully-saved state — that's what recovery restores if the live file
    is later found corrupt.
    """
    if path in _QUARANTINED:
        raise RuntimeError(
            f"Refusing to write {os.path.basename(path)}: its on-disk copy is "
            f"corrupt and no backup was found. Fix or remove the corrupt file in "
            f"data/ first (the corrupt copy is in data/backups/auto/)."
        )
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(rows, f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomic on the same filesystem
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise
    _backup_file(path)  # snapshot the committed (last-good) state


def load_students() -> list[dict[str, Any]]:
    return _load(STUDENTS_FILE)


def load_targets() -> list[dict[str, Any]]:
    return _load(TARGETS_FILE)


def load_probes() -> list[dict[str, Any]]:
    return _load(PROBES_FILE)


def save_students(rows): _save(STUDENTS_FILE, rows)
def save_targets(rows): _save(TARGETS_FILE, rows)


def _render_undo_banner(location_key: str) -> None:
    """Show an 'Undo last delete' banner if a recent snapshot exists.

    ``location_key`` namespaces the button's Streamlit key so the same banner
    can render on multiple pages without colliding.
    """
    snap = latest_undoable_snapshot()
    if not snap:
        return
    if snap["reason"] == "pre_undo":
        # Don't offer to undo an undo — that path lives in the backups, not the banner.
        return
    age_sec = int((datetime.now() - snap["ts"]).total_seconds())
    age_label = (
        f"{age_sec}s ago" if age_sec < 60
        else f"{age_sec // 60} min ago"
    )
    removed_label = (
        f" — {snap['removed']} row(s) removed" if snap["removed"] else ""
    )
    reason_label = snap["reason"].replace("_", " ") if snap["reason"] else "edit"
    cols = st.columns([5, 1])
    with cols[0]:
        st.info(
            f"↩ Recent delete: **{reason_label}**{removed_label} "
            f"({age_label}). Undo available for "
            f"{UNDO_WINDOW_SECONDS // 60} min after the change.",
            icon="↩",
        )
    with cols[1]:
        if st.button(
            "↩ Undo",
            key=f"undo_delete_{location_key}",
            type="primary",
            width="stretch",
        ):
            n = restore_targets_from_snapshot(snap["path"])
            st.toast(f"Restored — {n} targets in file.")
            st.rerun()


def snapshot_targets(reason: str = "edit") -> str | None:
    """Copy targets.json to data/backups/ with a timestamp and a reason tag.

    Returns the backup path, or None if there's nothing to snapshot. Old
    backups beyond ``MAX_TARGET_BACKUPS`` are pruned (oldest first).
    """
    if not os.path.exists(TARGETS_FILE):
        return None
    safe_reason = "".join(
        c if (c.isalnum() or c in "-_") else "_" for c in reason
    )[:40] or "edit"
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    path = os.path.join(BACKUPS_DIR, f"targets.{ts}.{safe_reason}.json")
    try:
        import shutil
        shutil.copy2(TARGETS_FILE, path)
    except Exception:
        return None
    # Prune oldest beyond cap.
    backups = sorted(
        [f for f in os.listdir(BACKUPS_DIR)
         if f.startswith("targets.") and f.endswith(".json")]
    )
    while len(backups) > MAX_TARGET_BACKUPS:
        try:
            os.remove(os.path.join(BACKUPS_DIR, backups.pop(0)))
        except Exception:
            break
    return path


def delete_targets(ids: set[str], reason: str = "delete") -> int:
    """Snapshot targets.json, then remove rows whose id is in ``ids``.

    Returns the number of rows actually removed.
    """
    if not ids:
        return 0
    snapshot_targets(reason=reason)
    rows = load_targets()
    keep = [r for r in rows if r.get("id") not in ids]
    removed = len(rows) - len(keep)
    if removed:
        save_targets(keep)
    return removed


def _parse_backup_name(name: str) -> tuple[datetime | None, str]:
    """Return (timestamp, reason) parsed from a backup filename, or (None, '')."""
    base = name[len("targets."):-len(".json")] if (
        name.startswith("targets.") and name.endswith(".json")
    ) else ""
    if "." not in base:
        return None, ""
    ts_str, _, reason = base.partition(".")
    try:
        return datetime.strptime(ts_str, "%Y%m%dT%H%M%S"), reason
    except ValueError:
        return None, ""


def latest_undoable_snapshot() -> dict | None:
    """Most recent backup within ``UNDO_WINDOW_SECONDS``, or None.

    Returns a dict with ``path``, ``ts`` (datetime), ``reason``, and
    ``removed`` (int — how many rows the current targets file is short by
    compared to the snapshot).
    """
    if not os.path.isdir(BACKUPS_DIR):
        return None
    candidates = []
    for name in os.listdir(BACKUPS_DIR):
        ts, reason = _parse_backup_name(name)
        if ts is None:
            continue
        candidates.append((ts, name, reason))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    ts, name, reason = candidates[0]
    if (datetime.now() - ts).total_seconds() > UNDO_WINDOW_SECONDS:
        return None
    path = os.path.join(BACKUPS_DIR, name)
    try:
        before_rows = json.load(open(path))
        after_rows = json.load(open(TARGETS_FILE))
        removed = max(0, len(before_rows) - len(after_rows))
    except Exception:
        removed = 0
    return {"path": path, "ts": ts, "reason": reason, "removed": removed}


def restore_targets_from_snapshot(path: str) -> int:
    """Replace targets.json with the contents of ``path``. Snapshots the
    current file first (reason='pre_undo') so the undo is itself undoable.

    Returns the number of rows in the restored file.
    """
    import shutil
    snapshot_targets(reason="pre_undo")
    shutil.copy2(path, TARGETS_FILE)
    return len(json.load(open(TARGETS_FILE)))
def save_probes(rows): _save(PROBES_FILE, rows)


def load_mastery_events() -> list[dict[str, Any]]:
    return _load(MASTERY_EVENTS_FILE)


def save_mastery_events(rows): _save(MASTERY_EVENTS_FILE, rows)


def log_mastery_event(
    student_id: str, target_id: str, event_type: str, day: str | None = None,
) -> None:
    """Append a +1 (mastered) or -1 (unmastered) event for the student/target.

    Idempotent against rapid duplicates: if the most recent event for this target
    is already the same type on the same day, no new event is written.
    The target's current domain is snapshotted onto the event so per-operant
    queries still work after the target is deleted.
    """
    if event_type not in ("mastered", "unmastered"):
        return
    if not day:
        day = date.today().isoformat()
    events = load_mastery_events()
    target_events = sorted(
        (e for e in events if e["target_id"] == target_id),
        key=lambda e: (e["date"], e.get("recorded_at", "")),
    )
    if target_events and target_events[-1]["type"] == event_type and target_events[-1]["date"] == day:
        return
    target = next((t for t in load_targets() if t["id"] == target_id), None)
    events.append({
        "id": new_id(),
        "student_id": student_id,
        "target_id": target_id,
        "type": event_type,
        "date": day,
        "recorded_at": now_iso(),
        "domain": target.get("domain", "") if target else "",
    })
    save_mastery_events(events)


def load_sessions() -> list[dict[str, Any]]:
    return _load(SESSIONS_FILE)


def save_sessions(rows): _save(SESSIONS_FILE, rows)


def load_behaviors() -> list[dict[str, Any]]:
    return _load(BEHAVIORS_FILE)


def save_behaviors(rows): _save(BEHAVIORS_FILE, rows)


def load_behavior_records() -> list[dict[str, Any]]:
    return _load(BEHAVIOR_RECORDS_FILE)


def save_behavior_records(rows): _save(BEHAVIOR_RECORDS_FILE, rows)


def upsert_behavior_record(
    behavior_id: str, student_id: str, day_iso: str,
    value: float, obs_minutes: float | None = None, notes: str = "",
) -> None:
    """Insert or replace a behavior record for the given (behavior, day)."""
    rows = load_behavior_records()
    rows = [
        r for r in rows
        if not (r["behavior_id"] == behavior_id and r["date"] == day_iso)
    ]
    rows.append({
        "id": new_id(),
        "behavior_id": behavior_id,
        "student_id": student_id,
        "date": day_iso,
        "value": float(value),
        "obs_minutes": float(obs_minutes) if obs_minutes else None,
        "notes": notes.strip(),
        "recorded_at": now_iso(),
    })
    save_behavior_records(rows)


def delete_behavior_record(behavior_id: str, day_iso: str) -> None:
    rows = [
        r for r in load_behavior_records()
        if not (r["behavior_id"] == behavior_id and r["date"] == day_iso)
    ]
    save_behavior_records(rows)


def load_target_bank() -> list[dict[str, Any]]:
    return _load(TARGET_BANK_FILE)


def save_target_bank(rows): _save(TARGET_BANK_FILE, rows)


# ── Intervention bank ─────────────────────────────────────────────────────────
# Category -> short descriptor shown under the heading.
INTERVENTION_CATEGORIES = {
    "Antecedent Manipulation": "stimulus control / motivation",
    "Consequence Manipulation": "reinforcer / extinction / punishment",
}
# Seeded on first use; users can add/remove from the Intervention Bank page.
DEFAULT_INTERVENTIONS = [
    ("Antecedent Manipulation", "Increase pairing"),
    ("Antecedent Manipulation", "Reduce # of demands (↑VR)"),
    ("Antecedent Manipulation", "Increase # of easy skills interspersed"),
    ("Antecedent Manipulation", "Decrease response effort"),
    ("Antecedent Manipulation", "Further reduce errors (modify prompt procedures)"),
    ("Antecedent Manipulation", "Change instruction pace (ITI)"),
    ("Antecedent Manipulation", "Decrease/increase session time"),
    ("Antecedent Manipulation", "Conduct Sr+ assessment"),
    ("Antecedent Manipulation", "Change field of stimuli"),
    ("Antecedent Manipulation", "Increase # of teaching trials"),
    ("Antecedent Manipulation", "Change physical environment"),
    ("Antecedent Manipulation", "Change aim"),
    ("Antecedent Manipulation", "Teach pre-requisite skills"),
    ("Antecedent Manipulation", "Decrease # of goals/objectives"),
    ("Antecedent Manipulation", "Build MO by deprivation of specific reinforcers"),
    ("Antecedent Manipulation", "Change teaching procedure"),
    ("Consequence Manipulation", "Provide more valuable reinforcer"),
    ("Consequence Manipulation", "Provide higher rate of reinforcement (lower VR)"),
    ("Consequence Manipulation", "Reinforce immediately"),
    ("Consequence Manipulation", "Provide a greater magnitude of reinforcement"),
    ("Consequence Manipulation", "Reinforce on transfer trials"),
    ("Consequence Manipulation", "Better use of extinction"),
    ("Consequence Manipulation", "Improve the implementation of differential reinforcement"),
]


def load_intervention_bank() -> list[dict[str, Any]]:
    """Load the intervention bank, seeding the defaults on first use."""
    rows = _load(INTERVENTION_BANK_FILE)
    if not rows:
        rows = [
            {"id": new_id(), "category": cat, "name": name, "created_at": now_iso()}
            for cat, name in DEFAULT_INTERVENTIONS
        ]
        _save(INTERVENTION_BANK_FILE, rows)
    return rows


def save_intervention_bank(rows): _save(INTERVENTION_BANK_FILE, rows)


def add_intervention_to_bank(category: str, name: str) -> dict | None:
    """Add a new intervention to the bank, de-duped by (category, name)."""
    name = name.strip()
    category = category.strip()
    if not name or not category:
        return None
    bank = load_intervention_bank()
    key = (category.lower(), name.lower())
    if any((b["category"].lower(), b["name"].lower()) == key for b in bank):
        return None
    rec = {"id": new_id(), "category": category, "name": name,
           "created_at": now_iso()}
    bank.append(rec)
    save_intervention_bank(bank)
    return rec


def attach_intervention(
    behavior_id: str, student_id: str, intervention: dict,
    start_date: str, notes: str, make_phase: bool,
) -> None:
    """Record an intervention on a behavior, optionally as a graph phase line."""
    behaviors = load_behaviors()
    for b in behaviors:
        if b["id"] != behavior_id:
            continue
        phase_id = ""
        if make_phase:
            ph = add_phase(
                student_id, start_date, intervention["name"], notes, behavior_id,
            )
            phase_id = ph["id"]
        b.setdefault("interventions", []).append({
            "id": new_id(),
            "intervention_id": intervention.get("id", ""),
            "name": intervention["name"],
            "category": intervention.get("category", ""),
            "start_date": start_date,
            "notes": notes.strip(),
            "phase_id": phase_id,
            "created_at": now_iso(),
        })
        save_behaviors(behaviors)
        return


def detach_intervention(behavior_id: str, attach_id: str) -> None:
    """Remove an attached intervention (and its phase line, if any)."""
    behaviors = load_behaviors()
    for b in behaviors:
        if b["id"] != behavior_id:
            continue
        keep = []
        for iv in b.get("interventions", []):
            if iv.get("id") == attach_id:
                if iv.get("phase_id"):
                    delete_phase(iv["phase_id"])
                continue
            keep.append(iv)
        b["interventions"] = keep
        save_behaviors(behaviors)
        return


def load_phases() -> list[dict[str, Any]]:
    """Phases are scoped to a student. Old per-behavior rows are migrated lazily."""
    rows = _load(PHASES_FILE)
    needs_save = False
    if rows:
        behaviors_lookup = None
        for r in rows:
            if not r.get("student_id"):
                # Migrate legacy per-behavior phase by looking up its student.
                bid = r.get("behavior_id", "")
                if behaviors_lookup is None:
                    behaviors_lookup = {b["id"]: b for b in load_behaviors()}
                src = behaviors_lookup.get(bid)
                if src and src.get("student_id"):
                    r["student_id"] = src["student_id"]
                    needs_save = True
        if needs_save:
            _save(PHASES_FILE, rows)
    return rows


def save_phases(rows): _save(PHASES_FILE, rows)


def add_phase(
    student_id: str, day_iso: str, label: str, notes: str = "",
    behavior_id: str = "",
) -> dict:
    """Add a phase line. behavior_id="" means it applies to every behavior."""
    rows = load_phases()
    rec = {
        "id": new_id(),
        "student_id": student_id,
        "behavior_id": behavior_id,
        "date": day_iso,
        "label": label.strip(),
        "notes": notes.strip(),
        "created_at": now_iso(),
    }
    rows.append(rec)
    save_phases(rows)
    return rec


def delete_phase(phase_id: str) -> None:
    save_phases([p for p in load_phases() if p["id"] != phase_id])


def phases_for_student(student_id: str) -> list[dict]:
    return sorted(
        [p for p in load_phases() if p.get("student_id") == student_id],
        key=lambda p: p["date"],
    )


def phases_for_behavior(student_id: str, behavior_id: str) -> list[dict]:
    """Phases that apply to a behavior: student-wide ones + this behavior's own."""
    return sorted(
        [
            p for p in load_phases()
            if p.get("student_id") == student_id
            and (not p.get("behavior_id") or p.get("behavior_id") == behavior_id)
        ],
        key=lambda p: p["date"],
    )


def _apply_phase_lines(fig, phases: list[dict]) -> None:
    """Add a dashed vertical line + text label for each phase to a plotly fig.

    The line and the annotation are added separately: passing ``annotation_*``
    to ``add_vline`` makes Plotly average the x-coordinates, which raises a
    TypeError on pandas Timestamps. A plain string date sidesteps that.
    """
    if not phases:
        return
    for ph in sorted(phases, key=lambda p: p["date"]):
        x_val = ph.get("date")
        if not x_val:
            continue
        fig.add_vline(
            x=x_val,
            line_width=1.5,
            line_dash="dash",
            line_color="#1c1917",
            opacity=0.6,
        )
        fig.add_annotation(
            x=x_val,
            y=1.0,
            yref="paper",
            yanchor="bottom",
            showarrow=False,
            text=ph.get("label", "Phase"),
            font=dict(size=11, color="#1c1917"),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#d6d3d1",
            borderwidth=1,
            borderpad=2,
        )


def _xrange_with_phases(
    data_dates, phases: list[dict],
    pad_days: int = 3, min_span_days: int = 0,
):
    """Return [lo, hi] Timestamps covering the data AND every phase date.

    Plotly auto-ranges only to trace data, so a phase dated outside the data
    span would be clipped. Callers set the x-axis range to this so phase
    lines are always visible.
    """
    dates = []
    for d in data_dates:
        try:
            dates.append(pd.to_datetime(d))
        except Exception:
            pass
    for ph in (phases or []):
        try:
            dates.append(pd.to_datetime(ph["date"]))
        except Exception:
            pass
    if not dates:
        return None
    lo, hi = min(dates), max(dates)
    if min_span_days and (hi - lo).days < min_span_days:
        hi = lo + pd.Timedelta(days=min_span_days)
    pad = pd.Timedelta(days=pad_days)
    return [lo - pad, hi + pad]


def save_targets_to_bank(target_dicts: list[dict], source_student_name: str = "") -> list[str]:
    """Snapshot the given targets into the bank. De-dupes by (description, domain, skill_list).

    Returns the list of newly created bank IDs (excludes duplicates that were skipped).
    """
    bank = load_target_bank()
    existing_keys = {
        (b["description"].strip().lower(), b.get("domain", ""), (b.get("skill_list") or "").strip().lower())
        for b in bank
    }
    new_ids: list[str] = []
    for t in target_dicts:
        key = (
            t["description"].strip().lower(),
            t.get("domain", ""),
            (t.get("skill_list") or "").strip().lower(),
        )
        if key in existing_keys:
            continue
        bid = new_id()
        bank.append({
            "id": bid,
            "description": t["description"].strip(),
            "domain": t.get("domain", ""),
            "skill_list": (t.get("skill_list") or "").strip(),
            "mastery_n": int(t.get("mastery_n", DEFAULT_MASTERY_N)),
            "mastery_criterion": t.get("mastery_criterion", ""),
            "source_student": source_student_name,
            "created_at": now_iso(),
        })
        existing_keys.add(key)
        new_ids.append(bid)
    if new_ids:
        save_target_bank(bank)
    return new_ids


def import_bank_to_student(bank_ids: list[str], student_id: str) -> int:
    """Copy bank entries into a student's targets as new In Acquisition rows.

    Skips bank entries the student already has (same operant + list + description,
    case-insensitive) so re-imports don't create duplicates.
    """
    bank = load_target_bank()
    targets = load_targets()
    existing_keys = {
        (
            (t.get("description") or "").strip().lower(),
            t.get("domain", ""),
            (t.get("skill_list") or "").strip().lower(),
        )
        for t in targets
        if t["student_id"] == student_id
    }
    n_added = 0
    for bid in bank_ids:
        b = next((x for x in bank if x["id"] == bid), None)
        if not b:
            continue
        key = (
            b["description"].strip().lower(),
            b.get("domain", ""),
            (b.get("skill_list") or "").strip().lower(),
        )
        if key in existing_keys:
            continue
        targets.append({
            "id": new_id(),
            "student_id": student_id,
            "description": b["description"],
            "domain": b.get("domain", ""),
            "skill_list": b.get("skill_list", ""),
            "mastery_n": int(b.get("mastery_n", DEFAULT_MASTERY_N)),
            "mastery_criterion": b.get("mastery_criterion", ""),
            "status": "In Acquisition",
            "mastered_date": "",
        })
        existing_keys.add(key)
        n_added += 1
    if n_added:
        save_targets(targets)
    return n_added


# Measurement-dimension catalog used by the Behaviors page.
MEASUREMENT_TYPES = {
    "frequency": {
        "label": "Frequency (count)",
        "unit": "count",
        "axis": "Count per session",
        "help": "How many times the behavior occurred during the session.",
        "value_step": 1.0,
        "value_min": 0.0,
        "value_format": "%d",
    },
    "rate": {
        "label": "Rate (per hour)",
        "unit": "per hour",
        "axis": "Rate (per hour)",
        "help": "Count divided by observation time. Enter both count and observation minutes.",
        "value_step": 1.0,
        "value_min": 0.0,
        "value_format": "%d",
    },
    "duration": {
        "label": "Duration (minutes)",
        "unit": "minutes",
        "axis": "Duration (minutes)",
        "help": "Total minutes the behavior occurred.",
        "value_step": 0.25,
        "value_min": 0.0,
        "value_format": "%.2f",
    },
    "latency": {
        "label": "Latency (seconds)",
        "unit": "seconds",
        "axis": "Latency (seconds)",
        "help": "Seconds between the SD/cue and the behavior onset.",
        "value_step": 0.5,
        "value_min": 0.0,
        "value_format": "%.1f",
    },
    "magnitude": {
        "label": "Magnitude / intensity (1–5)",
        "unit": "1–5",
        "axis": "Magnitude (1–5)",
        "help": "Subjective intensity rating, 1 = mild to 5 = severe.",
        "value_step": 1.0,
        "value_min": 1.0,
        "value_format": "%d",
    },
}


def _default_session_name(day_iso: str) -> str:
    try:
        d = datetime.strptime(day_iso, "%Y-%m-%d").date()
        return f"Cold Probes — {d.strftime('%A, %b %-d')}"
    except ValueError:
        return f"Cold Probes — {day_iso}"


def _migrate_submissions_to_sessions() -> None:
    """One-time migration: rewrite legacy submissions.json as sessions.json rows.

    Idempotent — only runs while submissions.json still exists. Each old
    submission becomes a completed session with started_at == ended_at.
    """
    if not os.path.exists(SUBMISSIONS_FILE):
        return
    legacy = _load(SUBMISSIONS_FILE)
    sessions = load_sessions()
    have = {(s["student_id"], s["date"]) for s in sessions}
    for sub in legacy:
        key = (sub.get("student_id", ""), sub.get("date", ""))
        if not key[0] or not key[1] or key in have:
            continue
        sessions.append({
            "id": new_id(),
            "student_id": key[0],
            "date": key[1],
            "name": _default_session_name(key[1]),
            "started_at": sub.get("submitted_at", ""),
            "ended_at": sub.get("submitted_at", ""),
            "clinician": sub.get("clinician", ""),
            "notes": "",
        })
        have.add(key)
    save_sessions(sessions)
    try:
        os.remove(SUBMISSIONS_FILE)
    except OSError:
        pass


def get_session(student_id: str, day_iso: str) -> dict | None:
    _migrate_submissions_to_sessions()
    for s in load_sessions():
        if s["student_id"] == student_id and s["date"] == day_iso:
            return s
    return None


def ensure_session_started(student_id: str, day_iso: str, clinician: str) -> dict:
    """Return the existing session for the day, creating one if absent."""
    existing = get_session(student_id, day_iso)
    if existing:
        return existing
    sessions = load_sessions()
    rec = {
        "id": new_id(),
        "student_id": student_id,
        "date": day_iso,
        "name": _default_session_name(day_iso),
        "started_at": now_iso(),
        "ended_at": "",
        "clinician": (clinician or "").strip(),
        "notes": "",
    }
    sessions.append(rec)
    save_sessions(sessions)
    return rec


def end_session(student_id: str, day_iso: str, clinician: str) -> None:
    sessions = load_sessions()
    rec = next(
        (s for s in sessions if s["student_id"] == student_id and s["date"] == day_iso),
        None,
    )
    if rec is None:
        rec = {
            "id": new_id(),
            "student_id": student_id,
            "date": day_iso,
            "name": _default_session_name(day_iso),
            "started_at": now_iso(),
            "ended_at": "",
            "clinician": (clinician or "").strip(),
            "notes": "",
        }
        sessions.append(rec)
    if not rec.get("started_at"):
        rec["started_at"] = now_iso()
    rec["ended_at"] = now_iso()
    if not rec.get("clinician") and clinician:
        rec["clinician"] = clinician.strip()
    save_sessions(sessions)


def reopen_session(student_id: str, day_iso: str) -> None:
    sessions = load_sessions()
    for s in sessions:
        if s["student_id"] == student_id and s["date"] == day_iso:
            s["ended_at"] = ""
            break
    save_sessions(sessions)


def update_session(student_id: str, day_iso: str, **fields) -> None:
    allowed = {"name", "clinician", "notes"}
    sessions = load_sessions()
    for s in sessions:
        if s["student_id"] == student_id and s["date"] == day_iso:
            for k, v in fields.items():
                if k in allowed and v is not None:
                    s[k] = v.strip() if isinstance(v, str) else v
            break
    save_sessions(sessions)


def ensure_mastery_event_backfill() -> None:
    """Seed mastery events for any currently-Mastered target that has no event yet,
    and annotate older events with the target's current domain.

    Idempotent. Lets the cumulative chart work for targets mastered before the
    event log existed, and lets per-operant filters work for events written
    before the domain field was added.
    """
    targets = load_targets()
    target_lookup = {t["id"]: t for t in targets}
    events = load_mastery_events()
    seeded_targets = {e["target_id"] for e in events}
    new_events = []
    for t in targets:
        if (
            t.get("status") == "Mastered"
            and t.get("mastered_date")
            and t["id"] not in seeded_targets
        ):
            new_events.append({
                "id": new_id(),
                "student_id": t["student_id"],
                "target_id": t["id"],
                "type": "mastered",
                "date": t["mastered_date"],
                "recorded_at": now_iso(),
                "domain": t.get("domain", ""),
            })
    annotated = False
    for e in events:
        if not e.get("domain"):
            tgt = target_lookup.get(e["target_id"])
            if tgt:
                e["domain"] = tgt.get("domain", "")
                annotated = True
    if new_events or annotated:
        save_mastery_events(events + new_events)


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Lookup helpers ───────────────────────────────────────────────────────────
def student_name(students, sid):
    for s in students:
        if s["id"] == sid:
            return s["name"]
    return "—"


def current_sid(students) -> str | None:
    """Return the sidebar-selected student id, falling back to the first student."""
    sid = st.session_state.get("current_student")
    if sid and any(s["id"] == sid for s in students):
        return sid
    return students[0]["id"] if students else None


def targets_for(student_id, targets, include_inactive=False):
    out = []
    for t in targets:
        if t["student_id"] != student_id:
            continue
        if not include_inactive and t["status"] != "In Acquisition":
            continue
        out.append(t)
    return out


def already_probed_today(probes, target_id, day: date) -> dict | None:
    iso = day.isoformat()
    for p in probes:
        if p["target_id"] == target_id and p["date"] == iso:
            return p
    return None


def target_probes_sorted(target_id: str, probes) -> list[dict]:
    """Chronological, oldest first, with stable tie-break on recorded_at."""
    rows = [p for p in probes if p["target_id"] == target_id]
    return sorted(rows, key=lambda p: (p["date"], p.get("recorded_at", "")))


def _streak_y_dates(target_id: str, probes) -> list[str]:
    """Probe dates of the current tail run of consecutive Y probes, oldest first.

    Spans sessions and weeks: PO ("probed out") and NP ("not probed") are
    skipped (they neither count nor break); any other response (N, NR, or
    legacy values) ends the run.
    """
    run: list[str] = []
    for p in reversed(target_probes_sorted(target_id, probes)):
        r = p["response"]
        if r == "Y":
            run.append(p["date"])
        elif r in ("PO", "NP"):
            continue
        else:
            break
    run.reverse()
    return run


def consecutive_y_streak(target_id: str, probes) -> int:
    """Length of the current tail run of consecutive Y probes."""
    return len(_streak_y_dates(target_id, probes))


def mastery_date_from_streak(target_id: str, probes, n: int) -> str:
    """The date the Nth consecutive Y was recorded — i.e., the date the mastery
    criterion was actually met (not the data-entry day). '' if the run is < n."""
    dates = _streak_y_dates(target_id, probes)
    return dates[n - 1] if len(dates) >= n else ""


def first_data_date(target_id: str, probes) -> str:
    """First date a Y or N probe was recorded for this target.

    NR (no response) is excluded — it isn't informative data collection.
    Returns '' if no Y/N probes have been logged yet.
    """
    yn = [p for p in probes if p["target_id"] == target_id and p["response"] in ("Y", "N")]
    return min((p["date"] for p in yn), default="")


def avg_days_to_mastery(targets: list[dict], probes: list[dict]) -> float | None:
    """Average (mastered_date − date introduced) in days across mastered targets.

    'Date introduced' is the first Y/N probe date (same convention as the
    Mastery log). Targets missing either anchor are skipped. Returns None
    if no eligible spans exist.
    """
    spans: list[int] = []
    for t in targets:
        if t.get("status") != "Mastered":
            continue
        md = (t.get("mastered_date") or "").strip()
        if not md:
            continue
        fd = first_data_date(t["id"], probes)
        if not fd:
            continue
        try:
            d_intro = date.fromisoformat(fd)
            d_mast = date.fromisoformat(md)
        except ValueError:
            continue
        spans.append((d_mast - d_intro).days)
    if not spans:
        return None
    return sum(spans) / len(spans)


def mastery_n_for(target: dict) -> int:
    try:
        return max(1, int(target.get("mastery_n", DEFAULT_MASTERY_N)))
    except (TypeError, ValueError):
        return DEFAULT_MASTERY_N


def apply_auto_mastery(target_id: str) -> dict | None:
    """If the target's streak now meets its criterion, mark it mastered.

    Returns the target dict when mastery was newly applied (for UI feedback),
    otherwise None. Safe to call after every probe write.
    """
    targets = load_targets()
    t = next((x for x in targets if x["id"] == target_id), None)
    if not t or t["status"] != "In Acquisition":
        return None
    probes = load_probes()
    n = mastery_n_for(t)
    if consecutive_y_streak(target_id, probes) < n:
        return None
    t["status"] = "Mastered"
    # Stamp the date the criterion was actually met (the Nth consecutive Y),
    # not the data-entry day — accurate even when probes are entered late.
    t["mastered_date"] = mastery_date_from_streak(target_id, probes, n) or date.today().isoformat()
    t["mastered_via"] = "criterion"
    t["mastered_probe_count"] = sum(1 for p in probes if p["target_id"] == target_id)
    save_targets(targets)
    log_mastery_event(t["student_id"], target_id, "mastered", t["mastered_date"])
    return t


def apply_po_mastery(target_id: str) -> dict | None:
    """A PO ('probed out') response moves the target to Mastered immediately.

    Date stamped is today's date; mastered_via='PO' marks the route so the
    UI can label it. Returns the target on first application, None if it was
    already mastered (idempotent).
    """
    targets = load_targets()
    t = next((x for x in targets if x["id"] == target_id), None)
    if not t or t["status"] == "Mastered":
        return None
    probes = load_probes()
    t["status"] = "Mastered"
    t["mastered_date"] = date.today().isoformat()
    t["mastered_via"] = "PO"
    t["mastered_probe_count"] = sum(1 for p in probes if p["target_id"] == target_id)
    save_targets(targets)
    log_mastery_event(t["student_id"], target_id, "mastered", t["mastered_date"])
    return t


def cumulative_mastery_series(
    student_id: str, operant: str | None = None,
) -> pd.DataFrame:
    """End-of-day running total of mastered targets for a student.

    Pass ``operant`` to scope the series to a single verbal operant. Backfills
    events from current target state (idempotent) so old data still shows up,
    and annotates legacy events with their domain. The last event of each day
    determines that day's total.
    """
    ensure_mastery_event_backfill()
    events = [e for e in load_mastery_events() if e["student_id"] == student_id]
    if operant is not None:
        targets_lookup = {t["id"]: t for t in load_targets()}
        events = [
            e for e in events
            if (e.get("domain") or targets_lookup.get(e["target_id"], {}).get("domain", "")) == operant
        ]
    if not events:
        return pd.DataFrame({"date": [], "total": []})
    events.sort(key=lambda e: (e["date"], e.get("recorded_at", "")))
    rows = []
    running = 0
    for e in events:
        running += 1 if e["type"] == "mastered" else -1
        rows.append({"date": e["date"], "total": running})
    df = pd.DataFrame(rows)
    df = df.groupby("date", as_index=False).last()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    # Fill every day from the first event through today so the x-axis is
    # consecutive dates and the line stays flat on days with no events.
    first = df["date"].min()
    end = max(df["date"].max(), pd.Timestamp(date.today()))
    full = pd.DataFrame({"date": pd.date_range(first, end, freq="D")})
    df = full.merge(df, on="date", how="left")
    df["total"] = df["total"].ffill().fillna(0).astype(int)
    return df


def _fmt_date(iso_str) -> str:
    """Format a YYYY-MM-DD (or date / datetime) value as MM/DD/YYYY.

    Returns the input as a string on failure so callers stay safe.
    """
    if iso_str is None or iso_str == "":
        return ""
    try:
        if isinstance(iso_str, (date, datetime)):
            d = iso_str.date() if isinstance(iso_str, datetime) else iso_str
        else:
            d = date.fromisoformat(str(iso_str)[:10])
        return d.strftime("%m/%d/%Y")
    except Exception:
        return str(iso_str)


def mastered_date_label(target: dict) -> str:
    """Date string for displays — appends '(PO)' when the route was probe-out."""
    d = target.get("mastered_date") or ""
    if not d:
        return ""
    label = _fmt_date(d)
    return f"{label} (PO)" if target.get("mastered_via") == "PO" else label


# ── Pages ────────────────────────────────────────────────────────────────────
def _render_probe_entry_operant(
    sid: str,
    domain: str,
    lists: dict[str, list[dict]],
    targets: list[dict],
    probes: list[dict],
    probe_date: date,
    clinician: str,
) -> None:
    """Render one operant's probe rows + add controls. Called inside a tab."""
    for skill_list in sorted(lists, key=lambda s: (s == "", s.lower())):
        if skill_list:
            st.markdown(f"**{skill_list}**")
        for t in lists[skill_list]:
            existing = already_probed_today(probes, t["id"], probe_date)
            streak = consecutive_y_streak(t["id"], probes)
            need = mastery_n_for(t)
            edit_open = st.session_state.get("editing_target_id") == t["id"]
            error_menu_open = st.session_state.get("pending_error") == (t["id"], probe_date.isoformat())
            cols = st.columns([4, 1, 1, 1, 1, 1])
            with cols[0]:
                streak_badge = f"Y streak: **{streak}/{need}**"
                if streak >= need:
                    streak_badge = f"🎉 **READY TO MASTER** ({streak}/{need})"
                label = f"{t['description']}  \n<span style='color:#666'>{streak_badge}</span>"
                if existing:
                    today_resp = existing["response"]
                    etype = existing.get("error_type")
                    if etype:
                        today_resp = f"{today_resp} ({ERROR_SUBTYPES.get(etype, etype)})"
                    elif today_resp == "NR":
                        today_resp = "N (No response)"
                    label = f"✔ {t['description']}  ·  today: **{today_resp}**  \n<span style='color:#666'>{streak_badge}</span>"
                desc_inner = st.columns([8, 2])
                with desc_inner[0]:
                    st.markdown(label, unsafe_allow_html=True)
                with desc_inner[1]:
                    edit_label = "Close" if edit_open else "Edit"
                    if st.button(
                        edit_label,
                        key=f"pe_edbtn_{t['id']}_{probe_date}",
                        width="stretch",
                        help="Edit this target",
                    ):
                        st.session_state["editing_target_id"] = None if edit_open else t["id"]
                        st.rerun()
            for i, resp in enumerate(["Y", "N", "PO", "NP", "Hold"]):
                with cols[i + 1]:
                    btn_label = resp
                    if resp == "N":
                        is_current = bool(existing) and existing["response"] in ("N", "NR")
                    elif resp == "Hold":
                        is_current = False
                    else:
                        is_current = bool(existing) and existing["response"] == resp
                    if resp == "Hold":
                        help_text = "Place this target on hold (removes from probe list, records today's date)."
                    elif resp == "N":
                        help_text = "Error — pick subtype"
                    else:
                        help_text = RESPONSE_LABEL[resp]
                    if resp == "Y":
                        st.markdown('<div class="cpt-y-btn"></div>', unsafe_allow_html=True)
                    elif resp == "N":
                        st.markdown('<div class="cpt-red-btn"></div>', unsafe_allow_html=True)
                    if st.button(
                        btn_label,
                        key=f"probe_{t['id']}_{resp}_{probe_date}",
                        type="primary" if is_current else "secondary",
                        width="stretch",
                        help=help_text,
                    ):
                        if resp == "Hold":
                            all_t = load_targets()
                            for x in all_t:
                                if x["id"] == t["id"]:
                                    x["status"] = "On Hold"
                                    x["on_hold_date"] = date.today().isoformat()
                                    break
                            save_targets(all_t)
                            st.session_state.pop("pending_error", None)
                            st.session_state["_probe_saved_msg"] = (
                                f"{t['description']} placed on hold."
                            )
                            st.toast(f"{t['description']} placed on hold.")
                            st.rerun()
                        elif is_current:
                            clear_probe(t["id"], probe_date)
                            st.session_state.pop("pending_error", None)
                            st.session_state["_probe_saved_msg"] = (
                                f"Cleared today's probe for {t['description']}."
                            )
                            st.rerun()
                        elif resp == "N":
                            pending_val = (t["id"], probe_date.isoformat())
                            if st.session_state.get("pending_error") == pending_val:
                                st.session_state.pop("pending_error", None)
                            else:
                                st.session_state["pending_error"] = pending_val
                            st.rerun()
                        else:
                            record_probe(t["id"], probe_date, resp, clinician)
                            if resp == "PO":
                                mastered = apply_po_mastery(t["id"])
                                if mastered:
                                    st.session_state["_just_mastered"] = f"{mastered['description']} (probed out)"
                            else:
                                mastered = apply_auto_mastery(t["id"])
                                if mastered:
                                    st.session_state["_just_mastered"] = mastered["description"]
                            st.session_state.pop("pending_error", None)
                            st.session_state["_probe_saved_msg"] = (
                                f"Saved {t['description']} — {btn_label}."
                            )
                            st.rerun()
            if error_menu_open:
                with st.container(border=True):
                    st.markdown("**Error type:**")
                    err_options = [
                        ("No response", "NR", None),
                        ("Incorrect", "N", "incorrect"),
                        ("Scrolling", "N", "scrolling"),
                    ]
                    ec = st.columns(len(err_options) + 1)
                    for j, (lbl, code, etype) in enumerate(err_options):
                        with ec[j]:
                            st.markdown('<div class="cpt-red-btn"></div>', unsafe_allow_html=True)
                            if st.button(
                                lbl,
                                key=f"err_{t['id']}_{probe_date}_{etype or 'nr'}",
                                width="stretch",
                                type="primary",
                            ):
                                record_probe(t["id"], probe_date, code, clinician, error_type=etype)
                                mastered = apply_auto_mastery(t["id"])
                                if mastered:
                                    st.session_state["_just_mastered"] = mastered["description"]
                                st.session_state.pop("pending_error", None)
                                st.session_state["_probe_saved_msg"] = (
                                    f"Saved {t['description']} — N ({lbl})."
                                )
                                st.rerun()
                    with ec[-1]:
                        if st.button(
                            "Cancel", key=f"err_cancel_{t['id']}_{probe_date}", width="stretch",
                        ):
                            st.session_state.pop("pending_error", None)
                            st.rerun()
            if edit_open:
                with st.container(border=True):
                    st.markdown(f"**Edit:** {t['description']}")
                    _render_edit_target_form(
                        t, targets, key_prefix=f"pe_ed_{t['id']}_{probe_date}",
                    )
        add_label = f"➕ Add target to {skill_list}" if skill_list else "➕ Add target"
        with st.expander(add_label):
            _render_add_target_form(
                sid, default_domain=domain, default_skill_list=skill_list,
                key_prefix=f"pe_{domain}_{skill_list or '_root'}", targets=targets,
            )


def page_probe_entry():
    students = load_students()
    targets = load_targets()
    probes = load_probes()

    if not students:
        st.header("Cold Probe Entry")
        st.info("Add a student on the **Students** page to begin.")
        return

    sid = current_sid(students)
    st.header(f"Cold Probe Entry · {student_name(students, sid)}")

    saved_msg = st.session_state.pop("_probe_saved_msg", None)
    if saved_msg:
        st.markdown(
            f'<div class="cpt-save-ribbon">✓ {saved_msg}</div>',
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns([1, 1])
    with col1:
        probe_date = st.date_input("Probe date", value=date.today())
    with col2:
        clinician = st.text_input("Clinician initials", value=st.session_state.get("clinician", ""))
        st.session_state["clinician"] = clinician

    session = get_session(sid, probe_date.isoformat())
    edit_key = f"editing_session_{sid}_{probe_date.isoformat()}"
    if session and st.session_state.get(edit_key):
        with st.container(border=True):
            st.markdown("**✎ Edit session**")
            new_name = st.text_input(
                "Session name", value=session.get("name", ""),
                key=f"sessname_{session['id']}",
            )
            new_clin = st.text_input(
                "Clinician initials", value=session.get("clinician", ""),
                key=f"sessclin_{session['id']}",
            )
            new_notes = st.text_area(
                "Notes", value=session.get("notes", ""), height=80,
                key=f"sessnotes_{session['id']}",
            )
            sc1, sc2 = st.columns([1, 1])
            with sc1:
                if st.button(
                    "Save", key=f"sesssave_{session['id']}", type="primary", width="stretch",
                ):
                    update_session(
                        sid, probe_date.isoformat(),
                        name=new_name.strip() or session.get("name") or _default_session_name(probe_date.isoformat()),
                        clinician=new_clin.strip(),
                        notes=new_notes.strip(),
                    )
                    if new_clin.strip():
                        st.session_state["clinician"] = new_clin.strip()
                    st.session_state.pop(edit_key, None)
                    st.rerun()
            with sc2:
                if st.button(
                    "Cancel", key=f"sesscancel_{session['id']}", width="stretch",
                ):
                    st.session_state.pop(edit_key, None)
                    st.rerun()
    elif session:
        is_completed = bool(session.get("ended_at"))
        badge_color = "#10b981" if is_completed else "#f59e0b"
        badge_bg = "#d1fae5" if is_completed else "#fef3c7"
        badge_label = "✅ Completed" if is_completed else "🟡 In Progress"
        with st.container(border=True):
            head = st.columns([6, 1])
            with head[0]:
                st.markdown(
                    f"### {session.get('name') or _default_session_name(probe_date.isoformat())} "
                    f"<span style='font-size:0.55em; padding:0.2em 0.7em; border-radius:999px; "
                    f"background:{badge_bg}; color:{badge_color}; vertical-align:middle; "
                    f"margin-left:0.4em;'>{badge_label}</span>",
                    unsafe_allow_html=True,
                )
                bits = []
                if session.get("started_at"):
                    try:
                        d_started = datetime.fromisoformat(session["started_at"])
                        bits.append(f"Started {d_started.strftime('%m/%d/%Y at %-I:%M %p')}")
                    except ValueError:
                        pass
                if is_completed and session.get("ended_at"):
                    try:
                        d_ended = datetime.fromisoformat(session["ended_at"])
                        bits.append(f"Ended {d_ended.strftime('%-I:%M %p')}")
                    except ValueError:
                        pass
                if session.get("clinician"):
                    bits.append(f"Clinician: **{session['clinician']}**")
                if bits:
                    st.caption(" · ".join(bits))
                if session.get("notes"):
                    st.caption(f"📝 {session['notes']}")
            with head[1]:
                if st.button(
                    "✎ Edit", key=f"sessedit_{session['id']}", width="stretch",
                    help="Rename, change clinician, or add notes.",
                ):
                    st.session_state[edit_key] = True
                    st.rerun()
    else:
        st.info(
            f"📝 No session yet for {probe_date.strftime('%m/%d/%Y')}. A session will start automatically "
            "when you record your first probe."
        )

    active = targets_for(sid, targets)
    st.caption("Cold probe = first-trial, no prompt, no reinforcement contingent on the response.")

    if not active:
        st.info("No active targets for this student yet.")
        with st.expander("➕ Add the first target", expanded=True):
            _render_add_target_form(
                sid, default_domain=None, default_skill_list=None,
                key_prefix="pe_newop_empty", targets=targets,
            )
    else:
        grouped = group_by_operant_then_list(active)
        for domain in sorted(grouped):
            st.subheader(domain)
            _render_probe_entry_operant(
                sid, domain, grouped[domain], targets, probes, probe_date, clinician,
            )
        st.divider()
        with st.expander("➕ New operant (start a new section)"):
            st.caption("Add the first target for an operant this student doesn't have yet.")
            _render_add_target_form(
                sid, default_domain=None, default_skill_list=None,
                key_prefix="pe_newop", targets=targets,
            )

    if "_just_mastered" in st.session_state:
        st.success(f"🎉 Mastered: **{st.session_state.pop('_just_mastered')}** — moved to the mastery log.")
        st.balloons()

    todays = [p for p in load_probes() if p["date"] == probe_date.isoformat()
              and any(t["id"] == p["target_id"] and t["student_id"] == sid for t in targets)]
    st.divider()
    # Re-read in case probes recorded above auto-started a session.
    session = get_session(sid, probe_date.isoformat())
    is_completed = bool(session and session.get("ended_at"))
    if todays:
        st.caption(f"{len(todays)} probes logged for {student_name(students, sid)} on {probe_date.strftime('%m/%d/%Y')}.")
        end_pending_key = f"_end_session_pending_{sid}_{probe_date.isoformat()}"
        if is_completed:
            reopen_col, _ = st.columns([1, 4])
            with reopen_col:
                if st.button(
                    "↩ Reopen Session",
                    key=f"reopen_{sid}_{probe_date}",
                    help="Mark this session as in-progress again so you can edit data.",
                    width="stretch",
                ):
                    reopen_session(sid, probe_date.isoformat())
                    st.rerun()
        elif st.session_state.get(end_pending_key):
            st.warning(
                f"**End this session?** It will be marked completed for {probe_date.strftime('%m/%d/%Y')}. "
                "You can always Reopen later if you need to edit."
            )
            yes_col, no_col = st.columns(2)
            with yes_col:
                if st.button(
                    "Yes, end session",
                    key=f"end_confirm_{sid}_{probe_date}",
                    type="primary", width="stretch",
                ):
                    end_session(sid, probe_date.isoformat(), clinician)
                    st.session_state.pop(end_pending_key, None)
                    st.rerun()
            with no_col:
                if st.button(
                    "Cancel", key=f"end_cancel_{sid}_{probe_date}", width="stretch",
                ):
                    st.session_state.pop(end_pending_key, None)
                    st.rerun()
        else:
            if st.button(
                "🛑 End Session",
                type="primary", width="stretch",
                key=f"end_{sid}_{probe_date}",
                help="Marks this day's session as completed.",
            ):
                st.session_state[end_pending_key] = True
                st.rerun()
        if is_completed:
            counts = {r: sum(1 for p in todays if p["response"] == r) for r in RESPONSES}
            yn_total = counts["Y"] + counts["N"]
            pct_y = round(100 * counts["Y"] / yn_total, 1) if yn_total else 0.0
            st.success(
                f"Session completed — **{student_name(students, sid)}** · {probe_date.strftime('%m/%d/%Y')} · "
                f"**{len(todays)}** probes · "
                f"Y: {counts['Y']} · N: {counts['N']} · "
                f"NR: {counts['NR']} · PO: {counts['PO']} · NP: {counts['NP']} · "
                f"{pct_y}% independent (Y/Y+N)"
            )
            t_lookup = {t["id"]: t for t in targets}
            df_day = pd.DataFrame([{
                "date": p["date"],
                "student": student_name(students, sid),
                "operant": t_lookup.get(p["target_id"], {}).get("domain", ""),
                "skill_list": t_lookup.get(p["target_id"], {}).get("skill_list", ""),
                "target": t_lookup.get(p["target_id"], {}).get("description", ""),
                "response": p["response"],
                "error_type": p.get("error_type", ""),
                "clinician": p.get("clinician", ""),
                "recorded_at": p.get("recorded_at", ""),
            } for p in todays]).sort_values(["operant", "skill_list", "target"])
            st.dataframe(df_day, width="stretch", hide_index=True)
            dl_csv, dl_pdf = st.columns(2)
            with dl_csv:
                st.download_button(
                    "📄 Download day as CSV",
                    df_day.to_csv(index=False).encode("utf-8"),
                    file_name=f"cold_probes_{student_name(students, sid).replace(' ', '_')}_{probe_date}.csv",
                    mime="text/csv",
                    width="stretch",
                )
            with dl_pdf:
                st.download_button(
                    "📄 Download session PDF",
                    data=build_session_pdf(
                        sid, probe_date.isoformat(), students, targets,
                        load_probes(), load_behaviors(), load_behavior_records(),
                        get_session(sid, probe_date.isoformat()),
                    ),
                    file_name=f"session_{student_name(students, sid).replace(' ', '_')}_{probe_date}.pdf",
                    mime="application/pdf",
                    width="stretch",
                )
    else:
        st.caption("No probes logged yet for this day.")


ERROR_SUBTYPES = {
    "no_response": "No response",
    "incorrect": "Incorrect",
    "scrolling": "Scrolling",
}


def record_probe(
    target_id: str, day: date, response: str, clinician: str,
    error_type: str | None = None,
) -> None:
    probes = load_probes()
    probes = [p for p in probes if not (p["target_id"] == target_id and p["date"] == day.isoformat())]
    entry = {
        "id": new_id(),
        "target_id": target_id,
        "date": day.isoformat(),
        "response": response,
        "clinician": clinician or "",
        "recorded_at": now_iso(),
    }
    if error_type:
        entry["error_type"] = error_type
    probes.append(entry)
    save_probes(probes)
    # Auto-start a session the moment any probe is logged for the day.
    target = next((t for t in load_targets() if t["id"] == target_id), None)
    if target:
        ensure_session_started(target["student_id"], day.isoformat(), clinician)


def clear_probe(target_id: str, day: date) -> None:
    probes = [p for p in load_probes()
              if not (p["target_id"] == target_id and p["date"] == day.isoformat())]
    save_probes(probes)


def page_home():
    students = load_students()
    targets = load_targets()
    probes = load_probes()

    st.markdown("## Repertiores")
    st.caption("Start a session by creating a new student or picking up where you left off.")
    st.write("")

    left, right = st.columns([2, 1], gap="large")

    with left:
        st.markdown("#### Continue with an existing student")
        if not students:
            st.info("No students yet — create one on the right to get started.")
        else:
            cols = st.columns(2)
            for i, s in enumerate(sorted(students, key=lambda x: x["name"].lower())):
                tcount = sum(1 for t in targets if t["student_id"] == s["id"])
                mcount = sum(1 for t in targets if t["student_id"] == s["id"] and t["status"] == "Mastered")
                last = max(
                    (p["date"] for p in probes
                     if any(t["id"] == p["target_id"] and t["student_id"] == s["id"] for t in targets)),
                    default="",
                )
                with cols[i % 2]:
                    with st.container(border=True):
                        st.markdown(f"### {s['name']}")
                        st.caption(
                            f"{tcount} targets · {mcount} mastered"
                            + (f" · last probe {last}" if last else " · no probes yet")
                        )
                        if st.button("Open", key=f"home_open_{s['id']}", type="primary", width="stretch"):
                            st.session_state["_pending_student"] = s["id"]
                            st.session_state["page"] = "Dashboard"
                            st.rerun()

    with right:
        st.markdown("#### ➕ New student")
        with st.form("home_add_student", clear_on_submit=True, border=True):
            name = st.text_input("Name or initials", placeholder="e.g., J.D.")
            dob = st.date_input("Date of birth (optional)", value=None)
            notes = st.text_area("Notes (optional)", height=100)
            if st.form_submit_button("Create student", type="primary", width="stretch"):
                if not name.strip():
                    st.error("Name is required.")
                else:
                    students.append({
                        "id": new_id(),
                        "name": name.strip(),
                        "dob": dob.isoformat() if dob else "",
                        "notes": notes.strip(),
                        "created_at": now_iso(),
                    })
                    save_students(students)
                    st.session_state["_pending_student"] = students[-1]["id"]
                    st.session_state["page"] = "Dashboard"
                    st.rerun()

    if students:
        st.divider()
        with st.expander("✎ Edit or remove a student"):
            sid_edit = st.selectbox(
                "Student",
                options=[s["id"] for s in students],
                format_func=lambda i: student_name(students, i),
                key="home_edit_pick",
            )
            rec = next(s for s in students if s["id"] == sid_edit)
            edit_name = st.text_input("Name", value=rec["name"], key="home_edit_name")
            edit_dob_value = rec.get("dob", "")
            edit_dob_default = (
                date.fromisoformat(edit_dob_value) if edit_dob_value else None
            )
            edit_dob = st.date_input(
                "Date of birth (optional)",
                value=edit_dob_default,
                key="home_edit_dob",
            )
            edit_notes = st.text_area(
                "Notes", value=rec.get("notes", ""), key="home_edit_notes", height=80,
            )
            ec1, ec2 = st.columns(2)
            with ec1:
                if st.button(
                    "Save changes", key="home_edit_save",
                    type="primary", width="stretch",
                ):
                    rec["name"] = edit_name.strip() or rec["name"]
                    rec["dob"] = edit_dob.isoformat() if edit_dob else ""
                    rec["notes"] = edit_notes.strip()
                    save_students(students)
                    st.toast("Saved.")
                    st.rerun()
            with ec2:
                pending_key = f"home_pending_del_{sid_edit}"
                if not st.session_state.get(pending_key):
                    if st.button(
                        "Delete student", key="home_edit_del",
                        width="stretch",
                    ):
                        st.session_state[pending_key] = True
                        st.rerun()
                else:
                    st.warning(
                        f"**Remove `{rec['name']}` from the roster?**  \n"
                        "Their targets, probes, sessions, and behavior records stay on disk."
                    )
                    yc, nc = st.columns(2)
                    with yc:
                        if st.button(
                            "Yes, delete",
                            key="home_edit_del_yes",
                            type="primary", width="stretch",
                        ):
                            save_students(
                                [s for s in students if s["id"] != sid_edit]
                            )
                            st.session_state.pop(pending_key, None)
                            st.toast(f"Removed {rec['name']}.")
                            st.rerun()
                    with nc:
                        if st.button(
                            "Cancel",
                            key="home_edit_del_no",
                            width="stretch",
                        ):
                            st.session_state.pop(pending_key, None)
                            st.rerun()


def _render_add_target_form(
    sid: str,
    default_domain: str | None,
    key_prefix: str,
    targets: list[dict],
    default_skill_list: str | None = None,
) -> None:
    """Inline add-target form.

    default_domain: pin operant to a specific value, or None to let the user pick.
    default_skill_list: pin the skill list to a value (e.g., 'Tacts of Nouns'),
      pass '' to pin to no list, or None to show a text input.
    """
    form_key = f"add_{key_prefix}"
    with st.form(form_key, clear_on_submit=True, border=False):
        c1, c2 = st.columns([3, 1])
        with c1:
            desc = st.text_area(
                "Target(s)",
                placeholder=(
                    'One target per line — paste multiple to add a batch:\n'
                    'SD: "What do you want?" — fruit punch\n'
                    'SD: "What is your name?" — Christian'
                ),
                label_visibility="collapsed",
                height=110,
            )
        with c2:
            mastery_n = st.number_input(
                "Cons. Y", min_value=1, max_value=20, value=DEFAULT_MASTERY_N, step=1,
                label_visibility="collapsed",
            )
        if default_domain is None:
            domain = st.selectbox("Verbal operant", DOMAINS, key=f"{key_prefix}_dom")
        else:
            domain = default_domain
        if default_skill_list is None:
            existing_lists: list[str] = []
            if default_domain is not None:
                existing_lists = sorted({
                    (t.get("skill_list") or "").strip()
                    for t in targets
                    if t["student_id"] == sid
                    and t["domain"] == default_domain
                    and (t.get("skill_list") or "").strip()
                })
            if existing_lists:
                NONE_OPT = "— No list —"
                NEW_OPT = "➕ New list…"
                options = [NONE_OPT, *existing_lists, NEW_OPT]
                picked = st.selectbox(
                    "Skill list",
                    options=options,
                    key=f"{key_prefix}_listpick",
                )
                new_name = st.text_input(
                    "New list name",
                    placeholder="Only used when '➕ New list…' is selected",
                    key=f"{key_prefix}_listnew",
                )
                if picked == NONE_OPT:
                    skill_list = ""
                elif picked == NEW_OPT:
                    skill_list = new_name.strip()
                else:
                    skill_list = picked
            else:
                skill_list = st.text_input(
                    "Skill list (optional)",
                    placeholder="e.g., Tacts of Nouns — leave blank for none",
                    key=f"{key_prefix}_list",
                )
        else:
            skill_list = default_skill_list
        if default_domain is None:
            label = "Add target"
        elif default_skill_list:
            label = f"Add to {default_domain} → {default_skill_list}"
        else:
            label = f"Add to {default_domain}"
        submitted = st.form_submit_button(label, type="primary", width="stretch")
        if submitted:
            lines = [ln.strip() for ln in desc.splitlines() if ln.strip()]
            if not lines:
                st.error("At least one target description required.")
            else:
                for line in lines:
                    targets.append({
                        "id": new_id(),
                        "student_id": sid,
                        "description": line,
                        "domain": domain,
                        "skill_list": skill_list.strip(),
                        "mastery_n": int(mastery_n),
                        "mastery_criterion": "",
                        "status": "In Acquisition",
                        "mastered_date": "",
                    })
                save_targets(targets)
                loc = (
                    f" → **{skill_list.strip()}**"
                    if skill_list.strip() else ""
                )
                n_label = "target" if len(lines) == 1 else "targets"
                st.session_state["_last_add_msg"] = (
                    f"✓ Added **{len(lines)}** {n_label} to **{domain}**{loc}."
                )
                st.toast(f"Added {len(lines)} {n_label}.")
                st.rerun()


def _render_edit_target_form(t: dict, targets: list[dict], key_prefix: str) -> None:
    """Editor for a single target: description, list, operant, status, criterion, delete."""
    new_desc = st.text_input("Description", value=t["description"], key=f"{key_prefix}_desc")
    c_dom, c_list = st.columns(2)
    with c_dom:
        new_domain = st.selectbox(
            "Operant", DOMAINS, index=DOMAINS.index(t["domain"]), key=f"{key_prefix}_dom",
        )
    with c_list:
        new_list = st.text_input(
            "Skill list (optional)", value=t.get("skill_list", ""), key=f"{key_prefix}_list",
        )
    c_stat, c_n = st.columns(2)
    with c_stat:
        new_status = st.selectbox(
            "Status", STATUSES, index=STATUSES.index(t["status"]), key=f"{key_prefix}_stat",
        )
    with c_n:
        new_n = st.number_input(
            "Consecutive Y to master", min_value=1, max_value=20,
            value=mastery_n_for(t), step=1, key=f"{key_prefix}_n",
        )
    new_crit = st.text_input(
        "Mastery notes", value=t.get("mastery_criterion", ""), key=f"{key_prefix}_crit",
    )
    save_col, del_col = st.columns([1, 1])
    with save_col:
        if st.button("Save", key=f"{key_prefix}_save", type="primary", width="stretch"):
            previously_mastered = t["status"] == "Mastered"
            final_desc = new_desc.strip() or t["description"]
            t["description"] = final_desc
            t["domain"] = new_domain
            t["skill_list"] = new_list.strip()
            t["status"] = new_status
            t["mastery_n"] = int(new_n)
            t["mastery_criterion"] = new_crit.strip()
            if new_status == "Mastered" and not previously_mastered and not t.get("mastered_date"):
                t["mastered_date"] = date.today().isoformat()
            if new_status != "Mastered":
                t["mastered_date"] = ""
            save_targets(targets)
            if new_status == "Mastered" and not previously_mastered:
                log_mastery_event(
                    t["student_id"], t["id"], "mastered",
                    t.get("mastered_date") or date.today().isoformat(),
                )
            elif previously_mastered and new_status != "Mastered":
                log_mastery_event(t["student_id"], t["id"], "unmastered")
            # Ribbon + close the inline edit panel so we return to the
            # probe-entry view.
            st.session_state["_probe_saved_msg"] = (
                f"Target updated — {final_desc}."
            )
            st.session_state["editing_target_id"] = None
            st.rerun()
    with del_col:
        if st.button("Delete", key=f"{key_prefix}_del", width="stretch"):
            removed_desc = t["description"]
            delete_targets({t["id"]}, reason=f"single_{t.get('domain','')}")
            st.session_state["_probe_saved_msg"] = (
                f"Target deleted — {removed_desc}. (Undo available for "
                f"{UNDO_WINDOW_SECONDS // 60} min.)"
            )
            st.session_state["editing_target_id"] = None
            st.rerun()


def group_by_operant_then_list(targets: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """Returns {operant: {skill_list: [targets...]}}.

    Empty skill_list maps to '' (rendered without a sublist header by callers).
    """
    out: dict[str, dict[str, list[dict]]] = {}
    for t in targets:
        out.setdefault(t["domain"], {}).setdefault(t.get("skill_list", "") or "", []).append(t)
    return out


def _render_operant_body(
    sid: str, op: str, op_lists: dict[str, list[dict]],
    targets: list[dict], probes: list[dict],
) -> None:
    """Render all skill lists + targets for a single operant."""
    op_targets = [t for sublist in op_lists.values() for t in sublist]
    n_active = sum(1 for t in op_targets if t["status"] == "In Acquisition")
    n_mastered = sum(1 for t in op_targets if t["status"] == "Mastered")
    n_planned = sum(1 for t in op_targets if t["status"] == "Planned")
    summary = f"{n_active} in acquisition · {n_mastered} mastered"
    if n_planned:
        summary += f" · {n_planned} planned"
    st.caption(summary)
    avg_d = avg_days_to_mastery(op_targets, probes)
    if avg_d is not None:
        n_eligible = sum(
            1 for t in op_targets
            if t.get("status") == "Mastered"
            and t.get("mastered_date")
            and first_data_date(t["id"], probes)
        )
        st.caption(
            f"⏱ **Avg rate of acquisition: {avg_d:.1f} days** "
            f"from introduction to mastery (n = {n_eligible})"
        )

    # ── Duplicates within this operant (skill list ignored) ──────────────────
    dup_map: dict[str, list[dict]] = {}
    for t in op_targets:
        dup_map.setdefault(t["description"].strip().lower(), []).append(t)
    dup_map = {k: v for k, v in dup_map.items() if len(v) > 1}
    if dup_map:
        n_extra = sum(len(v) - 1 for v in dup_map.values())
        with st.expander(
            f"🔁 {len(dup_map)} duplicate description(s) in {op} "
            f"({n_extra} extra cop{'y' if n_extra == 1 else 'ies'})",
            expanded=False,
        ):
            st.caption(
                "Targets whose description repeats within this operant (skill "
                "list ignored). Check the copies to remove — leave at least one "
                "per group. Removing a mastered copy also corrects the "
                "cumulative count."
            )
            d_rows: list[dict] = []
            d_ids: list[str] = []
            for desc, members in sorted(dup_map.items()):
                for m in sorted(
                    members,
                    key=lambda t: ((t.get("skill_list") or "").lower(), t.get("status", "")),
                ):
                    d_ids.append(m["id"])
                    d_rows.append({
                        "Select": False,
                        "Target": m["description"],
                        "List": m.get("skill_list", "") or "—",
                        "Status": m.get("status", ""),
                        "Mastered": mastered_date_label(m) or "—",
                    })
            d_ver = st.session_state.get(f"dup_ver_{sid}_{op}", 0)
            d_edited = st.data_editor(
                pd.DataFrame(d_rows),
                width="stretch",
                hide_index=True,
                key=f"dup_editor_{sid}_{op}_{d_ver}",
                column_config={
                    "Select": st.column_config.CheckboxColumn("✓", default=False),
                    "Target": st.column_config.TextColumn(disabled=True),
                    "List": st.column_config.TextColumn(disabled=True),
                    "Status": st.column_config.TextColumn(disabled=True),
                    "Mastered": st.column_config.TextColumn(disabled=True),
                },
            )
            d_sel = [
                d_ids[i]
                for i, r in enumerate(d_edited.to_dict("records"))
                if r.get("Select")
            ]
            d_pending = f"dup_pending_{sid}_{op}"
            if not st.session_state.get(d_pending):
                if st.button(
                    f"🗑️ Remove {len(d_sel)} selected duplicate(s)",
                    key=f"dup_del_btn_{sid}_{op}",
                    disabled=not d_sel,
                    width="stretch",
                ):
                    st.session_state[d_pending] = d_sel
                    st.rerun()
            else:
                ids_set = set(st.session_state[d_pending])
                sel_targets = [t for t in op_targets if t["id"] in ids_set]
                n_mast = sum(1 for t in sel_targets if t.get("status") == "Mastered")
                note = (
                    f" {n_mast} mastered will drop the cumulative count."
                    if n_mast else ""
                )
                st.warning(f"**Remove {len(ids_set)} duplicate target(s)?**{note}")
                cyes, cno = st.columns(2)
                with cyes:
                    if st.button(
                        "Yes, remove",
                        key=f"dup_del_yes_{sid}_{op}",
                        type="primary", width="stretch",
                    ):
                        for t in sel_targets:
                            if t.get("status") == "Mastered":
                                log_mastery_event(
                                    t["student_id"], t["id"], "unmastered",
                                )
                        delete_targets(ids_set, reason=f"dedup_{op}")
                        st.session_state.pop(d_pending, None)
                        st.session_state[f"dup_ver_{sid}_{op}"] = d_ver + 1
                        st.toast(
                            f"Removed {len(ids_set)} duplicate(s). "
                            "Undo at the top of the page."
                        )
                        st.rerun()
                with cno:
                    if st.button(
                        "Cancel",
                        key=f"dup_del_no_{sid}_{op}",
                        width="stretch",
                    ):
                        st.session_state.pop(d_pending, None)
                        st.rerun()

    for skill_list in sorted(op_lists, key=lambda s: (s == "", s.lower())):
        sublist = op_lists[skill_list]
        if skill_list:
            st.markdown(f"#### {skill_list}")
        active_targets = [t for t in sublist if t["status"] != "Planned"]
        planned_targets = [t for t in sublist if t["status"] == "Planned"]
        ordered = sorted(active_targets, key=lambda t: (
            0 if t["status"] == "In Acquisition" else (1 if t["status"] == "Maintenance" else 2),
            (t.get("mastered_date") or ""),
            t["description"],
        ))
        if ordered:
            df = pd.DataFrame([{
                "Select": False,
                "#": i + 1,
                "Target": t["description"],
                "Date Introduced": _fmt_date(first_data_date(t["id"], probes)) or "—",
                "Date Mastered": mastered_date_label(t) or "—",
                "Status": (
                    f"On Hold (since {t['on_hold_date']})"
                    if t["status"] == "On Hold" and t.get("on_hold_date")
                    else t["status"]
                ),
                "Y streak": consecutive_y_streak(t["id"], probes) if t["status"] == "In Acquisition" else "—",
                "Criterion": f"{mastery_n_for(t)} cons. Y",
            } for i, t in enumerate(ordered)])
            list_key = skill_list or "_root"
            editor_key = f"selectdf_{op}_{list_key}"
            edited = st.data_editor(
                df,
                width="stretch",
                hide_index=True,
                key=editor_key,
                column_config={
                    "Select": st.column_config.CheckboxColumn("✓", default=False),
                    "#": st.column_config.NumberColumn(disabled=True),
                    "Target": st.column_config.TextColumn(disabled=True),
                    "Date Introduced": st.column_config.TextColumn(disabled=True),
                    "Date Mastered": st.column_config.TextColumn(disabled=True),
                    "Status": st.column_config.TextColumn(disabled=True),
                    "Y streak": st.column_config.TextColumn(disabled=True),
                    "Criterion": st.column_config.TextColumn(disabled=True),
                },
            )
            selected_ids = [
                ordered[i]["id"]
                for i, row in enumerate(edited.to_dict("records"))
                if row.get("Select")
            ]
            pending_bulk_key = f"pending_bulk_delete_{op}_{list_key}"
            pending_ids = st.session_state.get(pending_bulk_key)
            if not pending_ids:
                act_save, act_del = st.columns(2)
                with act_save:
                    if st.button(
                        f"💾 Save {len(selected_ids)} to bank",
                        key=f"bulksave_btn_{op}_{list_key}",
                        disabled=not selected_ids,
                        width="stretch",
                        help="Snapshot the checked targets into the cross-student Target Bank.",
                    ):
                        picks = [t for t in ordered if t["id"] in set(selected_ids)]
                        n = len(save_targets_to_bank(
                            picks, source_student_name=student_name(load_students(), sid),
                        ))
                        if n:
                            st.toast(f"Saved {n} target(s) to bank.")
                        else:
                            st.toast("Already in bank — nothing new added.")
                        st.rerun()
                with act_del:
                    if st.button(
                        f"🗑️ Delete {len(selected_ids)} checked target(s)",
                        key=f"bulkdel_btn_{op}_{list_key}",
                        disabled=not selected_ids,
                        width="stretch",
                    ):
                        st.session_state[pending_bulk_key] = selected_ids
                        st.rerun()
            else:
                pending_targets = [t for t in ordered if t["id"] in set(pending_ids)]
                n = len(pending_targets)
                n_mastered = sum(1 for t in pending_targets if t.get("status") == "Mastered")
                drop_note = (
                    f" {n_mastered} mastered will drop the cumulative count."
                    if n_mastered else ""
                )
                st.warning(f"**Delete {n} target(s)?**{drop_note}")
                cy, cn = st.columns(2)
                with cy:
                    if st.button(
                        f"Yes, delete {n}",
                        key=f"bulkdel_yes_{op}_{list_key}",
                        type="primary", width="stretch",
                    ):
                        for t in pending_targets:
                            if t.get("status") == "Mastered":
                                log_mastery_event(
                                    t["student_id"], t["id"], "unmastered",
                                )
                        ids_set = set(pending_ids)
                        delete_targets(ids_set, reason=f"bulk_{op}")
                        st.session_state.pop(pending_bulk_key, None)
                        st.toast(
                            f"Deleted {n} target(s). Undo at the top of the "
                            "page for the next 30 min."
                        )
                        st.rerun()
                with cn:
                    if st.button(
                        "Cancel",
                        key=f"bulkdel_no_{op}_{list_key}",
                        width="stretch",
                    ):
                        st.session_state.pop(pending_bulk_key, None)
                        st.rerun()
        elif not planned_targets:
            st.caption("_No targets in this list yet._")
        if planned_targets:
            list_label = skill_list or "this list"
            with st.expander(
                f"🔜 Planned in {list_label} ({len(planned_targets)})",
                expanded=False,
            ):
                st.caption(
                    "Planned targets aren't probed yet and don't count toward "
                    "current totals or the cumulative mastered chart."
                )
                st.caption(
                    "**Introduce** starts teaching (goes to In Acquisition). "
                    "**Probed out** marks a skill the student already demonstrates — "
                    "it jumps straight to Mastered and counts toward the repertoire "
                    "total, tagged (PO), without teaching probes."
                )
                for pt in sorted(planned_targets, key=lambda t: t["description"].lower()):
                    pcols = st.columns([5, 2, 2])
                    with pcols[0]:
                        st.write(f"• {pt['description']}")
                    with pcols[1]:
                        if st.button(
                            "Introduce",
                            key=f"intro_{pt['id']}",
                            width="stretch",
                            type="primary",
                        ):
                            for x in targets:
                                if x["id"] == pt["id"]:
                                    x["status"] = "In Acquisition"
                                    break
                            save_targets(targets)
                            st.rerun()
                    with pcols[2]:
                        if st.button(
                            "Probed out",
                            key=f"probeout_{pt['id']}",
                            width="stretch",
                            help=(
                                "Student already has this skill. Marks it Mastered "
                                "via probe-out with today's date — no teaching probes."
                            ),
                        ):
                            today_iso = date.today().isoformat()
                            for x in targets:
                                if x["id"] == pt["id"]:
                                    x["status"] = "Mastered"
                                    x["mastered_date"] = today_iso
                                    x["mastered_via"] = "PO"
                                    x["mastered_probe_count"] = 0
                                    break
                            save_targets(targets)
                            log_mastery_event(sid, pt["id"], "mastered", today_iso)
                            st.toast(f"Probed out: {pt['description']}")
                            st.rerun()

        # ── Curriculum from bank (per-list recommendations) ────────────────
        bank_for_list = [
            bnk for bnk in load_target_bank()
            if bnk.get("domain") == op
            and (bnk.get("skill_list") or "").strip() == (skill_list or "").strip()
        ]
        if bank_for_list:
            student_descs_map = {
                t["description"].strip().lower(): t for t in sublist
            }
            n_total = len(bank_for_list)
            n_on_student = sum(
                1 for bnk in bank_for_list
                if bnk["description"].strip().lower() in student_descs_map
            )
            n_mastered = sum(
                1 for bnk in bank_for_list
                if student_descs_map.get(
                    bnk["description"].strip().lower(), {}
                ).get("status") == "Mastered"
            )
            n_remaining = n_total - n_on_student
            list_label = skill_list or "this list"
            header_extra = (
                f" · {n_remaining} suggested" if n_remaining else " · all added"
            )
            with st.expander(
                f"📚 Curriculum from bank — {list_label} "
                f"({n_mastered}/{n_total} mastered{header_extra})",
                expanded=False,
            ):
                st.caption(
                    "These are bank entries for this list. Already-on-student "
                    "items show their current status; remaining items are "
                    "recommended next steps — add them individually as the "
                    "student is ready."
                )
                pct = int(round(100 * n_mastered / n_total)) if n_total else 0
                st.progress(pct / 100 if n_total else 0,
                            text=f"{n_mastered} of {n_total} mastered ({pct}%)")

                def _sort_key(bnk):
                    existing = student_descs_map.get(
                        bnk["description"].strip().lower()
                    )
                    if not existing:
                        order = 0  # suggested first
                    elif existing["status"] == "In Acquisition":
                        order = 1
                    elif existing["status"] == "Planned":
                        order = 2
                    elif existing["status"] == "On Hold":
                        order = 3
                    elif existing["status"] == "Mastered":
                        order = 4
                    else:
                        order = 5
                    return (order, bnk["description"].lower())

                ordered_bank = sorted(bank_for_list, key=_sort_key)
                for bnk in ordered_bank:
                    desc_key = bnk["description"].strip().lower()
                    existing = student_descs_map.get(desc_key)
                    bcols = st.columns([6, 2])
                    with bcols[0]:
                        if existing:
                            status = existing["status"]
                            icon = {
                                "Mastered": "✅",
                                "In Acquisition": "🔄",
                                "Planned": "📅",
                                "On Hold": "⏸",
                                "Maintenance": "🔁",
                            }.get(status, "•")
                            st.write(
                                f"{icon} **{bnk['description']}** — _{status}_"
                            )
                        else:
                            st.write(f"⊕ {bnk['description']}  ·  _suggested_")
                    with bcols[1]:
                        if not existing:
                            if st.button(
                                "Add",
                                key=f"curric_add_{bnk['id']}",
                                type="primary",
                                width="stretch",
                            ):
                                import_bank_to_student([bnk["id"]], sid)
                                st.toast(f"Added: {bnk['description']}")
                                st.rerun()
    st.divider()
    all_in_op = [t for sublist in op_lists.values() for t in sublist]

    # ── Import from Target Bank ─────────────────────────────────────────────
    op_bank_entries = sorted(
        [bnk for bnk in load_target_bank() if bnk.get("domain") == op],
        key=lambda b: (
            (b.get("skill_list") or "").lower(),
            b["description"].lower(),
        ),
    )
    if op_bank_entries:
        with st.expander(
            f"📚 Import from Target Bank ({len(op_bank_entries)} {op} entries)"
        ):
            already_keys = {
                (t["description"].strip().lower(), (t.get("skill_list") or "").strip().lower())
                for t in all_in_op
            }
            list_options = ["All lists"] + sorted({
                (b.get("skill_list") or "").strip() or "— No list —"
                for b in op_bank_entries
            })
            bf1, bf2 = st.columns([1, 1])
            with bf1:
                pick_list = st.selectbox(
                    "Filter by list",
                    options=list_options,
                    key=f"bank_imp_list_{op}",
                )
            with bf2:
                hide_existing = st.checkbox(
                    "Hide entries already on this student",
                    value=True,
                    key=f"bank_imp_hide_{op}",
                )
            shown_entries = []
            for bnk in op_bank_entries:
                bl = (bnk.get("skill_list") or "").strip() or "— No list —"
                if pick_list != "All lists" and bl != pick_list:
                    continue
                key = (
                    bnk["description"].strip().lower(),
                    (bnk.get("skill_list") or "").strip().lower(),
                )
                already = key in already_keys
                if hide_existing and already:
                    continue
                shown_entries.append((bnk, already))

            if not shown_entries:
                st.caption("Nothing to import with the current filter.")
            else:
                imp_ver = st.session_state.get(f"bank_imp_ver_{op}", 0)
                imp_selected = set(
                    st.session_state.get(f"bank_imp_sel_{op}", [])
                )
                shown_ids = [bnk["id"] for bnk, _ in shown_entries]
                ica, icb, _ = st.columns([1, 1, 3])
                with ica:
                    if st.button(
                        "✓ Select all shown",
                        key=f"bank_imp_all_{op}",
                        width="stretch",
                    ):
                        imp_selected.update(shown_ids)
                        st.session_state[f"bank_imp_sel_{op}"] = list(imp_selected)
                        st.session_state[f"bank_imp_ver_{op}"] = imp_ver + 1
                        st.rerun()
                with icb:
                    if st.button(
                        "Clear",
                        key=f"bank_imp_clear_{op}",
                        width="stretch",
                    ):
                        st.session_state[f"bank_imp_sel_{op}"] = []
                        st.session_state[f"bank_imp_ver_{op}"] = imp_ver + 1
                        st.rerun()

                df = pd.DataFrame([{
                    "Select": bnk["id"] in imp_selected,
                    "List": bnk.get("skill_list", "") or "—",
                    "Target": bnk["description"],
                    "Cons. Y": int(bnk.get("mastery_n", DEFAULT_MASTERY_N)),
                    "Already on student": "✓" if already else "",
                } for (bnk, already) in shown_entries])
                edited = st.data_editor(
                    df, width="stretch", hide_index=True,
                    key=f"bank_imp_editor_{op}_{imp_ver}",
                    column_config={
                        "Select": st.column_config.CheckboxColumn("✓", default=False),
                        "List": st.column_config.TextColumn(disabled=True),
                        "Target": st.column_config.TextColumn(disabled=True),
                        "Cons. Y": st.column_config.NumberColumn(disabled=True),
                        "Already on student": st.column_config.TextColumn(disabled=True),
                    },
                )
                updated = set(imp_selected)
                for i, row in enumerate(edited.to_dict("records")):
                    fid = shown_entries[i][0]["id"]
                    if row.get("Select"):
                        updated.add(fid)
                    else:
                        updated.discard(fid)
                if updated != imp_selected:
                    st.session_state[f"bank_imp_sel_{op}"] = list(updated)
                    imp_selected = updated
                picked_for_import = [
                    bid for bid in updated
                    if any(b["id"] == bid for (b, _) in shown_entries)
                ]
                if st.button(
                    f"➕ Add {len(picked_for_import)} target(s) to this student",
                    key=f"bank_imp_add_{op}",
                    type="primary",
                    width="stretch",
                    disabled=not picked_for_import,
                ):
                    n_added = import_bank_to_student(picked_for_import, sid)
                    st.session_state[f"bank_imp_sel_{op}"] = []
                    st.session_state[f"bank_imp_ver_{op}"] = imp_ver + 1
                    sname = student_name(load_students(), sid)
                    n_label = "target" if n_added == 1 else "targets"
                    st.session_state["_last_add_msg"] = (
                        f"✓ Added **{n_added}** {n_label} from the Target Bank "
                        f"to **{sname}** ({op})."
                    )
                    st.toast(f"Added {n_added} {n_label} to {sname}.")
                    st.rerun()

    action_cols = st.columns(4)
    with action_cols[0]:
        with st.expander("➕ Add target"):
            _render_add_target_form(
                sid, default_domain=op, default_skill_list=None,
                key_prefix=f"tgt_add_{op}", targets=targets,
            )
    with action_cols[1]:
        with st.expander("✏️ Edit a target"):
            if not all_in_op:
                st.caption("No targets to edit.")
            else:
                edit_ordered = sorted(all_in_op, key=lambda t: (
                    (t.get("skill_list") or "").lower(), t["description"].lower(),
                ))
                pick_id = st.selectbox(
                    "Target",
                    options=[t["id"] for t in edit_ordered],
                    format_func=lambda i, _o=edit_ordered: (
                        f"[{next((t.get('skill_list') or '—') for t in _o if t['id'] == i)}] "
                        f"{next(t['description'] for t in _o if t['id'] == i)}"
                    ),
                    key=f"edit_pick_{op}",
                )
                pick_target = next(x for x in targets if x["id"] == pick_id)
                _render_edit_target_form(
                    pick_target, targets, key_prefix=f"ed_op_{op}_{pick_id}",
                )
    with action_cols[2]:
        with st.expander(f"⚙️ Manage lists"):
            st.caption("Add a target into a new or existing list.")
            _render_add_target_form(
                sid, default_domain=op, default_skill_list=None,
                key_prefix=f"tgt_newlist_{op}", targets=targets,
            )

            # ── Find & remove duplicates ────────────────────────────────────
            st.markdown("---")
            st.markdown("**🧹 Find duplicate targets**")
            dup_groups: dict[tuple, list[dict]] = {}
            for t in all_in_op:
                key = (
                    t["description"].strip().lower(),
                    (t.get("skill_list") or "").strip().lower(),
                )
                dup_groups.setdefault(key, []).append(t)
            duplicates_to_remove: list[str] = []
            preview: list[dict] = []
            for key, items in dup_groups.items():
                if len(items) < 2:
                    continue
                # Keep the "best" copy: a Mastered one if present, otherwise the
                # earliest. The rest go to removal.
                def _rank(t: dict) -> tuple:
                    return (
                        0 if t.get("status") == "Mastered" else 1,
                        t.get("mastered_date", "") or "",
                        t["id"],
                    )
                ordered_items = sorted(items, key=_rank)
                keeper = ordered_items[0]
                for extra in ordered_items[1:]:
                    duplicates_to_remove.append(extra["id"])
                    preview.append({
                        "Target": extra["description"],
                        "List": extra.get("skill_list", "") or "—",
                        "Duplicate status": extra.get("status", ""),
                        "Keeping": keeper.get("status", ""),
                    })
            if not duplicates_to_remove:
                st.caption("No duplicates found in this operant. ✓")
            else:
                st.warning(
                    f"Found **{len(duplicates_to_remove)}** duplicate "
                    f"target(s) across **{sum(1 for v in dup_groups.values() if len(v) >= 2)}** "
                    "groups."
                )
                st.dataframe(
                    pd.DataFrame(preview),
                    width="stretch", hide_index=True,
                )
                dup_pending_key = f"dup_remove_pending_{op}"
                if not st.session_state.get(dup_pending_key):
                    if st.button(
                        f"🧹 Remove {len(duplicates_to_remove)} duplicate(s)",
                        key=f"dup_remove_{op}",
                        type="primary", width="stretch",
                    ):
                        st.session_state[dup_pending_key] = list(duplicates_to_remove)
                        st.rerun()
                else:
                    pending_ids = st.session_state[dup_pending_key]
                    st.warning(
                        f"**Remove {len(pending_ids)} duplicate target(s)?** "
                        "An undo button will appear at the top of the page "
                        "for 30 min after confirming."
                    )
                    dy, dn = st.columns(2)
                    with dy:
                        if st.button(
                            f"Yes, remove {len(pending_ids)}",
                            key=f"dup_remove_yes_{op}",
                            type="primary", width="stretch",
                        ):
                            removed = delete_targets(
                                set(pending_ids), reason=f"duplicates_{op}",
                            )
                            st.session_state.pop(dup_pending_key, None)
                            st.toast(f"Removed {removed} duplicate(s).")
                            st.rerun()
                    with dn:
                        if st.button(
                            "Cancel",
                            key=f"dup_remove_no_{op}",
                            width="stretch",
                        ):
                            st.session_state.pop(dup_pending_key, None)
                            st.rerun()
            existing_named_lists = sorted({
                (t.get("skill_list") or "").strip()
                for t in all_in_op
                if (t.get("skill_list") or "").strip()
            })
            if existing_named_lists:
                st.markdown("---")
                list_pick = st.selectbox(
                    "Remove a list",
                    options=existing_named_lists,
                    key=f"dellist_pick_{op}",
                    help="Targets in the list keep their data — they just move to '— No list —'.",
                )
                in_list = [
                    t for t in all_in_op
                    if (t.get("skill_list") or "").strip() == list_pick
                ]
                if st.button(
                    f"🗑️ Remove '{list_pick}' ({len(in_list)} target{'s' if len(in_list) != 1 else ''})",
                    key=f"dellist_btn_{op}",
                    width="stretch",
                ):
                    for t in targets:
                        if (
                            t["domain"] == op
                            and (t.get("skill_list") or "").strip() == list_pick
                        ):
                            t["skill_list"] = ""
                    save_targets(targets)
                    st.toast(f"Removed '{list_pick}' — targets moved to no list.")
                    st.rerun()
    with action_cols[3]:
        with st.expander("🗑️ Delete a target"):
            if not all_in_op:
                st.caption("No targets to delete.")
            else:
                del_ordered = sorted(all_in_op, key=lambda t: (
                    t.get("skill_list", "") or "", t["description"],
                ))
                pick_id = st.selectbox(
                    "Target to delete",
                    options=[t["id"] for t in del_ordered],
                    format_func=lambda i, _o=del_ordered: (
                        f"[{next((t.get('skill_list') or '—') for t in _o if t['id'] == i)}] "
                        f"{next(t['description'] for t in _o if t['id'] == i)}"
                    ),
                    key=f"del_pick_{op}",
                )
                pending_key = "pending_delete_target_id"
                confirming = st.session_state.get(pending_key) == pick_id
                if not confirming:
                    if st.button(
                        "🗑️ Delete this target",
                        key=f"del_btn_{op}",
                        width="stretch",
                    ):
                        st.session_state[pending_key] = pick_id
                        st.rerun()
                else:
                    pick_target = next(t for t in del_ordered if t["id"] == pick_id)
                    n_probes = sum(1 for p in probes if p["target_id"] == pick_id)
                    was_mastered = pick_target.get("status") == "Mastered"
                    drop_note = (
                        " Cumulative mastered count will drop by 1." if was_mastered else ""
                    )
                    st.warning(
                        f"**Delete this target?**  \n"
                        f"`{pick_target['description']}`  \n"
                        f"Permanent.{drop_note} {n_probes} probe(s) orphaned."
                    )
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button(
                            "Yes, delete",
                            key=f"del_confirm_{op}",
                            type="primary",
                            width="stretch",
                        ):
                            if was_mastered:
                                log_mastery_event(
                                    pick_target["student_id"], pick_id, "unmastered",
                                )
                            delete_targets({pick_id}, reason=f"single_{op}")
                            st.session_state.pop(pending_key, None)
                            st.success(
                                f"Deleted: {pick_target['description']} "
                                f"(undo at the top of the page)."
                            )
                            st.rerun()
                    with c_no:
                        if st.button(
                            "Cancel",
                            key=f"del_cancel_{op}",
                            width="stretch",
                        ):
                            st.session_state.pop(pending_key, None)
                            st.rerun()

    mastered_in_op = sorted(
        [t for t in op_targets if t["status"] == "Mastered"],
        key=lambda t: ((t.get("mastered_date") or ""), t["description"]),
        reverse=True,
    )
    st.divider()
    st.subheader(f"🏆 Mastered {op}")
    if not mastered_in_op:
        st.caption(f"No mastered {op} targets yet.")
    else:
        df_m = pd.DataFrame([{
            "Select": False,
            "Date Introduced": _fmt_date(first_data_date(t["id"], probes)) or "—",
            "Date Mastered": mastered_date_label(t) or "—",
            "List": t.get("skill_list", "") or "—",
            "Target": t["description"],
            "Probes to mastery": t.get("mastered_probe_count", 0) or 0,
        } for t in mastered_in_op])
        n_po_op = sum(1 for t in mastered_in_op if t.get("mastered_via") == "PO")
        po_caption = (
            f" — {len(mastered_in_op) - n_po_op} taught · {n_po_op} probed out"
            if n_po_op else ""
        )
        st.caption(
            f"**{len(mastered_in_op)}** mastered target(s) in {op}{po_caption}."
        )
        m_editor_key = f"mastered_select_{op}"
        m_edited = st.data_editor(
            df_m,
            width="stretch",
            hide_index=True,
            key=m_editor_key,
            column_config={
                "Select": st.column_config.CheckboxColumn("✓", default=False),
                "Date Introduced": st.column_config.TextColumn(disabled=True),
                "Date Mastered": st.column_config.TextColumn(disabled=True),
                "List": st.column_config.TextColumn(disabled=True),
                "Target": st.column_config.TextColumn(disabled=True),
                "Probes to mastery": st.column_config.NumberColumn(disabled=True),
            },
        )
        m_selected_ids = [
            mastered_in_op[i]["id"]
            for i, row in enumerate(m_edited.to_dict("records"))
            if row.get("Select")
        ]
        m_pending_key = f"pending_mastered_delete_{op}"
        m_pending_ids = st.session_state.get(m_pending_key)
        if not m_pending_ids:
            mact_save, mact_unm, mact_del = st.columns(3)
            with mact_save:
                if st.button(
                    f"💾 Save {len(m_selected_ids)} to bank",
                    key=f"msave_btn_{op}",
                    disabled=not m_selected_ids,
                    width="stretch",
                    help="Snapshot the checked mastered targets into the cross-student Target Bank.",
                ):
                    picks = [t for t in mastered_in_op if t["id"] in set(m_selected_ids)]
                    n = len(save_targets_to_bank(
                        picks, source_student_name=student_name(load_students(), sid),
                    ))
                    if n:
                        st.toast(f"Saved {n} mastered target(s) to bank.")
                    else:
                        st.toast("Already in bank — nothing new added.")
                    st.rerun()
            with mact_unm:
                if st.button(
                    f"↩ Move {len(m_selected_ids)} back to In Acquisition",
                    key=f"munmastery_btn_{op}",
                    disabled=not m_selected_ids,
                    width="stretch",
                    help=(
                        "Undo mastery: status returns to In Acquisition, the "
                        "mastered date is cleared, and the cumulative count drops. "
                        "Existing probes are kept."
                    ),
                ):
                    ids_set = set(m_selected_ids)
                    all_targets = load_targets()
                    affected = 0
                    for t in all_targets:
                        if t["id"] in ids_set and t.get("status") == "Mastered":
                            t["status"] = "In Acquisition"
                            t["mastered_date"] = ""
                            t.pop("mastered_via", None)
                            t.pop("mastered_probe_count", None)
                            log_mastery_event(
                                t["student_id"], t["id"], "unmastered",
                            )
                            affected += 1
                    save_targets(all_targets)
                    st.toast(
                        f"Moved {affected} target(s) back to In Acquisition."
                    )
                    st.rerun()
            with mact_del:
                if st.button(
                    f"🗑️ Delete {len(m_selected_ids)} checked",
                    key=f"mdel_btn_{op}",
                    disabled=not m_selected_ids,
                    width="stretch",
                ):
                    st.session_state[m_pending_key] = m_selected_ids
                    st.rerun()
        else:
            n = len(m_pending_ids)
            n_probes_orphan = sum(
                1 for p in probes if p["target_id"] in set(m_pending_ids)
            )
            st.warning(
                f"**Delete {n} mastered target(s)?** Cumulative count will drop "
                f"by {n}. {n_probes_orphan} probe(s) will be orphaned."
            )
            mcy, mcn = st.columns(2)
            with mcy:
                if st.button(
                    f"Yes, delete {n}",
                    key=f"mdel_yes_{op}",
                    type="primary", width="stretch",
                ):
                    ids_set = set(m_pending_ids)
                    for t in mastered_in_op:
                        if t["id"] in ids_set:
                            log_mastery_event(
                                t["student_id"], t["id"], "unmastered",
                            )
                    delete_targets(ids_set, reason=f"mastered_bulk_{op}")
                    st.session_state.pop(m_pending_key, None)
                    st.toast(
                        f"Deleted {n} mastered target(s). Undo at the top "
                        "of the page for the next 30 min."
                    )
                    st.rerun()
            with mcn:
                if st.button(
                    "Cancel",
                    key=f"mdel_no_{op}",
                    width="stretch",
                ):
                    st.session_state.pop(m_pending_key, None)
                    st.rerun()

    st.divider()
    metric_col, _ = st.columns([1, 3])
    with metric_col:
        st.metric(
            label=f"Total mastered {op} targets",
            value=len(mastered_in_op),
        )


def page_targets():
    students = load_students()
    targets = load_targets()

    if not students:
        st.header("Verbal Behavior Programming")
        st.info("Add a student first.")
        return

    sid = current_sid(students)
    st.header(f"Verbal Behavior Programming · {student_name(students, sid)}")
    _render_undo_banner("vbp")

    rows = [t for t in targets if t["student_id"] == sid]
    probes = load_probes()
    grouped = group_by_operant_then_list(rows)
    ops_present = sorted(grouped)

    # ── Targets by status (cross-operant lookup) ─────────────────────────────
    if rows:
        with st.expander("🔎 Targets by status", expanded=False):
            tos_search = st.text_input(
                "Search (target name, operant, or list)",
                key="tos_search",
                placeholder="Type to filter…",
            )

            def _tos_filter(t: dict) -> bool:
                if not tos_search.strip():
                    return True
                s = tos_search.strip().lower()
                hay = " ".join([
                    t["description"],
                    t.get("domain", "") or "",
                    t.get("skill_list", "") or "",
                ]).lower()
                return s in hay

            def _row(t: dict, with_mastered: bool = False) -> dict:
                base = {
                    "Operant": t.get("domain", ""),
                    "List": t.get("skill_list", "") or "—",
                    "Target": t["description"],
                    "Y streak": (
                        consecutive_y_streak(t["id"], probes)
                        if t["status"] == "In Acquisition" else "—"
                    ),
                }
                if with_mastered:
                    base["Mastered on"] = mastered_date_label(t) or "—"
                return base

            in_acq = sorted(
                [t for t in rows if t["status"] == "In Acquisition" and _tos_filter(t)],
                key=lambda t: (
                    t.get("domain", ""),
                    (t.get("skill_list") or "").lower(),
                    t["description"].lower(),
                ),
            )
            mastered = sorted(
                [t for t in rows if t["status"] == "Mastered" and _tos_filter(t)],
                key=lambda t: ((t.get("mastered_date") or ""), t["description"]),
                reverse=True,
            )
            planned = sorted(
                [t for t in rows if t["status"] == "Planned" and _tos_filter(t)],
                key=lambda t: (
                    t.get("domain", ""),
                    (t.get("skill_list") or "").lower(),
                    t["description"].lower(),
                ),
            )

            tab_acq, tab_mas, tab_plan = st.tabs([
                f"🔄 In Acquisition ({len(in_acq)})",
                f"✅ Mastered ({len(mastered)})",
                f"📅 Future / Planned ({len(planned)})",
            ])
            with tab_acq:
                if not in_acq:
                    st.caption("No targets in acquisition right now.")
                else:
                    st.dataframe(
                        pd.DataFrame([_row(t) for t in in_acq]),
                        width="stretch", hide_index=True,
                    )
            with tab_mas:
                if not mastered:
                    st.caption("No mastered targets yet.")
                else:
                    st.dataframe(
                        pd.DataFrame([_row(t, with_mastered=True) for t in mastered]),
                        width="stretch", hide_index=True,
                    )
            with tab_plan:
                if not planned:
                    st.caption("No planned (future) targets right now.")
                else:
                    st.dataframe(
                        pd.DataFrame([_row(t) for t in planned]),
                        width="stretch", hide_index=True,
                    )

    st.caption("Pick an operant to see its skill lists and targets.")

    if ops_present:
        n_cols = 3
        cols = st.columns(n_cols)
        for i, op in enumerate(ops_present):
            op_targets = [t for sublist in grouped[op].values() for t in sublist]
            n_active = sum(1 for t in op_targets if t["status"] == "In Acquisition")
            n_mastered = sum(1 for t in op_targets if t["status"] == "Mastered")
            n_po = sum(
                1 for t in op_targets
                if t["status"] == "Mastered" and t.get("mastered_via") == "PO"
            )
            n_planned = sum(1 for t in op_targets if t["status"] == "Planned")
            n_lists = sum(1 for k in grouped[op] if k)
            with cols[i % n_cols]:
                with st.container(border=True):
                    st.markdown('<div class="opcard"></div>', unsafe_allow_html=True)
                    st.markdown(f"### {op}")
                    list_line = f"{n_lists} list{'s' if n_lists != 1 else ''} · " if n_lists else ""
                    planned_line = f" · {n_planned} planned" if n_planned else ""
                    po_line = f" ({n_po} probed out)" if n_po else ""
                    st.caption(f"{list_line}{n_active} in acquisition · {n_mastered} mastered{po_line}{planned_line}")
                    avg_d = avg_days_to_mastery(op_targets, probes)
                    if avg_d is not None:
                        st.caption(
                            f"⏱ Avg acquisition: **{avg_d:.1f} days** to mastery "
                            f"(n = {sum(1 for t in op_targets if t.get('status') == 'Mastered' and t.get('mastered_date') and first_data_date(t['id'], probes))})"
                        )
                    color_cls = OPERANT_BUTTON_CLASS.get(op)
                    if color_cls:
                        st.markdown(
                            f'<div class="{color_cls}"></div>',
                            unsafe_allow_html=True,
                        )
                    if st.button(
                        "Open", key=f"opcard_{op}", type="primary", width="stretch",
                    ):
                        st.session_state["current_operant"] = op
                        st.session_state["page"] = "Operant Detail"
                        st.rerun()
    else:
        st.info("No targets for this student yet — add the first one below.")

    st.divider()
    with st.expander("➕ Start a new operant section"):
        st.caption("Add the first target for an operant this student doesn't have yet.")
        _render_add_target_form(
            sid, default_domain=None, default_skill_list=None,
            key_prefix="tgt_newop_index", targets=targets,
        )

    st.divider()
    st.subheader("Mastered targets by operant")
    mastered_by_op: dict[str, int] = {}
    for t in rows:
        if t.get("status") == "Mastered":
            mastered_by_op[t["domain"]] = mastered_by_op.get(t["domain"], 0) + 1
    if not mastered_by_op:
        st.caption("No mastered targets yet — bars will appear here as targets are mastered.")
    else:
        df_bar = (
            pd.DataFrame(
                [{"Operant": op, "Mastered": n} for op, n in mastered_by_op.items()]
            )
            .sort_values("Mastered", ascending=False)
            .reset_index(drop=True)
        )
        max_total = int(df_bar["Mastered"].max())
        x_dtick = max(1, math.ceil(max_total / 6))
        fig = px.bar(
            df_bar, y="Operant", x="Mastered",
            orientation="h", text="Mastered",
        )
        fig.update_traces(
            marker_color="#ea580c",
            marker_line_width=0,
            textposition="outside",
            textfont=dict(color="#1c1917", size=14),
            hovertemplate="<b>%{y}</b><br>%{x} mastered<extra></extra>",
            cliponaxis=False,
        )
        fig.update_xaxes(
            showgrid=True, gridcolor="#f0eeec",
            zeroline=False, showline=False, ticks="",
            tickfont=dict(color="#a8a29e", size=11),
            tickformat="d", dtick=x_dtick, tick0=0,
            range=[0, max_total * 1.18],
            title=None,
        )
        fig.update_yaxes(
            showgrid=False, zeroline=False, showline=False, ticks="",
            tickfont=dict(color="#1c1917", size=14),
            title=None,
            autorange="reversed",
        )
        fig.update_layout(
            margin=dict(l=10, r=44, t=14, b=10),
            height=max(220, 64 + len(df_bar) * 52),
            bargap=0.42,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="-apple-system, BlinkMacSystemFont, Inter, 'Segoe UI', sans-serif",
                color="#1c1917",
            ),
            showlegend=False,
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#e7e5e4",
                font=dict(family="-apple-system, sans-serif", color="#1c1917"),
            ),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            f"Total: **{int(df_bar['Mastered'].sum())}** mastered across "
            f"{len(df_bar)} operant(s)."
        )

    st.divider()
    with st.expander("📥 Bulk add targets"):
        _render_bulk_add(sid)

    st.divider()
    st.subheader("🏆 Mastery log")
    _render_mastery_log_for_student(sid, students, targets, probes)

    st.divider()
    st.subheader("🗺 Mastery grid")
    st.caption(
        "Domain × target grid. Cells are colored by status and sorted "
        "mastered-first within each column."
    )
    _render_mastery_grid_for_student(sid, targets)


def page_operant_detail():
    students = load_students()
    targets = load_targets()
    probes = load_probes()

    if not students:
        st.header("Operant")
        st.info("Add a student first.")
        return

    sid = current_sid(students)
    op = st.session_state.get("current_operant")

    rows = [t for t in targets if t["student_id"] == sid]
    grouped = group_by_operant_then_list(rows)

    if not op or op not in grouped:
        st.header("Operant")
        st.info("Pick an operant from the Verbal Behavior Programming page.")
        if st.button("← Back"):
            st.session_state["page"] = "Verbal Behavior Programming"
            st.rerun()
        return

    back_col, title_col = st.columns([1, 5])
    with back_col:
        if st.button("← Back", key="op_detail_back", width="stretch"):
            st.session_state["page"] = "Verbal Behavior Programming"
            st.rerun()
    with title_col:
        st.header(f"{op} · {student_name(students, sid)}")
    _render_undo_banner(f"opdet_{op}")

    add_msg = st.session_state.pop("_last_add_msg", None)
    if add_msg:
        st.success(add_msg)

    # ── Per-operant PDF report ───────────────────────────────────────────────
    op_pdf_key = f"op_pdf_{sid}_{op}"
    op_pdf_bytes = st.session_state.get(op_pdf_key)
    if op_pdf_bytes is None:
        gen_col, _ = st.columns([1, 3])
        with gen_col:
            if st.button(
                f"📄 Generate {op} report (PDF)",
                key=f"op_pdf_gen_{op}", width="stretch",
            ):
                with st.spinner("Generating PDF — this can take a few seconds…"):
                    st.session_state[op_pdf_key] = build_operant_report_pdf(
                        sid, op, students, targets, probes,
                    )
                st.rerun()
    else:
        dl_col, regen_col = st.columns([3, 1])
        with dl_col:
            st.download_button(
                f"📄 Download {op} report (PDF)",
                data=op_pdf_bytes,
                file_name=(
                    f"{op.replace(' ', '_')}_report_"
                    f"{student_name(students, sid).replace(' ', '_')}_"
                    f"{date.today().isoformat()}.pdf"
                ),
                mime="application/pdf",
                key=f"op_pdf_dl_{op}", width="stretch",
            )
        with regen_col:
            if st.button(
                "Regenerate", key=f"op_pdf_regen_{op}", width="stretch",
                help="Rebuild after data changes.",
            ):
                st.session_state.pop(op_pdf_key, None)
                st.rerun()

    _render_operant_body(sid, op, grouped[op], targets, probes)

    st.divider()
    st.subheader(f"📈 Cumulative mastered — {op}")
    _render_cumulative_mastery(sid, operant=op)



def _render_mastery_grid_for_student(sid: str, targets: list[dict]) -> None:
    """VB-MAPP-style domain × target grid for one student.

    Columns are DOMAINS in VB-MAPP order; each cell is one target, colored by
    status. Cells inside a column are sorted mastered-first, then by introduced
    date. Read-only — no probe / edit affordances live here.
    """
    student_targets = [t for t in targets if t.get("student_id") == sid]
    if not student_targets:
        st.caption("No targets yet for this student.")
        return

    show_inactive = st.checkbox(
        "Include On Hold / Planned",
        value=False,
        key=f"grid_show_inactive_{sid}",
    )

    by_domain: dict[str, list[dict]] = {d: [] for d in VB_MAPP_DOMAIN_ORDER}
    extras: dict[str, list[dict]] = {}
    for t in student_targets:
        d = t.get("domain") or "Other"
        if d in by_domain:
            by_domain[d].append(t)
        else:
            extras.setdefault(d, []).append(t)

    status_order = ["Mastered", "Maintenance", "In Acquisition", "On Hold", "Planned"]

    def sort_column(items: list[dict]) -> list[dict]:
        return sorted(
            items,
            key=lambda t: (
                status_order.index(t.get("status"))
                if t.get("status") in status_order
                else 99,
                t.get("introduced") or "",
            ),
        )

    def visible(items: list[dict]) -> list[dict]:
        if show_inactive:
            return items
        return [t for t in items if t.get("status") not in ("On Hold", "Planned")]

    domains_in_use = [d for d in VB_MAPP_DOMAIN_ORDER if by_domain[d]] + sorted(extras)

    # Legend
    chips = "".join(
        f"<span style='display:inline-block;background:{GRID_STATUS_COLORS[s]};"
        f"color:white;padding:2px 8px;border-radius:3px;margin-right:6px;"
        f"font-size:0.75rem'>{s}</span>"
        for s in status_order
    )
    st.markdown(chips, unsafe_allow_html=True)
    st.markdown("")

    def cell_html(t: dict, max_chars: int = 38) -> str:
        status = t.get("status", "Planned")
        bg = GRID_STATUS_COLORS.get(status, "#bdbdbd")
        full_desc = (t.get("description") or "").strip()
        desc = full_desc[: max_chars - 1] + "…" if len(full_desc) > max_chars else full_desc
        mastered_date = t.get("mastered_date") or ""
        sub = (
            mastered_date
            if status in ("Mastered", "Maintenance") and mastered_date
            else status
        )
        return (
            f"<div style='background:{bg};color:white;"
            f"padding:6px 8px;border-radius:4px;margin-bottom:4px;"
            f"font-size:0.78rem;line-height:1.15;min-height:42px;"
            f"display:flex;flex-direction:column;justify-content:space-between;' "
            f"title=\"{html.escape(full_desc, quote=True)}\">"
            f"<div>{html.escape(desc)}</div>"
            f"<div style='opacity:0.85;font-size:0.7rem;margin-top:2px'>"
            f"{html.escape(sub)}</div>"
            f"</div>"
        )

    cols = st.columns(len(domains_in_use), gap="small")
    for col, domain in zip(cols, domains_in_use):
        all_in_col = sort_column(by_domain.get(domain) or extras[domain])
        col_targets = visible(all_in_col)
        mastered_n = sum(
            1 for t in all_in_col if t.get("status") in ("Mastered", "Maintenance")
        )
        with col:
            st.markdown(
                f"<div style='border-bottom:2px solid #333;padding-bottom:4px;"
                f"margin-bottom:6px;text-align:center'>"
                f"<div style='font-weight:600'>{html.escape(domain)}</div>"
                f"<div style='font-size:0.75rem;color:#555'>"
                f"{mastered_n} / {len(all_in_col)} mastered</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if not col_targets:
                st.markdown(
                    "<div style='color:#aaa;text-align:center;font-style:italic;"
                    "font-size:0.75rem'>(none)</div>",
                    unsafe_allow_html=True,
                )
                continue
            st.markdown(
                "".join(cell_html(t) for t in col_targets),
                unsafe_allow_html=True,
            )


def _render_mastery_log_for_student(
    sid: str, students: list[dict], targets: list[dict], probes: list[dict],
) -> None:
    """Mastered-targets table + metrics + CSV + delete-with-confirm, scoped to one student."""
    mastered = [t for t in targets if t["status"] == "Mastered" and t["student_id"] == sid]
    if not mastered:
        st.caption(
            "No mastered targets yet — they appear here when a target's Y streak "
            "reaches its criterion or it's probed out."
        )
        return

    rows = []
    for t in mastered:
        tp = [p for p in probes if p["target_id"] == t["id"]]
        rows.append({
            "Date Introduced": _fmt_date(first_data_date(t["id"], probes)) or "—",
            "Date Mastered": mastered_date_label(t) or "—",
            "Verbal operant": t["domain"],
            "Target": t["description"],
            "Criterion": f"{mastery_n_for(t)} consecutive Y" if t.get("mastered_via") != "PO" else "Probed out",
            "Probes to mastery": t.get("mastered_probe_count", len(tp)) or len(tp),
        })
    df = pd.DataFrame(rows).sort_values(
        ["Date Mastered", "Verbal operant"], ascending=[False, True],
    )

    c1, c2 = st.columns(2)
    c1.metric("Total mastered", len(df))
    c2.metric("Verbal operants", df["Verbal operant"].nunique() if len(df) else 0)

    st.dataframe(df, width="stretch", hide_index=True)

    with st.expander("By verbal operant"):
        by_op = df.groupby("Verbal operant").size().reset_index(name="Mastered targets")
        st.dataframe(by_op, width="stretch", hide_index=True)

    ml_csv, ml_pdf = st.columns(2)
    with ml_csv:
        st.download_button(
            "📄 Download mastery log CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"mastery_log_{student_name(students, sid).replace(' ', '_')}_{date.today().isoformat()}.csv",
            mime="text/csv",
            width="stretch",
        )
    with ml_pdf:
        st.download_button(
            "📄 Download mastery log PDF",
            data=build_mastery_log_pdf(sid, students, targets, probes),
            file_name=f"mastery_log_{student_name(students, sid).replace(' ', '_')}_{date.today().isoformat()}.pdf",
            mime="application/pdf",
            width="stretch",
        )

    with st.expander("🗑️ Delete a mastered target"):
        ordered = sorted(mastered, key=lambda t: (t["domain"], t["description"]))
        pick_id = st.selectbox(
            "Target to delete",
            options=[t["id"] for t in ordered],
            format_func=lambda i, _o=ordered: (
                f"[{next(t['domain'] for t in _o if t['id'] == i)}] "
                f"{next(t['description'] for t in _o if t['id'] == i)}"
            ),
            key="del_mastered_pick",
        )
        pending_key = "pending_delete_mastered_id"
        confirming = st.session_state.get(pending_key) == pick_id
        if not confirming:
            if st.button(
                "🗑️ Delete this mastered target",
                key="del_mastered_btn",
                width="stretch",
            ):
                st.session_state[pending_key] = pick_id
                st.rerun()
        else:
            pick_target = next(t for t in ordered if t["id"] == pick_id)
            n_probes = sum(1 for p in probes if p["target_id"] == pick_id)
            st.warning(
                f"**Are you sure you want to delete this mastered target?**  \n"
                f"`{pick_target['description']}` — mastered {mastered_date_label(pick_target)}.  \n"
                f"This will remove the target permanently and drop the cumulative mastered "
                f"count by 1. {n_probes} probe record(s) will be left in place but orphaned."
            )
            c_yes, c_no = st.columns(2)
            with c_yes:
                if st.button(
                    "Yes, delete permanently",
                    key="del_mastered_confirm",
                    type="primary",
                    width="stretch",
                ):
                    log_mastery_event(
                        pick_target["student_id"], pick_target["id"], "unmastered",
                    )
                    delete_targets({pick_id}, reason="mastered_single")
                    st.session_state.pop(pending_key, None)
                    st.success(
                        f"Deleted: {pick_target['description']} "
                        f"(undo at the top of the page)."
                    )
                    st.rerun()
            with c_no:
                if st.button(
                    "Cancel",
                    key="del_mastered_cancel",
                    width="stretch",
                ):
                    st.session_state.pop(pending_key, None)
                    st.rerun()


# ── PDF helpers ──────────────────────────────────────────────────────────────
_PDF_CHAR_MAP = {
    "—": "-",     # em dash
    "–": "-",     # en dash
    "•": "*",
    "…": "...",
    "✓": "y",
    "✗": "x",
    "✕": "x",
    "→": "->",
    "←": "<-",
    " ": " ",  # non-breaking space
    "‘": "'", "’": "'",  # curly singles
    "“": '"', "”": '"',  # curly doubles
    "🎉": "", "🏆": "", "🟡": "", "✅": "", "📝": "", "📄": "",
    "🚨": "", "🎯": "", "📋": "", "📥": "", "🔜": "", "📈": "",
    "🗑️": "", "⚙️": "", "🏠": "", "🗂": "", "🏦": "",
    "➕": "+", "↩": "<-", "✎": "",
}


def _pdf_safe(s: str | None) -> str:
    """Make a string safe for fpdf2's Latin-1 core fonts."""
    if s is None:
        return ""
    text = str(s)
    for old, new in _PDF_CHAR_MAP.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


class _ReportPDF(FPDF):
    def header(self):
        avail_w = self.w - self.l_margin - self.r_margin
        # Wordmark (left) + document descriptor (right).
        self.set_y(10)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(234, 88, 12)
        self.cell(avail_w / 2, 5, "REPERTIORES", align="L")
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(120, 113, 108)
        self.cell(
            avail_w / 2, 5,
            _pdf_safe(getattr(self, "_running_header", "")),
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R",
        )
        # Hairline rule under the masthead.
        self.set_draw_color(214, 211, 209)
        self.set_line_width(0.3)
        self.line(self.l_margin, 17.5, self.w - self.r_margin, 17.5)
        self.ln(7)

    def footer(self):
        avail_w = self.w - self.l_margin - self.r_margin
        self.set_draw_color(229, 229, 226)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.h - 14, self.w - self.r_margin, self.h - 14)
        self.set_y(-11)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(150, 145, 140)
        col_w = avail_w / 3
        self.cell(col_w, 5, "Confidential clinical record", align="L")
        gen = getattr(self, "_generated_iso", "") or ""
        self.cell(
            col_w, 5,
            f"Generated {_fmt_date(gen)}" if gen else "",
            align="C",
        )
        self.cell(
            col_w, 5,
            f"Page {self.page_no()}  ·  Repertiores",
            align="R",
        )


def _pdf_init(running_header: str) -> _ReportPDF:
    pdf = _ReportPDF(orientation="P", unit="mm", format="Letter")
    pdf._running_header = running_header
    pdf._generated_iso = date.today().isoformat()
    pdf.set_auto_page_break(auto=True, margin=20)
    try:
        pdf.set_title(_pdf_safe(running_header))
        pdf.set_author("Repertiores")
    except Exception:
        pass
    pdf.add_page()
    return pdf


def _pdf_h1(pdf: FPDF, text: str):
    pdf.set_text_color(28, 25, 23)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 11, _pdf_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(0.5)


def _pdf_h2(pdf: FPDF, text: str):
    pdf.ln(2)
    y = pdf.get_y()
    # Small orange accent tab beside the section title.
    pdf.set_fill_color(234, 88, 12)
    pdf.rect(pdf.l_margin, y + 1.0, 1.7, 4.6, style="F")
    pdf.set_x(pdf.l_margin + 4.2)
    pdf.set_text_color(28, 25, 23)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, _pdf_safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(229, 229, 226)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2.5)


def _pdf_caption(pdf: FPDF, text: str):
    pdf.set_text_color(120, 113, 108)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 4.4, _pdf_safe(text))
    pdf.set_text_color(28, 25, 23)
    pdf.ln(1)


def _pdf_kv_row(pdf: FPDF, label: str, value: str):
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(120, 113, 108)
    pdf.cell(54, 5.6, _pdf_safe(label))
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(28, 25, 23)
    pdf.cell(0, 5.6, _pdf_safe(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _pdf_table(pdf: FPDF, headers: list[str], rows: list[list[str]],
               widths: list[float] | None = None):
    if not rows:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(150, 145, 140)
        pdf.cell(0, 6, "(none)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(28, 25, 23)
        pdf.ln(1)
        return
    avail = pdf.w - pdf.l_margin - pdf.r_margin
    if widths is None:
        widths = [avail / len(headers)] * len(headers)
    else:
        total = sum(widths)
        widths = [w * avail / total for w in widths]
    table_w = sum(widths)
    row_h = 6.6

    def _draw_header():
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(120, 113, 108)
        for w, h in zip(widths, headers):
            pdf.cell(w, 6.5, _pdf_safe(str(h)), border=0)
        pdf.ln(6.5)
        pdf.set_draw_color(168, 162, 158)
        pdf.set_line_width(0.4)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + table_w, pdf.get_y())
        pdf.ln(0.6)

    _draw_header()
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(28, 25, 23)
    for i, row in enumerate(rows):
        if pdf.get_y() > pdf.h - 28:
            pdf.add_page()
            _draw_header()
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(28, 25, 23)
        row_y = pdf.get_y()
        if i % 2 == 1:
            pdf.set_fill_color(249, 248, 246)
            pdf.rect(pdf.l_margin, row_y, table_w, row_h, style="F")
        pdf.set_xy(pdf.l_margin, row_y)
        for w, cell in zip(widths, row):
            text = _pdf_safe(cell) if cell is not None else ""
            limit = max(4, int(w / 1.7))
            if len(text) > limit:
                text = text[: limit - 1] + "..."
            pdf.cell(w, row_h, text, border=0)
        pdf.ln(row_h)
        pdf.set_draw_color(235, 233, 230)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + table_w, pdf.get_y())
    pdf.ln(3)


def _pdf_legend_box(
    pdf: FPDF, title: str, entries: list[tuple],
    top_y: float, width: float = 70.0,
) -> float:
    """Draw a compact bordered reference box in the top-right corner.

    Each entry is ``(code, meaning)`` or ``(code, meaning, count)``. When a
    count is present it is shown right-aligned, so the box doubles as a
    response key + tally. Returns the box's bottom y.
    """
    x = pdf.w - pdf.r_margin - width
    pad = 3.0
    title_h = 5.2
    line_h = 4.3
    has_counts = any(len(e) >= 3 for e in entries)
    box_h = pad * 2 + title_h + line_h * len(entries)
    pdf.set_fill_color(255, 247, 237)
    pdf.set_draw_color(253, 200, 150)
    pdf.set_line_width(0.3)
    pdf.rect(x, top_y, width, box_h, style="DF")
    pdf.set_xy(x + pad, top_y + pad)
    pdf.set_font("Helvetica", "B", 7.3)
    pdf.set_text_color(154, 52, 18)
    pdf.cell(width - pad * 2, title_h, _pdf_safe(title))
    code_w = 9.0
    count_w = 11.0 if has_counts else 0.0
    meaning_w = width - pad * 2 - code_w - count_w
    cy = top_y + pad + title_h
    for entry in entries:
        code = str(entry[0])
        meaning = str(entry[1])
        count = entry[2] if len(entry) >= 3 else None
        pdf.set_xy(x + pad, cy)
        pdf.set_font("Helvetica", "B", 7.3)
        pdf.set_text_color(28, 25, 23)
        pdf.cell(code_w, line_h, _pdf_safe(code))
        pdf.set_font("Helvetica", "", 7.3)
        pdf.set_text_color(68, 64, 60)
        pdf.cell(meaning_w, line_h, _pdf_safe(meaning))
        if count is not None:
            pdf.set_font("Helvetica", "B", 7.3)
            pdf.set_text_color(28, 25, 23)
            pdf.cell(count_w, line_h, _pdf_safe(str(count)), align="R")
        cy += line_h
    pdf.set_text_color(28, 25, 23)
    return top_y + box_h


def _pdf_bytes(pdf: FPDF) -> bytes:
    out = pdf.output()
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)


def _safe_to_image(fig, **kw) -> bytes | None:
    """Render a Plotly figure to PNG via kaleido with a hard timeout.

    Returns None on any failure so PDF generation never hangs.
    """
    import threading
    result: dict = {"png": None, "err": None}

    def _go():
        try:
            result["png"] = fig.to_image(format="png", **kw)
        except Exception as e:
            result["err"] = e

    t = threading.Thread(target=_go, daemon=True)
    t.start()
    t.join(timeout=20.0)
    if t.is_alive():
        return None
    return result["png"]


def _mastered_by_op_bar_png(s_mastered: list[dict]) -> bytes | None:
    """Render the 'mastered targets by operant' bar chart via matplotlib.

    Matplotlib is used here instead of Plotly + kaleido so PDF generation is
    fast and reliable (kaleido spawns a headless browser and can hang).
    """
    if not s_mastered:
        return None
    counts: dict[str, int] = {}
    for t in s_mastered:
        counts[t["domain"]] = counts.get(t["domain"], 0) + 1
    if not counts:
        return None
    try:
        import io as _io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    ordered = sorted(counts.items(), key=lambda x: x[1])  # ascending for barh
    labels = [op for op, _ in ordered]
    values = [n for _, n in ordered]
    fig, ax = plt.subplots(
        figsize=(8, max(2.4, 0.55 * len(labels) + 0.8)),
        dpi=150,
    )
    bars = ax.barh(labels, values, color="#ea580c", edgecolor="none", height=0.6)
    max_val = max(values)
    ax.set_xlim(0, max_val * 1.18)
    for b, v in zip(bars, values):
        ax.text(
            v + max_val * 0.012, b.get_y() + b.get_height() / 2,
            str(int(v)), va="center", ha="left",
            fontsize=12, color="#1c1917",
        )
    ax.tick_params(axis="y", labelsize=12, length=0)
    ax.tick_params(axis="x", labelsize=10, length=0, colors="#78716c")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.grid(axis="x", color="#f0eeec", linestyle="-", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")
    fig.tight_layout()
    buf = _io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def build_progress_report_pdf(
    sid: str, students: list[dict], targets: list[dict],
    probes: list[dict], behaviors: list[dict],
    behavior_records: list[dict],
) -> bytes:
    name = student_name(students, sid)
    pdf = _pdf_init(f"Progress Report · {name}")
    _pdf_h1(pdf, f"{name}")

    s_targets = [t for t in targets if t["student_id"] == sid]
    s_mastered = [t for t in s_targets if t["status"] == "Mastered"]
    s_active = [t for t in s_targets if t["status"] == "In Acquisition"]
    s_planned = [t for t in s_targets if t["status"] == "Planned"]

    _pdf_h2(pdf, "Summary")
    _pdf_kv_row(pdf, "Total mastered targets:", str(len(s_mastered)))
    _pdf_kv_row(pdf, "In acquisition:", str(len(s_active)))
    _pdf_kv_row(pdf, "Planned:", str(len(s_planned)))
    pdf.ln(3)

    by_op: dict[str, int] = {}
    for t in s_mastered:
        by_op[t["domain"]] = by_op.get(t["domain"], 0) + 1
    if by_op:
        _pdf_h2(pdf, "Mastered targets by operant")
        bar_png = _mastered_by_op_bar_png(s_mastered)
        if bar_png:
            _pdf_embed_png(pdf, bar_png, max_height_mm=100)
        _pdf_table(
            pdf,
            ["Operant", "Mastered"],
            [[op, by_op[op]] for op in sorted(by_op, key=lambda k: -by_op[k])],
            widths=[3, 1],
        )

    cum_png = _cumulative_mastery_png(sid)
    if cum_png:
        _pdf_h2(pdf, "Cumulative mastered targets (by operant)")
        _pdf_caption(
            pdf,
            "Running total at the end of each day; probed-out targets included.",
        )
        _pdf_embed_png(pdf, cum_png, max_height_mm=95)

    if s_mastered:
        _pdf_h2(pdf, "Mastery log")
        rows = []
        for t in sorted(s_mastered,
                         key=lambda t: (t.get("mastered_date") or ""), reverse=True):
            tp = [p for p in probes if p["target_id"] == t["id"]]
            rows.append([
                _fmt_date(first_data_date(t["id"], probes)) or "-",
                mastered_date_label(t) or "-",
                t["domain"],
                t.get("skill_list", "") or "-",
                t["description"],
                str(t.get("mastered_probe_count", len(tp)) or len(tp)),
            ])
        _pdf_table(
            pdf,
            ["Date Introduced", "Date Mastered", "Operant", "List", "Target", "Probes"],
            rows,
            widths=[1.2, 1.2, 1.0, 1.2, 3.2, 0.7],
        )

    s_behaviors = [b for b in behaviors if b["student_id"] == sid]
    for b in s_behaviors:
        # One page per behavior of concern.
        pdf.add_page()
        mt = MEASUREMENT_TYPES.get(
            b.get("measurement", "frequency"),
            MEASUREMENT_TYPES["frequency"],
        )
        _pdf_h1(pdf, b["name"])
        _pdf_caption(pdf, f"{mt['label']}  ·  Behavior of concern  ·  {name}")
        if b.get("definition"):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(28, 25, 23)
            pdf.multi_cell(0, 4, _pdf_safe(b["definition"]))
            pdf.ln(1)

        b_recs = sorted(
            [r for r in behavior_records if r["behavior_id"] == b["id"]],
            key=lambda r: r["date"],
        )
        if not b_recs:
            _pdf_caption(pdf, "No sessions logged for this behavior yet.")
            continue

        analysis = behavior_analysis(
            b, behavior_records, phases_for_behavior(sid, b["id"]),
        )
        if analysis and analysis["overall"]:
            o = analysis["overall"]
            plain = _behavior_plain_summary(b, mt, o).replace("**", "")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(28, 25, 23)
            pdf.multi_cell(0, 4, _pdf_safe(plain))
            pdf.ln(1)
            _pdf_kv_row(
                pdf, "Typical day:",
                f"{o['mean']:.1f} {mt['unit']}  "
                f"(range {o['min']:g}-{o['max']:g})",
            )
            _pdf_kv_row(
                pdf, "Direction:",
                f"{_direction_label(o['trend_desc'])}  "
                f"({_direction_subtitle(o, mt)})",
            )
            _pdf_kv_row(
                pdf, "Consistency:",
                f"{_variability_label(o['variability_desc'])}  "
                f"({_variability_subtitle(o)})",
            )

        # Line graph is intentionally omitted from the progress report to keep
        # generation fast — per-behavior PDFs (one per detail page) include the
        # chart for clinicians who want it.

        # Compact session log — trimmed if a lot of rows so we can keep it on
        # the same page-spread as the chart.
        rows = []
        for r in reversed(b_recs):
            rows.append([
                _fmt_date(r["date"]),
                behavior_value_display(b, r),
                (r.get("notes", "") or "")[:60],
            ])
        max_inline_rows = 18
        if len(rows) > max_inline_rows:
            trimmed = rows[:max_inline_rows]
            _pdf_h2(pdf, "Recent sessions")
            _pdf_caption(
                pdf,
                f"Showing most recent {max_inline_rows} of {len(rows)} sessions "
                "to keep the report compact.",
            )
            _pdf_table(
                pdf,
                ["Date", "Value", "Notes"],
                trimmed,
                widths=[1, 1.6, 2.2],
            )
        else:
            _pdf_h2(pdf, "Session log")
            _pdf_table(
                pdf,
                ["Date", "Value", "Notes"],
                rows,
                widths=[1, 1.6, 2.2],
            )

    return _pdf_bytes(pdf)


def build_operant_report_pdf(
    sid: str, op: str, students: list[dict],
    targets: list[dict], probes: list[dict],
) -> bytes:
    """A report scoped to a single verbal operant for one student."""
    name = student_name(students, sid)
    pdf = _pdf_init(f"{op} Report · {name}")
    _pdf_h1(pdf, op)
    _pdf_caption(
        pdf,
        f"{name}  ·  Verbal operant report  ·  "
        f"generated {date.today().isoformat()}",
    )

    op_targets = [
        t for t in targets if t["student_id"] == sid and t["domain"] == op
    ]
    mastered = [t for t in op_targets if t["status"] == "Mastered"]
    active = [t for t in op_targets if t["status"] == "In Acquisition"]
    planned = [t for t in op_targets if t["status"] == "Planned"]
    n_po = sum(1 for t in mastered if t.get("mastered_via") == "PO")

    _pdf_h2(pdf, "Summary")
    mastered_val = str(len(mastered))
    if n_po:
        mastered_val += f"   ({len(mastered) - n_po} taught, {n_po} probed out)"
    _pdf_kv_row(pdf, "Mastered targets:", mastered_val)
    _pdf_kv_row(pdf, "In acquisition:", str(len(active)))
    _pdf_kv_row(pdf, "Planned:", str(len(planned)))
    avg_d = avg_days_to_mastery(op_targets, probes)
    if avg_d is not None:
        _pdf_kv_row(pdf, "Avg days to mastery:", f"{avg_d:.0f}")
    pdf.ln(3)

    if not op_targets:
        _pdf_caption(pdf, f"No {op} targets for this student yet.")
        return _pdf_bytes(pdf)

    # Cumulative chart scoped to this operant.
    cum_png = _cumulative_mastery_png(sid, operant=op)
    if cum_png:
        _pdf_h2(pdf, "Cumulative mastered targets")
        _pdf_caption(
            pdf,
            "Running total at the end of each day; probed-out targets included.",
        )
        _pdf_embed_png(pdf, cum_png, max_height_mm=90)

    # Per-skill-list breakdown.
    by_list: dict[str, dict[str, int]] = {}
    for t in op_targets:
        key = (t.get("skill_list", "") or "—")
        d = by_list.setdefault(key, {"Mastered": 0, "In acq.": 0, "Planned": 0})
        if t["status"] == "Mastered":
            d["Mastered"] += 1
        elif t["status"] == "In Acquisition":
            d["In acq."] += 1
        elif t["status"] == "Planned":
            d["Planned"] += 1
    if len(by_list) > 1 or "—" not in by_list:
        _pdf_h2(pdf, "By skill list")
        _pdf_table(
            pdf,
            ["Skill list", "Mastered", "In acq.", "Planned"],
            [
                [lst, str(d["Mastered"]), str(d["In acq."]), str(d["Planned"])]
                for lst, d in sorted(by_list.items())
            ],
            widths=[3, 1, 1, 1],
        )

    if active:
        _pdf_h2(pdf, "Current targets (in acquisition)")
        _pdf_table(
            pdf,
            ["List", "Target", "Date introduced", "Probes"],
            [
                [
                    t.get("skill_list", "") or "-",
                    t["description"],
                    _fmt_date(first_data_date(t["id"], probes)) or "-",
                    str(len([p for p in probes if p["target_id"] == t["id"]])),
                ]
                for t in sorted(active, key=lambda t: t["description"].lower())
            ],
            widths=[1.3, 3.2, 1.2, 0.7],
        )

    if mastered:
        _pdf_h2(pdf, "Mastery log")
        rows = []
        for t in sorted(
            mastered, key=lambda t: (t.get("mastered_date") or ""), reverse=True
        ):
            tp = [p for p in probes if p["target_id"] == t["id"]]
            rows.append([
                _fmt_date(first_data_date(t["id"], probes)) or "-",
                mastered_date_label(t) or "-",
                t.get("skill_list", "") or "-",
                t["description"],
                str(t.get("mastered_probe_count", len(tp)) or len(tp)),
            ])
        _pdf_table(
            pdf,
            ["Date Introduced", "Date Mastered", "List", "Target", "Probes"],
            rows,
            widths=[1.2, 1.2, 1.2, 3.2, 0.7],
        )

    if planned:
        _pdf_h2(pdf, "Planned targets")
        _pdf_table(
            pdf,
            ["List", "Target"],
            [
                [t.get("skill_list", "") or "-", t["description"]]
                for t in sorted(planned, key=lambda t: t["description"].lower())
            ],
            widths=[1.5, 4],
        )

    return _pdf_bytes(pdf)


def build_session_pdf(
    sid: str, day_iso: str, students: list[dict], targets: list[dict],
    probes: list[dict], behaviors: list[dict], behavior_records: list[dict],
    session: dict | None,
) -> bytes:
    name = student_name(students, sid)
    pdf = _pdf_init(f"Session · {name} · {day_iso}")

    legend_top = pdf.get_y()
    _pdf_h1(pdf, f"{name} — {_fmt_date(day_iso)}")
    if session:
        _pdf_caption(
            pdf,
            f"{session.get('name', '')} · "
            + ("Completed" if session.get("ended_at") else "In progress")
            + (f" · Clinician: {session['clinician']}" if session.get("clinician") else "")
        )
        if session.get("notes"):
            _pdf_caption(pdf, f"Notes: {session['notes']}")

    t_lookup = {t["id"]: t for t in targets if t["student_id"] == sid}
    todays = [
        p for p in probes
        if p["date"] == day_iso and p["target_id"] in t_lookup
    ]
    counts = {r: sum(1 for p in todays if p["response"] == r) for r in RESPONSES}
    yn_total = counts["Y"] + counts["N"]
    pct_y = round(100 * counts["Y"] / yn_total, 1) if yn_total else 0.0
    n_mastered_today = sum(
        1 for t in targets
        if t["student_id"] == sid
        and t.get("status") == "Mastered"
        and (t.get("mastered_date") or "") == day_iso
    )

    # Response breakdown — pinned top-right; doubles as the response key
    # (code + meaning) so no separate legend is needed.
    legend_bottom = _pdf_legend_box(
        pdf, "RESPONSE SUMMARY",
        [
            ("Y", "Independent correct", counts["Y"]),
            ("N", "Incorrect", counts["N"]),
            ("NR", "No response", counts["NR"]),
            ("PO", "Probed out", counts["PO"]),
            ("NP", "Not probed", counts["NP"]),
        ],
        top_y=legend_top,
    )
    if pdf.get_y() < legend_bottom + 4:
        pdf.set_y(legend_bottom + 4)

    _pdf_h2(pdf, "Cold probe summary")
    _pdf_kv_row(pdf, "Total probes:", str(len(todays)))
    _pdf_kv_row(pdf, "% independent (Y / Y+N):", f"{pct_y}%")
    _pdf_kv_row(pdf, "Targets mastered this session:", str(n_mastered_today))
    pdf.ln(1)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 113, 108)
    pdf.multi_cell(
        0, 4,
        _pdf_safe(
            "Response counts in the box, top-right. Error subtypes shown in "
            "parentheses after N: Incorrect, Scrolling, No response."
        ),
    )
    pdf.set_text_color(28, 25, 23)
    pdf.ln(3)

    if todays:
        _pdf_h2(pdf, "Probes")
        rows = []
        for p in sorted(
            todays,
            key=lambda p: (
                t_lookup[p["target_id"]]["domain"],
                t_lookup[p["target_id"]].get("skill_list", "") or "",
                t_lookup[p["target_id"]]["description"],
            ),
        ):
            t = t_lookup[p["target_id"]]
            err = p.get("error_type", "") or ""
            resp = p["response"] + (f" ({err})" if err else "")
            rows.append([
                t["domain"], t.get("skill_list", "") or "—",
                t["description"], resp,
            ])
        _pdf_table(
            pdf, ["Operant", "List", "Target", "Response"], rows,
            widths=[1.2, 1.5, 4, 1.3],
        )

    # Targets that reached mastery on this session day.
    mastered_today = [
        t for t in targets
        if t["student_id"] == sid
        and t.get("status") == "Mastered"
        and (t.get("mastered_date") or "") == day_iso
    ]
    _pdf_h2(pdf, "Targets mastered this session")
    if not mastered_today:
        _pdf_caption(pdf, "No targets reached mastery during this session.")
    else:
        m_rows = []
        for t in sorted(
            mastered_today,
            key=lambda t: (t["domain"], t.get("skill_list", "") or "", t["description"]),
        ):
            route = "Probed out" if t.get("mastered_via") == "PO" else "Met criterion"
            m_rows.append([
                t["domain"],
                t.get("skill_list", "") or "-",
                t["description"],
                route,
            ])
        _pdf_table(
            pdf, ["Operant", "List", "Target", "Route to mastery"], m_rows,
            widths=[1.2, 1.5, 3.7, 1.6],
        )

    s_behaviors = [b for b in behaviors if b["student_id"] == sid]
    day_b_recs = [r for r in behavior_records if r["date"] == day_iso and r["student_id"] == sid]
    if s_behaviors and day_b_recs:
        _pdf_h2(pdf, "Behavior data for the day")
        b_lookup = {b["id"]: b for b in s_behaviors}
        rows = []
        for r in day_b_recs:
            b = b_lookup.get(r["behavior_id"])
            if not b:
                continue
            mt = MEASUREMENT_TYPES.get(b["measurement"], MEASUREMENT_TYPES["frequency"])
            v = behavior_value_display(b, r)
            rows.append([b["name"], mt["label"], v, r.get("notes", "") or ""])
        _pdf_table(
            pdf, ["Behavior", "Measurement", "Value", "Notes"],
            rows, widths=[2, 1.5, 1.5, 3],
        )

    return _pdf_bytes(pdf)


def _behavior_line_chart_png(
    b: dict, records: list[dict],
    show_trend: bool = False, show_level: bool = False,
    window_days: int | None = None, period: str = "Per session",
) -> bytes | None:
    """Render the behavior's line-graph trend to a PNG byte string.

    Tries Plotly+kaleido first; falls back to matplotlib so the chart still
    embeds when kaleido is unavailable or times out (~20 s in headless mode).
    Pass ``window_days`` to restrict the chart to the most recent N days, and
    ``period`` (Daily/Weekly/Monthly) to aggregate into a bar chart.
    """
    mt = MEASUREMENT_TYPES.get(b["measurement"], MEASUREMENT_TYPES["frequency"])
    b_rows = sorted(
        [r for r in records if r["behavior_id"] == b["id"]],
        key=lambda r: r["date"],
    )
    if not b_rows:
        return None
    df_b = pd.DataFrame([{
        "Date": pd.to_datetime(r["date"]),
        "Value": _record_display_value(b, r),
    } for r in b_rows]).sort_values("Date")
    df_b = _aggregate_period(
        _filter_window(df_b, window_days), b["measurement"], period,
    )
    if df_b.empty:
        return None
    is_bar = period != "Per session"
    bphases = phases_for_behavior(b["student_id"], b["id"])
    xr = _xrange_with_phases(df_b["Date"], bphases)

    if is_bar:
        fig = px.bar(df_b, x="Date", y="Value")
        fig.update_traces(
            marker_color="#ea580c", marker_line_width=0,
            text=df_b["Value"], texttemplate="%{y:.0f}",
            textposition="outside", cliponaxis=False,
            textfont=dict(size=12, color="#1c1917"),
        )
    else:
        fig = px.line(df_b, x="Date", y="Value", markers=True)
        fig.update_traces(
            mode="lines+markers+text",
            line=dict(color="#ea580c"),
            marker=dict(size=9, color="#ea580c",
                        line=dict(width=1.5, color="white")),
            text=df_b["Value"], texttemplate="%{y:.0f}",
            textposition="top center",
            textfont=dict(size=11, color="#1c1917"),
        )
    fig.update_yaxes(
        title=dict(
            text=_graph_y_title(mt, b["measurement"], period),
            standoff=18, font=dict(size=14),
        ),
        rangemode="tozero",
        gridcolor="#f0eeec", zeroline=False,
        tickfont=dict(size=12),
    )
    fig.update_xaxes(
        title=None, gridcolor="#f0eeec", zeroline=False,
        tickangle=-35, tickfont=dict(size=11),
        showline=True, linecolor="#d6d3d1", linewidth=1,
    )
    _apply_period_xticks(fig, period)
    if xr:
        fig.update_xaxes(range=xr)
    _apply_phase_lines(fig, bphases)
    if show_level:
        level = float(df_b["Value"].mean())
        fig.add_hline(
            y=level,
            line=dict(color="#0ea5e9", width=2, dash="dot"),
            annotation_text=f"Level: {round(level)}",
            annotation_position="top left",
            annotation_font_color="#0369a1",
        )
    if show_trend:
        fit = _best_fit_line(df_b["Date"], df_b["Value"])
        if fit:
            x0, x1, y0, y1, _slope = fit
            fig.add_scatter(
                x=[x0, x1], y=[y0, y1], mode="lines",
                line=dict(color="#1c1917", width=2, dash="dash"),
                name="Trend", hoverinfo="skip", showlegend=False,
            )
    _integer_yaxis(fig, df_b["Value"])
    fig.update_layout(
        margin=dict(l=90, r=30, t=40, b=90),
        height=520,
        width=1200,
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        font=dict(family="Helvetica, Arial, sans-serif", color="#1c1917"),
    )
    png = _safe_to_image(fig, scale=2)
    if png:
        return png
    return _behavior_line_chart_png_mpl(
        b, df_b, bphases, xr, show_trend=show_trend, show_level=show_level,
        period=period,
    )


def _behavior_line_chart_png_mpl(
    b: dict, df_b: "pd.DataFrame", phases: list[dict], xr,
    show_trend: bool = False, show_level: bool = False,
    period: str = "Per session",
) -> bytes | None:
    """Matplotlib fallback for the behavior line chart (used when kaleido fails)."""
    try:
        import io as _io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except Exception:
        return None

    mt = MEASUREMENT_TYPES.get(b["measurement"], MEASUREMENT_TYPES["frequency"])
    fig, ax = plt.subplots(figsize=(12, 5.2), dpi=160)
    if period != "Per session":
        bar_w = {
            "Daily": 0.8, "Weekly": 5, "Monthly": 25, "Yearly": 300,
        }.get(period, 0.8)
        bars = ax.bar(df_b["Date"], df_b["Value"], width=bar_w, color="#ea580c")
        ax.bar_label(bars, fmt="%.0f", padding=3, fontsize=10, color="#1c1917")
    else:
        ax.plot(
            df_b["Date"], df_b["Value"],
            color="#ea580c", linewidth=2,
            marker="o", markersize=7,
            markerfacecolor="#ea580c", markeredgecolor="white",
            markeredgewidth=1.4,
        )
        for _x, _y in zip(df_b["Date"], df_b["Value"]):
            ax.annotate(
                f"{_y:.0f}", xy=(_x, _y), xytext=(0, 6),
                textcoords="offset points", ha="center", va="bottom",
                fontsize=9, color="#1c1917",
            )
    ax.set_ylabel(_graph_y_title(mt, b["measurement"], period),
                  fontsize=12, labelpad=12)
    ax.set_xlabel("")
    if show_level and len(df_b):
        level = float(df_b["Value"].mean())
        ax.axhline(
            y=level, color="#0ea5e9", linewidth=2, linestyle=":",
            label=f"Level: {round(level)}",
        )
        ax.annotate(
            f"Level: {round(level)}",
            xy=(0.01, level), xycoords=("axes fraction", "data"),
            xytext=(0, 3), textcoords="offset points",
            ha="left", va="bottom", fontsize=9, color="#0369a1",
        )
    if show_trend:
        fit = _best_fit_line(df_b["Date"], df_b["Value"])
        if fit:
            x0, x1, y0, y1, _slope = fit
            ax.plot(
                [x0, x1], [y0, y1],
                color="#1c1917", linewidth=2, linestyle="--",
            )
    y_lo, y_hi = ax.get_ylim()
    ax.set_ylim(0, max(y_hi, 1))
    if xr:
        ax.set_xlim(xr[0], xr[1])
    ax.grid(True, color="#f0eeec", linewidth=1)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#d6d3d1")

    for ph in phases or []:
        try:
            x_val = pd.to_datetime(ph["date"])
        except Exception:
            continue
        ax.axvline(
            x=x_val, color="#1c1917", linestyle="--",
            linewidth=1.2, alpha=0.6,
        )
        ax.annotate(
            ph.get("label", "Phase"),
            xy=(x_val, 1.0), xycoords=("data", "axes fraction"),
            xytext=(0, 4), textcoords="offset points",
            ha="center", va="bottom",
            fontsize=9, color="#1c1917",
            bbox=dict(
                boxstyle="round,pad=0.25",
                facecolor="white", edgecolor="#d6d3d1", linewidth=0.8,
            ),
        )

    if period == "Monthly":
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    elif period == "Yearly":
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    for label in ax.get_xticklabels():
        label.set_rotation(-35)
        label.set_horizontalalignment("left")
    fig.tight_layout()

    buf = _io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _behavior_scc_chart_png(b: dict, records: list[dict]) -> bytes | None:
    """Render the behavior's Standard Celeration Chart to a PNG byte string."""
    mt = MEASUREMENT_TYPES.get(b["measurement"], MEASUREMENT_TYPES["frequency"])
    b_rows = sorted(
        [r for r in records if r["behavior_id"] == b["id"]],
        key=lambda r: r["date"],
    )
    if not b_rows:
        return None
    scc_rows = []
    for r in b_rows:
        raw = _record_display_value(b, r)
        value_per_min = raw / 60.0 if b["measurement"] == "rate" else raw
        scc_rows.append({
            "Date": pd.to_datetime(r["date"]),
            "Value": max(float(value_per_min), 0.001),
        })
    df_scc = pd.DataFrame(scc_rows).sort_values("Date")
    scc_y_label = (
        "Count per minute"
        if b["measurement"] in ("rate", "frequency")
        else f"{mt['axis']} (log)"
    )
    fig = px.line(df_scc, x="Date", y="Value", markers=True)
    fig.update_traces(
        line=dict(color="#1c1917", width=1.5),
        marker=dict(size=7, color="#1c1917",
                    line=dict(width=1.2, color="white")),
    )
    fig.update_yaxes(
        type="log",
        range=[-3, 3],
        tickvals=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
        ticktext=[".001", ".01", ".1", "1", "10", "100", "1000"],
        gridcolor="#d6cfb8",
        zeroline=False,
        tickfont=dict(size=11),
        minor=dict(
            tickvals=[n * (10 ** e) for e in range(-3, 3) for n in range(2, 10)],
            gridcolor="#ece5d2",
            showgrid=True,
            ticks="",
        ),
        title=dict(text=scc_y_label, standoff=18, font=dict(size=14)),
    )
    _bphases = phases_for_behavior(b["student_id"], b["id"])
    fig.update_xaxes(
        range=_xrange_with_phases(
            df_scc["Date"], _bphases, pad_days=2, min_span_days=28,
        ),
        gridcolor="#d6cfb8",
        zeroline=False,
        showgrid=True,
        dtick=7 * 86400000,
        tickformat="%b %-d",
        title=None,
        tickangle=-35,
        tickfont=dict(size=11),
        minor=dict(
            dtick=86400000,
            gridcolor="#ece5d2",
            showgrid=True,
            ticks="",
        ),
    )
    _apply_phase_lines(fig, _bphases)
    fig.update_layout(
        margin=dict(l=90, r=30, t=40, b=90),
        height=700,
        width=1200,
        plot_bgcolor="#fffbef",
        paper_bgcolor="white",
        showlegend=False,
        font=dict(family="Helvetica, Arial, sans-serif", color="#1c1917"),
    )
    return _safe_to_image(fig, scale=2)


def _pdf_embed_png(pdf: FPDF, png: bytes, max_height_mm: float = 95.0):
    """Embed a PNG, fit to content width, preserving the source aspect ratio.

    Caps the rendered height at ``max_height_mm`` so the image doesn't push
    other sections off the page; falls through to ``add_page`` if it would.
    """
    if not png:
        return
    try:
        from PIL import Image
        with Image.open(io.BytesIO(png)) as img:
            img_w, img_h = img.size
    except Exception:
        img_w, img_h = 1100, 520
    aspect = img_h / img_w if img_w else 0.5
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    target_h = avail_w * aspect
    if target_h > max_height_mm:
        target_h = max_height_mm
        target_w = target_h / aspect if aspect else avail_w
    else:
        target_w = avail_w
    if pdf.get_y() + target_h > pdf.h - 18:
        pdf.add_page()
    pdf.image(
        io.BytesIO(png),
        x=pdf.l_margin,
        y=pdf.get_y(),
        w=target_w,
        h=target_h,
    )
    pdf.ln(target_h + 3)


def _pdf_chart_grid(
    pdf: FPDF, items: list[tuple], ncols: int = 2,
    gutter: float = 6.0, max_cell_h: float = 48.0,
):
    """Lay out (label, png) charts in an N-column grid with page-break handling.

    Each cell shows a small bold label above its chart. Charts keep their
    aspect ratio and are capped at ``max_cell_h`` mm tall.
    """
    if not items:
        return
    try:
        from PIL import Image
    except Exception:
        Image = None

    def _aspect(png: bytes) -> float:
        if Image is None:
            return 0.45
        try:
            with Image.open(io.BytesIO(png)) as im:
                iw, ih = im.size
            return (ih / iw) if iw else 0.45
        except Exception:
            return 0.45

    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = (avail_w - gutter * (ncols - 1)) / ncols
    label_h = 5.0
    for i in range(0, len(items), ncols):
        row = items[i:i + ncols]
        row_img_h = max(min(col_w * _aspect(png), max_cell_h) for _l, png in row)
        row_h = label_h + row_img_h + 5
        if pdf.get_y() + row_h > pdf.h - 18:
            pdf.add_page()
        y0 = pdf.get_y()
        for j, (lbl, png) in enumerate(row):
            x = pdf.l_margin + j * (col_w + gutter)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(120, 113, 108)
            pdf.text(x, y0 + 3.5, _pdf_safe(lbl))
            asp = _aspect(png)
            img_h = min(col_w * asp, max_cell_h)
            img_w = (img_h / asp) if asp else col_w
            if img_w > col_w:
                img_w, img_h = col_w, col_w * asp
            pdf.image(io.BytesIO(png), x=x, y=y0 + label_h, w=img_w, h=img_h)
        pdf.set_text_color(28, 25, 23)
        pdf.set_xy(pdf.l_margin, y0 + row_h)


def build_behavior_pdf(
    b: dict, sid: str, students: list[dict], records: list[dict],
) -> bytes:
    mt = MEASUREMENT_TYPES.get(b["measurement"], MEASUREMENT_TYPES["frequency"])
    name = student_name(students, sid)
    pdf = _pdf_init(f"Behavior of concern · {b['name']} · {name}")
    _pdf_h1(pdf, b["name"])
    _pdf_caption(
        pdf,
        f"{name}  ·  {mt['label']}  ·  generated {date.today().isoformat()}",
    )

    if b.get("definition"):
        _pdf_h2(pdf, "Operational definition")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(28, 25, 23)
        pdf.multi_cell(0, 5, _pdf_safe(b["definition"]))
        pdf.ln(2)

    b_records = sorted(
        [r for r in records if r["behavior_id"] == b["id"]],
        key=lambda r: r["date"],
    )

    _pdf_h2(pdf, "Summary")
    if not b_records:
        _pdf_caption(pdf, "No session data logged for this behavior yet.")
        return _pdf_bytes(pdf)

    display_vals = [_record_display_value(b, r) for r in b_records]
    _pdf_kv_row(pdf, "Total sessions:", str(len(b_records)))
    _pdf_kv_row(
        pdf, "Date range:",
        f"{b_records[0]['date']} to {b_records[-1]['date']}",
    )
    _pdf_kv_row(
        pdf, "Latest value:",
        f"{display_vals[-1]:g} {mt['unit']} on {b_records[-1]['date']}",
    )
    _pdf_kv_row(
        pdf, "Mean:",
        f"{sum(display_vals) / len(display_vals):.2f} {mt['unit']}",
    )
    _pdf_kv_row(
        pdf, "Min / Max:",
        f"{min(display_vals):g} / {max(display_vals):g} {mt['unit']}",
    )
    pdf.ln(3)

    applicable_phases = phases_for_behavior(sid, b["id"])
    if applicable_phases:
        _pdf_h2(pdf, "Phases")
        _pdf_caption(
            pdf,
            "Includes phases scoped to this behavior and student-wide phases.",
        )
        _pdf_table(
            pdf,
            ["Date", "Label", "Scope", "Notes"],
            [
                [
                    _fmt_date(p["date"]), p["label"],
                    "This behavior" if p.get("behavior_id") else "All behaviors",
                    p.get("notes", ""),
                ]
                for p in applicable_phases
            ],
            widths=[1, 2, 1.2, 2.5],
        )

    analysis = behavior_analysis(b, records, applicable_phases)
    if analysis and analysis["overall"]:
        _pdf_h2(pdf, "How is it going?")
        o = analysis["overall"]
        plain = _behavior_plain_summary(b, mt, o)
        # Strip markdown bold for PDF.
        plain = plain.replace("**", "")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(28, 25, 23)
        pdf.multi_cell(0, 5, _pdf_safe(plain))
        pdf.ln(2)
        _pdf_kv_row(
            pdf, "On a typical day:",
            f"{o['mean']:.1f} {mt['unit']}  "
            f"(range {o['min']:g}-{o['max']:g})",
        )
        _pdf_kv_row(
            pdf, "Direction:",
            f"{_direction_label(o['trend_desc'])}  "
            f"({_direction_subtitle(o, mt)})",
        )
        _pdf_kv_row(
            pdf, "Consistency:",
            f"{_variability_label(o['variability_desc'])}  "
            f"({_variability_subtitle(o)})",
        )
        _pdf_kv_row(
            pdf, "Sessions:",
            f"{o['n']} from {o['start_date']} to {o['end_date']}",
        )
        pdf.ln(2)
        if analysis["phases"]:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 6, _pdf_safe("Across program phases"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
            phase_rows = [
                [
                    p["label"],
                    f"{p['start_date']} - {p['end_date']}",
                    str(p["n"]),
                    f"{p['mean']:.1f}",
                    _direction_label(p["trend_desc"]),
                    _variability_label(p["variability_desc"]),
                ]
                for p in analysis["phases"]
            ]
            _pdf_table(
                pdf,
                [
                    "Phase", "Time period", "Sessions",
                    f"Typical ({mt['unit']})", "Direction", "Consistency",
                ],
                phase_rows,
                widths=[1.5, 1.6, 0.6, 1.0, 1.4, 1.4],
            )

    show_t = bool(st.session_state.get(f"bx_trend_{b['id']}"))
    show_l = bool(st.session_state.get(f"bx_level_{b['id']}"))
    # 1) Total line graph — every session over all time (default selection).
    if st.session_state.get(f"bx_pdf_line_{b['id']}", True):
        line_png = _behavior_line_chart_png(
            b, records, show_trend=show_t, show_level=show_l, period="Per session",
        )
        if line_png:
            _pdf_h2(pdf, "Line graph — all sessions")
            _pdf_embed_png(pdf, line_png, max_height_mm=85)
    # 2) Aggregated bar graphs — each selectable (Daily off by default).
    reducer_word = (
        "totals" if b["measurement"] in _GRAPH_SUM_MEASUREMENTS else "averages"
    )
    bar_specs = [
        ("Daily", f"bx_pdf_daily_{b['id']}", False),
        ("Weekly", f"bx_pdf_weekly_{b['id']}", True),
        ("Monthly", f"bx_pdf_monthly_{b['id']}", True),
        ("Yearly", f"bx_pdf_yearly_{b['id']}", True),
    ]
    bar_charts = []
    for period_name, skey, default_on in bar_specs:
        if not st.session_state.get(skey, default_on):
            continue
        png = _behavior_line_chart_png(
            b, records, show_trend=show_t, show_level=show_l, period=period_name,
        )
        if png:
            bar_charts.append((f"{period_name} {reducer_word}", png))
    if bar_charts:
        _pdf_h2(pdf, "Bar graphs")
        _pdf_chart_grid(pdf, bar_charts, ncols=2)

    if st.session_state.get(f"bx_pdf_scc_{b['id']}", True):
        scc_png = _behavior_scc_chart_png(b, records)
        if scc_png:
            _pdf_h2(pdf, "Standard Celeration Chart")
            _pdf_embed_png(pdf, scc_png, max_height_mm=115)

    _pdf_h2(pdf, "Session log")
    rows = []
    for r in reversed(b_records):
        v = behavior_value_display(b, r)
        if b["measurement"] == "rate":
            obs = r.get("obs_minutes") or 0
            v += f" [{int(r['value'])} in {obs:g} min]"
        rows.append([_fmt_date(r["date"]), v, r.get("notes", "") or ""])
    _pdf_table(pdf, ["Date", "Value", "Notes"], rows, widths=[1, 2, 3])

    return _pdf_bytes(pdf)


def build_mastery_log_pdf(
    sid: str, students: list[dict], targets: list[dict], probes: list[dict],
) -> bytes:
    name = student_name(students, sid)
    pdf = _pdf_init(f"Mastery Log · {name}")
    _pdf_h1(pdf, f"{name} — Mastery log")

    mastered = [t for t in targets if t["status"] == "Mastered" and t["student_id"] == sid]
    if not mastered:
        _pdf_caption(pdf, "No mastered targets yet.")
        return _pdf_bytes(pdf)

    by_op: dict[str, int] = {}
    for t in mastered:
        by_op[t["domain"]] = by_op.get(t["domain"], 0) + 1
    _pdf_kv_row(pdf, "Total mastered:", str(len(mastered)))
    _pdf_kv_row(pdf, "Operants represented:", str(len(by_op)))
    pdf.ln(2)

    _pdf_h2(pdf, "By operant")
    by_op_rows = []
    for op in sorted(by_op, key=lambda k: -by_op[k]):
        op_targets = [t for t in mastered if t["domain"] == op]
        avg_d = avg_days_to_mastery(op_targets, probes)
        by_op_rows.append([
            op,
            by_op[op],
            f"{avg_d:.1f}" if avg_d is not None else "-",
        ])
    _pdf_table(
        pdf,
        ["Operant", "Mastered", "Avg days to mastery"],
        by_op_rows,
        widths=[2.2, 1.0, 1.6],
    )

    _pdf_h2(pdf, "All mastered targets")
    rows = []
    for t in sorted(mastered, key=lambda t: (t.get("mastered_date") or ""), reverse=True):
        tp = [p for p in probes if p["target_id"] == t["id"]]
        rows.append([
            _fmt_date(first_data_date(t["id"], probes)) or "-",
            mastered_date_label(t) or "-",
            t["domain"],
            t.get("skill_list", "") or "-",
            t["description"],
            f"{mastery_n_for(t)} cons. Y" if t.get("mastered_via") != "PO" else "Probed out",
            str(t.get("mastered_probe_count", len(tp)) or len(tp)),
        ])
    _pdf_table(
        pdf,
        ["Date Introduced", "Date Mastered", "Operant", "List", "Target", "Criterion", "Probes"],
        rows,
        widths=[1.2, 1.2, 1.0, 1.2, 2.9, 1.2, 0.7],
    )
    return _pdf_bytes(pdf)


def page_export():
    st.header("Export")
    students = load_students()
    targets = load_targets()
    probes = load_probes()
    if not probes:
        st.info("Nothing to export yet.")
        return

    t_lookup = {t["id"]: t for t in targets}
    s_lookup = {s["id"]: s for s in students}
    rows = []
    for p in probes:
        t = t_lookup.get(p["target_id"], {})
        s = s_lookup.get(t.get("student_id", ""), {})
        rows.append({
            "date": p["date"],
            "student": s.get("name", ""),
            "domain": t.get("domain", ""),
            "target": t.get("description", ""),
            "response": p["response"],
            "error_type": p.get("error_type", ""),
            "clinician": p.get("clinician", ""),
            "recorded_at": p.get("recorded_at", ""),
        })
    df = pd.DataFrame(rows).sort_values(["date", "student", "target"])
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"cold_probes_{date.today().isoformat()}.csv",
        mime="text/csv",
    )


# ── App shell ────────────────────────────────────────────────────────────────
_CSS = """
<style>
/* Modern font stack — body only, leave icon fonts alone */
body {
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* Hide Streamlit chrome */
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

/* Keep the sidebar collapse/expand control visible */
[data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] {
  visibility: visible !important;
  display: block !important;
}

/* Force the sidebar visible (overrides Streamlit's collapsed transform) */
[data-testid="stSidebar"] {
  visibility: visible !important;
  display: flex !important;
  transform: none !important;
  margin-left: 0 !important;
  min-width: 244px !important;
}

/* App background — soft orange wash at top fading into warm stone */
.stApp {
  background:
    linear-gradient(180deg,
      #fff7ed 0%,
      #fef3e2 120px,
      #fafaf9 360px) no-repeat;
  background-attachment: fixed;
  background-color: #fafaf9;
}

/* Streamlit top bar — keep transparent so the wash shows through cleanly */
header[data-testid="stHeader"] {
  background: transparent !important;
  border-bottom: 1px solid rgba(254, 215, 170, 0.45);
}

/* Tighter top padding */
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1200px; }

/* Headers */
h1, h2, h3 { letter-spacing: -0.015em; color: #1c1917; }
h1 { font-weight: 700; }

/* Page hero — st.header renders as h2; give it a thin orange accent bar */
.block-container h2 {
  font-size: 1.95rem;
  font-weight: 650;
  line-height: 1.2;
  margin-top: 0.5rem;
  margin-bottom: 1.25rem;
  padding-bottom: 0.65rem;
  position: relative;
}
.block-container h2::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: 56px;
  height: 3px;
  border-radius: 2px;
  background: #ea580c;
}

h3 { font-weight: 600; padding-top: 0.5rem; }

/* Captions */
.stCaption, [data-testid="stCaptionContainer"] { color: #57534e; }

/* Sidebar polish */
[data-testid="stSidebar"] {
  background: #fafaf9;
  border-right: 1px solid #e7e5e4;
}
[data-testid="stSidebar"] h1 {
  font-size: 1.05rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  letter-spacing: -0.01em;
}
[data-testid="stSidebar"] .stButton > button {
  text-align: left;
  justify-content: flex-start;
  padding: 0.55rem 0.9rem;
  border-radius: 9px;
  font-weight: 500;
  border: 1px solid transparent;
  background: transparent;
  color: #44403c;
  transition: background 0.12s ease, color 0.12s ease;
  position: relative;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: #f5f5f4;
  color: #1c1917;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: #fff7ed;
  color: #9a3412;
  border-color: #fed7aa;
  box-shadow: inset 3px 0 0 #ea580c;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background: #ffedd5;
  color: #7c2d12;
}

/* Main-area buttons */
.main .stButton > button {
  border-radius: 9px;
  font-weight: 500;
  border: 1px solid #e7e5e4;
  transition: transform 0.05s ease, box-shadow 0.15s ease,
              border-color 0.12s ease, background 0.12s ease;
}
.main .stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 1px 2px rgba(28,25,23,0.06);
}
.main .stButton > button[kind="primary"] {
  border-color: #ea580c;
  box-shadow: 0 1px 2px rgba(234,88,12,0.18);
}
.main .stButton > button[kind="primary"]:hover {
  box-shadow: 0 2px 6px rgba(234,88,12,0.25);
}

/* Bordered containers (operant cards, session card, etc.) */
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 14px !important;
  border-color: #e7e5e4 !important;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(28,25,23,0.04);
  transition: box-shadow 0.15s ease, transform 0.05s ease,
              border-color 0.15s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  box-shadow: 0 4px 14px rgba(28,25,23,0.06);
  border-color: #d6d3d1 !important;
}

/* Dataframes */
[data-testid="stDataFrame"] {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e7e5e4;
}

/* Expanders */
[data-testid="stExpander"] {
  border: 1px solid #e7e5e4;
  border-radius: 11px;
  background: #ffffff;
  transition: border-color 0.12s ease, box-shadow 0.15s ease;
}
[data-testid="stExpander"]:hover { border-color: #d6d3d1; }
[data-testid="stExpander"] summary {
  font-weight: 500;
  padding: 0.65rem 0.85rem;
}

/* Inputs — softer borders */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stDateInput input, .stSelectbox > div > div {
  border-radius: 9px !important;
}

/* Tabs — refined indicator */
[data-testid="stTabs"] button[aria-selected="true"] {
  color: #ea580c !important;
}

/* Status / alert boxes — softer corners */
[data-testid="stAlertContentSuccess"],
[data-testid="stAlertContentInfo"],
[data-testid="stAlertContentWarning"],
[data-testid="stAlertContentError"],
[data-testid="stAlert"] {
  border-radius: 11px !important;
}

/* Section dividers */
hr { margin: 1.5rem 0; border-color: #e7e5e4; }

/* Metric blocks (Total mastered, Verbal operants, etc.) */
[data-testid="stMetric"] {
  background: #ffffff;
  border: 1px solid #e7e5e4;
  border-radius: 11px;
  padding: 0.85rem 1rem;
  box-shadow: 0 1px 2px rgba(28,25,23,0.04);
}
[data-testid="stMetricLabel"] { color: #78716c; font-weight: 500; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }

/* Save ribbon on the cold probe form */
.cpt-save-ribbon {
  background: linear-gradient(90deg, #16a34a 0%, #15803d 100%);
  color: #ffffff;
  font-weight: 600;
  font-size: 0.92rem;
  padding: 0.55rem 1rem;
  border-radius: 9px;
  margin: 0.25rem 0 0.75rem 0;
  box-shadow: 0 2px 6px rgba(21,128,61,0.25);
  animation: cptRibbonIn 0.25s ease-out;
}
@keyframes cptRibbonIn {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Outcome-button coloring — green for Y, red for N + error subtypes.
   Markers (.cpt-y-btn / .cpt-red-btn) are placed right before the
   target button; CSS `:has()` finds the marker's element container,
   then `+` styles the next sibling element-container's button.
   Adjacent-sibling `+` walks the DOM tree, so `display:none` on the
   marker container doesn't break the next-sibling match. */
.cpt-y-btn, .cpt-red-btn { display: none; }
[data-testid="stElementContainer"]:has(.cpt-y-btn),
[data-testid="stElementContainer"]:has(.cpt-red-btn),
[data-testid="element-container"]:has(.cpt-y-btn),
[data-testid="element-container"]:has(.cpt-red-btn) {
  display: none !important;
}

[data-testid="stElementContainer"]:has(.cpt-y-btn) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.cpt-y-btn) + [data-testid="element-container"] button {
  color: #2ca02c !important;
  border-color: #2ca02c !important;
}
[data-testid="stElementContainer"]:has(.cpt-y-btn) + [data-testid="stElementContainer"] button[kind="primary"],
[data-testid="stElementContainer"]:has(.cpt-y-btn) + [data-testid="stElementContainer"] button[data-testid="stBaseButton-primary"],
[data-testid="element-container"]:has(.cpt-y-btn) + [data-testid="element-container"] button[kind="primary"],
[data-testid="element-container"]:has(.cpt-y-btn) + [data-testid="element-container"] button[data-testid="stBaseButton-primary"] {
  background: #2ca02c !important;
  color: white !important;
  border-color: #2ca02c !important;
}

[data-testid="stElementContainer"]:has(.cpt-red-btn) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.cpt-red-btn) + [data-testid="element-container"] button {
  color: #d62728 !important;
  border-color: #d62728 !important;
}
[data-testid="stElementContainer"]:has(.cpt-red-btn) + [data-testid="stElementContainer"] button[kind="primary"],
[data-testid="stElementContainer"]:has(.cpt-red-btn) + [data-testid="stElementContainer"] button[data-testid="stBaseButton-primary"],
[data-testid="element-container"]:has(.cpt-red-btn) + [data-testid="element-container"] button[kind="primary"],
[data-testid="element-container"]:has(.cpt-red-btn) + [data-testid="element-container"] button[data-testid="stBaseButton-primary"] {
  background: #d62728 !important;
  color: white !important;
  border-color: #d62728 !important;
}

/* Operant cards on the Verbal Behavior Programming page — fixed height
   so every card is identical, button pinned to the bottom. */
.opcard { display: none; }
[data-testid="stVerticalBlockBorderWrapper"]:has(.opcard) {
  height: 260px !important;
  min-height: 260px !important;
  max-height: 260px !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.opcard)
  > div[data-testid="stVerticalBlock"] {
  flex: 1 1 auto !important;
  display: flex !important;
  flex-direction: column !important;
  height: 100%;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.opcard)
  > div[data-testid="stVerticalBlock"]
  > [data-testid="stElementContainer"]:has(.stButton) {
  margin-top: auto !important;
}

/* Operant-card "Open" button colors — one marker class per operant. */
.opbtn-yellow, .opbtn-purple, .opbtn-blue, .opbtn-green, .opbtn-red {
  display: none;
}
[data-testid="stElementContainer"]:has(.opbtn-yellow),
[data-testid="stElementContainer"]:has(.opbtn-purple),
[data-testid="stElementContainer"]:has(.opbtn-blue),
[data-testid="stElementContainer"]:has(.opbtn-green),
[data-testid="stElementContainer"]:has(.opbtn-red),
[data-testid="element-container"]:has(.opbtn-yellow),
[data-testid="element-container"]:has(.opbtn-purple),
[data-testid="element-container"]:has(.opbtn-blue),
[data-testid="element-container"]:has(.opbtn-green),
[data-testid="element-container"]:has(.opbtn-red) {
  display: none !important;
}

[data-testid="stElementContainer"]:has(.opbtn-yellow) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.opbtn-yellow) + [data-testid="element-container"] button {
  background: #eab308 !important;
  border-color: #ca8a04 !important;
  color: #1c1917 !important;
  box-shadow: 0 1px 2px rgba(202,138,4,0.25) !important;
}
[data-testid="stElementContainer"]:has(.opbtn-yellow) + [data-testid="stElementContainer"] button:hover,
[data-testid="element-container"]:has(.opbtn-yellow) + [data-testid="element-container"] button:hover {
  background: #ca8a04 !important;
  border-color: #a16207 !important;
}

[data-testid="stElementContainer"]:has(.opbtn-purple) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.opbtn-purple) + [data-testid="element-container"] button {
  background: #a855f7 !important;
  border-color: #9333ea !important;
  color: white !important;
  box-shadow: 0 1px 2px rgba(147,51,234,0.25) !important;
}
[data-testid="stElementContainer"]:has(.opbtn-purple) + [data-testid="stElementContainer"] button:hover,
[data-testid="element-container"]:has(.opbtn-purple) + [data-testid="element-container"] button:hover {
  background: #9333ea !important;
  border-color: #7e22ce !important;
}

[data-testid="stElementContainer"]:has(.opbtn-blue) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.opbtn-blue) + [data-testid="element-container"] button {
  background: #3b82f6 !important;
  border-color: #2563eb !important;
  color: white !important;
  box-shadow: 0 1px 2px rgba(37,99,235,0.25) !important;
}
[data-testid="stElementContainer"]:has(.opbtn-blue) + [data-testid="stElementContainer"] button:hover,
[data-testid="element-container"]:has(.opbtn-blue) + [data-testid="element-container"] button:hover {
  background: #2563eb !important;
  border-color: #1d4ed8 !important;
}

[data-testid="stElementContainer"]:has(.opbtn-green) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.opbtn-green) + [data-testid="element-container"] button {
  background: #16a34a !important;
  border-color: #15803d !important;
  color: white !important;
  box-shadow: 0 1px 2px rgba(21,128,61,0.25) !important;
}
[data-testid="stElementContainer"]:has(.opbtn-green) + [data-testid="stElementContainer"] button:hover,
[data-testid="element-container"]:has(.opbtn-green) + [data-testid="element-container"] button:hover {
  background: #15803d !important;
  border-color: #166534 !important;
}

[data-testid="stElementContainer"]:has(.opbtn-red) + [data-testid="stElementContainer"] button,
[data-testid="element-container"]:has(.opbtn-red) + [data-testid="element-container"] button {
  background: #dc2626 !important;
  border-color: #b91c1c !important;
  color: white !important;
  box-shadow: 0 1px 2px rgba(185,28,28,0.25) !important;
}
[data-testid="stElementContainer"]:has(.opbtn-red) + [data-testid="stElementContainer"] button:hover,
[data-testid="element-container"]:has(.opbtn-red) + [data-testid="element-container"] button:hover {
  background: #b91c1c !important;
  border-color: #991b1b !important;
}
</style>
"""


def _parse_bulk_po_text(
    text: str, default_operant: str, default_skill_list: str,
) -> list[dict]:
    """Parse bulk-PO paste text into row dicts.

    One target per line. Optional inline override using either:
      ``Operant: description``  (e.g., ``Tact: dog``)
      ``Operant / List: description``  (e.g., ``Tact / Animals: dog``)
    Lines without a recognized operant prefix fall back to ``default_operant``
    and ``default_skill_list``. Blank lines are skipped.
    """
    domain_lookup = {d.lower(): d for d in DOMAINS}
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        op = default_operant
        skill_list = default_skill_list
        desc = line
        if ":" in line:
            head, _, rest = line.partition(":")
            head_main, _, head_list = head.partition("/")
            head_key = head_main.strip().lower()
            if head_key in domain_lookup:
                op = domain_lookup[head_key]
                if head_list.strip():
                    skill_list = head_list.strip()
                desc = rest.strip()
        if desc:
            rows.append({
                "Description": desc,
                "Operant": op,
                "Skill list": skill_list,
            })
    return rows


_BULK_MODES = {
    "po": {
        "label": "Probed out (already mastered)",
        "help": (
            "Targets the student already demonstrates. Each row is added as "
            "**Mastered** via **PO** with today's date. They appear in the "
            "mastery log and bump the cumulative mastered chart."
        ),
        "needs_date": True,
        "verb": "Import",
        "result_status": "Mastered",
    },
    "plan": {
        "label": "Planned (not yet introduced)",
        "help": (
            "Targets you intend to teach later. Each row is added as **Planned** "
            "with no date and no probes. They stay off Probe Entry and the "
            "mastered chart until you press **Introduce** in the operant page."
        ),
        "needs_date": False,
        "verb": "Add",
        "result_status": "Planned",
    },
    "bank": {
        "label": "Target Bank only (no student attached)",
        "help": (
            "Loads these targets into the cross-student **Target Bank** without "
            "attaching them to anyone. Use the Target Bank page to add them to "
            "a student later."
        ),
        "needs_date": False,
        "verb": "Load",
        "result_status": "in Target Bank",
    },
}


def _render_bulk_add(sid: str):
    """Bulk-add UI body. Caller renders any surrounding header / expander."""
    mode_keys = list(_BULK_MODES)
    mode_labels = [_BULK_MODES[k]["label"] for k in mode_keys]
    chosen_idx = st.radio(
        "How should the new targets be added?",
        options=range(len(mode_keys)),
        format_func=lambda i: mode_labels[i],
        horizontal=True,
        key="bulk_mode",
    )
    mode = mode_keys[chosen_idx]
    cfg = _BULK_MODES[mode]
    st.caption(cfg["help"])

    last = st.session_state.get("last_bulk_import")
    if last and (last.get("mode") == "bank" or last.get("student_id") == sid):
        info_col, btn_col = st.columns([5, 2])
        with info_col:
            st.success(
                f"✓ Last import: **{last['count']}** target(s) as "
                f"**{last['result_status']}**."
            )
        with btn_col:
            if st.button(
                f"↩ Undo last import",
                key="bulk_undo",
                width="stretch",
                help="Removes the rows you just added (and any mastery they triggered).",
            ):
                ids_to_remove = set(last["target_ids"])
                if last.get("mode") == "bank":
                    save_target_bank(
                        [b for b in load_target_bank() if b["id"] not in ids_to_remove]
                    )
                else:
                    save_targets(
                        [t for t in load_targets() if t["id"] not in ids_to_remove]
                    )
                    save_mastery_events(
                        [e for e in load_mastery_events() if e["target_id"] not in ids_to_remove]
                    )
                st.session_state.pop("last_bulk_import", None)
                st.toast(f"Removed {last['count']} entry(ies).")
                st.rerun()

    targets = load_targets()
    ver = st.session_state.get("bulk_form_version", 0)

    c1, c2 = st.columns([1, 1])
    with c1:
        default_op = st.selectbox("Default operant", DOMAINS, key="bulk_default_op")

    existing_lists = sorted({
        (t.get("skill_list") or "").strip()
        for t in targets
        if t["student_id"] == sid
        and t["domain"] == default_op
        and (t.get("skill_list") or "").strip()
    })

    with c2:
        if existing_lists:
            NONE_OPT = "— No list —"
            NEW_OPT = "➕ New list…"
            options = [NONE_OPT, *existing_lists, NEW_OPT]
            picked = st.selectbox(
                "Default skill list",
                options=options,
                key=f"bulk_default_listpick_{default_op}_{ver}",
            )
            if picked == NEW_OPT:
                new_name = st.text_input(
                    "New list name",
                    key=f"bulk_default_listnew_{default_op}_{ver}",
                    placeholder="e.g., Tacts of Animals",
                )
                default_list = new_name.strip()
            elif picked == NONE_OPT:
                default_list = ""
            else:
                default_list = picked
        else:
            default_list = st.text_input(
                "Default skill list (optional)", key=f"bulk_default_list_{ver}",
                placeholder="e.g., Tacts of Animals",
            )

    mastered_on = date.today() if cfg["needs_date"] else None

    st.markdown("**1. Paste a list, upload a CSV, or edit the table below**")
    paste_tab, csv_tab = st.tabs(["📋 Paste", "📄 CSV"])
    parsed_rows: list[dict] = []
    with paste_tab:
        st.caption(
            "One target per line. Optional inline override: "
            "`Tact: dog` or `Tact / Animals: dog`. "
            "Lines without a prefix use the defaults above."
        )
        text = st.text_area(
            "Targets",
            height=180,
            key=f"bulk_paste_{ver}",
            placeholder='SD "Touch eyes."\nTact: dog\nMand / Snacks: pretzels',
            label_visibility="collapsed",
        )
        if text.strip():
            parsed_rows = _parse_bulk_po_text(text, default_op, default_list)
    with csv_tab:
        st.caption(
            "CSV with at least a `description` column. Optional `operant` "
            "and `skill_list` columns override the defaults per row."
        )
        up = st.file_uploader("CSV file", type=["csv"], key=f"bulk_csv_{ver}")
        if up is not None:
            try:
                df_in = pd.read_csv(up)
                df_in.columns = [c.strip().lower() for c in df_in.columns]
                if "description" not in df_in.columns:
                    st.error("CSV must include a `description` column.")
                else:
                    for _, r in df_in.iterrows():
                        desc = str(r.get("description", "")).strip()
                        if not desc:
                            continue
                        op = str(r.get("operant", "")).strip() or default_op
                        if op not in DOMAINS:
                            op = default_op
                        sl = str(r.get("skill_list", "")).strip() or default_list
                        parsed_rows.append({
                            "Description": desc, "Operant": op, "Skill list": sl,
                        })
            except Exception as e:
                st.error(f"Could not read CSV: {e}")

    st.markdown("**2. Review & edit**")
    if not parsed_rows:
        parsed_rows = [{"Description": "", "Operant": default_op, "Skill list": default_list}]
    edited = st.data_editor(
        pd.DataFrame(parsed_rows),
        num_rows="dynamic",
        width="stretch",
        key=f"bulk_editor_{mode}_{ver}",
        column_config={
            "Description": st.column_config.TextColumn("Description", required=True),
            "Operant": st.column_config.SelectboxColumn(
                "Operant", options=DOMAINS, required=True,
            ),
            "Skill list": st.column_config.TextColumn("Skill list (optional)"),
        },
    )

    final_rows = [
        r for r in edited.to_dict("records")
        if str(r.get("Description", "")).strip()
        and str(r.get("Operant", "")).strip() in DOMAINS
    ]
    st.caption(f"{len(final_rows)} target(s) ready.")

    button_label = (
        f"✅ {cfg['verb']} {len(final_rows)} target(s) as {cfg['result_status']}"
        + (" (PO)" if mode == "po" else "")
    )
    if st.button(
        button_label, type="primary", width="stretch", disabled=not final_rows,
    ):
        new_target_ids: list[str] = []
        if mode == "po":
            mastered_iso = mastered_on.isoformat()
            for r in final_rows:
                tid = new_id()
                new_target_ids.append(tid)
                targets.append({
                    "id": tid,
                    "student_id": sid,
                    "description": str(r["Description"]).strip(),
                    "domain": r["Operant"],
                    "skill_list": str(r.get("Skill list") or "").strip(),
                    "mastery_n": DEFAULT_MASTERY_N,
                    "mastery_criterion": "",
                    "status": "Mastered",
                    "mastered_date": mastered_iso,
                    "mastered_via": "PO",
                    "mastered_probe_count": 0,
                })
            save_targets(targets)
            for tid in new_target_ids:
                log_mastery_event(sid, tid, "mastered", mastered_iso)
            st.success(f"Imported {len(final_rows)} probed-out target(s).")
        elif mode == "plan":
            for r in final_rows:
                tid = new_id()
                new_target_ids.append(tid)
                targets.append({
                    "id": tid,
                    "student_id": sid,
                    "description": str(r["Description"]).strip(),
                    "domain": r["Operant"],
                    "skill_list": str(r.get("Skill list") or "").strip(),
                    "mastery_n": DEFAULT_MASTERY_N,
                    "mastery_criterion": "",
                    "status": "Planned",
                    "mastered_date": "",
                })
            save_targets(targets)
            st.success(f"Added {len(final_rows)} planned target(s).")
        else:  # mode == "bank"
            new_target_ids = save_targets_to_bank(
                [{
                    "description": str(r["Description"]).strip(),
                    "domain": r["Operant"],
                    "skill_list": str(r.get("Skill list") or "").strip(),
                    "mastery_n": DEFAULT_MASTERY_N,
                } for r in final_rows],
                source_student_name="bulk-add",
            )
            n_added = len(new_target_ids)
            n_dupes = len(final_rows) - n_added
            if n_added:
                msg = f"Loaded {n_added} entry(ies) into the Target Bank."
                if n_dupes:
                    msg += f" ({n_dupes} already present — skipped.)"
                st.success(msg)
            else:
                st.info("All rows were already in the bank — nothing new added.")
        st.session_state["last_bulk_import"] = {
            "student_id": sid,
            "target_ids": new_target_ids,
            "mode": mode,
            "count": len(new_target_ids),
            "result_status": cfg["result_status"] + (" (PO)" if mode == "po" else ""),
        }
        st.session_state["bulk_form_version"] = ver + 1
        st.rerun()


def _behavior_input(behavior: dict, existing: dict | None, key_prefix: str):
    """Render the right input(s) for a behavior's measurement type.

    Returns (value, obs_minutes) — obs_minutes is only set for rate behaviors.
    """
    measurement = behavior.get("measurement", "frequency")
    mt = MEASUREMENT_TYPES.get(measurement, MEASUREMENT_TYPES["frequency"])
    cur_val = existing["value"] if existing else mt["value_min"]
    cur_obs = existing.get("obs_minutes") if existing else None

    if measurement == "magnitude":
        idx_default = max(0, min(4, int(cur_val) - 1))
        choice = st.selectbox(
            mt["label"],
            options=[1, 2, 3, 4, 5],
            index=idx_default,
            key=f"{key_prefix}_val",
            help=mt["help"],
        )
        return float(choice), None

    if measurement == "rate":
        rc1, rc2 = st.columns([1, 1])
        with rc1:
            count = st.number_input(
                "Count",
                min_value=0, step=1, value=int(cur_val or 0),
                format="%d", key=f"{key_prefix}_count",
            )
        with rc2:
            obs = st.number_input(
                "Observation minutes",
                min_value=0.0, step=5.0,
                value=float(cur_obs) if cur_obs else 60.0,
                format="%.1f", key=f"{key_prefix}_obs",
            )
        return float(count), float(obs)

    if measurement == "frequency":
        val = st.number_input(
            mt["label"],
            min_value=0, step=1, value=int(cur_val or 0),
            format="%d",
            key=f"{key_prefix}_val",
            help=mt["help"],
        )
        return float(val), None

    # duration, latency — float-typed inputs
    val = st.number_input(
        mt["label"],
        min_value=float(mt["value_min"]),
        step=float(mt["value_step"]),
        value=float(cur_val or 0.0),
        format=mt["value_format"],
        key=f"{key_prefix}_val",
        help=mt["help"],
    )
    return float(val), None


_DIRECTION_LABELS = {
    "increasing": "↗ Going up",
    "decreasing": "↘ Going down",
    "stable": "→ Holding steady",
    "—": "—",
}

_VARIABILITY_LABELS = {
    "low": "Very consistent",
    "moderate": "Some ups and downs",
    "high": "Quite variable",
    "—": "—",
}


def _direction_label(key: str) -> str:
    return _DIRECTION_LABELS.get(key, "—")


def _variability_label(key: str) -> str:
    return _VARIABILITY_LABELS.get(key, "—")


def _qty_noun(unit: str, singular: bool) -> str:
    """Human counting noun for a measurement unit.

    'count' is a measurement *type*, not a thing you can have "2 of" — so
    frequency behaviors read as instance(s). Other units (minutes, seconds,
    per hour, 1–5) already read naturally and are returned unchanged.
    """
    if unit == "count":
        return "instance" if singular else "instances"
    return unit


def _whole_avg(mean: float, unit: str) -> str:
    """Decimal-free 'typical level' phrasing for a per-session average."""
    if mean >= 0.95:
        q = round(mean)
        return f"{q} {_qty_noun(unit, q == 1)}"
    if mean <= 0:
        return f"0 {_qty_noun(unit, False)}"
    return f"less than 1 {_qty_noun(unit, True)}"


def _whole_avg_card(mean: float, unit: str) -> str:
    """Compact decimal-free typical level for the metric card (uses '<1')."""
    if mean >= 0.95:
        q = round(mean)
        return f"{q} {_qty_noun(unit, q == 1)}"
    if mean <= 0:
        return f"0 {_qty_noun(unit, False)}"
    return f"<1 {_qty_noun(unit, True)}"


def _whole_avg_short(mean: float) -> str:
    """Bare decimal-free number for table cells (unit lives in the header)."""
    if mean >= 0.95:
        return str(round(mean))
    if mean <= 0:
        return "0"
    return "<1"


def _trend_rate_phrase(per_week: float, unit: str) -> str:
    """Decimal-free description of the weekly trend rate."""
    word = "down" if per_week < 0 else "up"
    wk = abs(per_week)
    if round(wk) >= 1:
        q = round(wk)
        return f"about {q} {_qty_noun(unit, q == 1)} {word}/week"
    return f"less than 1 {_qty_noun(unit, True)} {word}/week"


def _direction_subtitle(o: dict, mt: dict) -> str:
    if o["n"] < 2 or o["trend_desc"] == "stable":
        return "holding steady"
    return _trend_rate_phrase(o["slope_per_week"], mt["unit"])


def _variability_subtitle(o: dict) -> str:
    if o["n"] < 2:
        return "—"
    return f"range {o['min']:g}–{o['max']:g}"


def _behavior_plain_summary(b: dict, mt: dict, o: dict) -> str:
    """One-paragraph plain-English summary parents can read."""
    if o["n"] < 2:
        return (
            f"Only **{o['n']}** session logged so far for **{b['name']}** — "
            "not enough data to spot a trend yet. Keep logging and a clear "
            "picture will emerge."
        )
    direction = {
        "increasing": "going up",
        "decreasing": "going down",
        "stable": "holding steady",
    }.get(o["trend_desc"], "")
    consistency = {
        "low": "very consistent from session to session",
        "moderate": "with some day-to-day ups and downs",
        "high": "with quite a bit of variation between sessions",
    }.get(o["variability_desc"], "")
    avg_phrase = _whole_avg(o["mean"], mt["unit"])
    avg_lead = "averaging " + ("about " if o["mean"] >= 0.95 else "")
    parts = [
        f"Across **{o['n']}** sessions from {o['start_date']} to "
        f"{o['end_date']}, **{b['name']}** has been **{direction}**, "
        f"{avg_lead}**{avg_phrase}** per session"
    ]
    if consistency:
        parts.append(f", {consistency}")
    parts.append(".")
    if abs(o["slope_per_week"]) > 0.05 and o["trend_desc"] != "stable":
        wc = abs(o["slope_per_week"])
        word = "decreasing" if o["slope_per_week"] < 0 else "increasing"
        if round(wc) >= 1:
            parts.append(
                f" That works out to about **{round(wc)} "
                f"{_qty_noun(mt['unit'], round(wc) == 1)} "
                f"{word} per week** on average."
            )
        else:
            parts.append(
                f" The change is gradual — **less than 1 {mt['unit']} per week**."
            )
    return "".join(parts)


def _analyze_subset(b: dict, subset: list[dict]) -> dict | None:
    """Compute level/trend/variability stats for a list of behavior records."""
    if not subset:
        return None
    sorted_subset = sorted(subset, key=lambda r: r["date"])
    values = [_record_display_value(b, r) for r in sorted_subset]
    dates = pd.to_datetime([r["date"] for r in sorted_subset])
    n = len(values)
    mean = sum(values) / n
    sd = (
        math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
        if n > 1 else 0.0
    )
    v_min, v_max = min(values), max(values)
    v_range = v_max - v_min
    x_days = [(d - dates.min()).days for d in dates]
    slope = 0.0
    if n > 1 and len(set(x_days)) > 1:
        x_mean = sum(x_days) / n
        num = sum((x - x_mean) * (v - mean) for x, v in zip(x_days, values))
        den = sum((x - x_mean) ** 2 for x in x_days)
        slope = num / den if den else 0.0
    cv = (sd / mean) if mean else 0.0
    if n < 2:
        trend_desc = "—"
    elif mean == 0 or abs(slope) / (abs(mean) + 1e-9) < 0.02:
        trend_desc = "stable"
    elif slope > 0:
        trend_desc = "increasing"
    else:
        trend_desc = "decreasing"
    if n < 2:
        variability_desc = "—"
    elif cv < 0.2:
        variability_desc = "low"
    elif cv < 0.5:
        variability_desc = "moderate"
    else:
        variability_desc = "high"
    return {
        "n": n, "mean": mean, "sd": sd,
        "min": v_min, "max": v_max, "range": v_range,
        "slope_per_day": slope, "slope_per_week": slope * 7,
        "trend_desc": trend_desc,
        "cv": cv, "variability_desc": variability_desc,
        "start_date": dates.min().strftime("%m/%d/%Y"),
        "end_date": dates.max().strftime("%m/%d/%Y"),
    }


def behavior_analysis(
    b: dict, records: list[dict], phases: list[dict],
) -> dict | None:
    """Return overall + per-phase visual-analysis stats for a behavior."""
    b_records = sorted(
        [r for r in records if r["behavior_id"] == b["id"]],
        key=lambda r: r["date"],
    )
    if not b_records:
        return None
    overall = _analyze_subset(b, b_records)
    phase_blocks: list[dict] = []
    sorted_phases = sorted(phases, key=lambda p: p["date"]) if phases else []
    if sorted_phases:
        first_dt = pd.to_datetime(sorted_phases[0]["date"])
        pre = [r for r in b_records if pd.to_datetime(r["date"]) < first_dt]
        if pre:
            block = _analyze_subset(b, pre)
            if block:
                block["label"] = "Pre-phase"
                phase_blocks.append(block)
        for i, ph in enumerate(sorted_phases):
            start_dt = pd.to_datetime(ph["date"])
            if i + 1 < len(sorted_phases):
                end_dt = pd.to_datetime(sorted_phases[i + 1]["date"])
                subset = [
                    r for r in b_records
                    if start_dt <= pd.to_datetime(r["date"]) < end_dt
                ]
            else:
                subset = [
                    r for r in b_records
                    if pd.to_datetime(r["date"]) >= start_dt
                ]
            block = _analyze_subset(b, subset)
            if block:
                block["label"] = ph["label"]
                phase_blocks.append(block)
    return {"overall": overall, "phases": phase_blocks}


def _record_display_value(behavior: dict, record: dict) -> float:
    """The number to plot/display for a record (rate is computed)."""
    if behavior["measurement"] == "rate":
        obs = record.get("obs_minutes") or 0
        if obs <= 0:
            return 0.0
        return float(record["value"]) / (obs / 60.0)
    return float(record["value"])


def _humanize_rate(per_hour: float) -> str:
    """'8.57 per hour' -> 'about once every 7 min'."""
    if per_hour <= 0:
        return "no occurrences"
    minutes_between = 60.0 / per_hour
    if minutes_between >= 90:
        return f"about once every {minutes_between / 60.0:.1f} hr"
    if minutes_between >= 1.5:
        return f"about once every {round(minutes_between)} min"
    return f"about once every {round(minutes_between * 60.0)} sec"


def _humanize_minutes(mins: float) -> str:
    """1.25 -> '1 min 15 sec'."""
    total_sec = round(mins * 60)
    m, s = divmod(total_sec, 60)
    if m and s:
        return f"{m} min {s} sec"
    if m:
        return f"{m} min"
    return f"{s} sec"


def behavior_value_display(behavior: dict, record: dict) -> str:
    """Human-readable value: plain-language reframe with the decimal in parentheses.

    Frequency / magnitude are already whole numbers and are returned plainly.
    """
    measurement = behavior.get("measurement", "frequency")
    mt = MEASUREMENT_TYPES.get(measurement, MEASUREMENT_TYPES["frequency"])
    val = _record_display_value(behavior, record)
    if measurement == "rate":
        return f"{_humanize_rate(val)} ({val:.2f} per hour)"
    if measurement == "duration":
        return f"{_humanize_minutes(val)} ({val:g} min)"
    if measurement == "latency":
        if val >= 90:
            return f"about {val / 60.0:.1f} min ({val:g} sec)"
        return f"{val:g} sec"
    if measurement == "magnitude":
        return f"{int(val)} of 5"
    return f"{int(val)} {mt['unit']}"


# ── Behavior-graph time filters ──────────────────────────────────────────────
# Window options map a label to a look-back length in days (None = all history).
GRAPH_WINDOW_OPTIONS: dict[str, int | None] = {
    "All time": None,
    "Last 30 days": 30,
    "Last 3 months": 90,
    "Last 6 months": 182,
    "Last year": 365,
}
GRAPH_PERIOD_OPTIONS = ["Per session", "Daily", "Weekly", "Monthly"]
# Measurements that are additive over a period (total count / total minutes).
# Everything else (rate, latency, magnitude) is averaged instead.
_GRAPH_SUM_MEASUREMENTS = {"frequency", "duration"}


_GRAPH_CUSTOM_LABEL = "Custom…"


def _behavior_graph_controls(
    key_suffix: str, *, allow_period: bool = True, data_dates=None,
):
    """Render time-window (and optional aggregation) selectors.

    Returns ``(window_days, period, custom_range)``: ``window_days`` is an int
    or None (all time), ``period`` is one of ``GRAPH_PERIOD_OPTIONS``, and
    ``custom_range`` is None or a ``(start_date, end_date)`` tuple when the
    user picked **Custom…**.
    """
    cols = st.columns(2 if allow_period else 1)
    with cols[0]:
        window_label = st.selectbox(
            "Time window",
            list(GRAPH_WINDOW_OPTIONS) + [_GRAPH_CUSTOM_LABEL],
            index=0,
            key=f"bx_window_{key_suffix}",
        )
    period = "Per session"
    if allow_period:
        with cols[1]:
            period = st.selectbox(
                "Aggregate",
                GRAPH_PERIOD_OPTIONS,
                index=0,
                key=f"bx_period_{key_suffix}",
                help="Combine sessions into one point per day, week, or month.",
            )

    custom_range = None
    window_days = None
    if window_label == _GRAPH_CUSTOM_LABEL:
        if data_dates is not None and len(data_dates):
            _dts = pd.to_datetime(list(data_dates))
            d_lo, d_hi = _dts.min().date(), _dts.max().date()
        else:
            d_hi = date.today()
            d_lo = (pd.Timestamp(d_hi) - pd.Timedelta(days=30)).date()
        cc1, cc2 = st.columns(2)
        with cc1:
            c_start = st.date_input(
                "From", value=d_lo, key=f"bx_cfrom_{key_suffix}",
            )
        with cc2:
            c_end = st.date_input(
                "To", value=d_hi, key=f"bx_cto_{key_suffix}",
            )
        if c_start and c_end:
            if c_start > c_end:
                st.warning("'From' is after 'To' — showing the range anyway.")
                c_start, c_end = c_end, c_start
            custom_range = (c_start, c_end)
    else:
        window_days = GRAPH_WINDOW_OPTIONS[window_label]
    return window_days, period, custom_range


def _filter_window(df: pd.DataFrame, window_days: int | None) -> pd.DataFrame:
    """Keep rows whose ``Date`` falls within ``window_days`` of today."""
    if window_days is None or df.empty:
        return df
    cutoff = pd.Timestamp(date.today()) - pd.Timedelta(days=window_days)
    return df[df["Date"] >= cutoff]


def _apply_time_filter(df: pd.DataFrame, window_days, custom_range) -> pd.DataFrame:
    """Filter ``Date``/``Value`` rows by a custom range, else by ``window_days``."""
    if custom_range is not None and not df.empty:
        start, end = pd.Timestamp(custom_range[0]), pd.Timestamp(custom_range[1])
        return df[(df["Date"] >= start) & (df["Date"] <= end)]
    return _filter_window(df, window_days)


def _aggregate_period(
    df: pd.DataFrame, measurement: str, period: str,
) -> pd.DataFrame:
    """Bucket ``Date``/``Value`` rows by period, summing or averaging Value.

    Frequency and duration sum (additive totals); all other measurements are
    averaged. Empty buckets are dropped. ``Per session`` returns df unchanged.
    """
    if period == "Per session" or df.empty:
        return df
    reducer = "sum" if measurement in _GRAPH_SUM_MEASUREMENTS else "mean"
    # Group on the period each record falls in — only periods that actually have
    # data become points (no zero-filled empty days/weeks/months).
    if period == "Daily":
        keys = df["Date"].dt.normalize()
    elif period == "Weekly":
        keys = df["Date"].dt.to_period("W").dt.start_time
    elif period == "Yearly":
        keys = df["Date"].dt.to_period("Y").dt.start_time
    else:  # Monthly
        keys = df["Date"].dt.to_period("M").dt.start_time
    grouped = df.groupby(keys)["Value"].agg(reducer).reset_index()
    grouped.columns = ["Date", "Value"]
    return grouped.sort_values("Date")


def _graph_y_title(mt: dict, measurement: str, period: str) -> str:
    """Y-axis title reflecting aggregation, e.g. 'Count — monthly total'."""
    if period == "Per session":
        return mt["axis"]
    base = mt["axis"].replace(" per session", "")
    adj = {
        "Daily": "daily", "Weekly": "weekly",
        "Monthly": "monthly", "Yearly": "yearly",
    }.get(period, period.lower())
    reducer = "total" if measurement in _GRAPH_SUM_MEASUREMENTS else "average"
    return f"{base} — {adj} {reducer}"


def _apply_period_xticks(fig, period: str) -> None:
    """Format the date axis to match the aggregation period.

    Monthly bars show their x labels as ``MM/YYYY`` with one tick per month.
    """
    if period == "Monthly":
        fig.update_xaxes(tickformat="%m/%Y", dtick="M1")
    elif period == "Yearly":
        fig.update_xaxes(tickformat="%Y", dtick="M12")


def _integer_yaxis(fig, values) -> None:
    """Force whole-number y-axis ticks — never show decimals on the chart.

    Data points are left untouched (they fall between ticks as needed); only the
    tick labels/step are constrained to nice round integers (1, 2, 5, 10, …).
    """
    vmax = 1.0
    try:
        vmax = max((float(v) for v in values), default=1.0)
    except (TypeError, ValueError):
        vmax = 1.0
    vmax = max(vmax, 1.0)
    raw = max(vmax / 5.0, 1.0)  # aim for ~5 ticks
    mag = 10 ** math.floor(math.log10(raw))
    step = next((m * mag for m in (1, 2, 5, 10) if m * mag >= raw), 10 * mag)
    dtick = max(1, int(round(step)))
    fig.update_yaxes(tickformat="d", tickmode="linear", tick0=0, dtick=dtick)


def _best_fit_line(dates, values):
    """Least-squares endpoints for a best-fit line over (date, value) points.

    Returns ``(x0, x1, y0, y1)`` spanning the date range plus the slope, or
    None when a line can't be fit (fewer than 2 points on distinct dates).
    """
    x = [(d - dates.min()).days for d in dates]
    y = [float(v) for v in values]
    n = len(x)
    if n < 2 or len(set(x)) < 2:
        return None
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    den = sum((xi - x_mean) ** 2 for xi in x)
    if den == 0:
        return None
    slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y)) / den
    intercept = y_mean - slope * x_mean
    x_max = max(x)
    return dates.min(), dates.max(), intercept, intercept + slope * x_max, slope


def page_behaviors():
    students = load_students()
    if not students:
        st.header("Behaviors of Concern")
        st.info("Add a student first.")
        return

    sid = current_sid(students)
    st.header(f"Behaviors of Concern · {student_name(students, sid)}")
    st.caption("Log today's data quickly, or open a behavior to view trends and edit.")

    behaviors = load_behaviors()
    student_behaviors = [b for b in behaviors if b["student_id"] == sid]
    records = load_behavior_records()
    student_records = [r for r in records if r["student_id"] == sid]

    # ── Quick entry (one row per behavior, single Save-all) ──────────────────
    if student_behaviors:
        quick_ver = st.session_state.get("bx_quick_ver", 0)
        with st.container(border=True):
            st.markdown("### Log today's data")
            entry_day = st.date_input(
                "Date", value=date.today(), key="bx_quick_date",
            )
            day_iso = entry_day.isoformat()
            day_records = [
                r for r in records
                if r["date"] == day_iso and r["student_id"] == sid
            ]
            if day_records:
                last_recorded = max(r.get("recorded_at", "") for r in day_records)
                try:
                    dt = datetime.fromisoformat(last_recorded)
                    time_label = dt.strftime("%m/%d/%Y at %-I:%M %p")
                except (ValueError, TypeError):
                    time_label = last_recorded or "earlier"
                st.success(
                    f"✓ **Behavior data submitted for {_fmt_date(day_iso)}** — "
                    f"{len(day_records)} of {len(student_behaviors)} behavior(s) logged; "
                    f"last updated {time_label}."
                )
            else:
                st.caption(f"No behavior data submitted yet for {_fmt_date(day_iso)}.")
            pending: dict[str, tuple[float, float | None]] = {}
            for b in student_behaviors:
                existing = next(
                    (r for r in records
                     if r["behavior_id"] == b["id"] and r["date"] == day_iso),
                    None,
                )
                mt = MEASUREMENT_TYPES.get(
                    b["measurement"], MEASUREMENT_TYPES["frequency"]
                )
                row = st.columns([4, 3, 2])
                with row[0]:
                    st.markdown(f"**{b['name']}**")
                    st.caption(mt["label"])
                with row[1]:
                    # Inputs always start at defaults so saving clears them.
                    # The "Logged:" caption to the right shows the current saved value.
                    if b["measurement"] == "magnitude":
                        v = st.selectbox(
                            "value", options=[1, 2, 3, 4, 5],
                            index=0,
                            label_visibility="collapsed",
                            key=f"bxq_{b['id']}_{day_iso}_{quick_ver}",
                        )
                        pending[b["id"]] = (float(v), None)
                    elif b["measurement"] == "rate":
                        cc, oc = st.columns(2)
                        with cc:
                            cnt = st.number_input(
                                "count", min_value=0, step=1,
                                value=0, format="%d",
                                label_visibility="collapsed",
                                key=f"bxq_cnt_{b['id']}_{day_iso}_{quick_ver}",
                            )
                        with oc:
                            obs = st.number_input(
                                "obs min", min_value=0.0, step=5.0,
                                value=60.0, format="%.1f",
                                label_visibility="collapsed",
                                key=f"bxq_obs_{b['id']}_{day_iso}_{quick_ver}",
                            )
                        pending[b["id"]] = (float(cnt), float(obs))
                    elif b["measurement"] == "frequency":
                        v = st.number_input(
                            "value", min_value=0, step=1,
                            value=0, format="%d",
                            label_visibility="collapsed",
                            key=f"bxq_{b['id']}_{day_iso}_{quick_ver}",
                        )
                        pending[b["id"]] = (float(v), None)
                    else:
                        v = st.number_input(
                            "value",
                            min_value=float(mt["value_min"]),
                            step=float(mt["value_step"]),
                            value=float(mt["value_min"]),
                            format=mt["value_format"],
                            label_visibility="collapsed",
                            key=f"bxq_{b['id']}_{day_iso}_{quick_ver}",
                        )
                        pending[b["id"]] = (float(v), None)
                with row[2]:
                    if existing:
                        st.caption(
                            f"Logged: **{behavior_value_display(b, existing)}**"
                        )
                    else:
                        st.caption("—")
            sa, ca = st.columns([1, 1])
            with sa:
                if st.button(
                    "💾 Save all behaviors for this date",
                    key=f"bxq_save_all_{day_iso}",
                    type="primary",
                    width="stretch",
                ):
                    for b in student_behaviors:
                        v, obs = pending.get(b["id"], (0.0, None))
                        upsert_behavior_record(
                            b["id"], sid, day_iso, v, obs_minutes=obs,
                        )
                    st.session_state["bx_quick_ver"] = quick_ver + 1
                    st.toast(f"Saved {len(student_behaviors)} behavior(s) for {day_iso}.")
                    st.rerun()
            with ca:
                if st.button(
                    "Clear all for this date",
                    key=f"bxq_clear_all_{day_iso}",
                    width="stretch",
                ):
                    for b in student_behaviors:
                        delete_behavior_record(b["id"], day_iso)
                    st.session_state["bx_quick_ver"] = quick_ver + 1
                    st.toast(f"Cleared {len(student_behaviors)} behavior(s) for {day_iso}.")
                    st.rerun()

        student_phases = phases_for_student(sid)
        behavior_name_lookup = {b["id"]: b["name"] for b in student_behaviors}
        with st.expander(f"📌 Phases ({len(student_phases)})"):
            st.caption(
                "Mark intervention starts, treatment package changes, or other "
                "events. A phase can apply to **one** behavior or **all** of "
                "them — it appears as a dashed vertical line on the chart(s)."
            )
            if student_phases:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "Date": _fmt_date(p["date"]),
                            "Label": p["label"],
                            "Applies to": (
                                behavior_name_lookup.get(
                                    p.get("behavior_id"), "(removed behavior)"
                                )
                                if p.get("behavior_id")
                                else "All behaviors"
                            ),
                            "Notes": p.get("notes", ""),
                        }
                        for p in student_phases
                    ]),
                    width="stretch", hide_index=True,
                )
                del_id = st.selectbox(
                    "Remove a phase",
                    options=[p["id"] for p in student_phases],
                    format_func=lambda i: next(
                        f"{p['date']} — {p['label']}"
                        for p in student_phases if p["id"] == i
                    ),
                    key=f"bx_phase_del_pick_{sid}",
                )
                if st.button(
                    "🗑️ Remove selected phase",
                    key=f"bx_phase_del_btn_{sid}",
                ):
                    delete_phase(del_id)
                    for b in student_behaviors:
                        st.session_state.pop(f"bx_pdf_{b['id']}", None)
                    st.toast("Phase removed.")
                    st.rerun()
                st.markdown("---")
            st.markdown("**Add a phase**")
            with st.form(
                f"bx_phase_add_{sid}", clear_on_submit=True, border=False,
            ):
                ph_date = st.date_input("Date", value=date.today())
                ph_label = st.text_input(
                    "Label", placeholder="e.g., Started DRA, BIP revision",
                )
                ph_notes = st.text_area("Notes (optional)", height=70)
                ph_all = st.checkbox(
                    "Apply across all behaviors of concern",
                    value=True,
                    key=f"bx_phase_all_{sid}",
                )
                ph_behavior = st.selectbox(
                    "Behavior (used only when the box above is unchecked)",
                    options=[b["id"] for b in student_behaviors],
                    format_func=lambda i: behavior_name_lookup.get(i, i),
                    key=f"bx_phase_behavior_{sid}",
                ) if student_behaviors else None
                if st.form_submit_button(
                    "Add phase", type="primary", width="stretch",
                ):
                    if not ph_label.strip():
                        st.error("Label is required.")
                    else:
                        scoped_bid = (
                            "" if ph_all or not ph_behavior else ph_behavior
                        )
                        add_phase(
                            sid, ph_date.isoformat(),
                            ph_label.strip(), ph_notes.strip(),
                            behavior_id=scoped_bid,
                        )
                        for b in student_behaviors:
                            st.session_state.pop(f"bx_pdf_{b['id']}", None)
                        scope_txt = (
                            "all behaviors" if scoped_bid == ""
                            else behavior_name_lookup.get(scoped_bid, "behavior")
                        )
                        st.toast(
                            f"Added phase '{ph_label.strip()}' — {scope_txt}."
                        )
                        st.rerun()
        st.divider()

    if student_behaviors:
        n_cols = 3
        cols = st.columns(n_cols)
        for i, b in enumerate(student_behaviors):
            b_records = sorted(
                [r for r in student_records if r["behavior_id"] == b["id"]],
                key=lambda r: r["date"],
            )
            mt = MEASUREMENT_TYPES.get(
                b.get("measurement", "frequency"), MEASUREMENT_TYPES["frequency"]
            )
            with cols[i % n_cols]:
                with st.container(border=True):
                    st.markdown('<div class="opcard"></div>', unsafe_allow_html=True)
                    st.markdown(f"### {b['name']}")
                    parts = [mt["label"]]
                    if b_records:
                        parts.append(
                            f"{len(b_records)} session"
                            f"{'s' if len(b_records) != 1 else ''}"
                        )
                        parts.append(
                            f"latest **{behavior_value_display(b, b_records[-1])}**"
                        )
                        parts.append(f"on {_fmt_date(b_records[-1]['date'])}")
                    else:
                        parts.append("no sessions yet")
                    st.caption(" · ".join(parts))
                    if st.button(
                        "Open", key=f"bxcard_{b['id']}",
                        type="primary", width="stretch",
                    ):
                        st.session_state["current_behavior_id"] = b["id"]
                        st.session_state["page"] = "Behavior Detail"
                        st.rerun()
    else:
        st.info("No behaviors defined for this student yet — add one below.")

    st.divider()
    with st.expander("➕ Add a behavior"):
        with st.form("bx_add_behavior", clear_on_submit=True, border=False):
            name = st.text_input("Name", placeholder="e.g., Aggression")
            measurement = st.selectbox(
                "Measurement dimension",
                options=list(MEASUREMENT_TYPES),
                format_func=lambda k: MEASUREMENT_TYPES[k]["label"],
                key="bx_add_measurement",
            )
            definition = st.text_area(
                "Operational definition (optional)",
                placeholder="What counts as an instance of this behavior?",
                height=80,
            )
            if st.form_submit_button("Add behavior", type="primary", width="stretch"):
                if not name.strip():
                    st.error("Name is required.")
                else:
                    behaviors.append({
                        "id": new_id(),
                        "student_id": sid,
                        "name": name.strip(),
                        "definition": definition.strip(),
                        "measurement": measurement,
                        "created_at": now_iso(),
                    })
                    save_behaviors(behaviors)
                    st.success(f"Added {name.strip()}.")
                    st.rerun()

    if student_behaviors:
        with st.expander("⚙️ Manage behaviors"):
            pick_id = st.selectbox(
                "Behavior to modify",
                options=[b["id"] for b in student_behaviors],
                format_func=lambda i: next(
                    b["name"] for b in student_behaviors if b["id"] == i
                ),
                key="bx_manage_pick",
            )
            picked = next(b for b in student_behaviors if b["id"] == pick_id)
            new_name = st.text_input(
                "Name", value=picked["name"], key=f"bx_manage_name_{pick_id}",
            )
            new_meas = st.selectbox(
                "Measurement dimension",
                options=list(MEASUREMENT_TYPES),
                index=list(MEASUREMENT_TYPES).index(
                    picked.get("measurement", "frequency")
                ),
                format_func=lambda k: MEASUREMENT_TYPES[k]["label"],
                key=f"bx_manage_meas_{pick_id}",
                help="Existing records keep their numeric values; charts re-interpret them under the new dimension.",
            )
            new_def = st.text_area(
                "Operational definition",
                value=picked.get("definition", ""),
                key=f"bx_manage_def_{pick_id}",
                height=80,
            )
            mc1, mc2 = st.columns([1, 1])
            with mc1:
                if st.button(
                    "Save changes",
                    key=f"bx_manage_save_{pick_id}",
                    type="primary",
                    width="stretch",
                ):
                    for b in behaviors:
                        if b["id"] == pick_id:
                            b["name"] = new_name.strip() or picked["name"]
                            b["measurement"] = new_meas
                            b["definition"] = new_def.strip()
                            break
                    save_behaviors(behaviors)
                    st.toast(f"Saved {new_name.strip() or picked['name']}.")
                    st.rerun()
            with mc2:
                del_pending_key = f"bx_manage_del_pending_{pick_id}"
                if not st.session_state.get(del_pending_key):
                    if st.button(
                        "Delete behavior",
                        key=f"bx_manage_del_{pick_id}",
                        width="stretch",
                    ):
                        st.session_state[del_pending_key] = True
                        st.rerun()
                else:
                    st.warning(
                        f"**Delete `{picked['name']}` and all its records?**"
                    )
                    yc, nc = st.columns(2)
                    with yc:
                        if st.button(
                            "Yes, delete",
                            key=f"bx_manage_del_yes_{pick_id}",
                            type="primary",
                            width="stretch",
                        ):
                            save_behaviors(
                                [b for b in behaviors if b["id"] != pick_id]
                            )
                            save_behavior_records(
                                [r for r in records if r["behavior_id"] != pick_id]
                            )
                            st.session_state.pop(del_pending_key, None)
                            st.toast(f"Deleted {picked['name']}.")
                            st.rerun()
                    with nc:
                        if st.button(
                            "Cancel",
                            key=f"bx_manage_del_no_{pick_id}",
                            width="stretch",
                        ):
                            st.session_state.pop(del_pending_key, None)
                            st.rerun()

    if student_behaviors and student_records:
        st.divider()
        st.subheader("All behaviors · overlay")
        st.caption(
            "Each behavior on its own line. Y-axis shows raw values — units "
            "may differ across behaviors (see legend)."
        )
        window_days, period, agg_custom = _behavior_graph_controls(
            "agg", data_dates=[r["date"] for r in student_records],
        )
        b_lookup = {b["id"]: b for b in student_behaviors}
        agg_rows = []
        for r in student_records:
            b = b_lookup.get(r["behavior_id"])
            if not b:
                continue
            mt = MEASUREMENT_TYPES.get(
                b["measurement"], MEASUREMENT_TYPES["frequency"]
            )
            agg_rows.append({
                "Date": pd.to_datetime(r["date"]),
                "Value": _record_display_value(b, r),
                "Behavior": f"{b['name']} ({mt['unit']})",
                "measurement": b["measurement"],
            })
        df_agg = _apply_time_filter(
            pd.DataFrame(agg_rows), window_days, agg_custom,
        )
        if df_agg.empty:
            st.info("No records in the selected time window.")
            return
        if period != "Per session":
            parts = []
            for (beh, meas), grp in df_agg.groupby(["Behavior", "measurement"]):
                gg = _aggregate_period(grp[["Date", "Value"]], meas, period)
                gg["Behavior"] = beh
                parts.append(gg)
            df_agg = pd.concat(parts, ignore_index=True)
        df_agg = df_agg.sort_values("Date")
        if period == "Per session":
            fig = px.line(df_agg, x="Date", y="Value", color="Behavior", markers=True)
            fig.update_traces(
                mode="lines+markers+text",
                marker=dict(size=8, line=dict(width=1.5, color="white")),
                texttemplate="%{y:.0f}", textposition="top center",
                textfont=dict(size=10),
                hovertemplate="<b>%{fullData.name}</b><br>"
                "%{x|%b %-d, %Y}: %{y:.0f}<extra></extra>",
            )
        else:
            fig = px.bar(df_agg, x="Date", y="Value", color="Behavior")
            fig.update_layout(barmode="group")
            fig.update_traces(
                marker_line_width=0,
                texttemplate="%{y:.0f}", textposition="outside",
                cliponaxis=False, textfont=dict(size=10),
                hovertemplate="<b>%{fullData.name}</b><br>"
                "%{x|%b %-d, %Y}: %{y:.0f}<extra></extra>",
            )
        fig.update_yaxes(
            title=None, rangemode="tozero",
            gridcolor="#f0eeec", zeroline=False,
        )
        _integer_yaxis(fig, df_agg["Value"])
        fig.update_xaxes(
            title=None, gridcolor="#f0eeec", zeroline=False,
            showline=True, linecolor="#d6d3d1", linewidth=1,
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=340,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hoverlabel=dict(bgcolor="white", bordercolor="#e7e5e4"),
            font=dict(family="-apple-system, BlinkMacSystemFont, Inter, sans-serif",
                      color="#1c1917"),
        )
        st.plotly_chart(fig, width="stretch", key="bx_agg_chart")

    # ── Problem Behavior Summary (EFL) ──────────────────────────────────────
    s = next((x for x in students if x["id"] == sid), {})
    _efl_pb_summary_section(sid, s)


def page_behavior_detail():
    students = load_students()
    if not students:
        st.header("Behavior")
        st.info("Add a student first.")
        return

    sid = current_sid(students)
    behaviors = load_behaviors()
    records = load_behavior_records()
    bid = st.session_state.get("current_behavior_id")
    b = next(
        (x for x in behaviors if x["id"] == bid and x["student_id"] == sid),
        None,
    )

    if not b:
        st.header("Behavior")
        st.info("Pick a behavior from Behaviors of Concern.")
        if st.button("← Back", key="bx_detail_back_empty"):
            st.session_state["page"] = "Behaviors of Concern"
            st.rerun()
        return

    mt = MEASUREMENT_TYPES.get(b["measurement"], MEASUREMENT_TYPES["frequency"])

    back_col, title_col = st.columns([1, 5])
    with back_col:
        if st.button("← Back", key="bx_detail_back", width="stretch"):
            st.session_state["page"] = "Behaviors of Concern"
            st.rerun()
    with title_col:
        st.header(b["name"])

    detail_parts = [mt["label"]]
    if b.get("definition"):
        detail_parts.append(b["definition"])
    st.caption(" · ".join(detail_parts))

    with st.expander("⚙️ PDF report options", expanded=False):
        st.caption("Choose which graphs to include in the report.")
        gc1, gc2 = st.columns(2)
        gc1.checkbox(
            "Line graph (all sessions)", value=True,
            key=f"bx_pdf_line_{b['id']}",
        )
        gc2.checkbox(
            "Standard Celeration Chart", value=True,
            key=f"bx_pdf_scc_{b['id']}",
        )
        st.caption("Aggregated bar graphs:")
        bc1, bc2, bc3, bc4 = st.columns(4)
        bc1.checkbox("Daily", value=False, key=f"bx_pdf_daily_{b['id']}")
        bc2.checkbox("Weekly", value=True, key=f"bx_pdf_weekly_{b['id']}")
        bc3.checkbox("Monthly", value=True, key=f"bx_pdf_monthly_{b['id']}")
        bc4.checkbox("Yearly", value=True, key=f"bx_pdf_yearly_{b['id']}")

    pdf_session_key = f"bx_pdf_{b['id']}"
    pdf_bytes = st.session_state.get(pdf_session_key)
    if pdf_bytes is None:
        btn_col, _ = st.columns([1, 3])
        with btn_col:
            if st.button(
                "📄 Generate behavior report (PDF)",
                key=f"bx_detail_pdf_gen_{b['id']}",
                width="stretch",
            ):
                with st.spinner("Generating PDF — this can take a few seconds…"):
                    st.session_state[pdf_session_key] = build_behavior_pdf(
                        b, sid, students, records,
                    )
                st.rerun()
    else:
        dl_col, regen_col = st.columns([3, 1])
        with dl_col:
            st.download_button(
                "📄 Download behavior report (PDF)",
                data=pdf_bytes,
                file_name=(
                    f"{b['name'].replace(' ', '_')}_"
                    f"{student_name(students, sid).replace(' ', '_')}_"
                    f"{date.today().isoformat()}.pdf"
                ),
                mime="application/pdf",
                key=f"bx_detail_pdf_{b['id']}",
                width="stretch",
            )
        with regen_col:
            if st.button(
                "Regenerate",
                key=f"bx_detail_pdf_regen_{b['id']}",
                width="stretch",
                help="Rebuild the PDF after adding or editing data.",
            ):
                st.session_state.pop(pdf_session_key, None)
                st.rerun()

    # ── Interventions ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🧩 Interventions")
    attached = b.get("interventions", [])
    if attached:
        for iv in sorted(
            attached, key=lambda x: x.get("start_date", ""), reverse=True,
        ):
            ic = st.columns([6, 3, 1])
            note_txt = f" — {iv['notes']}" if iv.get("notes") else ""
            ic[0].markdown(
                f"**{iv['name']}**  \n_{iv.get('category', '')}_{note_txt}"
            )
            phase_tag = " · 📌 phase line" if iv.get("phase_id") else ""
            ic[1].caption(
                f"Started {_fmt_date(iv.get('start_date', ''))}{phase_tag}"
            )
            if ic[2].button(
                "✕", key=f"iv_detach_{b['id']}_{iv['id']}",
                help="Remove this intervention (and its phase line, if any).",
            ):
                detach_intervention(b["id"], iv["id"])
                st.toast("Removed intervention.")
                st.rerun()
    else:
        st.caption("No interventions attached to this behavior yet.")

    with st.expander("➕ Attach an intervention", expanded=not attached):
        ivbank = load_intervention_bank()
        if not ivbank:
            st.caption(
                "The Intervention Bank is empty — add some on the "
                "**Intervention Bank** page."
            )
        else:
            cats = sorted({x["category"] for x in ivbank})
            ac1, ac2 = st.columns(2)
            with ac1:
                pick_cat = st.selectbox(
                    "Category", cats, key=f"iv_att_cat_{b['id']}",
                )
            with ac2:
                cat_items = sorted(
                    [x for x in ivbank if x["category"] == pick_cat],
                    key=lambda x: x["name"].lower(),
                )
                pick_name = st.selectbox(
                    "Intervention", [x["name"] for x in cat_items],
                    key=f"iv_att_name_{b['id']}",
                )
            chosen = next(
                (x for x in cat_items if x["name"] == pick_name), None
            )
            d1, d2 = st.columns(2)
            with d1:
                start = st.date_input(
                    "Start date", value=date.today(),
                    key=f"iv_att_date_{b['id']}",
                )
            with d2:
                make_phase = st.checkbox(
                    "Mark a phase line on the graph at the start date",
                    value=True, key=f"iv_att_phase_{b['id']}",
                )
            notes = st.text_input(
                "Notes (optional)", key=f"iv_att_notes_{b['id']}",
            )
            if st.button(
                "Attach intervention", type="primary",
                disabled=chosen is None, key=f"iv_att_btn_{b['id']}",
            ):
                attach_intervention(
                    b["id"], sid, chosen, start.isoformat(), notes, make_phase,
                )
                st.toast(f"Attached: {chosen['name']}")
                st.rerun()

    edit_key = f"bx_detail_editing_{b['id']}"
    is_editing = st.session_state.get(edit_key, False)

    if is_editing:
        with st.container(border=True):
            st.markdown("**✎ Edit behavior**")
            new_name = st.text_input(
                "Name", value=b["name"], key=f"bx_detail_name_{b['id']}",
            )
            new_meas = st.selectbox(
                "Measurement dimension",
                options=list(MEASUREMENT_TYPES),
                index=list(MEASUREMENT_TYPES).index(b.get("measurement", "frequency")),
                format_func=lambda k: MEASUREMENT_TYPES[k]["label"],
                key=f"bx_detail_meas_{b['id']}",
                help="Existing records keep their numeric values; charts re-interpret them under the new dimension.",
            )
            new_def = st.text_area(
                "Operational definition",
                value=b.get("definition", ""),
                key=f"bx_detail_def_{b['id']}",
                height=80,
            )
            sc, cc, dc = st.columns([1, 1, 1])
            with sc:
                if st.button(
                    "Save changes",
                    key=f"bx_detail_save_{b['id']}",
                    type="primary",
                    width="stretch",
                ):
                    for x in behaviors:
                        if x["id"] == b["id"]:
                            x["name"] = new_name.strip() or b["name"]
                            x["measurement"] = new_meas
                            x["definition"] = new_def.strip()
                            break
                    save_behaviors(behaviors)
                    st.session_state.pop(edit_key, None)
                    st.toast("Saved.")
                    st.rerun()
            with cc:
                if st.button(
                    "Cancel",
                    key=f"bx_detail_cancel_{b['id']}",
                    width="stretch",
                ):
                    st.session_state.pop(edit_key, None)
                    st.rerun()
            with dc:
                del_pending_key = f"bx_detail_del_pending_{b['id']}"
                if not st.session_state.get(del_pending_key):
                    if st.button(
                        "Delete behavior",
                        key=f"bx_detail_del_{b['id']}",
                        width="stretch",
                    ):
                        st.session_state[del_pending_key] = True
                        st.rerun()
                else:
                    st.warning(
                        f"**Delete `{b['name']}` and all its records?**"
                    )
                    yc, nc = st.columns(2)
                    with yc:
                        if st.button(
                            "Yes, delete",
                            key=f"bx_detail_del_yes_{b['id']}",
                            type="primary",
                            width="stretch",
                        ):
                            save_behaviors(
                                [x for x in behaviors if x["id"] != b["id"]]
                            )
                            save_behavior_records(
                                [r for r in records if r["behavior_id"] != b["id"]]
                            )
                            st.session_state.pop(del_pending_key, None)
                            st.session_state.pop(edit_key, None)
                            st.session_state["page"] = "Behaviors of Concern"
                            st.toast(f"Deleted {b['name']}.")
                            st.rerun()
                    with nc:
                        if st.button(
                            "Cancel",
                            key=f"bx_detail_del_no_{b['id']}",
                            width="stretch",
                        ):
                            st.session_state.pop(del_pending_key, None)
                            st.rerun()
    else:
        with st.container(border=True):
            head = st.columns([5, 1])
            with head[0]:
                st.markdown("**Log session data**")
            with head[1]:
                if st.button(
                    "✎ Edit",
                    key=f"bx_detail_editbtn_{b['id']}",
                    width="stretch",
                ):
                    st.session_state[edit_key] = True
                    st.rerun()
            date_key = f"bx_detail_date_{b['id']}"
            pending_date_key = f"_bx_detail_pending_date_{b['id']}"
            if pending_date_key in st.session_state:
                st.session_state[date_key] = date.fromisoformat(
                    st.session_state.pop(pending_date_key)
                )
            entry_day = st.date_input(
                "Date", value=date.today(), key=date_key,
            )
            day_iso = entry_day.isoformat()
            existing = next(
                (r for r in records
                 if r["behavior_id"] == b["id"] and r["date"] == day_iso),
                None,
            )
            if entry_day != date.today():
                st.info(
                    f"✎ Editing prior session — {_fmt_date(day_iso)}",
                    icon="✎",
                )
            if existing:
                st.caption(
                    f"Logged for {_fmt_date(day_iso)}: "
                    f"**{behavior_value_display(b, existing)}**"
                )
            value, obs_minutes = _behavior_input(
                b, existing, key_prefix=f"bx_detail_input_{b['id']}_{day_iso}",
            )
            notes = st.text_input(
                "Notes (optional)",
                value=existing.get("notes", "") if existing else "",
                key=f"bx_detail_notes_{b['id']}_{day_iso}",
            )
            sc, cc = st.columns([1, 1])
            with sc:
                if st.button(
                    "Save",
                    key=f"bx_detail_record_save_{b['id']}_{day_iso}",
                    type="primary",
                    width="stretch",
                ):
                    upsert_behavior_record(
                        b["id"], sid, day_iso, value,
                        obs_minutes=obs_minutes, notes=notes,
                    )
                    st.toast(f"Saved {b['name']} for {day_iso}.")
                    st.rerun()
            with cc:
                if existing and st.button(
                    "Clear this date",
                    key=f"bx_detail_record_clear_{b['id']}_{day_iso}",
                    width="stretch",
                ):
                    delete_behavior_record(b["id"], day_iso)
                    st.toast(f"Cleared {b['name']} for {day_iso}.")
                    st.rerun()

    b_phases = phases_for_behavior(sid, b["id"])

    b_rows = sorted(
        [r for r in records if r["behavior_id"] == b["id"]],
        key=lambda r: r["date"],
    )
    if b_rows:
        st.divider()
        st.subheader("How is it going?")
        analysis = behavior_analysis(b, records, b_phases)
        if analysis and analysis["overall"]:
            o = analysis["overall"]
            summary = _behavior_plain_summary(b, mt, o)
            st.markdown(summary)
            kc1, kc2, kc3 = st.columns(3)
            kc1.metric(
                "On a typical day",
                _whole_avg_card(o["mean"], mt["unit"]),
                f"Range: {o['min']:g}–{o['max']:g}",
                delta_color="off",
            )
            kc2.metric(
                "Trend",
                _direction_label(o["trend_desc"]),
                _direction_subtitle(o, mt),
                delta_color="off",
            )
            kc3.metric(
                "Consistency",
                _variability_label(o["variability_desc"]),
                _variability_subtitle(o),
                delta_color="off",
            )
            if analysis["phases"]:
                st.markdown("**Across program phases**")
                phase_rows = [
                    {
                        "Phase": p["label"],
                        "Time period": f"{p['start_date']} → {p['end_date']}",
                        "Sessions": p["n"],
                        f"Typical day ({_qty_noun(mt['unit'], False)})": _whole_avg_short(p["mean"]),
                        "Trend": _direction_label(p["trend_desc"]),
                        "Consistency": _variability_label(p["variability_desc"]),
                    }
                    for p in analysis["phases"]
                ]
                st.dataframe(
                    pd.DataFrame(phase_rows), width="stretch", hide_index=True,
                )
            with st.expander("📊 Technical details (for clinicians)"):
                st.caption(
                    "Statistical summary. Mean ± SD is the level; slope is a "
                    "least-squares trend through the points; CV (coefficient "
                    "of variation) is SD / mean — a normalized variability score."
                )
                st.markdown(
                    f"**Overall** — N = {o['n']} · Mean ± SD = "
                    f"{o['mean']:.3f} ± {o['sd']:.3f} {mt['unit']} · "
                    f"Range = {o['min']:g}–{o['max']:g} {mt['unit']} · "
                    f"Slope = {o['slope_per_day']:+.4f}/day "
                    f"({o['slope_per_week']:+.3f}/week) · CV = {o['cv']:.3f}"
                )
                if analysis["phases"]:
                    tech_rows = [
                        {
                            "Phase": p["label"],
                            "N": p["n"],
                            "Mean": f"{p['mean']:.3f}",
                            "SD": f"{p['sd']:.3f}",
                            "Min": f"{p['min']:g}",
                            "Max": f"{p['max']:g}",
                            "Slope/day": f"{p['slope_per_day']:+.4f}",
                            "Slope/wk": f"{p['slope_per_week']:+.3f}",
                            "CV": f"{p['cv']:.3f}",
                        }
                        for p in analysis["phases"]
                    ]
                    st.dataframe(
                        pd.DataFrame(tech_rows), width="stretch", hide_index=True,
                    )

        st.divider()
        st.subheader("Session log")
        sorted_b_rows = sorted(b_rows, key=lambda r: r["date"], reverse=True)
        log_rows = []
        hc = st.columns([2, 3, 5, 1])
        hc[0].markdown("**Date**")
        hc[1].markdown("**Value**")
        hc[2].markdown("**Notes**")
        hc[3].markdown("**Edit**")
        for r in sorted_b_rows:
            value_text = behavior_value_display(b, r)
            if b["measurement"] == "rate":
                value_text += (
                    f"  ·  {int(r['value'])} in {r.get('obs_minutes', 0):g} min"
                )
            notes_text = r.get("notes", "") or ""
            log_rows.append({
                "Date": _fmt_date(r["date"]),
                "Value": value_text,
                "Notes": notes_text,
            })
            rc = st.columns([2, 3, 5, 1])
            rc[0].markdown(_fmt_date(r["date"]))
            rc[1].markdown(value_text)
            rc[2].markdown(notes_text or "_—_")
            if rc[3].button(
                "✎",
                key=f"bx_detail_log_edit_{b['id']}_{r['date']}",
                help=f"Edit this session ({_fmt_date(r['date'])})",
            ):
                st.session_state[f"_bx_detail_pending_date_{b['id']}"] = r["date"]
                st.rerun()
        df_log = pd.DataFrame(log_rows)
        st.download_button(
            "📄 Download session log CSV",
            data=df_log.to_csv(index=False).encode("utf-8"),
            file_name=f"{b['name'].replace(' ', '_')}_log_{date.today().isoformat()}.csv",
            mime="text/csv",
            key=f"bx_detail_log_csv_{b['id']}",
        )

        st.divider()
        _cur_period = st.session_state.get(
            f"bx_period_detail_{b['id']}", "Per session",
        )
        st.subheader("Bar graph" if _cur_period != "Per session" else "Line graph")
        bx_window_days, bx_period, bx_custom = _behavior_graph_controls(
            f"detail_{b['id']}", data_dates=[r["date"] for r in b_rows],
        )
        ov1, ov2 = st.columns(2)
        show_trend = ov1.checkbox(
            "📈 Trend line (line of best fit)",
            key=f"bx_trend_{b['id']}",
        )
        show_level = ov2.checkbox(
            "➖ Level line (average)",
            key=f"bx_level_{b['id']}",
        )
        df_b_all = pd.DataFrame([{
            "Date": pd.to_datetime(r["date"]),
            "Value": _record_display_value(b, r),
        } for r in b_rows]).sort_values("Date")
        df_b = _aggregate_period(
            _apply_time_filter(df_b_all, bx_window_days, bx_custom),
            b["measurement"], bx_period,
        )
        if df_b.empty:
            st.info("No sessions in the selected time window.")
        else:
            if bx_period == "Per session":
                fig = px.line(df_b, x="Date", y="Value", markers=True)
                fig.update_traces(
                    mode="lines+markers+text",
                    line=dict(color="#ea580c"),
                    marker=dict(size=9, color="#ea580c",
                                line=dict(width=1.5, color="white")),
                    text=df_b["Value"], texttemplate="%{y:.0f}",
                    textposition="top center",
                    textfont=dict(size=11, color="#1c1917"),
                    hovertemplate="%{x|%b %-d, %Y}: %{y:.0f}<extra></extra>",
                )
            else:
                fig = px.bar(df_b, x="Date", y="Value")
                fig.update_traces(
                    marker_color="#ea580c", marker_line_width=0,
                    text=df_b["Value"], texttemplate="%{y:.0f}",
                    textposition="outside", cliponaxis=False,
                    textfont=dict(size=11, color="#1c1917"),
                    hovertemplate="%{x|%b %-d, %Y}: %{y:.0f}<extra></extra>",
                )
            fig.update_yaxes(
                title=_graph_y_title(mt, b["measurement"], bx_period),
                rangemode="tozero",
                gridcolor="#f0eeec", zeroline=False,
            )
            _integer_yaxis(fig, df_b["Value"])
            fig.update_xaxes(
                title=None, gridcolor="#f0eeec", zeroline=False,
                showline=True, linecolor="#d6d3d1", linewidth=1,
            )
            _apply_period_xticks(fig, bx_period)
            _line_xr = _xrange_with_phases(df_b["Date"], b_phases)
            if _line_xr:
                fig.update_xaxes(range=_line_xr)
            _apply_phase_lines(fig, b_phases)
            overlay_notes: list[str] = []
            if show_level:
                level = float(df_b["Value"].mean())
                fig.add_hline(
                    y=level,
                    line=dict(color="#0ea5e9", width=2, dash="dot"),
                    annotation_text=f"Level: {round(level)}",
                    annotation_position="top left",
                    annotation_font_color="#0369a1",
                )
                overlay_notes.append(
                    f"**Level** (blue dotted) = average of about "
                    f"**{round(level)} {_qty_noun(mt['unit'], round(level) == 1)}**"
                )
            if show_trend:
                fit = _best_fit_line(df_b["Date"], df_b["Value"])
                if fit:
                    x0, x1, y0, y1, slope = fit
                    fig.add_scatter(
                        x=[x0, x1], y=[y0, y1], mode="lines",
                        line=dict(color="#1c1917", width=2, dash="dash"),
                        name="Trend", hoverinfo="skip", showlegend=False,
                    )
                    direction = (
                        "downward" if slope < 0
                        else "upward" if slope > 0 else "flat"
                    )
                    overlay_notes.append(
                        f"**Trend** (dashed) = line of best fit, sloping "
                        f"**{direction}**"
                    )
                else:
                    overlay_notes.append(
                        "**Trend** needs at least 2 sessions on different dates"
                    )
            fig.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=300,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                hoverlabel=dict(bgcolor="white", bordercolor="#e7e5e4"),
                font=dict(family="-apple-system, BlinkMacSystemFont, Inter, sans-serif",
                          color="#1c1917"),
            )
            st.plotly_chart(fig, width="stretch", key=f"bx_detail_chart_{b['id']}")
            latest_rec = max(b_rows, key=lambda r: r["date"])
            agg_note = (
                "" if bx_period == "Per session"
                else f", aggregated {bx_period.lower()} ({'total' if b['measurement'] in _GRAPH_SUM_MEASUREMENTS else 'average'})"
            )
            st.caption(
                f"Showing {len(df_b)} point(s){agg_note}. Most recent session: "
                f"**{behavior_value_display(b, latest_rec)}** on "
                f"{_fmt_date(latest_rec['date'])}."
            )
            if overlay_notes:
                st.caption(" · ".join(overlay_notes) + ".")

        with st.expander("📐 Compare time frames (all at once)", expanded=False):
            st.caption(
                "The same line graph at every time window, side by side. Uses "
                "your current **aggregation** and **trend/level** toggles above."
            )
            _windows = list(GRAPH_WINDOW_OPTIONS.items())
            _ncol = 2
            for _start in range(0, len(_windows), _ncol):
                _row = _windows[_start:_start + _ncol]
                _cols = st.columns(_ncol)
                for _col, (_wlabel, _wdays) in zip(_cols, _row):
                    with _col:
                        st.markdown(f"**{_wlabel}**")
                        dfw = _aggregate_period(
                            _filter_window(df_b_all, _wdays),
                            b["measurement"], bx_period,
                        )
                        if dfw.empty:
                            st.caption("_No sessions in this window._")
                            continue
                        if bx_period == "Per session":
                            mfig = px.line(dfw, x="Date", y="Value", markers=True)
                            mfig.update_traces(
                                line=dict(color="#ea580c"),
                                marker=dict(size=6, color="#ea580c",
                                            line=dict(width=1, color="white")),
                                hovertemplate="%{x|%b %-d, %Y}: "
                                "%{y:.0f}<extra></extra>",
                            )
                        else:
                            mfig = px.bar(dfw, x="Date", y="Value")
                            mfig.update_traces(
                                marker_color="#ea580c", marker_line_width=0,
                                hovertemplate="%{x|%b %-d, %Y}: "
                                "%{y:.0f}<extra></extra>",
                            )
                        mfig.update_yaxes(
                            title=None, rangemode="tozero",
                            gridcolor="#f0eeec", zeroline=False,
                            tickfont=dict(size=9),
                        )
                        _integer_yaxis(mfig, dfw["Value"])
                        mfig.update_xaxes(
                            title=None, gridcolor="#f0eeec", zeroline=False,
                            tickfont=dict(size=9),
                            showline=True, linecolor="#d6d3d1", linewidth=1,
                        )
                        _apply_period_xticks(mfig, bx_period)
                        if show_level:
                            _lv = float(dfw["Value"].mean())
                            mfig.add_hline(
                                y=_lv,
                                line=dict(color="#0ea5e9", width=1.5, dash="dot"),
                            )
                        if show_trend:
                            _ft = _best_fit_line(dfw["Date"], dfw["Value"])
                            if _ft:
                                _x0, _x1, _y0, _y1, _s = _ft
                                mfig.add_scatter(
                                    x=[_x0, _x1], y=[_y0, _y1], mode="lines",
                                    line=dict(color="#1c1917", width=1.5,
                                              dash="dash"),
                                    hoverinfo="skip", showlegend=False,
                                )
                        mfig.update_layout(
                            margin=dict(l=6, r=6, t=6, b=6),
                            height=200,
                            plot_bgcolor="rgba(0,0,0,0)",
                            paper_bgcolor="rgba(0,0,0,0)",
                            showlegend=False,
                            hoverlabel=dict(bgcolor="white", bordercolor="#e7e5e4"),
                            font=dict(
                                family="-apple-system, BlinkMacSystemFont, "
                                "Inter, sans-serif",
                                color="#1c1917",
                            ),
                        )
                        st.plotly_chart(
                            mfig, width="stretch",
                            key=f"bx_multi_{b['id']}_{_wlabel}",
                        )
                        st.caption(f"{len(dfw)} point(s)")

        # ── Standard Celeration Chart ────────────────────────────────────────
        st.subheader("Standard Celeration Chart")
        st.caption(
            "Respects the time window above; per-session points only — the SCC "
            "is never aggregated."
        )
        scc_cutoff = (
            pd.Timestamp(date.today()) - pd.Timedelta(days=bx_window_days)
            if bx_window_days is not None else None
        )
        scc_lo = pd.Timestamp(bx_custom[0]) if bx_custom else None
        scc_hi = pd.Timestamp(bx_custom[1]) if bx_custom else None
        scc_rows = []
        for r in b_rows:
            r_date = pd.to_datetime(r["date"])
            if bx_custom is not None:
                if r_date < scc_lo or r_date > scc_hi:
                    continue
            elif scc_cutoff is not None and r_date < scc_cutoff:
                continue
            raw = _record_display_value(b, r)
            # Convert to count-per-minute when the source is rate (per-hour).
            value_per_min = raw / 60.0 if b["measurement"] == "rate" else raw
            scc_rows.append({
                "Date": r_date,
                "Value": max(float(value_per_min), 0.001),  # log floor
            })
        if not scc_rows:
            st.info("No sessions in the selected time window.")
            return
        df_scc = pd.DataFrame(scc_rows).sort_values("Date")
        scc_y_label = (
            "Count per minute"
            if b["measurement"] in ("rate", "frequency")
            else f"{mt['axis']} (log)"
        )
        scc_fig = px.line(df_scc, x="Date", y="Value", markers=True)
        scc_fig.update_traces(
            line=dict(color="#1c1917", width=1.5),
            marker=dict(size=7, color="#1c1917",
                        line=dict(width=1.2, color="white")),
            hovertemplate="%{x|%b %-d, %Y}: %{y:.3f}<extra></extra>",
        )
        scc_fig.update_yaxes(
            type="log",
            range=[-3, 3],
            tickvals=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
            ticktext=[".001", ".01", ".1", "1", "10", "100", "1000"],
            gridcolor="#d6cfb8",
            zeroline=False,
            minor=dict(
                tickvals=[
                    n * (10 ** e)
                    for e in range(-3, 3)
                    for n in range(2, 10)
                ],
                gridcolor="#ece5d2",
                showgrid=True,
                ticks="",
            ),
            title=scc_y_label,
        )
        _scc_xr = _xrange_with_phases(
            df_scc["Date"], b_phases, pad_days=2, min_span_days=28,
        )
        scc_fig.update_xaxes(
            range=_scc_xr,
            gridcolor="#d6cfb8",
            zeroline=False,
            showgrid=True,
            dtick=7 * 86400000,  # 1-week grid (ms)
            tickformat="%b %-d",
            title=None,
            minor=dict(
                dtick=86400000,
                gridcolor="#ece5d2",
                showgrid=True,
                ticks="",
            ),
        )
        _apply_phase_lines(scc_fig, b_phases)
        scc_fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            height=420,
            plot_bgcolor="#fffbef",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            hoverlabel=dict(bgcolor="white", bordercolor="#e7e5e4"),
            font=dict(family="-apple-system, BlinkMacSystemFont, Inter, sans-serif",
                      color="#1c1917"),
        )
        st.plotly_chart(scc_fig, width="stretch", key=f"bx_scc_{b['id']}")
        st.caption(
            "Y-axis is logarithmic (factor-of-10 increments). Rate behaviors are "
            "shown as **count per minute** (raw value ÷ 60); other measurements "
            "are plotted on the same log scale. Values of 0 are displayed at the "
            "0.001 floor since log scales cannot show zero."
        )


def page_target_bank():
    students = load_students()
    bank = load_target_bank()
    sid = current_sid(students) if students else None

    st.header("Target Bank")
    st.caption(
        "Reusable target templates, shared across students. Save targets from "
        "any student, then import them into another student here."
    )

    bank_add_msg = st.session_state.pop("_bank_add_msg", None)
    if bank_add_msg:
        st.success(bank_add_msg)

    # ── Add to current student ───────────────────────────────────────────────
    if not bank:
        st.info(
            "The bank is empty. On a student's operant page, check targets and "
            "press **💾 Save N to bank** to populate it."
        )
    else:
        all_ops = sorted({b.get("domain", "") for b in bank if b.get("domain")})
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            op_filter = st.multiselect(
                "Operant", options=all_ops, default=all_ops, key="bank_op_filter",
            )
        with f2:
            list_options = sorted({
                (b.get("skill_list") or "").strip()
                for b in bank
                if b.get("domain") in op_filter and (b.get("skill_list") or "").strip()
            })
            list_filter = st.multiselect(
                "Skill list", options=list_options, default=list_options,
                key="bank_list_filter",
            )
        with f3:
            search = st.text_input(
                "Search description", key="bank_search",
                placeholder="e.g., Touch, dog, fruit punch…",
            )

        filtered = []
        list_filter_set = set(list_filter)
        s_lower = search.strip().lower()
        for b in bank:
            if b.get("domain") not in op_filter:
                continue
            sl = (b.get("skill_list") or "").strip()
            if list_options and sl not in list_filter_set:
                # Only enforce when there are named lists in scope; allow no-list entries
                if sl != "":
                    continue
            if s_lower and s_lower not in b["description"].lower():
                continue
            filtered.append(b)
        filtered = sorted(filtered, key=lambda b: (
            b.get("domain", ""), (b.get("skill_list") or ""), b["description"].lower(),
        ))

        st.caption(f"**{len(filtered)}** of **{len(bank)}** entries shown.")
        if filtered:
            selected_set: set[str] = set(
                st.session_state.get("bank_selected_ids", [])
            )
            sel_ver = st.session_state.get("bank_sel_ver", 0)
            filtered_ids = [b["id"] for b in filtered]
            n_shown_selected = sum(1 for fid in filtered_ids if fid in selected_set)

            sa1, sa2, sa3 = st.columns([1, 1, 4])
            with sa1:
                if st.button(
                    "✓ Select all shown",
                    key="bank_sel_all_btn",
                    width="stretch",
                ):
                    selected_set.update(filtered_ids)
                    st.session_state["bank_selected_ids"] = list(selected_set)
                    st.session_state["bank_sel_ver"] = sel_ver + 1
                    st.rerun()
            with sa2:
                if st.button(
                    "Clear selection",
                    key="bank_sel_clear_btn",
                    width="stretch",
                ):
                    st.session_state["bank_selected_ids"] = []
                    st.session_state["bank_sel_ver"] = sel_ver + 1
                    st.rerun()
            with sa3:
                st.caption(
                    f"**{n_shown_selected}** of {len(filtered_ids)} shown checked · "
                    f"{len(selected_set)} selected in total."
                )

            df = pd.DataFrame([{
                "Select": b["id"] in selected_set,
                "Operant": b.get("domain", ""),
                "List": b.get("skill_list", "") or "—",
                "Target": b["description"],
                "Cons. Y": int(b.get("mastery_n", DEFAULT_MASTERY_N)),
            } for b in filtered])
            edited = st.data_editor(
                df,
                width="stretch",
                hide_index=True,
                key=f"bank_editor_{sel_ver}",
                column_config={
                    "Select": st.column_config.CheckboxColumn("✓", default=False),
                    "Operant": st.column_config.TextColumn(disabled=True),
                    "List": st.column_config.TextColumn(disabled=True),
                    "Target": st.column_config.TextColumn(disabled=True),
                    "Cons. Y": st.column_config.NumberColumn(disabled=True),
                },
            )
            # Sync the editor's current state back into the session-state set so
            # checkbox edits + Select-all stay coherent across reruns and filter
            # changes.
            edited_records = edited.to_dict("records")
            updated_set = set(selected_set)
            for i, row in enumerate(edited_records):
                fid = filtered[i]["id"]
                if row.get("Select"):
                    updated_set.add(fid)
                else:
                    updated_set.discard(fid)
            if updated_set != selected_set:
                st.session_state["bank_selected_ids"] = list(updated_set)
                selected_set = updated_set

            picked_ids = [fid for fid in filtered_ids if fid in selected_set]
            if not students:
                st.caption("Add a student first to enable importing.")
            else:
                target_student_id = st.selectbox(
                    "Add to student",
                    options=[s["id"] for s in students],
                    index=[s["id"] for s in students].index(sid) if sid in [s["id"] for s in students] else 0,
                    format_func=lambda i: student_name(students, i),
                    key="bank_target_student",
                )
                act_add, act_del = st.columns(2)
                with act_add:
                    if st.button(
                        f"➕ Add {len(picked_ids)} to {student_name(students, target_student_id)}",
                        key="bank_add_btn",
                        type="primary",
                        disabled=not picked_ids,
                        width="stretch",
                    ):
                        n = import_bank_to_student(picked_ids, target_student_id)
                        sname = student_name(students, target_student_id)
                        n_label = "target" if n == 1 else "targets"
                        st.session_state["_bank_add_msg"] = (
                            f"✓ Added **{n}** {n_label} from the Target Bank "
                            f"to **{sname}**."
                        )
                        st.session_state["bank_selected_ids"] = []
                        st.toast(f"Added {n} {n_label} to {sname}.")
                        st.rerun()
                with act_del:
                    pending_bank_del = "bank_pending_delete"
                    if not st.session_state.get(pending_bank_del):
                        if st.button(
                            f"🗑️ Delete {len(picked_ids)} from bank",
                            key="bank_del_btn",
                            disabled=not picked_ids,
                            width="stretch",
                        ):
                            st.session_state[pending_bank_del] = picked_ids
                            st.rerun()
                    else:
                        ids_set = set(st.session_state[pending_bank_del])
                        st.warning(
                            f"**Remove {len(ids_set)} entries from the bank?** "
                            "Existing student copies of these targets are kept."
                        )
                        cy, cn = st.columns(2)
                        with cy:
                            if st.button(
                                "Yes, remove",
                                key="bank_del_yes",
                                type="primary", width="stretch",
                            ):
                                save_target_bank(
                                    [b for b in load_target_bank() if b["id"] not in ids_set]
                                )
                                st.session_state.pop(pending_bank_del, None)
                                st.toast(f"Removed {len(ids_set)} entries.")
                                st.rerun()
                        with cn:
                            if st.button(
                                "Cancel",
                                key="bank_del_no",
                                width="stretch",
                            ):
                                st.session_state.pop(pending_bank_del, None)
                                st.rerun()

    # ── Duplicate finder (within operant) ────────────────────────────────────
    if bank:
        st.divider()
        with st.expander("🔁 Find duplicates within an operant", expanded=False):
            st.caption(
                "Finds targets whose description appears more than once **within "
                "the same operant** (skill list ignored). The same word across "
                "different operants isn't flagged — only repeats inside one operant."
            )
            dup_groups: dict[tuple[str, str], list[dict]] = {}
            for b in bank:
                key = (b.get("domain", ""), b["description"].strip().lower())
                dup_groups.setdefault(key, []).append(b)
            dup_groups = {k: v for k, v in dup_groups.items() if len(v) > 1}
            dup_ops = sorted({op for (op, _desc) in dup_groups})

            if not dup_groups:
                st.success("No duplicates found within any operant. ✓")
            else:
                n_groups = len(dup_groups)
                n_redundant = sum(len(v) - 1 for v in dup_groups.values())
                st.caption(
                    f"**{n_groups}** duplicated description(s) across "
                    f"**{len(dup_ops)}** operant(s) · **{n_redundant}** redundant "
                    f"entry(ies) (extra copies beyond the first)."
                )
                scope = st.selectbox(
                    "Operant",
                    options=["All operants"] + dup_ops,
                    key="bank_dup_op_scope",
                )
                rows: list[dict] = []
                ordered_ids: list[str] = []
                for (op, _desc), entries in sorted(
                    dup_groups.items(), key=lambda kv: (kv[0][0], kv[0][1])
                ):
                    if scope != "All operants" and op != scope:
                        continue
                    ordered = sorted(
                        entries, key=lambda x: (x.get("skill_list") or "").lower()
                    )
                    for j, e in enumerate(ordered):
                        ordered_ids.append(e["id"])
                        rows.append({
                            "Select": False,
                            "Operant": op,
                            "Target": e["description"],
                            "List": e.get("skill_list", "") or "—",
                            "Cons. Y": int(e.get("mastery_n", DEFAULT_MASTERY_N)),
                            "Copy": f"{j + 1} of {len(ordered)}",
                        })

                if not rows:
                    st.caption("No duplicates in this operant.")
                else:
                    st.caption(
                        "Check the copies you want to remove. Within each group, "
                        "leave at least one unchecked to keep it."
                    )
                    dup_ver = st.session_state.get("bank_dup_ver", 0)
                    dup_edited = st.data_editor(
                        pd.DataFrame(rows),
                        width="stretch",
                        hide_index=True,
                        key=f"bank_dup_editor_{scope}_{dup_ver}",
                        column_config={
                            "Select": st.column_config.CheckboxColumn("✓", default=False),
                            "Operant": st.column_config.TextColumn(disabled=True),
                            "Target": st.column_config.TextColumn(disabled=True),
                            "List": st.column_config.TextColumn(disabled=True),
                            "Cons. Y": st.column_config.NumberColumn(disabled=True),
                            "Copy": st.column_config.TextColumn(disabled=True),
                        },
                    )
                    dup_selected_ids = [
                        ordered_ids[i]
                        for i, row in enumerate(dup_edited.to_dict("records"))
                        if row.get("Select")
                    ]
                    dup_pending = "bank_dup_pending_delete"
                    if not st.session_state.get(dup_pending):
                        if st.button(
                            f"🗑️ Remove {len(dup_selected_ids)} selected duplicate(s)",
                            key="bank_dup_del_btn",
                            disabled=not dup_selected_ids,
                            width="stretch",
                        ):
                            st.session_state[dup_pending] = dup_selected_ids
                            st.rerun()
                    else:
                        ids_set = set(st.session_state[dup_pending])
                        st.warning(
                            f"**Remove {len(ids_set)} duplicate entry(ies) from the "
                            "bank?** Student copies of these targets are kept."
                        )
                        dcy, dcn = st.columns(2)
                        with dcy:
                            if st.button(
                                "Yes, remove", key="bank_dup_del_yes",
                                type="primary", width="stretch",
                            ):
                                save_target_bank(
                                    [b for b in load_target_bank()
                                     if b["id"] not in ids_set]
                                )
                                st.session_state.pop(dup_pending, None)
                                st.session_state["bank_dup_ver"] = (
                                    st.session_state.get("bank_dup_ver", 0) + 1
                                )
                                st.toast(f"Removed {len(ids_set)} duplicate(s).")
                                st.rerun()
                        with dcn:
                            if st.button(
                                "Cancel", key="bank_dup_del_no", width="stretch",
                            ):
                                st.session_state.pop(dup_pending, None)
                                st.rerun()

    # ── Lists overview (drill-down) ──────────────────────────────────────────
    st.divider()
    with st.expander("📋 List overview", expanded=False):
        st.caption(
            "Drill down from operant to skill list to individual targets. "
            "Counts include students who already have a copy of each target."
        )

        all_targets = load_targets()
        all_students = load_students()
        student_lookup = {s["id"]: s["name"] for s in all_students}

        # Build operant → list → entries
        by_op: dict[str, dict[str, list[dict]]] = {}
        for entry in bank:
            op = entry.get("domain", "") or "—"
            list_name = (entry.get("skill_list") or "").strip() or "— No list —"
            by_op.setdefault(op, {}).setdefault(list_name, []).append(entry)

        # Build a "students per (op, list, description)" lookup for cross-reference
        students_for_target: dict[tuple[str, str, str], list[str]] = {}
        for t in all_targets:
            key = (
                t.get("domain", "") or "—",
                (t.get("skill_list") or "").strip() or "— No list —",
                t["description"].strip().lower(),
            )
            sname = student_lookup.get(t["student_id"], "")
            if sname:
                students_for_target.setdefault(key, []).append(sname)

        if not by_op:
            st.caption("Bank is empty — nothing to drill into yet.")
        else:
            op_keys = sorted(by_op.keys())
            op_tabs = st.tabs(op_keys)
            for tab, op in zip(op_tabs, op_keys):
                with tab:
                    lists = by_op[op]
                    n_total = sum(len(v) for v in lists.values())
                    n_named = sum(1 for k in lists if k != "— No list —")
                    st.caption(
                        f"**{n_named}** named list(s) · **{n_total}** entries in {op}."
                    )
                    ordered_lists = sorted(
                        lists.keys(),
                        key=lambda s: (s == "— No list —", s.lower()),
                    )
                    for list_name in ordered_lists:
                        entries = lists[list_name]
                        entry_count = len(entries)
                        with st.expander(
                            f"📂 {list_name} ({entry_count})",
                            expanded=False,
                        ):
                            ordered_entries = sorted(
                                entries, key=lambda e: e["description"].lower(),
                            )
                            rows = []
                            for e in ordered_entries:
                                key = (
                                    op,
                                    list_name,
                                    e["description"].strip().lower(),
                                )
                                used_by = students_for_target.get(key, [])
                                rows.append({
                                    "Target": e["description"],
                                    "Cons. Y": int(
                                        e.get("mastery_n", DEFAULT_MASTERY_N)
                                    ),
                                    "Used by students": (
                                        ", ".join(sorted(set(used_by)))
                                        if used_by else "—"
                                    ),
                                })
                            st.dataframe(
                                pd.DataFrame(rows),
                                width="stretch", hide_index=True,
                            )

    # ── Bulk upload to bank ──────────────────────────────────────────────────
    st.divider()
    with st.expander("📥 Bulk add to bank (paste a list or upload CSV)"):
        st.caption(
            "Paste a list of targets or upload a CSV. Each row becomes a bank "
            "entry. Lists are created automatically by virtue of containing "
            "entries. Use **Operant: target** or **Operant / List: target** "
            "to override the defaults per line."
        )
        bv = st.session_state.get("bank_bulk_ver", 0)
        bc1, bc2 = st.columns(2)
        with bc1:
            bulk_default_op = st.selectbox(
                "Default operant", DOMAINS, key=f"bank_bulk_op_{bv}",
            )
        bulk_existing_lists = sorted({
            (e.get("skill_list") or "").strip()
            for e in bank
            if e.get("domain") == bulk_default_op
            and (e.get("skill_list") or "").strip()
        })
        with bc2:
            if bulk_existing_lists:
                NONE_OPT = "— No list —"
                NEW_OPT = "+ New list..."
                opts = [NONE_OPT, *bulk_existing_lists, NEW_OPT]
                bulk_picked = st.selectbox(
                    "Default skill list",
                    options=opts,
                    key=f"bank_bulk_listpick_{bulk_default_op}_{bv}",
                )
                if bulk_picked == NEW_OPT:
                    bulk_default_list = st.text_input(
                        "New list name",
                        key=f"bank_bulk_listnew_{bulk_default_op}_{bv}",
                        placeholder="e.g., Tacts of Animals",
                    ).strip()
                elif bulk_picked == NONE_OPT:
                    bulk_default_list = ""
                else:
                    bulk_default_list = bulk_picked
            else:
                bulk_default_list = st.text_input(
                    "Default skill list (optional)",
                    key=f"bank_bulk_list_{bulk_default_op}_{bv}",
                    placeholder="Type a name to create a new list",
                ).strip()

        ptab, ctab = st.tabs(["📋 Paste", "📄 CSV"])
        bulk_rows: list[dict] = []
        with ptab:
            text = st.text_area(
                "Targets",
                height=180,
                key=f"bank_bulk_paste_{bv}",
                placeholder='SD "Touch eyes."\nTact: dog\nMand / Snacks: pretzels',
                label_visibility="collapsed",
            )
            if text.strip():
                bulk_rows = _parse_bulk_po_text(
                    text, bulk_default_op, bulk_default_list,
                )
        with ctab:
            st.caption(
                "CSV with at least a `description` column. Optional `operant` "
                "and `skill_list` columns override the defaults per row."
            )
            up = st.file_uploader(
                "CSV file", type=["csv"], key=f"bank_bulk_csv_{bv}",
            )
            if up is not None:
                try:
                    df_in = pd.read_csv(up)
                    df_in.columns = [c.strip().lower() for c in df_in.columns]
                    if "description" not in df_in.columns:
                        st.error("CSV must include a `description` column.")
                    else:
                        for _, r in df_in.iterrows():
                            d = str(r.get("description", "")).strip()
                            if not d:
                                continue
                            opv = str(r.get("operant", "")).strip() or bulk_default_op
                            if opv not in DOMAINS:
                                opv = bulk_default_op
                            sl = str(r.get("skill_list", "")).strip() or bulk_default_list
                            bulk_rows.append({
                                "Description": d, "Operant": opv, "Skill list": sl,
                            })
                except Exception as e:
                    st.error(f"Could not read CSV: {e}")

        if bulk_rows:
            preview = pd.DataFrame(bulk_rows)
            st.caption(f"**{len(bulk_rows)}** target(s) parsed — preview:")
            st.dataframe(preview, width="stretch", hide_index=True)

        if st.button(
            f"📥 Load {len(bulk_rows)} entry(ies) into bank",
            type="primary", width="stretch", disabled=not bulk_rows,
            key=f"bank_bulk_submit_{bv}",
        ):
            new_ids = save_targets_to_bank(
                [{
                    "description": r["Description"],
                    "domain": r["Operant"],
                    "skill_list": r.get("Skill list") or "",
                } for r in bulk_rows],
                source_student_name="bulk-upload",
            )
            n_added = len(new_ids)
            n_dupes = len(bulk_rows) - n_added
            msg = []
            if n_added:
                msg.append(f"Loaded {n_added} entry(ies).")
            if n_dupes:
                msg.append(f"{n_dupes} already in bank — skipped.")
            st.success(" ".join(msg) or "Nothing new to load.")
            st.session_state["bank_bulk_ver"] = bv + 1
            st.rerun()


def page_intervention_bank():
    st.header("Intervention Bank")
    st.caption(
        "A reusable library of interventions, grouped by category. Add your "
        "own, then attach them to a behavior of concern from its detail page "
        "(where you can also drop a phase-change line when one starts)."
    )

    bank = load_intervention_bank()

    # ── Add a new intervention ───────────────────────────────────────────────
    existing_cats = sorted(
        {b["category"] for b in bank} | set(INTERVENTION_CATEGORIES)
    )
    with st.expander("➕ Add an intervention", expanded=False):
        ver = st.session_state.get("iv_add_ver", 0)
        c1, c2 = st.columns([1, 2])
        with c1:
            NEW_CAT = "➕ New category…"
            cat_pick = st.selectbox(
                "Category",
                options=existing_cats + [NEW_CAT],
                key=f"iv_add_cat_{ver}",
            )
            if cat_pick == NEW_CAT:
                category = st.text_input(
                    "New category name", key=f"iv_add_newcat_{ver}",
                ).strip()
            else:
                category = cat_pick
        with c2:
            name = st.text_input(
                "Intervention", key=f"iv_add_name_{ver}",
                placeholder="e.g., Increase reinforcer variety",
            )
        if st.button(
            "Add to bank", type="primary", disabled=not (name.strip() and category),
            key=f"iv_add_btn_{ver}",
        ):
            rec = add_intervention_to_bank(category, name)
            if rec:
                st.session_state["iv_add_ver"] = ver + 1
                st.toast(f"Added: {rec['name']}")
                st.rerun()
            else:
                st.warning("That intervention is already in the bank.")

    # ── Browse by category ───────────────────────────────────────────────────
    by_cat: dict[str, list[dict]] = {}
    for b in bank:
        by_cat.setdefault(b.get("category", "Uncategorized"), []).append(b)

    if not bank:
        st.info("The bank is empty.")
        return

    st.caption(f"**{len(bank)}** interventions across **{len(by_cat)}** categories.")
    all_cats = sorted({b["category"] for b in bank} | set(INTERVENTION_CATEGORIES))
    editing = st.session_state.get("iv_editing")
    pending_del = st.session_state.get("iv_pending_del")
    for cat in sorted(by_cat):
        desc = INTERVENTION_CATEGORIES.get(cat, "")
        label = f"{cat}" + (f" — {desc}" if desc else "")
        with st.expander(f"{label}  ({len(by_cat[cat])})", expanded=True):
            for iv in sorted(by_cat[cat], key=lambda x: x["name"].lower()):
                # ── Edit mode ────────────────────────────────────────────────
                if editing == iv["id"]:
                    with st.container(border=True):
                        e1, e2 = st.columns([2, 1])
                        new_name = e1.text_input(
                            "Intervention", value=iv["name"],
                            key=f"iv_edit_name_{iv['id']}",
                        )
                        new_cat = e2.selectbox(
                            "Category", all_cats,
                            index=(all_cats.index(iv["category"])
                                   if iv["category"] in all_cats else 0),
                            key=f"iv_edit_cat_{iv['id']}",
                        )
                        s1, s2 = st.columns(2)
                        if s1.button(
                            "💾 Save", key=f"iv_edit_save_{iv['id']}",
                            type="primary", width="stretch",
                            disabled=not new_name.strip(),
                        ):
                            allb = load_intervention_bank()
                            for x in allb:
                                if x["id"] == iv["id"]:
                                    x["name"] = new_name.strip()
                                    x["category"] = new_cat
                                    break
                            save_intervention_bank(allb)
                            st.session_state.pop("iv_editing", None)
                            st.toast("Saved.")
                            st.rerun()
                        if s2.button(
                            "Cancel", key=f"iv_edit_cancel_{iv['id']}",
                            width="stretch",
                        ):
                            st.session_state.pop("iv_editing", None)
                            st.rerun()
                    continue
                # ── Delete confirmation (warning) ────────────────────────────
                if pending_del == iv["id"]:
                    st.warning(
                        f"**Delete \"{iv['name']}\" from the bank?** This can't "
                        "be undone. Behaviors already using it keep their copy."
                    )
                    d1, d2 = st.columns(2)
                    if d1.button(
                        "Yes, delete", key=f"iv_del_yes_{iv['id']}",
                        type="primary", width="stretch",
                    ):
                        save_intervention_bank(
                            [x for x in load_intervention_bank()
                             if x["id"] != iv["id"]]
                        )
                        st.session_state.pop("iv_pending_del", None)
                        st.toast(f"Deleted: {iv['name']}")
                        st.rerun()
                    if d2.button(
                        "Cancel", key=f"iv_del_no_{iv['id']}", width="stretch",
                    ):
                        st.session_state.pop("iv_pending_del", None)
                        st.rerun()
                    continue
                # ── Normal row ───────────────────────────────────────────────
                row = st.columns([7, 1, 1])
                row[0].write(f"• {iv['name']}")
                if row[1].button("✎", key=f"iv_edit_{iv['id']}", help="Edit"):
                    st.session_state["iv_editing"] = iv["id"]
                    st.session_state.pop("iv_pending_del", None)
                    st.rerun()
                if row[2].button(
                    "🗑️", key=f"iv_del_{iv['id']}", help="Delete from bank",
                ):
                    st.session_state["iv_pending_del"] = iv["id"]
                    st.session_state.pop("iv_editing", None)
                    st.rerun()


def _cumulative_mastery_fig(sid: str, operant: str | None, view: str):
    """Build the cumulative-mastery figure. Returns (fig, y_series) or None.

    ``operant`` scopes to one operant (single line). Otherwise ``view`` selects
    'Combined total' (one filled line) or per-operant lines.
    """
    if operant is not None:
        s = cumulative_mastery_series(sid, operant)
        if s.empty or int(s["total"].max()) <= 0:
            return None
        df = s.rename(columns={"date": "Date", "total": "Mastered"})
        fig = px.line(df, x="Date", y="Mastered", markers=True)
        fig.update_traces(
            line=dict(color="#ea580c"),
            marker=dict(size=5, color="#ea580c", line=dict(width=1, color="white")),
            hovertemplate="%{x|%b %-d, %Y}: %{y:.0f} mastered<extra></extra>",
        )
        return fig, df["Mastered"]

    targets = load_targets()
    ops = sorted({
        t["domain"] for t in targets
        if t.get("student_id") == sid and t.get("domain")
    })
    frames = []
    for op in ops:
        s = cumulative_mastery_series(sid, op)
        if not s.empty and int(s["total"].max()) > 0:
            s = s.copy()
            s["Operant"] = op
            frames.append(s)
    if not frames:
        return None
    if view == "Combined total":
        df = cumulative_mastery_series(sid).rename(
            columns={"date": "Date", "total": "Mastered"}
        )
        fig = px.area(df, x="Date", y="Mastered")
        fig.update_traces(
            line=dict(color="#ea580c", width=2),
            fillcolor="rgba(234,88,12,0.12)",
            hovertemplate="%{x|%b %-d, %Y}: %{y:.0f} mastered<extra></extra>",
        )
        return fig, df["Mastered"]
    df = pd.concat(frames, ignore_index=True).rename(
        columns={"date": "Date", "total": "Mastered"}
    )
    fig = px.line(df, x="Date", y="Mastered", color="Operant", markers=True)
    fig.update_traces(
        marker=dict(size=5, line=dict(width=1, color="white")),
        hovertemplate="<b>%{fullData.name}</b><br>"
        "%{x|%b %-d, %Y}: %{y:.0f} mastered<extra></extra>",
    )
    return fig, df["Mastered"]


def _style_cumulative_fig(fig, y_series, *, show_legend: bool, height: int = 320):
    fig.update_yaxes(
        title="Targets mastered", rangemode="tozero",
        gridcolor="#f0eeec", zeroline=False,
    )
    _integer_yaxis(fig, y_series)
    fig.update_xaxes(
        title=None, gridcolor="#f0eeec", zeroline=False,
        showline=True, linecolor="#d6d3d1", linewidth=1,
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, title=None),
        hoverlabel=dict(bgcolor="white", bordercolor="#e7e5e4"),
        font=dict(family="-apple-system, BlinkMacSystemFont, Inter, sans-serif",
                  color="#1c1917"),
    )


def _render_cumulative_mastery(sid: str, operant: str | None = None) -> None:
    """Cumulative running-total mastered-targets chart (all operants or one)."""
    view = "By operant"
    if operant is None:
        view = st.radio(
            "View", ["By operant", "Combined total"],
            horizontal=True, key=f"cum_view_{sid}",
            label_visibility="collapsed",
        )
    built = _cumulative_mastery_fig(sid, operant, view)
    if built is None:
        scope = f"{operant} " if operant else ""
        st.caption(
            f"No mastered {scope}targets yet — the cumulative chart appears "
            "here as targets are mastered."
        )
        return
    fig, y_series = built
    _style_cumulative_fig(fig, y_series, show_legend=operant is None and view != "Combined total")
    st.plotly_chart(
        fig, width="stretch", key=f"cum_chart_{sid}_{operant or view}",
    )
    st.caption(
        "Running total of mastered targets at the end of each day "
        "(probed-out targets included)."
    )


def _cumulative_mastery_png(sid: str, operant: str | None = None) -> bytes | None:
    """Render the cumulative mastered-targets chart to a PNG for the PDF."""
    built = _cumulative_mastery_fig(sid, operant, "By operant")
    if built is None:
        return None
    fig, y_series = built
    _style_cumulative_fig(fig, y_series, show_legend=operant is None, height=440)
    fig.update_layout(
        width=1100, height=440,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=70, r=30, t=40, b=60),
        font=dict(family="Helvetica, Arial, sans-serif", color="#1c1917"),
    )
    fig.update_xaxes(tickangle=-35, tickfont=dict(size=11))
    png = _safe_to_image(fig, scale=2)
    if png:
        return png
    return _cumulative_mastery_png_mpl(sid, operant)


def _cumulative_mastery_png_mpl(sid: str, operant: str | None) -> bytes | None:
    """Matplotlib fallback for the cumulative mastered-targets chart."""
    try:
        import io as _io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except Exception:
        return None
    series_map: dict[str, "pd.DataFrame"] = {}
    if operant is not None:
        s = cumulative_mastery_series(sid, operant)
        if not s.empty and int(s["total"].max()) > 0:
            series_map[operant] = s
    else:
        targets = load_targets()
        for op in sorted({
            t["domain"] for t in targets
            if t.get("student_id") == sid and t.get("domain")
        }):
            s = cumulative_mastery_series(sid, op)
            if not s.empty and int(s["total"].max()) > 0:
                series_map[op] = s
    if not series_map:
        return None
    fig, ax = plt.subplots(figsize=(12, 4.8), dpi=160)
    for op, s in series_map.items():
        ax.plot(s["date"], s["total"], linewidth=2, label=op)
    ax.set_ylabel("Targets mastered", fontsize=12, labelpad=10)
    ax.set_ylim(bottom=0)
    ax.grid(True, color="#f0eeec", linewidth=1)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#d6d3d1")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    for label in ax.get_xticklabels():
        label.set_rotation(-35)
        label.set_horizontalalignment("left")
    if operant is None:
        ax.legend(loc="upper left", fontsize=9, frameon=False, ncol=3)
    fig.tight_layout()
    buf = _io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def page_student_dashboard():
    students = load_students()
    if not students:
        st.header("Dashboard")
        st.info("Add a student on **Student Home** to begin.")
        return

    sid = current_sid(students)
    st.header(f"{student_name(students, sid)}")
    st.caption("Pick what to work on.")

    pdf_session_key = f"dash_pdf_{sid}"
    pdf_bytes = st.session_state.get(pdf_session_key)
    if pdf_bytes is None:
        gen_col, _ = st.columns([1, 3])
        with gen_col:
            if st.button(
                "📄 Generate progress report (PDF)",
                key="dash_pdf_gen",
                width="stretch",
            ):
                with st.spinner("Generating PDF — this can take several seconds…"):
                    st.session_state[pdf_session_key] = build_progress_report_pdf(
                        sid, students, load_targets(), load_probes(),
                        load_behaviors(), load_behavior_records(),
                    )
                st.rerun()
    else:
        dl_col, regen_col = st.columns([3, 1])
        with dl_col:
            st.download_button(
                "📄 Download progress report (PDF)",
                data=pdf_bytes,
                file_name=(
                    f"progress_report_"
                    f"{student_name(students, sid).replace(' ', '_')}_"
                    f"{date.today().isoformat()}.pdf"
                ),
                mime="application/pdf",
                key="dash_pdf_btn",
                width="stretch",
            )
        with regen_col:
            if st.button(
                "Regenerate",
                key="dash_pdf_regen",
                width="stretch",
                help="Rebuild after data changes.",
            ):
                st.session_state.pop(pdf_session_key, None)
                st.rerun()

    cards = [
        (
            "📝", "Collect Cold Probe Data",
            "Run a probe session and record Y / N / PO / NP per target.",
            "Collect Cold Probe Data",
        ),
        (
            "🎯", "Verbal Behavior Programming",
            "Manage operants, lists, and targets. View mastery progress.",
            "Verbal Behavior Programming",
        ),
        (
            "🚨", "Behaviors of Concern",
            "Log session data for behaviors of concern and watch trends.",
            "Behaviors of Concern",
        ),
    ]
    cols = st.columns(3, gap="medium")
    for col, (icon, title, desc, page) in zip(cols, cards):
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:2.4rem;line-height:1'>{icon}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"### {title}")
                st.caption(desc)
                if st.button(
                    "Open",
                    key=f"dash_open_{page}",
                    type="primary",
                    width="stretch",
                ):
                    st.session_state["page"] = page
                    st.rerun()

    # Assessments card — curriculum assessments live here, not in the sidebar.
    st.write("")
    arow = st.columns(3, gap="medium")
    with arow[0]:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:2.4rem;line-height:1'>📋</div>",
                unsafe_allow_html=True,
            )
            st.markdown("### Assessments")
            st.caption(
                "Curriculum assessments — Essential for Living and VB-MAPP milestones."
            )
            if st.button(
                "Essential for Living", key="dash_open_efl",
                type="primary", width="stretch",
            ):
                st.session_state["page"] = "EFL Assessment"
                st.rerun()
            if st.button(
                "VB-MAPP Milestones", key="dash_open_vbmapp",
                type="primary", width="stretch",
            ):
                st.session_state["page"] = "VB-MAPP Assessment"
                st.rerun()

    st.divider()
    st.subheader("📈 Cumulative mastered targets")
    _render_cumulative_mastery(sid)


# ── EFL Assessment (freestanding) ────────────────────────────────────────────
EFL_FILE = os.path.join(DATA_DIR, "efl_assessments.json")

EFL_SKILLS = [
    # (Category, Code, Skill statement)
    # ── Must-Have (the foundational 8) ───────────────────────────────────────
    ("Must-Have", "MH1", "Makes requests for highly preferred items, foods, and activities"),
    ("Must-Have", "MH2", "Waits after making a request"),
    ("Must-Have", "MH3", "Accepts 'no,' removals, and denials"),
    ("Must-Have", "MH4", "Completes 10 consecutive, brief, previously acquired tasks"),
    ("Must-Have", "MH5", "Accepts transitions"),
    ("Must-Have", "MH6", "Completes daily living tasks related to health and safety"),
    ("Must-Have", "MH7", "Tolerates situations involving non-preferred experiences"),
    ("Must-Have", "MH8", "Accepts new and changing environments and people"),

    # ── Should-Have ──────────────────────────────────────────────────────────
    ("Should-Have", "SH1", "Engages with toys or leisure items for 30 minutes"),
    ("Should-Have", "SH2", "Tolerates close proximity to peers"),
    ("Should-Have", "SH3", "Makes choices between offered items"),
    ("Should-Have", "SH4", "Imitates simple gross-motor actions"),
    ("Should-Have", "SH5", "Imitates simple fine-motor actions"),
    ("Should-Have", "SH6", "Follows simple one-step directions"),
    ("Should-Have", "SH7", "Discriminates between common items"),
    ("Should-Have", "SH8", "Identifies common items receptively"),
    ("Should-Have", "SH9", "Tacts (names) common items"),
    ("Should-Have", "SH10", "Provides personal information (name / age)"),

    # ── Functional Communication ─────────────────────────────────────────────
    ("Functional Communication", "FC1", "Requests preferred items with words, signs, or AAC"),
    ("Functional Communication", "FC2", "Requests preferred activities"),
    ("Functional Communication", "FC3", "Requests a break"),
    ("Functional Communication", "FC4", "Requests adult attention"),
    ("Functional Communication", "FC5", "Requests help"),
    ("Functional Communication", "FC6", "Indicates 'yes' or 'no'"),
    ("Functional Communication", "FC7", "Greets familiar people"),
    ("Functional Communication", "FC8", "Communicates pain, discomfort, or illness"),

    # ── Daily Living ─────────────────────────────────────────────────────────
    ("Daily Living", "DL1", "Independent toileting"),
    ("Daily Living", "DL2", "Washes hands"),
    ("Daily Living", "DL3", "Eats with utensils"),
    ("Daily Living", "DL4", "Drinks from an open cup"),
    ("Daily Living", "DL5", "Dresses upper body"),
    ("Daily Living", "DL6", "Dresses lower body"),
    ("Daily Living", "DL7", "Brushes teeth"),
    ("Daily Living", "DL8", "Combs or brushes hair"),

    # ── Tolerating ───────────────────────────────────────────────────────────
    ("Tolerating", "TL1", "Tolerates haircuts"),
    ("Tolerating", "TL2", "Tolerates dental visits"),
    ("Tolerating", "TL3", "Tolerates medical examinations"),
    ("Tolerating", "TL4", "Tolerates required clothing (e.g., shoes, glasses)"),
    ("Tolerating", "TL5", "Tolerates loud or unexpected sounds"),
    ("Tolerating", "TL6", "Tolerates schedule changes"),
    ("Tolerating", "TL7", "Tolerates riding in vehicles"),
    ("Tolerating", "TL8", "Tolerates community outings"),
]
EFL_STATUS_OPTIONS = ["—", "Not yet", "Emerging", "Mastered"]
EFL_TESTS = [1, 2, 3, 4]

# Markdown task-analysis files live one directory up from the Repertiores app.
TASK_ANALYSES_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "task_analyses",
)
EFL_DOMAIN_LABELS = {
    "domain_1_requests": "Requests",
    "domain_2_listener_responses": "Listener Responses",
    "domain_3_visual_imitation_matching": "Visual Imitation & Matching",
    "domain_4_daily_living_skills": "Daily Living Skills",
    "domain_5_tacts_intraverbals": "Tacts & Intraverbals",
    "domain_6_tolerating_skills": "Tolerating Skills",
    "domain_7_functional_academic": "Functional Academic",
}
# Start with domain 1 — confirm the parser before expanding to the rest.
EFL_ENABLED_DOMAINS = ["domain_1_requests"]

# Default Repertiores operant per EFL domain — used to pre-fill the operant
# when pushing task-analysis steps into a student's cold-probe program.
EFL_DEFAULT_OPERANT_BY_DOMAIN = {
    "domain_1_requests":                "Mand",
    "domain_2_listener_responses":      "Listener",
    "domain_3_visual_imitation_matching": "Imitation",
    "domain_4_daily_living_skills":     "Self-Help",
    "domain_5_tacts_intraverbals":      "Tact",
    "domain_6_tolerating_skills":       "Other",
    "domain_7_functional_academic":     "Academics",
}


def _extract_efl_steps(sections: dict) -> list[str]:
    """Pull learner-behavior steps from a parsed task analysis.

    Looks for a markdown table whose header has a 'learner behavior' column and
    returns the cells of that column in order. Numbered lists (1. 2. 3.) describe
    instructor procedure and are intentionally NOT returned — cold-probe targets
    must be learner behaviors, not procedural steps. Returns [] if no learner-
    behavior table is present (e.g., preference-assessment skills R1–R5).
    """
    import re

    def _split_row(row: str) -> list[str]:
        parts = [c.strip() for c in row.strip().strip("|").split("|")]
        return parts

    seen: list[str] = []
    for body in sections.values():
        lines = body.splitlines()
        i = 0
        while i < len(lines):
            ln = lines[i]
            if "|" in ln and re.search(r"learner\s+behavior", ln, re.IGNORECASE):
                header_cells = _split_row(ln)
                col_idx = next(
                    (k for k, c in enumerate(header_cells)
                     if re.search(r"learner\s+behavior", c, re.IGNORECASE)),
                    None,
                )
                if col_idx is None:
                    i += 1
                    continue
                # Skip separator row (|---|---|).
                j = i + 1
                if j < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[j]):
                    j += 1
                while j < len(lines) and "|" in lines[j]:
                    cells = _split_row(lines[j])
                    if col_idx < len(cells):
                        text = cells[col_idx].strip().strip("*").strip()
                        # Skip blank cells, dashes, and "Repeat steps 1-N" footers.
                        if text and text not in {"—", "-", "–"} and text not in seen:
                            seen.append(text)
                    j += 1
                i = j
            else:
                i += 1
    return seen


def targets_linked_to_efl(
    student_id: str, skill_code: str, all_targets: list[dict],
) -> list[dict]:
    return [
        t for t in all_targets
        if t.get("student_id") == student_id
        and t.get("efl_skill_code") == skill_code
    ]


def _derive_efl_live_status(
    student_id: str, skill_code: str, all_targets: list[dict],
) -> tuple[str, str]:
    """Compute the EFL skill's live status from its linked cold-probe targets.

    Returns ``(label, summary)`` where label is one of
    ``Mastered``, ``Emerging``, ``Not yet``, or ``—`` (no links yet).
    """
    linked = targets_linked_to_efl(student_id, skill_code, all_targets)
    if not linked:
        return ("—", "no targets linked")
    n_total = len(linked)
    n_mastered = sum(1 for t in linked if t.get("status") == "Mastered")
    n_active = sum(
        1 for t in linked
        if t.get("status") in ("In Acquisition", "Maintenance")
    )
    summary = f"{n_mastered} / {n_total} mastered"
    if n_mastered == n_total:
        return ("Mastered", summary)
    if n_mastered > 0 or n_active > 0:
        return ("Emerging", summary)
    return ("Not yet", summary)


def _parse_task_analysis_md(path: str) -> dict | None:
    """Parse one R##_*.md file into {code, name, sections, path}."""
    import re
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None
    lines = text.splitlines()
    first = next((l for l in lines if l.strip()), "").strip().lstrip("#").strip()
    m = re.match(r"^(R[\d\-–\s]+R?\d*)\s*[—\-]\s*(.+)$", first)
    if m:
        code = m.group(1).strip()
        name = m.group(2).strip()
    else:
        code = os.path.basename(path).split("_")[0]
        name = first or os.path.basename(path)
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for ln in lines:
        if ln.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = ln[3:].strip()
            buf = []
        elif current is not None:
            buf.append(ln)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return {"code": code, "name": name, "sections": sections, "path": path}


def load_efl_catalog_from_files() -> list[dict]:
    """Build the EFL catalog by parsing markdown files under TASK_ANALYSES_ROOT.

    Returns a list of {category, code, name, path, sections}. Empty list if the
    directory is missing or no enabled domain has any files.
    """
    skills: list[dict] = []
    if not os.path.isdir(TASK_ANALYSES_ROOT):
        return skills
    for domain_dir in EFL_ENABLED_DOMAINS:
        full = os.path.join(TASK_ANALYSES_ROOT, domain_dir)
        if not os.path.isdir(full):
            continue
        label = EFL_DOMAIN_LABELS.get(domain_dir, domain_dir)
        for f in sorted(os.listdir(full)):
            if not f.endswith(".md"):
                continue
            path = os.path.join(full, f)
            parsed = _parse_task_analysis_md(path)
            if not parsed:
                continue
            skills.append({
                "category": label,
                **parsed,
            })
    return skills


def load_efl() -> list[dict[str, Any]]:
    return _load(EFL_FILE)


def save_efl(rows): _save(EFL_FILE, rows)


def efl_for_student(student_id: str) -> dict:
    """Return the student's EFL assessment record (creates an empty shell if absent).

    Shape:
      {
        "student_id": str,
        "tests": {1: {"date": iso, "tester": str, "notes": str}, 2: ..., 3: ..., 4: ...},
        "statuses": {1: {skill_code: status, ...}, 2: ..., 3: ..., 4: ...},
      }
    """
    rows = load_efl()
    for r in rows:
        if r.get("student_id") == student_id:
            # Backfill any missing test slots.
            r.setdefault("tests", {})
            r.setdefault("statuses", {})
            for n in EFL_TESTS:
                r["tests"].setdefault(str(n), {"date": "", "tester": "", "notes": ""})
                r["statuses"].setdefault(str(n), {})
            return r
    rec = {
        "student_id": student_id,
        "tests": {str(n): {"date": "", "tester": "", "notes": ""} for n in EFL_TESTS},
        "statuses": {str(n): {} for n in EFL_TESTS},
    }
    rows.append(rec)
    save_efl(rows)
    return rec


def save_efl_for_student(student_id: str, record: dict) -> None:
    rows = load_efl()
    found = False
    for i, r in enumerate(rows):
        if r.get("student_id") == student_id:
            rows[i] = record
            found = True
            break
    if not found:
        rows.append(record)
    save_efl(rows)


# ── EFL Problem Behavior Summary ──────────────────────────────────────────────
# A digital version of the EFL "Summary of the Learner's Assessments and
# Subsequent Progress on Problem Behavior" sheet. For up to two problem
# behaviors, the clinician records — at the initial assessment and at the end of
# four follow-up time periods — where the learner falls on each scale (type,
# intensity, medications, restraints, protective equipment, crisis
# stabilization, self-restraints, and frequency). On the paper form each time
# period is a color; here each period is a colored chip in the chosen cell.
EFL_PB_FILE = os.path.join(DATA_DIR, "efl_pb_summaries.json")

EFL_PB_BEHAVIORS = [
    ("PB1", "PB1 (Problem Behavior 1)"),
    ("PB2", "PB2 (Problem Behavior 2)"),
]

# Period key → display label. "initial" plus four follow-up periods.
EFL_PB_PERIODS = [
    ("initial", "Initial assessment"),
    ("tp1", "Time period 1"),
    ("tp2", "Time period 2"),
    ("tp3", "Time period 3"),
    ("tp4", "Time period 4"),
]

# Period key → RGB chip color used in the grid + PDF (mirrors "enter a color").
EFL_PB_PERIOD_COLORS = {
    "initial": (28, 25, 23),    # near-black
    "tp1": (37, 99, 235),       # blue
    "tp2": (22, 163, 74),       # green
    "tp3": (234, 88, 12),       # orange
    "tp4": (147, 51, 234),      # purple
}

# Each scale on the form: storage key, on-screen label, short PDF label, and the
# ordered option cells (most → least, matching the sheet's left-to-right order).
EFL_PB_DIMENSIONS = [
    {"key": "measure", "label": "Measure (IA / IM)", "pdf": "Measure",
     "options": ["IA", "IM"]},
    {"key": "basis", "label": "Basis (Instance / Episode)", "pdf": "Basis",
     "options": ["Instance", "Episode"]},
    {"key": "type", "label": "Type of problem behavior", "pdf": "Type",
     "options": ["SIB", "Agg", "Des", "Dis", "Rep"]},
    {"key": "intensity", "label": "Intensity", "pdf": "Intensity",
     "options": ["Sev", "Mod", "Mild"]},
    {"key": "meds", "label": "Psychoactive medications", "pdf": "Medications",
     "options": ["Med3+>", "Med3+", "Med3+<", "Med2>", "Med2", "Med2<",
                 "Med1>", "Med1", "Med1<", "-Med"]},
    {"key": "mech", "label": "Mechanical restraints", "pdf": "Mech. restraints",
     "options": ["MRA", "MRC", "MR>2", "MR>1", "MR", "MR<1", "MR<2", "MR<3",
                 "-MR"]},
    {"key": "prot", "label": "Protective equipment", "pdf": "Protective equip.",
     "options": ["PEA", "PEC", "PE>2", "PE>1", "PE", "PE<1", "PE<2", "PE<3",
                 "-PE"]},
    {"key": "crisis", "label": "Crisis stabilization", "pdf": "Crisis stab.",
     "options": ["CS>5hW", "CS 2-5hW", "CS 1-2hW", "CS 30m-1hW", "CS<30mW",
                 "-CS"]},
    {"key": "selfrest", "label": "Self-restraints", "pdf": "Self-restraints",
     "options": ["SR>2", "SR>1", "SR", "SR<1", "SR<2", "SR<3", "-SR"]},
    {"key": "freq", "label": "Frequency of occurrence", "pdf": "Frequency",
     "options": [">100D", "50-100D", "20-50D", "10-20D", "1-10D", "<1D",
                 "<1W", "<1M", "<1Y"]},
]

# Legend text reproduced from the bottom of the paper form.
EFL_PB_LEGEND = [
    ("Type of problem behavior", [
        "SIB - Self-injurious", "Agg - Aggressive", "Des - Destructive",
        "Dis - Disruptive", "Rep - Repetitive"]),
    ("Intensity", ["Sev - Severe", "Mod - Moderate", "Mild - Mild"]),
    ("Psychoactive medications", [
        "Med3+>  3+ meds, some dosage increases",
        "Med3+   3+ medications",
        "Med3+<  3+ meds, some dosage reductions",
        "Med2>   2 meds, some dosage increases",
        "Med2    2 medications",
        "Med2<   2 meds, some dosage reductions",
        "Med1>   1 med, some dosage increases",
        "Med1    1 medication",
        "Med1<   1 med, some dosage reductions",
        "-Med    No medications"]),
    ("Mechanical restraints  (MRA continuous / MRC contingent)", [
        "MR>2  increased twice", "MR>1  increased once",
        "MR    at initial assessment", "MR<1  partially faded once",
        "MR<2  partially faded twice", "MR<3  partially faded 3x",
        "-MR   not required"]),
    ("Protective equipment  (PEA continuous / PEC contingent)", [
        "PE>2  increased twice", "PE>1  increased once",
        "PE    at initial assessment", "PE<1  partially faded once",
        "PE<2  partially faded twice", "PE<3  partially faded 3x",
        "-PE   not required"]),
    ("Crisis stabilization procedures", [
        "CS>5hW    used > 5 hours/week", "CS 2-5hW  used 2-5 hours/week",
        "CS 1-2hW  used 1-2 hours/week", "CS 30m-1hW used 30 min-1 hour/week",
        "CS<30mW   used < 30 min/week", "-CS       not required"]),
    ("Self-restraints", [
        "SR>2  increased twice", "SR>1  increased once",
        "SR    at initial assessment", "SR<1  partially faded once",
        "SR<2  partially faded twice", "SR<3  partially faded 3x",
        "-SR   not occurring"]),
    ("Frequency of occurrence (per day unless noted)", [
        ">100D  > 100 instances/day", "50-100D  50-100/day",
        "20-50D  20-50/day", "10-20D  10-20/day", "1-10D  1-10/day",
        "<1D  less than once/day", "<1W  less than once/week",
        "<1M  less than once/month", "<1Y  not in one year"]),
]


def load_efl_pb() -> list[dict[str, Any]]:
    return _load(EFL_PB_FILE)


def save_efl_pb(rows): _save(EFL_PB_FILE, rows)


def _empty_efl_pb_behavior() -> dict:
    return {
        "name": "",
        "absence_skills": "",
        "periods": {
            pk: {d["key"]: "-" for d in EFL_PB_DIMENSIONS}
            for pk, _ in EFL_PB_PERIODS
        },
    }


def efl_pb_for_student(student_id: str) -> dict:
    """Return the student's PB-summary record, creating an empty shell if absent
    and backfilling any newly added behaviors / periods / dimensions."""
    rows = load_efl_pb()
    rec = next((r for r in rows if r.get("student_id") == student_id), None)
    if rec is None:
        rec = {"student_id": student_id, "behaviors": {}}
    rec.setdefault("behaviors", {})
    for bk, _ in EFL_PB_BEHAVIORS:
        b = rec["behaviors"].setdefault(bk, _empty_efl_pb_behavior())
        b.setdefault("name", "")
        b.setdefault("absence_skills", "")
        periods = b.setdefault("periods", {})
        for pk, _ in EFL_PB_PERIODS:
            cell = periods.setdefault(pk, {})
            for d in EFL_PB_DIMENSIONS:
                cell.setdefault(d["key"], "-")
    return rec


def save_efl_pb_for_student(student_id: str, record: dict) -> None:
    rows = load_efl_pb()
    for i, r in enumerate(rows):
        if r.get("student_id") == student_id:
            rows[i] = record
            break
    else:
        rows.append(record)
    save_efl_pb(rows)


def _pb_grid_row(pdf, label, options, sel_by_option,
                 x0, label_w, cell_w, row_h):
    """Draw one labeled scale row: a label then a cell per option, with a small
    colored chip in any cell selected by a time period. ``sel_by_option`` maps
    option → list of period keys that landed on it."""
    if pdf.get_y() + row_h > pdf.h - pdf.b_margin:
        pdf.add_page()
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 6.5)
    pdf.set_text_color(70, 70, 70)
    pdf.set_xy(x0, y + (row_h - 3) / 2)
    pdf.cell(label_w - 1.5, 3, _pdf_safe(label), align="L")
    x = x0 + label_w
    for opt in options:
        pdf.set_draw_color(170, 170, 170)
        pdf.set_line_width(0.2)
        pdf.rect(x, y, cell_w, row_h)
        pdf.set_font("Helvetica", "", 5.6)
        pdf.set_text_color(30, 30, 30)
        pdf.set_xy(x, y + 0.8)
        pdf.cell(cell_w, 2.6, _pdf_safe(opt), align="C")
        periods = sel_by_option.get(opt, [])
        if periods:
            chip, gap = 1.9, 0.5
            total = len(periods) * chip + (len(periods) - 1) * gap
            sx = x + (cell_w - total) / 2
            sy = y + row_h - chip - 0.7
            for pk in periods:
                pdf.set_fill_color(*EFL_PB_PERIOD_COLORS.get(pk, (0, 0, 0)))
                pdf.rect(sx, sy, chip, chip, style="F")
                sx += chip + gap
        x += cell_w
    pdf.set_xy(x0, y + row_h)


def build_efl_pb_pdf(student: dict, record: dict) -> bytes:
    name = student.get("name", "")
    pdf = _pdf_init(f"EFL Problem Behavior Summary · {name}")
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin

    # Title block.
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(28, 25, 23)
    pdf.cell(0, 7, "ESSENTIAL FOR LIVING",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(0, 5,
             _pdf_safe("A Summary of the Learner's Assessments and Subsequent "
                       "Progress on Problem Behavior"),
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(1.5)
    _pdf_kv_row(pdf, "Learner", name or "-")
    _pdf_kv_row(pdf, "Generated", _fmt_date(date.today().isoformat()))
    pdf.ln(1)

    # Period color legend.
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(70, 70, 70)
    x = pdf.l_margin
    y = pdf.get_y()
    for pk, plabel in EFL_PB_PERIODS:
        pdf.set_fill_color(*EFL_PB_PERIOD_COLORS[pk])
        pdf.rect(x, y + 0.4, 3, 3, style="F")
        pdf.set_xy(x + 3.8, y)
        pdf.cell(34, 4, _pdf_safe(plabel))
        x += 40
    pdf.set_y(y + 5.5)

    label_w = 30.0
    n_cols_max = max(len(d["options"]) for d in EFL_PB_DIMENSIONS)
    cell_w = (avail_w - label_w) / n_cols_max
    row_h = 6.2

    for bk, blabel in EFL_PB_BEHAVIORS:
        b = record.get("behaviors", {}).get(bk, {})
        block_h = 7 + row_h * len(EFL_PB_DIMENSIONS) + 12
        if pdf.get_y() + block_h > pdf.h - pdf.b_margin:
            pdf.add_page()
        pdf.ln(2)
        pdf.set_fill_color(245, 244, 242)
        pdf.set_draw_color(120, 113, 108)
        pdf.set_line_width(0.3)
        by = pdf.get_y()
        pdf.rect(pdf.l_margin, by, avail_w, 6, style="DF")
        pdf.set_xy(pdf.l_margin + 1.5, by + 1.2)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(28, 25, 23)
        nm = (b.get("name") or "").strip()
        pdf.cell(0, 3.6, _pdf_safe(f"{blabel}:  {nm}" if nm else f"{blabel}:"))
        pdf.set_y(by + 7)

        periods = b.get("periods", {})
        for d in EFL_PB_DIMENSIONS:
            sel_by_option: dict[str, list[str]] = {}
            for pk, _ in EFL_PB_PERIODS:
                val = (periods.get(pk, {}) or {}).get(d["key"], "-")
                if val and val != "-" and val in d["options"]:
                    sel_by_option.setdefault(val, []).append(pk)
            _pb_grid_row(pdf, d["pdf"], d["options"], sel_by_option,
                         pdf.l_margin, label_w, cell_w, row_h)

        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(90, 85, 80)
        absence = (b.get("absence_skills") or "").strip()
        pdf.multi_cell(
            0, 3.6,
            _pdf_safe(f"{bk} occurs in the absence of these skills: "
                      f"{absence or '-'}"))

    # Legend reference page.
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(28, 25, 23)
    pdf.cell(0, 6, "Scale reference",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    col_w = avail_w / 2
    for heading, lines in EFL_PB_LEGEND:
        needed = 4.4 + len(lines) * 3.3 + 2
        if pdf.get_y() + needed > pdf.h - pdf.b_margin:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 7.8)
        pdf.set_text_color(234, 88, 12)
        pdf.cell(0, 4.2, _pdf_safe(heading),
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(50, 48, 46)
        for ln in lines:
            pdf.cell(0, 3.3, _pdf_safe(ln),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.5)

    return _pdf_bytes(pdf)


def _efl_pb_summary_section(sid: str, s: dict) -> None:
    """Interactive EFL Problem Behavior Summary, saved per student."""
    st.divider()
    st.subheader("Problem Behavior Summary")
    st.caption(
        "EFL *Summary of the Learner's Assessments and Subsequent Progress on "
        "Problem Behavior*. For each problem behavior, pick where the learner "
        "falls on every scale at the initial assessment and at the end of up to "
        "four time periods. Each period is color-coded (like the paper form)."
    )

    # Period color legend.
    legend = "  ".join(
        f"<span style='display:inline-block;width:10px;height:10px;"
        f"background:rgb{EFL_PB_PERIOD_COLORS[pk]};border-radius:2px;"
        f"margin:0 3px -1px 0'></span>{plabel}"
        for pk, plabel in EFL_PB_PERIODS
    )
    st.markdown(legend, unsafe_allow_html=True)

    rec = efl_pb_for_student(sid)
    pbver = st.session_state.get("efl_pb_ver", 0)

    period_labels = [lbl for _, lbl in EFL_PB_PERIODS]
    label_to_pk = {lbl: pk for pk, lbl in EFL_PB_PERIODS}
    edits: dict[str, Any] = {}
    name_inputs: dict[str, str] = {}
    absence_inputs: dict[str, str] = {}

    pb_col_config = {
        "Period": st.column_config.TextColumn(width="small", disabled=True),
    }
    for d in EFL_PB_DIMENSIONS:
        pb_col_config[d["label"]] = st.column_config.SelectboxColumn(
            d["label"], options=["-"] + d["options"], required=False,
            width="small",
        )

    tabs = st.tabs([lbl for _, lbl in EFL_PB_BEHAVIORS])
    for tab, (bk, blabel) in zip(tabs, EFL_PB_BEHAVIORS):
        with tab:
            b = rec["behaviors"][bk]
            name_inputs[bk] = st.text_input(
                f"{blabel} — behavior",
                value=b.get("name", ""),
                placeholder="e.g. hitting others",
                key=f"efl_pb_name_{bk}_{pbver}",
            )
            rows = []
            for pk, plabel in EFL_PB_PERIODS:
                cell = b["periods"].get(pk, {})
                row = {"Period": plabel}
                for d in EFL_PB_DIMENSIONS:
                    v = cell.get(d["key"], "-")
                    row[d["label"]] = v if v in (["-"] + d["options"]) else "-"
                rows.append(row)
            edits[bk] = st.data_editor(
                pd.DataFrame(rows, columns=["Period"] +
                             [d["label"] for d in EFL_PB_DIMENSIONS]),
                width="stretch",
                hide_index=True,
                key=f"efl_pb_grid_{bk}_{pbver}",
                column_config=pb_col_config,
            )
            absence_inputs[bk] = st.text_area(
                f"{bk} occurs in the absence of these skills",
                value=b.get("absence_skills", ""),
                key=f"efl_pb_absence_{bk}_{pbver}",
                height=70,
            )

    save_col, dl_col = st.columns(2)
    with save_col:
        if st.button(
            "💾 Save problem behavior summary", type="primary",
            width="stretch", key=f"efl_pb_save_{pbver}",
        ):
            for bk, _ in EFL_PB_BEHAVIORS:
                b = rec["behaviors"][bk]
                b["name"] = (name_inputs.get(bk, "") or "").strip()
                b["absence_skills"] = (absence_inputs.get(bk, "") or "").strip()
                for r in edits[bk].to_dict("records"):
                    pk = label_to_pk.get(r.get("Period", ""))
                    if not pk:
                        continue
                    for d in EFL_PB_DIMENSIONS:
                        v = r.get(d["label"], "-")
                        if v not in (["-"] + d["options"]):
                            v = "-"
                        b["periods"].setdefault(pk, {})[d["key"]] = v
            save_efl_pb_for_student(sid, rec)
            st.session_state["efl_pb_ver"] = pbver + 1
            st.toast("Problem behavior summary saved.")
            st.rerun()
    with dl_col:
        st.download_button(
            "📄 Download summary PDF",
            data=build_efl_pb_pdf(s, rec),
            file_name=(
                f"efl_pb_summary_{(s.get('name','') or 'learner').replace(' ', '_')}"
                f"_{date.today().isoformat()}.pdf"
            ),
            mime="application/pdf",
            width="stretch",
            key=f"efl_pb_pdf_{pbver}",
        )
    st.caption(
        "The PDF reflects the **last saved** data — save first if you just made "
        "changes. A scale-reference legend is appended on the final page."
    )


# The 8 EFL "Must-Have" skills — overview cards shown atop the EFL report.
# (icon emoji, title, subtitle).
EFL_MUST_HAVE_SKILLS = [
    ("🙋", "Making Requests", "[mands]"),
    ("⏳", "Waiting after making requests", ""),
    ("🔄", "Accepting Removals", "Transitions, Sharing, and Taking Turns"),
    ("✅", "Completing Required Tasks",
     "Completing Previously Acquired Tasks when asked to do so"),
    ("🚫", 'Accepting "No"', ""),
    ("🧭", "Following Directions", "related to Health and Safety"),
    ("🧼", "Completing Daily Living Skills", "related to Health and Safety"),
    ("💪", "Tolerating Skills", "related to Health and Safety"),
]


def _efl_must_have_overview() -> None:
    """Render the 8 Must-Have skills as a styled card grid (matches the EFL
    one-pager)."""
    cards = "".join(
        f'<div class="efl-mh-card">'
        f'<div class="efl-mh-icon">{icon}</div>'
        f'<div class="efl-mh-num">{i}</div>'
        f'<div class="efl-mh-title">{title}</div>'
        + (f'<div class="efl-mh-sub">{sub}</div>' if sub else
           '<div class="efl-mh-sub">&nbsp;</div>')
        + '</div>'
        for i, (icon, title, sub) in enumerate(EFL_MUST_HAVE_SKILLS, start=1)
    )
    st.markdown(
        """
        <style>
        .efl-mh-wrap{background:#fdebef;border-radius:18px;
          padding:26px 22px 30px;margin:4px 0 8px;}
        .efl-mh-h1{text-align:center;font-weight:800;letter-spacing:2px;
          font-size:34px;color:#1a1a1a;margin:0 0 8px;
          font-family:'Arial Black','Helvetica Neue',sans-serif;}
        .efl-mh-h1 .hl{color:#a4243b;}
        .efl-mh-lead{text-align:center;color:#444;font-size:15px;margin:0 0 22px;}
        .efl-mh-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
        @media (max-width:1100px){.efl-mh-grid{grid-template-columns:repeat(2,1fr);}}
        @media (max-width:620px){.efl-mh-grid{grid-template-columns:1fr;}}
        .efl-mh-card{background:#fff;border-radius:16px;padding:22px 16px 20px;
          text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.05);
          display:flex;flex-direction:column;align-items:center;}
        .efl-mh-icon{font-size:34px;line-height:1;margin-bottom:10px;}
        .efl-mh-num{width:34px;height:34px;line-height:34px;border-radius:50%;
          background:#a4243b;color:#fff;font-weight:700;margin:0 auto 12px;}
        .efl-mh-title{font-weight:600;color:#222;font-size:16px;margin-bottom:4px;}
        .efl-mh-sub{color:#666;font-size:13px;line-height:1.35;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="efl-mh-wrap">'
        '<div class="efl-mh-h1">THE <span class="hl">MUST-HAVE</span> SKILLS</div>'
        '<div class="efl-mh-lead">These skills are some of the first skills '
        'addressed in Essential for Living.</div>'
        f'<div class="efl-mh-grid">{cards}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── EFL Quick Assessment (QA) ─────────────────────────────────────────────────
# The 18-area "Quick Assessment" rated 1-4. Items 3-10 are "The Essential
# Eight". Stored per student.
EFL_QA_FILE = os.path.join(DATA_DIR, "efl_qa.json")
EFL_QA_SCALE = [1, 2, 3, 4]
# Each item: number, label, Essential-Eight flag, prompt (definition), and the
# four scale descriptors keyed 1-4.
EFL_QA_ITEMS = [
    {"num": 1, "label": "Spoken Words", "e8": False,
     "prompt": "The extent to which a learner exhibits spontaneous, "
               "understandable spoken words and the conditions under which "
               "spoken-word repetitions occur",
     "levels": {
         1: "Exhibits only noises and a few sounds",
         2: "Exhibits occasional words or spoken-word repetitions, but neither "
            "are understandable",
         3: "Exhibits a few spontaneous spoken words and spoken-word "
            "repetitions, both of which are understandable",
         4: "Exhibits many spontaneous, spoken-words, nearly typical "
            "spoken-word interactions, and spoken-word repetitions when asked "
            "to do so, all of which are understandable"}},
    {"num": 2, "label": "Alternative Method of Speaking", "e8": False,
     "prompt": "A method of speaking used by learners, who do not exhibit "
               "understandable spoken words or spoken-word repetitions",
     "levels": {
         1: "Has no formal method of speaking or is using one or more "
            "ineffective methods",
         2: "A new alternative method of speaking is being tested",
         3: "Has been using an effective, alternative method of speaking for "
            "1-6 months",
         4: "Has been using an effective, alternative method of speaking for "
            "more than 6 months"}},
    {"num": 3, "label": "Making Requests", "e8": True,
     "prompt": "The tendency to make requests for highly preferred items and "
               "activities",
     "levels": {
         1: "Makes requests by exhibiting problem behavior",
         2: "Makes requests by leading others to items",
         3: "Makes requests for 1-3 preferred items or activities with or "
            "without prompts",
         4: "Makes requests for 10 or more preferred items or activities "
            "without prompts using and effective method of speaking"}},
    {"num": 4, "label": "Waiting", "e8": True,
     "prompt": "The tendency to wait when access to items or activities is "
               "delayed after a request",
     "levels": {
         1: "Exhibits problem behavior when access is delayed for a few seconds",
         2: "Waits for 1 minute with complaints or other minor disruptions",
         3: "Waits for 5 minutes without complaints",
         4: "Waits for 20 minutes without complaints"}},
    {"num": 5,
     "label": "Accepting Removals, Making Transitions, Sharing and Taking Turns",
     "e8": True,
     "prompt": "The tendency to accept the removal of preferred items and "
               "activities by persons in authority or peers, to make "
               "transitions from preferred activities to non-preferred ones, "
               "and to share and take turns with preferred ones",
     "levels": {
         1: "Exhibits problem behavior when preferred items or activities are "
            "removed, during transitions, or during required sharing or taking "
            "turns",
         2: "Makes complaints when preferred items or activities are removed, "
            "during transitions, or during required sharing or taking turns",
         3: "Complains when preferred items or activities are removed, during "
            "transitions, or when required to share or take turns, but only "
            "when motivating events are strong",
         4: "Accepts the removal of items and activities, transitions, shares, "
            "and takes turns without complaints"}},
    {"num": 6,
     "label": "Completing 10 Consecutive, Brief, Previously Acquired Tasks",
     "e8": True,
     "prompt": "The tendency to complete brief, previously acquired tasks "
               "between opportunities to make requests",
     "levels": {
         1: "Exhibits problem behavior when directed to complete a brief, "
            "previously acquired task",
         2: "Completes 1-3 consecutive, brief, previously acquired tasks "
            "without disruptive behavior",
         3: "Completes 4-6 consecutive, brief, previously acquired tasks "
            "without complaints",
         4: "Completes 10 or more consecutive, brief, previously acquired "
            "tasks of varying durations and requiring varying degrees of "
            "effort without complaints"}},
    {"num": 7, "label": "Accepting 'No'", "e8": True,
     "prompt": "The tendency to accept 'no' when access to items or activities "
               "is denied following requests that were taught and requests for "
               "dangerous items and activities that were not taught",
     "levels": {
         1: 'Exhibits problem behavior when told "no"',
         2: 'Complains when told "no"',
         3: "Complains only when motivation related to the requested item or "
            "activity is strong",
         4: "Readily accepts \"no\" by continuing with ongoing activities"}},
    {"num": 8, "label": "Following Directions Related to Health and Safety",
     "e8": True,
     "prompt": "The tendency to follow directions from others that insure "
               "safety and that permit safe movement throughout the community",
     "levels": {
         1: "Does not follow any directions that involve matters of safety and "
            "cannot be taken most places within the community without problem "
            "behavior or risking safety",
         2: 'Follows only a few directions and requires "hands on" supervision '
            "at all times",
         3: "Follows many directions related to safety and can be taken most "
            "places in a group of three with one supervisor",
         4: "Follows all directions that involve matters of health and safety "
            "and can be taken anywhere with minimal supervision"}},
    {"num": 9,
     "label": "Completing Daily Living Skills Related to Health and Safety",
     "e8": True,
     "prompt": "The tendency to perform daily living skills which have an "
               "immediate impact on the health and safety of the learner",
     "levels": {
         1: "Does not complete any daily living skills related to health and "
            "safety without prompts, resistance to prompts, or problem behavior",
         2: "Completes 1-3 daily living skills related to health and safety "
            "with complaints, some resistance to prompts, or some problem "
            "behavior",
         3: "Completes 4-6 daily living skills related to health and safety",
         4: "Completes most daily living skills related to health and safety"}},
    {"num": 10,
     "label": "Tolerating Situations Related to Health and Safety", "e8": True,
     "prompt": "The tendency to tolerate unpleasant situations which have an "
               "immediate impact on the health and safety of the learner",
     "levels": {
         1: "Because of intense episodes of problem behavior, instructors and "
            "care providers occasionally avoid routine activities related to "
            "health and safety",
         2: "Tolerates 1-3 routine activities related to health and safety "
            "with some complaints or problem behavior",
         3: "Tolerates 4-6 routine activities related to health and safety",
         4: "Tolerates most routine activities related to health and safety "
            "without problem behavior"}},
    {"num": 11, "label": "Matching", "e8": False,
     "prompt": "The tendency to match items-to-items, photographs-to-items, "
               "and text-to-items",
     "levels": {
         1: "Does not match identical items",
         2: "Matches only identical items",
         3: "Matches a few photographs or miniature items with items or "
            "activities and vice versa",
         4: "Matches photographs or miniature items, but not text, with items "
            "or activities and vice versa"}},
    {"num": 12, "label": "Imitation", "e8": False,
     "prompt": "The tendency to imitate motor movements made by others",
     "levels": {
         1: "Does not imitate any movements",
         2: "Imitates some finger, hand, arm movements, but not motor "
            "movements with items",
         3: "Imitates many finger, hand, arm movements and a few motor "
            "movements with items",
         4: "Imitates finger, hand, and arm movements and motor movements with "
            "items, but does not copy words that have been written, typed, or "
            "Braille-written"}},
    {"num": 13, "label": "Other Daily Living Skills", "e8": False,
     "prompt": "The tendency to perform daily living skills that do not have "
               "an immediate impact on the health and safety of the learner",
     "levels": {
         1: "Does not complete any daily living skills not related to health "
            "and safety without prompts, resistance to prompts, or problem "
            "behavior",
         2: "Completes 1-3 daily living skills not related to health and "
            "safety with complaints, some resistance to prompts, or some "
            "problem behavior",
         3: "Completes 4-6 daily living skills not related to health and safety",
         4: "Completes most daily living skills not related to health and "
            "safety"}},
    {"num": 14, "label": "Tolerating Other Situations", "e8": False,
     "prompt": "The tendency to tolerate unpleasant situations which do not "
               "have an immediate impact on the health and safety of the "
               "learner",
     "levels": {
         1: "Because of intense episodes of problem behavior, instructors and "
            "care providers occasionally avoid routine activities not related "
            "to health and safety",
         2: "Tolerates 1-3 routine activities not related to health and safety "
            "with some complaints or problem behavior",
         3: "Tolerates 4-6 routine activities not related to health and safety",
         4: "Tolerates most routine activities not related to health and "
            "safety without problem behavior"}},
    {"num": 15, "label": "Naming and Describing", "e8": False,
     "prompt": "The tendency to name and describe items, activities, people, "
               "places, locations, and items with features that are part of "
               "routine events",
     "levels": {
         1: "Does not exhibit any names or descriptions",
         2: "Names some items and activities that are part of 1-3 routine "
            "events",
         3: "Names many items, activities, familiar people, and places that "
            "are part of 4-6 routine events",
         4: "Names or describes many items, activities, familiar people, "
            "places, locations, and items with features that are part of 7 or "
            "more routine events"}},
    {"num": 16,
     "label": "Following Directions, Recognizing, and Retrieving", "e8": False,
     "prompt": "The tendency to follow directions, to recognize items, "
               "activities, people, places, locations, and items with "
               "features, and to retrieve items, people, and items with "
               "features that are part of routine events",
     "levels": {
         1: "Does not follow directions to complete routine activities and "
            "does not recognize or retrieve any item that is part of a routine "
            "activity",
         2: "Follows directions to complete routine activities, and recognizes "
            "and retrieves some items that are part of 1-3 routine events",
         3: "Recognizes and retrieves many items, activities, familiar people, "
            "and places that are part of 4-6 routine events",
         4: "Recognizes and retrieves many items, activities, familiar people, "
            "places, locations, and items with features that are part of 7 or "
            "more routine events"}},
    {"num": 17, "label": "Answering Questions", "e8": False,
     "prompt": "The tendency to answer questions that occur before, during, or "
               "after routine events",
     "levels": {
         1: "Cannot answer any commonly occurring questions",
         2: 'Answers some questions like "Do you want juice?", "Can you help '
            'me?", "What do you want?", or "Which one do you want?" that are '
            "part of 1-3 routine events",
         3: 'Answers many questions like "Where are the napkins?", "Who is '
            'that?", "What are you going to do?", "What are you going to get '
            'at the mall?", "Who is helping you?", "Where are you going?", and '
            '"When do you want your cigar?" that are a part of 4-6 routine '
            "events",
         4: 'Answers many questions like "What are you going to do after '
            'lunch?", "Where did you put your blue pants?", and "Who is '
            'driving you to the movies?" that are a part of 7 or more routine '
            "events"}},
    {"num": 18, "label": "Problem Behavior", "e8": False,
     "prompt": "The tendency for the learner to exhibit problem behavior",
     "levels": {
         1: "Exhibits frequent and intense self-injurious, aggressive, or "
            "destructive behavior",
         2: "Exhibits infrequent and less intense self-injurious, aggressive, "
            "or destructive behavior",
         3: "Exhibits disruptive behavior or frequent complaining that "
            "presents a problem",
         4: "Does not exhibit problem behavior"}},
]


def load_efl_qa() -> list[dict[str, Any]]:
    return _load(EFL_QA_FILE)


def save_efl_qa(rows): _save(EFL_QA_FILE, rows)


def efl_qa_for_student(student_id: str) -> dict:
    rows = load_efl_qa()
    rec = next((r for r in rows if r.get("student_id") == student_id), None)
    if rec is None:
        rec = {"student_id": student_id}
    rec.setdefault("scores", {})
    rec.setdefault("date", "")
    rec.setdefault("assessor", "")
    rec.setdefault("notes", "")
    return rec


def save_efl_qa_for_student(student_id: str, record: dict) -> None:
    rows = load_efl_qa()
    for i, r in enumerate(rows):
        if r.get("student_id") == student_id:
            rows[i] = record
            break
    else:
        rows.append(record)
    save_efl_qa(rows)


def build_efl_qa_pdf(student: dict, record: dict) -> bytes:
    name = student.get("name", "")
    pdf = _pdf_init(f"EFL Quick Assessment · {name}")
    avail = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(28, 25, 23)
    pdf.cell(0, 7, "THE ESSENTIAL FOR LIVING QUICK ASSESSMENT (QA)",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    _pdf_kv_row(pdf, "Learner", name or "-")
    _pdf_kv_row(pdf, "Generated", _fmt_date(date.today().isoformat()))
    if (record.get("date") or "").strip():
        _pdf_kv_row(pdf, "Assessment date", _fmt_date(record["date"]))
    if (record.get("assessor") or "").strip():
        _pdf_kv_row(pdf, "Assessor", record["assessor"])
    pdf.ln(2)

    scores = record.get("scores", {})
    cell_w, gap, box_h = 11.0, 2.0, 6.0
    cells_w = len(EFL_QA_SCALE) * cell_w + (len(EFL_QA_SCALE) - 1) * gap
    label_w = avail - cells_w

    for item in EFL_QA_ITEMS:
        num, label = item["num"], item["label"]
        if num == 3:
            if pdf.get_y() + 6 > pdf.h - pdf.b_margin:
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(122, 30, 40)
            pdf.cell(0, 5, "The Essential Eight (items 3-10)",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pdf.get_y() + box_h + 1.5 > pdf.h - pdf.b_margin:
            pdf.add_page()
        y = pdf.get_y()
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(28, 25, 23)
        pdf.set_xy(pdf.l_margin, y)
        pdf.cell(label_w, box_h, _pdf_safe(f"{num}. {label}"), align="L")
        x = pdf.l_margin + label_w
        cur = scores.get(str(num))
        for val in EFL_QA_SCALE:
            sel = cur == val
            if sel:
                pdf.set_fill_color(37, 99, 235)
                pdf.set_draw_color(37, 99, 235)
                pdf.rect(x, y + 0.3, cell_w, box_h - 0.6, style="DF")
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 8)
            else:
                pdf.set_draw_color(175, 175, 175)
                pdf.rect(x, y + 0.3, cell_w, box_h - 0.6, style="D")
                pdf.set_text_color(90, 90, 90)
                pdf.set_font("Helvetica", "", 8)
            pdf.set_xy(x, y + 0.3)
            pdf.cell(cell_w, box_h - 0.6, str(val), align="C")
            x += cell_w + gap
        pdf.set_y(y + box_h + 1.5)

    notes = (record.get("notes") or "").strip()
    if notes:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(28, 25, 23)
        pdf.cell(0, 4.4, "Notes", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(60, 58, 56)
        pdf.multi_cell(0, 4, _pdf_safe(notes))

    # ── Scale descriptors reference ────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(28, 25, 23)
    pdf.cell(0, 6, "Scale descriptors", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 113, 108)
    pdf.cell(0, 4.4, "The selected score for each area is highlighted.",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)
    for item in EFL_QA_ITEMS:
        num = item["num"]
        cur = scores.get(str(num))
        # Heading + prompt, kept together with at least the first descriptor.
        if pdf.get_y() + 16 > pdf.h - pdf.b_margin:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(28, 25, 23)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(avail, 4.4, _pdf_safe(f"{num}. {item['label']}"))
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 113, 108)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(avail, 3.8, _pdf_safe(item["prompt"]))
        pdf.ln(0.5)
        for val in EFL_QA_SCALE:
            txt = item["levels"][val]
            sel = cur == val
            line = f"{val}.  {txt}"
            if pdf.get_y() + 7 > pdf.h - pdf.b_margin:
                pdf.add_page()
            x0, y0 = pdf.l_margin, pdf.get_y()
            if sel:
                pdf.set_font("Helvetica", "B", 8.5)
                pdf.set_text_color(37, 99, 235)
            else:
                pdf.set_font("Helvetica", "", 8.5)
                pdf.set_text_color(55, 53, 51)
            pdf.set_xy(x0 + 3, y0)
            pdf.multi_cell(avail - 3, 4, _pdf_safe(line))
            if sel:
                # Accent bar beside the chosen descriptor.
                pdf.set_fill_color(37, 99, 235)
                pdf.rect(x0, y0 + 0.4, 1.4, pdf.get_y() - y0 - 0.8, style="F")
        pdf.ln(2)

    return _pdf_bytes(pdf)


def _efl_qa_rows(items, scores, sid, show_desc=False) -> None:
    for item in items:
        num, label = item["num"], item["label"]
        cols = st.columns([0.60, 0.10, 0.10, 0.10, 0.10])
        cols[0].markdown(f"**{num}.** {label}")
        cur = scores.get(str(num))
        for idx, val in enumerate(EFL_QA_SCALE):
            with cols[idx + 1]:
                if st.button(
                    str(val),
                    key=f"efl_qa_{sid}_{num}_{val}",
                    type="primary" if cur == val else "secondary",
                    width="stretch",
                    help=item["levels"].get(val, ""),
                ):
                    scores[str(num)] = None if cur == val else val
                    st.rerun()
        if show_desc:
            st.caption(f"_{item['prompt']}_")
            for val in EFL_QA_SCALE:
                txt = item["levels"][val]
                if cur == val:
                    st.markdown(
                        f"<div style='border-left:3px solid #2563eb;"
                        f"padding-left:8px;margin:1px 0'><b>{val}.</b> {txt}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div style='padding-left:11px;margin:1px 0;"
                        f"color:#6b6b6b;font-size:0.86em'>{val}. {txt}</div>",
                        unsafe_allow_html=True,
                    )


def _efl_qa_section(sid: str, s: dict) -> None:
    """Interactive EFL Quick Assessment (18 areas, scored 1-4), per student."""
    st.divider()
    st.subheader("Quick Assessment (QA)")
    st.caption(
        "The Essential for Living *Quick Assessment* — rate each of the 18 areas "
        "**1–4**. Items **3–10** make up *The Essential Eight*. Click a number to "
        "set it (click again to clear), then **Save**. Hover a number to see what "
        "that score means."
    )
    show_desc = st.toggle(
        "Show scale descriptors", key=f"efl_qa_showdesc_{sid}",
        help="Show the full 1–4 descriptor text under each area.",
    )

    rec = efl_qa_for_student(sid)
    ss_key = f"_efl_qa_scores_{sid}"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = {
            k: v for k, v in rec.get("scores", {}).items() if v
        }
    scores = st.session_state[ss_key]

    mc = st.columns(2)
    date_val = mc[0].text_input(
        "Assessment date", value=rec.get("date", ""),
        placeholder="YYYY-MM-DD", key=f"efl_qa_date_{sid}",
    )
    assessor_val = mc[1].text_input(
        "Assessor", value=rec.get("assessor", ""), key=f"efl_qa_assessor_{sid}",
    )

    _efl_qa_rows([i for i in EFL_QA_ITEMS if i["num"] <= 2],
                 scores, sid, show_desc)
    with st.container(border=True):
        st.markdown("**⟮ The Essential Eight ⟯**")
        _efl_qa_rows([i for i in EFL_QA_ITEMS if 3 <= i["num"] <= 10],
                     scores, sid, show_desc)
    _efl_qa_rows([i for i in EFL_QA_ITEMS if i["num"] >= 11],
                 scores, sid, show_desc)

    notes_val = st.text_area(
        "Notes", value=rec.get("notes", ""), key=f"efl_qa_notes_{sid}", height=70,
    )

    answered = sum(1 for v in scores.values() if v)
    st.caption(f"Answered **{answered} / {len(EFL_QA_ITEMS)}** areas.")

    # PDF reflects what's currently on screen (session scores + meta).
    pdf_rec = {
        "student_id": sid,
        "scores": {k: v for k, v in scores.items() if v},
        "date": date_val.strip(),
        "assessor": assessor_val.strip(),
        "notes": notes_val.strip(),
    }

    save_col, dl_col = st.columns(2)
    with save_col:
        if st.button(
            "💾 Save Quick Assessment", type="primary", width="stretch",
            key=f"efl_qa_save_{sid}",
        ):
            rec.update(pdf_rec)
            save_efl_qa_for_student(sid, rec)
            st.toast("Quick Assessment saved.")
            st.rerun()
    with dl_col:
        st.download_button(
            "📄 Download QA PDF",
            data=build_efl_qa_pdf(s, pdf_rec),
            file_name=(
                f"efl_quick_assessment_"
                f"{(s.get('name','') or 'learner').replace(' ', '_')}"
                f"_{date.today().isoformat()}.pdf"
            ),
            mime="application/pdf",
            width="stretch",
            key=f"efl_qa_pdf_{sid}",
        )


# ── EFL Complete Assessment ───────────────────────────────────────────────────
# Full EFL skill inventory organized by domain. Each skill row carries five
# status buttons: MM (Marked Mastered, user), QA (auto — flagged by a Quick
# Assessment answer), ID (user — identify for further assessment), N/A (user —
# not applicable), IA (auto — teaching has started). MM/ID/N/A are persisted
# per student; QA/IA are derived at render time.
EFL_COMPLETE_FILE = os.path.join(DATA_DIR, "efl_complete.json")

# Display order of the status buttons. ``auto`` buttons are read-only.
EFL_COMPLETE_BUTTONS = [
    {"key": "mm", "label": "MM", "auto": False,
     "help": "Marked Mastered — mark this skill as mastered."},
    {"key": "qa", "label": "QA", "auto": True,
     "help": "Highlighted when a Quick Assessment answer flags this skill as "
             "possibly needing further assessment."},
    {"key": "id", "label": "ID", "auto": False,
     "help": "Identify this skill for further assessment."},
    {"key": "na", "label": "N/A", "auto": False,
     "help": "Mark this skill as not applicable to this learner."},
    {"key": "ia", "label": "IA", "auto": True,
     "help": "Auto-selected when skill teaching has started."},
]
EFL_COMPLETE_USER_KEYS = [b["key"] for b in EFL_COMPLETE_BUTTONS if not b["auto"]]

# Domains and their skills. Codes preserved exactly as on the EFL form
# (note intentional gaps, e.g. R5 is omitted). More domains appended as added.
EFL_COMPLETE_DOMAINS = [
    {"code": "D1", "name": "Requests and Related Listener Responses",
     "prefix": "R", "items": [
         ("R 1", "Determining Learner Interests"),
         ("R 2", "Indicates Interest in Items & Activities From R1"),
         ("R 3", "Indicates Interest in Items & Activities from R2"),
         ("R 4", "Instructs the Learner to Mand for Items & Activities from R3"),
         ("R 6", "Determining Preferred Items & Activities"),
         ("R 7", "Requests Highly Preferred Items or Activities Frequently "
                 "Available"),
         ("R 8", "Requests to Entertain Themselves or Reduce Anxiety"),
         ("R 9", "Waits After Making Request for Items in R7 and R8"),
         ("R 10", "Accepts Removal of 10 Items or Activities from R7 & R8 by "
                  "Person in Authority"),
         ("R 11", "Completes 10 Consecutive, Brief, Previously Acquired Tasks"),
         ("R 12", "Shares or Takes Turns with Items and Activities in R7 and R8"),
         ("R 13", "Transitions from Preferred Items & Activities to Required "
                  "Tasks"),
         ("R 14", "Requests Removal of or Less Intensity of 1-4 Situations"),
         ("R 15", "'Accepts No' After Requesting Item and Activities Often "
                  "Honored"),
         ("R 16", "'Accepts No' After Requesting Dangerous Items or Activities"),
         ("R 17", "Requests Forcefully and Repeatedly for Someone to Stop"),
         ("R 18", "Requests Help In a Threatening or Dangerous Situation"),
         ("R 19", "Requests Audience and Item or Activity in R7 and R8"),
         ("R 20", "Requests Communication Board, Book, or Device"),
         ("R 21", "Politely Refuses Access to Preferred Items or Activities"),
     ]},
    {"code": "D2", "name": "Listener Responses, Names and Description",
     "prefix": "LR, LRND", "items": [
         ("LR 1", "Holds and Maintains Contact with Someone's Hand When "
                  "Directed"),
         ("LR 2", "Moves Toward and Stands or Sits Next to Someone when "
                  "Directed"),
         ("LR 3", "Moves Toward and Stand or Remains in Line When Directed"),
         ("LR 4", "Waits Within Arms Length of Someone or Waits in Line when "
                  "Directed"),
         ("LR 5", "Stands Up, Sits Down, Folds Hands, etc. when Directed"),
         ("LR 6", "Moves From One Locations to Another when Directed"),
         ("LR 7", "Waits at a Location when Directed"),
         ("LR 8", "Moves to and Remains in Designated Area when Directed"),
         ("LR 9", "Stops Moving or Engaging in a Dangerous Activity when "
                  "Directed"),
         ("LR 10", "Turns Toward Others when Name is Called and Makes Responses "
                   "from LR1-9"),
         ("LR 11", "Fastens Seat Belt and Remains in Seat Belt when Directed"),
     ]},
    {"code": "D4", "name": "Daily Living and Related Skills", "prefix": "DLS",
     "items": [
         ("DLS_EDF 1", "Consumes Thick or Thickened Liquids Orally"),
         ("DLS_SLP 1", "Goes to Sleep at Bedtime"),
         ("DLS_MT 1", "Transported with a Hoist (MR)"),
         ("DLS_AHS 1", "Does not Pick up Knives, etc Without Supervision or "
                       "Training"),
         ("DLS_HS 1", "Performs Required Exercises or Therapeutic Activities "
                      "(MR)"),
         ("DLS_EDF 2", "Consumes Three Thin Liquids Orally, Including Water"),
         ("DLS_SLP 2", "Sleeps Through the Night"),
         ("DLS_MT 2", "Transports Self to Toilet (MR)"),
         ("DLS_AHS 2", "Does not Take Medications Without Supervision or "
                       "Training"),
         ("DLS_HS 2", "Looks Both Ways, Waits for Traffic to Clear, Crosses "
                      "Street quickly (MR)"),
         ("DLS_EDF 3", "Consumes Three Soft Foods"),
         ("DLS_MT 3", "Transports Self From Bed or Chair to Wheelchair or MOVE "
                      "Device with a Return (MR)"),
         ("DLS_AHS 3", "Does not Use Cleaning Fluids without Supervision or "
                       "Training"),
         ("DLS_HS 3", "Wears External Clothing Appropriate to Weather "
                      "Conditions (MR)"),
         ("DLS_EDF 4", "Chews Three Soft Foods"),
         ("DLS_MT 4", "Transports Self From Bed or Chair to Walker or Gait "
                      "Trainer with a Return (MR)"),
         ("DLS_AHS 4", "Does not Touch Insecticides"),
         ("DLS_HS 4", "Fastens and Remains in Seat Belt"),
         ("DLS_EDF 5", "Munches Three Crunchy Foods"),
         ("DLS_MT 5", "Transported in a Wheelchair"),
         ("DLS_AHS 5", "Does not Walk After Dark Without Companion"),
         ("DLS_HS 5", "Attends Medical Appointments"),
         ("DLS_EDF 6", "Chews Three Crunchy Foods"),
         ("DLS_AHS 6", "Does not Walk on Wet Floors"),
         ("DLS_HS 6", "Attends Dental Appointments"),
         ("DLS_EDF 7", "Chews Three Chewy Foods"),
         ("DLS_AHS 7", "Does not Turn On Hot Water Before Cold Water"),
         ("DLS_HS 7", "Attends Therapy Appointments"),
         ("DLS_EDF 8", "Drinks with a Sippy Cup"),
         ("DLS_AHS 8", "Does not Enter Pools, Lakes, etc. Without Supervision"),
         ("DLS_HS 8", "Engages in Safe, Personal, Sexual Behavior in "
                      "Appropriate Setting (MR)"),
         ("DLS_EDF 9", "Drinks from a Cup or Glass"),
         ("DLS_AHS 9", "Does not Touch Matches or Lighters"),
         ("DLS_AHS 10", "Does not Plug In or Touch an Iron"),
         ("DLS_AHS 11", "Does not Pick up Car Keys"),
         ("DLS_AHS 12", "Does not Put Harmful Items in Their Mouth"),
         ("DLS_AHS 13", "Does not Put Anything in Their Eyes, Ears, Rectum, "
                        "etc."),
         ("DLS_AHS 14", "Does not Go into or Across Street Without Supervision"),
         ("DLS_AHS 15", "Does not Talk to, Walk with, Get in Car with or Open "
                        "Door to Strangers"),
     ]},
    {"code": "D6", "name": "Tolerating Skills and Eggshells", "prefix": "T",
     "items": [
         ("T-BHI 1", "The Sight, Sound, or Scent of An Unfamiliar Person"),
         ("T-EDF 1", "A Gastrostomy or Nasogastric Tube"),
         ("T-DM 1", "Medication Hidden in Food"),
         ("T-Slp 1", "Parent's Bed"),
         ("T-Toil 1", "Someone Changing Your Diaper"),
         ("T-PRM 1", "A Bed Chair"),
         ("T-PTA 1", "Glasses or Contact Lenses"),
         ("T-PEMR 1", "A Helmet"),
         ("T-BPH 1", "Someone Washing Your Hands"),
         ("T-DD 1", "Someone Brushing Your Teeth"),
         ("T-BHI 2", "In the Same Room with An Unfamiliar Person"),
         ("T-EDF 2", "A Feeding Pump"),
         ("T-DM 2", "Liquid Medication from an Oral Syringe"),
         ("T-Slp 2", "A Crib"),
         ("T-Toil 2", "Potty Chair or Adapted Toilet"),
         ("T-PRM 2", "A Side Lyer"),
         ("T-PTA 2", "A Hearing Aide or Cochlear Implant"),
         ("T-PEMR 2", "A Face Guard"),
         ("T-BPH 2", "Someone Washing Your Face"),
         ("T-BHI 3", "In Close Physical Proximity to An Unfamiliar Person"),
         ("T-EDF 3", "Thickened Liquids"),
         ("T-DM 3", "Liquid Medication from a Spoon"),
         ("T-Slp 3", "Own Bed"),
         ("T-Toil 3", "Toilet"),
         ("T-PRM 3", "A Corner Chair"),
         ("T-PTA 3", "A Wheelchair"),
         ("T-PEMR 3", "Padded Arm Guards"),
         ("T-BPH 3", "Someone Washing Your Ears"),
         ("T-BHI 4", "Demonstration Prompts"),
         ("T-EDF 4", "Liquids"),
         ("T-DM 4", "Pill or Vitamins"),
         ("T-Slp 4", "Pajamas"),
         ("T-Toil 4", "Catheter"),
         ("T-PRM 4", "A Prone to Supine Stander"),
         ("T-PTA 4", "A Gait Trainer"),
         ("T-PEMR 4", "Padded Gloves or Mitts"),
         ("T-BPH 4", "Someone Shampooing Your Hair"),
         ("T-BHI 5", "Touch, Physical Guidance, or Physical Prompts"),
         ("T-EDF 5", "Baby Food"),
         ("T-DM 5", "Oxygen from a Nasal Tube"),
         ("T-Slp 5", "Light's Off"),
         ("T-Toil 5", "A Colostomy or Ileostomy Bag"),
         ("T-PRM 5", "An Adapted Chair"),
         ("T-PTA 5", "A Walker"),
         ("T-PEMR 5", "Finger Cots"),
         ("T-BPH 5", "Someone Brushing or Combing Your Hair"),
         ("T-EDF 6", "Pureed Foods"),
         ("T-DM 6", "An Inhaler"),
         ("T-PRM 6", "Range of Motion Exercises"),
         ("T-PTA 6", "A Seat Belt"),
         ("T-PEMR 6", "Knee or Elbow Pads"),
         ("T-BPH 6", "A Sponge Bath"),
         ("T-EDF 7", "Soft Foods"),
         ("T-DM 7", "Testing Blood by Pricking a Finger"),
         ("T-PTA 7", "A MOVE Device"),
         ("T-PEMR 7", "A Jumpsuit"),
         ("T-BPH 7", "A Tub Bath"),
         ("T-EDF 8", "Mashed Foods"),
         ("T-DM 8", "Insulin Injection"),
         ("T-PTA 8", "A Helmet"),
         ("T-PEMR 8", "A Posey Vest"),
         ("T-BPH 8", "A Hoist"),
         ("T-EDF 9", "An Adapted Spoon"),
         ("T-DM 9", "Ventilation and Suction"),
         ("T-PTA 9", "AFOs"),
         ("T-PEMR 9", "Arm Splints"),
         ("T-EDF 10", "An Adapted Cup, Bowl, or Plate"),
         ("T-PTA 10", "Splints"),
         ("T-PEMR 10", "A Mat Wrap or Restraint Board"),
         ("T-EDF 11", "Solid Foods"),
         ("T-PTA 11", "Braces"),
     ]},
]

# code -> truthy condition for the QA auto-highlight. Filled in later once the
# Quick-Assessment-to-skill mapping rules are provided.
EFL_COMPLETE_QA_FLAGS: dict[str, bool] = {}


def load_efl_complete() -> list[dict[str, Any]]:
    return _load(EFL_COMPLETE_FILE)


def save_efl_complete(rows): _save(EFL_COMPLETE_FILE, rows)


def efl_complete_for_student(student_id: str) -> dict:
    rows = load_efl_complete()
    rec = next((r for r in rows if r.get("student_id") == student_id), None)
    if rec is None:
        rec = {"student_id": student_id}
    rec.setdefault("skills", {})
    return rec


def save_efl_complete_for_student(student_id: str, record: dict) -> None:
    rows = load_efl_complete()
    for i, r in enumerate(rows):
        if r.get("student_id") == student_id:
            rows[i] = record
            break
    else:
        rows.append(record)
    save_efl_complete(rows)


def _efl_complete_qa_flag(sid: str, code: str) -> bool:
    """Whether the QA auto-highlight is on for this skill (mapping TBD)."""
    return bool(EFL_COMPLETE_QA_FLAGS.get(code))


def _efl_complete_ia_flag(sid: str, code: str, all_targets: list) -> bool:
    """IA (teaching started) — true if any of the learner's targets is linked
    to this EFL skill code."""
    return any(
        t.get("student_id") == sid and t.get("efl_skill_code") == code
        for t in all_targets
    )


def _efl_complete_auto(sid: str, code: str, all_targets: list) -> dict:
    return {
        "qa": _efl_complete_qa_flag(sid, code),
        "ia": _efl_complete_ia_flag(sid, code, all_targets),
    }


def build_efl_complete_pdf(student: dict, sid: str, flags: dict) -> bytes:
    name = student.get("name", "")
    pdf = _pdf_init(f"EFL Complete Assessment · {name}")
    avail = pdf.w - pdf.l_margin - pdf.r_margin
    all_targets = load_targets()

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(28, 25, 23)
    pdf.cell(0, 7, "THE ESSENTIAL FOR LIVING COMPLETE ASSESSMENT",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)
    _pdf_kv_row(pdf, "Learner", name or "-")
    _pdf_kv_row(pdf, "Generated", _fmt_date(date.today().isoformat()))
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(120, 113, 108)
    pdf.cell(0, 4.2,
             "MM Marked Mastered · QA flagged by Quick Assessment · "
             "ID identify for assessment · N/A not applicable · IA teaching "
             "started", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1.5)

    cell_w, gap, box_h = 9.5, 1.6, 5.4
    n = len(EFL_COMPLETE_BUTTONS)
    cells_w = n * cell_w + (n - 1) * gap
    label_w = avail - cells_w

    for domain in EFL_COMPLETE_DOMAINS:
        if pdf.get_y() + 10 > pdf.h - pdf.b_margin:
            pdf.add_page()
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(122, 30, 40)
        pdf.multi_cell(avail, 5,
                       _pdf_safe(f"{domain['code']} — {domain['name']} "
                                 f"({domain['prefix']})"))
        # Column headers above the button cells.
        y = pdf.get_y()
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(120, 113, 108)
        x = pdf.l_margin + label_w
        for btn in EFL_COMPLETE_BUTTONS:
            pdf.set_xy(x, y)
            pdf.cell(cell_w, 3.4, btn["label"], align="C")
            x += cell_w + gap
        pdf.set_y(y + 3.8)

        for code, desc in domain["items"]:
            if pdf.get_y() + box_h + 1 > pdf.h - pdf.b_margin:
                pdf.add_page()
            cur = flags.get(code, {})
            auto = _efl_complete_auto(sid, code, all_targets)
            y = pdf.get_y()
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(28, 25, 23)
            pdf.set_xy(pdf.l_margin, y)
            pdf.multi_cell(label_w - 1, box_h, _pdf_safe(f"{code}  {desc}"),
                           max_line_height=2.7)
            row_end_y = pdf.get_y()
            x = pdf.l_margin + label_w
            for btn in EFL_COMPLETE_BUTTONS:
                k = btn["key"]
                on = auto.get(k, False) if btn["auto"] else bool(cur.get(k))
                if on:
                    pdf.set_fill_color(37, 99, 235)
                    pdf.set_draw_color(37, 99, 235)
                    pdf.rect(x, y + 0.2, cell_w, box_h - 0.4, style="DF")
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Helvetica", "B", 6.5)
                else:
                    pdf.set_draw_color(185, 185, 185)
                    pdf.rect(x, y + 0.2, cell_w, box_h - 0.4, style="D")
                    pdf.set_text_color(150, 150, 150)
                    pdf.set_font("Helvetica", "", 6.5)
                pdf.set_xy(x, y + 0.2)
                pdf.cell(cell_w, box_h - 0.4, btn["label"], align="C")
                x += cell_w + gap
            pdf.set_y(max(y + box_h, row_end_y) + 0.8)

    return _pdf_bytes(pdf)


def _efl_complete_section(sid: str, s: dict) -> None:
    """Interactive EFL Complete Assessment (skills by domain), per student."""
    st.divider()
    st.subheader("Complete Assessment")
    if not EFL_COMPLETE_DOMAINS:
        st.info("No Complete Assessment domains defined yet.")
        return
    st.caption(
        "Full EFL skill inventory by domain. **MM** mark mastered · **QA** "
        "(auto) flagged by the Quick Assessment · **ID** identify for further "
        "assessment · **N/A** not applicable · **IA** (auto) teaching started. "
        "Hover a button for details. Click **Save** when done."
    )

    rec = efl_complete_for_student(sid)
    ss_key = f"_efl_complete_flags_{sid}"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = {
            c: dict(v) for c, v in rec.get("skills", {}).items()
        }
    flags = st.session_state[ss_key]
    all_targets = load_targets()

    dom_codes = [d["code"] for d in EFL_COMPLETE_DOMAINS]
    dom_by_code = {d["code"]: d for d in EFL_COMPLETE_DOMAINS}
    dom = st.selectbox(
        "Domain", options=dom_codes,
        format_func=lambda c: f"{c} — {dom_by_code[c]['name']} "
                              f"({dom_by_code[c]['prefix']})",
        key=f"efl_cmp_dom_{sid}",
    )
    domain = dom_by_code[dom]

    for code, desc in domain["items"]:
        cur = flags.setdefault(code, {})
        cols = st.columns([0.50, 0.10, 0.10, 0.10, 0.10, 0.10])
        cols[0].markdown(f"**{code}** · {desc}")
        auto = _efl_complete_auto(sid, code, all_targets)
        for i, btn in enumerate(EFL_COMPLETE_BUTTONS):
            k = btn["key"]
            with cols[i + 1]:
                if btn["auto"]:
                    on = auto.get(k, False)
                    st.button(
                        btn["label"], key=f"efl_cmp_{sid}_{code}_{k}",
                        type="primary" if on else "secondary",
                        disabled=True, width="stretch", help=btn["help"],
                    )
                else:
                    on = bool(cur.get(k))
                    if st.button(
                        btn["label"], key=f"efl_cmp_{sid}_{code}_{k}",
                        type="primary" if on else "secondary",
                        width="stretch", help=btn["help"],
                    ):
                        cur[k] = not on
                        st.rerun()

    # Per-domain progress.
    dom_codes_set = {c for c, _ in domain["items"]}
    marked = sum(
        1 for c in dom_codes_set
        if any(flags.get(c, {}).get(k) for k in EFL_COMPLETE_USER_KEYS)
    )
    st.caption(f"{marked} / {len(dom_codes_set)} skills marked in **{dom}**.")

    save_col, dl_col = st.columns(2)
    with save_col:
        if st.button(
            "💾 Save Complete Assessment", type="primary", width="stretch",
            key=f"efl_cmp_save_{sid}",
        ):
            rec["skills"] = {
                c: {k: True for k in EFL_COMPLETE_USER_KEYS if v.get(k)}
                for c, v in flags.items()
                if any(v.get(k) for k in EFL_COMPLETE_USER_KEYS)
            }
            save_efl_complete_for_student(sid, rec)
            st.toast("Complete Assessment saved.")
            st.rerun()
    with dl_col:
        st.download_button(
            "📄 Download Complete Assessment PDF",
            data=build_efl_complete_pdf(s, sid, flags),
            file_name=(
                f"efl_complete_assessment_"
                f"{(s.get('name','') or 'learner').replace(' ', '_')}"
                f"_{date.today().isoformat()}.pdf"
            ),
            mime="application/pdf",
            width="stretch",
            key=f"efl_cmp_pdf_{sid}",
        )


def page_efl_assessment():
    students = load_students()
    if not students:
        st.header("EFL Assessment")
        st.info("Add a student on **Student Home** first.")
        return

    sid = current_sid(students)
    s = next((x for x in students if x["id"] == sid), {})
    st.header(f"EFL Assessment · {s.get('name','')}")

    saved_msg = st.session_state.pop("_efl_saved_msg", None)
    if saved_msg:
        st.markdown(
            f'<div class="cpt-save-ribbon">✓ {saved_msg}</div>',
            unsafe_allow_html=True,
        )

    st.caption(
        "Freestanding scoring grid for the *Essential for Living* curriculum — "
        "starting with the 8 Must-Have skills. Pick a status for each skill on up "
        "to four test administrations and record the date and tester for each."
    )

    _efl_must_have_overview()

    rec = efl_for_student(sid)
    ever = st.session_state.get("efl_ver", 0)

    # ── Student info ────────────────────────────────────────────────────────
    info_dob = s.get("dob", "")
    info_age = ""
    try:
        if info_dob:
            dob_d = date.fromisoformat(info_dob)
            today = date.today()
            yrs = (today - dob_d).days / 365.25
            info_age = f"{yrs:.1f} yrs ({(today - dob_d).days} days)"
    except Exception:
        info_age = ""
    info_cols = st.columns(3)
    with info_cols[0]:
        st.metric("Child's name", s.get("name", ""))
    with info_cols[1]:
        st.metric("Date of birth", _fmt_date(info_dob) or "—")
    with info_cols[2]:
        st.metric("Current age", info_age or "—")

    # ── Test administrations (date + tester per test) ──────────────────────
    st.divider()
    st.subheader("Test administrations")
    test_meta_rows = []
    for n in EFL_TESTS:
        meta = rec["tests"].get(str(n), {})
        test_meta_rows.append({
            "Test": f"{n}st" if n == 1 else f"{n}nd" if n == 2 else f"{n}rd" if n == 3 else f"{n}th",
            "Date": meta.get("date", ""),
            "Tester": meta.get("tester", ""),
            "Notes": meta.get("notes", ""),
        })
    meta_edited = st.data_editor(
        pd.DataFrame(test_meta_rows),
        width="stretch",
        hide_index=True,
        key=f"efl_meta_{ever}",
        column_config={
            "Test": st.column_config.TextColumn(disabled=True),
            "Date": st.column_config.TextColumn(
                help="ISO date YYYY-MM-DD (storage) — leave blank if the test wasn't run.",
            ),
            "Tester": st.column_config.TextColumn(),
            "Notes": st.column_config.TextColumn(),
        },
    )

    st.caption(
        "Edit a test's date / tester / notes inline above, or skill statuses "
        "in the grid below — then **Save**. To wipe one test entirely, use:"
    )
    clear_cols = st.columns(len(EFL_TESTS))
    for i, n in enumerate(EFL_TESTS):
        n_set = sum(
            1 for v in rec["statuses"].get(str(n), {}).values()
            if v in ("Mastered", "Emerging", "Not yet")
        )
        meta_filled = any(
            (rec["tests"].get(str(n), {}) or {}).get(k, "").strip()
            for k in ("date", "tester", "notes")
        )
        has_data = n_set > 0 or meta_filled
        pending_key = f"_efl_clear_pending_{sid}_{n}"
        with clear_cols[i]:
            if st.session_state.get(pending_key):
                st.warning(f"Clear Test {n}?  \n_{n_set} response(s) + meta will be wiped._")
                yc, nc = st.columns(2)
                with yc:
                    if st.button(
                        f"Yes, clear",
                        key=f"efl_clear_yes_{sid}_{n}_{ever}",
                        type="primary", width="stretch",
                    ):
                        rec["tests"][str(n)] = {"date": "", "tester": "", "notes": ""}
                        rec["statuses"][str(n)] = {}
                        save_efl_for_student(sid, rec)
                        st.session_state.pop(pending_key, None)
                        st.session_state["efl_ver"] = ever + 1
                        st.session_state["_efl_saved_msg"] = (
                            f"Test {n} cleared for {s.get('name','')}."
                        )
                        st.toast(f"Test {n} cleared.")
                        st.rerun()
                with nc:
                    if st.button(
                        "Cancel",
                        key=f"efl_clear_no_{sid}_{n}_{ever}",
                        width="stretch",
                    ):
                        st.session_state.pop(pending_key, None)
                        st.rerun()
            else:
                if st.button(
                    f"🗑 Clear Test {n}",
                    key=f"efl_clear_btn_{sid}_{n}_{ever}",
                    disabled=not has_data,
                    width="stretch",
                    help=(
                        f"Wipe Test {n}'s date/tester/notes and all skill "
                        "statuses for this student."
                        if has_data else
                        f"Test {n} has no data to clear."
                    ),
                ):
                    st.session_state[pending_key] = True
                    st.rerun()

    # ── Skill grid grouped by category (tabs) ───────────────────────────────
    st.subheader("Skills")
    # Prefer file-based catalog (parsed from task_analyses/*.md). Fall back to
    # the hardcoded EFL_SKILLS if the directory is missing or empty.
    from collections import OrderedDict
    file_catalog = load_efl_catalog_from_files()
    catalog_by_code: dict[str, dict] = {}
    cats: dict[str, list[tuple[str, str]]] = OrderedDict()
    if file_catalog:
        for skill in file_catalog:
            cats.setdefault(skill["category"], []).append((skill["code"], skill["name"]))
            catalog_by_code[skill["code"]] = skill
        enabled_labels = ", ".join(
            EFL_DOMAIN_LABELS.get(d, d) for d in EFL_ENABLED_DOMAINS
        )
        st.caption(
            f"Loaded **{len(file_catalog)}** skills from "
            f"`task_analyses/` — enabled domain(s): **{enabled_labels}**. "
            "Pick a row's status; expand a skill below to read its full "
            "task analysis."
        )
    else:
        for cat, code, name in EFL_SKILLS:
            cats.setdefault(cat, []).append((code, name))
        st.caption(
            f"Using the hardcoded starter catalog ({len(EFL_SKILLS)} skills) — "
            f"no markdown task analyses found at `{TASK_ANALYSES_ROOT}`."
        )

    # Load targets once so the live column can reflect each skill's actual
    # cold-probe mastery from linked targets.
    all_targets_now = load_targets()

    column_config = {
        "Code": st.column_config.TextColumn(width="small", disabled=True),
        "Skill": st.column_config.TextColumn(disabled=True),
        "Live (from probes)": st.column_config.TextColumn(disabled=True),
    }
    for n in EFL_TESTS:
        column_config[f"Test {n}"] = st.column_config.SelectboxColumn(
            f"Test {n}",
            options=EFL_STATUS_OPTIONS,
            required=False,
        )

    cat_names = list(cats.keys())
    tab_labels = [f"{c} ({len(cats[c])})" for c in cat_names]
    tabs = st.tabs(tab_labels)
    all_edits: dict[str, pd.DataFrame] = {}
    for tab, cat in zip(tabs, cat_names):
        with tab:
            rows = []
            for code, name in cats[cat]:
                row = {"Code": code, "Skill": name}
                live_label, live_summary = _derive_efl_live_status(
                    sid, code, all_targets_now,
                )
                if live_label == "—":
                    row["Live (from probes)"] = "—"
                else:
                    row["Live (from probes)"] = f"{live_label}  ·  {live_summary}"
                for n in EFL_TESTS:
                    current = rec["statuses"].get(str(n), {}).get(code, "—")
                    row[f"Test {n}"] = current if current in EFL_STATUS_OPTIONS else "—"
                rows.append(row)
            edited = st.data_editor(
                pd.DataFrame(rows),
                width="stretch",
                hide_index=True,
                key=f"efl_skills_{cat}_{ever}",
                column_config=column_config,
            )
            all_edits[cat] = edited

    # ── Snapshot summary ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Snapshot")
    all_codes = [code for items in cats.values() for code, _ in items]
    total = len(all_codes)

    # Live derived from cold-probe data
    live_labels = {
        c: _derive_efl_live_status(sid, c, all_targets_now)[0]
        for c in all_codes
    }
    live_counts = {
        s: sum(1 for v in live_labels.values() if v == s)
        for s in ["Mastered", "Emerging", "Not yet"]
    }
    live_no_link = sum(1 for v in live_labels.values() if v == "—")

    snap_cols = st.columns(5)
    with snap_cols[0]:
        st.metric(
            "Live (from probes)",
            f"{live_counts['Mastered']} / {total}",
            f"M {live_counts['Mastered']} · E {live_counts['Emerging']} · "
            f"N {live_counts['Not yet']} · — {live_no_link}",
            delta_color="off",
        )
    for i, n in enumerate(EFL_TESTS):
        statuses = rec["statuses"].get(str(n), {})
        relevant = {c: statuses.get(c, "—") for c in all_codes}
        counts = {
            s: sum(1 for v in relevant.values() if v == s)
            for s in ["Mastered", "Emerging", "Not yet"]
        }
        with snap_cols[i + 1]:
            st.metric(
                f"Test {n}",
                f"{counts['Mastered']} / {total}",
                f"M {counts['Mastered']} · E {counts['Emerging']} · "
                f"N {counts['Not yet']}",
                delta_color="off",
            )

    with st.expander("By category"):
        cat_rows = []
        for cat, items in cats.items():
            cat_codes = [c for c, _ in items]
            n_live_mastered = sum(
                1 for c in cat_codes if live_labels.get(c) == "Mastered"
            )
            row = {
                "Category": cat,
                "Skills": len(cat_codes),
                "Live Mastered": f"{n_live_mastered} / {len(cat_codes)}",
            }
            for n in EFL_TESTS:
                statuses = rec["statuses"].get(str(n), {})
                n_mastered = sum(1 for c in cat_codes if statuses.get(c) == "Mastered")
                row[f"Test {n} Mastered"] = f"{n_mastered} / {len(cat_codes)}"
            cat_rows.append(row)
        st.dataframe(pd.DataFrame(cat_rows), width="stretch", hide_index=True)

    # ── Task analysis viewer ───────────────────────────────────────────────
    if catalog_by_code:
        st.divider()
        st.subheader("Task analysis")
        ordered_codes = [c for items in cats.values() for c, _ in items]
        pick_code = st.selectbox(
            "Skill",
            options=ordered_codes,
            format_func=lambda c: f"{c} — {catalog_by_code[c]['name']}",
            key=f"efl_ta_pick_{ever}",
        )
        skill = catalog_by_code.get(pick_code, {})
        sections = skill.get("sections", {})
        if not sections:
            st.caption("No parsed sections for this skill.")
        else:
            st.caption(f"Source: `{os.path.relpath(skill.get('path', ''))}`")
            for section_title, body in sections.items():
                with st.expander(section_title):
                    st.markdown(body)

        # ── Track steps as cold-probe targets ──────────────────────────────
        st.markdown("---")
        st.markdown("**📝 Track learner-behavior steps as cold-probe targets**")
        steps = _extract_efl_steps(sections)
        if not steps:
            st.caption(
                "No learner-behavior steps in this skill — it documents "
                "instructor procedure only (e.g., preference assessment). "
                "Nothing to track here."
            )
        else:
            # Derive the domain dir from the file path → default operant.
            sp = skill.get("path", "") or ""
            domain_dir = ""
            for d in EFL_ENABLED_DOMAINS:
                if f"/{d}/" in sp.replace(os.sep, "/"):
                    domain_dir = d
                    break
            default_operant = EFL_DEFAULT_OPERANT_BY_DOMAIN.get(domain_dir, "Other")

            linked = targets_linked_to_efl(sid, pick_code, all_targets_now)
            linked_by_desc = {(t.get("description") or "").strip(): t for t in linked}

            with st.form(key=f"efl_track_{pick_code}_{ever}"):
                c1, c2 = st.columns(2)
                with c1:
                    op_idx = DOMAINS.index(default_operant) if default_operant in DOMAINS else 0
                    op_choice = st.selectbox(
                        "Operant",
                        options=DOMAINS,
                        index=op_idx,
                        key=f"efl_track_op_{pick_code}_{ever}",
                    )
                with c2:
                    list_choice = st.text_input(
                        "Skill list",
                        value=f"EFL: {pick_code}",
                        key=f"efl_track_list_{pick_code}_{ever}",
                    )
                mastery_n_choice = st.number_input(
                    "Mastery N (consecutive Y to auto-master)",
                    min_value=1, max_value=10, value=3, step=1,
                    key=f"efl_track_n_{pick_code}_{ever}",
                )

                st.caption("Pick steps to add as cold-probe targets.")
                pick_flags: dict[int, bool] = {}
                for i, step_text in enumerate(steps, start=1):
                    existing = linked_by_desc.get(step_text)
                    if existing:
                        status = existing.get("status", "")
                        md = existing.get("mastered_date", "")
                        if md:
                            try:
                                md_disp = datetime.fromisoformat(md).strftime("%m/%d/%Y")
                            except Exception:
                                md_disp = md
                            tag = f"✓ {status} ({md_disp})"
                        else:
                            tag = f"✓ {status}"
                        st.markdown(f"- **{i}.** {step_text}  ·  _{tag}_")
                        pick_flags[i] = False
                    else:
                        pick_flags[i] = st.checkbox(
                            f"{i}. {step_text}",
                            key=f"efl_track_pick_{pick_code}_{i}_{ever}",
                        )

                submitted = st.form_submit_button(
                    "➕ Add selected steps as cold-probe targets",
                    type="primary",
                    width="stretch",
                )
                if submitted:
                    chosen = [steps[i - 1] for i, v in pick_flags.items() if v]
                    if not chosen:
                        st.warning("No new steps selected.")
                    else:
                        targets_now = load_targets()
                        for line in chosen:
                            targets_now.append({
                                "id": new_id(),
                                "student_id": sid,
                                "description": line,
                                "domain": op_choice,
                                "skill_list": list_choice.strip(),
                                "mastery_n": int(mastery_n_choice),
                                "mastery_criterion": "",
                                "status": "In Acquisition",
                                "mastered_date": "",
                                "efl_skill_code": pick_code,
                            })
                        save_targets(targets_now)
                        n_label = "target" if len(chosen) == 1 else "targets"
                        st.session_state["_efl_saved_msg"] = (
                            f"✓ Added {len(chosen)} {n_label} from **{pick_code}** "
                            f"to **{op_choice}** → {list_choice.strip()}."
                        )
                        st.toast(f"Added {len(chosen)} {n_label}.")
                        st.session_state["efl_ver"] = ever + 1
                        st.rerun()

    # ── Save ────────────────────────────────────────────────────────────────
    st.divider()
    if st.button(
        "💾 Save EFL assessment", type="primary", width="stretch",
        key=f"efl_save_{ever}",
    ):
        # Merge meta edits back.
        meta_records = meta_edited.to_dict("records")
        for i, n in enumerate(EFL_TESTS):
            m = meta_records[i] if i < len(meta_records) else {}
            rec["tests"][str(n)] = {
                "date": str(m.get("Date", "") or "").strip(),
                "tester": str(m.get("Tester", "") or "").strip(),
                "notes": str(m.get("Notes", "") or "").strip(),
            }
        # Merge skill statuses back from every category tab.
        for cat, edited in all_edits.items():
            for row in edited.to_dict("records"):
                code = row.get("Code", "")
                if not code:
                    continue
                for n in EFL_TESTS:
                    v = row.get(f"Test {n}", "—")
                    if v not in EFL_STATUS_OPTIONS:
                        v = "—"
                    rec["statuses"].setdefault(str(n), {})[code] = v
        save_efl_for_student(sid, rec)
        n_set = sum(
            1 for n in EFL_TESTS
            for v in rec["statuses"].get(str(n), {}).values()
            if v in ("Mastered", "Emerging", "Not yet")
        )
        st.session_state["efl_ver"] = ever + 1
        st.session_state["_efl_saved_msg"] = (
            f"EFL assessment saved for {s.get('name','')} — "
            f"{n_set} response(s) recorded."
        )
        st.toast("EFL assessment saved.")
        st.rerun()

    # ── Quick Assessment (separate persisted record) ────────────────────────
    _efl_qa_section(sid, s)

    # ── Complete Assessment (separate persisted record) ─────────────────────
    _efl_complete_section(sid, s)


# ── VB-MAPP Milestones Assessment ─────────────────────────────────────────────
VBMAPP_FILE = os.path.join(DATA_DIR, "vbmapp_assessments.json")
# The 170 milestones live in the sibling vbmapp_curriculum package (one dir up).
VBMAPP_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vbmapp_curriculum", "data", "milestones.json",
)
VBMAPP_STATUS_OPTIONS = ["—", "0", "½", "1"]
VBMAPP_SCORE_VALUE = {"—": None, "0": 0.0, "½": 0.5, "1": 1.0}
VBMAPP_TESTS = [1, 2, 3, 4]
VBMAPP_LEVELS = [1, 2, 3]
# Max points per level on the Milestones Master Scoring Form.
VBMAPP_LEVEL_MAX = {1: 45, 2: 60, 3: 65}

# VB-MAPP skill area → Repertiores operant, used to pre-fill the operant when
# pushing a milestone into a student's cold-probe program.
VBMAPP_OPERANT_BY_AREA = {
    "Mand": "Mand", "Tact": "Tact", "Listener": "Listener",
    "VP-MTS": "Visual Performance", "Play": "Play", "Social": "Social",
    "Imitation": "Imitation", "Echoic": "Echoic", "Vocal": "Echoic",
    "LRFFC": "Listener", "Intraverbal": "Intraverbal", "Group": "Other",
    "Linguistics": "Tact", "Reading": "Academics", "Writing": "Academics",
    "Math": "Academics",
}


def load_vbmapp_catalog() -> list[dict]:
    """Load the 170 milestones from vbmapp_curriculum's data file (file order)."""
    try:
        with open(VBMAPP_DATA_FILE, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return []
    return raw.get("milestones", [])


def load_vbmapp() -> list[dict[str, Any]]:
    return _load(VBMAPP_FILE)


def save_vbmapp(rows): _save(VBMAPP_FILE, rows)


def vbmapp_for_student(student_id: str) -> dict:
    """Return the student's VB-MAPP record (creates an empty shell if absent).

    Shape mirrors the EFL record:
      {
        "student_id": str,
        "tests":    {1: {"date","tester","notes"}, ... 4},
        "statuses": {1: {milestone_code: "—"/"0"/"½"/"1"}, ... 4},
      }
    """
    rows = load_vbmapp()
    for r in rows:
        if r.get("student_id") == student_id:
            r.setdefault("tests", {})
            r.setdefault("statuses", {})
            for n in VBMAPP_TESTS:
                r["tests"].setdefault(str(n), {"date": "", "tester": "", "notes": ""})
                r["statuses"].setdefault(str(n), {})
            return r
    rec = {
        "student_id": student_id,
        "tests": {str(n): {"date": "", "tester": "", "notes": ""} for n in VBMAPP_TESTS},
        "statuses": {str(n): {} for n in VBMAPP_TESTS},
    }
    rows.append(rec)
    save_vbmapp(rows)
    return rec


def save_vbmapp_for_student(student_id: str, record: dict) -> None:
    rows = load_vbmapp()
    found = False
    for i, r in enumerate(rows):
        if r.get("student_id") == student_id:
            rows[i] = record
            found = True
            break
    if not found:
        rows.append(record)
    save_vbmapp(rows)


def targets_linked_to_vbmapp(
    student_id: str, code: str, all_targets: list[dict],
) -> list[dict]:
    return [
        t for t in all_targets
        if t.get("student_id") == student_id
        and t.get("vbmapp_milestone_code") == code
    ]


def _derive_vbmapp_live_status(
    student_id: str, code: str, all_targets: list[dict],
) -> tuple[str, str]:
    """Live milestone score from linked cold-probe targets.

    Returns ``(label, summary)`` where label is ``1`` (all linked targets
    mastered), ``½`` (some mastered / in progress), ``0`` (none), or ``—``
    (no targets linked yet).
    """
    linked = targets_linked_to_vbmapp(student_id, code, all_targets)
    if not linked:
        return ("—", "no targets linked")
    n_total = len(linked)
    n_mastered = sum(1 for t in linked if t.get("status") == "Mastered")
    n_active = sum(
        1 for t in linked
        if t.get("status") in ("In Acquisition", "Maintenance")
    )
    summary = f"{n_mastered} / {n_total} mastered"
    if n_mastered == n_total:
        return ("1", summary)
    if n_mastered > 0 or n_active > 0:
        return ("½", summary)
    return ("0", summary)


def _vbmapp_points(statuses_for_test: dict, codes: list[str]) -> float:
    """Sum of 0/0.5/1 point values for the given codes in one test."""
    total = 0.0
    for c in codes:
        v = VBMAPP_SCORE_VALUE.get(statuses_for_test.get(c, "—"))
        if v:
            total += v
    return total


def page_vbmapp_assessment():
    students = load_students()
    if not students:
        st.header("VB-MAPP Assessment")
        st.info("Add a student on **Student Home** first.")
        return

    sid = current_sid(students)
    s = next((x for x in students if x["id"] == sid), {})
    st.header(f"VB-MAPP Milestones · {s.get('name','')}")

    saved_msg = st.session_state.pop("_vbmapp_saved_msg", None)
    if saved_msg:
        st.markdown(
            f'<div class="cpt-save-ribbon">✓ {saved_msg}</div>',
            unsafe_allow_html=True,
        )

    catalog = load_vbmapp_catalog()
    if not catalog:
        st.error(
            "Couldn't load the milestone catalog. Expected it at "
            f"`{VBMAPP_DATA_FILE}` (from the vbmapp_curriculum package)."
        )
        return

    st.caption(
        "VB-MAPP Milestones Assessment (Sundberg, 2008) — 170 milestones across "
        "3 levels × 16 skill areas. Score each **0 / ½ / 1** on up to four test "
        "administrations. Library content: `vbmapp_curriculum`."
    )

    rec = vbmapp_for_student(sid)
    ever = st.session_state.get("vbmapp_ver", 0)

    # ── Student info ─────────────────────────────────────────────────────────
    info_dob = s.get("dob", "")
    info_age = ""
    try:
        if info_dob:
            dob_d = date.fromisoformat(info_dob)
            today = date.today()
            yrs = (today - dob_d).days / 365.25
            info_age = f"{yrs:.1f} yrs ({(today - dob_d).days} days)"
    except Exception:
        info_age = ""
    info_cols = st.columns(3)
    info_cols[0].metric("Child's name", s.get("name", ""))
    info_cols[1].metric("Date of birth", _fmt_date(info_dob) or "—")
    info_cols[2].metric("Current age", info_age or "—")

    # ── Test administrations ────────────────────────────────────────────────
    st.divider()
    st.subheader("Test administrations")
    test_meta_rows = []
    for n in VBMAPP_TESTS:
        meta = rec["tests"].get(str(n), {})
        test_meta_rows.append({
            "Test": {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}[n],
            "Date": meta.get("date", ""),
            "Tester": meta.get("tester", ""),
            "Notes": meta.get("notes", ""),
        })
    meta_edited = st.data_editor(
        pd.DataFrame(test_meta_rows),
        width="stretch",
        hide_index=True,
        key=f"vbmapp_meta_{ever}",
        column_config={
            "Test": st.column_config.TextColumn(disabled=True),
            "Date": st.column_config.TextColumn(
                help="ISO date YYYY-MM-DD — leave blank if the test wasn't run.",
            ),
            "Tester": st.column_config.TextColumn(),
            "Notes": st.column_config.TextColumn(),
        },
    )

    st.caption(
        "Edit a test's date / tester / notes inline above, or milestone "
        "scores in the grid below — then **Save**. To wipe one test entirely, use:"
    )
    clear_cols = st.columns(len(VBMAPP_TESTS))
    for i, n in enumerate(VBMAPP_TESTS):
        n_set = sum(
            1 for v in rec["statuses"].get(str(n), {}).values()
            if v in ("0", "½", "1")
        )
        meta_filled = any(
            (rec["tests"].get(str(n), {}) or {}).get(k, "").strip()
            for k in ("date", "tester", "notes")
        )
        has_data = n_set > 0 or meta_filled
        pending_key = f"_vbmapp_clear_pending_{sid}_{n}"
        with clear_cols[i]:
            if st.session_state.get(pending_key):
                st.warning(f"Clear Test {n}?  \n_{n_set} response(s) + meta will be wiped._")
                yc, nc = st.columns(2)
                with yc:
                    if st.button(
                        f"Yes, clear",
                        key=f"vbmapp_clear_yes_{sid}_{n}_{ever}",
                        type="primary", width="stretch",
                    ):
                        rec["tests"][str(n)] = {"date": "", "tester": "", "notes": ""}
                        rec["statuses"][str(n)] = {}
                        save_vbmapp_for_student(sid, rec)
                        st.session_state.pop(pending_key, None)
                        st.session_state["vbmapp_ver"] = ever + 1
                        st.session_state["_vbmapp_saved_msg"] = (
                            f"Test {n} cleared for {s.get('name','')}."
                        )
                        st.toast(f"Test {n} cleared.")
                        st.rerun()
                with nc:
                    if st.button(
                        "Cancel",
                        key=f"vbmapp_clear_no_{sid}_{n}_{ever}",
                        width="stretch",
                    ):
                        st.session_state.pop(pending_key, None)
                        st.rerun()
            else:
                if st.button(
                    f"🗑 Clear Test {n}",
                    key=f"vbmapp_clear_btn_{sid}_{n}_{ever}",
                    disabled=not has_data,
                    width="stretch",
                    help=(
                        f"Wipe Test {n}'s date/tester/notes and all milestone "
                        "scores for this student."
                        if has_data else
                        f"Test {n} has no data to clear."
                    ),
                ):
                    st.session_state[pending_key] = True
                    st.rerun()

    # ── Skill grid grouped by level (tabs) ──────────────────────────────────
    st.subheader("Milestones")
    all_targets_now = load_targets()

    column_config = {
        "Code": st.column_config.TextColumn(width="small", disabled=True),
        "Area": st.column_config.TextColumn(width="small", disabled=True),
        "Skill": st.column_config.TextColumn(disabled=True),
        "Live (from probes)": st.column_config.TextColumn(disabled=True),
    }
    for n in VBMAPP_TESTS:
        column_config[f"Test {n}"] = st.column_config.SelectboxColumn(
            f"Test {n}", options=VBMAPP_STATUS_OPTIONS, required=False,
        )

    by_level = {lvl: [m for m in catalog if m["level"] == lvl] for lvl in VBMAPP_LEVELS}
    tabs = st.tabs([f"Level {lvl} ({len(by_level[lvl])})" for lvl in VBMAPP_LEVELS])
    all_edits: dict[int, pd.DataFrame] = {}
    for tab, lvl in zip(tabs, VBMAPP_LEVELS):
        with tab:
            rows = []
            for m in by_level[lvl]:
                code = m["code"]
                live_label, live_summary = _derive_vbmapp_live_status(
                    sid, code, all_targets_now,
                )
                row = {
                    "Code": m["m_code"],
                    "Area": m["area"],
                    "Skill": m["title"],
                    "Live (from probes)": (
                        "—" if live_label == "—"
                        else f"{live_label}  ·  {live_summary}"
                    ),
                    "_code": code,  # hidden canonical key
                }
                for n in VBMAPP_TESTS:
                    cur = rec["statuses"].get(str(n), {}).get(code, "—")
                    row[f"Test {n}"] = cur if cur in VBMAPP_STATUS_OPTIONS else "—"
                rows.append(row)
            df = pd.DataFrame(rows)
            edited = st.data_editor(
                df,
                width="stretch",
                hide_index=True,
                key=f"vbmapp_skills_{lvl}_{ever}",
                column_config=column_config,
                column_order=["Code", "Area", "Skill", "Live (from probes)"]
                + [f"Test {n}" for n in VBMAPP_TESTS],
            )
            edited["_code"] = df["_code"].values  # data_editor drops hidden col edits
            all_edits[lvl] = edited

    # ── Snapshot (Master Scoring Form rollup) ───────────────────────────────
    st.divider()
    st.subheader("Master Form snapshot")
    codes_by_level = {lvl: [m["code"] for m in by_level[lvl]] for lvl in VBMAPP_LEVELS}
    all_codes = [c for lvl in VBMAPP_LEVELS for c in codes_by_level[lvl]]

    live_labels = {
        c: _derive_vbmapp_live_status(sid, c, all_targets_now)[0] for c in all_codes
    }

    snap_cols = st.columns(5)
    live_points = sum(VBMAPP_SCORE_VALUE.get(v) or 0 for v in live_labels.values())
    snap_cols[0].metric(
        "Live (from probes)", f"{live_points:.1f} / 170",
        "derived from linked cold probes", delta_color="off",
    )
    for i, n in enumerate(VBMAPP_TESTS):
        statuses = rec["statuses"].get(str(n), {})
        pts = _vbmapp_points(statuses, all_codes)
        per_lvl = " · ".join(
            f"L{lvl} {_vbmapp_points(statuses, codes_by_level[lvl]):.0f}/{VBMAPP_LEVEL_MAX[lvl]}"
            for lvl in VBMAPP_LEVELS
        )
        snap_cols[i + 1].metric(f"Test {n}", f"{pts:.1f} / 170", per_lvl, delta_color="off")

    with st.expander("By area"):
        area_rows = []
        areas_seen: list[str] = []
        for m in catalog:
            if m["area_label"] not in areas_seen:
                areas_seen.append(m["area_label"])
        for area_label in areas_seen:
            area_codes = [m["code"] for m in catalog if m["area_label"] == area_label]
            row = {"Area": area_label, "Milestones": len(area_codes)}
            for n in VBMAPP_TESTS:
                statuses = rec["statuses"].get(str(n), {})
                row[f"Test {n} pts"] = f"{_vbmapp_points(statuses, area_codes):.1f}"
            area_rows.append(row)
        st.dataframe(pd.DataFrame(area_rows), width="stretch", hide_index=True)

    # ── Milestone detail + track as cold-probe targets ──────────────────────
    st.divider()
    st.subheader("Milestone detail")
    by_code = {m["code"]: m for m in catalog}
    pick_code = st.selectbox(
        "Milestone",
        options=[m["code"] for m in catalog],
        format_func=lambda c: (
            f"L{by_code[c]['level']} · {by_code[c]['area']} · "
            f"{by_code[c]['m_code']} — {by_code[c]['title'][:60]}"
        ),
        key=f"vbmapp_pick_{ever}",
    )
    m = by_code[pick_code]
    st.markdown(f"**{m['area_label']} · {m['m_code']}** — {m['title']}")
    st.caption(f"Measurement: {m['measure']}  ·  Objective: {m['objective']}")
    st.markdown(f"- ✓ **For 1 point:** {m['score_1']}")
    if m.get("score_half"):
        st.markdown(f"- ½ **For ½ point:** {m['score_half']}")

    st.markdown("---")
    st.markdown("**📝 Track this milestone as a cold-probe target**")
    default_operant = VBMAPP_OPERANT_BY_AREA.get(m["area"], "Other")
    linked = targets_linked_to_vbmapp(sid, pick_code, all_targets_now)
    if linked:
        st.caption(f"Already linked: {len(linked)} cold-probe target(s).")
        for t in linked:
            tag = t.get("status", "")
            st.markdown(f"- {t.get('description','')}  ·  _{tag}_")
    with st.form(key=f"vbmapp_track_{pick_code}_{ever}"):
        c1, c2 = st.columns(2)
        op_idx = DOMAINS.index(default_operant) if default_operant in DOMAINS else 0
        op_choice = c1.selectbox(
            "Operant", options=DOMAINS, index=op_idx,
            key=f"vbmapp_track_op_{pick_code}_{ever}",
        )
        list_choice = c2.text_input(
            "Skill list", value=f"VB-MAPP: {m['area']} {m['m_code']}",
            key=f"vbmapp_track_list_{pick_code}_{ever}",
        )
        desc = st.text_input(
            "Target description", value=m["title"],
            key=f"vbmapp_track_desc_{pick_code}_{ever}",
        )
        mastery_n_choice = st.number_input(
            "Mastery N (consecutive Y to auto-master)",
            min_value=1, max_value=10, value=3, step=1,
            key=f"vbmapp_track_n_{pick_code}_{ever}",
        )
        submitted = st.form_submit_button(
            "➕ Add as cold-probe target", type="primary", width="stretch",
        )
        if submitted:
            if not desc.strip():
                st.warning("Target description is empty.")
            else:
                targets_now = load_targets()
                targets_now.append({
                    "id": new_id(),
                    "student_id": sid,
                    "description": desc.strip(),
                    "domain": op_choice,
                    "skill_list": list_choice.strip(),
                    "mastery_n": int(mastery_n_choice),
                    "mastery_criterion": "",
                    "status": "In Acquisition",
                    "mastered_date": "",
                    "vbmapp_milestone_code": pick_code,
                })
                save_targets(targets_now)
                st.session_state["_vbmapp_saved_msg"] = (
                    f"✓ Added cold-probe target from **{m['area']} {m['m_code']}** "
                    f"to **{op_choice}** → {list_choice.strip()}."
                )
                st.toast("Cold-probe target added.")
                st.session_state["vbmapp_ver"] = ever + 1
                st.rerun()

    # ── Save ─────────────────────────────────────────────────────────────────
    st.divider()
    if st.button(
        "💾 Save VB-MAPP assessment", type="primary", width="stretch",
        key=f"vbmapp_save_{ever}",
    ):
        meta_records = meta_edited.to_dict("records")
        for i, n in enumerate(VBMAPP_TESTS):
            mr = meta_records[i] if i < len(meta_records) else {}
            rec["tests"][str(n)] = {
                "date": str(mr.get("Date", "") or "").strip(),
                "tester": str(mr.get("Tester", "") or "").strip(),
                "notes": str(mr.get("Notes", "") or "").strip(),
            }
        for lvl, edited in all_edits.items():
            for row in edited.to_dict("records"):
                code = row.get("_code", "")
                if not code:
                    continue
                for n in VBMAPP_TESTS:
                    v = row.get(f"Test {n}", "—")
                    if v not in VBMAPP_STATUS_OPTIONS:
                        v = "—"
                    rec["statuses"].setdefault(str(n), {})[code] = v
        save_vbmapp_for_student(sid, rec)
        n_set = sum(
            1 for n in VBMAPP_TESTS
            for v in rec["statuses"].get(str(n), {}).values()
            if v in ("0", "½", "1")
        )
        st.session_state["vbmapp_ver"] = ever + 1
        st.session_state["_vbmapp_saved_msg"] = (
            f"VB-MAPP assessment saved for {s.get('name','')} — "
            f"{n_set} score(s) recorded."
        )
        st.toast("VB-MAPP assessment saved.")
        st.rerun()


def main():
    st.set_page_config(
        page_title="Repertiores",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    # Surface any data-file load problems detected this run (recovered or blocked).
    if _LOAD_ERRORS:
        for _pth, _msg in list(_LOAD_ERRORS.items()):
            st.error(f"🚨 Data file **{os.path.basename(_pth)}** {_msg}")
    # Apply any deferred student switch BEFORE the sidebar selectbox instantiates.
    # Streamlit forbids writing to a widget-owned key after the widget renders.
    if "_pending_student" in st.session_state:
        st.session_state["current_student"] = st.session_state.pop("_pending_student")
    st.sidebar.title("🎯 Repertiores")

    # Suite: link back to the app chooser (only present inside the desktop bundle).
    _switch_url = os.environ.get("SWITCH_URL")
    if _switch_url:
        st.sidebar.markdown(
            f'<a href="{_switch_url}" target="_self" style="display:inline-block;'
            f'text-decoration:none;font-size:12px;color:#2563eb;font-weight:700;'
            f'background:#eff6ff;border:1.5px solid #bfdbfe;border-radius:20px;'
            f'padding:3px 12px;margin-bottom:8px;">⌂ Suite Home</a>',
            unsafe_allow_html=True,
        )

    students = load_students()
    st.sidebar.markdown("**Student**")
    if students:
        ids = [s["id"] for s in students]
        default_idx = ids.index(current_sid(students)) if current_sid(students) in ids else 0
        picked = st.sidebar.selectbox(
            "Student",
            options=ids,
            index=default_idx,
            format_func=lambda i: student_name(students, i),
            label_visibility="collapsed",
            key="current_student",
        )
    else:
        st.sidebar.caption("No students yet — add one on Student Home.")

    if DEV_MODE:
        st.sidebar.caption("DEV_MODE — no auth")

    pages = [
        ("Student Home", "🏠"),
        ("Dashboard", "🗂"),
        ("Target Bank", "🏦"),
        ("Intervention Bank", "🧩"),
        ("Export", "📤"),
    ]
    page_names = [name for name, _ in pages]
    valid_pages = set(page_names) | {
        "Operant Detail",
        "Collect Cold Probe Data",
        "Verbal Behavior Programming",
        "Behaviors of Concern",
        "Behavior Detail",
        "EFL Assessment",
        "VB-MAPP Assessment",
    }
    if "page" not in st.session_state:
        st.session_state["page"] = "Student Home"
    elif st.session_state["page"] not in valid_pages:
        st.session_state["page"] = "Student Home"
    for name, icon in pages:
        if st.sidebar.button(
            f"{icon}  {name}",
            key=f"nav_{name}",
            type="primary" if st.session_state["page"] == name else "secondary",
            width="stretch",
        ):
            st.session_state["page"] = name
            st.rerun()

    {
        "Student Home": page_home,
        "Dashboard": page_student_dashboard,
        "Target Bank": page_target_bank,
        "Intervention Bank": page_intervention_bank,
        "EFL Assessment": page_efl_assessment,
        "VB-MAPP Assessment": page_vbmapp_assessment,
        "Collect Cold Probe Data": page_probe_entry,
        "Verbal Behavior Programming": page_targets,
        "Operant Detail": page_operant_detail,
        "Behaviors of Concern": page_behaviors,
        "Behavior Detail": page_behavior_detail,
        "Export": page_export,
    }[st.session_state["page"]]()


if __name__ == "__main__":
    main()
