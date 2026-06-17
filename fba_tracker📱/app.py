import re
import base64
import hashlib
import hmac
import time as _time
import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import shutil
from datetime import date, datetime, timedelta
import plotly.express as px
import plotly.graph_objects as _go
try:
    import anthropic as _anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


# ── Dev mode — set to False before deploying ─────────────────────────────────
DEV_MODE = True

# ── Data files ────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE      = os.path.join(DATA_DIR, "abc_entries.json")
STUDENTS_FILE  = os.path.join(DATA_DIR, "students.json")
PROFILES_FILE  = os.path.join(DATA_DIR, "student_profiles.json")
ARCHIVE_FILE   = os.path.join(DATA_DIR, "archived_students.json")
CATEGORIES_FILE= os.path.join(DATA_DIR, "categories.json")
USERS_FILE     = os.path.join(DATA_DIR, "users.json")
AUDIT_FILE     = os.path.join(DATA_DIR, "audit_log.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Data safety: atomic writes + rolling backups + corruption recovery ───────
# Ported from Repertiores so FBA's clinical data has the same protection: every
# save is atomic (temp file + os.replace) and snapshots the last-good copy; a
# corrupt file is recovered from the newest backup rather than silently lost.
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")
AUTO_BACKUPS_DIR = os.path.join(BACKUPS_DIR, "auto")
os.makedirs(AUTO_BACKUPS_DIR, exist_ok=True)
MAX_AUTO_BACKUPS = 15

# Files whose on-disk copy failed to parse and could not be recovered. Saving to
# these is blocked so a corrupt file is never overwritten with empty data.
_QUARANTINED: set = set()
# path -> human-readable message about a load problem, surfaced as a banner.
_LOAD_ERRORS: dict = {}


def _backup_file(path: str) -> None:
    """Copy ``path`` into the auto-backup folder, pruning to MAX_AUTO_BACKUPS.
    Called after each successful write. Failures are non-fatal — a backup miss
    must never block the actual save."""
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


def _recover_or_quarantine(path: str, err: Exception, default):
    """Handle a data file that exists but won't parse: preserve the corrupt copy,
    recover the newest parseable backup, else quarantine the path so _safe_save
    refuses to overwrite it. Returns recovered data, or ``default`` if none."""
    name = os.path.basename(path)
    stem = os.path.splitext(name)[0]
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    msg = getattr(err, "msg", str(err))
    try:
        shutil.copy2(path, os.path.join(AUTO_BACKUPS_DIR, f"{stem}.{ts}.corrupt"))
    except Exception:
        pass
    candidates = []
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
            f"was unreadable ({msg}); recovered from backup {os.path.basename(fp)}. "
            f"The corrupt copy was saved as {stem}.{ts}.corrupt in data/backups/auto/."
        )
        return data
    _QUARANTINED.add(path)
    _LOAD_ERRORS[path] = (
        f"is corrupt ({msg}) and no usable backup was found. Saving to this file "
        f"is blocked to prevent data loss; the corrupt copy is preserved as "
        f"{stem}.{ts}.corrupt in data/backups/auto/."
    )
    return default


def _safe_load(path: str, default):
    """Load JSON from ``path`` with corruption recovery. Returns ``default`` if
    the file is missing, or recovers/quarantines if it exists but won't parse."""
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        # Do NOT silently return default — a later save would overwrite
        # recoverable data with nothing.
        return _recover_or_quarantine(path, e, default)
    _QUARANTINED.discard(path)
    _LOAD_ERRORS.pop(path, None)
    return data


def _safe_save(path: str, data) -> None:
    """Atomically write ``data`` to ``path`` (temp file + os.replace), then
    snapshot the committed copy. Refuses to write a quarantined file."""
    if path in _QUARANTINED:
        raise RuntimeError(
            f"Refusing to write {os.path.basename(path)}: its on-disk copy is "
            f"corrupt and no backup was found. Fix or remove the corrupt file in "
            f"data/ first (the corrupt copy is in data/backups/auto/)."
        )
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
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

# ── Repertiores roster bridge ────────────────────────────────────────────────
# FBA shares its learner roster with Repertiores: the same person carries the
# same 8-char student_id across both apps. FBA keys its own records by the
# Repertiores DISPLAY NAME (so its name-based UI is unchanged), but every record
# is stamped with student_id for the robust cross-app link (Phase 3 handoff).
def _repertiores_data_dir() -> str:
    """Locate Repertiores' data dir (live app-support copy, else workspace copy)."""
    env = os.environ.get("REPERTIORES_DATA_DIR")
    if env and os.path.exists(os.path.join(env, "students.json")):
        return env
    live = os.path.join(os.path.expanduser("~"), "Library", "Application Support",
                        "Repertiores", "data")
    if os.path.exists(os.path.join(live, "students.json")):
        return live
    ws = os.path.join(os.path.dirname(__file__), "..", "Repertiores", "data")
    return ws

REPERTIORES_STUDENTS_FILE = os.path.join(_repertiores_data_dir(), "students.json")

def load_roster() -> list:
    """Repertiores learners as [{'id','name',...}] — the shared source of truth."""
    data = _safe_load(REPERTIORES_STUDENTS_FILE, [])
    return data if isinstance(data, list) else []

def roster_id_for_name(name: str):
    """Resolve a display name to its Repertiores student_id, or None."""
    if not name:
        return None
    for s in load_roster():
        if s.get("name") == name:
            return s.get("id")
    return None

# ── HIPAA: Session timeout (minutes) ─────────────────────────────────────────
SESSION_TIMEOUT_MIN = 20

# ── HIPAA: Password hashing ───────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    """SHA-256 with a fixed app-level salt. Replace with bcrypt in production."""
    salt = "fba_hipaa_salt_2026"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        return _safe_load(USERS_FILE, {})
    # Default admin account — password 'Admin123!' (hash stored, never plain text)
    default = {
        "admin": {
            "password_hash": _hash_password("Admin123!"),
            "name": "Administrator",
            "role": "admin",
        }
    }
    _safe_save(USERS_FILE, default)
    return default

def verify_user(username: str, password: str):
    users = load_users()
    u = users.get(username.lower().strip())
    if not u:
        return None
    if hmac.compare_digest(u["password_hash"], _hash_password(password)):
        return u
    return None

# ── HIPAA: Audit logging ──────────────────────────────────────────────────────
def audit_log(action: str, detail: str = ""):
    user = st.session_state.get("login_email", "unknown")
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user,
        "action": action,
        "detail": detail,
    }
    logs = _safe_load(AUDIT_FILE, [])
    logs.append(entry)
    _safe_save(AUDIT_FILE, logs)

# ── HIPAA: Session activity tracking ─────────────────────────────────────────
def touch_session():
    st.session_state["last_active"] = _time.time()

def check_session_timeout():
    last = st.session_state.get("last_active")
    if last and (_time.time() - last) > SESSION_TIMEOUT_MIN * 60:
        st.session_state.logged_in = False
        st.session_state.selected_student = None
        audit_log("AUTO_LOGOUT", f"Session timed out after {SESSION_TIMEOUT_MIN} min")

# ── Enum values ───────────────────────────────────────────────────────────────
LOCATIONS = ["Classroom", "Library", "Hallway", "Playground", "Bathroom",
             "Gymnasium", "Cafeteria", "Other"]
PEOPLE_INTERVENING = ["Peer/another child", "Teacher", "Paraprofessional",
                      "Guidance Counselors", "Security Officers", "None", "Other"]
SUBJECTS = ["Language Arts", "Math", "Physical Education", "Science",
            "Social Studies", "Art", "Music", "N/A"]
ACTIVITIES = ["Academic Work", "Leisure Activity (Alone)",
              "Leisure Activity (with another person)",
              "Meal (preparation, eating, clean up)",
              "Self care or daily living tasks", "Alone", "Other"]
INSTRUCTIONAL_FORMATS = [
    "Cooperative Learning (Peer partners)", "Small group (2-12 students)",
    "Large group (13 or more students)", "Independent/ Seat work",
    "1 to 1 (Student to staff ratio)", "Dyad (2 students 1 staff)",
    "Unstructured time", "Other",
]
ANTECEDENTS = [
    "No antecedent observed",
    "Peer reactions or interactions (Att)(Esc)",
    "Staff attention is diverted or removed (Att)",
    "Absence or presence of a specific person (Att)",
    "Loud, bright, chaotic, or crowded environment (Sel)",
    "Transition to a different activity or location (Tan)",
    "Prompt, redirection or to correction of student work (Esc)(Att)",
    "Instruction, direction, or request to complete task (Esc)(Att)",
    "Object/activity delayed, denied, interrupted or terminated (Tan)",
    "Unstructured activity, free time (Att)(Sel)",
    "Other",
]
BEHAVIORS = [
    "Off-Task", "Fidgeting", "Calling out/ Making sounds", "Out of seat",
    "Non-compliance", "Arguing", "Elopement", "Mand/ request",
    "Compliance/ on task", "Self-injurious behavior", "Aggression",
    "Property destruction", "Other",
]
BEHAVIOR_ABBREVS_DEFAULT = {
    "Off-Task":                     "OFT",
    "Fidgeting":                    "FDG",
    "Calling out/ Making sounds":   "COS",
    "Out of seat":                  "OOS",
    "Non-compliance":               "NCM",
    "Arguing":                      "ARG",
    "Elopement":                    "ELP",
    "Mand/ request":                "MND",
    "Compliance/ on task":          "COT",
    "Self-injurious behavior":      "SIB",
    "Aggression":                   "AGG",
    "Property destruction":         "PDX",
    "Other":                        "OTH",
}
CONSEQUENCES = [
    "Staff intervention (reaction or interaction) (Att)",
    "Staff attention is diverted or removed (Att)",
    "Peer reactions or interactions (Att)",
    "Preferred object or activity given (Tan)",
    "Object/activity removed or terminated (Tan)",
    "No environmental change (Sel)",
    "Tasks delayed or removed (Esc)",
    "Other",
]

# ── Motivating Operations defaults ────────────────────────────────────────────
MO_DEFAULTS = {
    "Biological / Physical": [
        {"key": "sleep_deprived",       "label": "Student arrived appearing drowsy — yawning, heavy eyelids, slow movement",         "tier": 2, "auto_field": None},
        {"key": "illness_pain",         "label": "Student visited nurse today or verbally reported discomfort / observable guarding", "tier": 2, "auto_field": None},
        {"key": "gi_issues",            "label": "Student showing signs of GI distress — reported stomachache, vomiting, or diarrhea observed / reported", "tier": 2, "auto_field": None},
        {"key": "hunger",               "label": "Behavior occurring before scheduled meal or snack / student requesting food",       "tier": 2, "auto_field": None},
        {"key": "fatigue",              "label": "High-demand activity immediately preceded this session",                           "tier": 2, "auto_field": None},
        {"key": "medication_change",    "label": "Medication changed, missed, or new dose today",                                    "tier": 2, "auto_field": None},
        {"key": "sensory_over",         "label": "Environment noisier, brighter, or more crowded than typical",                     "tier": 2, "auto_field": None},
        {"key": "sensory_under",        "label": "Unstructured / free time with low sensory input — minimal activity in environment","tier": 1, "auto_field": "activity"},
    ],
    "Social / Emotional": [
        {"key": "social_deprivation",   "label": "Less than typical adult interaction before session / preferred person absent",     "tier": 2, "auto_field": None},
        {"key": "social_satiation",     "label": "Group larger than typical or high-interaction period immediately preceded session","tier": 2, "auto_field": None},
        {"key": "preferred_person_absent", "label": "Named preferred staff member or peer not present today",                       "tier": 2, "auto_field": None},
        {"key": "recent_conflict",      "label": "Significant negative social interaction occurred before this session",            "tier": 3, "auto_field": None},
    ],
    "Environmental / Contextual": [
        {"key": "schedule_change",      "label": "Schedule changed or disrupted from posted routine",                               "tier": 2, "auto_field": None},
        {"key": "transition",           "label": "Transition from preferred to non-preferred activity",                             "tier": 1, "auto_field": "antecedent"},
        {"key": "item_removed",         "label": "Preferred item or activity removed within last 30 minutes",                       "tier": 2, "auto_field": None},
        {"key": "item_unavailable",     "label": "Preferred item/activity requested and denied before session",                     "tier": 2, "auto_field": None},
        {"key": "unfamiliar_person",    "label": "Unfamiliar adult or peer present in environment",                                 "tier": 3, "auto_field": None},
        {"key": "novel_environment",    "label": "Setting is unfamiliar to student",                                               "tier": 3, "auto_field": None},
    ],
    "Task / Instructional": [
        {"key": "high_demand",          "label": "High task difficulty or low perceived chance of success",                         "tier": 1, "auto_field": "antecedent"},
        {"key": "long_task",            "label": "Long task duration — extended work period without break",                         "tier": 2, "auto_field": None},
        {"key": "low_choice",           "label": "Low perceived control or choice in current activity",                             "tier": 2, "auto_field": None},
        {"key": "nonpreferred_task",    "label": "Non-preferred subject or activity currently assigned",                            "tier": 2, "auto_field": None},
        {"key": "independent_work",     "label": "Expected to work independently with little support",                              "tier": 1, "auto_field": "instructional_format"},
    ],
}

# ── Category loader (custom overrides defaults) ───────────────────────────────
def load_categories():
    saved = _safe_load(CATEGORIES_FILE, {})
    return {
        "behaviors":             saved.get("behaviors",             BEHAVIORS),
        "behavior_abbrevs":      saved.get("behavior_abbrevs",      BEHAVIOR_ABBREVS_DEFAULT),
        "antecedents":           saved.get("antecedents",           ANTECEDENTS),
        "consequences":          saved.get("consequences",          CONSEQUENCES),
        "locations":             saved.get("locations",             LOCATIONS),
        "people_intervening":    saved.get("people_intervening",    PEOPLE_INTERVENING),
        "subjects":              saved.get("subjects",              SUBJECTS),
        "activities":            saved.get("activities",            ACTIVITIES),
        "instructional_formats": saved.get("instructional_formats", INSTRUCTIONAL_FORMATS),
        "custom_mos":            saved.get("custom_mos",            []),
    }

def save_categories(cats):
    _safe_save(CATEGORIES_FILE, cats)

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
<style>
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] { background: transparent; height: 0 !important; }
[data-testid="stAppViewContainer"],
[data-testid="stMain"] { background: #f3f4f6; }

.block-container {
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    max-width: 100% !important;
}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #e5e7eb;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
    border: 1.5px solid #d1d5db;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important;
    padding: 6px 18px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    color: #6b7280 !important;
    background: #f3f4f6 !important;
    border: 1.5px solid #c9cdd4 !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #111827 !important;
    font-weight: 700 !important;
    border: 1.5px solid #9ca3af !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    border: 1.5px solid #d1d5db;
    border-radius: 0 0 10px 10px;
    border-top: none;
    padding: 16px 12px !important;
    background: white;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

/* Gray section headings */
h1, h2, h3,
div[style*="font-weight:700"][style*="color:#111"],
div[style*="font-weight:800"][style*="color:#111"] {
    color: #4b5563 !important;
}

/* Primary buttons */
.stButton > button[kind="primary"] {
    background: #16a34a !important;
    border: none !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover { background: #15803d !important; }

/* Form submit button (Save Entry) */
[data-testid="stFormSubmitButton"] > button {
    background: #16a34a !important;
    border: none !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    height: 48px !important;
}
[data-testid="stFormSubmitButton"] > button:hover { background: #15803d !important; }


/* Secondary / default buttons */
.stButton > button {
    border-radius: 8px !important;
    border: 1.5px solid #d1d5db !important;
    background: white !important;
    color: #374151 !important;
    font-size: 13px !important;
}
.stButton > button:hover { background: #f9fafb !important; }

/* Inputs & selects */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div {
    background: white !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}

/* Date / Time / Number input containers */
[data-baseweb="input"] {
    background: white !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 8px !important;
}
[data-baseweb="input"] input {
    background: white !important;
    color: #111827 !important;
}
[data-testid="stDateInput"] > div,
[data-testid="stTimeInput"] > div,
[data-testid="stNumberInput"] > div {
    background: white !important;
    border-radius: 8px !important;
}
[data-testid="stNumberInput"] button {
    background: white !important;
    border-color: #e5e7eb !important;
    color: #374151 !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: white;
    border: 1.5px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px 16px;
}

/* Download button */
.stDownloadButton > button {
    border-radius: 8px !important;
    background: white !important;
    border: 1.5px solid #d1d5db !important;
    color: #374151 !important;
    font-size: 13px !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1.5px solid #e5e7eb;
}

/* Form container */
[data-testid="stForm"] {
    background: white !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 14px !important;
    padding: 24px !important;
}

hr { border-color: #e5e7eb !important; }


/* All horizontal radio buttons — shared base */
.stRadio > div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    gap: 6px !important;
    flex-wrap: nowrap !important;
}
.stRadio > div[role="radiogroup"] > label {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border: 1.5px solid #d1d5db !important;
    background: white !important;
    cursor: pointer !important;
    margin: 0 !important;
}
.stRadio > div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}
.stRadio > div[role="radiogroup"] > label > div {
    font-size: 13px !important;
    color: #374151 !important;
    line-height: 1 !important;
}
.stRadio > div[role="radiogroup"] > label:has(input:checked) {
    background: #1e2d3d !important;
    border-color: #1e2d3d !important;
}
.stRadio > div[role="radiogroup"] > label:has(input:checked) > div {
    color: white !important;
    font-weight: 700 !important;
}

/* Intensity radio (5+ options) — small circles */
.stRadio > div[role="radiogroup"]:has(> label:nth-child(5)) > label {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    border-radius: 50% !important;
    padding: 0 !important;
}

/* Short radio (≤4 options, e.g. Weekly/Monthly/Yearly) — pill shape */
.stRadio > div[role="radiogroup"]:not(:has(> label:nth-child(5))) > label {
    height: 34px !important;
    min-width: 80px !important;
    border-radius: 20px !important;
    padding: 0 14px !important;
}

/* Add new student dashed button */
button[kind="secondary"]:has-text("＋") {
    border: 2px dashed #d1d5db !important;
    border-radius: 16px !important;
    background: transparent !important;
    color: #6b7280 !important;
    font-size: 15px !important;
    padding: 18px !important;
    height: auto !important;
}
/* Student card arrow button — minimal */
[data-testid="stButton"] button[title^="Open"] {
    background: transparent !important;
    border: none !important;
    color: #9ca3af !important;
    font-size: 22px !important;
}

/* Log table rows */
table tbody tr {
    border-bottom: 1px solid #f3f4f6;
}
table tbody tr:hover { background: #f9fafb; }
table tbody td { padding: 12px 12px; vertical-align: middle; }
</style>
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_json(path):
    return _safe_load(path, [])

def save_json(path, data):
    _safe_save(path, data)

def load_profiles() -> dict:
    """Load student profiles dict keyed by student name."""
    return _safe_load(PROFILES_FILE, {})

def save_profiles(profiles: dict):
    _safe_save(PROFILES_FILE, profiles)

def load_archive() -> list:
    """Load list of archived student records [{name, archived_date, entry_count}]."""
    return _safe_load(ARCHIVE_FILE, [])

def save_archive(archive: list):
    _safe_save(ARCHIVE_FILE, archive)

def duration_from_seconds(s):
    if not s: return None
    if s <= 30:   return "0 seconds- 30 seconds"
    if s <= 60:   return "30 seconds- 1 minute"
    if s <= 300:  return "1 minute- 5 minutes"
    if s <= 600:  return "5 minutes- 10 minutes"
    if s <= 1200: return "10 minutes- 20 minutes"
    if s <= 1800: return "20 minutes- 30 minutes"
    return "More than 30 minutes"

# ── Login Page ────────────────────────────────────────────────────────────────
def page_login():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] { background: #f8f9fa !important; }
    .login-wrap {
        max-width: 420px;
        margin: 60px auto 0 auto;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .login-card {
        width: 100%;
        background: white;
        border-radius: 18px;
        padding: 40px 36px 32px 36px;
        box-shadow: 0 2px 16px rgba(0,0,0,0.07);
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    </style>
    <div class="login-wrap">
      <div class="login-card">
        <!-- Logo -->
        <div style="width:80px;height:80px;background:#1e2d3d;border-radius:50%;
                    display:flex;align-items:center;justify-content:center;margin-bottom:22px;">
          <svg width="44" height="44" viewBox="0 0 44 44" fill="none">
            <polygon points="22,4 38,13 38,31 22,40 6,31 6,13" fill="none"
                     stroke="#d4a843" stroke-width="2"/>
            <polygon points="22,10 33,16 33,28 22,34 11,28 11,16" fill="none"
                     stroke="#d4a843" stroke-width="1.5"/>
            <rect x="16" y="12" width="12" height="2" rx="1" fill="#d4a843"/>
            <rect x="16" y="30" width="12" height="2" rx="1" fill="#d4a843"/>
            <path d="M16 14 Q22 22 28 30" stroke="#d4a843" stroke-width="1.5" fill="none"/>
            <path d="M28 14 Q22 22 16 30" stroke="#d4a843" stroke-width="1.5" fill="none"/>
          </svg>
        </div>
        <div style="font-size:26px;font-weight:800;color:#111827;text-align:center;
                    line-height:1.25;margin-bottom:6px;">
          Welcome to FBA Data Tracker (v.4.6.26)
        </div>
        <div style="font-size:14px;color:#9ca3af;margin-bottom:28px;">
          Sign in to continue
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Center the form with narrow columns
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:4px;">Email</div>', unsafe_allow_html=True)
        email = st.text_input("Email", placeholder="you@example.com",
                              label_visibility="collapsed", key="login_email_input")
        st.markdown('<div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:4px;margin-top:8px;">Password</div>', unsafe_allow_html=True)
        st.text_input("Password", type="password", placeholder="••••••••",
                      label_visibility="collapsed", key="login_pw_input")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <style>
        div[data-testid="stButton"]:has(button[data-testid="login-btn"]) button {
            background: #1e2d3d !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            height: 48px !important;
        }
        </style>""", unsafe_allow_html=True)
        if st.button("Sign in", use_container_width=True, key="login_btn"):
            u = verify_user(email.strip(), st.session_state.get("login_pw_input", ""))
            if u:
                st.session_state.logged_in = True
                st.session_state.login_email = email.strip().lower()
                st.session_state.observer_name = u.get("name", email.strip())
                st.session_state.user_role = u.get("role", "observer")
                touch_session()
                audit_log("LOGIN", f"User {email.strip()} signed in")
                st.rerun()
            else:
                audit_log("LOGIN_FAIL", f"Failed login attempt for {email.strip()}")
                st.error("Invalid username or password.")

        # ── Create account toggle ─────────────────────────────────────────────
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <style>
        div[data-testid="stButton"]:has(button[data-testid="show_register_btn"]) button {
            background: transparent !important;
            color: #6b7280 !important;
            border: 1.5px solid #e5e7eb !important;
            border-radius: 10px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            height: 40px !important;
        }
        div[data-testid="stButton"]:has(button[data-testid="show_register_btn"]) button:hover {
            border-color: #16a34a !important;
            color: #15803d !important;
            background: #f0fdf4 !important;
        }
        </style>""", unsafe_allow_html=True)
        if st.button("＋ Create new account", use_container_width=True, key="show_register_btn"):
            st.session_state["show_register"] = not st.session_state.get("show_register", False)
            st.rerun()

        if st.session_state.get("show_register"):
            st.markdown(
                '<div style="background:#f0fdf4;border:1.5px solid #86efac;'
                'border-radius:14px;padding:20px 20px 16px 20px;margin-top:8px;">',
                unsafe_allow_html=True
            )
            st.markdown("**Create Account**")
            reg_name = st.text_input("Full Name", placeholder="Your full name", key="reg_name")
            reg_user = st.text_input("Username", placeholder="Choose a username", key="reg_user")
            reg_pw   = st.text_input("Password", type="password",
                                     placeholder="Min 8 characters", key="reg_pw")
            reg_pw2  = st.text_input("Confirm Password", type="password",
                                     placeholder="Re-enter password", key="reg_pw2")

            if st.button("Create Account", type="primary", use_container_width=True,
                         key="register_submit_btn"):
                errs = []
                if not reg_name.strip():
                    errs.append("Full name is required.")
                if not reg_user.strip():
                    errs.append("Username is required.")
                elif len(reg_user.strip()) < 3:
                    errs.append("Username must be at least 3 characters.")
                if len(reg_pw) < 8:
                    errs.append("Password must be at least 8 characters.")
                if reg_pw != reg_pw2:
                    errs.append("Passwords do not match.")
                users = load_users()
                if reg_user.strip().lower() in users:
                    errs.append("That username is already taken.")
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    users[reg_user.strip().lower()] = {
                        "password_hash": _hash_password(reg_pw),
                        "name": reg_name.strip(),
                        "role": "observer",
                    }
                    _safe_save(USERS_FILE, users)
                    audit_log("REGISTER", f"New account created: {reg_user.strip().lower()}")
                    st.success(f"Account created! You can now sign in as **{reg_user.strip()}**.")
                    st.session_state["show_register"] = False
                    st.rerun()
            if st.button("Cancel", use_container_width=True, key="cancel_register_btn"):
                st.session_state["show_register"] = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;'
            'padding:10px 14px;margin-top:16px;font-size:11px;color:#92400e;line-height:1.5;">'
            '<b>⚠ HIPAA Notice:</b> This application may contain Protected Health Information (PHI). '
            'By signing in you agree to access only information necessary for your role, '
            'maintain confidentiality, and comply with your organization\'s privacy policies. '
            'All access is logged.</div>',
            unsafe_allow_html=True
        )


# ── Student Selector ──────────────────────────────────────────────────────────
def page_student_selector():
    observer = st.session_state.get("observer_name", "")
    first = observer.split()[0] if observer else ""

    # ── Header bar ────────────────────────────────────────────────────────────
    # ── Header ────────────────────────────────────────────────────────────────
    hc1, hc2 = st.columns([7, 1])
    with hc1:
        st.markdown(
            '<div style="background:#e5e7eb;padding:16px 24px;'
            'margin:0 -1rem 0 -1rem;border-bottom:1px solid #d1d5db;">'
            '<div style="font-size:18px;font-weight:900;letter-spacing:.05em;color:#111;">'
            'ABC DATA COLLECTION</div>'
            '<div style="font-size:12px;color:#6b7280;margin-top:1px;">'
            'Functional Behavior Assessment</div>'
            '</div>',
            unsafe_allow_html=True
        )
    with hc2:
        st.markdown(
            '<div style="background:#e5e7eb;padding:10px 0 10px 0;'
            'margin:0 -1rem 0 0;border-bottom:1px solid #d1d5db;'
            'display:flex;align-items:center;justify-content:flex-end;gap:10px;padding-right:12px;">'
            '<div style="text-align:right;">'
            '<div style="font-size:13px;font-weight:700;color:#111;">'
            + (observer if observer else "Set your name") +
            '</div>'
            '<div style="font-size:11px;color:#6b7280;">Data Collector</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if st.button("↪", key="logout_btn", help="Sign out", use_container_width=True):
            audit_log("LOGOUT", "User signed out")
            st.session_state.logged_in = False
            st.session_state.selected_student = None
            st.rerun()

    # ── Observer name (shown only if not set) ─────────────────────────────────
    if not observer:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        obs = st.text_input("Your name", placeholder="Enter your name as Data Collector",
                            key="obs_login")
        if obs:
            st.session_state.observer_name = obs
            st.rerun()

    # ── Center icon + title ───────────────────────────────────────────────────
    greeting = f"Welcome{', ' + first + '!' if first else '!'}"
    st.markdown(
        '<div style="text-align:center;margin:40px 0 32px 0;">'
        '<div style="width:72px;height:72px;background:#dcfce7;border-radius:20px;'
        'display:inline-flex;align-items:center;justify-content:center;'
        'font-size:32px;margin-bottom:18px;">🎓</div>'
        '<div style="font-size:26px;font-weight:800;color:#111;margin-bottom:8px;">'
        'Select a Student</div>'
        '<div style="font-size:15px;color:#6b7280;">'
        + greeting + ' Choose a student to begin recording observations.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    students = load_json(STUDENTS_FILE)

    # ── Onboarding empty state ────────────────────────────────────────────────
    if not students:
        st.markdown(
            '<div style="text-align:center;padding:40px 20px 32px 20px;">'
            '<div style="font-size:48px;margin-bottom:16px;">🎒</div>'
            '<div style="font-size:20px;font-weight:700;color:#111827;margin-bottom:8px;">'
            'No students yet</div>'
            '<div style="font-size:14px;color:#6b7280;max-width:320px;margin:0 auto 24px auto;">'
            'Add your first student using the button below to start recording ABC observations.</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # ── Student cards ─────────────────────────────────────────────────────────
    profiles   = load_profiles()
    all_entries_for_count = load_json(DATA_FILE)

    # Avatar color palette — cycles through students
    _AVATAR_COLORS = [
        ("#dcfce7", "#16a34a"),  # green
        ("#dbeafe", "#2563eb"),  # blue
        ("#fce7f3", "#db2777"),  # pink
        ("#fef9c3", "#ca8a04"),  # yellow
        ("#ede9fe", "#7c3aed"),  # purple
        ("#ffedd5", "#ea580c"),  # orange
        ("#ccfbf1", "#0d9488"),  # teal
    ]

    st.markdown("""
    <style>
    .stu-card-visual {
        background: white;
        border: 1.5px solid #e5e7eb;
        border-radius: 16px;
        padding: 16px 16px 14px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
        margin-bottom: 12px;
    }
    /* Each card lives in its own stColumn — scope to that */
    [data-testid="stColumn"]:has(.stu-card-marker) {
        position: relative !important;
    }
    [data-testid="stColumn"]:has(.stu-card-marker) [data-testid="stButton"] {
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: 140px !important;
        z-index: 5 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stColumn"]:has(.stu-card-marker) [data-testid="stButton"] > button {
        opacity: 0 !important;
        width: 100% !important;
        height: 100% !important;
        cursor: pointer !important;
        border-radius: 16px !important;
        padding: 0 !important;
    }
    /* Only highlight the card in the column whose button is hovered */
    [data-testid="stColumn"]:has([data-testid="stButton"]:hover) .stu-card-visual {
        border-color: #16a34a !important;
        box-shadow: 0 4px 16px rgba(22,163,74,0.14) !important;
        background: #f0fdf4 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Lay cards out in a 2-column grid
    cols_per_row = 2
    rows = [students[i:i+cols_per_row] for i in range(0, len(students), cols_per_row)]
    for row_students in rows:
        grid_cols = st.columns(cols_per_row)
        for col, name in zip(grid_cols, row_students):
            i = students.index(name)
            bg, fg = _AVATAR_COLORS[i % len(_AVATAR_COLORS)]
            initial = name[0].upper()
            prof = profiles.get(name, {})
            entry_count = len([e for e in all_entries_for_count if e.get("student_name") == name])

            # Calculate age from DOB
            age_str = ""
            dob_raw = prof.get("dob", "")
            if dob_raw:
                for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y"):
                    try:
                        dob_dt = datetime.strptime(dob_raw.strip(), fmt)
                        today = date.today()
                        age = today.year - dob_dt.year - ((today.month, today.day) < (dob_dt.month, dob_dt.day))
                        age_str = f"Age {age}"
                        break
                    except Exception:
                        pass

            school_district = prof.get("school", "") or ""

            # Build subtitle: name line info
            subtitle_parts = []
            if school_district:
                subtitle_parts.append(school_district)
            if age_str:
                subtitle_parts.append(age_str)
            subtitle = "  ·  ".join(subtitle_parts) if subtitle_parts else "No profile info yet"

            # Bottom chips
            chips_html = ""
            for chip_val in [
                age_str if age_str else None,
                prof.get("grade"),
                f"BCBA: {prof['case_manager']}" if prof.get("case_manager") else None,
                prof.get("eligibility"),
            ]:
                if chip_val:
                    chips_html += (
                        f'<span style="background:#f3f4f6;border-radius:6px;padding:3px 8px;'
                        f'font-size:11px;color:#374151;margin:2px 2px 2px 0;display:inline-block;">'
                        f'{chip_val}</span>'
                    )
            if not chips_html:
                chips_html = (
                    '<span style="background:#fef9c3;color:#854d0e;border-radius:6px;'
                    'padding:3px 8px;font-size:11px;display:inline-block;">✏️ Complete profile</span>'
                )

            with col:
                st.markdown('<div class="stu-card-marker"></div>', unsafe_allow_html=True)
                if st.button(" ", key=f"sel_{i}", use_container_width=True):
                    st.session_state.selected_student = name
                    st.rerun()
                st.markdown(
                    f'<div class="stu-card-visual">'
                    f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
                    f'  <div style="width:50px;height:50px;flex-shrink:0;background:{bg};border-radius:12px;'
                    f'       display:flex;align-items:center;justify-content:center;'
                    f'       color:{fg};font-weight:800;font-size:20px;">{initial}</div>'
                    f'  <div style="flex:1;min-width:0;">'
                    f'    <div style="font-size:15px;font-weight:700;color:#111827;">{name}</div>'
                    f'    <div style="font-size:11px;color:#6b7280;margin-top:2px;'
                    f'         overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{subtitle}</div>'
                    f'  </div>'
                    f'  <div style="text-align:center;flex-shrink:0;background:{bg};'
                    f'       border-radius:10px;padding:5px 10px;">'
                    f'    <div style="font-size:17px;font-weight:800;color:{fg};line-height:1;">{entry_count}</div>'
                    f'    <div style="font-size:10px;color:{fg};opacity:0.8;">entr{"ies" if entry_count != 1 else "y"}</div>'
                    f'  </div>'
                    f'</div>'
                    f'<div style="border-top:1px solid #f3f4f6;margin:0 0 8px 0;"></div>'
                    f'<div>{chips_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ── Action buttons row ────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Add / Edit / Archive / Remove action buttons on selector page */
    .stMarkdown:has(.action-btn-add) + [data-testid="stButton"] > button {
        background: #f0fdf4 !important;
        border: 2px solid #86efac !important;
        border-radius: 12px !important;
        height: 56px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #15803d !important;
        box-shadow: 0 1px 4px rgba(22,163,74,0.10) !important;
        transition: all 0.15s !important;
    }
    .stMarkdown:has(.action-btn-add) + [data-testid="stButton"] > button:hover {
        background: #dcfce7 !important;
        border-color: #16a34a !important;
        box-shadow: 0 3px 10px rgba(22,163,74,0.18) !important;
    }
    .stMarkdown:has(.action-btn-edit) + [data-testid="stButton"] > button {
        background: #eff6ff !important;
        border: 2px solid #93c5fd !important;
        border-radius: 12px !important;
        height: 56px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #1d4ed8 !important;
        box-shadow: 0 1px 4px rgba(59,130,246,0.10) !important;
        transition: all 0.15s !important;
    }
    .stMarkdown:has(.action-btn-edit) + [data-testid="stButton"] > button:hover {
        background: #dbeafe !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 3px 10px rgba(59,130,246,0.18) !important;
    }
    .stMarkdown:has(.action-btn-archive) + [data-testid="stButton"] > button {
        background: #faf5ff !important;
        border: 2px solid #c4b5fd !important;
        border-radius: 12px !important;
        height: 56px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #6d28d9 !important;
        box-shadow: 0 1px 4px rgba(109,40,217,0.10) !important;
        transition: all 0.15s !important;
    }
    .stMarkdown:has(.action-btn-archive) + [data-testid="stButton"] > button:hover {
        background: #ede9fe !important;
        border-color: #7c3aed !important;
        box-shadow: 0 3px 10px rgba(109,40,217,0.18) !important;
    }
    .stMarkdown:has(.action-btn-remove) + [data-testid="stButton"] > button {
        background: #fff7ed !important;
        border: 2px solid #fdba74 !important;
        border-radius: 12px !important;
        height: 56px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #c2410c !important;
        box-shadow: 0 1px 4px rgba(234,88,12,0.10) !important;
        transition: all 0.15s !important;
    }
    .stMarkdown:has(.action-btn-remove) + [data-testid="stButton"] > button:hover {
        background: #ffedd5 !important;
        border-color: #ea580c !important;
        box-shadow: 0 3px 10px rgba(234,88,12,0.18) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    act1, act2, act3, act4 = st.columns(4)

    with act1:
        st.markdown('<div class="action-btn-add"></div>', unsafe_allow_html=True)
        if st.button("＋  Add New Student", use_container_width=True, key="show_add_btn"):
            st.session_state.show_add_student = not st.session_state.get("show_add_student", False)
            st.session_state.show_edit_selector = False
            st.session_state.show_remove_selector = False
            st.session_state.show_archive_selector = False
            st.rerun()

    with act2:
        st.markdown('<div class="action-btn-edit"></div>', unsafe_allow_html=True)
        if st.button("✏️  Edit Student", use_container_width=True, key="show_edit_selector_btn"):
            st.session_state.show_edit_selector = not st.session_state.get("show_edit_selector", False)
            st.session_state.show_add_student = False
            st.session_state.show_remove_selector = False
            st.session_state.show_archive_selector = False
            st.rerun()

    with act3:
        st.markdown('<div class="action-btn-archive"></div>', unsafe_allow_html=True)
        if st.button("🗄  Archive Student", use_container_width=True, key="show_archive_selector_btn"):
            st.session_state.show_archive_selector = not st.session_state.get("show_archive_selector", False)
            st.session_state.show_add_student = False
            st.session_state.show_edit_selector = False
            st.session_state.show_remove_selector = False
            st.rerun()

    with act4:
        st.markdown('<div class="action-btn-remove"></div>', unsafe_allow_html=True)
        if st.button("🗑  Remove Student", use_container_width=True, key="show_remove_selector_btn"):
            st.session_state.show_remove_selector = not st.session_state.get("show_remove_selector", False)
            st.session_state.show_add_student = False
            st.session_state.show_edit_selector = False
            st.session_state.show_archive_selector = False
            st.rerun()

    # ── Add new student panel ─────────────────────────────────────────────────
    if st.session_state.get("show_add_student"):
        st.markdown(
            '<div style="background:#f0fdf4;border:2px solid #86efac;'
            'border-radius:14px;padding:20px 22px;margin-top:14px;">',
            unsafe_allow_html=True
        )
        st.markdown("**Add New Student**")
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            new_name = st.text_input("Student name", placeholder="Full name",
                                     label_visibility="collapsed", key="new_student")
        with c2:
            if st.button("Add", type="primary", use_container_width=True, key="add_stu_confirm"):
                n = new_name.strip()
                if n and n not in students:
                    students.append(n)
                    save_json(STUDENTS_FILE, students)
                    st.session_state.show_add_student = False
                    st.session_state.selected_student = n
                    st.session_state["show_settings"] = True
                    st.rerun()
                elif n in students:
                    st.warning("Already exists.")
        with c3:
            if st.button("Cancel", use_container_width=True, key="cancel_add"):
                st.session_state.show_add_student = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Edit student panel ────────────────────────────────────────────────────
    if st.session_state.get("show_edit_selector") and students:
        profiles = load_profiles()
        st.markdown(
            '<div style="background:#eff6ff;border:2px solid #93c5fd;'
            'border-radius:14px;padding:20px 22px;margin-top:14px;">',
            unsafe_allow_html=True
        )
        st.markdown("**Edit Student Information**")
        edit_target = st.selectbox("Select student to edit", students, key="edit_sel_target")
        prof = profiles.get(edit_target, {})

        r1a, r1b = st.columns(2)
        with r1a:
            es_name = st.text_input("Full Name", value=edit_target, key="es_name")
        with r1b:
            es_dob = st.text_input("Date of Birth (MM/DD/YYYY)", value=prof.get("dob", ""),
                                   key="es_dob", placeholder="MM/DD/YYYY")

        r2a, r2b = st.columns(2)
        with r2a:
            grade_options = ["", "Pre-K", "Kindergarten", "1st", "2nd", "3rd",
                             "4th", "5th", "6th", "7th", "8th", "9th", "10th",
                             "11th", "12th", "Post-Secondary"]
            cur_grade = prof.get("grade", "")
            es_grade = st.selectbox("Grade", grade_options,
                                    index=grade_options.index(cur_grade) if cur_grade in grade_options else 0,
                                    key="es_grade")
        with r2b:
            gender_options = ["", "Male", "Female", "Non-binary", "Other", "Prefer not to say"]
            cur_gender = prof.get("gender", "")
            es_gender = st.selectbox("Gender", gender_options,
                                     index=gender_options.index(cur_gender) if cur_gender in gender_options else 0,
                                     key="es_gender")

        r3a, r3b = st.columns(2)
        with r3a:
            disability_options = [
                "", "Autism Spectrum Disorder", "Emotional Disturbance",
                "Intellectual Disability", "Other Health Impairment",
                "Specific Learning Disability", "Speech/Language Impairment",
                "Traumatic Brain Injury", "Multiple Disabilities",
                "Developmental Delay", "Other"
            ]
            cur_dis = prof.get("disability_category", "")
            es_disability = st.selectbox("Disability Category (IDEA)", disability_options,
                                         index=disability_options.index(cur_dis) if cur_dis in disability_options else 0,
                                         key="es_disability")
        with r3b:
            es_eligibility = st.text_input("IEP / 504 Eligibility",
                                           value=prof.get("eligibility", ""),
                                           key="es_eligibility",
                                           placeholder="e.g., IEP – Autism")

        r4a, r4b = st.columns(2)
        with r4a:
            es_teacher = st.text_input("Primary Teacher", value=prof.get("teacher", ""), key="es_teacher")
        with r4b:
            es_case_mgr = st.text_input("Case Manager / BCBA", value=prof.get("case_manager", ""), key="es_case_mgr")

        r5a, r5b = st.columns(2)
        with r5a:
            es_school = st.text_input("School District", value=prof.get("school", ""), key="es_school")
        with r5b:
            es_classroom = st.text_input("Classroom / Program", value=prof.get("classroom", ""), key="es_classroom")

        es_notes = st.text_area("Background / Clinical Notes", value=prof.get("notes", ""),
                                key="es_notes", height=80,
                                placeholder="Relevant history, reinforcers, sensory needs, medical info, etc.")

        sv1, sv2 = st.columns([1, 1])
        with sv1:
            if st.button("💾 Save Changes", type="primary", use_container_width=True, key="es_save"):
                new_name_clean = es_name.strip()
                all_stu = load_json(STUDENTS_FILE)
                all_ent = load_json(DATA_FILE)
                if not new_name_clean:
                    st.warning("Name cannot be blank.")
                elif new_name_clean != edit_target and new_name_clean in all_stu:
                    st.warning(f"'{new_name_clean}' already exists.")
                else:
                    if new_name_clean != edit_target:
                        all_stu = [new_name_clean if s == edit_target else s for s in all_stu]
                        save_json(STUDENTS_FILE, all_stu)
                        updated = [dict(e, student_name=new_name_clean)
                                   if e.get("student_name") == edit_target else e for e in all_ent]
                        save_json(DATA_FILE, updated)
                        if edit_target in profiles:
                            profiles[new_name_clean] = profiles.pop(edit_target)
                    profiles[new_name_clean] = {
                        "dob": es_dob.strip(), "grade": es_grade, "gender": es_gender,
                        "disability_category": es_disability, "eligibility": es_eligibility.strip(),
                        "teacher": es_teacher.strip(), "case_manager": es_case_mgr.strip(),
                        "school": es_school.strip(), "classroom": es_classroom.strip(),
                        "notes": es_notes.strip(),
                    }
                    save_profiles(profiles)
                    audit_log("EDIT_STUDENT_INFO", f"Updated profile for '{new_name_clean}'"
                              + (f" (renamed from '{edit_target}')" if new_name_clean != edit_target else ""))
                    st.session_state.show_edit_selector = False
                    st.rerun()
        with sv2:
            if st.button("Cancel", use_container_width=True, key="es_cancel"):
                st.session_state.show_edit_selector = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Remove student panel ──────────────────────────────────────────────────
    if st.session_state.get("show_remove_selector") and students:
        st.markdown(
            '<div style="background:#fff7ed;border:2px solid #fdba74;'
            'border-radius:14px;padding:20px 22px;margin-top:14px;">',
            unsafe_allow_html=True
        )
        st.markdown("**Remove a Student**")
        to_del = st.selectbox("Select student to remove", students, key="del_sel")
        entry_count = len([e for e in load_json(DATA_FILE) if e.get("student_name") == to_del])

        st.markdown(
            f'<div style="background:#fef2f2;border:1.5px solid #fca5a5;border-radius:10px;'
            f'padding:12px 16px;margin:12px 0;font-size:13px;color:#7f1d1d;">'
            f'⚠️ Removing <b>{to_del}</b> will permanently delete the student and all '
            f'<b>{entry_count} ABC entr{"ies" if entry_count != 1 else "y"}</b>. '
            f'This cannot be undone.</div>',
            unsafe_allow_html=True
        )
        if not st.session_state.get("confirm_del"):
            rd1, rd2 = st.columns([1, 1])
            with rd1:
                if st.button("Delete Student + All Data", type="secondary",
                             use_container_width=True, key="del_stu_trigger"):
                    st.session_state.confirm_del = True
                    st.rerun()
            with rd2:
                if st.button("Cancel", use_container_width=True, key="cancel_remove_panel"):
                    st.session_state.show_remove_selector = False
                    st.rerun()
        else:
            st.error(f"**Final confirmation:** permanently delete **{to_del}** and all {entry_count} entries?")
            cf1, cf2 = st.columns(2)
            with cf1:
                if st.button("Yes, permanently delete", type="primary",
                             use_container_width=True, key="del_stu_final"):
                    students = [s for s in students if s != to_del]
                    save_json(STUDENTS_FILE, students)
                    entries = load_json(DATA_FILE)
                    save_json(DATA_FILE,
                              [e for e in entries if e.get("student_name") != to_del])
                    st.session_state.confirm_del = False
                    st.session_state.show_remove_selector = False
                    st.rerun()
            with cf2:
                if st.button("Cancel", use_container_width=True, key="cancel_del"):
                    st.session_state.confirm_del = False
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Archive student panel ─────────────────────────────────────────────────
    if st.session_state.get("show_archive_selector") and students:
        arc_target = st.selectbox("Select student to archive", students, key="arc_sel_target")
        arc_entry_count = len([e for e in load_json(DATA_FILE) if e.get("student_name") == arc_target])
        st.info(
            f"📦 Archiving removes **{arc_target}** from the active list but preserves all "
            f"{arc_entry_count} entr{'ies' if arc_entry_count != 1 else 'y'} and profile info. "
            f"You can restore them at any time."
        )
        ar1, ar2 = st.columns(2)
        with ar1:
            if st.button("Archive Student", type="primary", use_container_width=True, key="arc_confirm"):
                active = load_json(STUDENTS_FILE)
                archive = load_archive()
                active = [s for s in active if s != arc_target]
                save_json(STUDENTS_FILE, active)
                archive.append({
                    "name": arc_target,
                    "archived_date": datetime.now().strftime("%Y-%m-%d"),
                    "entry_count": arc_entry_count,
                })
                save_archive(archive)
                audit_log("ARCHIVE_STUDENT", f"Archived student '{arc_target}' ({arc_entry_count} entries preserved)")
                st.session_state.show_archive_selector = False
                st.rerun()
        with ar2:
            if st.button("Cancel", use_container_width=True, key="arc_cancel"):
                st.session_state.show_archive_selector = False
                st.rerun()

    # ── Archived students section ─────────────────────────────────────────────
    archive = load_archive()
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:13px;font-weight:700;color:#6d28d9;'
        'letter-spacing:0.05em;text-transform:uppercase;margin-bottom:8px;">'
        '🗄 Archived Students</div>',
        unsafe_allow_html=True
    )
    if not archive:
        st.markdown(
            '<div style="background:#faf5ff;border:1.5px solid #e9d5ff;border-radius:12px;'
            'padding:16px 20px;text-align:center;color:#7c3aed;font-size:13px;">'
            'No archived students. Use <b>🗄 Archive Student</b> above to move a student here '
            'while preserving all their data.</div>',
            unsafe_allow_html=True
        )
    if archive:
        for idx, rec in enumerate(archive):
            arc_name = rec.get("name", "Unknown")
            arc_date = rec.get("archived_date", "")
            arc_count = rec.get("entry_count", 0)
            # Current actual entry count (data still in file)
            current_count = len([e for e in load_json(DATA_FILE) if e.get("student_name") == arc_name])
            col_info, col_restore, col_delete = st.columns([5, 1.4, 1.4])
            with col_info:
                st.markdown(
                    f'<div style="background:#faf5ff;border:1.5px solid #ddd6fe;border-radius:10px;'
                    f'padding:10px 14px;display:flex;align-items:center;gap:10px;">'
                    f'<div style="width:36px;height:36px;background:#ede9fe;border-radius:50%;'
                    f'display:flex;align-items:center;justify-content:center;'
                    f'color:#7c3aed;font-weight:700;font-size:14px;">{arc_name[0].upper()}</div>'
                    f'<div><div style="font-weight:700;color:#4c1d95;font-size:14px;">{arc_name}</div>'
                    f'<div style="font-size:12px;color:#7c3aed;">Archived {arc_date} &nbsp;·&nbsp; {current_count} entries</div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            with col_restore:
                if st.button("↩ Restore", use_container_width=True, key=f"restore_{idx}"):
                    active = load_json(STUDENTS_FILE)
                    if arc_name not in active:
                        active.append(arc_name)
                        save_json(STUDENTS_FILE, active)
                    updated_archive = [r for r in archive if r.get("name") != arc_name]
                    save_archive(updated_archive)
                    audit_log("RESTORE_STUDENT", f"Restored archived student '{arc_name}'")
                    st.rerun()
            with col_delete:
                if st.button("🗑 Delete", use_container_width=True, key=f"arc_del_{idx}"):
                    st.session_state[f"confirm_arc_del_{idx}"] = True
                    st.rerun()
            if st.session_state.get(f"confirm_arc_del_{idx}"):
                st.error(
                    f"Permanently delete **{arc_name}** and all {current_count} entries? "
                    f"This cannot be undone."
                )
                fd1, fd2 = st.columns(2)
                with fd1:
                    if st.button("Yes, permanently delete", type="primary",
                                 use_container_width=True, key=f"arc_del_confirm_{idx}"):
                        updated_archive = [r for r in archive if r.get("name") != arc_name]
                        save_archive(updated_archive)
                        all_entries = load_json(DATA_FILE)
                        save_json(DATA_FILE, [e for e in all_entries if e.get("student_name") != arc_name])
                        profiles = load_profiles()
                        if arc_name in profiles:
                            del profiles[arc_name]
                            save_profiles(profiles)
                        audit_log("DELETE_ARCHIVED_STUDENT", f"Permanently deleted archived student '{arc_name}'")
                        st.session_state.pop(f"confirm_arc_del_{idx}", None)
                        st.rerun()
                with fd2:
                    if st.button("Cancel", use_container_width=True, key=f"arc_del_cancel_{idx}"):
                        st.session_state.pop(f"confirm_arc_del_{idx}", None)
                        st.rerun()

# ── Tab: New Entry ────────────────────────────────────────────────────────────
def tab_new_entry(all_entries, student_name, observer_name):
    student_nums = [e.get("number", 0) for e in all_entries if e.get("student_name") == student_name]
    next_num = max(student_nums, default=0) + 1
    cats = load_categories()

    # Confirmation banner after save
    last_saved = st.session_state.pop("last_saved_entry", None)
    if last_saved:
        st.markdown(
            '<div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:12px;'
            'padding:16px 20px;margin-bottom:16px;display:flex;align-items:center;gap:12px;">'
            '<div style="font-size:22px;">✅</div>'
            '<div>'
            '<div style="font-weight:700;font-size:15px;color:#15803d;">Entry #' + str(last_saved) + ' recorded successfully</div>'
            '<div style="font-size:13px;color:#16a34a;margin-top:2px;">'
            'The observation has been saved. You can view it in the Log tab.</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # Card header
    st.markdown(f"""
    <div style="background:white;border:1.5px solid #e5e7eb;border-radius:14px;
                padding:20px 24px 0 24px;margin-bottom:0;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
            <div style="width:38px;height:38px;background:#dcfce7;border-radius:50%;
                        display:flex;align-items:center;justify-content:center;
                        color:#16a34a;font-weight:700;font-size:13px;flex-shrink:0;">
                #{next_num}
            </div>
            <div>
                <div style="font-weight:700;font-size:16px;color:#111;">
                    Record Observation
                </div>
                <div style="font-size:12px;color:#6b7280;">
                    Fill in all ABC fields. Required: Antecedent, Behavior, Consequence *
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    interval_type = None
    interval_length = None
    interval_number = None

    # ── Session-Level MO Checklist (outside form — persists across entries) ───
    with st.expander("⚡ Motivating Operations — Conditions Present Today", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Note any conditions present <b>before or during this session</b>. '
            'Check all that apply. These are saved with every entry recorded today '
            'and used to identify which conditions predict higher behavior rates.</div>',
            unsafe_allow_html=True
        )

        # ── Tier 1 auto-detect from prior entries this session ────────────────
        session_date_str = str(date.today())
        prior_today = [e for e in all_entries
                       if e.get("student_name") == student_name
                       and str(e.get("date", ""))[:10] == session_date_str]
        auto_flags = set()
        if prior_today:
            last_ant  = (prior_today[-1].get("antecedent") or "").lower()
            last_act  = (prior_today[-1].get("activity")  or "").lower()
            last_inst = (prior_today[-1].get("instructional_format") or "").lower()
            if any(w in last_ant for w in ["instruction", "direction", "request", "task", "demand"]):
                auto_flags.add("high_demand")
            if any(w in last_ant for w in ["transition", "activity"]):
                auto_flags.add("transition")
            if any(w in last_act for w in ["free", "unstructured", "leisure", "alone"]):
                auto_flags.add("sensory_under")
            if any(w in last_inst for w in ["independent", "seat work"]):
                auto_flags.add("independent_work")

        if auto_flags:
            auto_labels = []
            for domain, items in MO_DEFAULTS.items():
                for mo in items:
                    if mo["key"] in auto_flags:
                        auto_labels.append(mo["label"][:60] + "…")
            st.markdown(
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
                'padding:8px 12px;margin-bottom:10px;font-size:12px;color:#15803d;">'
                '<b>Auto-detected from today\'s entries:</b> ' + " · ".join(auto_labels) + '</div>',
                unsafe_allow_html=True
            )

        # ── Checkboxes by domain ──────────────────────────────────────────────
        if "mo_session_state" not in st.session_state:
            st.session_state.mo_session_state = {}

        for domain, items in MO_DEFAULTS.items():
            st.markdown(
                f'<div style="font-size:12px;font-weight:700;color:#374151;'
                f'margin:10px 0 4px 0;">{domain}</div>',
                unsafe_allow_html=True
            )
            for mo in items:
                is_auto = mo["key"] in auto_flags
                default_val = st.session_state.mo_session_state.get(mo["key"], is_auto)
                label = mo["label"]
                if is_auto:
                    label = "🔍 " + label + " (auto-detected)"
                checked = st.checkbox(label, value=default_val, key=f"mo_{mo['key']}")
                st.session_state.mo_session_state[mo["key"]] = checked

        # ── Custom MOs ────────────────────────────────────────────────────────
        custom_mos = cats.get("custom_mos", [])
        if custom_mos:
            st.markdown(
                '<div style="font-size:12px;font-weight:700;color:#374151;'
                'margin:10px 0 4px 0;">Custom</div>',
                unsafe_allow_html=True
            )
            for cmo in custom_mos:
                safe_key = "mo_custom_" + cmo[:30].replace(" ", "_")
                default_val = st.session_state.mo_session_state.get(safe_key, False)
                checked = st.checkbox(cmo, value=default_val, key=safe_key)
                st.session_state.mo_session_state[safe_key] = checked

        # ── Free text for Tier 3 / idiosyncratic conditions ───────────────────
        st.markdown(
            '<div style="font-size:12px;font-weight:700;color:#374151;margin:10px 0 4px 0;">'
            'Other conditions not listed above</div>',
            unsafe_allow_html=True
        )
        mo_notes = st.text_input(
            "Other MO notes",
            value=st.session_state.get("mo_notes_today", ""),
            placeholder="e.g. 'wore new shoes', 'substitute teacher', 'parent visit day'",
            label_visibility="collapsed",
            key="mo_notes_input"
        )
        st.session_state["mo_notes_today"] = mo_notes

        if st.button("✓ Save MO Conditions for This Session", key="save_mo_btn", type="primary"):
            st.success("MO conditions saved — they will be attached to all entries recorded today.")

    with st.form("abc_form", clear_on_submit=True):
        # Date / Time / Duration
        c1, c2, c3 = st.columns(3)
        with c1:
            entry_date = st.date_input("Date *", value=date.today())
        with c2:
            entry_time = st.time_input("Time *", value=datetime.now().time())
        with c3:
            obs_minutes = st.number_input("Observation Duration (min)",
                                          min_value=0.0, value=0.0,
                                          step=0.5, format="%.2f",
                                          placeholder="e.g. 30")

        # SETTING section
        st.markdown("""
        <div style="background:#f9fafb;border:1.5px solid #e5e7eb;border-radius:10px;
                    padding:16px 18px 4px 18px;margin:12px 0;">
            <div style="font-size:11px;font-weight:700;letter-spacing:.08em;
                        color:#6b7280;margin-bottom:12px;">SETTING</div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            location = st.selectbox("Location", [""] + cats["locations"],
                                    format_func=lambda x: "Select location" if x == "" else x)
        with c2:
            people = st.selectbox("People Intervening", [""] + cats["people_intervening"],
                                  format_func=lambda x: "Select people intervening" if x == "" else x)
        c1, c2 = st.columns(2)
        with c1:
            subject = st.selectbox("Subject", [""] + cats["subjects"],
                                   format_func=lambda x: "Select subject" if x == "" else x)
        with c2:
            activity = st.selectbox("Activity", [""] + cats["activities"],
                                    format_func=lambda x: "Select activity" if x == "" else x)
        inst_format = st.selectbox("Instructional Format", [""] + cats["instructional_formats"],
                                   format_func=lambda x: "Select instructional format" if x == "" else x)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── A-B-C section ─────────────────────────────────────────────────────
        st.markdown("""
        <div style="background:#f9fafb;border:1.5px solid #e5e7eb;border-radius:10px;
                    padding:16px 18px 4px 18px;margin:12px 0;">
            <div style="font-size:13px;font-weight:700;color:#16a34a;margin-bottom:12px;">
                A – B – C
            </div>
        """, unsafe_allow_html=True)

        antecedent = st.selectbox("Antecedent (A) *", [""] + cats["antecedents"],
                                  format_func=lambda x: "Select antecedent" if x == "" else x)
        behavior = st.selectbox("Behavior (B) *", [""] + cats["behaviors"],
                                format_func=lambda x: "Select behavior" if x == "" else x)
        # Show operational definition if one exists for the selected behavior
        if behavior:
            _beh_def = cats.get("behavior_definitions", {}).get(behavior, "").strip()
            if _beh_def:
                st.markdown(
                    f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;'
                    f'padding:10px 14px;margin:4px 0 8px 0;font-size:0.88rem;color:#1e40af;">'
                    f'<span style="font-weight:600;">📋 Operational Definition:</span> {_beh_def}'
                    f'</div>',
                    unsafe_allow_html=True
                )
        consequence = st.selectbox("Consequence (C) *", [""] + cats["consequences"],
                                   format_func=lambda x: "Select consequence" if x == "" else x)

        # ── Episode & Severity ────────────────────────────────────────────────
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        ep_col, sev_col = st.columns(2)
        with ep_col:
            episode_id = st.text_input(
                "Episode ID",
                placeholder="e.g. 'AM-episode-3' — links entries in same event",
                help="Tag entries that belong to the same behavioral episode or escalation chain.",
                key="episode_id_inp",
            )
        with sev_col:
            severity_tier = st.radio(
                "Severity Tier",
                options=["—", "Tier 1 — Mild", "Tier 2 — Moderate", "Tier 3 — Severe"],
                index=0,
                horizontal=True,
                key="severity_tier_inp",
                help="Tier 1 = low intensity / early escalation. Tier 3 = highest intensity / most dangerous.",
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Duration + Intensity ──────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Behavior Duration**")
            dc1, dc2 = st.columns([2, 1])
            with dc1:
                dur_amount = st.number_input("Amount", min_value=0, value=0,
                                             placeholder="Enter amount",
                                             label_visibility="collapsed")
            with dc2:
                dur_unit = st.selectbox("Unit", ["Seconds", "Minutes"],
                                        label_visibility="collapsed")

        # Intensity inside form
        st.markdown("**Intensity (1–10)**")
        intensity = st.radio("Intensity", options=list(range(1, 11)),
                             index=4, horizontal=True,
                             label_visibility="collapsed")

        # ── Notes + Photo attachment ──────────────────────────────────────────
        notes = st.text_area("Notes / Comments", placeholder="Additional observations...",
                             label_visibility="visible")

        st.markdown("**Attach Photo** *(optional)*")
        uploaded_image = st.file_uploader(
            "Photo", type=["jpg", "jpeg", "png"],
            label_visibility="collapsed", key="entry_photo"
        )
        if uploaded_image is not None:
            st.image(uploaded_image, width=180)

        submitted = st.form_submit_button(f"Save Entry #{next_num}", type="primary",
                                          use_container_width=True)

    if submitted:
        errors = []
        if not antecedent:
            errors.append("Antecedent (A) is required.")
        if not behavior:
            errors.append("Behavior (B) is required.")
        if not consequence:
            errors.append("Consequence (C) is required.")
        if entry_date > date.today():
            errors.append("Date cannot be in the future.")
        if errors:
            for err in errors:
                st.error(err)
            return
        # Encode image to base64 if provided
        image_b64 = None
        image_filename = None
        if uploaded_image is not None:
            image_b64 = base64.b64encode(uploaded_image.read()).decode("utf-8")
            image_filename = uploaded_image.name
        entry = {
            "number": next_num,
            "date": str(entry_date),
            "time": str(entry_time),
            "student_name": student_name,
            "student_id": roster_id_for_name(student_name),
            "observer_name": observer_name,
            "observation_duration_minutes": obs_minutes or None,
            "location": location or None,
            "people_intervening": people or None,
            "subject": subject or None,
            "activity": activity or None,
            "instructional_format": inst_format or None,
            "interval_type": interval_type,
            "interval_length_seconds": interval_length,
            "interval_number": interval_number,
            "antecedent": antecedent or None,
            "behavior": behavior,
            "consequence": consequence or None,
            "episode_id": episode_id.strip() or None,
            "severity_tier": severity_tier if severity_tier != "—" else None,
            "motivating_operations": {
                k: v for k, v in st.session_state.get("mo_session_state", {}).items() if v
            } or None,
            "mo_notes": st.session_state.get("mo_notes_today", "").strip() or None,
            "actual_duration_seconds": (dur_amount * 60 if dur_unit == "Minutes" else dur_amount) or None,
            "duration": duration_from_seconds(dur_amount * 60 if dur_unit == "Minutes" else dur_amount),
            "intensity": intensity,
            "notes": notes.strip() or None,
            "image_b64": image_b64,
            "image_filename": image_filename,
        }
        all_entries.append(entry)
        save_json(DATA_FILE, all_entries)
        audit_log("CREATE_ENTRY", f"Entry #{next_num} for student [{student_name}] behavior [{behavior}]")
        st.session_state["last_saved_entry"] = next_num
        st.rerun()

# ── Tab: Log ──────────────────────────────────────────────────────────────────
def fmt_duration(entry):
    s = entry.get("actual_duration_seconds")
    try:
        if not s or (isinstance(s, float) and (s != s)):  # None or NaN
            return "—"
        s = float(s)
        if s < 60:
            return f"{int(s)}s"
        return f"{int(s)//60}m {int(s)%60}s"
    except Exception:
        return "—"

def fmt_date(d):
    try:
        return datetime.strptime(str(d), "%Y-%m-%d").strftime("%m/%d/%y")
    except Exception:
        return str(d)

def fmt_time(t):
    try:
        return datetime.strptime(str(t)[:5], "%H:%M").strftime("%H:%M")
    except Exception:
        return str(t)[:5]

def truncate(text, n=30):
    if not text:
        return "—"
    text = str(text)
    return text[:n] + "..." if len(text) > n else text

INTENSITY_COLORS = {
    range(1, 4):  ("#dcfce7", "#16a34a"),  # low   — green
    range(4, 7):  ("#fef9c3", "#ca8a04"),  # mid   — yellow
    range(7, 11): ("#fee2e2", "#dc2626"),  # high  — red
}

def intensity_badge(val):
    try:
        if val is None or (isinstance(val, float) and val != val):
            return "—"
        val = int(val)
    except (TypeError, ValueError):
        return "—"
    for r, (bg, fg) in INTENSITY_COLORS.items():
        if val in r:
            return (f'<span style="background:{bg};color:{fg};font-weight:700;'
                    f'font-size:12px;padding:3px 8px;border-radius:20px;">{val}</span>')
    return str(val)

def behavior_badge(text, abbrevs=None):
    if not text:
        return "—"
    display = (abbrevs or {}).get(text, text)
    title = f' title="{text}"' if display != text else ""
    return (f'<span style="background:#dcfce7;color:#16a34a;font-weight:600;'
            f'font-size:12px;padding:4px 10px;border-radius:20px;cursor:default;"'
            f'{title}>{display}</span>')

def _apply_filters(entries, beh_key, obs_key, from_key, to_key):
    """Shared filter logic for Log and Summary tabs."""
    behaviors_seen = sorted(set(e.get("behavior", "") for e in entries if e.get("behavior")))
    observers_seen = sorted(set(e.get("observer_name", "") for e in entries if e.get("observer_name")))
    all_dates = sorted(set(e.get("date", "") for e in entries if e.get("date")))
    min_date = pd.to_datetime(all_dates[0]).date() if all_dates else date.today()
    max_date = pd.to_datetime(all_dates[-1]).date() if all_dates else date.today()

    fc1, fc2, fc3, fc4 = st.columns([3, 3, 2, 1])
    with fc1:
        beh_f = st.selectbox("Behavior", ["All behaviors"] + behaviors_seen,
                             key=beh_key, label_visibility="collapsed")
    with fc2:
        obs_f = st.selectbox("Observer", ["All observers"] + observers_seen,
                             key=obs_key, label_visibility="collapsed")
    with fc3:
        dr1, dr2 = st.columns(2)
        with dr1:
            date_from = st.date_input("From", value=min_date, key=from_key,
                                      label_visibility="visible")
        with dr2:
            date_to = st.date_input("To", value=max_date, key=to_key,
                                    label_visibility="visible")
    with fc4:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        if st.button("Clear", use_container_width=True, key=f"clear_{beh_key}"):
            st.session_state[beh_key] = "All behaviors"
            st.session_state[obs_key] = "All observers"
            st.session_state[from_key] = min_date
            st.session_state[to_key] = max_date
            st.rerun()

    filtered = entries
    if beh_f != "All behaviors":
        filtered = [e for e in filtered if e.get("behavior") == beh_f]
    if obs_f != "All observers":
        filtered = [e for e in filtered if e.get("observer_name") == obs_f]
    filtered = [e for e in filtered
                if e.get("date") and date_from <= pd.to_datetime(e["date"]).date() <= date_to]
    return filtered


def tab_log(filtered_entries, all_entries, student_name="", abbrevs=None):
    st.markdown(f"""
    <div style="font-size:18px;font-weight:700;color:#111;margin-bottom:10px;">
        Entries — {student_name}
    </div>""", unsafe_allow_html=True)

    if not filtered_entries:
        st.markdown(
            '<div style="text-align:center;padding:48px 20px;">'
            '<div style="font-size:40px;margin-bottom:12px;">📋</div>'
            '<div style="font-size:16px;font-weight:600;color:#374151;margin-bottom:6px;">No entries yet</div>'
            '<div style="font-size:13px;color:#9ca3af;">Go to the <b>📋 New ABC Entry</b> tab to record your first observation.</div>'
            '</div>',
            unsafe_allow_html=True
        )
        return

    # Free-text search
    search_q = st.text_input("🔍 Search entries", placeholder="Search notes, antecedents, consequences…",
                              key="log_search", label_visibility="collapsed")
    if search_q:
        q = search_q.lower()
        filtered_entries = [
            e for e in filtered_entries
            if any(q in str(e.get(f, "") or "").lower()
                   for f in ["antecedent", "behavior", "consequence", "notes",
                              "observer_name", "location", "activity"])
        ]

    filtered_entries = _apply_filters(filtered_entries,
                                      "log_beh_f", "log_obs_f",
                                      "log_date_from", "log_date_to")

    df = pd.DataFrame(filtered_entries).sort_values("number", ascending=False)
    csv = df.to_csv(index=False).encode()

    def _to_xlsx(dataframe):
        import io
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            return None
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="ABC Data")
        return buf.getvalue()

    xlsx_bytes = _to_xlsx(df)

    entry_label = "entry" if len(filtered_entries) == 1 else "entries"
    ec1, ec2, ec3 = st.columns([7, 2, 2])
    with ec1:
        st.markdown(
            f'<div style="background:#dcfce7;color:#16a34a;font-weight:600;font-size:13px;'
            f'padding:5px 12px;border-radius:20px;display:inline-block;margin:4px 0 8px 0;">'
            f'{len(filtered_entries)} {entry_label}</div>',
            unsafe_allow_html=True
        )
    with ec2:
        st.download_button("Export CSV", csv, "abc_data.csv", "text/csv",
                           key="dl_log", use_container_width=True)
    with ec3:
        if xlsx_bytes:
            st.download_button("Export XLSX", xlsx_bytes, "abc_data.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="dl_log_xlsx", use_container_width=True)
        else:
            st.caption("openpyxl not installed")

    # Build HTML table
    rows_html = ""
    for _, row in df.iterrows():
        episode = str(row.get("episode_id") or "").strip()
        episode = "" if episode.lower() in ("none", "nan") else episode
        episode_cell = (
            f'<span style="background:#ede9fe;color:#6d28d9;font-size:11px;'
            f'font-weight:600;padding:2px 7px;border-radius:10px;">{episode}</span>'
            if episode else "—"
        )
        _sev_raw = str(row.get("severity_tier") or "").strip()
        _sev_raw = "" if _sev_raw.lower() in ("none", "nan") else _sev_raw
        _sev_colors = {
            "Tier 1": ("#fef9c3", "#854d0e"),
            "Tier 2": ("#ffedd5", "#c2410c"),
            "Tier 3": ("#fee2e2", "#991b1b"),
        }
        _sev_key = _sev_raw[:6] if _sev_raw else ""
        _sev_bg, _sev_fg = _sev_colors.get(_sev_key, ("#f3f4f6", "#6b7280"))
        severity_cell = (
            f'<span style="background:{_sev_bg};color:{_sev_fg};font-size:11px;'
            f'font-weight:600;padding:2px 7px;border-radius:10px;">{_sev_raw}</span>'
            if _sev_raw else "—"
        )
        interval = row.get("interval_type") or ""
        interval_num = row.get("interval_number")
        interval_str = str(interval) if isinstance(interval, str) and interval else ""
        try:
            iv_num_str = str(int(interval_num)) if interval_num is not None else "—"
        except (ValueError, TypeError):
            iv_num_str = "—"
        interval_cell = (
            f'<span style="background:#fef9c3;color:#854d0e;font-size:11px;'
            f'font-weight:600;padding:2px 7px;border-radius:10px;">'
            f'{interval_str[:3]} #{iv_num_str}</span>'
            if interval_str else "—"
        )
        photo_cell = (
            '<span style="font-size:15px;" title="Photo attached">📷</span>'
            if row.get("image_b64") else "—"
        )
        rows_html += (
            '<tr>'
            f'<td style="font-weight:700;color:#374151;">{int(row.get("number") or 0)}</td>'
            f'<td>{fmt_date(row.get("date",""))}</td>'
            f'<td style="color:#6b7280;">{fmt_time(row.get("time",""))}</td>'
            f'<td style="font-weight:600;">{row.get("student_name","")}</td>'
            f'<td style="color:#6b7280;">{row.get("observer_name","") or "—"}</td>'
            f'<td>{row.get("location","") or "—"}</td>'
            f'<td style="color:#374151;max-width:120px;">{truncate(row.get("antecedent",""), 28)}</td>'
            f'<td>{behavior_badge(row.get("behavior",""), abbrevs)}</td>'
            f'<td style="color:#374151;max-width:120px;">{truncate(row.get("consequence",""), 28)}</td>'
            f'<td style="font-weight:600;">{fmt_duration(row)}</td>'
            f'<td>{intensity_badge(row.get("intensity"))}</td>'
            f'<td>{interval_cell}</td>'
            f'<td>{episode_cell}</td>'
            f'<td>{severity_cell}</td>'
            f'<td style="text-align:center;">{photo_cell}</td>'
            '</tr>'
        )

    header_cells = "".join(
        f'<th style="padding:10px 12px;text-align:left;font-size:11px;'
        f'font-weight:700;letter-spacing:.06em;color:#6b7280;">{h}</th>'
        for h in ["#", "DATE", "TIME", "STUDENT", "OBSERVER", "LOCATION",
                  "ANTECEDENT", "BEHAVIOR", "CONSEQUENCE", "DURATION", "INT",
                  "INTERVAL", "EPISODE", "SEVERITY", "📷"]
    )
    table_html = (
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
        'overflow:hidden;margin-top:8px;">'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:13px;'
        'font-family:system-ui,sans-serif;">'
        '<thead><tr style="border-bottom:1.5px solid #e5e7eb;">'
        + header_cells +
        '</tr></thead>'
        '<tbody>' + rows_html + '</tbody>'
        '</table></div></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Photo viewer ──────────────────────────────────────────────────────────
    photo_entries = [e for e in filtered_entries if e.get("image_b64")]
    if photo_entries:
        with st.expander(f"📷 View attached photos ({len(photo_entries)})"):
            cols = st.columns(3)
            for i, e in enumerate(photo_entries):
                with cols[i % 3]:
                    img_data = base64.b64decode(e["image_b64"])
                    st.image(img_data, caption=f"Entry #{e.get('number')} — {e.get('behavior','')}", use_container_width=True)
                    if e.get("notes"):
                        st.caption(e["notes"])

    st.markdown("<br>", unsafe_allow_html=True)
    nums = sorted([e.get("number") for e in filtered_entries if e.get("number")], reverse=True)

    # ── Edit an entry ─────────────────────────────────────────────────────────
    with st.expander("✏️ Edit an entry"):
        cats = load_categories()
        edit_num = st.selectbox("Select entry to edit", nums, key="edit_entry_num",
                                format_func=lambda n: f"Entry #{n}")
        edit_entry = next((e for e in filtered_entries if e.get("number") == edit_num), None)
        if edit_entry:
            with st.form("edit_entry_form"):
                ee1, ee2 = st.columns(2)
                with ee1:
                    e_date = st.date_input("Date", value=pd.to_datetime(edit_entry.get("date", date.today())).date())
                with ee2:
                    try:
                        t_val = datetime.strptime(str(edit_entry.get("time","00:00"))[:5], "%H:%M").time()
                    except Exception:
                        t_val = datetime.now().time()
                    e_time = st.time_input("Time", value=t_val)

                e_ant = st.selectbox("Antecedent (A) *", [""] + cats["antecedents"],
                                     index=([""] + cats["antecedents"]).index(edit_entry.get("antecedent",""))
                                     if edit_entry.get("antecedent","") in cats["antecedents"] else 0)
                e_beh = st.selectbox("Behavior (B) *", [""] + cats["behaviors"],
                                     index=([""] + cats["behaviors"]).index(edit_entry.get("behavior",""))
                                     if edit_entry.get("behavior","") in cats["behaviors"] else 0)
                e_con = st.selectbox("Consequence (C) *", [""] + cats["consequences"],
                                     index=([""] + cats["consequences"]).index(edit_entry.get("consequence",""))
                                     if edit_entry.get("consequence","") in cats["consequences"] else 0)

                ee3, ee4 = st.columns(2)
                with ee3:
                    loc_opts = [""] + LOCATIONS
                    e_loc = st.selectbox("Location", loc_opts,
                                         index=loc_opts.index(edit_entry.get("location",""))
                                         if edit_entry.get("location","") in loc_opts else 0)
                with ee4:
                    e_intensity = st.radio("Intensity (1–10)", options=list(range(1,11)),
                                           index=int(edit_entry.get("intensity", 5)) - 1,
                                           horizontal=True)
                e_notes = st.text_area("Notes", value=edit_entry.get("notes","") or "")
                save_edit = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)

            if save_edit:
                edit_errors = []
                if not e_ant:
                    edit_errors.append("Antecedent is required.")
                if not e_beh:
                    edit_errors.append("Behavior is required.")
                if not e_con:
                    edit_errors.append("Consequence is required.")
                if e_date > date.today():
                    edit_errors.append("Date cannot be in the future.")
                if edit_errors:
                    for err in edit_errors:
                        st.error(err)
                else:
                    updated = []
                    for e in all_entries:
                        if e.get("number") == edit_num and e.get("student_name") == student_name:
                            e = dict(e)
                            e["date"] = str(e_date)
                            e["time"] = str(e_time)
                            e["antecedent"] = e_ant or None
                            e["behavior"] = e_beh
                            e["consequence"] = e_con or None
                            e["location"] = e_loc or None
                            e["intensity"] = e_intensity
                            e["notes"] = e_notes.strip() or None
                        updated.append(e)
                    save_json(DATA_FILE, updated)
                    audit_log("EDIT_ENTRY", f"Entry #{edit_num} edited for student [{student_name}]")
                    st.success(f"Entry #{edit_num} updated.")
                    st.rerun()

    # ── Delete an entry ───────────────────────────────────────────────────────
    with st.expander("🗑 Delete an entry"):
        c1, c2 = st.columns([3, 1])
        with c1:
            del_num = st.selectbox("Entry #", nums, key="del_num",
                                   label_visibility="collapsed",
                                   format_func=lambda n: f"Entry #{n}")
        with c2:
            if st.button("Delete", type="secondary", use_container_width=True):
                save_json(DATA_FILE,
                          [e for e in all_entries if e.get("number") != del_num])
                audit_log("DELETE_ENTRY", f"Entry #{del_num} deleted")
                st.success(f"Entry #{del_num} deleted.")
                st.rerun()

# ── PDF Report helpers ────────────────────────────────────────────────────────
def _fig_to_svg(fig, width=680, height=300):
    """Export a Plotly figure as an SVG string (requires kaleido)."""
    try:
        return fig.to_image(format="svg", width=width, height=height).decode("utf-8")
    except Exception:
        return ""

_PLOTLY_CONFIG = {
    "toImageButtonOptions": {"format": "jpeg", "scale": 2, "filename": "fba_chart"},
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
}


def _chart_block(title, svg):
    if not svg:
        return ""
    return (
        f'<h3 style="font-size:13px;font-weight:700;color:#374151;margin:28px 0 6px 0;'
        f'border-bottom:1.5px solid #e5e7eb;padding-bottom:5px;">{title}</h3>'
        f'<div style="max-width:100%;">{svg}</div>'
    )


def generate_pdf_report(filtered_entries, student_name, observer_name=""):
    """Build a styled HTML report with vector SVG charts and return HTML bytes."""

    df = pd.DataFrame(filtered_entries)

    # ── Metrics ──────────────────────────────────────────────────────────────
    date_range = ""
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"]).sort_values()
        date_range = (dates.min().strftime("%b %d, %Y")
                      + " \u2013 " + dates.max().strftime("%b %d, %Y"))

    total = len(df)
    avg_int = (f"{df['intensity'].mean():.1f}"
               if "intensity" in df.columns and df["intensity"].notna().any() else "\u2014")
    most_common = (df["behavior"].mode()[0]
                   if "behavior" in df.columns and len(df) else "\u2014")
    total_min = None
    behavior_rate = None
    if "observation_duration_minutes" in df.columns and \
            df["observation_duration_minutes"].notna().any():
        total_min = df["observation_duration_minutes"].sum()
        behavior_rate = len(df) / total_min if total_min else None
    rate_str = (f"{behavior_rate:.2f} resp/min" if behavior_rate else "\u2014")

    if "date" in df.columns:
        session_counts = (df.groupby(["date", "setting"]).size()
                          if "setting" in df.columns else df.groupby("date").size())
        freq_range_str = f"{int(session_counts.min())} \u2013 {int(session_counts.max())}"
    else:
        freq_range_str = "\u2014"

    # ── Charts ───────────────────────────────────────────────────────────────
    charts_html = ""

    # 1. Behavior frequency
    if "behavior" in df.columns:
        bc = df["behavior"].value_counts().reset_index()
        bc.columns = ["behavior", "count"]
        f1 = px.bar(bc, x="behavior", y="count", text="count",
                    color_discrete_sequence=["#16a34a"])
        f1.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        f1.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                         font_family="system-ui", height=300,
                         margin=dict(l=10, r=10, t=20, b=60),
                         xaxis=dict(tickangle=-30, gridcolor="#e5e7eb"),
                         yaxis=dict(gridcolor="#e5e7eb", dtick=1,
                                    range=[0, int(bc["count"].max()) + 1]))
        charts_html += _chart_block("Behavior Frequency", _fig_to_svg(f1))

    # 2. Frequency by day of week
    if "date" in df.columns:
        day_order = ["Monday", "Tuesday", "Wednesday",
                     "Thursday", "Friday", "Saturday", "Sunday"]
        df["_dow"] = pd.to_datetime(df["date"]).dt.day_name()
        dow = df.groupby("_dow").size().reset_index(name="count")
        dow["_dow"] = pd.Categorical(dow["_dow"], categories=day_order, ordered=True)
        dow = dow.sort_values("_dow")
        f2 = px.bar(dow, x="_dow", y="count", text="count",
                    labels={"_dow": ""}, color_discrete_sequence=["#16a34a"])
        f2.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        f2.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                         font_family="system-ui", height=260,
                         margin=dict(l=10, r=10, t=20, b=40),
                         xaxis=dict(gridcolor="#e5e7eb"),
                         yaxis=dict(gridcolor="#e5e7eb", dtick=1,
                                    range=[0, int(dow["count"].max()) + 1]))
        charts_html += _chart_block("Frequency by Day of Week", _fig_to_svg(f2))

    # 3. Behaviors over time + trend lines
    if "date" in df.columns and "behavior" in df.columns:
        df["_date_only"] = pd.to_datetime(df["date"]).dt.normalize()
        td = df.groupby(["_date_only", "behavior"]).size().reset_index(name="count")
        clrs = px.colors.qualitative.Safe
        f3 = _go.Figure()
        for idx, beh in enumerate(td["behavior"].unique()):
            bdf = td[td["behavior"] == beh].sort_values("_date_only")
            c = clrs[idx % len(clrs)]
            f3.add_trace(_go.Scatter(x=bdf["_date_only"], y=bdf["count"],
                                     mode="lines+markers", name=beh,
                                     line=dict(color=c, width=2), marker=dict(size=6)))
            if len(bdf) >= 3:
                xn = (bdf["_date_only"] - bdf["_date_only"].min()).dt.days.values
                z = np.polyfit(xn, bdf["count"].values, 1)
                p = np.poly1d(z)
                xr = np.linspace(xn.min(), xn.max(), 50)
                xd = [bdf["_date_only"].min() + pd.Timedelta(days=int(d)) for d in xr]
                arrow = "\u2191" if z[0] > 0 else "\u2193"
                f3.add_trace(_go.Scatter(x=xd, y=p(xr), mode="lines",
                                         name=f"{beh} trend {arrow}",
                                         line=dict(color=c, width=1.5, dash="dash")))
        max_t = int(td["count"].max()) if len(td) else 1
        f3.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                         font_family="system-ui", height=320,
                         xaxis=dict(tickformat="%b %d, %Y", gridcolor="#e5e7eb"),
                         yaxis=dict(gridcolor="#e5e7eb", dtick=1, range=[0, max_t + 1]),
                         legend=dict(orientation="h", y=1.08),
                         margin=dict(l=10, r=10, t=50, b=40))
        charts_html += _chart_block("Behaviors Over Time + Trend Lines",
                                    _fig_to_svg(f3, height=320))

    # 4. Time-of-day heatmap
    if "time" in df.columns and "behavior" in df.columns:
        def _hr(t):
            try:
                return int(str(t).split(":")[0])
            except Exception:
                return None
        df["_hr"] = df["time"].apply(_hr)
        dh = df.dropna(subset=["_hr"])
        if len(dh):
            hb = dh.groupby(["_hr", "behavior"]).size().reset_index(name="count")
            all_hr = list(range(7, 21))
            all_beh = sorted(dh["behavior"].unique())
            piv = hb.pivot(index="behavior", columns="_hr", values="count")\
                    .reindex(index=all_beh, columns=all_hr).fillna(0)
            hl = [f"{h}am" if h < 12 else ("12pm" if h == 12 else f"{h-12}pm")
                  for h in all_hr]
            ht = max(200, len(all_beh) * 40 + 80)
            f4 = _go.Figure(data=_go.Heatmap(
                z=piv.values.tolist(), x=hl, y=list(piv.index),
                colorscale=[[0, "#f0fdf4"], [0.5, "#4ade80"], [1, "#15803d"]],
                showscale=True))
            f4.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                             font_family="system-ui", height=ht,
                             margin=dict(l=10, r=10, t=10, b=40))
            charts_html += _chart_block("Time-of-Day Heatmap",
                                        _fig_to_svg(f4, height=ht))

    # 5. Antecedent → Behavior heatmap
    if "antecedent" in df.columns and "behavior" in df.columns:
        dab = df.dropna(subset=["antecedent", "behavior"])
        dab = dab[dab["antecedent"] != ""]
        if len(dab):
            ab = dab.groupby(["antecedent", "behavior"]).size().reset_index(name="count")
            pab = ab.pivot(index="antecedent", columns="behavior", values="count").fillna(0)
            ht2 = max(200, len(pab.index) * 40 + 100)
            f5 = _go.Figure(data=_go.Heatmap(
                z=pab.values.tolist(), x=list(pab.columns), y=list(pab.index),
                colorscale=[[0, "#fff7ed"], [0.5, "#fb923c"], [1, "#c2410c"]],
                showscale=True))
            f5.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                             font_family="system-ui", height=ht2,
                             margin=dict(l=10, r=10, t=10, b=60),
                             xaxis=dict(tickangle=-30))
            charts_html += _chart_block("Antecedent \u2192 Behavior Heatmap",
                                        _fig_to_svg(f5, height=ht2))

    # ── HTML template ─────────────────────────────────────────────────────────
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        "body{font-family:system-ui,-apple-system,sans-serif;color:#111;"
        "margin:0;padding:0;background:white;}"
        ".header{background:#1e2d3d;color:white;padding:28px 40px 22px 40px;}"
        ".header h1{font-size:22px;font-weight:800;margin:0;color:white;}"
        ".header p{font-size:12px;color:#94a3b8;margin:5px 0 0 0;}"
        ".body{padding:32px 40px;}"
        ".metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:24px;}"
        ".metric{border:1.5px solid #e5e7eb;border-radius:10px;padding:12px 14px;}"
        ".mv{font-size:24px;font-weight:700;color:#16a34a;line-height:1.1;}"
        ".ml{font-size:11px;font-weight:700;color:#111;margin-top:3px;}"
        ".ms{font-size:10px;color:#6b7280;}"
        "svg{max-width:100%;height:auto;display:block;}"
        "</style></head><body>"
        "<div class='header'>"
        "<h1>FBA Summary Report \u2014 " + student_name + "</h1>"
        "<p>" + date_range + " &nbsp;\u00b7&nbsp; Observer: "
        + (observer_name or "\u2014") + " &nbsp;\u00b7&nbsp; Generated: "
        + datetime.now().strftime("%b %d, %Y") + "</p>"
        "<p style='color:#f87171;font-size:11px;font-weight:700;letter-spacing:.08em;margin-top:4px;'>"
        "CONFIDENTIAL — CONTAINS PROTECTED HEALTH INFORMATION (PHI) — "
        "HIPAA PROTECTED — DO NOT DISTRIBUTE WITHOUT AUTHORIZATION</p>"
        "</div>"
        "<div class='body'>"
        "<div class='metrics'>"
        "<div class='metric'><div class='mv'>" + str(total) + "</div>"
        "<div class='ml'>Total Entries</div></div>"
        "<div class='metric'><div class='mv'>" + avg_int + "</div>"
        "<div class='ml'>Avg. Intensity</div><div class='ms'>out of 10</div></div>"
        "<div class='metric'><div class='mv' style='font-size:16px;'>" + most_common + "</div>"
        "<div class='ml'>Most Common Behavior</div></div>"
        "<div class='metric'><div class='mv' style='font-size:16px;'>" + rate_str + "</div>"
        "<div class='ml'>Behavior Rate</div></div>"
        "<div class='metric'><div class='mv'>" + freq_range_str + "</div>"
        "<div class='ml'>Occurrence Range</div><div class='ms'>per session</div></div>"
        "</div>"
        + charts_html +
        "</div></body></html>"
    )

    # Add print CSS so browser prints cleanly
    html = html.replace(
        "</style>",
        "@media print { body { margin: 0; } .no-print { display: none; } }</style>"
    )
    return html.encode("utf-8"), None


# ── Tab: Summary ──────────────────────────────────────────────────────────────
def tab_summary(filtered_entries):
    if not filtered_entries:
        st.markdown("""
        <div style="text-align:center;padding:48px;color:#9ca3af;font-size:14px;">
            No data to summarize yet.
        </div>""", unsafe_allow_html=True)
        return

    filtered_entries = _apply_filters(filtered_entries,
                                      "sum_beh_f", "sum_obs_f",
                                      "sum_date_from", "sum_date_to")
    if not filtered_entries:
        st.info("No entries match the current filters.")
        return

    df = pd.DataFrame(filtered_entries)
    BLUE = "#4f6ef7"

    # ── PDF Export ────────────────────────────────────────────────────────────
    student_name_pdf = df["student_name"].iloc[0] if "student_name" in df.columns else "Student"
    observer_name_pdf = df["observer_name"].iloc[0] if "observer_name" in df.columns else ""
    pdf_col, _ = st.columns([2, 6])
    with pdf_col:
        if st.button("Export Report", use_container_width=True, key="pdf_btn"):
            with st.spinner("Generating report…"):
                html_bytes, err = generate_pdf_report(
                    filtered_entries, student_name_pdf, observer_name_pdf
                )
            if err:
                st.error(f"Report generation failed: {err}")
            else:
                st.download_button(
                    "Download Report (HTML)",
                    data=html_bytes,
                    file_name=f"FBA_Report_{student_name_pdf.replace(' ', '_')}.html",
                    mime="text/html",
                    key="pdf_dl",
                )
                st.caption("Open the file in your browser → File → Print → Save as PDF")

    # ── Intervals of Agreement ────────────────────────────────────────────────
    show_ioa = st.checkbox("Show Intervals of Agreement", key="show_ioa_cb")
    if show_ioa:
        if "observer_name" in df.columns:
            observers = [o for o in df["observer_name"].dropna().unique() if o]
        else:
            observers = []
        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;'
            'border-radius:12px;padding:20px;margin-top:8px;">'
            '<div style="font-weight:600;font-size:15px;color:#111;margin-bottom:4px;">'
            'Intervals of Agreement</div>'
            '<div style="font-size:12px;color:#6b7280;margin-bottom:14px;">'
            'Compare two observers on the same date to calculate agreement %</div>',
            unsafe_allow_html=True
        )
        if len(observers) >= 2:
            irr_c1, irr_c2 = st.columns(2)
            with irr_c1:
                obs1 = st.selectbox("Observer 1", observers, key="irr_obs1")
            with irr_c2:
                obs2_opts = [o for o in observers if o != obs1]
                obs2 = st.selectbox("Observer 2", obs2_opts, key="irr_obs2") if obs2_opts else None
            if obs2:
                df1 = df[df["observer_name"] == obs1].copy()
                df2 = df[df["observer_name"] == obs2].copy()
                shared_dates = set(df1["date"].unique()) & set(df2["date"].unique())
                if shared_dates:
                    irr_rows = []
                    for d in sorted(shared_dates):
                        b1 = set(df1[df1["date"] == d]["behavior"].dropna())
                        b2 = set(df2[df2["date"] == d]["behavior"].dropna())
                        if b1 or b2:
                            agree = len(b1 & b2)
                            total = len(b1 | b2)
                            pct = round(agree / total * 100, 1) if total else 100.0
                            irr_rows.append({"Date": d, "Observer 1": obs1, "Observer 2": obs2,
                                             "Agreements": agree, "Total Behaviors": total,
                                             "Agreement %": f"{pct}%"})
                    if irr_rows:
                        irr_df = pd.DataFrame(irr_rows)
                        avg_pct = irr_df["Agreement %"].apply(lambda x: float(x.strip("%"))).mean()
                        color = "#15803d" if avg_pct >= 80 else ("#d97706" if avg_pct >= 60 else "#dc2626")
                        st.markdown(
                            f'<div style="font-size:28px;font-weight:800;color:{color};margin-bottom:8px;">'
                            f'{avg_pct:.1f}% <span style="font-size:14px;font-weight:500;color:#6b7280;">'
                            f'average agreement across {len(irr_rows)} shared session(s)</span></div>',
                            unsafe_allow_html=True
                        )
                        st.dataframe(irr_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("No shared session dates found.")
                else:
                    st.info("These two observers have no entries on the same date.")
        else:
            st.info("At least two observers with data are needed for this analysis.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Dimension of Behavior Fields header ──────────────────────────────────
    st.markdown(
        '<div style="font-weight:700;font-size:15px;color:#111;margin-top:16px;margin-bottom:8px;">'
        'Dimension of Behavior Fields</div>',
        unsafe_allow_html=True
    )

    # ── Metric cards ──────────────────────────────────────────────────────────
    avg_intensity = f"{df['intensity'].mean():.1f}" if "intensity" in df.columns else "—"
    most_common = df["behavior"].mode()[0] if "behavior" in df.columns and len(df) else "—"

    total_min = None
    behavior_rate = None
    if "observation_duration_minutes" in df.columns and \
            df["observation_duration_minutes"].notna().any():
        total_min = df["observation_duration_minutes"].sum()
        behavior_rate = len(df) / total_min if total_min else None

    rate_str = f"{behavior_rate:.2f}" if behavior_rate is not None else "—"
    rate_sub = f"responses/min ({total_min} min observed)" if total_min else "no observation time recorded"

    # Frequency range: count entries per (date, setting) session
    if "date" in df.columns:
        session_counts = df.groupby(["date", "setting"]).size() if "setting" in df.columns \
            else df.groupby("date").size()
        freq_min = int(session_counts.min())
        freq_max = int(session_counts.max())
        freq_range_str = f"{freq_min} – {freq_max}"
        freq_range_sub = "occurrences per session"
    else:
        freq_range_str = "—"
        freq_range_sub = "no session data"

    st.markdown(
        '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px;">'
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;padding:20px 18px;">'
        '<div style="font-size:36px;font-weight:700;color:#16a34a;">' + str(len(df)) + '</div>'
        '<div style="font-size:14px;font-weight:600;color:#111;margin-top:4px;">Total Entries</div>'
        '</div>'
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;padding:20px 18px;">'
        '<div style="font-size:36px;font-weight:700;color:#16a34a;">' + avg_intensity + '</div>'
        '<div style="font-size:14px;font-weight:600;color:#111;margin-top:4px;">Avg. Intensity</div>'
        '<div style="font-size:12px;color:#6b7280;">out of 10</div>'
        '</div>'
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;padding:20px 18px;">'
        '<div style="font-size:22px;font-weight:700;color:#16a34a;line-height:1.2;">' + most_common + '</div>'
        '<div style="font-size:14px;font-weight:600;color:#111;margin-top:4px;">Most Common Behavior</div>'
        '</div>'
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;padding:20px 18px;">'
        '<div style="font-size:36px;font-weight:700;color:#16a34a;">' + rate_str + '</div>'
        '<div style="font-size:14px;font-weight:600;color:#111;margin-top:4px;">Behavior Rate</div>'
        '<div style="font-size:12px;color:#6b7280;">' + rate_sub + '</div>'
        '</div>'
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;padding:20px 18px;">'
        '<div style="font-size:32px;font-weight:700;color:#16a34a;">' + freq_range_str + '</div>'
        '<div style="font-size:14px;font-weight:600;color:#111;margin-top:4px;">Range of Occurrences (min–max)</div>'
        '<div style="font-size:12px;color:#6b7280;">' + freq_range_sub + '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Behavior Rate box ─────────────────────────────────────────────────────
    if behavior_rate is not None:
        mins_between = 1 / behavior_rate if behavior_rate > 0 else None
        per_hour = behavior_rate * 60

        if mins_between is not None and mins_between >= 1:
            freq_whole = int(mins_between)
            freq_secs  = int((mins_between - freq_whole) * 60)
            if freq_secs > 0:
                plain_freq = f"approximately once every {freq_whole} min {freq_secs} sec"
            else:
                plain_freq = f"approximately once every {freq_whole} minute{'s' if freq_whole != 1 else ''}"
        elif mins_between is not None:
            plain_freq = f"approximately {int(1/mins_between)} times per minute"
        else:
            plain_freq = ""

        st.markdown(
            '<div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-radius:12px;'
            'padding:20px 24px;margin-bottom:20px;">'
            '<div style="font-size:13px;font-weight:700;color:#16a34a;margin-bottom:12px;">'
            'Behavior Rate</div>'
            '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px;">'
            '<span style="font-size:36px;font-weight:800;color:#16a34a;">' + f"{behavior_rate:.2f}" + '</span>'
            '<span style="font-size:15px;color:#374151;">responses / min</span>'
            '</div>'
            '<div style="font-size:14px;color:#374151;margin:8px 0 4px 0;">'
            'That is <b>' + plain_freq + '</b>, or about <b>' + f"{per_hour:.0f}" + ' behaviors per hour</b>.'
            '</div>'
            '<div style="font-size:12px;color:#9ca3af;margin-top:8px;padding-top:8px;'
            'border-top:1px solid #bbf7d0;">'
            + str(len(df)) + ' observed behaviors &divide; ' + str(total_min) + ' minutes of observation'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # ── Setting field charts ──────────────────────────────────────────────────
    setting_fields = [
        ("location",             "Location"),
        ("people_intervening",   "People Intervening"),
        ("subject",              "Subject"),
        ("activity",             "Activity"),
        ("instructional_format", "Instructional Format"),
    ]
    setting_cols = [f for f, _ in setting_fields if f in df.columns and df[f].notna().any()]
    if setting_cols:
        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
            'padding:20px;margin-top:12px;">'
            '<div style="font-weight:700;font-size:15px;color:#111;margin-bottom:16px;">'
            'Setting Fields</div>',
            unsafe_allow_html=True
        )
        field_labels = dict(setting_fields)
        for i in range(0, len(setting_cols), 2):
            pair = setting_cols[i:i+2]
            gcols = st.columns(len(pair))
            for col, field in zip(gcols, pair):
                with col:
                    counts = (
                        df[field].dropna()
                        .loc[df[field] != ""]
                        .value_counts()
                        .reset_index()
                    )
                    counts.columns = ["value", "count"]
                    if len(counts):
                        fig_s = px.bar(
                            counts, x="count", y="value", orientation="h",
                            text="count",
                            labels={"value": "", "count": "Count"},
                            color_discrete_sequence=["#4f6ef7"],
                        )
                        fig_s.update_traces(texttemplate="%{text:.0f}", textposition="outside")
                        fig_s.update_layout(
                            plot_bgcolor="white", paper_bgcolor="white",
                            font_family="system-ui",
                            height=max(200, len(counts) * 44 + 80),
                            margin=dict(l=0, r=50, t=10, b=50),
                            xaxis=dict(gridcolor="#e5e7eb", automargin=True, tickformat="d"),
                            yaxis=dict(autorange="reversed", automargin=True),
                        )
                        field_subtitles = {
                            "location": "The physical environment where the behavior was observed.",
                            "people_intervening": "The individuals present or responding at the time of the behavior.",
                            "subject": "The academic or curricular area being addressed during the observation.",
                            "activity": "The task or activity the student was engaged in when the behavior occurred.",
                            "instructional_format": "The type of instructional arrangement in place during the observation.",
                        }
                        subtitle = field_subtitles.get(field, "")
                        st.markdown(
                            f'<div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:2px;">'
                            f'{field_labels[field]}</div>'
                            + (f'<div style="font-size:11px;color:#6b7280;margin-bottom:6px;">{subtitle}</div>' if subtitle else ''),
                            unsafe_allow_html=True
                        )
                        st.plotly_chart(fig_s, use_container_width=True, config=_PLOTLY_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── ABC Fields ───────────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
        'padding:20px;margin-top:12px;">'
        '<div style="font-weight:700;font-size:15px;color:#111;margin-bottom:16px;">'
        'ABC Fields</div>',
        unsafe_allow_html=True
    )
    c1, c2 = st.columns(2)
    with c1:
        if "behavior" in df.columns:
            beh_counts = df["behavior"].value_counts().reset_index()
            beh_counts.columns = ["behavior", "count"]
            fig = px.bar(beh_counts, y="behavior", x="count",
                         orientation="h", title="",
                         labels={"behavior": "", "count": ""},
                         color_discrete_sequence=[BLUE])
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              font_family="system-ui", margin=dict(l=0,r=50,t=10,b=50),
                              height=300, xaxis=dict(tickformat="d"),
                              yaxis=dict(autorange="reversed", automargin=True))
            fig.update_traces(text=beh_counts["count"], textposition="inside",
                              texttemplate="%{text:.0f}",
                              insidetextfont=dict(color="white", size=13))
            st.markdown("""<div style="background:white;border:1.5px solid #e5e7eb;
                border-radius:12px;padding:16px;">
                <div style="font-weight:600;font-size:15px;color:#111;margin-bottom:8px;">
                Behaviors</div>""", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        if "antecedent" in df.columns:
            ant_counts = df["antecedent"].value_counts().reset_index()
            ant_counts.columns = ["antecedent", "count"]
            fig = px.bar(ant_counts, y="antecedent", x="count",
                         orientation="h", title="",
                         labels={"antecedent": "", "count": ""},
                         color_discrete_sequence=["#818cf8"])
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              font_family="system-ui", margin=dict(l=0,r=50,t=10,b=50),
                              height=300, xaxis=dict(tickformat="d"),
                              yaxis=dict(autorange="reversed", automargin=True))
            fig.update_traces(text=ant_counts["count"], textposition="inside",
                              texttemplate="%{text:.0f}",
                              insidetextfont=dict(color="white", size=13))
            st.markdown("""<div style="background:white;border:1.5px solid #e5e7eb;
                border-radius:12px;padding:16px;">
                <div style="font-weight:600;font-size:15px;color:#111;margin-bottom:4px;">
                Antecedents</div>
                <div style="font-size:12px;color:#6b7280;margin-bottom:8px;">
                An antecedent is any event or stimulus that occurs before a behavior and may include one or multiple factors that set the occasion for the behavior to occur.</div>""",
                unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if "consequence" in df.columns:
            con_counts = df["consequence"].value_counts().reset_index()
            con_counts.columns = ["consequence", "count"]
            fig = px.bar(con_counts, y="consequence", x="count",
                         orientation="h", title="",
                         labels={"consequence": "", "count": ""},
                         color_discrete_sequence=["#60a5fa"])
            fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                              font_family="system-ui", margin=dict(l=0,r=50,t=10,b=50),
                              height=260, xaxis=dict(tickformat="d"),
                              yaxis=dict(autorange="reversed", automargin=True))
            fig.update_traces(text=con_counts["count"], textposition="inside",
                              texttemplate="%{text:.0f}",
                              insidetextfont=dict(color="white", size=13))
            st.markdown("""<div style="background:white;border:1.5px solid #e5e7eb;
                border-radius:12px;padding:16px;">
                <div style="font-weight:600;font-size:15px;color:#111;margin-bottom:4px;">
                Consequences</div>
                <div style="font-size:12px;color:#6b7280;margin-bottom:8px;">
                A consequence is any event or stimulus that occurs after a behavior.</div>""",
                unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Function of the Behavior ─────────────────────────────────────────────
    FUNC_DEFS = [
        ("Att", "Positive Reinforcement-\nAttention",   "#7b9cb8"),
        ("Tan", "Positive Reinforcement-\nTangibles",   "#8ab87b"),
        ("Esc", "Negative Reinforcement-\nEscape",      "#c9a840"),
        ("Sel", "Automatic reinforcement-\nSensory",    "#c97a5a"),
    ]

    def _tags(text):
        return re.findall(r'\(([A-Za-z]+)\)', str(text) if text else "")

    ant_fc = {d[0]: 0 for d in FUNC_DEFS}
    con_fc = {d[0]: 0 for d in FUNC_DEFS}
    for _, row in df.iterrows():
        for t in _tags(row.get("antecedent", "")):
            if t in ant_fc: ant_fc[t] += 1
        for t in _tags(row.get("consequence", "")):
            if t in con_fc: con_fc[t] += 1

    totals_fc = {d[0]: ant_fc[d[0]] + con_fc[d[0]] for d in FUNC_DEFS}

    if any(totals_fc.values()):
        # Short x-axis labels (no newlines)
        FUNC_SHORT = ["Attention", "Tangibles", "Escape", "Sensory"]
        FUNC_FULL  = [
            "Positive Reinforcement – Attention",
            "Positive Reinforcement – Tangibles",
            "Negative Reinforcement – Escape",
            "Automatic Reinforcement – Sensory",
        ]
        ANT_COLORS = ["#5b8db8", "#5ca05c", "#c9a840", "#c97a5a"]
        CON_COLORS = ["#3a6a96", "#3d7d3d", "#a07a10", "#a0503a"]

        ant_vals = [ant_fc[d[0]] for d in FUNC_DEFS]
        con_vals = [con_fc[d[0]] for d in FUNC_DEFS]
        tot_vals = [totals_fc[d[0]] for d in FUNC_DEFS]

        fig_func = _go.Figure()

        # Antecedents layer (bottom)
        fig_func.add_trace(_go.Bar(
            name="Antecedents",
            x=FUNC_SHORT, y=ant_vals,
            marker_color=ANT_COLORS,
            marker_line_width=0,
            text=[v if v > 0 else "" for v in ant_vals],
            textposition="inside",
            texttemplate="%{text:.0f}",
            insidetextfont=dict(color="white", size=13, family="system-ui"),
            hovertemplate="%{x}<br>Antecedents: %{y}<extra></extra>",
        ))

        # Consequences layer (top)
        fig_func.add_trace(_go.Bar(
            name="Consequences",
            x=FUNC_SHORT, y=con_vals,
            marker_color=CON_COLORS,
            marker_line_width=0,
            text=[v if v > 0 else "" for v in con_vals],
            textposition="inside",
            texttemplate="%{text:.0f}",
            insidetextfont=dict(color="white", size=13, family="system-ui"),
            hovertemplate="%{x}<br>Consequences: %{y}<extra></extra>",
        ))

        # Total annotations above each bar
        for i, (label, total) in enumerate(zip(FUNC_SHORT, tot_vals)):
            if total > 0:
                fig_func.add_annotation(
                    x=label, y=total,
                    text=f"<b>{total}</b>",
                    showarrow=False,
                    yshift=10,
                    font=dict(size=14, color="#111827", family="system-ui"),
                )

        fig_func.update_layout(
            barmode="stack",
            plot_bgcolor="white",
            paper_bgcolor="white",
            font_family="system-ui",
            xaxis=dict(
                title=dict(text="Function of Behavior", font=dict(size=12, color="#6b7280")),
                tickfont=dict(size=13, color="#111827"),
                showgrid=False,
            ),
            yaxis=dict(
                title=dict(text="Count", font=dict(size=12, color="#6b7280")),
                gridcolor="#f3f4f6",
                gridwidth=1,
                zeroline=False,
                dtick=1,
                tick0=0,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="left", x=0,
                font=dict(size=12),
                bgcolor="rgba(0,0,0,0)",
            ),
            margin=dict(l=10, r=10, t=40, b=10),
            height=380,
            bargap=0.35,
        )

        # ── Summary cards row ─────────────────────────────────────────────────
        dominant_idx = tot_vals.index(max(tot_vals)) if max(tot_vals) > 0 else 0
        dominant_label = FUNC_FULL[dominant_idx]
        dominant_total = tot_vals[dominant_idx]

        # Build cards HTML
        cards_html = ""
        for i in range(4):
            cards_html += (
                '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
                'padding:16px;border-top:4px solid ' + ANT_COLORS[i] + ';">'
                '<div style="font-size:11px;font-weight:700;letter-spacing:.06em;'
                'color:' + ANT_COLORS[i] + ';margin-bottom:6px;">' + FUNC_SHORT[i].upper() + '</div>'
                '<div style="font-size:28px;font-weight:800;color:#111;">' + str(tot_vals[i]) + '</div>'
                '<div style="font-size:11px;color:#9ca3af;margin-top:4px;">'
                + str(ant_vals[i]) + ' ant &middot; ' + str(con_vals[i]) + ' con'
                '</div></div>'
            )

        st.markdown(
            '<div style="font-size:20px;font-weight:800;color:#111;margin:32px 0 4px 0;">'
            'FUNCTION OF THE BEHAVIOR</div>'
            '<div style="font-size:13px;color:#6b7280;margin-bottom:20px;">'
            'The perceived function is based on direct observation of antecedent and '
            'consequence events that occur prior to and after the target behavior.</div>'
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">'
            + cards_html + '</div>',
            unsafe_allow_html=True
        )

        # Chart full width
        st.plotly_chart(fig_func, use_container_width=True, config=_PLOTLY_CONFIG)

        # Table full width below chart
        tbl_header = '<th style="padding:12px 16px;text-align:left;font-size:12px;font-weight:700;color:#6b7280;min-width:120px;"></th>'
        for i, d in enumerate(FUNC_DEFS):
            tbl_header += (
                '<th style="padding:12px 16px;text-align:center;font-size:12px;'
                'font-weight:700;letter-spacing:.04em;color:' + ANT_COLORS[i] + ';min-width:100px;">'
                + FUNC_FULL[i] + '</th>'
            )

        tbl_rows = ""
        for row_label, row_dict in [("Antecedents", ant_fc),
                                    ("Consequences", con_fc),
                                    ("Total", totals_fc)]:
            is_total = row_label == "Total"
            fw = "700" if is_total else "500"
            bg = "background:#f9fafb;" if is_total else ""
            tbl_rows += '<tr style="' + bg + '">'
            tbl_rows += (
                '<td style="padding:12px 16px;border-bottom:1px solid #e5e7eb;'
                'font-weight:' + fw + ';font-size:14px;">' + row_label + '</td>'
            )
            for i, d in enumerate(FUNC_DEFS):
                tbl_rows += (
                    '<td style="padding:12px 16px;border-bottom:1px solid #e5e7eb;'
                    'text-align:center;font-size:14px;font-weight:' + fw
                    + ';color:' + ANT_COLORS[i] + ';">'
                    + str(row_dict[d[0]]) + '</td>'
                )
            tbl_rows += '</tr>'

        dominant_html = (
            '<div style="margin-top:16px;padding:12px;background:#f0fdf4;'
            'border-radius:8px;font-size:13px;color:#15803d;">'
            '<b>Dominant function:</b> ' + dominant_label
            + ' (' + str(dominant_total) + ' instances)</div>'
        )

        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
            'padding:20px;margin-top:8px;overflow-x:auto;">'
            '<div style="font-weight:700;font-size:13px;color:#111;margin-bottom:14px;'
            'letter-spacing:.03em;">PERCEIVED FUNCTION</div>'
            '<table style="width:100%;border-collapse:collapse;font-family:system-ui,sans-serif;">'
            '<thead><tr style="border-bottom:2px solid #e5e7eb;">' + tbl_header + '</tr></thead>'
            '<tbody>' + tbl_rows + '</tbody>'
            '</table>' + dominant_html + '</div>',
            unsafe_allow_html=True
        )

    # ── Frequency by Day of Week ──────────────────────────────────────────────
    if "date" in df.columns:
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        df["day_of_week"] = pd.to_datetime(df["date"]).dt.day_name()
        dow_df = df.groupby("day_of_week").size().reset_index(name="count")
        dow_df["day_of_week"] = pd.Categorical(dow_df["day_of_week"], categories=day_order, ordered=True)
        dow_df = dow_df.sort_values("day_of_week")
        max_dow = int(dow_df["count"].max()) if len(dow_df) else 1
        fig_dow = px.bar(
            dow_df, x="day_of_week", y="count",
            labels={"day_of_week": "", "count": "Occurrences"},
            text="count",
            color_discrete_sequence=["#16a34a"],
        )
        fig_dow.update_traces(
            texttemplate="%{text:.0f}", textposition="outside",
            marker_color="#16a34a",
        )
        fig_dow.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="system-ui",
            xaxis=dict(gridcolor="#e5e7eb"),
            yaxis=dict(
                gridcolor="#e5e7eb", dtick=1, tick0=0,
                range=[0, max_dow + 1],
            ),
            margin=dict(l=0, r=20, t=20, b=40),
            height=300,
        )
        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;'
            'border-radius:12px;padding:16px;margin-top:12px;">'
            '<div style="font-weight:600;font-size:15px;color:#111;margin-bottom:8px;">'
            'Frequency by Day of Week</div>',
            unsafe_allow_html=True
        )
        st.plotly_chart(fig_dow, use_container_width=True, config=_PLOTLY_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Behaviors over time ───────────────────────────────────────────────────
    if "date" in df.columns and "behavior" in df.columns:
        df["date_only"] = pd.to_datetime(df["date"]).dt.normalize()
        time_df = df.groupby(["date_only", "behavior"]).size().reset_index(name="count")
        max_count = int(time_df["count"].max()) if len(time_df) else 1
        fig = px.line(time_df, x="date_only", y="count", color="behavior",
                      labels={"date_only": "Date", "count": "Count"},
                      markers=True)

        # ── Trend / Celeration overlay ────────────────────────────────────────
        trend_rows = []
        _color_map = {tr.name: tr.line.color for tr in fig.data}
        for beh in time_df["behavior"].unique():
            sub = time_df[time_df["behavior"] == beh].sort_values("date_only")
            if len(sub) < 2:
                continue
            days = (sub["date_only"] - sub["date_only"].min()).dt.days.to_numpy(dtype=float)
            counts = sub["count"].to_numpy(dtype=float)
            span = days.max() - days.min()
            if span <= 0:
                continue
            # Linear slope (counts/day → counts/week)
            slope_day, intercept = np.polyfit(days, counts, 1)
            slope_week = slope_day * 7
            # Log-linear celeration (× per week)
            log_counts = np.log(counts + 1.0)
            log_slope, _ = np.polyfit(days, log_counts, 1)
            celeration = float(np.exp(log_slope * 7))
            if celeration >= 1.10:
                direction, dcolor = "Accelerating ↗", "#dc2626"
            elif celeration <= 0.90:
                direction, dcolor = "Decelerating ↘", "#15803d"
            else:
                direction, dcolor = "Stable →", "#6b7280"

            # Add trend line to chart
            x_fit = [sub["date_only"].min(), sub["date_only"].max()]
            y_fit = [max(0.0, intercept),
                     max(0.0, intercept + slope_day * span)]
            fig.add_trace(_go.Scatter(
                x=x_fit, y=y_fit, mode="lines",
                name=f"{beh} trend",
                line=dict(color=_color_map.get(beh, "#6b7280"),
                           dash="dash", width=1.5),
                hovertemplate=(f"<b>{beh} trend</b><br>"
                                f"Slope: {slope_week:+.2f} /wk<br>"
                                f"Celeration: ×{celeration:.2f} /wk<extra></extra>"),
                showlegend=False,
            ))
            trend_rows.append({
                "Behavior": beh,
                "Slope (counts/wk)": round(slope_week, 2),
                "Celeration (×/wk)": round(celeration, 2),
                "Direction": direction,
                "_color": dcolor,
            })

        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="system-ui",
            xaxis=dict(tickformat="%b %d, %Y", gridcolor="#e5e7eb"),
            yaxis=dict(
                gridcolor="#e5e7eb",
                dtick=1,
                tick0=0,
                range=[0, max_count + 0.5],
            ),
            margin=dict(l=0, r=20, t=10, b=40),
        )
        st.markdown("""<div style="background:white;border:1.5px solid #e5e7eb;
            border-radius:12px;padding:16px;margin-top:12px;">
            <div style="font-weight:600;font-size:15px;color:#111;margin-bottom:8px;">
            Behaviors Over Time</div>""", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)

        # Trend metrics cards
        if trend_rows:
            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#6b7280;'
                'text-transform:uppercase;letter-spacing:.05em;margin:12px 0 8px 0;">'
                'Trend Analysis — Linear Slope &amp; Celeration (×/week)</div>',
                unsafe_allow_html=True
            )
            st.caption(
                "Celeration = multiplicative rate of change per week "
                "(×1.0 = stable, ×2.0 = doubling, ÷2.0 = halving). "
                "Threshold: ≥×1.10 accelerating, ≤×0.90 decelerating."
            )
            t_cols = st.columns(min(4, len(trend_rows)))
            for i, row in enumerate(trend_rows):
                with t_cols[i % len(t_cols)]:
                    st.markdown(
                        f'<div style="background:white;border:1.5px solid {row["_color"]};'
                        f'border-radius:10px;padding:12px;margin-bottom:8px;">'
                        f'<div style="font-size:11px;font-weight:700;color:#111;'
                        f'margin-bottom:6px;">{row["Behavior"]}</div>'
                        f'<div style="font-size:11px;color:#6b7280;">Slope</div>'
                        f'<div style="font-size:16px;font-weight:700;color:#111;'
                        f'margin-bottom:4px;">{row["Slope (counts/wk)"]:+.2f} /wk</div>'
                        f'<div style="font-size:11px;color:#6b7280;">Celeration</div>'
                        f'<div style="font-size:16px;font-weight:700;color:#111;'
                        f'margin-bottom:4px;">×{row["Celeration (×/wk)"]:.2f} /wk</div>'
                        f'<div style="font-size:11px;font-weight:700;color:{row["_color"]};'
                        f'margin-top:6px;">{row["Direction"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Occurrence Over Time ──────────────────────────────────────────────────
    if "time" in df.columns and "date" in df.columns and "behavior" in df.columns:

        def time_to_hours(t):
            try:
                parts = str(t).split(":")
                return int(parts[0]) + int(parts[1]) / 60
            except Exception:
                return None

        df["time_hours"] = df["time"].apply(time_to_hours)
        df["date_dt"] = pd.to_datetime(df["date"])
        df_sc = df.dropna(subset=["time_hours", "date_dt"]).copy()

        tick_vals = list(range(7, 21))
        tick_text = [f"{h}am" if h < 12 else ("12pm" if h == 12 else f"{h-12}pm")
                     for h in tick_vals]

        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
            'padding:20px 20px 8px 20px;margin-top:20px;">'
            '<div style="font-weight:700;font-size:16px;color:#111;margin-bottom:14px;">'
            'Occurrence Over Time (Weekly / Monthly / Yearly)</div>',
            unsafe_allow_html=True
        )

        view = st.radio("View", ["Weekly", "Monthly", "Yearly"],
                        horizontal=True, label_visibility="collapsed",
                        key="occurrence_view")

        if view == "Weekly":
            df_sc["period"] = df_sc["date_dt"].dt.strftime("%a %m/%d")
            x_title = "Day"
        elif view == "Monthly":
            df_sc["period"] = df_sc["date_dt"].dt.strftime("%b %Y")
            x_title = "Month"
        else:
            df_sc["period"] = df_sc["date_dt"].dt.strftime("%Y").astype(str)
            x_title = "Year"

        # Sort periods chronologically by first occurrence
        period_order = sorted(df_sc["period"].unique(),
                              key=lambda p: df_sc.loc[df_sc["period"] == p, "date_dt"].min())

        # Build readable hover: behavior, day, time
        df_sc["hover_time"] = df_sc["time_hours"].apply(
            lambda h: f"{int(h)}:{'%02d' % int((h % 1) * 60)} "
                      f"({'am' if int(h) < 12 else 'pm'})"
        )

        fig_occ = px.scatter(
            df_sc, x="period", y="time_hours", color="behavior",
            labels={"period": x_title, "time_hours": ""},
            color_discrete_sequence=px.colors.qualitative.Safe,
            category_orders={"period": period_order},
            hover_data={"period": True, "time_hours": False,
                        "behavior": True, "hover_time": True},
        )
        fig_occ.update_traces(
            marker=dict(size=12, line=dict(width=1, color="white")),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{x}<extra></extra>",
        )
        fig_occ.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="system-ui",
            xaxis=dict(
                title=x_title, gridcolor="#e5e7eb", gridwidth=1, griddash="dash",
                tickangle=-30, type="category",
                categoryorder="array", categoryarray=period_order,
            ),
            yaxis=dict(
                tickvals=tick_vals, ticktext=tick_text,
                range=[6.5, 20.5], gridcolor="#e5e7eb", gridwidth=1, griddash="dash",
                title="",
            ),
            legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, x=0),
            margin=dict(l=10, r=10, t=40, b=40),
            height=380,
        )
        st.plotly_chart(fig_occ, use_container_width=True, config=_PLOTLY_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Time-of-Day Heatmap ───────────────────────────────────────────────────
    if "time" in df.columns and "behavior" in df.columns:
        def _to_hour(t):
            try:
                return int(str(t).split(":")[0])
            except Exception:
                return None
        df["hour"] = df["time"].apply(_to_hour)
        df_h = df.dropna(subset=["hour"])
        if len(df_h):
            # Map hours to school-based periods
            _PERIOD_DEFS = [
                ("Arrival",               range(7, 8)),
                ("Morning Instruction",   range(8, 11)),
                ("Midday / Lunch",        range(11, 13)),
                ("Afternoon Instruction", range(13, 15)),
                ("Dismissal",             range(15, 16)),
                ("Home",                  range(16, 22)),
            ]
            def _hour_to_period(h):
                for label, rng in _PERIOD_DEFS:
                    if h in rng:
                        return label
                return "Other"
            df_h = df_h.copy()
            df_h["period"] = df_h["hour"].apply(_hour_to_period)
            period_order = [p for p, _ in _PERIOD_DEFS if p in df_h["period"].unique()]

            # Sort behaviors by category
            _BEH_ORDER = [
                "Aggression", "Non-compliance", "Arguing", "Property destruction", "Elopement",
                "Off-Task", "Fidgeting", "Calling out/ Making sounds", "Out of seat",
                "Mand/ request", "Compliance/ on task",
                "Self-injurious behavior", "Other",
            ]
            present_behs = df_h["behavior"].unique()
            beh_order = [b for b in _BEH_ORDER if b in present_behs] + \
                        [b for b in present_behs if b not in _BEH_ORDER]

            period_beh = df_h.groupby(["period", "behavior"]).size().reset_index(name="count")
            pivot = period_beh.pivot(index="period", columns="behavior", values="count") \
                              .reindex(index=period_order, columns=beh_order, fill_value=0) \
                              .fillna(0)

            z_vals = pivot.values.tolist()
            text_vals = [[int(v) if v > 0 else "" for v in row] for row in z_vals]
            max_val = max(v for row in z_vals for v in row) if z_vals else 1

            # Color scale: 0=white, low=light green, high=dark green
            colorscale = [[0, "#ffffff"], [0.001, "#f0fdf4"], [0.35, "#86efac"],
                          [0.65, "#22c55e"], [1, "#15803d"]]

            fig_heat = _go.Figure(data=_go.Heatmap(
                z=z_vals,
                x=list(pivot.columns),
                y=list(pivot.index),
                text=text_vals,
                texttemplate="%{text}",
                textfont=dict(size=14, color="#111"),
                colorscale=colorscale,
                zmin=0, zmax=max(max_val, 1),
                showscale=False,
                hoverongaps=False,
                hovertemplate="<b>%{y}</b><br><b>%{x}</b><br>Frequency: %{z}<extra></extra>",
            ))
            n_rows = len(period_order)
            fig_heat.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="system-ui",
                margin=dict(l=0, r=0, t=10, b=0),
                height=max(300, n_rows * 70 + 160),
                xaxis=dict(
                    domain=[0.24, 1.0],
                    side="bottom", tickangle=-35, tickfont=dict(size=12),
                ),
                yaxis=dict(
                    domain=[0.22, 1.0],
                    tickfont=dict(size=12),
                ),
            )

            # Dynamic caption: find peak period
            flat = [(pivot.index[r], pivot.columns[c], int(pivot.iloc[r, c]))
                    for r in range(len(pivot.index)) for c in range(len(pivot.columns))]
            flat_sorted = sorted(flat, key=lambda x: -x[2])
            if flat_sorted and flat_sorted[0][2] > 0:
                peak_period, peak_beh, peak_n = flat_sorted[0]
                caption = (f"<b>{peak_beh}</b> occurs most frequently during "
                           f"<b>{peak_period}</b> ({peak_n} instance{'s' if peak_n != 1 else ''}).")
            else:
                caption = "No time-of-day pattern detected with current data."

            st.markdown(
                '<div style="background:white;border:1.5px solid #e5e7eb;'
                'border-radius:12px;padding:16px;margin-top:12px;">'
                '<div style="font-weight:600;font-size:15px;color:#111;margin-bottom:2px;">'
                'Time-of-Day Heatmap</div>'
                '<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">'
                'Frequency per observation period — higher shading indicates greater observed frequency</div>',
                unsafe_allow_html=True
            )
            st.plotly_chart(fig_heat, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown(
                f'<div style="font-size:12px;color:#374151;background:#f9fafb;border-radius:6px;'
                f'padding:10px 14px;margin-top:-8px;">{caption}</div>',
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Antecedent → Behavior Heatmap ────────────────────────────────────────
    if "antecedent" in df.columns and "behavior" in df.columns:
        df_ab = df.dropna(subset=["antecedent", "behavior"])
        df_ab = df_ab[df_ab["antecedent"] != ""]
        if len(df_ab):
            ab_counts = df_ab.groupby(["antecedent", "behavior"]).size().reset_index(name="count")

            # Sort behaviors by category on X-axis
            _BEH_ORDER_AB = [
                "Aggression", "Non-compliance", "Arguing", "Property destruction", "Elopement",
                "Off-Task", "Fidgeting", "Calling out/ Making sounds", "Out of seat",
                "Mand/ request", "Compliance/ on task",
                "Self-injurious behavior", "Other",
            ]
            present_behs_ab = list(ab_counts["behavior"].unique())
            beh_col_order = [b for b in _BEH_ORDER_AB if b in present_behs_ab] + \
                            [b for b in present_behs_ab if b not in _BEH_ORDER_AB]

            pivot_ab = ab_counts.pivot(index="antecedent", columns="behavior", values="count") \
                                 .reindex(columns=beh_col_order, fill_value=0).fillna(0)

            ab_z = pivot_ab.values.tolist()
            ab_text = [[int(v) if v > 0 else "" for v in row] for row in ab_z]
            ab_max = max(v for row in ab_z for v in row) if ab_z else 1

            colorscale_ab = [[0, "#ffffff"], [0.001, "#fff7ed"], [0.35, "#fdba74"],
                             [0.65, "#f97316"], [1, "#c2410c"]]

            fig_ab = _go.Figure(data=_go.Heatmap(
                z=ab_z,
                x=list(pivot_ab.columns),
                y=list(pivot_ab.index),
                text=ab_text,
                texttemplate="%{text}",
                textfont=dict(size=14, color="#111"),
                colorscale=colorscale_ab,
                zmin=0, zmax=max(ab_max, 1),
                showscale=False,
                hovertemplate="<b>Ant:</b> %{y}<br><b>Beh:</b> %{x}<br>Frequency: %{z}<extra></extra>",
            ))
            fig_ab.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="system-ui",
                margin=dict(l=0, r=0, t=10, b=0),
                height=max(300, len(pivot_ab.index) * 70 + 180),
                xaxis=dict(
                    domain=[0.30, 1.0],
                    tickangle=-35, tickfont=dict(size=12),
                ),
                yaxis=dict(
                    domain=[0.25, 1.0],
                    tickfont=dict(size=12),
                ),
            )

            # Dynamic caption
            ab_flat = [(pivot_ab.index[r], pivot_ab.columns[c], int(pivot_ab.iloc[r, c]))
                       for r in range(len(pivot_ab.index)) for c in range(len(pivot_ab.columns))]
            ab_peak = sorted(ab_flat, key=lambda x: -x[2])
            if ab_peak and ab_peak[0][2] > 0:
                pk_ant, pk_beh, pk_n = ab_peak[0]
                ab_caption = (f"<b>{pk_beh}</b> occurs most frequently following "
                              f"<b>{pk_ant}</b> ({pk_n} instance{'s' if pk_n != 1 else ''}).")
            else:
                ab_caption = "No antecedent-behavior pattern detected with current data."

            st.markdown(
                '<div style="background:white;border:1.5px solid #e5e7eb;'
                'border-radius:12px;padding:16px;margin-top:12px;">'
                '<div style="font-weight:600;font-size:15px;color:#111;margin-bottom:2px;">'
                'Antecedent → Behavior Heatmap</div>'
                '<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">'
                'Frequency of antecedent-behavior pairings — which antecedents most reliably predict which behaviors?</div>',
                unsafe_allow_html=True
            )
            st.plotly_chart(fig_ab, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown(
                f'<div style="font-size:12px;color:#374151;background:#f9fafb;border-radius:6px;'
                f'padding:10px 14px;margin-top:-8px;">{ab_caption}</div>',
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Behavior Co-occurrence ────────────────────────────────────────────────
    if "behavior" in df.columns and "date" in df.columns:
        session_key = "date" if "setting" not in df.columns else None
        grp_col = ["date", "setting"] if "setting" in df.columns else ["date"]
        sessions = df.groupby(grp_col)["behavior"].apply(list)
        cooc = {}
        for beh_list in sessions:
            unique_behs = list(set(beh_list))
            for i in range(len(unique_behs)):
                for j in range(i + 1, len(unique_behs)):
                    pair = tuple(sorted([unique_behs[i], unique_behs[j]]))
                    cooc[pair] = cooc.get(pair, 0) + 1
        if cooc:
            # Sort behaviors by category
            _BEH_ORDER_CO = [
                "Aggression", "Non-compliance", "Arguing", "Property destruction", "Elopement",
                "Off-Task", "Fidgeting", "Calling out/ Making sounds", "Out of seat",
                "Mand/ request", "Compliance/ on task",
                "Self-injurious behavior", "Other",
            ]
            present_behs_co = list(df["behavior"].unique())
            all_behs = [b for b in _BEH_ORDER_CO if b in present_behs_co] + \
                       [b for b in present_behs_co if b not in _BEH_ORDER_CO]
            matrix = {b: {b2: 0 for b2 in all_behs} for b in all_behs}
            for (b1, b2), cnt in cooc.items():
                matrix[b1][b2] = cnt
                matrix[b2][b1] = cnt
            co_df = pd.DataFrame(matrix, index=all_behs, columns=all_behs)

            co_z = co_df.values.tolist()
            co_text = [[int(v) if v > 0 else "" for v in row] for row in co_z]
            co_max = max(v for row in co_z for v in row) if co_z else 1

            colorscale_co = [[0, "#ffffff"], [0.001, "#f0f9ff"], [0.35, "#7dd3fc"],
                             [0.65, "#0ea5e9"], [1, "#0369a1"]]

            fig_co = _go.Figure(data=_go.Heatmap(
                z=co_z,
                x=list(co_df.columns),
                y=list(co_df.index),
                text=co_text,
                texttemplate="%{text}",
                textfont=dict(size=14, color="#111"),
                colorscale=colorscale_co,
                zmin=0, zmax=max(co_max, 1),
                showscale=False,
                hovertemplate="<b>%{y}</b> + <b>%{x}</b><br>Co-occurred in %{z} session(s)<extra></extra>",
            ))
            fig_co.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="system-ui",
                margin=dict(l=0, r=0, t=10, b=0),
                height=max(300, len(all_behs) * 70 + 180),
                xaxis=dict(
                    domain=[0.28, 1.0],
                    tickangle=-35, tickfont=dict(size=12),
                ),
                yaxis=dict(
                    domain=[0.25, 1.0],
                    tickfont=dict(size=12),
                ),
            )

            # Dynamic caption
            co_pairs = sorted(
                [(b1, b2, cooc.get(tuple(sorted([b1, b2])), 0))
                 for b1 in all_behs for b2 in all_behs if b1 < b2],
                key=lambda x: -x[2]
            )
            if co_pairs and co_pairs[0][2] > 0:
                cp_b1, cp_b2, cp_n = co_pairs[0]
                co_caption = (f"<b>{cp_b1}</b> and <b>{cp_b2}</b> co-occurred most frequently "
                              f"({cp_n} session{'s' if cp_n != 1 else ''}).")
            else:
                co_caption = "No behavior co-occurrence patterns detected with current data."

            st.markdown(
                '<div style="background:white;border:1.5px solid #e5e7eb;'
                'border-radius:12px;padding:16px;margin-top:12px;">'
                '<div style="font-weight:600;font-size:15px;color:#111;margin-bottom:2px;">'
                'Behavior Co-occurrence</div>'
                '<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">'
                'Frequency of behaviors occurring in the same session — higher shading indicates greater co-occurrence</div>',
                unsafe_allow_html=True
            )
            st.plotly_chart(fig_co, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown(
                f'<div style="font-size:12px;color:#374151;background:#f9fafb;border-radius:6px;'
                f'padding:10px 14px;margin-top:-8px;">{co_caption}</div>',
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Trend Lines on Behaviors Over Time ────────────────────────────────────
    if "date" in df.columns and "behavior" in df.columns:
        df["date_only"] = pd.to_datetime(df["date"]).dt.normalize()
        trend_df = df.groupby(["date_only", "behavior"]).size().reset_index(name="count")
        if len(trend_df["date_only"].unique()) >= 3:
            colors = px.colors.qualitative.Safe
            fig_trend = _go.Figure()
            for idx, beh in enumerate(trend_df["behavior"].unique()):
                bdf = trend_df[trend_df["behavior"] == beh].sort_values("date_only")
                color = colors[idx % len(colors)]
                fig_trend.add_trace(_go.Scatter(
                    x=bdf["date_only"], y=bdf["count"],
                    mode="lines+markers", name=beh,
                    line=dict(color=color, width=2),
                    marker=dict(size=7),
                ))
                # Trend line via linear regression
                x_num = (bdf["date_only"] - bdf["date_only"].min()).dt.days.values
                y_vals = bdf["count"].values
                if len(x_num) >= 2:
                    z = np.polyfit(x_num, y_vals, 1)
                    p = np.poly1d(z)
                    x_range = np.linspace(x_num.min(), x_num.max(), 50)
                    x_dates = [bdf["date_only"].min() + pd.Timedelta(days=int(d)) for d in x_range]
                    direction = "↑" if z[0] > 0 else "↓"
                    fig_trend.add_trace(_go.Scatter(
                        x=x_dates, y=p(x_range),
                        mode="lines", name=f"{beh} trend {direction}",
                        line=dict(color=color, width=1.5, dash="dash"),
                        showlegend=True,
                    ))
            max_t = int(trend_df["count"].max()) if len(trend_df) else 1
            fig_trend.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="system-ui",
                xaxis=dict(tickformat="%b %d, %Y", gridcolor="#e5e7eb"),
                yaxis=dict(gridcolor="#e5e7eb", dtick=1, tick0=0, range=[0, max_t + 1]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                margin=dict(l=0, r=20, t=40, b=40),
                height=360,
            )
            st.markdown(
                '<div style="background:white;border:1.5px solid #e5e7eb;'
                'border-radius:12px;padding:16px;margin-top:12px;">'
                '<div style="font-weight:600;font-size:15px;color:#111;margin-bottom:4px;">'
                'Behaviors Over Time + Trend Lines</div>'
                '<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">'
                'Dashed lines show increasing (↑) or decreasing (↓) trends</div>',
                unsafe_allow_html=True
            )
            st.plotly_chart(fig_trend, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown("</div>", unsafe_allow_html=True)



    # ── AI Pattern Analysis ───────────────────────────────────────────────────
    st.markdown(
        '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
        'padding:20px;margin-top:16px;">'
        '<div style="font-weight:700;font-size:15px;color:#111;margin-bottom:4px;">AI Pattern Analysis</div>'
        '<div style="font-size:12px;color:#6b7280;margin-bottom:14px;">'
        'Analyzes all data above — setting fields, ABC fields, behavior dimensions, trends, and function.</div>',
        unsafe_allow_html=True
    )

    if not _ANTHROPIC_AVAILABLE:
        st.warning("Install the `anthropic` package to enable AI analysis: `pip install anthropic`")
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            api_key = st.text_input(
                "Anthropic API Key", type="password",
                placeholder="sk-ant-...",
                help="Enter your Anthropic API key. It is not stored.",
                key="ai_api_key_input"
            )

        if st.button("Run AI Analysis", type="primary", key="ai_analyze_btn"):
            if not api_key:
                st.warning("An API key is required to run analysis.")
            else:
                # Build a structured data summary to send to the model
                summary_parts = []

                summary_parts.append(f"Student data summary ({len(df)} entries):")
                summary_parts.append(f"- Date range: {df['date'].min()} to {df['date'].max()}" if "date" in df.columns else "")

                if "behavior" in df.columns:
                    beh_counts = df["behavior"].value_counts()
                    summary_parts.append("Behavior frequencies: " + ", ".join(f"{b} ({n})" for b, n in beh_counts.items()))

                if "antecedent" in df.columns:
                    ant_counts = df["antecedent"].value_counts()
                    summary_parts.append("Antecedent frequencies: " + ", ".join(f"{a} ({n})" for a, n in ant_counts.items()))

                if "consequence" in df.columns:
                    con_counts = df["consequence"].value_counts()
                    summary_parts.append("Consequence frequencies: " + ", ".join(f"{c} ({n})" for c, n in con_counts.items()))

                for field, label in [("location","Location"),("people_intervening","People Intervening"),
                                     ("subject","Subject"),("activity","Activity"),
                                     ("instructional_format","Instructional Format")]:
                    if field in df.columns and df[field].notna().any():
                        counts = df[field].value_counts()
                        summary_parts.append(f"{label}: " + ", ".join(f"{v} ({n})" for v, n in counts.items()))

                if "intensity" in df.columns and df["intensity"].notna().any():
                    summary_parts.append(f"Average intensity: {df['intensity'].mean():.1f}/10")

                if "date" in df.columns:
                    df["_dow"] = pd.to_datetime(df["date"]).dt.day_name()
                    dow = df["_dow"].value_counts()
                    summary_parts.append("Behavior by day of week: " + ", ".join(f"{d} ({n})" for d, n in dow.items()))

                if "time" in df.columns and df["time"].notna().any():
                    try:
                        df["_hour"] = pd.to_datetime(df["time"], format="%H:%M:%S", errors="coerce").dt.hour
                        hour_counts = df["_hour"].dropna().value_counts().sort_index()
                        if len(hour_counts):
                            summary_parts.append("Behavior by hour: " + ", ".join(f"{int(h):02d}:00 ({n})" for h, n in hour_counts.items()))
                    except Exception:
                        pass

                data_text = "\n".join(p for p in summary_parts if p)

                prompt = (
                    "You are a Board Certified Behavior Analyst (BCBA) reviewing ABC (Antecedent-Behavior-Consequence) "
                    "data collected on a student. Analyze the following data and identify meaningful patterns, "
                    "hypotheses about behavior function, notable antecedent-behavior-consequence chains, "
                    "time/setting patterns, and any clinical observations that would be useful for an FBA report. "
                    "Be specific and reference the actual data values. Organize your response with clear headings.\n\n"
                    + data_text
                )

                with st.spinner("Analyzing data…"):
                    try:
                        client = _anthropic.Anthropic(api_key=api_key)
                        message = client.messages.create(
                            model="claude-opus-4-6",
                            max_tokens=1024,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        result = message.content[0].text
                        st.session_state["ai_analysis_result"] = result
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")

        if st.session_state.get("ai_analysis_result"):
            st.markdown(
                '<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;'
                'padding:16px;margin-top:12px;font-size:14px;line-height:1.7;color:#111;">'
                + st.session_state["ai_analysis_result"].replace("\n", "<br>") + '</div>',
                unsafe_allow_html=True
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Standard Celeration Chart ─────────────────────────────────────────────
    if ("date" in df.columns and "behavior" in df.columns
            and "observation_duration_minutes" in df.columns
            and df["observation_duration_minutes"].notna().any()):

        scc_df = df.dropna(subset=["observation_duration_minutes"]).copy()
        scc_df["date_only"] = pd.to_datetime(scc_df["date"]).dt.normalize()
        scc_df["observation_duration_minutes"] = \
            pd.to_numeric(scc_df["observation_duration_minutes"], errors="coerce")
        scc_df = scc_df[scc_df["observation_duration_minutes"] > 0]

        # Aggregate per (date, behavior): count / session duration
        scc_agg = (
            scc_df.groupby(["date_only", "behavior"])
            .agg(count=("behavior", "size"),
                 minutes=("observation_duration_minutes", "first"))
            .reset_index()
        )
        scc_agg["rate_per_min"] = scc_agg["count"] / scc_agg["minutes"]
        scc_agg = scc_agg[scc_agg["rate_per_min"] > 0]

        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;'
            'border-radius:12px;padding:16px;margin-top:20px;">'
            '<div style="font-weight:600;font-size:15px;color:#111;margin-bottom:4px;">'
            'Standard Celeration Chart</div>'
            '<div style="font-size:11px;color:#6b7280;margin-bottom:10px;">'
            'Precision-teaching SCC — y-axis: rate/min (semi-log, 6 cycles 0.001–1000); '
            'x-axis: calendar days. A straight line = constant celeration (multiplicative rate '
            'of change per week). Ascending = accelerating; descending = decelerating.'
            '</div>',
            unsafe_allow_html=True
        )

        if len(scc_agg) < 2 or scc_agg["behavior"].nunique() == 0:
            st.info(
                "SCC requires at least 2 sessions with observation_duration_minutes > 0 "
                "and at least one behavior recorded."
            )
        else:
            fig_scc = _go.Figure()
            clrs = px.colors.qualitative.Safe
            min_date = scc_agg["date_only"].min()
            max_date = scc_agg["date_only"].max()
            cel_rows = []

            for idx, beh in enumerate(sorted(scc_agg["behavior"].unique())):
                sub = scc_agg[scc_agg["behavior"] == beh].sort_values("date_only")
                clr = clrs[idx % len(clrs)]

                fig_scc.add_trace(_go.Scatter(
                    x=sub["date_only"],
                    y=sub["rate_per_min"],
                    mode="markers",
                    name=beh,
                    marker=dict(size=9, color=clr, line=dict(width=1, color="white")),
                    hovertemplate=("<b>" + beh + "</b><br>"
                                   "Date: %{x|%b %d, %Y}<br>"
                                   "Rate: %{y:.3f} /min<extra></extra>"),
                ))

                if len(sub) >= 2:
                    days = (sub["date_only"] - min_date).dt.days.to_numpy(dtype=float)
                    log_r = np.log10(sub["rate_per_min"].to_numpy(dtype=float))
                    if days.max() - days.min() > 0:
                        slope_day, intercept = np.polyfit(days, log_r, 1)
                        celeration = float(10 ** (slope_day * 7))
                        if celeration >= 1.10:
                            direction = "Accelerating ↗"
                        elif celeration <= 0.90:
                            direction = "Decelerating ↘"
                        else:
                            direction = "Stable →"

                        x_fit = [sub["date_only"].min(), sub["date_only"].max()]
                        d_fit = [(d - min_date).days for d in x_fit]
                        y_fit = [10 ** (intercept + slope_day * d) for d in d_fit]
                        fig_scc.add_trace(_go.Scatter(
                            x=x_fit, y=y_fit, mode="lines",
                            name=f"{beh} celeration ×{celeration:.2f}/wk",
                            line=dict(color=clr, dash="dash", width=1.5),
                            hovertemplate=(f"<b>{beh}</b><br>"
                                           f"Celeration: ×{celeration:.2f} /wk"
                                           "<extra></extra>"),
                        ))
                        cel_rows.append({
                            "Behavior": beh,
                            "Celeration (×/wk)": round(celeration, 2),
                            "Direction": direction,
                            "Sessions": len(sub),
                        })

            span_days = max(14, (max_date - min_date).days + 7)

            fig_scc.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="system-ui",
                height=520,
                xaxis=dict(
                    title="Calendar Days",
                    tickformat="%b %d, %Y",
                    gridcolor="#e5e7eb",
                    showline=True, linecolor="#9ca3af", mirror=False,
                ),
                yaxis=dict(
                    title="Rate per Minute (log scale)",
                    type="log",
                    range=[-3, 3],
                    gridcolor="#9ca3af",
                    gridwidth=1,
                    minor=dict(showgrid=True, gridcolor="#f3f4f6", gridwidth=0.5),
                    showline=True, linecolor="#9ca3af",
                ),
                legend=dict(orientation="h", y=-0.22),
                margin=dict(l=10, r=10, t=10, b=90),
            )
            st.plotly_chart(fig_scc, use_container_width=True, config=_PLOTLY_CONFIG)

            if cel_rows:
                st.markdown(
                    '<div style="font-size:11px;font-weight:700;color:#6b7280;'
                    'text-transform:uppercase;letter-spacing:.05em;margin:8px 0;">'
                    'Celeration Summary</div>',
                    unsafe_allow_html=True
                )
                st.dataframe(pd.DataFrame(cel_rows), hide_index=True,
                             use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)


# ── Tab: Computational Models ────────────────────────────────────────────────
def tab_computational_models(filtered_entries, student=""):
    if not filtered_entries:
        st.info("No data recorded yet.")
        return
    import numpy as np
    import plotly.graph_objects as _go
    df = pd.DataFrame(filtered_entries)

    # ── Function Hypothesis Comparison ───────────────────────────────────────
    if student:
        ia_all  = load_indirect()
        ia_data = ia_all.get(student, {})

        saved_fast = ia_data.get("fast", {})
        saved_mas  = ia_data.get("mas",  {})
        saved_qfab = ia_data.get("qfab", {})
        saved_fai  = ia_data.get("fai",  {})

        indirect_scores = {}
        if saved_fast: indirect_scores["FAST"] = _fast_subscale_scores(saved_fast)
        if saved_mas:  indirect_scores["MAS"]  = _mas_subscale_scores(saved_mas)
        if saved_qfab: indirect_scores["QFAB"] = _qfab_function_scores(saved_qfab)
        if saved_fai:  indirect_scores["FAI"]  = _fai_function_scores(saved_fai)

        if indirect_scores:
            st.markdown(
                '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
                'padding:20px;margin-bottom:16px;">'
                '<div style="font-weight:700;font-size:15px;color:#111;margin-bottom:4px;">'
                'Function Hypothesis Comparison</div>'
                '<div style="font-size:12px;color:#6b7280;margin-bottom:14px;">'
                'Compares informant-rated function (indirect assessment) against '
                'the empirical signal in the ABC data (antecedent frequency by function category). '
                'Convergence across sources strengthens the hypothesis; divergence warrants further investigation.</div>',
                unsafe_allow_html=True
            )

            functions = ["Attention", "Escape", "Tangible", "Sensory / Automatic"]

            # ── Indirect assessment table ─────────────────────────────────────
            table_rows = []
            for inst, scores in indirect_scores.items():
                total = sum(scores.values()) or 1
                row = {"Source": inst, "Type": "Indirect"}
                for fn in functions:
                    row[fn] = f"{scores.get(fn, 0) / total * 100:.0f}%"
                row["Top Function"] = max(scores, key=scores.get)
                table_rows.append(row)

            # ── ABC-derived function signal ───────────────────────────────────
            _fn_map = {
                "Attention":           ["(Att)", "Att)"],
                "Escape":              ["(Esc)", "Esc)"],
                "Tangible":            ["(Tan)", "Tan)"],
                "Sensory / Automatic": ["(Sel)", "Sel)"],
            }
            if "antecedent" in df.columns:
                total_abc = len(df)
                abc_fn_counts = {fn: 0 for fn in functions}
                for _, row in df.iterrows():
                    ant = str(row.get("antecedent", "") or "")
                    for fn, tags in _fn_map.items():
                        if any(tag in ant for tag in tags):
                            abc_fn_counts[fn] += 1
                abc_total = sum(abc_fn_counts.values()) or 1
                abc_row = {"Source": "ABC Data", "Type": "Direct Observation"}
                for fn in functions:
                    abc_row[fn] = f"{abc_fn_counts[fn] / abc_total * 100:.0f}%"
                abc_row["Top Function"] = max(abc_fn_counts, key=abc_fn_counts.get)
                table_rows.append(abc_row)

                # ── Convergence callout ───────────────────────────────────────
                indirect_tops = [max(s, key=s.get) for s in indirect_scores.values()]
                abc_top = abc_row["Top Function"]
                n_agree = sum(1 for t in indirect_tops if t == abc_top)
                n_total = len(indirect_tops)
                if n_agree == n_total and n_total > 0:
                    callout_bg, callout_border, callout_color = "#f0fdf4", "#bbf7d0", "#16a34a"
                    callout_msg = (
                        f"<b>Convergent:</b> all {n_total} indirect instrument{'s' if n_total>1 else ''} "
                        f"and the ABC data agree — <b>{abc_top}</b>-maintained behavior. "
                        f"Hypothesis is well-supported."
                    )
                elif n_agree > 0:
                    callout_bg, callout_border, callout_color = "#fffbeb", "#fde68a", "#92400e"
                    callout_msg = (
                        f"<b>Partial convergence:</b> {n_agree} of {n_total} indirect instruments "
                        f"agree with the ABC data ({abc_top}). "
                        f"Review divergent instruments before finalising the hypothesis."
                    )
                else:
                    callout_bg, callout_border, callout_color = "#fef2f2", "#fecaca", "#991b1b"
                    callout_msg = (
                        f"<b>Divergent:</b> indirect assessment and ABC data suggest different functions. "
                        f"Indirect: <b>{indirect_tops[0]}</b> — ABC data: <b>{abc_top}</b>. "
                        f"Additional data collection recommended before concluding function."
                    )

            st.dataframe(
                pd.DataFrame(table_rows).set_index("Source"),
                use_container_width=True
            )

            if "antecedent" in df.columns:
                st.markdown(
                    f'<div style="background:{callout_bg};border:1.5px solid {callout_border};'
                    f'border-radius:8px;padding:12px 16px;margin-top:8px;font-size:13px;'
                    f'color:{callout_color};">{callout_msg}</div>',
                    unsafe_allow_html=True
                )

            # ── Side-by-side bar chart ────────────────────────────────────────
            colors = {"Attention": "#6366f1", "Escape": "#f59e0b",
                      "Tangible": "#10b981", "Sensory / Automatic": "#ef4444"}
            fig_hyp = _go.Figure()
            sources = list(indirect_scores.keys())
            if "antecedent" in df.columns:
                sources.append("ABC Data")
            for fn in functions:
                y_vals = []
                for src in sources:
                    if src == "ABC Data":
                        total = sum(abc_fn_counts.values()) or 1
                        y_vals.append(round(abc_fn_counts.get(fn, 0) / total * 100, 1))
                    else:
                        s = indirect_scores[src]
                        total = sum(s.values()) or 1
                        y_vals.append(round(s.get(fn, 0) / total * 100, 1))
                fig_hyp.add_trace(_go.Bar(
                    name=fn, x=sources, y=y_vals,
                    marker_color=colors[fn],
                    text=[f"{v:.0f}%" for v in y_vals],
                    textposition="outside",
                ))
            fig_hyp.update_layout(
                barmode="group",
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="system-ui", height=320,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(title="% of total", tickformat="d", range=[0, 110]),
                xaxis=dict(title=""),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_hyp, use_container_width=True, config=_PLOTLY_CONFIG)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Reinforcer Gap Analysis ───────────────────────────────────────────
        saved_reinf = ia_data.get("reinforcers", {})
        if saved_reinf and "consequence" in df.columns:
            pr_scores = {label: _likert_score(saved_reinf.get(key, ""), 4)
                         for key, label, _ in _POS_REINFORCERS}
            top_reinf = {k: v for k, v in pr_scores.items() if v >= 3}

            if top_reinf:
                cons_text = " ".join(df["consequence"].dropna().astype(str).str.lower().tolist())
                gap_items = []
                used_items = []
                for label, rating in top_reinf.items():
                    first_word = label.split("/")[0].split("(")[0].strip().lower().split()[0]
                    if first_word in cons_text:
                        used_items.append((label, rating))
                    else:
                        gap_items.append((label, rating))

                st.markdown(
                    '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
                    'padding:20px;margin-bottom:16px;">'
                    '<div style="font-weight:700;font-size:15px;color:#111;margin-bottom:4px;">'
                    'Reinforcer Gap Analysis</div>'
                    '<div style="font-size:12px;color:#6b7280;margin-bottom:14px;">'
                    'Compares highly-rated reinforcers (3–4 on the inventory) against '
                    'consequences recorded in the ABC log. Gaps indicate reinforcers that '
                    'are available but not yet being used as intervention consequences.</div>',
                    unsafe_allow_html=True
                )
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown(
                        '<div style="font-size:12px;font-weight:700;color:#16a34a;margin-bottom:6px;">'
                        'Appearing in ABC log</div>',
                        unsafe_allow_html=True
                    )
                    if used_items:
                        for label, rating in used_items:
                            st.markdown(
                                f'<div style="font-size:12px;padding:4px 8px;background:#f0fdf4;'
                                f'border-radius:6px;margin-bottom:3px;">✓ {label} ({rating}/4)</div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            '<div style="font-size:12px;color:#9ca3af;">None detected yet.</div>',
                            unsafe_allow_html=True
                        )
                with g2:
                    st.markdown(
                        '<div style="font-size:12px;font-weight:700;color:#f59e0b;margin-bottom:6px;">'
                        'Not yet used as consequence</div>',
                        unsafe_allow_html=True
                    )
                    if gap_items:
                        for label, rating in gap_items:
                            st.markdown(
                                f'<div style="font-size:12px;padding:4px 8px;background:#fffbeb;'
                                f'border-radius:6px;margin-bottom:3px;">· {label} ({rating}/4)</div>',
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(
                            '<div style="font-size:12px;color:#9ca3af;">'
                            'All highly-rated reinforcers appear in the log.</div>',
                            unsafe_allow_html=True
                        )
                st.markdown("</div>", unsafe_allow_html=True)

    # ── Computational Models ──────────────────────────────────────────────────
    st.markdown(
        '<div style="font-weight:700;font-size:15px;color:#111;margin-top:20px;margin-bottom:10px;">'
        'Computational Models</div>',
        unsafe_allow_html=True
    )

    # ── Lag Sequential Analysis ───────────────────────────────────────────────
    if "behavior" in df.columns and "date" in df.columns:
        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
            'padding:20px;margin-top:16px;">'
            '<div style="font-weight:700;font-size:15px;color:#111;margin-bottom:2px;">'
            'Lag Sequential Analysis</div>'
            '<div style="font-size:12px;color:#6b7280;margin-bottom:14px;">'
            'Examines whether behaviors occur together more or less often than expected by chance. '
            'Each cell shows a z-score: <b style="color:#15803d;">green = facilitated</b> '
            '(behavior B significantly more likely after A), '
            '<b style="color:#dc2626;">red = inhibited</b> (less likely). '
            'Cells outside ±1.96 are statistically significant (p &lt; .05).</div>',
            unsafe_allow_html=True
        )

        # Sort by date + time within sessions
        df_lsa = df.copy()
        if "time" in df_lsa.columns:
            df_lsa["_sort_key"] = pd.to_datetime(
                df_lsa["date"].astype(str) + " " + df_lsa["time"].astype(str), errors="coerce"
            )
        else:
            df_lsa["_sort_key"] = pd.to_datetime(df_lsa["date"], errors="coerce")
        df_lsa = df_lsa.sort_values("_sort_key")

        session_cols = ["date"] + (["setting"] if "setting" in df_lsa.columns else [])

        # Build flattened behavior sequence with None as session boundary
        sequence = []
        for _, grp in df_lsa.groupby(session_cols, sort=False):
            behs = list(grp["behavior"].dropna())
            if len(behs) >= 2:
                sequence.extend(behs)
            sequence.append(None)  # session boundary

        # Count lag-1 transitions (skip boundaries)
        behaviors_lsa = sorted(df_lsa["behavior"].dropna().unique())
        trans = pd.DataFrame(0, index=behaviors_lsa, columns=behaviors_lsa, dtype=float)
        for i in range(len(sequence) - 1):
            a, b = sequence[i], sequence[i + 1]
            if a is not None and b is not None:
                trans.loc[a, b] += 1

        total_trans = trans.values.sum()
        if total_trans >= 4:
            given_totals = trans.sum(axis=1)
            base_rates   = trans.sum(axis=0) / total_trans

            # Compute z-scores (Bakeman & Gottman adjusted residual)
            z_mat = pd.DataFrame(0.0, index=behaviors_lsa, columns=behaviors_lsa)
            cp_mat = pd.DataFrame(0.0, index=behaviors_lsa, columns=behaviors_lsa)
            for giv in behaviors_lsa:
                n_giv = given_totals[giv]
                if n_giv == 0:
                    continue
                for crit in behaviors_lsa:
                    if giv == crit:
                        continue
                    obs_cp = trans.loc[giv, crit] / n_giv
                    p_crit = base_rates[crit]
                    cp_mat.loc[giv, crit] = round(obs_cp, 3)
                    se = np.sqrt(p_crit * (1 - p_crit) / n_giv) if p_crit > 0 else 0
                    if se > 0:
                        z_mat.loc[giv, crit] = round((obs_cp - p_crit) / se, 2)

            # Sort rows/cols by behavior category order
            _BEH_ORDER_LSA = [
                "Aggression", "Non-compliance", "Arguing", "Property destruction", "Elopement",
                "Off-Task", "Fidgeting", "Calling out/ Making sounds", "Out of seat",
                "Mand/ request", "Compliance/ on task", "Self-injurious behavior", "Other",
            ]
            ordered = [b for b in _BEH_ORDER_LSA if b in behaviors_lsa] + \
                      [b for b in behaviors_lsa if b not in _BEH_ORDER_LSA]
            z_mat   = z_mat.reindex(index=ordered, columns=ordered, fill_value=0)
            cp_mat  = cp_mat.reindex(index=ordered, columns=ordered, fill_value=0)

            z_vals  = z_mat.values.tolist()
            # Diagonal = no self-transitions → show as blank
            for i in range(len(ordered)):
                z_vals[i][i] = None
            text_vals = [
                [f"{v:.1f}" if v is not None and abs(v) > 0 else "" for v in row]
                for row in z_vals
            ]

            fig_lsa = _go.Figure(data=_go.Heatmap(
                z=z_vals,
                x=ordered,
                y=ordered,
                text=text_vals,
                texttemplate="%{text}",
                textfont=dict(size=12, color="#111"),
                colorscale=[
                    [0,    "#dc2626"],
                    [0.25, "#fca5a5"],
                    [0.5,  "#ffffff"],
                    [0.75, "#86efac"],
                    [1,    "#15803d"],
                ],
                zmid=0,
                zmin=-3, zmax=3,
                showscale=False,
                hoverongaps=False,
                hovertemplate=(
                    "<b>Given:</b> %{y}<br>"
                    "<b>Then:</b> %{x}<br>"
                    "<b>z =</b> %{z:.2f}<extra></extra>"
                ),
            ))
            fig_lsa.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="system-ui",
                margin=dict(l=0, r=0, t=10, b=0),
                height=max(300, len(ordered) * 58 + 160),
                xaxis=dict(domain=[0.26, 1.0], tickangle=-35, tickfont=dict(size=11),
                           title=dict(text="Then (criterion behavior)", font=dict(size=12))),
                yaxis=dict(domain=[0.22, 1.0], tickfont=dict(size=11),
                           title=dict(text="Given (antecedent behavior)", font=dict(size=12))),
            )
            st.plotly_chart(fig_lsa, use_container_width=True, config=_PLOTLY_CONFIG)

            # Significant transitions table
            sig_rows = []
            for giv in ordered:
                for crit in ordered:
                    if giv == crit:
                        continue
                    z = z_mat.loc[giv, crit]
                    if abs(z) >= 1.96:
                        cp = cp_mat.loc[giv, crit]
                        direction = "Facilitated ↑" if z > 0 else "Inhibited ↓"
                        sig_rows.append({
                            "Given behavior": giv,
                            "Criterion behavior": crit,
                            "z-score": round(z, 2),
                            "Cond. probability": f"{cp:.2f}",
                            "Direction": direction,
                        })
            if sig_rows:
                sig_df = pd.DataFrame(sig_rows).sort_values("z-score", key=abs, ascending=False)
                st.markdown(
                    '<div style="font-size:13px;font-weight:600;color:#111;margin-top:12px;margin-bottom:6px;">'
                    'Significant Transitions (|z| ≥ 1.96, p &lt; .05)</div>',
                    unsafe_allow_html=True
                )
                st.dataframe(sig_df, hide_index=True, use_container_width=True)
            else:
                st.info("No statistically significant transitions detected with current data.")

            st.markdown(
                '<div style="font-size:11px;color:#9ca3af;margin-top:8px;">'
                'Z-scores computed using Bakeman &amp; Gottman (1997) adjusted residual method. '
                'Diagonal (self-transitions) is excluded. '
                'Minimum 4 total transitions required.</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("At least 4 behavior transitions across sessions are needed for lag sequential analysis.")

        st.markdown("</div>", unsafe_allow_html=True)

    # 1. Naive Bayes Function Classifier + Bayesian Updating ──────────────────
    with st.expander("Naive Bayes Function Classifier & Bayesian Updating", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Uses antecedent and consequence tags to estimate the probability each behavior '
            'serves Attention, Escape, Tangible, or Sensory function. '
            'Bayesian updating shows how confidence in each function evolves as data accumulates.</div>',
            unsafe_allow_html=True
        )
        import re as _re

        FUNC_TAGS = {"Att": "Attention", "Tan": "Tangible", "Esc": "Escape", "Sel": "Sensory"}

        def _extract_tags(text):
            return _re.findall(r'\(([A-Za-z]+)\)', str(text) if text else "")

        def _entry_func_vector(row):
            tags = []
            tags += _extract_tags(row.get("antecedent", ""))
            tags += _extract_tags(row.get("consequence", ""))
            return {f: tags.count(f) for f in FUNC_TAGS}

        if "antecedent" in df.columns and "consequence" in df.columns:
            df_nb = df.copy()
            # Build feature matrix
            feat_rows = [_entry_func_vector(r) for _, r in df_nb.iterrows()]
            feat_df = pd.DataFrame(feat_rows, columns=list(FUNC_TAGS.keys())).fillna(0)
            total_tags = feat_df.sum(axis=1)
            labeled = feat_df[total_tags > 0]

            if len(labeled) >= 3:
                # Dirichlet-Multinomial Bayesian posterior per behavior
                behaviors_nb = df_nb["behavior"].dropna().unique()
                prior = np.ones(4)  # uniform Dirichlet prior

                nb_results = []
                for beh in behaviors_nb:
                    mask = (df_nb["behavior"] == beh)
                    beh_feats = feat_df[mask]
                    counts = beh_feats.sum().values + prior
                    posterior = counts / counts.sum()
                    nb_results.append({
                        "Behavior": beh,
                        "Attention": round(posterior[0], 3),
                        "Escape":    round(posterior[2], 3),
                        "Tangible":  round(posterior[1], 3),
                        "Sensory":   round(posterior[3], 3),
                        "Most Likely Function": list(FUNC_TAGS.values())[int(np.argmax(posterior))],
                    })

                nb_df = pd.DataFrame(nb_results).sort_values("Most Likely Function")

                # Stacked bar chart
                fig_nb = _go.Figure()
                colors_nb = {"Attention": "#5b8db8", "Escape": "#c9a840",
                             "Tangible": "#5ca05c", "Sensory": "#c97a5a"}
                for func, color in colors_nb.items():
                    fig_nb.add_trace(_go.Bar(
                        name=func, x=nb_df["Behavior"], y=nb_df[func],
                        marker_color=color,
                        hovertemplate=f"<b>%{{x}}</b><br>{func}: %{{y:.1%}}<extra></extra>",
                    ))
                fig_nb.update_layout(
                    barmode="stack", plot_bgcolor="white", paper_bgcolor="white",
                    font_family="system-ui", height=340,
                    margin=dict(l=0, r=10, t=10, b=0),
                    yaxis=dict(tickformat=".0%", range=[0, 1], gridcolor="#e5e7eb",
                               title="Posterior probability"),
                    xaxis=dict(automargin=True),
                    legend=dict(orientation="h", y=1.08),
                )
                st.plotly_chart(fig_nb, use_container_width=True, config=_PLOTLY_CONFIG)
                st.dataframe(nb_df, hide_index=True, use_container_width=True)

    # 2. Hidden Markov Model ───────────────────────────────────────────────────
    with st.expander("Autoregressive Model (ARIMA) — Behavior Frequency Forecast", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Fits an ARIMA time-series model to daily behavior counts and forecasts '
            'the next 7 days with 95% confidence intervals. '
            'Helps teams anticipate high-frequency periods.</div>',
            unsafe_allow_html=True
        )
        if "behavior" in df.columns and "date" in df.columns:
            try:
                from statsmodels.tsa.arima.model import ARIMA as _ARIMA
                import warnings as _warnings

                df_ar = df.copy()
                df_ar["_date"] = pd.to_datetime(df_ar["date"])
                daily = df_ar.groupby("_date").size().reset_index(name="count")
                daily = daily.set_index("_date").asfreq("D", fill_value=0)

                behaviors_ar = sorted(df_ar["behavior"].dropna().unique())
                sel_beh_ar = st.selectbox(
                    "Behavior to forecast", ["All behaviors"] + list(behaviors_ar),
                    key="arima_beh_sel"
                )
                if sel_beh_ar != "All behaviors":
                    daily = df_ar[df_ar["behavior"] == sel_beh_ar].groupby("_date").size() \
                                 .reindex(daily.index, fill_value=0).to_frame(name="count")

                if len(daily) >= 7:
                    with _warnings.catch_warnings():
                        _warnings.simplefilter("ignore")
                        model_ar = _ARIMA(daily["count"], order=(1, 1, 1))
                        fit_ar = model_ar.fit()

                    forecast = fit_ar.get_forecast(steps=7)
                    fc_mean = forecast.predicted_mean
                    fc_ci = forecast.conf_int(alpha=0.05)
                    fc_dates = pd.date_range(daily.index[-1] + pd.Timedelta(days=1), periods=7)
                    fc_mean.index = fc_dates
                    fc_ci.index = fc_dates

                    fig_ar = _go.Figure()
                    fig_ar.add_trace(_go.Scatter(
                        x=daily.index, y=daily["count"],
                        name="Observed", mode="lines+markers",
                        line=dict(color="#4f6ef7", width=2),
                        marker=dict(size=6),
                    ))
                    fig_ar.add_trace(_go.Scatter(
                        x=fc_dates, y=fc_mean.clip(lower=0),
                        name="Forecast", mode="lines+markers",
                        line=dict(color="#f97316", width=2, dash="dash"),
                        marker=dict(size=7, symbol="diamond"),
                    ))
                    fig_ar.add_trace(_go.Scatter(
                        x=list(fc_dates) + list(fc_dates)[::-1],
                        y=list(fc_ci.iloc[:, 1].clip(lower=0)) +
                          list(fc_ci.iloc[:, 0].clip(lower=0))[::-1],
                        fill="toself", fillcolor="rgba(249,115,22,0.15)",
                        line=dict(width=0), name="95% CI", hoverinfo="skip",
                    ))
                    fig_ar.add_vline(x=str(daily.index[-1]), line_dash="dot",
                                     line_color="#9ca3af", line_width=1.5)
                    fig_ar.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white",
                        font_family="system-ui", height=320,
                        margin=dict(l=0, r=10, t=10, b=0),
                        xaxis=dict(title="Date", gridcolor="#e5e7eb",
                                   tickformat="%b %d"),
                        yaxis=dict(title="Daily count", gridcolor="#e5e7eb",
                                   rangemode="nonnegative", tickformat="d"),
                        legend=dict(orientation="h", y=1.08),
                    )
                    st.plotly_chart(fig_ar, use_container_width=True, config=_PLOTLY_CONFIG)
                    st.markdown(
                        f'<div style="font-size:12px;color:#374151;background:#f9fafb;'
                        f'border-radius:6px;padding:10px 14px;">'
                        f'7-day forecast mean: <b>{fc_mean.mean():.0f}</b> behaviors/day '
                        f'(95% CI: {fc_ci.iloc[:,0].mean():.0f}–{fc_ci.iloc[:,1].mean():.0f}). '
                        f'Shaded region shows uncertainty range.</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.info("At least 7 days of data are needed for ARIMA forecasting.")
            except Exception as e:
                st.warning(f"ARIMA unavailable: {e}")
        else:
            st.info("Behavior and date data required.")

    # 4. Behavioral Network Graph ─────────────────────────────────────────────
    with st.expander("Regression Analysis — Behavior Predictors", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Uses logistic and linear regression to identify which antecedents, consequences, '
            'settings, time-of-day, and day-of-week are the strongest predictors of each behavior. '
            'Coefficients show direction and magnitude of each predictor\'s effect.</div>',
            unsafe_allow_html=True
        )
        if "behavior" not in df.columns or len(df) < 10:
            st.info("At least 10 entries are needed for regression analysis.")
        else:
            import re as _re_reg
            from scipy import stats as _stats

            df_reg = df.copy()

            # ── Feature engineering ──────────────────────────────────────────
            # Time of day → hour (numeric)
            if "time" in df_reg.columns:
                df_reg["_hour"] = pd.to_datetime(df_reg["time"], format="%H:%M", errors="coerce").dt.hour
            else:
                df_reg["_hour"] = np.nan

            # Day of week (0=Mon … 6=Sun)
            if "date" in df_reg.columns:
                df_reg["_dow"] = pd.to_datetime(df_reg["date"], errors="coerce").dt.dayofweek

            # One-hot encode antecedent, consequence, setting (top-N only to keep it readable)
            _TOP_N = 6
            feature_cols = []
            for col, prefix in [("antecedent", "Ant"), ("consequence", "Con"), ("setting", "Set")]:
                if col in df_reg.columns:
                    top_vals = df_reg[col].value_counts().head(_TOP_N).index.tolist()
                    for val in top_vals:
                        safe = _re_reg.sub(r"[^A-Za-z0-9]", "_", str(val))[:20]
                        col_name = f"{prefix}_{safe}"
                        df_reg[col_name] = (df_reg[col] == val).astype(int)
                        feature_cols.append(col_name)

            if "_hour" in df_reg.columns and df_reg["_hour"].notna().sum() > 0:
                feature_cols.append("_hour")
            if "_dow" in df_reg.columns and df_reg["_dow"].notna().sum() > 0:
                feature_cols.append("_dow")

            if not feature_cols:
                st.info("No antecedent, consequence, or setting data available for regression.")
            else:
                behaviors_reg = sorted(df_reg["behavior"].dropna().unique())
                selected_beh = st.selectbox(
                    "Select behavior to model", behaviors_reg, key="reg_beh_sel"
                )

                df_reg["_target"] = (df_reg["behavior"] == selected_beh).astype(int)
                df_model = df_reg[feature_cols + ["_target"]].dropna()

                if len(df_model) < 10 or df_model["_target"].sum() < 3:
                    st.info("Not enough occurrences of this behavior for regression (need ≥ 3 positive cases and ≥ 10 rows).")
                else:
                    X = df_model[feature_cols].values.astype(float)
                    y = df_model["_target"].values.astype(float)

                    # Standardise numeric cols (_hour, _dow) for comparable coefficients
                    X_scaled = X.copy()
                    for j, fc in enumerate(feature_cols):
                        if fc in ("_hour", "_dow"):
                            std = X_scaled[:, j].std()
                            if std > 0:
                                X_scaled[:, j] = (X_scaled[:, j] - X_scaled[:, j].mean()) / std

                    # Add intercept
                    X_int = np.column_stack([np.ones(len(X_scaled)), X_scaled])

                    # Logistic regression via gradient descent (no sklearn dependency)
                    def _sigmoid(z):
                        return 1 / (1 + np.exp(-np.clip(z, -500, 500)))

                    def _logistic_fit(X, y, lr=0.05, iters=500):
                        w = np.zeros(X.shape[1])
                        for _ in range(iters):
                            pred = _sigmoid(X @ w)
                            grad = X.T @ (pred - y) / len(y)
                            w -= lr * grad
                        return w

                    try:
                        w = _logistic_fit(X_int, y)
                        coefs = w[1:]  # drop intercept

                        # Approximate standard errors via Hessian diagonal
                        pred = _sigmoid(X_int @ w)
                        W_diag = pred * (1 - pred)
                        XtWX = X_int.T @ np.diag(W_diag) @ X_int
                        cov = np.linalg.pinv(XtWX)
                        se = np.sqrt(np.diag(cov)[1:])
                        z_scores = coefs / np.where(se > 0, se, 1e-9)
                        p_vals = 2 * (1 - _stats.norm.cdf(np.abs(z_scores)))

                        # Pretty labels
                        label_map = {"_hour": "Time of Day (hour)", "_dow": "Day of Week"}
                        labels = [label_map.get(fc, fc.replace("_", " ")) for fc in feature_cols]

                        reg_df = pd.DataFrame({
                            "Predictor": labels,
                            "Coefficient (log-odds)": np.round(coefs, 3),
                            "Std Error": np.round(se, 3),
                            "z": np.round(z_scores, 2),
                            "p-value": np.round(p_vals, 4),
                            "Significant": ["✓" if p < 0.05 else "" for p in p_vals],
                        }).sort_values("Coefficient (log-odds)", key=abs, ascending=False)

                        # Bar chart of coefficients
                        colors_reg = ["#16a34a" if c > 0 else "#dc2626"
                                      for c in reg_df["Coefficient (log-odds)"]]
                        fig_reg = _go.Figure(_go.Bar(
                            x=reg_df["Predictor"],
                            y=reg_df["Coefficient (log-odds)"],
                            marker_color=colors_reg,
                            hovertemplate="<b>%{x}</b><br>Coef: %{y:.3f}<extra></extra>",
                        ))
                        fig_reg.add_hline(y=0, line_color="#9ca3af", line_width=1)
                        fig_reg.update_layout(
                            plot_bgcolor="white", paper_bgcolor="white",
                            font_family="system-ui", height=320,
                            margin=dict(l=0, r=0, t=10, b=0),
                            xaxis=dict(tickangle=-35, automargin=True),
                            yaxis=dict(title="Log-odds coefficient", gridcolor="#e5e7eb"),
                        )
                        st.plotly_chart(fig_reg, use_container_width=True, config=_PLOTLY_CONFIG)
                        st.dataframe(reg_df, hide_index=True, use_container_width=True)

                        st.markdown(
                            '<div style="font-size:11px;color:#9ca3af;margin-top:8px;">'
                            'Logistic regression with log-odds coefficients. '
                            'Positive = predictor increases likelihood of this behavior; '
                            'negative = decreases likelihood. '
                            '✓ = significant at p &lt; .05. '
                            'Antecedent/consequence/setting features one-hot encoded; '
                            'hour and day-of-week standardized.</div>',
                            unsafe_allow_html=True
                        )
                    except Exception as _reg_err:
                        st.warning(f"Regression could not be computed: {_reg_err}")

    # ── Motivating Operations Analysis ───────────────────────────────────────
    with st.expander("Motivating Operations Analysis", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Shows which motivating operations co-occur most frequently with each behavior '
            'and whether behavior rate is significantly higher on sessions when each MO is present. '
            'Only entries with MO data recorded are included.</div>',
            unsafe_allow_html=True
        )

        # Build MO-enriched dataframe
        mo_entries = [e for e in filtered_entries if e.get("motivating_operations")]
        if len(mo_entries) < 5:
            st.info("At least 5 entries with MO data are needed. Open the ⚡ Motivating Operations section in the New ABC Entry form to start recording.")
        else:
            df_mo = pd.DataFrame(filtered_entries)
            df_mo_only = pd.DataFrame(mo_entries)

            # Build a flat label lookup from MO_DEFAULTS
            _mo_label = {}
            for _dom, _items in MO_DEFAULTS.items():
                for _m in _items:
                    _mo_label[_m["key"]] = _m["label"][:55] + "…" if len(_m["label"]) > 55 else _m["label"]

            # Expand MO dicts into binary columns
            all_mo_keys = set()
            for e in mo_entries:
                all_mo_keys.update(e.get("motivating_operations", {}).keys())
            all_mo_keys = sorted(all_mo_keys)

            for mk in all_mo_keys:
                df_mo[mk] = df_mo["motivating_operations"].apply(
                    lambda d: bool(d.get(mk)) if isinstance(d, dict) else False
                )

            behaviors_mo = sorted(df_mo["behavior"].dropna().unique())
            sel_beh_mo = st.selectbox("Select behavior", behaviors_mo, key="mo_beh_sel")

            beh_mask_mo = df_mo["behavior"] == sel_beh_mo
            total_mo = len(df_mo)

            rows_mo = []
            for mk in all_mo_keys:
                if mk not in df_mo.columns:
                    continue
                mo_present = df_mo[mk].astype(bool)
                n_present  = mo_present.sum()
                n_absent   = total_mo - n_present
                if n_present < 2:
                    continue

                rate_present = (beh_mask_mo & mo_present).sum() / n_present
                rate_absent  = (beh_mask_mo & ~mo_present).sum() / n_absent if n_absent > 0 else 0
                diff = rate_present - rate_absent

                label = _mo_label.get(mk, mk.replace("_", " ").title())
                rows_mo.append({
                    "Motivating Operation": label,
                    "Rate w/ MO": round(rate_present, 3),
                    "Rate w/o MO": round(rate_absent, 3),
                    "Difference": round(diff, 3),
                    "n (MO present)": int(n_present),
                })

            if not rows_mo:
                st.info("Not enough MO variation in the data yet.")
            else:
                mo_df = pd.DataFrame(rows_mo).sort_values("Difference", ascending=False)

                # Bar chart
                bar_colors_mo = ["#16a34a" if d > 0 else "#dc2626" for d in mo_df["Difference"]]
                fig_mo = _go.Figure(_go.Bar(
                    x=mo_df["Motivating Operation"],
                    y=mo_df["Difference"],
                    marker_color=bar_colors_mo,
                    text=[f"{v:+.2f}" for v in mo_df["Difference"]],
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Rate w/ MO: %{customdata[0]:.3f}<br>"
                        "Rate w/o MO: %{customdata[1]:.3f}<br>"
                        "Diff: %{y:+.3f}<extra></extra>"
                    ),
                    customdata=mo_df[["Rate w/ MO", "Rate w/o MO"]].values,
                ))
                fig_mo.add_hline(y=0, line_color="#9ca3af", line_width=1)
                fig_mo.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    font_family="system-ui", height=340,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis=dict(tickangle=-35, automargin=True),
                    yaxis=dict(title="Behavior rate difference", gridcolor="#e5e7eb",
                               tickformat=".2f"),
                )
                st.plotly_chart(fig_mo, use_container_width=True, config=_PLOTLY_CONFIG)
                st.dataframe(mo_df, hide_index=True, use_container_width=True)

                # Plain-language summary
                top_mo = mo_df.iloc[0]
                if top_mo["Difference"] > 0.05:
                    st.markdown(
                        f'<div style="font-size:12px;color:#374151;background:#f0fdf4;'
                        f'border:1px solid #bbf7d0;border-radius:6px;padding:10px 14px;margin-top:6px;">'
                        f'<b>Strongest MO predictor:</b> <i>{top_mo["Motivating Operation"]}</i> — '
                        f'{sel_beh_mo} occurs at a rate of <b>{top_mo["Rate w/ MO"]:.0%}</b> when '
                        f'this condition is present vs. <b>{top_mo["Rate w/o MO"]:.0%}</b> when absent '
                        f'(Δ = {top_mo["Difference"]:+.2f}).</div>',
                        unsafe_allow_html=True
                    )

                st.markdown(
                    '<div style="font-size:11px;color:#9ca3af;margin-top:8px;">'
                    'Positive difference = MO present is associated with higher behavior rate. '
                    'Based only on entries where MO data was recorded.</div>',
                    unsafe_allow_html=True
                )

    # ── Conditional Probability Analysis ─────────────────────────────────────
    with st.expander("Conditional Probability Analysis", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Compares <b>P(behavior | antecedent present)</b> vs. '
            '<b>P(behavior | antecedent absent)</b> for each antecedent-behavior pair. '
            'A large difference between these two probabilities is strong evidence that '
            'the antecedent is a reliable predictor — directly informing function hypotheses.</div>',
            unsafe_allow_html=True
        )
        if "antecedent" not in df.columns or "behavior" not in df.columns or len(df) < 5:
            st.info("At least 5 entries with antecedent and behavior data are needed.")
        else:
            from scipy import stats as _cpa_stats

            behaviors_cpa = sorted(df["behavior"].dropna().unique())
            antecedents_cpa = sorted(df["antecedent"].dropna().unique())
            antecedents_cpa = [a for a in antecedents_cpa if a != ""]

            sel_beh_cpa = st.selectbox(
                "Select behavior", behaviors_cpa, key="cpa_beh_sel"
            )

            rows_cpa = []
            total_n = len(df)
            beh_mask = df["behavior"] == sel_beh_cpa

            for ant in antecedents_cpa:
                ant_mask   = df["antecedent"] == ant
                n_ant      = ant_mask.sum()
                n_no_ant   = total_n - n_ant
                if n_ant == 0:
                    continue

                # P(beh | ant present)
                p_given    = (beh_mask & ant_mask).sum() / n_ant
                # P(beh | ant absent)
                p_absent   = (beh_mask & ~ant_mask).sum() / n_no_ant if n_no_ant > 0 else 0

                # Fisher's exact test for significance
                a = (beh_mask & ant_mask).sum()
                b = n_ant - a
                c = (beh_mask & ~ant_mask).sum()
                d = n_no_ant - c
                _, p_val = _cpa_stats.fisher_exact([[a, b], [c, d]])

                diff = p_given - p_absent
                rows_cpa.append({
                    "Antecedent": ant,
                    "P(beh | ant)": round(p_given, 3),
                    "P(beh | no ant)": round(p_absent, 3),
                    "Difference": round(diff, 3),
                    "n (ant present)": int(n_ant),
                    "p-value": round(p_val, 4),
                    "Significant": "✓" if p_val < 0.05 else "",
                })

            if not rows_cpa:
                st.info("Not enough antecedent data for this behavior.")
            else:
                cpa_df = pd.DataFrame(rows_cpa).sort_values("Difference", ascending=False)

                # Bar chart — difference scores
                bar_colors = ["#16a34a" if d > 0 else "#dc2626"
                              for d in cpa_df["Difference"]]
                fig_cpa = _go.Figure(_go.Bar(
                    x=cpa_df["Antecedent"],
                    y=cpa_df["Difference"],
                    marker_color=bar_colors,
                    text=[f"{v:+.2f}" for v in cpa_df["Difference"]],
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "P(beh|ant): %{customdata[0]:.3f}<br>"
                        "P(beh|no ant): %{customdata[1]:.3f}<br>"
                        "Diff: %{y:+.3f}<extra></extra>"
                    ),
                    customdata=cpa_df[["P(beh | ant)", "P(beh | no ant)"]].values,
                ))
                fig_cpa.add_hline(y=0, line_color="#9ca3af", line_width=1)
                fig_cpa.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    font_family="system-ui", height=320,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis=dict(tickangle=-35, automargin=True),
                    yaxis=dict(title="P(beh|ant) − P(beh|no ant)",
                               gridcolor="#e5e7eb", tickformat=".2f"),
                )
                st.plotly_chart(fig_cpa, use_container_width=True, config=_PLOTLY_CONFIG)
                st.dataframe(cpa_df, hide_index=True, use_container_width=True)

                # Highlight top predictor
                top = cpa_df.iloc[0]
                if top["Difference"] > 0.1:
                    st.markdown(
                        f'<div style="font-size:12px;color:#374151;background:#f0fdf4;'
                        f'border:1px solid #bbf7d0;border-radius:6px;padding:10px 14px;margin-top:4px;">'
                        f'<b>Strongest predictor:</b> <b>{top["Antecedent"]}</b> — '
                        f'{sel_beh_cpa} occurs in <b>{top["P(beh | ant)"]:.0%}</b> of observations '
                        f'when this antecedent is present vs. '
                        f'<b>{top["P(beh | no ant)"]:.0%}</b> when absent '
                        f'(Δ = {top["Difference"]:+.2f}'
                        f'{", p < .05" if top["Significant"] == "✓" else ""}).</div>',
                        unsafe_allow_html=True
                    )
                st.markdown(
                    '<div style="font-size:11px;color:#9ca3af;margin-top:8px;">'
                    'Significance tested with Fisher\'s exact test. '
                    'Positive difference = antecedent increases behavior likelihood; '
                    'negative = decreases. ✓ = significant at p &lt; .05.</div>',
                    unsafe_allow_html=True
                )

    # ── FBA Scatter Plot (Touchette et al., 1985) ─────────────────────────────
    with st.expander("FBA Scatter Plot (Touchette Format)", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Maps behavior occurrences across time slots (rows) and individual '
            'session dates (columns). Filled cells indicate the behavior occurred during '
            'that slot on that date. Identifies predictable time patterns at the session level. '
            'Slot size is adjustable (15 min / 30 min / 1 hour). '
            '<i>Touchette et al. (1985)</i></div>',
            unsafe_allow_html=True
        )
        if "time" not in df.columns or "date" not in df.columns or "behavior" not in df.columns:
            st.info("Time, date, and behavior data are all required for scatter plot analysis.")
        else:
            behaviors_sp = sorted(df["behavior"].dropna().unique())
            sel_beh_sp = st.selectbox(
                "Select behavior", behaviors_sp, key="sp_beh_sel"
            )

            slot_label_map = {
                "15 minutes": 15,
                "30 minutes": 30,
                "1 hour":     60,
            }
            slot_choice = st.radio(
                "Time slot size",
                options=list(slot_label_map.keys()),
                index=1,
                horizontal=True,
                key="sp_slot"
            )
            slot_mins = slot_label_map[slot_choice]

            df_sp = df[df["behavior"] == sel_beh_sp].copy()
            df_sp["_date"] = pd.to_datetime(df_sp["date"], errors="coerce").dt.date
            df_sp = df_sp.dropna(subset=["_date"])

            def _to_slot(t, mins):
                try:
                    h, m = int(str(t).split(":")[0]), int(str(t).split(":")[1])
                    slot_num = (h * 60 + m) // mins
                    start_h  = (slot_num * mins) // 60
                    start_m  = (slot_num * mins) % 60
                    end_tot  = slot_num * mins + mins
                    end_h    = end_tot // 60
                    end_m    = end_tot % 60
                    return (
                        slot_num,
                        f"{start_h}:{'%02d'%start_m}–{end_h}:{'%02d'%end_m}"
                    )
                except Exception:
                    return (None, None)

            df_sp[["_slot_num", "_slot_label"]] = df_sp["time"].apply(
                lambda t: pd.Series(_to_slot(t, slot_mins))
            )
            df_sp = df_sp.dropna(subset=["_slot_num"])
            df_sp["_slot_num"] = df_sp["_slot_num"].astype(int)

            if len(df_sp) == 0:
                st.info("No time data recorded for this behavior.")
            else:
                # Build grid
                all_dates  = sorted(df_sp["_date"].unique())
                slot_info  = df_sp[["_slot_num", "_slot_label"]].drop_duplicates().sort_values("_slot_num")
                all_slots  = slot_info["_slot_num"].tolist()
                slot_labels= slot_info["_slot_label"].tolist()

                # Count occurrences per (date, slot)
                occ = df_sp.groupby(["_date", "_slot_num"]).size().reset_index(name="count")
                occ_lookup = {(r["_date"], r["_slot_num"]): r["count"]
                              for _, r in occ.iterrows()}

                # Build z matrix: rows=slots (bottom→top), cols=dates
                z_grid  = []
                txt_grid = []
                for slot in all_slots:
                    row_z   = []
                    row_txt = []
                    for d in all_dates:
                        cnt = occ_lookup.get((d, slot), 0)
                        row_z.append(cnt)
                        row_txt.append(str(cnt) if cnt > 0 else "")
                    z_grid.append(row_z)
                    txt_grid.append(row_txt)

                date_labels = [str(d) for d in all_dates]
                cell_h = max(28, min(52, 400 // max(len(all_slots), 1)))
                fig_sp = _go.Figure(data=_go.Heatmap(
                    z=z_grid,
                    x=date_labels,
                    y=slot_labels,
                    text=txt_grid,
                    texttemplate="%{text}",
                    textfont=dict(size=12, color="#111"),
                    colorscale=[
                        [0,    "#ffffff"],
                        [0.01, "#dcfce7"],
                        [0.4,  "#4ade80"],
                        [1.0,  "#15803d"],
                    ],
                    zmin=0,
                    showscale=False,
                    hoverongaps=False,
                    hovertemplate="<b>%{y}</b><br>%{x}<br>Occurrences: %{z}<extra></extra>",
                ))
                fig_sp.update_layout(
                    plot_bgcolor="white", paper_bgcolor="white",
                    font_family="system-ui",
                    height=max(300, len(all_slots) * cell_h + 120),
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis=dict(
                        title="Date", tickangle=-45, tickfont=dict(size=11),
                        side="bottom",
                    ),
                    yaxis=dict(
                        title="Time Slot", tickfont=dict(size=11),
                        autorange="reversed",
                    ),
                )
                st.plotly_chart(fig_sp, use_container_width=True, config=_PLOTLY_CONFIG)

                # Summary: which slot has most occurrences
                slot_totals = occ.groupby("_slot_num")["count"].sum()
                if len(slot_totals):
                    peak_slot_num = slot_totals.idxmax()
                    peak_label = slot_info.loc[
                        slot_info["_slot_num"] == peak_slot_num, "_slot_label"
                    ].values[0]
                    peak_n = int(slot_totals.max())
                    pct_slots_active = (z_grid != [[0]*len(all_dates)]*len(all_slots)) and len(all_slots) > 0
                    concentrated = slot_totals.max() / slot_totals.sum() > 0.5
                    st.markdown(
                        f'<div style="font-size:12px;color:#374151;background:#f9fafb;'
                        f'border-radius:6px;padding:10px 14px;margin-top:4px;">'
                        f'<b>{sel_beh_sp}</b> occurs most frequently during '
                        f'<b>{peak_label}</b> ({peak_n} instance{"s" if peak_n != 1 else ""}). '
                        + ('<b>Pattern is concentrated</b> — over 50% of occurrences fall in one time slot, '
                           'suggesting a strong time-based predictor.' if concentrated else
                           'Occurrences are distributed across multiple time slots.')
                        + '</div>',
                        unsafe_allow_html=True
                    )
                st.markdown(
                    '<div style="font-size:11px;color:#9ca3af;margin-top:6px;">'
                    'Based on Touchette, MacDonald &amp; Langer (1985). '
                    'Numbers inside cells show occurrence count per slot. '
                    'Empty cells = no occurrence recorded.</div>',
                    unsafe_allow_html=True
                )


# ── Tab: Interval Recording ───────────────────────────────────────────────────
def tab_interval(all_entries, student_name, observer_name):
    cats = load_categories()

    # ── Session state keys ────────────────────────────────────────────────────
    import time as _time
    SS = st.session_state
    if "iv_active" not in SS:       SS.iv_active = False
    if "iv_grid" not in SS:         SS.iv_grid = {}
    if "iv_behavior" not in SS:     SS.iv_behavior = ""
    if "iv_type" not in SS:         SS.iv_type = "Whole Interval"
    if "iv_length" not in SS:       SS.iv_length = 10
    if "iv_total" not in SS:        SS.iv_total = 20
    if "iv_saved" not in SS:        SS.iv_saved = False
    if "iv_interval_start" not in SS: SS.iv_interval_start = None
    if "iv_current_interval" not in SS: SS.iv_current_interval = 1
    if "iv_flash" not in SS:        SS.iv_flash = False

    # ── Saved confirmation ────────────────────────────────────────────────────
    if SS.iv_saved:
        SS.iv_saved = False
        st.success("Interval session saved successfully.")

    # ── Setup panel (shown when not active) ───────────────────────────────────
    if not SS.iv_active:
        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:14px;'
            'padding:24px;max-width:560px;margin:0 auto;">'
            '<div style="font-size:18px;font-weight:800;color:#111;margin-bottom:4px;">Interval Recording</div>'
            '<div style="font-size:13px;color:#6b7280;margin-bottom:20px;">'
            'Configure your session then tap Start to begin recording.</div>',
            unsafe_allow_html=True
        )

        behavior_opts = cats.get("behaviors", [])
        beh_idx = behavior_opts.index(SS.iv_behavior) if SS.iv_behavior in behavior_opts else 0
        SS.iv_behavior = st.selectbox(
            "Behavior to observe *",
            behavior_opts,
            index=beh_idx,
            key="iv_beh_sel"
        )

        SS.iv_type = st.selectbox(
            "Interval Type",
            ["Whole Interval", "Partial Interval", "Momentary Time Sampling"],
            key="iv_type_sel"
        )

        sc1, sc2 = st.columns(2)
        with sc1:
            SS.iv_length = st.number_input(
                "Interval Length (sec)", min_value=1, value=int(SS.iv_length), key="iv_len_inp"
            )
        with sc2:
            SS.iv_total = st.number_input(
                "Total Intervals", min_value=1, value=int(SS.iv_total), key="iv_total_inp"
            )

        total_sec = SS.iv_length * SS.iv_total
        total_min = total_sec // 60
        total_rem = total_sec % 60
        st.markdown(
            f'<div style="background:#f0fdf4;border-radius:8px;padding:10px 14px;'
            f'font-size:13px;color:#15803d;margin:12px 0;">'
            f'Session length: <b>{total_min}m {total_rem}s</b> '
            f'({SS.iv_total} × {SS.iv_length}s intervals)</div>',
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("▶  Start Session", type="primary", use_container_width=True,
                     key="iv_start_btn"):
            if not SS.iv_behavior:
                st.error("Select a behavior first.")
            else:
                SS.iv_grid = {i: None for i in range(1, int(SS.iv_total) + 1)}
                SS.iv_active = True
                SS.iv_current_interval = 1
                SS.iv_interval_start = _time.time()
                SS.iv_flash = False
                st.rerun()

    # ── Active recording ──────────────────────────────────────────────────────
    else:
        total = int(SS.iv_total)
        iv_len = int(SS.iv_length)
        cur = int(SS.iv_current_interval)
        recorded = sum(1 for v in SS.iv_grid.values() if v is not None)
        occurrences = sum(1 for v in SS.iv_grid.values() if v is True)
        pct = round(occurrences / total * 100, 1) if total else 0

        # ── JS countdown timer (runs in browser, no server refresh needed) ────
        start_ts = int(SS.iv_interval_start) if SS.iv_interval_start else int(_time.time())
        st.markdown(
            f'<style>'
            f'@keyframes ivFlash{{0%{{background:#dc2626}}60%{{background:#fee2e2}}100%{{background:white}}}}'
            f'.iv-card{{background:white;border:1.5px solid #e5e7eb;border-radius:12px;'
            f'padding:16px 20px;margin-bottom:12px;display:flex;align-items:center;'
            f'justify-content:space-between;flex-wrap:wrap;gap:8px;}}'
            f'</style>'
            f'<div class="iv-card" id="iv-card">'
            f'<div>'
            f'<div style="font-size:16px;font-weight:800;color:#111;">{SS.iv_behavior}</div>'
            f'<div style="font-size:12px;color:#6b7280;">{SS.iv_type} · {iv_len}s intervals</div>'
            f'</div>'
            f'<div style="text-align:center;">'
            f'<div id="iv-countdown" style="font-size:56px;font-weight:900;color:#16a34a;'
            f'font-variant-numeric:tabular-nums;line-height:1;">{iv_len}</div>'
            f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">seconds remaining</div>'
            f'</div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px;font-weight:800;color:#111;">#{cur}</div>'
            f'<div style="font-size:11px;color:#6b7280;">of {total} intervals</div>'
            f'</div>'
            f'<div style="display:flex;gap:16px;text-align:center;">'
            f'<div><div style="font-size:20px;font-weight:800;color:#16a34a;">{occurrences}/{total}</div>'
            f'<div style="font-size:11px;color:#6b7280;">X marked</div></div>'
            f'<div><div style="font-size:20px;font-weight:800;color:#16a34a;">{pct}%</div>'
            f'<div style="font-size:11px;color:#6b7280;">% occurrence</div></div>'
            f'</div>'
            f'</div>'
            f'<script>'
            f'(function(){{'
            f'  var ivLen={iv_len}, startTs={start_ts};'
            f'  function tick(){{'
            f'    var el=document.getElementById("iv-countdown");'
            f'    var card=document.getElementById("iv-card");'
            f'    if(!el)return;'
            f'    var elapsed=Math.floor(Date.now()/1000)-startTs;'
            f'    var rem=ivLen-elapsed;'
            f'    if(rem<=0){{'
            f'      el.textContent="0";'
            f'      el.style.color="#dc2626";'
            f'      if(card)card.style.animation="ivFlash 0.8s ease-out";'
            f'      return;'
            f'    }}'
            f'    el.textContent=rem;'
            f'    el.style.color=rem<=3?"#dc2626":rem<=6?"#d97706":"#16a34a";'
            f'    setTimeout(tick,200);'
            f'  }}'
            f'  tick();'
            f'}})();'
            f'</script>',
            unsafe_allow_html=True
        )

        # ── Current interval mark buttons ─────────────────────────────────────
        cur_val = SS.iv_grid.get(cur)
        st.markdown(
            f'<div style="text-align:center;margin-bottom:10px;">'
            f'<div style="font-size:13px;font-weight:700;color:#6b7280;margin-bottom:8px;">'
            f'INTERVAL #{cur} — Mark behavior for this interval:</div>'
            '</div>',
            unsafe_allow_html=True
        )
        mb1, mb2, mb3 = st.columns([2, 2, 4])
        with mb1:
            x_style = "primary" if cur_val is True else "secondary"
            if st.button("✕  X  (Observed)", key="iv_mark_x", use_container_width=True,
                         type=x_style):
                SS.iv_grid[cur] = True
                if cur < total:
                    SS.iv_current_interval = cur + 1
                    SS.iv_interval_start = _time.time()
                st.rerun()
        with mb2:
            o_style = "primary" if cur_val is False else "secondary"
            if st.button("○  O  (Not observed)", key="iv_mark_o", use_container_width=True,
                         type=o_style):
                SS.iv_grid[cur] = False
                if cur < total:
                    SS.iv_current_interval = cur + 1
                    SS.iv_interval_start = _time.time()
                st.rerun()
        with mb3:
            st.markdown(
                '<div style="padding:8px 0;font-size:13px;color:#6b7280;">'
                '<b>X</b> = behavior observed &nbsp;·&nbsp; <b>O</b> = behavior not observed'
                '</div>',
                unsafe_allow_html=True
            )

        # ── Grid overview ─────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:11px;font-weight:700;letter-spacing:.06em;'
            'color:#6b7280;margin:14px 0 6px 0;">ALL INTERVALS</div>',
            unsafe_allow_html=True
        )
        cols_per_row = 10
        intervals = list(SS.iv_grid.keys())
        for row_start in range(0, total, cols_per_row):
            row_intervals = intervals[row_start:row_start + cols_per_row]
            cols = st.columns(len(row_intervals))
            for col, iv_num in zip(cols, row_intervals):
                val = SS.iv_grid[iv_num]
                is_cur = iv_num == cur
                if val is True:
                    label = f"X\n{iv_num}"
                elif val is False:
                    label = f"O\n{iv_num}"
                else:
                    label = f"—\n{iv_num}"
                with col:
                    if st.button(label, key=f"iv_btn_{iv_num}", use_container_width=True,
                                 type="primary" if is_cur else "secondary"):
                        SS.iv_current_interval = iv_num
                        st.rerun()

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # ── Action buttons ────────────────────────────────────────────────────
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if st.button("💾  Save Session", type="primary", use_container_width=True,
                         key="iv_save_btn"):
                student_nums = [e.get("number", 0) for e in all_entries if e.get("student_name") == SS.get("iv_student")]
                next_num = max(student_nums, default=0) + 1
                entry = {
                    "number": next_num,
                    "date": str(date.today()),
                    "time": str(datetime.now().time()),
                    "student_name": student_name,
                    "student_id": roster_id_for_name(student_name),
                    "observer_name": observer_name,
                    "observation_duration_minutes": round(iv_len * total / 60, 2),
                    "behavior": SS.iv_behavior,
                    "interval_type": SS.iv_type,
                    "interval_length_seconds": iv_len,
                    "interval_total": total,
                    "interval_occurrences": occurrences,
                    "interval_pct": pct,
                    "interval_grid": SS.iv_grid,
                    "entry_type": "interval_session",
                }
                all_entries.append(entry)
                save_json(DATA_FILE, all_entries)
                SS.iv_active = False
                SS.iv_grid = {}
                SS.iv_interval_start = None
                SS.iv_current_interval = 1
                SS.iv_saved = True
                st.rerun()
        with ac2:
            if st.button("↺  Reset Grid", use_container_width=True, key="iv_reset_btn"):
                SS.iv_grid = {i: None for i in range(1, total + 1)}
                SS.iv_interval_start = _time.time()
                SS.iv_current_interval = 1
                st.rerun()
        with ac3:
            if st.button("✕  Cancel", use_container_width=True, key="iv_cancel_btn"):
                SS.iv_active = False
                SS.iv_grid = {}
                SS.iv_interval_start = None
                SS.iv_current_interval = 1
                st.rerun()



# ── Indirect Assessment Tab ───────────────────────────────────────────────────
INDIRECT_FILE = os.path.join(DATA_DIR, "indirect_assessments.json")

def load_indirect() -> dict:
    return _safe_load(INDIRECT_FILE, {})

def save_indirect(data: dict):
    _safe_save(INDIRECT_FILE, data)

# ── Instrument definitions ────────────────────────────────────────────────────
_QFAB_ITEMS = [
    # (key, question, response_type)  response_type: "text" | "likert5" | "yesno" | "multi"
    ("qfab_informant",    "Informant name and role", "text"),
    ("qfab_date",         "Date of interview", "text"),
    ("qfab_beh_desc",     "Describe the behavior(s) of concern in observable terms", "text"),
    ("qfab_settings",     "In which settings / times does the behavior most often occur?", "text"),
    ("qfab_settings_not", "In which settings / times does the behavior rarely or never occur?", "text"),
    ("qfab_antecedent",   "What typically happens right before the behavior?", "text"),
    ("qfab_consequence",  "What typically happens right after the behavior?", "text"),
    ("qfab_function_att", "Does the behavior seem to get adult or peer attention?",           "likert5"),
    ("qfab_function_esc", "Does the behavior seem to help the student avoid tasks or demands?","likert5"),
    ("qfab_function_tan", "Does the behavior seem to get access to items or activities?",     "likert5"),
    ("qfab_function_sel", "Does the behavior seem to occur even when alone (sensory/automatic)?","likert5"),
    ("qfab_history",      "How long has this behavior been a concern?", "text"),
    ("qfab_prior_int",    "What interventions have been tried? Were they effective?", "text"),
    ("qfab_summary",      "Additional comments or hypotheses from informant", "text"),
]

_FACTS_ITEMS = [
    ("facts_informant",   "Informant name and role", "text"),
    ("facts_date",        "Date", "text"),
    ("facts_beh_topog",   "Describe the behavior (topography — what does it look like physically?)", "text"),
    ("facts_beh_freq",    "How often does the behavior occur? (times per day / week)", "text"),
    ("facts_beh_dur",     "How long does each episode typically last?", "text"),
    ("facts_beh_intense", "How intense / disruptive is the behavior?", "likert5"),
    ("facts_time_am",     "Morning (before 10 am): behavior likelihood",   "likert5"),
    ("facts_time_mid",    "Mid-morning (10 am–noon): behavior likelihood", "likert5"),
    ("facts_time_lunch",  "Lunch / transition: behavior likelihood",       "likert5"),
    ("facts_time_pm",     "Afternoon: behavior likelihood",                "likert5"),
    ("facts_time_late",   "Late day / end of school: behavior likelihood", "likert5"),
    ("facts_setting_ind", "Independent work: behavior likelihood",  "likert5"),
    ("facts_setting_grp", "Group instruction: behavior likelihood", "likert5"),
    ("facts_setting_un",  "Unstructured time: behavior likelihood", "likert5"),
    ("facts_setting_trn", "Transitions: behavior likelihood",       "likert5"),
    ("facts_ant_demand",  "Antecedent — Difficult task / demand presented",        "likert5"),
    ("facts_ant_correct", "Antecedent — Correction / redirection given",           "likert5"),
    ("facts_ant_peer",    "Antecedent — Peer interaction / conflict",              "likert5"),
    ("facts_ant_att_div", "Antecedent — Adult attention diverted",                 "likert5"),
    ("facts_ant_denied",  "Antecedent — Preferred item/activity denied or removed","likert5"),
    ("facts_con_att",     "Consequence — Adult attention provided",      "likert5"),
    ("facts_con_remove",  "Consequence — Task/demand removed or reduced","likert5"),
    ("facts_con_peer",    "Consequence — Peer attention",               "likert5"),
    ("facts_con_item",    "Consequence — Access to item/activity",      "likert5"),
    ("facts_con_none",    "Consequence — No observable change",         "likert5"),
    ("facts_function",    "What is your best guess about the primary function of this behavior?", "text"),
    ("facts_summary",     "Additional notes", "text"),
]

_FAI_ITEMS = [
    ("fai_informant",      "Informant name and role", "text"),
    ("fai_date",           "Date", "text"),
    ("fai_describe",       "Describe the target behavior(s) in observable, measurable terms", "text"),
    ("fai_exceptions",     "Are there times when the behavior never occurs? Describe.", "text"),
    ("fai_med_rx",         "Is the student on any medications that may affect behavior?", "text"),
    ("fai_medical",        "Any medical or physical conditions relevant to behavior?", "text"),
    ("fai_sleep",          "Typical sleep pattern — hours per night, any disruptions?", "text"),
    ("fai_diet",           "Any dietary concerns that may affect behavior?", "text"),
    ("fai_comm_level",     "Student's primary communication mode and approximate level", "text"),
    ("fai_reinf_social",   "Effectiveness of social praise as reinforcer",    "likert5"),
    ("fai_reinf_tangible", "Effectiveness of tangible items as reinforcers",  "likert5"),
    ("fai_reinf_activity", "Effectiveness of preferred activities as reinforcers", "likert5"),
    ("fai_reinf_sensory",  "Effectiveness of sensory input as reinforcer",    "likert5"),
    ("fai_reinf_escape",   "Does the student work to avoid / escape tasks?",  "likert5"),
    ("fai_reinf_items",    "List specific reinforcers observed to be effective", "text"),
    ("fai_antecedents",    "List the most common antecedents you observe", "text"),
    ("fai_consequences",   "List the most common consequences that follow the behavior", "text"),
    ("fai_function_att",   "Function: Attention-maintained likelihood",  "likert5"),
    ("fai_function_esc",   "Function: Escape-maintained likelihood",     "likert5"),
    ("fai_function_tan",   "Function: Tangible-maintained likelihood",   "likert5"),
    ("fai_function_auto",  "Function: Automatic/sensory likelihood",     "likert5"),
    ("fai_hypothesis",     "State your functional hypothesis in a summary sentence", "text"),
    ("fai_notes",          "Additional observations", "text"),
]

_FAST_ITEMS = [
    ("fast_informant",  "Informant name and role", "text"),
    ("fast_date",       "Date", "text"),
    # Attention subscale
    ("fast_1",  "The behavior occurs when you stop attending to this person",           "likert5"),
    ("fast_2",  "The behavior occurs when you are attending to someone else",           "likert5"),
    ("fast_3",  "The behavior stops when you provide attention",                        "likert5"),
    ("fast_4",  "The behavior occurs to get you to do something with the person",       "likert5"),
    # Escape subscale
    ("fast_5",  "The behavior occurs when the person is asked to do something",         "likert5"),
    ("fast_6",  "The behavior occurs during difficult tasks",                           "likert5"),
    ("fast_7",  "The behavior stops when demands are removed",                          "likert5"),
    ("fast_8",  "The behavior occurs to avoid or delay activities",                     "likert5"),
    # Tangible subscale
    ("fast_9",  "The behavior occurs when preferred items are taken away",              "likert5"),
    ("fast_10", "The behavior occurs when the person cannot access preferred items",    "likert5"),
    ("fast_11", "The behavior stops when preferred items are given",                    "likert5"),
    ("fast_12", "The behavior occurs to get items or activities",                       "likert5"),
    # Sensory/Automatic subscale
    ("fast_13", "The behavior occurs even when no one is watching",                     "likert5"),
    ("fast_14", "The behavior occurs even when the person has everything they want",    "likert5"),
    ("fast_15", "The behavior seems to be self-stimulatory (sensory input)",            "likert5"),
    ("fast_16", "The behavior occurs regardless of what is happening in the environment","likert5"),
    ("fast_notes", "Additional comments", "text"),
]

_MAS_ITEMS = [
    ("mas_informant",  "Informant name and role", "text"),
    ("mas_date",       "Date", "text"),
    # Sensory subscale (items 1–4 in original MAS)
    ("mas_1",  "Would the behavior occur continuously if no one was around?",                          "likert6"),
    ("mas_2",  "Does the behavior occur when the person is left alone?",                              "likert6"),
    ("mas_3",  "Does the behavior occur even though no one is watching?",                             "likert6"),
    ("mas_4",  "Does the behavior seem to be self-reinforcing (provides its own reward)?",            "likert6"),
    # Escape subscale (items 5–8)
    ("mas_5",  "Does the behavior occur when a request is made of the person?",                       "likert6"),
    ("mas_6",  "Does the behavior seem to occur when the person wants to avoid a task?",              "likert6"),
    ("mas_7",  "Does the behavior occur when the person is told they cannot do something?",           "likert6"),
    ("mas_8",  "Does the behavior seem to occur when an activity has become too difficult?",          "likert6"),
    # Attention subscale (items 9–12)
    ("mas_9",  "Does the behavior occur when you stop attending to the person?",                      "likert6"),
    ("mas_10", "Does the behavior seem to be a way of getting your attention?",                       "likert6"),
    ("mas_11", "Does the behavior occur when you are talking to someone else?",                       "likert6"),
    ("mas_12", "Does the behavior occur when you are not paying attention to the person?",            "likert6"),
    # Tangible subscale (items 13–16)
    ("mas_13", "Does the behavior occur when preferred objects/activities are not available?",         "likert6"),
    ("mas_14", "Does the behavior seem to be a way of getting a desired item or activity?",           "likert6"),
    ("mas_15", "Does the behavior occur when you take away a preferred object/activity?",             "likert6"),
    ("mas_16", "Does the behavior occur when preferred items are present but unavailable?",           "likert6"),
    ("mas_notes", "Additional comments", "text"),
]

_LIKERT5_OPTS  = ["0 — Never", "1 — Rarely", "2 — Sometimes", "3 — Often", "4 — Always"]
_LIKERT6_OPTS  = ["0 — Never", "1 — Almost never", "2 — Seldom", "3 — Half the time", "4 — Usually", "5 — Almost always", "6 — Always"]

def _likert_score(val, max_val=4):
    """Return numeric score from a likert option string."""
    try:
        return int(str(val).split("—")[0].strip())
    except Exception:
        return 0

def _render_indirect_form(instrument_key, items, student, saved_data):
    """Render a form for one indirect assessment instrument. Returns saved dict on submit."""
    prefix = f"ia_{instrument_key}_{student}_"
    with st.form(f"ia_form_{instrument_key}_{student}"):
        responses = {}
        for key, question, rtype in items:
            st.markdown(
                f'<div style="font-size:13px;font-weight:600;color:#111;margin-top:10px;">'
                f'{question}</div>',
                unsafe_allow_html=True
            )
            saved_val = saved_data.get(key, "")
            if rtype == "text":
                responses[key] = st.text_area(
                    question, value=str(saved_val) if saved_val else "",
                    label_visibility="collapsed", key=prefix + key, height=68
                )
            elif rtype == "likert5":
                cur_val = saved_val if saved_val in _LIKERT5_OPTS else _LIKERT5_OPTS[0]
                responses[key] = st.select_slider(
                    question, options=_LIKERT5_OPTS, value=cur_val,
                    label_visibility="collapsed", key=prefix + key
                )
            elif rtype == "likert6":
                cur_val = saved_val if saved_val in _LIKERT6_OPTS else _LIKERT6_OPTS[0]
                responses[key] = st.select_slider(
                    question, options=_LIKERT6_OPTS, value=cur_val,
                    label_visibility="collapsed", key=prefix + key
                )
        submitted = st.form_submit_button("💾  Save Responses", type="primary")
    if submitted:
        return responses
    return None


def _mas_subscale_scores(resp):
    keys = [
        ("Sensory / Automatic", ["mas_1","mas_2","mas_3","mas_4"]),
        ("Escape",              ["mas_5","mas_6","mas_7","mas_8"]),
        ("Attention",           ["mas_9","mas_10","mas_11","mas_12"]),
        ("Tangible",            ["mas_13","mas_14","mas_15","mas_16"]),
    ]
    scores = {}
    for label, ks in keys:
        scores[label] = sum(_likert_score(resp.get(k, ""), max_val=6) for k in ks)
    return scores

def _fast_subscale_scores(resp):
    keys = [
        ("Attention", ["fast_1","fast_2","fast_3","fast_4"]),
        ("Escape",    ["fast_5","fast_6","fast_7","fast_8"]),
        ("Tangible",  ["fast_9","fast_10","fast_11","fast_12"]),
        ("Sensory / Automatic", ["fast_13","fast_14","fast_15","fast_16"]),
    ]
    scores = {}
    for label, ks in keys:
        scores[label] = sum(_likert_score(resp.get(k, ""), max_val=4) for k in ks)
    return scores

def _fai_function_scores(resp):
    return {
        "Attention":           _likert_score(resp.get("fai_function_att", ""), 4),
        "Escape":              _likert_score(resp.get("fai_function_esc", ""), 4),
        "Tangible":            _likert_score(resp.get("fai_function_tan", ""), 4),
        "Sensory / Automatic": _likert_score(resp.get("fai_function_auto",""), 4),
    }

def _qfab_function_scores(resp):
    return {
        "Attention":           _likert_score(resp.get("qfab_function_att", ""), 4),
        "Escape":              _likert_score(resp.get("qfab_function_esc", ""), 4),
        "Tangible":            _likert_score(resp.get("qfab_function_tan", ""), 4),
        "Sensory / Automatic": _likert_score(resp.get("qfab_function_sel", ""), 4),
    }

def _render_function_bar(scores, title="Function Profile"):
    if not any(scores.values()):
        return
    labels = list(scores.keys())
    vals   = list(scores.values())
    colors = ["#6366f1", "#f59e0b", "#10b981", "#ef4444"]
    fig = _go.Figure(_go.Bar(
        x=labels, y=vals,
        marker_color=colors[:len(labels)],
        text=vals, textposition="outside",
    ))
    fig.update_layout(
        title=title,
        plot_bgcolor="white", paper_bgcolor="white",
        font_family="system-ui",
        height=260,
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis=dict(title="Score", tickformat="d"),
        xaxis=dict(title=""),
    )
    st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CONFIG)


def tab_indirect_assessment(student: str):
    ia_all  = load_indirect()
    ia_data = ia_all.get(student, {})

    # ── Session state for selected instrument ─────────────────────────────────
    nav_key = f"ia_nav_{student}"
    if nav_key not in st.session_state:
        st.session_state[nav_key] = "QFAB"

    _INSTRUMENTS = [
        ("QFAB",        "qfab",       "📝"),
        ("FACTS",       "facts",      "📋"),
        ("FAI",         "fai",        "📄"),
        ("FAST",        "fast",       "⚡"),
        ("MAS",         "mas",        "📊"),
        ("Results",     None,         "📊"),
    ]

    nav_col, content_col = st.columns([1, 3], gap="medium")

    with nav_col:
        for name, data_key, icon in _INSTRUMENTS:
            is_active   = st.session_state[nav_key] == name
            is_complete = bool(data_key and ia_data.get(data_key))
            label = f"✓ {name}" if is_complete else name
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"ia_nav_btn_{student}_{name}",
                         use_container_width=True, type=btn_type):
                st.session_state[nav_key] = name
                st.rerun()

    selected = st.session_state[nav_key]

    with content_col:

        # ── Results ──────────────────────────────────────────────────────────
        if selected == "Results":
            saved_qfab  = ia_data.get("qfab",  {})
            saved_facts = ia_data.get("facts", {})
            saved_fai   = ia_data.get("fai",   {})
            saved_fast  = ia_data.get("fast",  {})
            saved_mas   = ia_data.get("mas",   {})

            functions = ["Attention", "Escape", "Tangible", "Sensory / Automatic"]
            completed = {}
            if saved_qfab:  completed["QFAB"]  = _qfab_function_scores(saved_qfab)
            if saved_fai:   completed["FAI"]   = _fai_function_scores(saved_fai)
            if saved_fast:  completed["FAST"]  = _fast_subscale_scores(saved_fast)
            if saved_mas:   completed["MAS"]   = _mas_subscale_scores(saved_mas)

            if not completed and not saved_facts:
                st.info("No instruments completed yet. Select an instrument from the left panel and save responses to see results here.")
            else:
                # ── Cross-instrument comparison table ─────────────────────────
                if completed:
                    st.markdown(
                        '<div style="font-weight:700;font-size:15px;color:#111;margin-bottom:10px;">'
                        'Cross-Instrument Function Summary</div>',
                        unsafe_allow_html=True
                    )
                    table_rows = []
                    for inst, scores in completed.items():
                        total = sum(scores.values()) or 1
                        row = {"Instrument": inst}
                        for fn in functions:
                            row[fn] = f"{scores.get(fn, 0) / total * 100:.0f}%"
                        row["Top Function"] = max(scores, key=scores.get)
                        table_rows.append(row)
                    st.dataframe(
                        pd.DataFrame(table_rows).set_index("Instrument"),
                        use_container_width=True
                    )
                    st.markdown(
                        '<div style="font-weight:700;font-size:15px;color:#111;'
                        'margin-top:18px;margin-bottom:6px;">Function Profile by Instrument</div>',
                        unsafe_allow_html=True
                    )
                    colors = {"Attention": "#6366f1", "Escape": "#f59e0b",
                              "Tangible": "#10b981", "Sensory / Automatic": "#ef4444"}
                    fig_cross = _go.Figure()
                    for fn in functions:
                        fig_cross.add_trace(_go.Bar(
                            name=fn,
                            x=list(completed.keys()),
                            y=[completed[inst].get(fn, 0) for inst in completed],
                            marker_color=colors[fn],
                        ))
                    fig_cross.update_layout(
                        barmode="group",
                        plot_bgcolor="white", paper_bgcolor="white",
                        font_family="system-ui", height=300,
                        margin=dict(l=0, r=0, t=10, b=0),
                        yaxis=dict(title="Score", tickformat="d"),
                        xaxis=dict(title=""),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig_cross, use_container_width=True, config=_PLOTLY_CONFIG)
                    top_counts = {fn: 0 for fn in functions}
                    for scores in completed.values():
                        top_counts[max(scores, key=scores.get)] += 1
                    consensus_fn = max(top_counts, key=top_counts.get)
                    n_agree = top_counts[consensus_fn]
                    n_total = len(completed)
                    st.markdown(
                        f'<div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-radius:10px;'
                        f'padding:14px 18px;margin-top:4px;">'
                        f'<b>{n_agree} of {n_total} instrument{"s" if n_total > 1 else ""} '
                        f'point to <span style="color:#16a34a;">{consensus_fn}</span> '
                        f'as the primary function.</b>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                # ── FACTS charts ──────────────────────────────────────────────
                if saved_facts:
                    st.markdown(
                        '<div style="font-weight:700;font-size:15px;color:#111;'
                        'margin-top:22px;margin-bottom:6px;">FACTS — Time of Day Likelihood</div>',
                        unsafe_allow_html=True
                    )
                    time_keys = [
                        ("facts_time_am",   "Morning"),
                        ("facts_time_mid",  "Mid-morning"),
                        ("facts_time_lunch","Lunch"),
                        ("facts_time_pm",   "Afternoon"),
                        ("facts_time_late", "Late day"),
                    ]
                    t_labels = [l for _, l in time_keys]
                    t_vals   = [_likert_score(saved_facts.get(k, "")) for k, _ in time_keys]
                    fig_t = _go.Figure(_go.Bar(x=t_labels, y=t_vals, marker_color="#6366f1",
                                               text=t_vals, textposition="outside"))
                    fig_t.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                        font_family="system-ui", height=220,
                                        margin=dict(l=0,r=0,t=10,b=0),
                                        yaxis=dict(title="Rating (0–4)", tickformat="d", range=[0,5]))
                    st.plotly_chart(fig_t, use_container_width=True, config=_PLOTLY_CONFIG)

                    st.markdown(
                        '<div style="font-weight:700;font-size:15px;color:#111;'
                        'margin-top:14px;margin-bottom:6px;">FACTS — Setting Likelihood</div>',
                        unsafe_allow_html=True
                    )
                    setting_keys = [
                        ("facts_setting_ind", "Independent"),
                        ("facts_setting_grp", "Group"),
                        ("facts_setting_un",  "Unstructured"),
                        ("facts_setting_trn", "Transitions"),
                    ]
                    s_labels = [l for _, l in setting_keys]
                    s_vals   = [_likert_score(saved_facts.get(k, "")) for k, _ in setting_keys]
                    fig_s = _go.Figure(_go.Bar(x=s_labels, y=s_vals, marker_color="#10b981",
                                               text=s_vals, textposition="outside"))
                    fig_s.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                        font_family="system-ui", height=220,
                                        margin=dict(l=0,r=0,t=10,b=0),
                                        yaxis=dict(title="Rating (0–4)", tickformat="d", range=[0,5]))
                    st.plotly_chart(fig_s, use_container_width=True, config=_PLOTLY_CONFIG)

                    st.markdown(
                        '<div style="font-weight:700;font-size:15px;color:#111;'
                        'margin-top:14px;margin-bottom:6px;">FACTS — Antecedent Ratings</div>',
                        unsafe_allow_html=True
                    )
                    ant_keys = [
                        ("facts_ant_demand",  "Difficult task"),
                        ("facts_ant_correct", "Correction"),
                        ("facts_ant_peer",    "Peer conflict"),
                        ("facts_ant_att_div", "Attn. diverted"),
                        ("facts_ant_denied",  "Item denied"),
                    ]
                    a_labels = [l for _, l in ant_keys]
                    a_vals   = [_likert_score(saved_facts.get(k, "")) for k, _ in ant_keys]
                    fig_a = _go.Figure(_go.Bar(x=a_labels, y=a_vals, marker_color="#f59e0b",
                                               text=a_vals, textposition="outside"))
                    fig_a.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                        font_family="system-ui", height=220,
                                        margin=dict(l=0,r=0,t=10,b=0),
                                        yaxis=dict(title="Rating (0–4)", tickformat="d", range=[0,5]))
                    st.plotly_chart(fig_a, use_container_width=True, config=_PLOTLY_CONFIG)

                # ── FAI informant hypothesis ──────────────────────────────────
                if saved_fai:
                    hyp = saved_fai.get("fai_hypothesis", "").strip()
                    if hyp:
                        st.markdown(
                            f'<div style="background:#f0fdf4;border:1.5px solid #bbf7d0;'
                            f'border-radius:10px;padding:14px 18px;margin-top:16px;">'
                            f'<div style="font-size:11px;font-weight:700;color:#16a34a;margin-bottom:4px;">'
                            f'FAI — INFORMANT HYPOTHESIS</div>'
                            f'<div style="font-size:13px;color:#111;">{hyp}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

        # ── QFAB ─────────────────────────────────────────────────────────────
        elif selected == "QFAB":
            st.markdown(
                '<div style="font-size:12px;color:#6b7280;margin-bottom:10px;">'
                '<b>Questionnaire for Functional Behavioral Assessment (QFAB)</b> — '
                'A flexible open-format interview covering behavior description, '
                'antecedents, consequences, and informant-rated function hypotheses. '
                'Suitable for teacher or parent informants.</div>',
                unsafe_allow_html=True
            )
            saved_qfab = ia_data.get("qfab", {})
            result = _render_indirect_form("qfab", _QFAB_ITEMS, student, saved_qfab)
            if result is not None:
                ia_data["qfab"] = result
                ia_all[student] = ia_data
                save_indirect(ia_all)
                audit_log("INDIRECT_SAVE", f"QFAB saved for '{student}'")
                st.toast("QFAB saved.", icon="✅")

        # ── FACTS ────────────────────────────────────────────────────────────
        elif selected == "FACTS":
            st.markdown(
                '<div style="font-size:12px;color:#6b7280;margin-bottom:10px;">'
                '<b>Functional Assessment Checklist for Teachers and Staff (FACTS)</b> — '
                'O\'Neill et al. Two-part interview: Part A identifies routines and settings; '
                'Part B focuses the analysis on the highest-priority routine. '
                'Rates antecedents, consequences, and perceived function.</div>',
                unsafe_allow_html=True
            )
            saved_facts = ia_data.get("facts", {})
            result = _render_indirect_form("facts", _FACTS_ITEMS, student, saved_facts)
            if result is not None:
                ia_data["facts"] = result
                ia_all[student] = ia_data
                save_indirect(ia_all)
                audit_log("INDIRECT_SAVE", f"FACTS saved for '{student}'")
                st.toast("FACTS saved.", icon="✅")

        # ── FAI ──────────────────────────────────────────────────────────────
        elif selected == "FAI":
            st.markdown(
                '<div style="font-size:12px;color:#6b7280;margin-bottom:10px;">'
                '<b>Functional Assessment Interview (FAI)</b> — O\'Neill et al. '
                'Comprehensive structured interview covering behavior description, '
                'ecological factors (medical, sleep, diet), communication profile, '
                'reinforcer effectiveness, and functional hypothesis. '
                'Typically completed with a teacher and parent.</div>',
                unsafe_allow_html=True
            )
            saved_fai = ia_data.get("fai", {})
            result = _render_indirect_form("fai", _FAI_ITEMS, student, saved_fai)
            if result is not None:
                ia_data["fai"] = result
                ia_all[student] = ia_data
                save_indirect(ia_all)
                audit_log("INDIRECT_SAVE", f"FAI saved for '{student}'")
                st.toast("FAI saved.", icon="✅")

        # ── FAST ─────────────────────────────────────────────────────────────
        elif selected == "FAST":
            st.markdown(
                '<div style="font-size:12px;color:#6b7280;margin-bottom:10px;">'
                '<b>Functional Analysis Screening Tool (FAST)</b> — Iwata & DeLeon. '
                '16-item rating scale organized into four subscales: '
                'Attention, Escape, Tangible, and Sensory/Automatic. '
                'Highest subscale score indicates the most likely behavioral function. '
                'Quick to administer (5–10 minutes).</div>',
                unsafe_allow_html=True
            )
            saved_fast = ia_data.get("fast", {})
            result = _render_indirect_form("fast", _FAST_ITEMS, student, saved_fast)
            if result is not None:
                ia_data["fast"] = result
                ia_all[student] = ia_data
                save_indirect(ia_all)
                audit_log("INDIRECT_SAVE", f"FAST saved for '{student}'")
                st.toast("FAST saved.", icon="✅")

        # ── MAS ──────────────────────────────────────────────────────────────
        elif selected == "MAS":
            st.markdown(
                '<div style="font-size:12px;color:#6b7280;margin-bottom:10px;">'
                '<b>Motivation Assessment Scale (MAS)</b> — Durand & Crimmins (1988). '
                '16-item rating scale with four subscales: Sensory, Escape, Attention, Tangible. '
                'Each subscale scored 0–24. Widely used in clinical and school settings. '
                'Complete one MAS per behavior of concern.</div>',
                unsafe_allow_html=True
            )
            saved_mas = ia_data.get("mas", {})
            result = _render_indirect_form("mas", _MAS_ITEMS, student, saved_mas)
            if result is not None:
                ia_data["mas"] = result
                ia_all[student] = ia_data
                save_indirect(ia_all)
                audit_log("INDIRECT_SAVE", f"MAS saved for '{student}'")
                st.toast("MAS saved.", icon="✅")

        # ── Reinforcer Assessment ─────────────────────────────────────────────


# ── Reinforcer Assessment Tab ─────────────────────────────────────────────────
_REINF_RATING = ["0 — Not effective", "1 — Mildly effective",
                 "2 — Moderately effective", "3 — Highly effective", "4 — Most preferred"]
_POS_REINFORCERS = [
    ("pr_verbal_praise",    "Verbal praise / specific praise",              "Social"),
    ("pr_attention",        "One-on-one adult attention",                    "Social"),
    ("pr_peer_interaction", "Peer interaction / social time",                "Social"),
    ("pr_high_five",        "Physical acknowledgment (high-five, fist bump)","Social"),
    ("pr_stickers",         "Stickers / stamps / tokens",                    "Tangible"),
    ("pr_food_snack",       "Preferred food or snack",                       "Tangible"),
    ("pr_fidget",           "Fidget or sensory toy",                         "Tangible"),
    ("pr_prize_box",        "Prize box / treasure chest item",               "Tangible"),
    ("pr_screen_time",      "Screen time / tablet / computer",               "Activity"),
    ("pr_free_choice",      "Free choice / preferred activity time",         "Activity"),
    ("pr_game",             "Game (board game, card game, video game)",      "Activity"),
    ("pr_movement",         "Movement break / physical activity",            "Activity"),
    ("pr_music",            "Music / listening to preferred songs",          "Sensory"),
    ("pr_sensory_input",    "Preferred sensory input (squeeze, spin, etc.)", "Sensory"),
    ("pr_quiet_space",      "Access to quiet space",                         "Sensory"),
    ("pr_helper_role",      "Helper / leadership role in class",             "Other"),
    ("pr_homework_pass",    "Homework pass / reduced work",                  "Other"),
    ("pr_extra_recess",     "Extra recess or outdoor time",                  "Other"),
]
_NEG_REINFORCERS = [
    ("nr_demand_removal",   "Task or demand removed / reduced",               "Escape — Task"),
    ("nr_task_shortened",   "Task shortened or broken into smaller steps",    "Escape — Task"),
    ("nr_diff_reduced",     "Difficulty of task reduced",                     "Escape — Task"),
    ("nr_peer_removed",     "Removed from group or peer proximity",           "Escape — Social"),
    ("nr_adult_backs_off",  "Adult withdraws / stops giving attention",       "Escape — Social"),
    ("nr_alone_time",       "Access to time alone / isolation preferred",     "Escape — Social"),
    ("nr_avoid_transition", "Transition delayed or avoided",                  "Escape — Transition"),
    ("nr_avoid_noise",      "Removed from noisy / crowded environment",       "Escape — Sensory"),
    ("nr_avoid_bright",     "Removed from bright lights / visual stimulation","Escape — Sensory"),
    ("nr_avoid_touch",      "Avoids unexpected touch or physical proximity",  "Escape — Sensory"),
]

def tab_reinforcers(student: str):
    ia_all  = load_indirect()
    ia_data = ia_all.get(student, {})
    saved_reinf = ia_data.get("reinforcers", {})

    pr_col, nr_col = st.columns(2)

    # ── Positive ─────────────────────────────────────────────────────────────
    with pr_col:
        st.markdown(
            '<div style="font-weight:700;font-size:14px;color:#6366f1;margin-bottom:8px;">'
            'Positive Reinforcers</div>',
            unsafe_allow_html=True
        )
        with st.form(f"reinf_form_pos_{student}"):
            pr_responses = {}
            categories = list(dict.fromkeys(c for _, _, c in _POS_REINFORCERS))
            for cat in categories:
                st.markdown(
                    f'<div style="font-size:11px;font-weight:700;color:#6366f1;'
                    f'text-transform:uppercase;letter-spacing:.05em;margin-top:12px;">'
                    f'{cat}</div>',
                    unsafe_allow_html=True
                )
                for key, label, c in _POS_REINFORCERS:
                    if c != cat:
                        continue
                    saved_val = saved_reinf.get(key, _REINF_RATING[0])
                    cur_val = saved_val if saved_val in _REINF_RATING else _REINF_RATING[0]
                    st.markdown(
                        f'<div style="font-size:12px;font-weight:600;color:#111;margin-top:6px;">'
                        f'{label}</div>', unsafe_allow_html=True
                    )
                    pr_responses[key] = st.select_slider(
                        label, options=_REINF_RATING, value=cur_val,
                        label_visibility="collapsed", key=f"reinf_pr_{student}_{key}"
                    )
            pr_notes = st.text_area(
                "Notes", value=saved_reinf.get("pr_notes", ""),
                key=f"reinf_pr_notes_{student}", height=60
            )
            pr_submitted = st.form_submit_button("💾  Save", type="primary", use_container_width=True)
        if pr_submitted:
            updated = {**saved_reinf, **pr_responses, "pr_notes": pr_notes}
            ia_data["reinforcers"] = updated
            ia_all[student] = ia_data
            save_indirect(ia_all)
            audit_log("INDIRECT_SAVE", f"Positive reinforcers saved for '{student}'")
            st.toast("Positive reinforcers saved.", icon="✅")
            saved_reinf = ia_data.get("reinforcers", {})
        pr_scores = {label: _likert_score(saved_reinf.get(key, ""), 4)
                     for key, label, _ in _POS_REINFORCERS}
        top_pr = {k: v for k, v in pr_scores.items() if v > 0}
        if top_pr:
            top_sorted = dict(sorted(top_pr.items(), key=lambda x: x[1], reverse=True)[:8])
            fig_pr = _go.Figure(_go.Bar(
                x=list(top_sorted.values()), y=list(top_sorted.keys()),
                orientation="h", marker_color="#6366f1",
                text=list(top_sorted.values()), textposition="outside",
            ))
            fig_pr.update_layout(
                title="Top Positive Reinforcers",
                plot_bgcolor="white", paper_bgcolor="white", font_family="system-ui",
                height=max(200, len(top_sorted) * 30 + 60),
                margin=dict(l=0, r=40, t=40, b=0),
                xaxis=dict(tickformat="d", range=[0, 5]),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_pr, use_container_width=True, config=_PLOTLY_CONFIG)

    # ── Negative ─────────────────────────────────────────────────────────────
    with nr_col:
        st.markdown(
            '<div style="font-weight:700;font-size:14px;color:#ef4444;margin-bottom:8px;">'
            'Negative Reinforcers</div>',
            unsafe_allow_html=True
        )
        with st.form(f"reinf_form_neg_{student}"):
            nr_responses = {}
            nr_categories = list(dict.fromkeys(c for _, _, c in _NEG_REINFORCERS))
            for cat in nr_categories:
                st.markdown(
                    f'<div style="font-size:11px;font-weight:700;color:#ef4444;'
                    f'text-transform:uppercase;letter-spacing:.05em;margin-top:12px;">'
                    f'{cat}</div>',
                    unsafe_allow_html=True
                )
                for key, label, c in _NEG_REINFORCERS:
                    if c != cat:
                        continue
                    saved_val = saved_reinf.get(key, _REINF_RATING[0])
                    cur_val = saved_val if saved_val in _REINF_RATING else _REINF_RATING[0]
                    st.markdown(
                        f'<div style="font-size:12px;font-weight:600;color:#111;margin-top:6px;">'
                        f'{label}</div>', unsafe_allow_html=True
                    )
                    nr_responses[key] = st.select_slider(
                        label, options=_REINF_RATING, value=cur_val,
                        label_visibility="collapsed", key=f"reinf_nr_{student}_{key}"
                    )
            nr_notes = st.text_area(
                "Notes", value=saved_reinf.get("nr_notes", ""),
                key=f"reinf_nr_notes_{student}", height=60
            )
            nr_submitted = st.form_submit_button("💾  Save", type="primary", use_container_width=True)
        if nr_submitted:
            updated = {**saved_reinf, **nr_responses, "nr_notes": nr_notes}
            ia_data["reinforcers"] = updated
            ia_all[student] = ia_data
            save_indirect(ia_all)
            audit_log("INDIRECT_SAVE", f"Negative reinforcers saved for '{student}'")
            st.toast("Negative reinforcers saved.", icon="✅")
            saved_reinf = ia_data.get("reinforcers", {})
        nr_scores = {label: _likert_score(saved_reinf.get(key, ""), 4)
                     for key, label, _ in _NEG_REINFORCERS}
        top_nr = {k: v for k, v in nr_scores.items() if v > 0}
        if top_nr:
            top_sorted = dict(sorted(top_nr.items(), key=lambda x: x[1], reverse=True))
            fig_nr = _go.Figure(_go.Bar(
                x=list(top_sorted.values()), y=list(top_sorted.keys()),
                orientation="h", marker_color="#ef4444",
                text=list(top_sorted.values()), textposition="outside",
            ))
            fig_nr.update_layout(
                title="Escape / Avoidance Profile",
                plot_bgcolor="white", paper_bgcolor="white", font_family="system-ui",
                height=max(200, len(top_sorted) * 30 + 60),
                margin=dict(l=0, r=40, t=40, b=0),
                xaxis=dict(tickformat="d", range=[0, 5]),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_nr, use_container_width=True, config=_PLOTLY_CONFIG)


# ── Category Settings Page ────────────────────────────────────────────────────
def page_settings():
    st.markdown(
        '<div style="margin-bottom:4px;">'
        '<div style="font-size:22px;font-weight:800;color:#111;letter-spacing:.03em;">'
        'CATEGORY SETTINGS</div>'
        '<div style="font-size:13px;color:#6b7280;margin-top:2px;">'
        'Customize dropdown options used throughout the app</div>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    cats = load_categories()
    tab_abc, tab_setting, tab_mo, tab_users, tab_audit = st.tabs(
        ["A – B – C", "Setting Fields", "⚡ Motivating Operations", "👤 Users", "🔒 Audit Log"]
    )

    def category_editor(label, key, cats):
        items = cats[key]
        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:14px;padding:20px;">'
            '<div style="font-size:17px;font-weight:700;color:#111;margin-bottom:8px;">' + label + '</div>'
            '<div style="font-size:12px;color:#9ca3af;background:#f9fafb;border-radius:8px;'
            'padding:10px;margin-bottom:12px;">Using built-in defaults. Add a custom option or '
            'delete one to customize this list.</div>',
            unsafe_allow_html=True
        )

        # Scrollable list of items
        for i, item in enumerate(items):
            c1, c2 = st.columns([10, 1])
            with c1:
                st.markdown(
                    '<div style="padding:10px 14px;background:#f9fafb;border:1px solid #e5e7eb;'
                    'border-radius:8px;font-size:13px;color:#111;margin-bottom:4px;">'
                    + item + '</div>',
                    unsafe_allow_html=True
                )
            with c2:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                if st.button("✕", key=f"del_{key}_{i}", help="Remove"):
                    items.pop(i)
                    cats[key] = items
                    save_categories(cats)
                    st.rerun()

        # Add new
        st.markdown("</div>", unsafe_allow_html=True)
        a1, a2 = st.columns([5, 1])
        with a1:
            new_val = st.text_input("New option", placeholder=f"Add new {label.lower()} option...",
                                    label_visibility="collapsed", key=f"new_{key}")
        with a2:
            if st.button("＋ Add", key=f"add_{key}", type="primary", use_container_width=True):
                v = new_val.strip()
                if v and v not in items:
                    items.append(v)
                    cats[key] = items
                    save_categories(cats)
                    st.rerun()
                elif v in items:
                    st.warning("Already exists.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_abc:
        c1, c2 = st.columns(2)
        with c1:
            category_editor("Behaviors", "behaviors", cats)
        with c2:
            category_editor("Antecedents", "antecedents", cats)

        # ── Behavior Abbreviations ────────────────────────────────────────────
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="background:white;border:1.5px solid #e5e7eb;border-radius:14px;padding:20px;">'
            '<div style="font-size:17px;font-weight:700;color:#111;margin-bottom:4px;">Behavior Abbreviations</div>'
            '<div style="font-size:12px;color:#9ca3af;margin-bottom:14px;">'
            'Short labels shown in the Log table. Hover over badge to see full name.</div>',
            unsafe_allow_html=True
        )
        abbrevs = cats.get("behavior_abbrevs", {})
        behaviors = cats.get("behaviors", [])
        for beh in behaviors:
            ab1, ab2, ab3 = st.columns([4, 3, 1])
            with ab1:
                st.markdown(
                    f'<div style="padding:8px 12px;background:#f9fafb;border:1px solid #e5e7eb;'
                    f'border-radius:8px;font-size:13px;color:#111;">{beh}</div>',
                    unsafe_allow_html=True
                )
            with ab2:
                new_abbr = st.text_input(
                    "Abbr", value=abbrevs.get(beh, ""),
                    placeholder="e.g. OT, AGG",
                    label_visibility="collapsed",
                    key=f"abbr_{beh}"
                )
            with ab3:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                if st.button("✓", key=f"save_abbr_{beh}", help="Save"):
                    abbrevs[beh] = new_abbr.strip() if new_abbr.strip() else beh
                    cats["behavior_abbrevs"] = abbrevs
                    save_categories(cats)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        c1, _ = st.columns(2)
        with c1:
            category_editor("Consequences", "consequences", cats)

        # ── Operational Behavioral Definitions ───────────────────────────────
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:17px;font-weight:700;color:#111;margin-bottom:4px;">'
            'Operational Behavioral Definitions</div>'
            '<div style="font-size:13px;color:#6b7280;margin-bottom:16px;">'
            'Write a clear, observable, and measurable definition for each behavior. '
            'Definitions appear in the New ABC Entry form as a reference when recording data.</div>',
            unsafe_allow_html=True
        )
        defs = cats.get("behavior_definitions", {})
        def_checks = cats.get("behavior_def_checks", {})
        behaviors = cats.get("behaviors", [])
        if not behaviors:
            st.info("No behaviors defined yet. Add behaviors above first.")

        _CHECKLIST = [
            ("topography",  "Describes observable, physical actions (topography) — what the body does"),
            ("onset_offset","Includes when the behavior starts and stops (onset / offset)"),
            ("threshold",   "Specifies an intensity or duration threshold if needed"),
            ("exclusion",   "Includes at least one exclusion — what does NOT count"),
            ("ioa",         "Tested with a second observer (IOA ≥ 80%)"),
        ]

        for beh in behaviors:
            saved_def   = defs.get(beh, "")
            saved_chks  = def_checks.get(beh, {})
            all_checked = all(saved_chks.get(k, False) for k, _ in _CHECKLIST)
            label = f"📋 {beh}  ✓" if (saved_def and all_checked) else f"📋 {beh}"
            with st.expander(label, expanded=bool(saved_def) and not all_checked):
                st.markdown(
                    '<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">'
                    'Write the definition below, then use the checklist to confirm it meets '
                    'quality criteria before saving.</div>',
                    unsafe_allow_html=True
                )
                new_def = st.text_area(
                    "Definition",
                    value=saved_def,
                    height=110,
                    placeholder=(
                        f"'{beh}' is defined as any instance of… "
                        f"The behavior begins when… and ends when… "
                        f"Does not include…"
                    ),
                    label_visibility="collapsed",
                    key=f"def_{beh}"
                )

                st.markdown(
                    '<div style="font-size:12px;font-weight:600;color:#374151;'
                    'margin:10px 0 4px 0;">Quality Checklist</div>',
                    unsafe_allow_html=True
                )
                new_chks = {}
                for ck_key, ck_label in _CHECKLIST:
                    new_chks[ck_key] = st.checkbox(
                        ck_label,
                        value=saved_chks.get(ck_key, False),
                        key=f"chk_{beh}_{ck_key}"
                    )

                all_now = all(new_chks.values())
                ready   = bool(new_def.strip()) and all_now

                if not all_now and new_def.strip():
                    remaining = sum(1 for k, _ in _CHECKLIST if not new_chks.get(k))
                    st.markdown(
                        f'<div style="font-size:11px;color:#d97706;margin-top:4px;">'
                        f'{remaining} checklist item{"s" if remaining != 1 else ""} remaining</div>',
                        unsafe_allow_html=True
                    )

                dc1, dc2 = st.columns([1, 4])
                with dc1:
                    if st.button(
                        "💾 Save",
                        key=f"save_def_{beh}",
                        type="primary",
                        use_container_width=True,
                        disabled=not bool(new_def.strip()),
                    ):
                        defs[beh] = new_def.strip()
                        cats["behavior_definitions"] = defs
                        def_checks[beh] = new_chks
                        cats["behavior_def_checks"] = def_checks
                        save_categories(cats)
                        st.success("Definition saved." if not all_now else "✓ Definition complete and verified.")
                        st.rerun()
                with dc2:
                    if saved_def and all_checked:
                        st.markdown(
                            '<div style="font-size:12px;color:#16a34a;padding-top:8px;">'
                            '✓ Definition complete and verified</div>',
                            unsafe_allow_html=True
                        )
                    elif saved_def:
                        st.markdown(
                            '<div style="font-size:12px;color:#d97706;padding-top:8px;">'
                            '⚠ Definition saved — checklist incomplete</div>',
                            unsafe_allow_html=True
                        )

    with tab_setting:
        c1, c2 = st.columns(2)
        with c1:
            category_editor("Locations", "locations", cats)
        with c2:
            category_editor("People Intervening", "people_intervening", cats)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            category_editor("Subjects", "subjects", cats)
        with c2:
            category_editor("Activities", "activities", cats)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        c1, _ = st.columns(2)
        with c1:
            category_editor("Instructional Formats", "instructional_formats", cats)

    # ── Motivating Operations tab ─────────────────────────────────────────────
    with tab_mo:
        st.markdown(
            '<div style="font-size:13px;color:#6b7280;margin-bottom:16px;">'
            'The default MO list covers biological, social, environmental, and task conditions. '
            'Add custom MOs below for conditions specific to your students or setting. '
            'All items appear as checkboxes in the New ABC Entry form.</div>',
            unsafe_allow_html=True
        )

        # ── Default MO list (read-only display) ──────────────────────────────
        st.markdown(
            '<div style="font-size:15px;font-weight:700;color:#111;margin-bottom:10px;">'
            'Default Motivating Operations</div>',
            unsafe_allow_html=True
        )
        tier_colors = {1: ("#dcfce7", "#15803d", "Auto-detected"),
                       2: ("#eff6ff", "#1d4ed8", "Observer checkbox"),
                       3: ("#fef9c3", "#854d0e", "External / contextual")}
        for domain, items in MO_DEFAULTS.items():
            with st.expander(domain, expanded=False):
                for mo in items:
                    bg, fg, tier_label = tier_colors[mo["tier"]]
                    st.markdown(
                        f'<div style="display:flex;align-items:flex-start;gap:10px;'
                        f'padding:8px 10px;border:1px solid #e5e7eb;border-radius:8px;'
                        f'background:white;margin-bottom:6px;">'
                        f'<span style="background:{bg};color:{fg};font-size:10px;font-weight:700;'
                        f'padding:2px 7px;border-radius:10px;white-space:nowrap;margin-top:2px;">'
                        f'Tier {mo["tier"]}</span>'
                        f'<span style="font-size:13px;color:#374151;">{mo["label"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # ── Custom MOs ────────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:15px;font-weight:700;color:#111;margin:20px 0 6px 0;">'
            'Custom Motivating Operations</div>'
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'Add conditions specific to your students or setting.</div>',
            unsafe_allow_html=True
        )
        custom_mos = cats.get("custom_mos", [])
        if custom_mos:
            for i, cmo in enumerate(custom_mos):
                cm1, cm2 = st.columns([5, 1])
                with cm1:
                    st.markdown(
                        f'<div style="padding:9px 12px;background:white;border:1px solid #e5e7eb;'
                        f'border-radius:8px;font-size:13px;color:#374151;">{cmo}</div>',
                        unsafe_allow_html=True
                    )
                with cm2:
                    if st.button("✕", key=f"del_cmo_{i}", use_container_width=True):
                        custom_mos.pop(i)
                        cats["custom_mos"] = custom_mos
                        save_categories(cats)
                        st.rerun()
        else:
            st.markdown(
                '<div style="font-size:12px;color:#9ca3af;padding:10px;">No custom MOs added yet.</div>',
                unsafe_allow_html=True
            )
        cmo_c1, cmo_c2 = st.columns([5, 1])
        with cmo_c1:
            new_cmo = st.text_input(
                "New custom MO", placeholder="Describe the observable condition...",
                label_visibility="collapsed", key="new_cmo_input"
            )
        with cmo_c2:
            if st.button("＋ Add", key="add_cmo_btn", type="primary", use_container_width=True):
                v = new_cmo.strip()
                if v and v not in custom_mos:
                    custom_mos.append(v)
                    cats["custom_mos"] = custom_mos
                    save_categories(cats)
                    st.rerun()
                elif v in custom_mos:
                    st.warning("Already exists.")

    # ── Users tab (admin only) ────────────────────────────────────────────────
    with tab_users:
        if st.session_state.get("user_role") != "admin":
            st.warning("Admin access required to manage users.")
        else:
            st.markdown("**User Accounts**")
            users = load_users()
            for uname, udata in users.items():
                uc1, uc2, uc3 = st.columns([3, 2, 1])
                with uc1:
                    st.markdown(
                        f'<div style="padding:8px 12px;background:#f9fafb;border:1px solid #e5e7eb;'
                        f'border-radius:8px;font-size:13px;">'
                        f'<b>{uname}</b> — {udata.get("name","")} '
                        f'<span style="color:#6b7280;">({udata.get("role","observer")})</span></div>',
                        unsafe_allow_html=True
                    )
                with uc2:
                    st.markdown(
                        '<div style="font-size:11px;color:#6b7280;padding-top:10px;">●●●●●●●● (hashed)</div>',
                        unsafe_allow_html=True
                    )
                with uc3:
                    if uname != "admin" and st.button("✕", key=f"del_user_{uname}"):
                        del users[uname]
                        _safe_save(USERS_FILE, users)
                        audit_log("DELETE_USER", f"User {uname} deleted")
                        st.rerun()

            st.markdown("---")
            st.markdown("**Add User**")
            nu1, nu2, nu3, nu4 = st.columns([2, 2, 2, 1])
            with nu1:
                new_uname = st.text_input("Username", key="new_uname", label_visibility="collapsed",
                                          placeholder="Username")
            with nu2:
                new_uname_display = st.text_input("Full name", key="new_uname_display",
                                                  label_visibility="collapsed", placeholder="Full name")
            with nu3:
                new_pw = st.text_input("Password", type="password", key="new_upw",
                                       label_visibility="collapsed", placeholder="Password")
            with nu4:
                if st.button("Add", key="add_user_btn", type="primary", use_container_width=True):
                    if new_uname.strip() and new_pw.strip():
                        if len(new_pw) < 8:
                            st.error("Password must be at least 8 characters.")
                        elif new_uname.lower() in users:
                            st.error("Username already exists.")
                        else:
                            users[new_uname.lower()] = {
                                "password_hash": _hash_password(new_pw),
                                "name": new_uname_display.strip() or new_uname,
                                "role": "observer",
                            }
                            _safe_save(USERS_FILE, users)
                            audit_log("CREATE_USER", f"User {new_uname} created")
                            st.success(f"User '{new_uname}' added.")
                            st.rerun()

    # ── Audit Log tab ─────────────────────────────────────────────────────────
    with tab_audit:
        st.markdown("**Access & Activity Log**")
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:12px;">'
            'All user actions are automatically recorded for HIPAA compliance.</div>',
            unsafe_allow_html=True
        )
        if os.path.exists(AUDIT_FILE):
            with open(AUDIT_FILE) as f:
                logs = json.load(f)
            if logs:
                log_df = pd.DataFrame(reversed(logs))
                log_df["timestamp"] = pd.to_datetime(log_df["timestamp"]).dt.strftime("%m/%d/%Y %H:%M:%S")
                st.dataframe(log_df, hide_index=True, use_container_width=True)
                csv = log_df.to_csv(index=False).encode()
                st.download_button("Export Audit Log (CSV)", csv, "audit_log.csv",
                                   "text/csv", key="dl_audit")
            else:
                st.info("No audit events recorded yet.")
        else:
            st.info("No audit log found.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="FBA Data Tracker", page_icon="📋",
                       layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Data safety: surface any corrupt/recovered file from this session ──────
    for _p, _msg in _LOAD_ERRORS.items():
        _name = os.path.basename(_p)
        if _p in _QUARANTINED:
            st.error(f"⚠️ **{_name}** {_msg}")
        else:
            st.warning(f"♻️ **{_name}** {_msg}")

    for key, default in [("logged_in", False), ("selected_student", None),
                          ("observer_name", ""), ("confirm_del", False),
                          ("last_active", None), ("user_role", "observer"),
                          ("show_edit_student", False), ("confirm_clear", False),
                          ("show_edit_selector", False), ("show_remove_selector", False),
                          ("show_archive_selector", False), ("confirm_archive", False),
                          ("show_register", False)]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ── HIPAA: check session timeout before anything else ─────────────────────
    if DEV_MODE:
        st.session_state.logged_in = True
        st.session_state.observer_name = st.session_state.get("observer_name") or "Dev User"
        st.session_state.user_role = "admin"
        st.session_state.login_email = "dev"
    else:
        check_session_timeout()
        if st.session_state.logged_in:
            touch_session()

    if not st.session_state.logged_in:
        page_login()
        return

    if st.session_state.get("show_settings"):
        with st.form("settings_back_form", border=False):
            submitted = st.form_submit_button("← Back to Student")
        if submitted:
            st.session_state["show_settings"] = False
            st.rerun()
        page_settings()
        return

    if not st.session_state.selected_student:
        page_student_selector()
        return

    student     = st.session_state.selected_student
    observer    = st.session_state.observer_name
    all_entries = load_json(DATA_FILE)
    student_entries = [e for e in all_entries if e.get("student_name") == student]

    # ── Top bar ───────────────────────────────────────────────────────────────
    initial = student[0].upper()
    _prof = load_profiles().get(student, {})
    _prof_chips = ""
    for _val in [_prof.get("grade"), _prof.get("disability_category") or _prof.get("eligibility"),
                 _prof.get("teacher") and f"Teacher: {_prof['teacher']}",
                 _prof.get("school")]:
        if _val:
            _prof_chips += (f'<span style="background:#f0fdf4;color:#15803d;border-radius:20px;'
                            f'padding:2px 9px;font-size:11px;font-weight:600;margin-right:4px;">{_val}</span>')
    st.markdown(
        f'<div style="background:white;border-bottom:1.5px solid #e5e7eb;'
        f'padding:10px 20px;margin:0 -1rem 20px -1rem;'
        f'display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
        f'<div style="display:flex;align-items:center;gap:8px;background:#f0fdf4;'
        f'border:1.5px solid #bbf7d0;border-radius:20px;padding:5px 12px 5px 8px;">'
        f'<div style="width:24px;height:24px;background:#dcfce7;border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;'
        f'color:#16a34a;font-weight:700;font-size:11px;">{initial}</div>'
        f'<span style="font-weight:700;color:#15803d;font-size:14px;">{student}</span>'
        f'</div>'
        f'{_prof_chips}'
        f'<span style="color:#6b7280;font-size:13px;">Collector: <b style="color:#111;">{observer}</b></span>'
        f'<span style="margin-left:auto;font-size:11px;color:#9ca3af;">🔒 Session: {SESSION_TIMEOUT_MIN} min</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Top action buttons ────────────────────────────────────────────────────
    bc1, bc2, bc3, bc4, bc5, _ = st.columns([1, 1.4, 1.4, 1.4, 1, 1])
    with bc1:
        if st.button("Return to Student Page", use_container_width=True):
            st.session_state.selected_student = None
            st.rerun()
    with bc2:
        if st.button("✏️ Edit Student", use_container_width=True,
                     help="Edit this student's information"):
            st.session_state.show_edit_student = not st.session_state.get("show_edit_student", False)
            st.session_state.confirm_clear = False
            st.session_state.confirm_archive = False
            st.rerun()
    with bc3:
        if st.button("🗄 Archive", use_container_width=True,
                     help="Archive this student (preserves all data)"):
            st.session_state.confirm_archive = not st.session_state.get("confirm_archive", False)
            st.session_state.show_edit_student = False
            st.session_state.confirm_clear = False
            st.rerun()
    with bc4:
        if st.button("🗑 Remove All Entries", use_container_width=True,
                     help="Delete all entries for this student"):
            st.session_state.confirm_clear = True
            st.session_state.show_edit_student = False
            st.session_state.confirm_archive = False
            st.rerun()
    with bc5:
        if st.button("⚙", use_container_width=True, help="Category settings"):
            st.session_state["show_settings"] = True
            st.rerun()

    # ── Archive confirmation ──────────────────────────────────────────────────
    if st.session_state.get("confirm_archive"):
        st.warning(
            f"**Archive {student}?**  \n"
            f"This will remove **{student}** from the active student list. "
            f"All {len(student_entries)} entries and profile information will be preserved "
            f"and can be restored any time from the student selector page."
        )
        ca1, ca2 = st.columns(2)
        with ca1:
            if st.button("Yes, Archive Student", type="primary", use_container_width=True,
                         key="do_archive_student"):
                active = load_json(STUDENTS_FILE)
                active = [s for s in active if s != student]
                save_json(STUDENTS_FILE, active)
                archive_list = load_archive()
                archive_list.append({
                    "name": student,
                    "archived_date": datetime.now().strftime("%Y-%m-%d"),
                    "entry_count": len(student_entries),
                })
                save_archive(archive_list)
                audit_log("ARCHIVE_STUDENT", f"Archived student '{student}' ({len(student_entries)} entries preserved)")
                st.session_state.confirm_archive = False
                st.session_state.selected_student = None
                st.rerun()
        with ca2:
            if st.button("Cancel", use_container_width=True, key="cancel_archive_student"):
                st.session_state.confirm_archive = False
                st.rerun()

    # ── Profile completeness nudge ────────────────────────────────────────────
    _nudge_prof = load_profiles().get(student, {})
    _required_fields = ["grade", "disability_category", "teacher", "school"]
    _missing = [f for f in _required_fields if not _nudge_prof.get(f)]
    if _missing and not st.session_state.get("show_edit_student"):
        st.markdown(
            '<div style="background:#fffbeb;border:1.5px solid #fde68a;border-radius:10px;'
            'padding:10px 16px;margin-bottom:12px;display:flex;align-items:center;gap:10px;">'
            '<span style="font-size:18px;">📝</span>'
            '<span style="font-size:13px;color:#92400e;">Student profile is incomplete. '
            'Click <b>✏️ Edit Student</b> to add grade, disability category, teacher, and school.</span>'
            '</div>',
            unsafe_allow_html=True
        )

    # ── Edit student information ──────────────────────────────────────────────
    if st.session_state.get("show_edit_student"):
        profiles = load_profiles()
        prof = profiles.get(student, {})

        st.markdown(
            '<div style="background:#f0f9ff;border:1.5px solid #bae6fd;'
            'border-radius:12px;padding:20px 22px;margin:10px 0;">',
            unsafe_allow_html=True
        )
        st.markdown("### Edit Student Information")

        # Row 1 — Name + DOB
        r1a, r1b = st.columns(2)
        with r1a:
            new_student_name = st.text_input("Full Name", value=student, key="edit_stu_name")
        with r1b:
            new_dob = st.text_input("Date of Birth (MM/DD/YYYY)",
                                    value=prof.get("dob", ""), key="edit_stu_dob",
                                    placeholder="MM/DD/YYYY")

        # Row 2 — Grade + Gender
        r2a, r2b = st.columns(2)
        with r2a:
            grade_options = ["", "Pre-K", "Kindergarten", "1st", "2nd", "3rd",
                             "4th", "5th", "6th", "7th", "8th", "9th", "10th",
                             "11th", "12th", "Post-Secondary"]
            cur_grade = prof.get("grade", "")
            grade_idx = grade_options.index(cur_grade) if cur_grade in grade_options else 0
            new_grade = st.selectbox("Grade", grade_options, index=grade_idx, key="edit_stu_grade")
        with r2b:
            gender_options = ["", "Male", "Female", "Non-binary", "Other", "Prefer not to say"]
            cur_gender = prof.get("gender", "")
            gender_idx = gender_options.index(cur_gender) if cur_gender in gender_options else 0
            new_gender = st.selectbox("Gender", gender_options, index=gender_idx, key="edit_stu_gender")

        # Row 3 — Disability category + Eligibility
        r3a, r3b = st.columns(2)
        with r3a:
            disability_options = [
                "", "Autism Spectrum Disorder", "Emotional Disturbance",
                "Intellectual Disability", "Other Health Impairment",
                "Specific Learning Disability", "Speech/Language Impairment",
                "Traumatic Brain Injury", "Multiple Disabilities",
                "Developmental Delay", "Other"
            ]
            cur_dis = prof.get("disability_category", "")
            dis_idx = disability_options.index(cur_dis) if cur_dis in disability_options else 0
            new_disability = st.selectbox("Disability Category (IDEA)", disability_options,
                                          index=dis_idx, key="edit_stu_disability")
        with r3b:
            new_eligibility = st.text_input("IEP / 504 Eligibility",
                                            value=prof.get("eligibility", ""),
                                            key="edit_stu_eligibility",
                                            placeholder="e.g., IEP – Autism")

        # Row 4 — Teacher + Case manager
        r4a, r4b = st.columns(2)
        with r4a:
            new_teacher = st.text_input("Primary Teacher",
                                        value=prof.get("teacher", ""),
                                        key="edit_stu_teacher")
        with r4b:
            new_case_mgr = st.text_input("Case Manager / BCBA",
                                         value=prof.get("case_manager", ""),
                                         key="edit_stu_case_mgr")

        # Row 5 — School + Classroom
        r5a, r5b = st.columns(2)
        with r5a:
            new_school = st.text_input("School District", value=prof.get("school", ""),
                                       key="edit_stu_school")
        with r5b:
            new_classroom = st.text_input("Classroom / Program",
                                          value=prof.get("classroom", ""),
                                          key="edit_stu_classroom")

        # Row 6 — Notes
        new_notes = st.text_area("Background / Clinical Notes",
                                 value=prof.get("notes", ""),
                                 key="edit_stu_notes", height=90,
                                 placeholder="Relevant history, reinforcers, sensory needs, medical info, etc.")

        # Save / Cancel
        sv1, sv2 = st.columns([1, 1])
        with sv1:
            if st.button("💾 Save Changes", type="primary", use_container_width=True,
                         key="save_edit_student"):
                new_name_clean = new_student_name.strip()
                if not new_name_clean:
                    st.warning("Student name cannot be blank.")
                else:
                    stu_list = load_json(STUDENTS_FILE)
                    if new_name_clean != student and new_name_clean in stu_list:
                        st.warning(f"A student named '{new_name_clean}' already exists.")
                    else:
                        # Rename in students list and all entries if name changed
                        if new_name_clean != student:
                            stu_list = [new_name_clean if s == student else s for s in stu_list]
                            save_json(STUDENTS_FILE, stu_list)
                            updated_entries = []
                            for e in all_entries:
                                if e.get("student_name") == student:
                                    e = dict(e)
                                    e["student_name"] = new_name_clean
                                updated_entries.append(e)
                            save_json(DATA_FILE, updated_entries)
                            # Move profile to new key
                            if student in profiles:
                                profiles[new_name_clean] = profiles.pop(student)

                        # Save profile fields
                        profiles[new_name_clean] = {
                            "dob": new_dob.strip(),
                            "grade": new_grade,
                            "gender": new_gender,
                            "disability_category": new_disability,
                            "eligibility": new_eligibility.strip(),
                            "teacher": new_teacher.strip(),
                            "case_manager": new_case_mgr.strip(),
                            "school": new_school.strip(),
                            "classroom": new_classroom.strip(),
                            "notes": new_notes.strip(),
                        }
                        save_profiles(profiles)
                        audit_log("EDIT_STUDENT_INFO", f"Updated profile for '{new_name_clean}'"
                                  + (f" (renamed from '{student}')" if new_name_clean != student else ""))
                        st.session_state.selected_student = new_name_clean
                        st.session_state.show_edit_student = False
                        st.rerun()
        with sv2:
            if st.button("Cancel", use_container_width=True, key="cancel_edit_student"):
                st.session_state.show_edit_student = False
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("confirm_clear"):
        st.warning(
            f"**Remove all entries for {student}?**  \n"
            f"This will permanently delete all {len(student_entries)} record(s) for this student. This cannot be undone."
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("Yes, remove all entries", type="primary", use_container_width=True):
                save_json(DATA_FILE,
                          [e for e in all_entries
                           if e.get("student_name") != student])
                audit_log("DELETE_ALL_ENTRIES", f"Removed all {len(student_entries)} entries for student: {student}")
                st.session_state.confirm_clear = False
                st.success(f"All entries for {student} have been removed.")
                st.rerun()
        with cc2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_clear = False
                st.rerun()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "🗂  Indirect Assessment",
        "🎯  Reinforcers",
        "📋  New ABC Entry",
        "⏱  New Interval Recording Entry",
        f"⊞  Log ({len(student_entries)})",
        "📊  Basic Summary Data",
        "🧮  Computational Models",
    ])
    with t1:
        tab_indirect_assessment(student)
    with t2:
        tab_reinforcers(student)
    with t3:
        tab_new_entry(all_entries, student, observer)
    with t4:
        tab_interval(all_entries, student, observer)
    with t5:
        _abbrevs = load_categories().get("behavior_abbrevs", {})
        tab_log(student_entries, all_entries, student, abbrevs=_abbrevs)
    with t6:
        tab_summary(student_entries)
    with t7:
        tab_computational_models(student_entries, student)


if __name__ == "__main__":
    main()
