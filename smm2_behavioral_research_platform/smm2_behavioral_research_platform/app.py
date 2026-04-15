"""
SMM2 Behavioral Research Platform
Live behavioral event coding companion app.

Run:  python -m smm2_behavioral_research_platform
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import csv
import datetime
import uuid
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).parent.parent
DATA_DIR    = ROOT_DIR / "data" / "raw"
CONFIG_PATH = Path(__file__).parent / "phenomena.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Theme colours ──────────────────────────────────────────────────────────────
BG      = "#1a1a2e"
BG2     = "#16213e"
ACCENT  = "#e94560"
TEXT    = "#eaeaea"
SUBTEXT = "#a8a8b3"
BTN_BG  = "#0f3460"
GREEN   = "#4ade80"
YELLOW  = "#facc15"
RED     = "#ef4444"


# ══════════════════════════════════════════════════════════════════════════════
# App
# ══════════════════════════════════════════════════════════════════════════════
class SMM2App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMM2 Behavioral Research Platform")
        self.geometry("980x740")
        self.minsize(820, 620)
        self.configure(bg=BG)

        self.phenomena: dict = self._load_phenomena()
        self.session:   dict = {}
        self.events:    list = []

        # Style ttk widgets
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=BG2, background=BG2,
                        foreground=TEXT, selectbackground=BTN_BG)
        style.configure("Treeview", background=BG2, foreground=TEXT,
                        fieldbackground=BG2, rowheight=24)
        style.configure("Treeview.Heading", background=BTN_BG, foreground=TEXT,
                        relief="flat")
        style.map("Treeview", background=[("selected", BTN_BG)])
        style.configure("TScrollbar", background=BG2, troughcolor=BG)

        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self._frames: dict = {}
        for Cls in (SetupFrame, RecordingFrame, ReviewFrame):
            frame = Cls(container, self)
            self._frames[Cls] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show(SetupFrame)

    # ── Navigation ─────────────────────────────────────────────────────────────
    def show(self, cls):
        frame = self._frames[cls]
        if hasattr(frame, "refresh"):
            frame.refresh()
        frame.tkraise()

    # ── Persistence helpers ────────────────────────────────────────────────────
    def _load_phenomena(self) -> dict:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    # ── Session API ────────────────────────────────────────────────────────────
    def start_session(self, data: dict):
        self.session = data
        self.session["session_id"] = str(uuid.uuid4())[:8].upper()
        self.session["start_dt"]   = datetime.datetime.now()
        self.events = []
        self.show(RecordingFrame)

    def log_event(self, code: str, label: str, note: str = "") -> dict:
        now     = datetime.datetime.now()
        elapsed = (now - self.session["start_dt"]).total_seconds()
        rec = {
            "session_id":     self.session["session_id"],
            "participant_id": self.session["participant_id"],
            "observer_id":    self.session["observer_id"],
            "level_id":       self.session["level_id"],
            "phenomenon":     self.session["phenomenon_key"],
            "condition":      self.session["condition"],
            "date":           self.session["start_dt"].strftime("%Y-%m-%d"),
            "wall_time":      now.strftime("%H:%M:%S.%f")[:-3],
            "elapsed_s":      round(elapsed, 3),
            "event_code":     code,
            "event_label":    label,
            "note":           note,
        }
        self.events.append(rec)
        return rec

    def end_session(self):
        self.show(ReviewFrame)

    def export_csv(self) -> Path:
        s     = self.session
        ts    = s["start_dt"].strftime("%Y%m%d_%H%M%S")
        fname = f"{s['participant_id']}_{s['level_id']}_{s['session_id']}_{ts}.csv"
        path  = DATA_DIR / fname
        if self.events:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(self.events[0].keys()))
                writer.writeheader()
                writer.writerows(self.events)
        return path


# ══════════════════════════════════════════════════════════════════════════════
# Setup Frame
# ══════════════════════════════════════════════════════════════════════════════
class SetupFrame(tk.Frame):
    def __init__(self, parent, app: SMM2App):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        # ── Header ────────────────────────────────────────────────────────────
        tk.Label(self, text="SMM2 Behavioral Research Platform",
                 font=("Helvetica", 20, "bold"), fg=ACCENT, bg=BG
                 ).pack(pady=(40, 4))
        tk.Label(self, text="Session Setup",
                 font=("Helvetica", 13), fg=SUBTEXT, bg=BG
                 ).pack(pady=(0, 28))

        # ── Form ──────────────────────────────────────────────────────────────
        form = tk.Frame(self, bg=BG)
        form.pack(padx=120, fill="x")

        self._vars: dict = {}

        for lbl, key in [
            ("Participant ID",             "participant_id"),
            ("Observer ID",                "observer_id"),
            ("Level ID  (SMM2 Course ID)", "level_id"),
        ]:
            self._make_entry(form, lbl, key)

        # Condition
        self._lbl(form, "Condition")
        self._cond = tk.StringVar(value="Research")
        ttk.Combobox(form, textvariable=self._cond,
                     values=["Demo", "Practice", "Research"],
                     state="readonly", font=("Helvetica", 12)
                     ).pack(fill="x", pady=(2, 14))

        # Phenomenon
        self._lbl(form, "Phenomenon")
        keys   = list(self.app.phenomena.keys())
        labels = [self.app.phenomena[k]["label"] for k in keys]
        self._phenom_keys   = keys
        self._phenom_labels = labels
        self._phenom_var    = tk.StringVar(value=labels[0] if labels else "")
        self._phenom_box    = ttk.Combobox(form, textvariable=self._phenom_var,
                                            values=labels, state="readonly",
                                            font=("Helvetica", 12))
        self._phenom_box.pack(fill="x", pady=(2, 14))

        # Notes
        self._lbl(form, "Session Notes  (optional)")
        self._notes = tk.Text(form, height=3, font=("Helvetica", 11),
                              bg=BG2, fg=TEXT, insertbackground=TEXT,
                              relief="flat", bd=6)
        self._notes.pack(fill="x", pady=(2, 28))

        # Start button
        tk.Button(self, text="  \u25b6   Start Session  ",
                  font=("Helvetica", 14, "bold"),
                  bg=ACCENT, fg="white", relief="flat", cursor="hand2",
                  activebackground="#c73652", activeforeground="white",
                  command=self._start
                  ).pack(ipadx=10, ipady=10)

    def _lbl(self, parent, text: str):
        tk.Label(parent, text=text, font=("Helvetica", 11, "bold"),
                 fg=SUBTEXT, bg=BG, anchor="w").pack(fill="x")

    def _make_entry(self, parent, label: str, key: str):
        self._lbl(parent, label)
        v = tk.StringVar()
        tk.Entry(parent, textvariable=v, font=("Helvetica", 12),
                 bg=BG2, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=6
                 ).pack(fill="x", pady=(2, 14))
        self._vars[key] = v

    def _start(self):
        label = self._phenom_var.get()
        try:
            idx = self._phenom_labels.index(label)
            key = self._phenom_keys[idx]
        except ValueError:
            key = ""

        self.app.start_session({
            "participant_id":   self._vars["participant_id"].get().strip() or "P001",
            "observer_id":      self._vars["observer_id"].get().strip()    or "O001",
            "level_id":         self._vars["level_id"].get().strip()       or "UNKNOWN",
            "condition":        self._cond.get(),
            "phenomenon_key":   key,
            "phenomenon_label": label,
            "session_notes":    self._notes.get("1.0", "end").strip(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# Recording Frame
# ══════════════════════════════════════════════════════════════════════════════
class RecordingFrame(tk.Frame):
    _TICK_MS = 100   # timer refresh interval

    def __init__(self, parent, app: SMM2App):
        super().__init__(parent, bg=BG)
        self.app          = app
        self._paused      = False
        self._pause_start = None
        self._paused_secs = 0.0
        self._after_id    = None
        self._hotkeys: dict = {}   # key -> (code, label)
        self._build()

    # ── Layout ─────────────────────────────────────────────────────────────────
    def _build(self):
        # Header bar
        hdr = tk.Frame(self, bg=BG2)
        hdr.pack(fill="x")

        self._session_lbl = tk.Label(hdr, text="", font=("Helvetica", 10),
                                      fg=SUBTEXT, bg=BG2, anchor="w")
        self._session_lbl.pack(side="left", padx=16, pady=8)

        tk.Button(hdr, text="\u25a0  Stop",
                  font=("Helvetica", 10, "bold"),
                  bg=RED, fg="white", relief="flat", cursor="hand2",
                  command=self._stop
                  ).pack(side="right", padx=8, pady=6, ipadx=10)

        self._pause_btn = tk.Button(hdr, text="\u23f8  Pause",
                                     font=("Helvetica", 10, "bold"),
                                     bg=BTN_BG, fg="white", relief="flat",
                                     cursor="hand2", command=self._toggle_pause)
        self._pause_btn.pack(side="right", padx=4, pady=6, ipadx=10)

        # Timer
        timer_row = tk.Frame(self, bg=BG)
        timer_row.pack(pady=(16, 2))

        self._timer_lbl = tk.Label(timer_row, text="00:00.0",
                                    font=("Courier", 54, "bold"),
                                    fg=GREEN, bg=BG)
        self._timer_lbl.pack()

        self._clock_lbl = tk.Label(timer_row, text="",
                                    font=("Helvetica", 12), fg=SUBTEXT, bg=BG)
        self._clock_lbl.pack()

        self._phenom_lbl = tk.Label(self, text="",
                                     font=("Helvetica", 13, "bold"),
                                     fg=ACCENT, bg=BG)
        self._phenom_lbl.pack(pady=(2, 10))

        # Event buttons area
        self._btn_frame = tk.Frame(self, bg=BG)
        self._btn_frame.pack(padx=16, fill="x")

        # Note row
        note_row = tk.Frame(self, bg=BG)
        note_row.pack(padx=16, pady=(10, 4), fill="x")

        tk.Label(note_row, text="Note:", font=("Helvetica", 11),
                 fg=SUBTEXT, bg=BG).pack(side="left")
        self._note_var = tk.StringVar()
        self._note_entry = tk.Entry(note_row, textvariable=self._note_var,
                                     font=("Helvetica", 11),
                                     bg=BG2, fg=TEXT, insertbackground=TEXT,
                                     relief="flat", bd=4, width=44)
        self._note_entry.pack(side="left", padx=(8, 8))
        tk.Button(note_row, text="Log Note  [N]",
                  font=("Helvetica", 10), bg=BTN_BG, fg="white",
                  relief="flat", cursor="hand2",
                  command=self._log_note
                  ).pack(side="left")

        # Event log
        tk.Label(self, text="\u2014  Recent Events  \u2014",
                 font=("Helvetica", 10), fg=SUBTEXT, bg=BG).pack(pady=(10, 2))

        log_wrap = tk.Frame(self, bg=BG2)
        log_wrap.pack(padx=16, pady=(0, 16), fill="both", expand=True)

        self._log = tk.Text(log_wrap, font=("Courier", 10),
                             bg=BG2, fg=TEXT, state="disabled",
                             relief="flat", wrap="none", height=9)
        sb_y = tk.Scrollbar(log_wrap, orient="vertical",   command=self._log.yview)
        sb_x = tk.Scrollbar(log_wrap, orient="horizontal", command=self._log.xview)
        self._log.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
        sb_y.pack(side="right",  fill="y")
        sb_x.pack(side="bottom", fill="x")
        self._log.pack(side="left", fill="both", expand=True, padx=8, pady=8)

    # ── Refresh (called every time we navigate here) ────────────────────────────
    def refresh(self):
        s = self.app.session
        self._session_lbl.configure(
            text=(f"Session {s.get('session_id','')}  |  "
                  f"P: {s.get('participant_id','')}  |  "
                  f"Level: {s.get('level_id','')}  |  "
                  f"Condition: {s.get('condition','')}"))
        self._phenom_lbl.configure(text=s.get("phenomenon_label", ""))

        # Reset pause state
        self._paused      = False
        self._paused_secs = 0.0
        self._pause_start = None
        self._pause_btn.configure(text="\u23f8  Pause", bg=BTN_BG)
        self._timer_lbl.configure(fg=GREEN)

        # Clear log
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        self._note_var.set("")

        # Rebuild event buttons
        for w in self._btn_frame.winfo_children():
            w.destroy()
        self._hotkeys.clear()
        self._unbind_hotkeys()

        phenom_key  = s.get("phenomenon_key", "")
        events_cfg  = self.app.phenomena.get(phenom_key, {}).get("events", [])
        cols        = 4

        for i, ev in enumerate(events_cfg):
            code  = ev["code"]
            label = ev["label"]
            key   = ev["key"]
            self._hotkeys[key] = (code, label)
            btn = tk.Button(
                self._btn_frame,
                text=f"{label}\n[ {key.upper()} ]",
                font=("Helvetica", 11, "bold"),
                bg=BTN_BG, fg="white", relief="flat", cursor="hand2",
                wraplength=180, height=2,
                command=lambda c=code, l=label: self._log_ev(c, l)
            )
            btn.grid(row=i // cols, column=i % cols,
                     padx=6, pady=6, sticky="ew")

        for c in range(cols):
            self._btn_frame.columnconfigure(c, weight=1)

        self._bind_hotkeys()

        # Start ticker
        if self._after_id:
            self.after_cancel(self._after_id)
        self._tick()

    # ── Timer ──────────────────────────────────────────────────────────────────
    def _tick(self):
        if not self._paused:
            e = self._elapsed()
            m = int(e // 60)
            s = e % 60
            self._timer_lbl.configure(text=f"{m:02d}:{s:04.1f}")
        self._clock_lbl.configure(
            text=datetime.datetime.now().strftime("%H:%M:%S"))
        self._after_id = self.after(self._TICK_MS, self._tick)

    def _elapsed(self) -> float:
        if not self.app.session.get("start_dt"):
            return 0.0
        raw = (datetime.datetime.now() - self.app.session["start_dt"]).total_seconds()
        return max(0.0, raw - self._paused_secs)

    # ── Event logging ──────────────────────────────────────────────────────────
    def _log_ev(self, code: str, label: str):
        if self._paused:
            return
        note = self._note_var.get().strip()
        ev   = self.app.log_event(code, label, note)
        self._note_var.set("")
        self._append_log(ev)

    def _log_note(self):
        note = self._note_var.get().strip()
        if note:
            ev = self.app.log_event("NOTE", "Observer Note", note)
            self._note_var.set("")
            self._append_log(ev)

    def _append_log(self, ev: dict):
        line = (f"  {ev['wall_time']}  {ev['elapsed_s']:>9.3f}s"
                f"  {ev['event_code']:<22}  {ev['note']}\n")
        self._log.configure(state="normal")
        self._log.insert("1.0", line)
        self._log.configure(state="disabled")

    # ── Pause / Stop ───────────────────────────────────────────────────────────
    def _toggle_pause(self):
        if self._paused:
            dur = (datetime.datetime.now() - self._pause_start).total_seconds()
            self._paused_secs += dur
            self._paused       = False
            self._pause_start  = None
            self._pause_btn.configure(text="\u23f8  Pause", bg=BTN_BG)
            self._timer_lbl.configure(fg=GREEN)
            self.app.log_event("SESSION_RESUME", "Session Resumed")
        else:
            self._pause_start = datetime.datetime.now()
            self._paused      = True
            self._pause_btn.configure(text="\u25b6  Resume", bg=YELLOW)
            self._timer_lbl.configure(fg=YELLOW)
            self.app.log_event("SESSION_PAUSE", "Session Paused")

    def _stop(self):
        if messagebox.askyesno("End Session",
                               "End this session and proceed to review?"):
            if self._after_id:
                self.after_cancel(self._after_id)
            self._unbind_hotkeys()
            self.app.log_event("SESSION_END", "Session Ended")
            self.app.end_session()

    # ── Hotkeys ────────────────────────────────────────────────────────────────
    def _bind_hotkeys(self):
        for key, (code, label) in self._hotkeys.items():
            self.app.bind(f"<KeyPress-{key}>",
                          lambda e, c=code, l=label: self._log_ev(c, l))
        self.app.bind("<KeyPress-n>", lambda e: self._log_note())

    def _unbind_hotkeys(self):
        for key in list(self._hotkeys.keys()):
            try:
                self.app.unbind(f"<KeyPress-{key}>")
            except Exception:
                pass
        try:
            self.app.unbind("<KeyPress-n>")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Review Frame
# ══════════════════════════════════════════════════════════════════════════════
class ReviewFrame(tk.Frame):
    def __init__(self, parent, app: SMM2App):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text="Session Review",
                 font=("Helvetica", 18, "bold"), fg=ACCENT, bg=BG
                 ).pack(pady=(30, 4))
        self._summary = tk.Label(self, text="",
                                  font=("Helvetica", 11), fg=SUBTEXT, bg=BG)
        self._summary.pack(pady=(0, 14))

        # Treeview table
        tbl_wrap = tk.Frame(self, bg=BG2)
        tbl_wrap.pack(padx=20, fill="both", expand=True)

        cols     = ("wall_time", "elapsed_s", "event_code", "event_label", "note")
        headers  = {"wall_time": "Wall Time", "elapsed_s": "Elapsed (s)",
                    "event_code": "Code", "event_label": "Label", "note": "Note"}
        col_w    = {"wall_time": 115, "elapsed_s": 90, "event_code": 160,
                    "event_label": 190, "note": 260}

        self._tree = ttk.Treeview(tbl_wrap, columns=cols,
                                   show="headings", height=22)
        for c in cols:
            self._tree.heading(c, text=headers[c])
            self._tree.column(c, width=col_w[c], anchor="w")

        vsb = ttk.Scrollbar(tbl_wrap, orient="vertical",
                             command=self._tree.yview)
        hsb = ttk.Scrollbar(tbl_wrap, orient="horizontal",
                             command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set,
                              xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(side="left", fill="both", expand=True)

        # Buttons
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(pady=18)

        for txt, color, cmd in [
            ("Export CSV",   GREEN,  self._export),
            ("New Session",  BTN_BG, self._new_session),
            ("Quit",         ACCENT, self.app.quit),
        ]:
            tk.Button(btn_row, text=txt,
                      font=("Helvetica", 12, "bold"),
                      bg=color, fg="#1a1a2e" if color == GREEN else "white",
                      relief="flat", cursor="hand2", command=cmd
                      ).pack(side="left", ipadx=14, ipady=8, padx=8)

    def refresh(self):
        evs = self.app.events
        s   = self.app.session

        dur_s = (datetime.datetime.now() - s["start_dt"]).total_seconds()
        m, sec = divmod(dur_s, 60)
        self._summary.configure(
            text=(f"Session {s.get('session_id','')}  |  "
                  f"Participant: {s.get('participant_id','')}  |  "
                  f"Phenomenon: {s.get('phenomenon_label','')}  |  "
                  f"Events: {len(evs)}  |  "
                  f"Duration: {int(m):02d}:{sec:04.1f}"))

        for row in self._tree.get_children():
            self._tree.delete(row)
        for ev in evs:
            self._tree.insert("", "end", values=(
                ev["wall_time"], ev["elapsed_s"],
                ev["event_code"], ev["event_label"], ev["note"]
            ))

    def _export(self):
        path = self.app.export_csv()
        messagebox.showinfo("Exported", f"Data saved to:\n{path}")

    def _new_session(self):
        self.app.show(SetupFrame)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = SMM2App()
    app.mainloop()


if __name__ == "__main__":
    main()
