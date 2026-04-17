# Builder's Guide: Delay Discounting — DEMO Level

**Curriculum position**: 21 of 21
**Phenomenon**: Hyperbolic delay discounting (Mazur 1987) — 5 delay conditions
**Audience**: Instructor demonstration + participant research

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None (Small Mario) |
| Level Length | ~100 tiles (varies by condition — see table) |

---

## Five Separate Courses (one per LL delay condition)

| Course | Condition | LL delay target | LL corridor length |
|---|---|---|---|
| Course A | D_3s  |  ~3 s |   4 tiles |
| Course B | D_10s | ~10 s |  13 tiles |
| Course C | D_20s | ~20 s |  27 tiles |
| Course D | D_40s | ~40 s |  53 tiles |
| Course E | D_60s | ~60 s |  80 tiles |

Walk-speed assumption: **1.33 tiles/second** (calibrate at session start).

Total level width ≈ 25 + LL corridor + 10 (end/loop). For Course E: ~115 tiles.

---

## Shared Fork Structure (all 5 courses — build once, clone 4 times)

### Approach Corridor (x=1–10)
- Ground: y=1, x=1–10
- Mario walks freely to the fork; no blocks, no obstacles

### Fork Junction (x=11)
- Hard block divider [H] at x=11, y=1–4 (4-high wall)
- Upper gap (y=5): entry to LL path (right)
- Lower gap (y=1): entry to SS path (left)

> Design note: SS on the LEFT (lower path, immediate access) is counterintuitive
> since "later" usually = far right. This guide places SS on the LEFT so participants
> commit via a downward/immediate visual; the LL path extends upward-and-right
> (longer). Flip L/R if preferred — just mirror the event codes in companion app.

### SS Path (Left, Lower) — x=11–20 (fixed, all courses)
- Ground: y=1, x=11–20
- Open corridor y=1–3 (walk-in, no jump needed)
- **1 ? coin block** at y=3, x=13 — delivers 1 coin
- Post-coin corridor x=14–20 (6 tiles to loop pipe)
- Loop pipe entry: x=20, y=1 → sub-area → return to x=1

**SS delay**: ~1 s (Mario walks from fork to coin in ≈1.5 tiles = ~1 s)

### LL Path (Right, Upper) — x=11 through (variable end)
- Upper corridor: y=5–7, 3 tiles tall (ceiling = Hard blocks at y=8)
- Entry: gap at x=11, y=5 (Mario jumps up from x=10)
- **Delay corridor**: purely flat walk, NO obstacles, NO coins, NO enemies
  - Length determined by condition (4, 13, 27, 53, or 80 tiles)
- **5 coin blocks clustered at end of delay corridor**:
  Place 5 consecutive [?] blocks at y=6 (each containing 1 coin)
  — use one "coin shower" visual or 5 separate ? blocks in a row
- Post-coin corridor (~5 tiles) → Loop pipe exit

### Loop Pipe Return
Both SS and LL exit pipes → shared sub-area → single pipe back to main area x=1.
Each return = 1 new trial.

---

## Condition-Specific Measurements

### Course A (LL = ~3 s, 4-tile corridor)
- LL path: fork (x=11) → jump up → walk 4 tiles (x=12–15) → 5 coin blocks at x=16–20
- Total LL path length: ~10 tiles
- Level total width: ~35 tiles

### Course B (LL = ~10 s, 13-tile corridor)
- LL delay corridor: x=12–24 (13 tiles of flat walking)
- 5 coin blocks at x=25–29
- Level total: ~50 tiles

### Course C (LL = ~20 s, 27-tile corridor)
- LL delay corridor: x=12–38
- 5 coin blocks at x=39–43
- Level total: ~70 tiles

### Course D (LL = ~40 s, 53-tile corridor)
- LL delay corridor: x=12–64
- 5 coin blocks at x=65–69
- Level total: ~95 tiles

### Course E (LL = ~60 s, 80-tile corridor)
- LL delay corridor: x=12–91
- 5 coin blocks at x=92–96
- Level total: ~115 tiles

> The LL corridor **MUST be a featureless straight walk** — no enemies, no optional
> coins, no gaps. The delay must be purely temporal, not effortful. Any added
> obstacle makes the delay confounded with response effort.

---

## Goal Pole Placement

Every course needs a goal pole to formally "end" each session, but participants
loop indefinitely during the 20 trials. Place goal pole in an inaccessible
sub-area (e.g., behind a wall accessible only after 20 trials — not necessary
for session logistics). **Practical approach**: no goal pole; observer ends session
after 20 choices via companion app Stop button.

Alternatively: Place goal pole at the very end of the LL path (after the 5 coin
blocks) so participants who choose LL enough times eventually reach it. But this
confounds trial count with ending criterion. Recommendation: omit goal pole;
session ends on observer command after trial 20.

---

## Instructor Demonstration Script

### Demo Walk-through — Show 4 conditions in sequence

**Course A (3 s LL)**:
"Two paths. Left: 1 coin right here. Right: 5 coins but I walk for 3 seconds.
The wait is nothing — I pick right every time."
Make 5 choices, all LL. "5 coins × 5 = 25 coins. Easy."

**Course C (20 s LL)**:
"Now the wait is 20 seconds. Still 5 coins vs. 1 coin."
Mix choices: 3 LL, 2 SS. "I'm starting to hesitate. Sometimes the wait feels
too long. That's discounting — the 5 coins are worth less to me when they're further away."

**Course E (60 s LL)**:
"Now 60 seconds. A full minute of walking."
Mostly SS choices: 4 SS, 1 LL. "I keep picking left — 1 coin NOW beats 5 coins
a minute from now. The delayed reward has been so heavily discounted that it's
worth less than the immediate one."

**Debrief + equation**:
"The value V of a delayed reward = A / (1 + k × D). A is the amount, D is the delay,
k is my personal discount rate. Higher k = I discount more steeply = more impulsive.
From my choices, we can estimate my k by finding the delay at which I'm indifferent —
where I pick each path 50% of the time. For 5-coin LL vs. 1-coin SS, that indifference
delay D₅₀ satisfies: k = 4 / D₅₀."

### Preference Reversal (optional, advanced demo)

If time permits, demonstrate preference reversal with a custom course:
- SS = 1 coin at 30 s delay (30-tile corridor on left)
- LL = 5 coins at 60 s delay (60-tile corridor on right)
- Same 30-s gap as the near-pair, but both pushed 29 s into the future
- Prediction: participant now picks LL (hyperbolic's signature prediction)

This requires one additional course build. Optional for demo.

---

## Observer Setup

Observer codes at each fork choice:
- `SS_CHOICE` (key: s) — Mario enters left path
- `LL_CHOICE` (key: l) — Mario enters right path
- `SS_SR` (key: a) — when Mario collects the 1 SS coin
- `LL_SR` (key: d) — when Mario collects the final LL coin (5th one)
- `ABANDON_LL` (key: x) — if Mario enters LL path but reverses/retreats before coins
- `WAIT_PAUSE` (key: p) — if Mario stops walking in LL corridor for ≥3 s
- `IMPULSIVE_REVERSAL` (key: r) — if participant switches from ≥3 consecutive
  LL-choices to SS within the same session (within-session discount shift)

After each session, compute P(LL) = count(LL_CHOICE) / 20. Record in session CSV.
Cross-session: fit hyperbolic model via notebook 09.

---

## Verification Checklist
- [ ] 5 separate courses built (Conditions A–E) with exact LL corridor lengths
- [ ] SS path: 1 coin at x=13, y=3 (fixed across all courses)
- [ ] LL path: 5 consecutive ? coin blocks (each yields 1 coin) at corridor end
- [ ] LL corridor contains NO enemies, NO optional coins, NO gaps (pure temporal delay)
- [ ] Walk-speed calibration performed (10 tiles in ~7.5 s)
- [ ] Loop pipes return Mario to approach corridor (x=1)
- [ ] No time limit on any course
- [ ] All 5 course IDs recorded in INDEX.md with delay-condition labels
- [ ] Test-play: confirm Mario can walk LL corridor without error
- [ ] Test-play: time the 60-s LL corridor — should feel like a genuine wait
