# Builder's Guide: Punishment — DEMO Level

**Curriculum position**: 5 of 20
**Phenomenon**: Positive Punishment — ABAB reversal with Buzzy Beetle fork
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | **Super Mario** |
| Level Length | ~200 tiles (loop) |

---

## Level Overview

A fork with two paths:
- **Left path (punished)**: High coin density (3 coins per trip) + Buzzy Beetle
- **Right path (safe)**: Low coin density (1 coin per trip) + no beetle

The ABAB reversal is implemented across 4 course uploads:
- **A1**: Buzzy Beetle on LEFT path (punishment present)
- **B1**: No Buzzy Beetle on either path (punishment absent)
- **A2**: Buzzy Beetle returns to LEFT (punishment present)
- **B2**: No Buzzy Beetle again (punishment absent)

> Build two courses: one with beetle (A phases) and one without (B phases).

---

## Fork Layout (same for all phases)

### Ground and Structure (x=1 to 100)
- Ground: y=1, x=1–100
- Approach corridor: x=1–20 (flat ground, Mario walks in)
- Fork point: x=21 — Hard block wall divides path into upper (left) and lower (right)
  - Upper path (left): y=4–6, x=21–70 (3 tiles tall, above divider)
  - Lower path (right): y=1–3, x=21–70 (3 tiles below divider)
  - Divider: Hard blocks [H] at y=4, x=21–70 (ceiling of lower path / floor of upper path)
- Paths rejoin at x=71 → loop pipe returns Mario to start (x=1) via sub-area pipe

### LEFT Path (Upper) — Coin-Rich, Punished
Upper path entrance: gap at x=21, y=5 (Mario jumps up to enter)

**Coins** on left path (3 coins per trip):
- [?] blocks at x=30, 45, 60 (y=6) → each contains 1 coin

**Buzzy Beetle** (A phases only):
- Place Buzzy Beetle at x=40, y=5 (middle of left path)
- Patrol range: 3 tiles. No wings.
- Contact: Mario loses Super state (downsizes). This is the punisher.

**Exit**: Pipe at x=69, y=5 → loops to Sub-area entry → main area start.

### RIGHT Path (Lower) — Coin-Lean, Safe
Lower path entrance: ground-level at x=21, y=1 (Mario walks in without jumping)

**Coins** on right path (1 coin per trip):
- [?] block at x=45, y=3 → 1 coin

**No Buzzy Beetle** on right path in any phase.

**Exit**: Pipe at x=69, y=1 → loops to Sub-area entry → main area start.

### Loop Return
Sub-area (1 tile): place an exit pipe that sends Mario back to x=1 of main area.
Each choice = 1 trial. Observer codes LEFT or RIGHT at the fork.

---

## ABAB Phases — What Changes Between Courses

| Phase | Left path Beetle | Left coins | Right coins |
|---|---|---|---|
| A1 (Course 1) | YES at x=40 | 3 | 1 |
| B1 (Course 2) | NO | 3 | 1 |
| A2 (Course 3) | YES at x=40 | 3 | 1 |
| B2 (Course 4) | NO | 3 | 1 |

**Only the Buzzy Beetle changes.** Coin density stays constant throughout.
This isolates punishment as the independent variable.

---

## Power-Up Recovery

Place a **Mushroom** block [?] hidden (invisible block — long-press → invisible option)
at x=10, y=3 (approach corridor) so Mario can restore Super state if he's been hit.
This ensures he starts each trial in Super state.

---

## Instructor Script Notes

**Phase A1 (Beetle on Left)**:
"Two paths — left has 3 coins, right has only 1. Which do I take?"
Go left. Get hit by beetle. "Ouch — I lost my power. The left path punished me."
Go right. "Safe, but only 1 coin." Repeat 10 choices. "Notice I start choosing
right more — punishment suppresses behavior."

**Phase B1 (No Beetle)**:
"Beetle is gone." Go left multiple times. "I go left every time — 3 coins is
better. When punishment stops, the behavior returns."

**Phase A2 and B2**: Repeat patterns. Demonstrate suppression returns/lifts with punisher.

**Debrief**: "Positive punishment = adding an aversive stimulus (beetle contact) after
a response (going left), which decreases the future probability of that response.
Behavior didn't disappear — it suppressed while the punisher was present."

---

## Verification Checklist
- [ ] Course starts as Super Mario
- [ ] Left path: 3 coin blocks, correct position
- [ ] Right path: 1 coin block, no beetle in any phase
- [ ] Phase A courses: Buzzy Beetle at x=40 of left path
- [ ] Phase B courses: Buzzy Beetle removed from left path
- [ ] Loop pipe returns Mario to fork start after each choice
- [ ] Hidden mushroom in approach corridor
- [ ] All 4 phase courses built and uploaded
- [ ] ABAB course IDs recorded in INDEX.md
- [ ] Test-played: verify beetle contact removes power-up
