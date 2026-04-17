"""
Generate SMM2 Behavioral Research Platform — Project Overview PDF
Run: python generate_project_overview.py
Output: reports/SMM2_Behavioral_Research_Platform_Overview.pdf
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
REPORTS = BASE / "reports"
REPORTS.mkdir(exist_ok=True)
OUT = REPORTS / "SMM2_Behavioral_Research_Platform_Overview.pdf"

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0f3460")
RED    = colors.HexColor("#e94560")
GREEN  = colors.HexColor("#4ade80")
GOLD   = colors.HexColor("#facc15")
GREY   = colors.HexColor("#334155")
LGREY  = colors.HexColor("#f1f5f9")
WHITE  = colors.white
BLACK  = colors.black

# ── Styles ────────────────────────────────────────────────────────────────────
base_styles = getSampleStyleSheet()

def make_style(name, parent="Normal", **kwargs):
    return ParagraphStyle(name, parent=base_styles[parent], **kwargs)

S_TITLE   = make_style("S_TITLE",   "Title",  fontSize=26, textColor=NAVY,
                        spaceAfter=6, alignment=TA_CENTER, leading=30)
S_SUB     = make_style("S_SUB",     "Normal", fontSize=13, textColor=GREY,
                        spaceAfter=12, alignment=TA_CENTER)
S_H1      = make_style("S_H1",      "Heading1", fontSize=17, textColor=WHITE,
                        spaceAfter=6, leading=20)
S_H2      = make_style("S_H2",      "Heading2", fontSize=13, textColor=NAVY,
                        spaceBefore=10, spaceAfter=4, leading=16)
S_H3      = make_style("S_H3",      "Heading3", fontSize=11, textColor=GREY,
                        spaceBefore=6, spaceAfter=3, leading=14)
S_BODY    = make_style("S_BODY",    "Normal",  fontSize=10, textColor=BLACK,
                        leading=14, spaceAfter=5, alignment=TA_JUSTIFY)
S_BULLET  = make_style("S_BULLET",  "Normal",  fontSize=10, textColor=BLACK,
                        leading=13, leftIndent=18, bulletIndent=6,
                        spaceAfter=2)
S_CODE    = make_style("S_CODE",    "Normal",  fontSize=8,
                        fontName="Courier", textColor=NAVY,
                        backColor=LGREY, leading=11, leftIndent=12,
                        rightIndent=12, spaceAfter=4)
S_CAPTION = make_style("S_CAPTION", "Normal",  fontSize=8.5, textColor=GREY,
                        alignment=TA_CENTER, spaceAfter=6)
S_TABLE_H = make_style("S_TABLE_H", "Normal",  fontSize=9, textColor=WHITE,
                        fontName="Helvetica-Bold", leading=12,
                        alignment=TA_CENTER)
S_TABLE_B = make_style("S_TABLE_B", "Normal",  fontSize=8.5, textColor=BLACK,
                        leading=12, alignment=TA_LEFT)
S_NOTE    = make_style("S_NOTE",    "Normal",  fontSize=9, textColor=GREY,
                        leading=12, leftIndent=10, rightIndent=10,
                        spaceAfter=4)

# ── Helper builders ──────────────────────────────────────────────────────────
def section_header(title):
    """Navy banner with white text used as a section divider."""
    data = [[Paragraph(title, S_H1)]]
    t = Table(data, colWidths=[6.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [NAVY]),
    ]))
    return t

def info_box(text, bg=LGREY, border=NAVY):
    data = [[Paragraph(text, S_NOTE)]]
    t = Table(data, colWidths=[6.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("BOX",           (0,0), (-1,-1), 1, border),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return t

def make_table(headers, rows, col_widths=None):
    if col_widths is None:
        col_widths = [6.5*inch / len(headers)] * len(headers)
    header_row = [Paragraph(h, S_TABLE_H) for h in headers]
    body_rows  = [[Paragraph(str(c), S_TABLE_B) for c in r] for r in rows]
    data = [header_row] + body_rows
    t = Table(data, colWidths=col_widths)
    style = [
        ("BACKGROUND",    (0,0), (-1,0),  NAVY),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LGREY]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]
    t.setStyle(TableStyle(style))
    return t

def bullet(text):
    return Paragraph(f"• {text}", S_BULLET)

def h2(text): return Paragraph(text, S_H2)
def h3(text): return Paragraph(text, S_H3)
def body(text): return Paragraph(text, S_BODY)
def sp(n=6): return Spacer(1, n)
def hr(): return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"))
def code(text): return Paragraph(text.replace("\n", "<br/>").replace(" ", "&nbsp;"), S_CODE)

# ── Content ───────────────────────────────────────────────────────────────────
story = []

# ═══════════════════════════════════════════════════════════
# COVER
# ═══════════════════════════════════════════════════════════
story += [
    sp(60),
    Paragraph("SMM2 Behavioral Research Platform", S_TITLE),
    sp(8),
    Paragraph("Project Overview &amp; Technical Reference", S_SUB),
    sp(4),
    HRFlowable(width="60%", thickness=2, color=RED, hAlign="CENTER"),
    sp(12),
    Paragraph(
        "A comprehensive platform for programmed instruction and behavioral data collection "
        "using Super Mario Maker 2 as an experimental apparatus, covering 20 behavioral "
        "phenomena across simple and compound reinforcement schedules.",
        make_style("cover_body", fontSize=11, alignment=TA_CENTER,
                   textColor=GREY, leading=16)),
    sp(20),
    make_table(
        ["Component", "Count", "Status"],
        [
            ["Behavioral phenomena", "21", "Complete"],
            ["Level specs (research docs)", "21", "Complete"],
            ["Companion app event configs", "21 + 1 alias", "Complete"],
            ["Analysis notebooks", "10 (00–09)", "Complete"],
            ["SMM2 builder's guides", "24 files", "Complete"],
            ["Machine-readable parameters", "1 (parameters.json)", "Complete"],
        ],
        col_widths=[3.0*inch, 1.5*inch, 2.0*inch]
    ),
    sp(20),
    Paragraph("ABA 761 — Introduction to Python for Behavior Analysis", S_CAPTION),
    Paragraph("Endicott College | operantteachingtech.com", S_CAPTION),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 1. OVERVIEW
# ═══════════════════════════════════════════════════════════
story += [
    section_header("1. Project Overview"),
    sp(10),
    h2("Purpose"),
    body(
        "The SMM2 Behavioral Research Platform uses Super Mario Maker 2 (SMM2) as a "
        "controlled experimental environment for two complementary goals: "
        "<b>programmed instruction</b> (teaching behavioral principles through direct "
        "experience) and <b>behavioral data collection</b> (recording participants' "
        "in-game behavior as operant data). "
        "The platform targets three audiences: students observing instructor demonstrations, "
        "research participants whose behavior is coded and analyzed, and researchers "
        "replicating the paradigms at other institutions."
    ),
    sp(6),
    h2("Why SMM2?"),
    body(
        "SMM2 provides a uniquely controllable behavioral environment: response requirements "
        "are discrete and measurable (block hits, fork choices, path selections), reinforcers "
        "are concrete and immediate (coins, stars), antecedent stimuli are visually distinct "
        "(background themes and filters), and the level editor allows precise programming of "
        "reinforcement schedules by controlling block placement and coin availability. "
        "The game imposes no ceiling on response rate and produces moment-to-moment behavior "
        "streams that map directly onto operant concepts."
    ),
    sp(6),
    h2("Distribution"),
    body(
        "Controlled laboratory distribution only. Levels are uploaded to Nintendo's servers "
        "as private courses; course IDs are shared only with enrolled participants in a "
        "supervised lab setting. Screen recording + live behavioral coding + SMM2 built-in "
        "stats provide three synchronized data streams per session."
    ),
    sp(10),
    h2("Data Flow"),
    info_box(
        "SMM2 level played → Screen recording (MP4, timestamped) + Companion app live coding "
        "(CSV, wall_time key) + SMM2 built-in stats (manually entered CSV) → "
        "data/raw/ → 00_data_pipeline.ipynb (clean + join) → data/processed/ → "
        "Analysis notebooks 01–08 → reports/figures/"
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 2. REPOSITORY STRUCTURE
# ═══════════════════════════════════════════════════════════
story += [
    section_header("2. Repository Structure"),
    sp(10),
    body("GitHub: <b>joeO3335-design/aba-761-python</b> (branch: main)"),
    sp(6),
    body("Platform lives in the <b>smm2_behavioral_research_platform/</b> subdirectory, "
         "generated with Cookiecutter Data Science (ccds)."),
    sp(8),
    make_table(
        ["Path", "Contents"],
        [
            ["smm2_behavioral_research_platform/",         "Project root (ccds scaffold)"],
            ["  smm2_behavioral_research_platform/app.py", "tkinter companion app (live coder)"],
            ["  smm2_behavioral_research_platform/phenomena.json", "Event configs for all 20 phenomena"],
            ["  notebooks/00_data_pipeline.ipynb",         "Load, clean, validate raw CSVs → parquet"],
            ["  notebooks/01_rate_analysis.ipynb",         "Cumulative records, post-SR pause, ext. burst"],
            ["  notebooks/02_discrimination_generalization.ipynb", "Discrimination index, generalization gradient"],
            ["  notebooks/03_matching_law.ipynb",          "GML fit (OLS), sensitivity + bias plots"],
            ["  notebooks/04_explore_exploit.ipynb",       "ε-greedy + softmax MLE, directed vs. random"],
            ["  notebooks/05_sequential_behavior.ipynb",   "Trials-to-criterion, chain completion rates"],
            ["  notebooks/06_ioa.ipynb",                   "Total count + 10-s window IOA, flags <80%"],
            ["  notebooks/07_behavioral_momentum_amelioration.ipynb", "Nevin model fit, local-rate melioration test"],
            ["  notebooks/08_compound_schedules.ipynb",    "CONC matching, ALT dominance, CONJ IRI, MULT contrast, MIX vs. MULT, CHAIN gradient, TAND vs. CHAIN"],
            ["  references/level_specs/",                  "20 level spec .md files + INDEX.md + parameters.json"],
            ["  references/builder_guides/",               "23 tile-by-tile SMM2 construction guides"],
            ["  data/raw/",                                 "Raw CSV files from companion app"],
            ["  data/processed/",                          "Parquet files (post-pipeline)"],
            ["  reports/figures/",                         "Analysis output figures"],
        ],
        col_widths=[3.4*inch, 3.1*inch]
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 3. COMPANION APP
# ═══════════════════════════════════════════════════════════
story += [
    section_header("3. Companion App (Live Behavioral Coder)"),
    sp(10),
    h2("Technology"),
    body("Python 3 + tkinter (zero external dependencies). Run with: "
         "<font name='Courier' size='9'>python -m smm2_behavioral_research_platform</font>"),
    sp(6),
    h2("Architecture — Three Frames"),
    make_table(
        ["Frame", "Purpose", "Key Fields"],
        [
            ["SetupFrame",     "Session configuration", "Participant ID, Observer ID, Level ID, Phenomenon selector"],
            ["RecordingFrame", "Live event coding", "Event buttons (per-phenomenon hotkeys), elapsed timer, Note field, Pause/Resume"],
            ["ReviewFrame",    "Post-session review", "Scrollable event log, Export CSV button, Start new session"],
        ],
        col_widths=[1.4*inch, 2.0*inch, 3.1*inch]
    ),
    sp(8),
    h2("CSV Output Schema"),
    body("Every button press writes one row to <font name='Courier' size='9'>data/raw/{pid}_{level}_{session}.csv</font>:"),
    sp(4),
    make_table(
        ["Column", "Type", "Description"],
        [
            ["session_id",     "UUID",      "Unique session identifier"],
            ["participant_id", "string",    "Participant code"],
            ["observer_id",    "string",    "Observer code"],
            ["level_id",       "string",    "SMM2 course ID"],
            ["phenomenon",     "string",    "phenomenon_key (matches phenomena.json)"],
            ["condition",      "string",    "Observer-entered condition label"],
            ["date",           "YYYY-MM-DD","Session date"],
            ["wall_time",      "ISO 8601",  "Absolute timestamp (sync key with screen recording)"],
            ["elapsed_s",      "float",     "Seconds since session start (pauses excluded)"],
            ["event_code",     "string",    "e.g. RESPONSE, SR_PLUS, LEFT, CHAIN_BREAK"],
            ["event_label",    "string",    "Human-readable label from phenomena.json"],
            ["note",           "string",    "Observer free-text note"],
        ],
        col_widths=[1.5*inch, 1.0*inch, 4.0*inch]
    ),
    sp(8),
    h2("Config-Driven Event Buttons"),
    body(
        "Each phenomenon's buttons are defined in <font name='Courier' size='9'>phenomena.json</font> "
        "as a list of <font name='Courier' size='9'>{key, label, code}</font> objects. "
        "Adding a new phenomenon requires only a JSON entry — no code changes. "
        "Keyboard hotkeys are single characters (a–z, 0–9) set in the JSON."
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 4. CURRICULUM — SIMPLE SCHEDULES (1–13)
# ═══════════════════════════════════════════════════════════
story += [
    section_header("4. Curriculum — Simple Schedules (Phenomena 1–13)"),
    sp(10),
    body(
        "The first 13 phenomena follow Skinner's programmed instruction sequence: "
        "each builds directly on the prior concept. Positive reinforcement is taught "
        "first (coin from block = SR+), then schedule parameters, then derived phenomena "
        "(extinction, negative reinforcement, punishment, shaping) and finally quantitative "
        "models (matching law, explore/exploit, behavioral momentum, amelioration)."
    ),
    sp(8),
    make_table(
        ["#", "Phenomenon", "SMM2 Mechanic", "Key Dependent Variable"],
        [
            ["1",  "Positive Reinforcement",  "? blocks → coins (CRF, FR3, VR3, EXT zones)",        "Response rate by schedule zone"],
            ["2",  "Reinforcement Schedules",  "FR3, VR3, FI5s, VI5.5s zones",                       "Post-SR pause, run length, scallop"],
            ["3",  "Extinction",               "Active vs. used blocks; 4-session ABA",               "Response rate over blocks; ext. burst"],
            ["4",  "Negative Reinforcement",   "Goomba escape + coin-trail avoidance warning",        "Escape latency; avoidance proportion"],
            ["5",  "Punishment",               "Buzzy Beetle on rich fork (ABAB reversal)",           "% left-path choices vs. phase"],
            ["6",  "Shaping",                  "5-step progressive jump difficulty",                  "Trials-to-criterion per step"],
            ["7",  "Stimulus Control",         "Night filter SD, Sunset filter SΔ (8 zones)",         "Discrimination index"],
            ["8",  "Generalization",           "Cross-theme probes (Underground→Castle→Airship)",     "Responses per probe; gradient slope"],
            ["9",  "Behavioral Chaining",      "P-switch → ON/OFF switch → P-switch 2 → flag",       "Chain completion rate; link latencies"],
            ["10", "Matching Law",             "Concurrent coin-density fork (5 ratio conditions)",   "GML: sensitivity a, bias b"],
            ["11", "Explore / Exploit",        "Hidden block branches + 100-s timer (4 run blocks)",  "Exploration rate; ε-greedy + UCB1 fit"],
            ["12", "Behavioral Momentum",      "Rich CRF vs. lean FR10 + free-SR disruptor",         "Resistance-to-change ratio; Nevin fit"],
            ["13", "Amelioration",             "CONC FR-FR vs. VI-VI fork (40 choices × 2)",          "Run length; local-rate melioration test"],
        ],
        col_widths=[0.25*inch, 1.55*inch, 2.4*inch, 2.3*inch]
    ),
    sp(10),
    h2("Programmed Instruction Rationale"),
    body(
        "Each phenomenon uses two levels: a <b>Demo level</b> the instructor plays live "
        "while narrating, and a <b>Research level</b> the participant plays while an "
        "observer codes behavior in real time using the companion app. "
        "This mirrors Skinner's programmed instruction format: the student first observes "
        "the contingency operationalized (the game mechanic IS the contingency, not a "
        "metaphor for it), then experiences it directly."
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 5. CURRICULUM — COMPOUND SCHEDULES (14–20)
# ═══════════════════════════════════════════════════════════
story += [
    section_header("5. Curriculum — Compound Schedules &amp; Choice (Phenomena 14–21)"),
    sp(10),
    body(
        "Compound schedules arrange two or more component schedules in specific logical "
        "relationships. Ferster and Skinner (1957) identified the primary types. "
        "These seven phenomena form an advanced module taught after the simple schedule foundations."
    ),
    sp(8),
    make_table(
        ["#", "Schedule", "Logic", "SMM2 Mechanic", "Key Comparison"],
        [
            ["14", "CONC\n(Concurrent)", "Both always on;\nfree switching",
             "Symmetric fork + COD blocks", "FR-FR (exclusive) vs. VI-VI (matching); COD effect"],
            ["15", "ALT\n(Alternative)", "Reinforce when\nEITHER met first",
             "FR blocks race ground coin\n(FI timer)", "FR3 FI20s (FR wins) vs. FR20 FI5s (FI wins)"],
            ["16", "CONJ\n(Conjunctive)", "Reinforce only\nwhen BOTH met",
             "P-switch gate (FI) + FR blocks", "Binding constraint: FR vs. FI; IRI vs. pure schedules"],
            ["17", "MULT\n(Multiple)", "Different schedules,\ndifferent SDs",
             "Night (VI5s) vs. Sunset (EXT)\nsub-areas; ABA reversal", "Behavioral contrast in ABA phases"],
            ["18", "MIX\n(Mixed)", "Same alternation,\nno SDs",
             "Identical appearance;\nVI/EXT unsignaled", "EXT-component rate MIX vs. MULT"],
            ["19", "CHAIN\n(Chained)", "Sequential; SD change\nat each link",
             "P-switch blue coins as\nconditioned SR", "Goal gradient; L1 rate vs. TAND"],
            ["20", "TAND\n(Tandem)", "Sequential; NO SD\nchange at links",
             "Silent sequential FR blocks;\nno P-switch signal", "Flat IRT vs. CHAIN gradient; post-C1 pause"],
            ["21", "Delay Discounting", "Choice: amount\nvs. delay",
             "SS/LL fork; 5 delay\nconditions (3–60 s)", "Hyperbolic V=A/(1+kD); fit k, D₅₀"],
        ],
        col_widths=[0.28*inch, 0.85*inch, 1.1*inch, 1.7*inch, 2.57*inch]
    ),
    sp(10),
    info_box(
        "<b>Note on related phenomena:</b> <b>Melioration</b> is covered in spec #13 "
        "(Amelioration/Melioration — Herrnstein &amp; Vaughan 1980 used the terms "
        "interchangeably; phenomena.json exposes a 'melioration' alias pointing to the "
        "same event set). <b>Behavioral Momentum</b> is spec #12 (Nevin 1974 paradigm). "
        "Delay Discounting (#21) extends the choice/self-control module."
    ),
    sp(6),
    h2("Key Conceptual Contrasts"),
    make_table(
        ["Pair", "What the comparison isolates"],
        [
            ["MULT vs. MIX",   "Functional role of discriminative stimuli (SD vs. no SD with same schedules)"],
            ["CHAIN vs. TAND", "Conditioned reinforcement effect (SR at link transitions vs. no SR)"],
            ["ALT vs. CONJ",   "OR-logic vs. AND-logic compound; which requirement dominates rate"],
            ["CONC vs. ALT",   "Free simultaneous choice (CONC) vs. first-wins sequential race (ALT)"],
        ],
        col_widths=[1.5*inch, 5.0*inch]
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 6. LEVEL SPECIFICATIONS
# ═══════════════════════════════════════════════════════════
story += [
    section_header("6. Level Specifications"),
    sp(10),
    body(
        "Each of the 20 phenomena has a level spec file in "
        "<font name='Courier' size='9'>references/level_specs/</font>. "
        "All specs follow a standard template:"
    ),
    sp(6),
    make_table(
        ["Section", "Contents"],
        [
            ["Phenomenon",          "Theoretical background, key predictions, primary references"],
            ["Learning Objective",  "What participants should observe and be able to articulate"],
            ["Behavioral Target",   "Specific response, consequence, antecedent, and schedule parameters"],
            ["SMM2 Level Settings", "Game style, theme, filter, time limit, starting power-up"],
            ["Demo Level Design",   "ASCII layout diagram, mechanics used, instructor script notes"],
            ["Research Level Design","Participant procedure, contingency parameter tables, procedural notes"],
            ["Variables",           "IV table + DV table with companion app event codes"],
            ["Analysis Notes",      "Primary and secondary DVs, statistical models, expected results"],
            ["Observer Notes",      "IOA requirements, ambiguous code definitions, tie-breaking rules"],
            ["Replication Notes",   "Course ID slots, calibration steps, sequence specifications"],
            ["Key References",      "APA-format citations for the primary empirical/theoretical sources"],
        ],
        col_widths=[1.8*inch, 4.7*inch]
    ),
    sp(10),
    h2("parameters.json"),
    body(
        "All IV parameters are stored in machine-readable form in "
        "<font name='Courier' size='9'>references/level_specs/parameters.json</font>. "
        "Analysis notebooks load this file to auto-label conditions without hardcoding. "
        "Fields include schedule values, FR/FI requirements, VI sequences, path lengths, "
        "COD values, expected predictions, and model equations."
    ),
    sp(6),
    info_box(
        "Example — amelioration VI-VI sequence (exact replication parameter): "
        "Left VI3s: [1,4,2,5,3,4,1,6,2,4] s | Right VI9s: [5,12,7,11,9,8,10,13,6,9] s. "
        "These sequences are fixed across all sessions for replication fidelity."
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 7. BUILDER'S GUIDES
# ═══════════════════════════════════════════════════════════
story += [
    section_header("7. SMM2 Builder's Guides"),
    sp(10),
    body(
        "Because SMM2 levels must be built manually inside the Nintendo Switch game editor, "
        "the platform includes tile-by-tile construction guides for every level. "
        "Guides are in <font name='Courier' size='9'>references/builder_guides/</font> "
        "(23 files: 1 overview + 20 demo guides + 2 research level guides for phenomenon 1)."
    ),
    sp(8),
    h2("Coordinate System"),
    body(
        "<b>x</b> = tile columns from the left edge (1-based). "
        "<b>y</b> = tile rows from the ground (1 = ground row, increasing upward). "
        "Example: a pipe at (12, 1) sits in column 12, on the ground."
    ),
    sp(6),
    h2("Tile Shorthand"),
    make_table(
        ["Symbol", "Object", "Symbol", "Object"],
        [
            ["[?]", "? Block (coin or power-up)",   "[!]", "Used/Empty Block (no coin)"],
            ["[B]", "Brick Block",                   "[H]", "Hard Block"],
            ["[G]", "Ground tile",                   "[$]", "Coin on ground"],
            ["[P]", "Pipe (upward)",                 "[SW]", "ON/OFF Switch block"],
            ["[PS]","P-Switch",                      "[NB]", "Note Block"],
            ["[F]", "Goal Pole",                     "[CP]", "Checkpoint Flag"],
            ["[Gm]","Goomba",                        "[Bz]", "Buzzy Beetle"],
        ],
        col_widths=[0.6*inch, 2.65*inch, 0.6*inch, 2.65*inch]
    ),
    sp(8),
    h2("Guide Structure (each file)"),
    make_table(
        ["Section", "Contents"],
        [
            ["Course Settings",   "Game style, theme, filter, time limit, power-up, level length"],
            ["Level Overview",    "ASCII-art zone diagram; number of separate courses needed"],
            ["Tile-by-Tile",      "Exact x,y coordinates for every block, pipe, coin, and enemy"],
            ["Block State",       "Active [?] vs. pre-emptied [!]; contents of each ? block"],
            ["Mechanics Notes",   "P-switch timing, loop pipe connections, VI approximation method"],
            ["Instructor Script", "Narration cues tied to specific in-game moments"],
            ["Verification",      "Checklist before uploading; test-play requirements"],
        ],
        col_widths=[1.5*inch, 5.0*inch]
    ),
    sp(10),
    h2("SMM2 Mechanic Reference for Key Schedule Approximations"),
    make_table(
        ["Schedule Type", "SMM2 Implementation"],
        [
            ["FR n",        "n-1 empty [!] blocks followed by 1 active [?] coin block"],
            ["VR (mean n)", "Preset sequence of [!]/[?] blocks per ratio values from parameters.json"],
            ["FI t seconds","Ground coin at tile distance = t × 1.33 tiles/s from trial start"],
            ["VI t seconds","Observer opens P-switch gate per preset interval sequence; or ground coins at interval-distance tiles"],
            ["COD n responses", "n empty [!] blocks at path entry (must be hit before coin accessible)"],
            ["Conditioned SR (CHAIN)", "P-switch activates blue coin trail — visual SD2 onset is the CR"],
            ["Free disruptor", "Ground coins ([$]) at y=1 — Mario collects passively by walking"],
            ["Concurrent paths","Symmetric fork with loop pipes; equal path length for VI; unequal for FR (natural travel cost)"],
        ],
        col_widths=[1.8*inch, 4.7*inch]
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 8. ANALYSIS NOTEBOOKS
# ═══════════════════════════════════════════════════════════
story += [
    section_header("8. Analysis Notebooks"),
    sp(10),
    body(
        "Nine Jupyter notebooks cover the full analysis pipeline from raw CSV to "
        "publication-ready figures. All notebooks are in "
        "<font name='Courier' size='9'>smm2_behavioral_research_platform/notebooks/</font>."
    ),
    sp(8),
    make_table(
        ["Notebook", "Analyses"],
        [
            ["00 — Data Pipeline",
             "Load raw CSVs; validate schema; merge with parameters.json; compute elapsed_s; save parquet"],
            ["01 — Rate Analysis",
             "Cumulative response records; post-SR pause by schedule; extinction burst detection; IRT distributions"],
            ["02 — Discrimination / Generalization",
             "Discrimination index (R1-R2)/(R1+R2); generalization gradient; Pearson r with similarity scores"],
            ["03 — Matching Law",
             "B1/B2 and R1/R2 per condition; OLS GML fit; sensitivity a and bias b; undermatching test"],
            ["04 — Explore / Exploit",
             "Exploration rate by run block; ε-greedy MLE; softmax/temperature MLE; directed vs. random exploration proxy (Wilson et al. 2021)"],
            ["05 — Sequential Behavior",
             "Shaping: trials-to-criterion per step; backslide frequency. Chaining: link completion rate; inter-link latency"],
            ["06 — IOA",
             "Total count IOA; 10-second time-window IOA; flags sessions <80%; exports ioa_results.csv"],
            ["07 — Behavioral Momentum / Amelioration",
             "Resistance-to-change ratio; Nevin (1992) model fit; molar GML by schedule type; local-rate melioration test"],
            ["08 — Compound Schedules",
             "CONC: GML fit + COD switching. ALT: dominant component. CONJ: IRI + binding constraint. "
             "MULT: behavioral contrast ABA. MIX vs. MULT: EXT-component rate. CHAIN: goal gradient IRT. "
             "TAND vs. CHAIN: post-component pause"],
            ["09 — Delay Discounting",
             "P(LL) by delay condition; hyperbolic vs. exponential curve_fit; individual k "
             "and D₅₀ extraction; group curve overlay; optional preference reversal test"],
        ],
        col_widths=[1.8*inch, 4.7*inch]
    ),
    sp(10),
    h2("Key Statistical Methods"),
    make_table(
        ["Method", "Used For", "Notebook"],
        [
            ["OLS linear regression",         "GML: log(B1/B2) ~ log(R1/R2)", "03, 07, 08"],
            ["scipy.optimize.minimize (MLE)", "ε-greedy ε; softmax temperature; Nevin b,a", "04, 07"],
            ["Pearson correlation",            "Generalization gradient similarity", "02"],
            ["Paired t-test",                  "Resistance ratio rich vs. lean; MIX vs. MULT EXT rate", "07, 08"],
            ["Rolling window (5 choices)",     "Local reinforcement rate (amelioration/melioration)", "07, 08"],
            ["Regression on sequence #",       "Within-session learning in MIX; extinction decay", "08, 01"],
        ],
        col_widths=[2.0*inch, 2.8*inch, 1.7*inch]
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 9. IOA AND REPLICATION
# ═══════════════════════════════════════════════════════════
story += [
    section_header("9. Interobserver Agreement & Replication"),
    sp(10),
    h2("IOA Methods"),
    make_table(
        ["Method", "Formula", "Threshold", "Used For"],
        [
            ["Total count IOA",    "smaller / larger × 100",    "≥80%",  "Frequency events (RESPONSE, LEFT/RIGHT)"],
            ["Time-window IOA",    "agreements / (agree+disagree) per 10-s bin", "≥80%", "Timed events (PAUSE, EXCLUSIVE)"],
            ["Exact agreement",    "Simultaneous identical codes", "100%", "Discrete unambiguous events (link entries, SD transitions)"],
            ["±2-s window",        "Codes within 2 s counted as agreed", "≥80%", "Observer-timed FI events"],
        ],
        col_widths=[1.4*inch, 2.3*inch, 0.8*inch, 2.0*inch]
    ),
    sp(8),
    h2("Pre-Session Replication Checklist"),
    body("From INDEX.md — required before each data collection session:"),
    sp(4),
    *[bullet(b) for b in [
        "Level built and test-played by a naive observer (not the builder)",
        "Course ID recorded in INDEX.md",
        "Block/coin placement verified with stopwatch (interval schedules)",
        "Starting power-up state confirmed at each checkpoint",
        "Observer trained to IOA criterion (≥80% agreement on pilot coding session)",
        "Companion app phenomena.json verified to match current level design",
        "Screen recording software running and timestamp-synced with wall_time",
        "Participant instructions script printed and available",
        "VI sequences confirmed identical to parameters.json preset values",
        "Path lengths equal in concurrent VI-VI conditions (no travel-time bias)",
    ]],
    sp(10),
    h2("Walk-Speed Calibration"),
    body(
        "Normal Mario walk speed ≈ <b>1.33 tiles/second</b> (verified: 10 tiles in ~7.5 s). "
        "FI interval tile distances in builder's guides use this constant. "
        "Calibrate at the start of each session by timing Mario walking 10 tiles "
        "in the approach corridor. If speed deviates >10%, adjust tile distances."
    ),
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 10. THEORETICAL FOUNDATIONS
# ═══════════════════════════════════════════════════════════
story += [
    section_header("10. Theoretical Foundations & Key Equations"),
    sp(10),
    h2("Generalized Matching Law (GML)"),
    body("Baum (1974). Applied in Matching Law (10), Amelioration (13), and Concurrent Schedules (14)."),
    info_box("log(B₁/B₂) = a · log(R₁/R₂) + log(b)   where: a = sensitivity (slope), b = bias (intercept exponentiated)"),
    sp(4),
    body("Strict matching: a = 1, b = 1. Undermatching: a < 1. Overmatching: a > 1. Bias: b ≠ 1."),
    sp(8),
    h2("Nevin (1992) Behavioral Momentum Model"),
    body("Applied in Behavioral Momentum (12)."),
    info_box("log(B_d / B_0) = −b · d · R^(−a)   where: B_d = post-disruption rate, B_0 = baseline rate, d = disruptor magnitude, R = reinforcement rate, a = sensitivity to reinforcement, b = disruptor efficacy"),
    sp(8),
    h2("Melioration / Local Rate Test"),
    body("Herrnstein & Vaughan (1980). Applied in Amelioration (13) and Concurrent Schedules (14)."),
    info_box("P(switch to left | local_rate_left > local_rate_right) >> P(switch to left | local_rate_left < local_rate_right)   Local rate = rolling 5-choice window reinforcers per choice"),
    sp(8),
    h2("Explore/Exploit Models"),
    body("Applied in Explore/Exploit (11)."),
    make_table(
        ["Model", "Policy", "Free Parameter"],
        [
            ["ε-greedy",  "Exploit with prob 1−ε; explore randomly with prob ε", "ε ∈ [0,1]"],
            ["Softmax",   "P(arm i) ∝ exp(Q_i / τ)", "Temperature τ > 0"],
            ["UCB1",      "Choose argmax[Q_i + c√(ln n / n_i)]", "Confidence c > 0"],
        ],
        col_widths=[1.2*inch, 3.3*inch, 2.0*inch]
    ),
    sp(8),
    h2("Hyperbolic Discounting (Mazur 1987)"),
    body("Applied in Delay Discounting (21)."),
    info_box("V = A / (1 + k · D)    (hyperbolic, fits better than exponential in most studies) "
             "Indifference: k = (A_LL/A_SS − 1) / D₅₀.  For A_LL=5, A_SS=1: k = 4/D₅₀. "
             "Higher k = steeper discounting = more 'impulsive.' Signature prediction: "
             "preference reversal at near-vs-distant delay pairs with equal delay gap."),
    sp(8),
    h2("Key References"),
    *[body(ref) for ref in [
        "Baum, W. M. (1974). On two types of deviation from the matching law. <i>JEAB, 22</i>, 231–242.",
        "Ferster, C. B., &amp; Skinner, B. F. (1957). <i>Schedules of Reinforcement</i>. Appleton-Century-Crofts.",
        "Herrnstein, R. J. (1961). Relative and absolute strength of response as a function of frequency of reinforcement. <i>JEAB, 4</i>, 267–272.",
        "Herrnstein, R. J., &amp; Vaughan, W. (1980). Melioration and behavioral allocation. In <i>Limits to Action</i> (pp. 143–176).",
        "Nevin, J. A. (1974). Response strength in multiple schedules. <i>JEAB, 21</i>, 389–408.",
        "Nevin, J. A., &amp; Grace, R. C. (2000). Behavioral momentum and the law of effect. <i>BBS, 23</i>, 73–90.",
        "Reynolds, G. S. (1961). Behavioral contrast. <i>JEAB, 4</i>, 57–71.",
        "Kelleher, R. T., &amp; Gollub, L. R. (1962). A review of positive conditioned reinforcement. <i>JEAB, 5</i>, 543–597.",
        "Wilson, R. C., et al. (2021). Balancing exploration and exploitation with information and randomization. <i>Current Opinion in Behavioral Sciences, 38</i>, 49–56.",
        "Mazur, J. E. (1987). An adjusting procedure for studying delayed reinforcement. In Commons et al. (Eds.), <i>Quantitative Analyses of Behavior: Vol. 5</i> (pp. 55–73). Erlbaum.",
        "Rachlin, H., &amp; Green, L. (1972). Commitment, choice, and self-control. <i>JEAB, 17</i>, 15–22.",
        "Ainslie, G. (1975). Specious reward: A behavioral theory of impulsiveness. <i>Psychological Bulletin, 82</i>, 463–496.",
    ]],
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 11. QUICK-START GUIDE
# ═══════════════════════════════════════════════════════════
story += [
    section_header("11. Quick-Start Guide"),
    sp(10),
    h2("A. Build a Level"),
    *[bullet(b) for b in [
        "Open the builder's guide for the phenomenon (references/builder_guides/##_demo_*.md)",
        "Create a new course in SMM2 → Course Maker → New Course",
        "Set Course Settings exactly as listed in the guide header",
        "Place tiles following the tile-by-tile table (x,y coordinates)",
        "Test-play the level yourself; then have a naive observer test it",
        "Upload → record the course ID in references/level_specs/INDEX.md",
    ]],
    sp(8),
    h2("B. Run a Session"),
    *[bullet(b) for b in [
        "Start screen recording software (e.g., OBS) and note the start wall_time",
        "Launch companion app: python -m smm2_behavioral_research_platform",
        "SetupFrame: enter Participant ID, Observer ID, Level ID, select Phenomenon",
        "Press Start Recording — this starts the elapsed_s timer",
        "Code events in real time using keyboard hotkeys or on-screen buttons",
        "Use the Note field for any ambiguous events",
        "Press Stop → Review → Export CSV → file saved to data/raw/",
    ]],
    sp(8),
    h2("C. Analyze Data"),
    *[bullet(b) for b in [
        "Place raw CSV files in data/raw/",
        "Run notebook 00_data_pipeline.ipynb — produces data/processed/*.parquet",
        "Run notebook 06_ioa.ipynb — verify IOA ≥80% before proceeding",
        "Run the phenomenon-specific notebook (01–08) for analysis and figures",
        "Figures saved to reports/figures/",
    ]],
    sp(8),
    h2("D. Add a New Phenomenon"),
    *[bullet(b) for b in [
        "Copy TEMPLATE.md from references/level_specs/ and fill in all sections",
        "Add the phenomenon key and event list to phenomena.json",
        "Add machine-readable parameters to parameters.json",
        "Add a row to INDEX.md (curriculum table + CSV key table)",
        "Write a builder's guide in references/builder_guides/",
        "Add analysis code to the appropriate notebook (or create a new one)",
    ]],
    sp(10),
    PageBreak(),
]

# ═══════════════════════════════════════════════════════════
# 12. COMPLETE PHENOMENA REFERENCE
# ═══════════════════════════════════════════════════════════
story += [
    section_header("12. Complete Phenomena Reference"),
    sp(10),
    make_table(
        ["#", "CSV Key", "Label", "Spec File", "Notebook"],
        [
            ["1",  "positive_reinforcement",  "Positive Reinforcement",           "01_positive_reinforcement.md",   "01"],
            ["2",  "reinforcement_schedules",  "Reinforcement Schedules",          "03_reinforcement_schedules.md",  "01"],
            ["3",  "extinction",               "Extinction",                       "04_extinction.md",               "01"],
            ["4",  "negative_reinforcement",   "Negative Reinforcement",           "02_negative_reinforcement.md",   "01"],
            ["5",  "punishment",               "Punishment",                       "08_punishment.md",               "01"],
            ["6",  "shaping",                  "Shaping",                          "05_shaping.md",                  "05"],
            ["7",  "stimulus_control",         "Stimulus Control / Discrimination","06_stimulus_control.md",         "02"],
            ["8",  "generalization",           "Generalization",                   "07_generalization.md",           "02"],
            ["9",  "chaining",                 "Behavioral Chaining",              "09_chaining.md",                 "05"],
            ["10", "matching_law",             "Matching Law",                     "10_matching_law.md",             "03"],
            ["11", "explore_exploit",          "Exploration vs. Exploitation",     "11_explore_exploit.md",          "04"],
            ["12", "behavioral_momentum",      "Behavioral Momentum",              "12_behavioral_momentum.md",      "07"],
            ["13", "amelioration",             "Amelioration",                     "13_amelioration.md",             "07"],
            ["14", "concurrent_schedules",     "Concurrent Schedules (CONC)",      "14_concurrent_schedules.md",     "08"],
            ["15", "alternative_schedules",    "Alternative Schedules (ALT)",      "15_alternative_schedules.md",    "08"],
            ["16", "conjunctive_schedules",    "Conjunctive Schedules (CONJ)",     "16_conjunctive_schedules.md",    "08"],
            ["17", "multiple_schedules",       "Multiple Schedules (MULT)",        "17_multiple_schedules.md",       "08"],
            ["18", "mixed_schedules",          "Mixed Schedules (MIX)",            "18_mixed_schedules.md",          "08"],
            ["19", "chained_schedules",        "Chained Schedules (CHAIN)",        "19_chained_schedules.md",        "08"],
            ["20", "tandem_schedules",         "Tandem Schedules (TAND)",          "20_tandem_schedules.md",         "08"],
            ["21", "delay_discounting",        "Delay Discounting",                "21_delay_discounting.md",        "09"],
            ["—",  "melioration",              "(alias → amelioration, #13)",      "13_amelioration.md",             "07"],
        ],
        col_widths=[0.28*inch, 1.72*inch, 1.82*inch, 1.95*inch, 0.73*inch]
    ),
    sp(14),
    HRFlowable(width="100%", thickness=1.5, color=RED),
    sp(8),
    Paragraph("SMM2 Behavioral Research Platform — End of Document", S_CAPTION),
    Paragraph("Generated programmatically from project source files | reportlab", S_CAPTION),
]

# ═══════════════════════════════════════════════════════════
# BUILD PDF
# ═══════════════════════════════════════════════════════════
def on_page(canvas, doc):
    canvas.saveState()
    # Footer
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(0.75*inch, 0.5*inch, "SMM2 Behavioral Research Platform")
    canvas.drawRightString(7.75*inch, 0.5*inch, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
    canvas.setLineWidth(0.5)
    canvas.line(0.75*inch, 0.62*inch, 7.75*inch, 0.62*inch)
    canvas.restoreState()

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=0.75*inch,
    rightMargin=0.75*inch,
    topMargin=0.75*inch,
    bottomMargin=0.75*inch,
    title="SMM2 Behavioral Research Platform — Project Overview",
    author="ABA 761 — Endicott College",
    subject="Behavioral research platform using Super Mario Maker 2",
)

doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"PDF written → {OUT}")
