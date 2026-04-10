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
CATEGORIES_FILE= os.path.join(DATA_DIR, "categories.json")
USERS_FILE     = os.path.join(DATA_DIR, "users.json")
AUDIT_FILE     = os.path.join(DATA_DIR, "audit_log.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ── HIPAA: Session timeout (minutes) ─────────────────────────────────────────
SESSION_TIMEOUT_MIN = 20

# ── HIPAA: Password hashing ───────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    """SHA-256 with a fixed app-level salt. Replace with bcrypt in production."""
    salt = "fba_hipaa_salt_2026"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    # Default admin account — password 'Admin123!' (hash stored, never plain text)
    default = {
        "admin": {
            "password_hash": _hash_password("Admin123!"),
            "name": "Administrator",
            "role": "admin",
        }
    }
    with open(USERS_FILE, "w") as f:
        json.dump(default, f, indent=2)
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
    logs = []
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE) as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append(entry)
    with open(AUDIT_FILE, "w") as f:
        json.dump(logs, f, indent=2, default=str)

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

# ── Category loader (custom overrides defaults) ───────────────────────────────
def load_categories():
    if os.path.exists(CATEGORIES_FILE):
        saved = json.load(open(CATEGORIES_FILE))
    else:
        saved = {}
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
    }

def save_categories(cats):
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(cats, f, indent=2)

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
    max-width: 900px !important;
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
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

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

    # ── Student cards ─────────────────────────────────────────────────────────
    # CSS: target the button that immediately follows a .student-card-marker div
    # using the adjacent sibling combinator + :has(). Both are siblings in
    # Streamlit's stVerticalBlock, so this reliably matches only student buttons.
    st.markdown("""
    <style>
    .stMarkdown:has(.student-card-marker) + [data-testid="stButton"] > button {
        background: white !important;
        border: 1.5px solid #e5e7eb !important;
        border-radius: 12px !important;
        height: 60px !important;
        text-align: left !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #111827 !important;
        justify-content: flex-start !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        padding: 0 18px !important;
    }
    .stMarkdown:has(.student-card-marker) + [data-testid="stButton"] > button:hover {
        background: #f0fdf4 !important;
        border-color: #16a34a !important;
        color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    for i, name in enumerate(students):
        initial = name[0].upper()
        av_col, btn_col = st.columns([1, 9])
        with av_col:
            st.markdown(
                f'<div style="height:60px;display:flex;align-items:center;justify-content:center;">'
                f'<div style="width:40px;height:40px;background:#dcfce7;border-radius:50%;'
                f'display:flex;align-items:center;justify-content:center;'
                f'color:#16a34a;font-weight:700;font-size:15px;">{initial}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with btn_col:
            # marker div → button are adjacent siblings → CSS :has() targets the button
            st.markdown('<div class="student-card-marker"></div>', unsafe_allow_html=True)
            if st.button(f"{name}   →", key=f"sel_{i}", use_container_width=True):
                st.session_state.selected_student = name
                st.rerun()

    # ── Add new student (dashed card style) ───────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if not st.session_state.get("show_add_student"):
        if st.button("＋  Add new student", use_container_width=True,
                     key="show_add_btn"):
            st.session_state.show_add_student = True
            st.rerun()
    else:
        st.markdown(
            '<div style="border:2px dashed #d1d5db;border-radius:16px;padding:20px 24px;">',
            unsafe_allow_html=True
        )
        c1, c2 = st.columns([5, 1])
        with c1:
            new_name = st.text_input("Student name", placeholder="Full name",
                                     label_visibility="collapsed", key="new_student")
        with c2:
            if st.button("Add", type="primary", use_container_width=True):
                n = new_name.strip()
                if n and n not in students:
                    students.append(n)
                    save_json(STUDENTS_FILE, students)
                    st.session_state.show_add_student = False
                    st.rerun()
                elif n in students:
                    st.warning("Already exists.")
        if st.button("Cancel", key="cancel_add", use_container_width=True):
            st.session_state.show_add_student = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Remove a student ──────────────────────────────────────────────────────
    if students:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        with st.expander("Remove a student"):
            to_del = st.selectbox("Student", students, key="del_sel")
            entry_count = len([e for e in load_json(DATA_FILE)
                               if e.get("student_name") == to_del])

            if not st.session_state.get("confirm_del"):
                st.markdown(
                    '<div style="background:#fff7ed;border:1.5px solid #fed7aa;'
                    'border-radius:10px;padding:14px 16px;margin:10px 0;">'
                    '<div style="font-weight:700;color:#c2410c;font-size:13px;margin-bottom:4px;">'
                    '⚠️ This action cannot be undone</div>'
                    '<div style="font-size:13px;color:#7c2d12;">Removing <b>'
                    + to_del + '</b> will permanently delete the student and all <b>'
                    + str(entry_count) + ' ABC entr'
                    + ('ies' if entry_count != 1 else 'y') + '</b>.</div>'
                    '</div>',
                    unsafe_allow_html=True
                )
                if st.button("Delete student + all data", type="secondary"):
                    st.session_state.confirm_del = True
                    st.rerun()
            else:
                st.markdown(
                    '<div style="background:#fef2f2;border:2px solid #fca5a5;'
                    'border-radius:10px;padding:16px;margin:10px 0;">'
                    '<div style="font-weight:700;color:#dc2626;font-size:14px;margin-bottom:6px;">'
                    '🚨 Final confirmation</div>'
                    '<div style="font-size:13px;color:#7f1d1d;">Permanently delete <b>'
                    + to_del + '</b> and all <b>' + str(entry_count) + ' entr'
                    + ('ies' if entry_count != 1 else 'y') + '</b>? This cannot be recovered.</div>'
                    '</div>',
                    unsafe_allow_html=True
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, permanently delete", type="primary",
                                 use_container_width=True):
                        students = [s for s in students if s != to_del]
                        save_json(STUDENTS_FILE, students)
                        entries = load_json(DATA_FILE)
                        save_json(DATA_FILE,
                                  [e for e in entries if e.get("student_name") != to_del])
                        st.session_state.confirm_del = False
                        st.rerun()
                with c2:
                    if st.button("Cancel", use_container_width=True, key="cancel_del"):
                        st.session_state.confirm_del = False
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
        consequence = st.selectbox("Consequence (C) *", [""] + cats["consequences"],
                                   format_func=lambda x: "Select consequence" if x == "" else x)

        # ABC Chain linking
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        chain_col1, chain_col2 = st.columns([1, 3])
        with chain_col1:
            is_chain = st.checkbox("Part of behavior chain", key="chain_cb")
        with chain_col2:
            chain_label = st.text_input(
                "Chain label (e.g. 'Morning transition')",
                placeholder="Label to link related entries",
                label_visibility="collapsed",
                key="chain_label_inp",
                disabled=not is_chain
            ) if is_chain else ""

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
        if not behavior:
            st.error("Behavior is required.")
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
            "chain_label": chain_label.strip() if is_chain and chain_label else None,
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
        st.markdown("""
        <div style="text-align:center;padding:48px;color:#9ca3af;font-size:14px;">
            No entries yet.
        </div>""", unsafe_allow_html=True)
        return

    filtered_entries = _apply_filters(filtered_entries,
                                      "log_beh_f", "log_obs_f",
                                      "log_date_from", "log_date_to")

    df = pd.DataFrame(filtered_entries).sort_values("number", ascending=False)
    csv = df.to_csv(index=False).encode()

    entry_label = "entry" if len(filtered_entries) == 1 else "entries"
    ec1, ec2 = st.columns([8, 2])
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

    # Build HTML table
    rows_html = ""
    for _, row in df.iterrows():
        chain = row.get("chain_label") or ""
        chain_cell = (
            f'<span style="background:#ede9fe;color:#6d28d9;font-size:11px;'
            f'font-weight:600;padding:2px 7px;border-radius:10px;">{chain}</span>'
            if chain else "—"
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
            f'<td>{chain_cell}</td>'
            f'<td style="text-align:center;">{photo_cell}</td>'
            '</tr>'
        )

    header_cells = "".join(
        f'<th style="padding:10px 12px;text-align:left;font-size:11px;'
        f'font-weight:700;letter-spacing:.06em;color:#6b7280;">{h}</th>'
        for h in ["#", "DATE", "TIME", "STUDENT", "OBSERVER", "LOCATION",
                  "ANTECEDENT", "BEHAVIOR", "CONSEQUENCE", "DURATION", "INT",
                  "INTERVAL", "CHAIN", "📷"]
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
    st.markdown("**Delete an entry**")
    nums = sorted([e.get("number") for e in filtered_entries if e.get("number")],
                  reverse=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        del_num = st.selectbox("Entry #", nums, key="del_num",
                               label_visibility="collapsed")
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
                            xaxis=dict(gridcolor="#e5e7eb", automargin=True),
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
                              height=300, yaxis=dict(autorange="reversed", automargin=True))
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
                              height=300, yaxis=dict(autorange="reversed", automargin=True))
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
                              height=260, yaxis=dict(autorange="reversed", automargin=True))
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

    # ── Computational Models ──────────────────────────────────────────────────
    st.markdown(
        '<div style="font-weight:700;font-size:15px;color:#111;margin-top:20px;margin-bottom:10px;">'
        'Computational Models</div>',
        unsafe_allow_html=True
    )

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

                # Bayesian updating over time
                if "date" in df_nb.columns:
                    st.markdown(
                        '<div style="font-size:13px;font-weight:600;color:#111;'
                        'margin-top:16px;margin-bottom:6px;">Bayesian Updating Over Time</div>'
                        '<div style="font-size:12px;color:#6b7280;margin-bottom:8px;">'
                        'How confidence in each function evolves as more data is collected.</div>',
                        unsafe_allow_html=True
                    )
                    df_sorted = df_nb.sort_values("date")
                    alpha = np.ones(4)
                    history = []
                    for _, row in df_sorted.iterrows():
                        v = _entry_func_vector(row)
                        alpha += np.array([v["Att"], v["Tan"], v["Esc"], v["Sel"]])
                        p = alpha / alpha.sum()
                        # 95% credible interval via beta marginals
                        ci_lo = np.array([max(0, p[i] - 1.96*np.sqrt(p[i]*(1-p[i])/alpha.sum()))
                                          for i in range(4)])
                        ci_hi = np.array([min(1, p[i] + 1.96*np.sqrt(p[i]*(1-p[i])/alpha.sum()))
                                          for i in range(4)])
                        history.append({
                            "date": row["date"], "n": int(alpha.sum() - 4),
                            **{f"p_{f}": round(p[i], 4) for i, f in enumerate(FUNC_TAGS.values())},
                            **{f"lo_{f}": round(ci_lo[i], 4) for i, f in enumerate(FUNC_TAGS.values())},
                            **{f"hi_{f}": round(ci_hi[i], 4) for i, f in enumerate(FUNC_TAGS.values())},
                        })
                    hist_df = pd.DataFrame(history)
                    fig_bay = _go.Figure()
                    for func, color in colors_nb.items():
                        fig_bay.add_trace(_go.Scatter(
                            x=hist_df["n"], y=hist_df[f"p_{func}"],
                            name=func, mode="lines", line=dict(color=color, width=2),
                        ))
                        fig_bay.add_trace(_go.Scatter(
                            x=pd.concat([hist_df["n"], hist_df["n"][::-1]]),
                            y=pd.concat([hist_df[f"hi_{func}"], hist_df[f"lo_{func}"][::-1]]),
                            fill="toself", fillcolor=color, opacity=0.15,
                            line=dict(width=0), showlegend=False, hoverinfo="skip",
                        ))
                    fig_bay.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white",
                        font_family="system-ui", height=300,
                        margin=dict(l=0, r=10, t=10, b=0),
                        xaxis=dict(title="Observations (n)", gridcolor="#e5e7eb"),
                        yaxis=dict(title="Posterior probability", tickformat=".0%",
                                   range=[0, 1], gridcolor="#e5e7eb"),
                        legend=dict(orientation="h", y=1.08),
                    )
                    st.plotly_chart(fig_bay, use_container_width=True, config=_PLOTLY_CONFIG)
            else:
                st.info("Not enough tagged antecedent/consequence data. Add entries with (Att), (Esc), (Tan), or (Sel) tags in antecedents or consequences.")
        else:
            st.info("Antecedent and consequence data required.")

    # 2. Hidden Markov Model ───────────────────────────────────────────────────
    with st.expander("Hidden Markov Model — Behavioral State Inference", expanded=False):
        st.caption(
            "Infers hidden behavioral states (Regulated, Escalating, Crisis) from the "
            "observable sequence of behaviors and intensities. Shows the most likely "
            "state at each observation and the transition matrix between states. "
            "A Hidden Markov Model (HMM) is a way to understand behavior when the most important "
            "parts — the internal states driving behavior — can't be directly observed."
        )
        st.markdown("**Core idea**")
        st.markdown(
            "- In behavioral analysis, we often see observable actions (e.g., calling out, task refusal), "
            "but not the underlying state (e.g., frustration, escape motivation, escalation phase).\n"
            "- An HMM helps infer those hidden states from patterns in what we can observe."
        )
        if "behavior" in df.columns and "date" in df.columns:
            try:
                from hmmlearn import hmm as _hmm

                df_hmm = df.copy()
                if "time" in df_hmm.columns:
                    df_hmm["_sk"] = pd.to_datetime(
                        df_hmm["date"].astype(str) + " " + df_hmm["time"].astype(str), errors="coerce"
                    )
                else:
                    df_hmm["_sk"] = pd.to_datetime(df_hmm["date"], errors="coerce")
                df_hmm = df_hmm.sort_values("_sk").dropna(subset=["behavior"])

                # Encode behaviors as integers
                beh_list_hmm = sorted(df_hmm["behavior"].unique())
                beh_enc = {b: i for i, b in enumerate(beh_list_hmm)}
                obs_seq = df_hmm["behavior"].map(beh_enc).values.reshape(-1, 1)

                if len(obs_seq) >= 6:
                    n_states = min(3, len(obs_seq) // 2)
                    STATE_NAMES = ["Regulated", "Escalating", "Crisis"][:n_states]
                    STATE_COLORS = ["#16a34a", "#d97706", "#dc2626"][:n_states]

                    model_hmm = _hmm.CategoricalHMM(
                        n_components=n_states, n_iter=100, random_state=42
                    )
                    model_hmm.fit(obs_seq)
                    state_seq = model_hmm.predict(obs_seq)

                    # Assign state labels by emission entropy (low entropy = regulated)
                    emit_entropy = [-np.sum(p * np.log(p + 1e-9))
                                    for p in model_hmm.emissionprob_]
                    state_order = np.argsort(emit_entropy)
                    label_map = {state_order[i]: STATE_NAMES[i] for i in range(n_states)}
                    color_map = {state_order[i]: STATE_COLORS[i] for i in range(n_states)}
                    state_labels = [label_map[s] for s in state_seq]

                    # State sequence chart
                    fig_hmm = _go.Figure()
                    for state in STATE_NAMES:
                        mask = [s == state for s in state_labels]
                        fig_hmm.add_trace(_go.Scatter(
                            x=df_hmm["_sk"][mask],
                            y=[state] * sum(mask),
                            mode="markers",
                            name=state,
                            marker=dict(
                                color=STATE_COLORS[STATE_NAMES.index(state)],
                                size=12, symbol="circle",
                            ),
                            text=df_hmm["behavior"][mask],
                            hovertemplate="<b>%{text}</b><br>%{x}<extra></extra>",
                        ))
                    fig_hmm.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white",
                        font_family="system-ui", height=260,
                        margin=dict(l=0, r=10, t=10, b=0),
                        xaxis=dict(title="Time", gridcolor="#e5e7eb"),
                        yaxis=dict(title="Inferred State", automargin=True,
                                   categoryorder="array",
                                   categoryarray=list(reversed(STATE_NAMES))),
                        legend=dict(orientation="h", y=1.1),
                    )
                    st.plotly_chart(fig_hmm, use_container_width=True, config=_PLOTLY_CONFIG)

                    # Transition matrix
                    trans_mat = model_hmm.transmat_
                    reordered = [list(STATE_NAMES).index(label_map[i])
                                 for i in range(n_states)]
                    t_reord = trans_mat[np.ix_(state_order, state_order)]
                    t_text = [[f"{v:.2f}" for v in row] for row in t_reord.tolist()]

                    fig_trans = _go.Figure(data=_go.Heatmap(
                        z=t_reord.tolist(), x=STATE_NAMES, y=STATE_NAMES,
                        text=t_text, texttemplate="%{text}",
                        textfont=dict(size=14, color="#111"),
                        colorscale=[[0,"#ffffff"],[0.5,"#fde68a"],[1,"#dc2626"]],
                        showscale=False, zmin=0, zmax=1,
                        hovertemplate="From <b>%{y}</b> → <b>%{x}</b>: %{z:.2f}<extra></extra>",
                    ))
                    fig_trans.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white",
                        font_family="system-ui", height=260,
                        margin=dict(l=0, r=0, t=30, b=0),
                        xaxis=dict(title="To state", domain=[0.22, 1.0]),
                        yaxis=dict(title="From state", domain=[0.15, 1.0], automargin=True),
                        title=dict(text="State Transition Probabilities", font=dict(size=13)),
                    )
                    st.plotly_chart(fig_trans, use_container_width=True, config=_PLOTLY_CONFIG)

                    # Most common transition
                    np.fill_diagonal(t_reord, 0)
                    peak_from, peak_to = np.unravel_index(t_reord.argmax(), t_reord.shape)
                    st.markdown(
                        f'<div style="font-size:12px;color:#374151;background:#f9fafb;'
                        f'border-radius:6px;padding:10px 14px;">'
                        f'Most likely escalation path: <b>{STATE_NAMES[peak_from]}</b> → '
                        f'<b>{STATE_NAMES[peak_to]}</b> '
                        f'(p = {t_reord[peak_from, peak_to]:.2f})</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.info("At least 6 behavior observations are needed for HMM.")
            except Exception as e:
                st.warning(f"HMM unavailable: {e}")
        else:
            st.info("Behavior and date data required.")

    # 3. ARIMA Forecast ────────────────────────────────────────────────────────
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
                                   rangemode="nonnegative"),
                        legend=dict(orientation="h", y=1.08),
                    )
                    st.plotly_chart(fig_ar, use_container_width=True, config=_PLOTLY_CONFIG)
                    st.markdown(
                        f'<div style="font-size:12px;color:#374151;background:#f9fafb;'
                        f'border-radius:6px;padding:10px 14px;">'
                        f'7-day forecast mean: <b>{fc_mean.mean():.1f}</b> behaviors/day '
                        f'(95% CI: {fc_ci.iloc[:,0].mean():.1f}–{fc_ci.iloc[:,1].mean():.1f}). '
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
    with st.expander("Behavioral Network Graph", expanded=False):
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:16px;">'
            'Treats behaviors as nodes and transitions as directed edges. '
            'Node size = frequency. Edge thickness = transition strength. '
            'Hub behaviors (high in-degree + out-degree) are likely to trigger cascades. '
            'A pivot behavior is a critical link within a behavior chain that both receives input from multiple antecedents '
            'and leads to multiple subsequent behaviors. Unlike a general hub (which simply has many connections), '
            'a pivot plays a strategic role in driving progression between behaviors, often toward escalation.'
            '<br><br>'
            'For example, <i>Calling Out</i> may be triggered by different preceding behaviors and, once it occurs, '
            'consistently leads toward more severe outcomes — making it a key leverage point for intervention.'
            '<br><br>'
            '<b>Why this is important in FBA:</b>'
            '<ul style="margin:6px 0 6px 16px;padding:0;">'
            '<li>Addressing a pivot can disrupt several behavior pathways simultaneously</li>'
            '<li>It allows intervention earlier in the chain, when redirection is more feasible</li>'
            '<li>It represents an efficient target compared to focusing only on end-stage behaviors (e.g., aggression)</li>'
            '<li>In network graphs, high-centrality (red) nodes often signal likely pivot behaviors</li>'
            '</ul>'
            '<b>In essence:</b> Pivot behaviors are high-impact intervention points that allow practitioners to prevent '
            'escalation by intervening at a critical moment in the behavioral sequence.</div>',
            unsafe_allow_html=True
        )
        if "behavior" in df.columns and "date" in df.columns:
            try:
                import networkx as _nx

                # Build transition counts (reuse lag-1 logic)
                df_net = df.copy()
                if "time" in df_net.columns:
                    df_net["_sk"] = pd.to_datetime(
                        df_net["date"].astype(str) + " " + df_net["time"].astype(str), errors="coerce"
                    )
                else:
                    df_net["_sk"] = pd.to_datetime(df_net["date"], errors="coerce")
                df_net = df_net.sort_values("_sk")
                session_cols_net = ["date"] + (["setting"] if "setting" in df_net.columns else [])

                net_seq = []
                for _, grp in df_net.groupby(session_cols_net, sort=False):
                    net_seq.extend(list(grp["behavior"].dropna()))
                    net_seq.append(None)

                edge_counts = {}
                node_freq = df_net["behavior"].value_counts().to_dict()
                for i in range(len(net_seq) - 1):
                    a, b = net_seq[i], net_seq[i+1]
                    if a and b and a != b:
                        edge_counts[(a, b)] = edge_counts.get((a, b), 0) + 1

                if edge_counts:
                    G = _nx.DiGraph()
                    for beh, freq in node_freq.items():
                        G.add_node(beh, freq=freq)
                    for (a, b), w in edge_counts.items():
                        G.add_edge(a, b, weight=w)

                    # Layout
                    pos = _nx.spring_layout(G, seed=42, k=2.5)

                    max_freq = max(node_freq.values())
                    max_edge = max(edge_counts.values())

                    # Identify hub nodes (top by degree centrality)
                    centrality = _nx.degree_centrality(G)
                    hub_threshold = np.percentile(list(centrality.values()), 66)

                    fig_net = _go.Figure()

                    # Edges
                    for (a, b), w in edge_counts.items():
                        x0, y0 = pos[a]
                        x1, y1 = pos[b]
                        alpha = 0.3 + 0.5 * (w / max_edge)
                        fig_net.add_trace(_go.Scatter(
                            x=[x0, x1, None], y=[y0, y1, None],
                            mode="lines",
                            line=dict(width=1 + 3 * (w / max_edge), color=f"rgba(100,100,100,{alpha:.2f})"),
                            hoverinfo="none", showlegend=False,
                        ))

                    # Nodes
                    for beh in G.nodes():
                        x, y = pos[beh]
                        freq = node_freq.get(beh, 1)
                        is_hub = centrality[beh] >= hub_threshold
                        color = "#dc2626" if is_hub else "#4f6ef7"
                        size = 20 + 30 * (freq / max_freq)
                        fig_net.add_trace(_go.Scatter(
                            x=[x], y=[y], mode="markers+text",
                            text=[beh], textposition="top center",
                            textfont=dict(size=11, color="#111"),
                            marker=dict(size=size, color=color,
                                        line=dict(width=2, color="white")),
                            name="Hub" if is_hub else "Behavior",
                            hovertemplate=f"<b>{beh}</b><br>Frequency: {freq}<br>"
                                          f"Centrality: {centrality[beh]:.2f}<extra></extra>",
                            showlegend=False,
                        ))

                    fig_net.update_layout(
                        plot_bgcolor="white", paper_bgcolor="white",
                        font_family="system-ui", height=480,
                        margin=dict(l=20, r=20, t=20, b=20),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    )
                    st.plotly_chart(fig_net, use_container_width=True, config=_PLOTLY_CONFIG)

                    # Hub summary
                    hubs = sorted([b for b in G.nodes() if centrality[b] >= hub_threshold],
                                  key=lambda b: -centrality[b])
                    if hubs:
                        st.markdown(
                            '<div style="font-size:12px;color:#374151;background:#fef2f2;'
                            'border:1px solid #fecaca;border-radius:6px;padding:10px 14px;">'
                            '<b>Hub behaviors</b> (red nodes — highest transition centrality): '
                            + ", ".join(f"<b>{h}</b>" for h in hubs) +
                            '. These behaviors are most connected to others and may act as '
                            'triggers or pivots in behavioral chains.</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.info("At least 2 behavior transitions needed for the network graph.")
            except Exception as e:
                st.warning(f"Network graph unavailable: {e}")
        else:
            st.info("Behavior and date data required.")

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



# ── Category Settings Page ────────────────────────────────────────────────────
def page_settings():
    # Back button
    if st.button("← Back"):
        st.session_state["show_settings"] = False
        st.rerun()

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
    tab_abc, tab_setting, tab_users, tab_audit = st.tabs(
        ["A – B – C", "Setting Fields", "👤 Users", "🔒 Audit Log"]
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
                        with open(USERS_FILE, "w") as f:
                            json.dump(users, f, indent=2)
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
                            with open(USERS_FILE, "w") as f:
                                json.dump(users, f, indent=2)
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
                       layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)

    for key, default in [("logged_in", False), ("selected_student", None),
                          ("observer_name", ""), ("confirm_del", False),
                          ("last_active", None), ("user_role", "observer")]:
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
    st.markdown(f"""
    <div style="background:white;border-bottom:1.5px solid #e5e7eb;
                padding:10px 20px;margin:0 -1rem 20px -1rem;
                display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <div style="display:flex;align-items:center;gap:8px;background:#f0fdf4;
                    border:1.5px solid #bbf7d0;border-radius:20px;
                    padding:5px 12px 5px 8px;cursor:pointer;">
            <div style="width:24px;height:24px;background:#dcfce7;border-radius:50%;
                        display:flex;align-items:center;justify-content:center;
                        color:#16a34a;font-weight:700;font-size:11px;">{initial}</div>
            <span style="font-weight:600;color:#15803d;font-size:13px;">{student}</span>
            <span style="color:#86efac;font-size:11px;">▾</span>
        </div>
        <span style="color:#6b7280;font-size:13px;">Collector: <b style="color:#111;">{observer}</b></span>
        <span style="margin-left:auto;font-size:11px;color:#9ca3af;">
            🔒 Session expires in <b id="session-countdown">{SESSION_TIMEOUT_MIN}:00</b>
        </span>
    </div>
    <script>
    (function(){{
        var last={int(_time.time())}, timeout={SESSION_TIMEOUT_MIN * 60};
        function tick(){{
            var rem = timeout - (Math.floor(Date.now()/1000) - last);
            if(rem <= 0){{ document.getElementById('session-countdown').textContent = '0:00'; return; }}
            var m = Math.floor(rem/60), s = rem%60;
            var el = document.getElementById('session-countdown');
            if(el) el.textContent = m+':'+(s<10?'0':'')+s;
            setTimeout(tick, 1000);
        }}
        tick();
    }})();
    </script>
    """, unsafe_allow_html=True)

    # ── Top action buttons ────────────────────────────────────────────────────
    bc1, bc2, bc3, _ = st.columns([1, 1, 1, 5])
    with bc1:
        if st.button("Switch", use_container_width=True):
            st.session_state.selected_student = None
            st.rerun()
    with bc2:
        if st.button("🗑", use_container_width=True,
                     help="Delete all entries for this student"):
            st.session_state.confirm_clear = True
            st.rerun()
    with bc3:
        if st.button("⚙", use_container_width=True, help="Category settings"):
            st.session_state["show_settings"] = True
            st.rerun()

    if st.session_state.get("confirm_clear"):
        st.error(f"Delete ALL {len(student_entries)} entries for {student}?")
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("Yes, delete all", type="primary"):
                save_json(DATA_FILE,
                          [e for e in all_entries
                           if e.get("student_name") != student])
                st.session_state.confirm_clear = False
                st.rerun()
        with cc2:
            if st.button("Cancel"):
                st.session_state.confirm_clear = False
                st.rerun()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    t1, t2, t3, t4 = st.tabs([
        "📋  New ABC Entry",
        "⏱  New Interval Recording Entry",
        f"⊞  Log ({len(student_entries)})",
        "📊  Summary",
    ])
    with t1:
        tab_new_entry(all_entries, student, observer)
    with t2:
        tab_interval(all_entries, student, observer)
    with t3:
        _abbrevs = load_categories().get("behavior_abbrevs", {})
        tab_log(student_entries, all_entries, student, abbrevs=_abbrevs)
    with t4:
        tab_summary(student_entries)


if __name__ == "__main__":
    main()
