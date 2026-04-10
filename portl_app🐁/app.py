"""
PORTL App — Portable Operant Research and Teaching Lab
Flask web application: Simulation + Research Data Tool
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import sqlite3
import json
import os
import io
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "portl.db")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Research projects
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            research_question TEXT,
            behavior_definition TEXT,
            measurement_method TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Sessions belong to a project
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            session_number INTEGER NOT NULL,
            date TEXT NOT NULL,
            condition TEXT NOT NULL,
            procedure_notes TEXT,
            teacher_notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # Interval data within a session (10-reinforcer intervals)
    c.execute("""
        CREATE TABLE IF NOT EXISTS intervals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            interval_number INTEGER NOT NULL,
            behavior_count INTEGER DEFAULT 0,
            reinforcers_delivered INTEGER DEFAULT 10,
            errors INTEGER DEFAULT 0,
            plan_notes TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    # Simulation log (optional — records simulated sessions)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sim_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now')),
            procedure TEXT,
            target_behavior TEXT,
            log TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Main routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Simulation routes
# ---------------------------------------------------------------------------

@app.route("/simulation")
def simulation():
    return render_template("simulation.html")


@app.route("/api/simulation/save", methods=["POST"])
def save_simulation():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "INSERT INTO sim_sessions (procedure, target_behavior, log) VALUES (?, ?, ?)",
        (data.get("procedure", ""), data.get("target_behavior", ""), json.dumps(data.get("log", [])))
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Research data tool routes
# ---------------------------------------------------------------------------

@app.route("/research")
def research():
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("research.html", projects=projects)


@app.route("/research/project/new", methods=["GET", "POST"])
def new_project():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            """INSERT INTO projects (title, participant_id, research_question,
               behavior_definition, measurement_method)
               VALUES (?, ?, ?, ?, ?)""",
            (
                request.form["title"],
                request.form["participant_id"],
                request.form["research_question"],
                request.form["behavior_definition"],
                request.form["measurement_method"],
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("research"))
    return render_template("project_form.html", project=None)


@app.route("/research/project/<int:project_id>")
def view_project(project_id):
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    sessions = conn.execute(
        "SELECT * FROM sessions WHERE project_id=? ORDER BY session_number",
        (project_id,)
    ).fetchall()
    conn.close()
    return render_template("project_view.html", project=project, sessions=sessions)


@app.route("/research/project/<int:project_id>/session/new", methods=["GET", "POST"])
def new_session(project_id):
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if request.method == "POST":
        # Insert session
        cur = conn.execute(
            """INSERT INTO sessions (project_id, session_number, date, condition,
               procedure_notes, teacher_notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                request.form["session_number"],
                request.form["date"],
                request.form["condition"],
                request.form.get("procedure_notes", ""),
                request.form.get("teacher_notes", ""),
            )
        )
        session_id = cur.lastrowid

        # Insert interval rows
        num_intervals = int(request.form.get("num_intervals", 1))
        for i in range(1, num_intervals + 1):
            conn.execute(
                """INSERT INTO intervals (session_id, interval_number, behavior_count,
                   reinforcers_delivered, errors, plan_notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    i,
                    int(request.form.get(f"behavior_{i}", 0)),
                    int(request.form.get(f"reinforcers_{i}", 10)),
                    int(request.form.get(f"errors_{i}", 0)),
                    request.form.get(f"plan_{i}", ""),
                )
            )
        conn.commit()
        conn.close()
        return redirect(url_for("view_project", project_id=project_id))
    conn.close()
    return render_template("session_form.html", project=project,
                           today=datetime.now().strftime("%Y-%m-%d"))


@app.route("/research/project/<int:project_id>/session/<int:session_id>")
def view_session(project_id, session_id):
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    intervals = conn.execute(
        "SELECT * FROM intervals WHERE session_id=? ORDER BY interval_number",
        (session_id,)
    ).fetchall()
    conn.close()
    return render_template("session_view.html", project=project, session=session, intervals=intervals)


@app.route("/api/research/project/<int:project_id>/chart_data")
def chart_data(project_id):
    conn = get_db()
    sessions = conn.execute(
        "SELECT id, session_number, condition FROM sessions WHERE project_id=? ORDER BY session_number",
        (project_id,)
    ).fetchall()

    labels = []
    totals = []
    conditions = []

    for s in sessions:
        intervals = conn.execute(
            "SELECT behavior_count FROM intervals WHERE session_id=?",
            (s["id"],)
        ).fetchall()
        total = sum(row["behavior_count"] for row in intervals)
        labels.append(f"S{s['session_number']}")
        totals.append(total)
        conditions.append(s["condition"])

    conn.close()
    return jsonify({"labels": labels, "totals": totals, "conditions": conditions})


@app.route("/research/project/<int:project_id>/export")
def export_project(project_id):
    conn = get_db()
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    sessions = conn.execute(
        "SELECT * FROM sessions WHERE project_id=? ORDER BY session_number",
        (project_id,)
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header info
    writer.writerow(["PORTL Research Data Export"])
    writer.writerow(["Project:", project["title"]])
    writer.writerow(["Participant:", project["participant_id"]])
    writer.writerow(["Research Question:", project["research_question"]])
    writer.writerow(["Behavior Definition:", project["behavior_definition"]])
    writer.writerow(["Measurement Method:", project["measurement_method"]])
    writer.writerow([])

    # Session data
    writer.writerow(["Session", "Date", "Condition", "Interval", "Behavior Count",
                     "Reinforcers Delivered", "Errors", "Plan Notes"])

    for s in sessions:
        intervals = conn.execute(
            "SELECT * FROM intervals WHERE session_id=? ORDER BY interval_number",
            (s["id"],)
        ).fetchall()
        for iv in intervals:
            writer.writerow([
                s["session_number"], s["date"], s["condition"],
                iv["interval_number"], iv["behavior_count"],
                iv["reinforcers_delivered"], iv["errors"], iv["plan_notes"]
            ])

    conn.close()
    output.seek(0)
    filename = f"portl_{project['participant_id']}_export.csv"
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5050)
