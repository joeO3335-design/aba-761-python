# Builder's Guide: Chained Schedules (CHAIN) — DEMO Level

**Curriculum position**: 19 of 20
**Phenomenon**: CHAIN FR FR — two-link chain with P-switch blue coins as conditioned reinforcer
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | ~60 tiles per chain trial |

---

## Three Courses

| Course | Condition | Link 1 | Link 2 | Signal at L1→L2 |
|---|---|---|---|---|
| Course 1 | CHAIN FR3 FR3 | FR3 | FR3 | Yes (blue coins) |
| Course 2 | CHAIN FR5 FR3 | FR5 | FR3 | Yes |
| Course 3 | CHAIN FR3 FR5 | FR3 | FR5 | Yes |

All 3 courses share identical geometry. Only block counts differ.

---

## Chain Layout (all courses)

### Trial structure: Loop
Each trial = 1 chain attempt. Loop pipe returns Mario to start after completing
or timing out. P-switch duration = 10 s.

### Ground and Structure (x=1–60)
Ground: y=1, x=1–60.

**Link 1 zone** (x=1–25):
- **P-switch** at x=3, y=2 (Mario jumps to hit it from below, or place on ground)
  When hit: blue coins appear on ground (positions set below). This IS the conditioned SR (SD2 onset).
- **Link 1 FR blocks** at y=4:
  - Course 1 (FR3): [!] x=6, [!] x=9, [!] x=12 (3 blocks; none yield coins individually)
  - Course 2 (FR5): [!] x=6, [!] x=8, [!] x=10, [!] x=12, [!] x=14
  - Course 3 (FR3): same as Course 1
  > Observer counts hits and codes L1_RESP for each. L1_SR coded when blue coins appear (P-switch activates).

**Blue coins** (appear when P-switch active):
- Ground coins at y=1: x=18, 20, 22, 24 — these appear in blue when P-switch is on
- These coins form the visual SD2 (conditioned reinforcer marking Link 2 entry)

> **Important**: P-switch is hit at x=3 FIRST, starting the 10-second clock.
> THEN Mario hits the FR blocks (x=6–14). Then blue coins appear at x=18–24.
> Mario must complete FR in Link 1 before collecting blue coins and entering Link 2.
> The blue coins appear immediately when P-switch is hit — they don't wait for FR completion.
> This means the conditioned SR (blue trail) IS the signal for Link 2 availability,
> but Mario must have already met FR1 to actually collect the Link 2 reinforcer.
>
> **Practical adjustment**: Put the P-switch at x=12 (after FR blocks at x=6,9,12).
> Mario hits FR blocks first, THEN hits P-switch. Blue coins appear. This ensures
> FR1 is met before SD2 (blue coins) appears.

**Revised Link 1 layout**:
- FR blocks: x=5 [!], x=8 [!], x=11 [!] (for FR3); Mario hits all 3.
- P-switch at x=14, y=2 (Mario jumps to hit after completing FR3 blocks).
- Blue coins appear at x=18,20,22,24 (SD2 onset = conditioned SR for Link 1 completion).

### Link 2 zone (x=26–52):
- **Link 2 FR blocks** at y=4:
  - Course 1 (FR3): [!] x=28, [!] x=31, [?] x=34 (3 blocks; COIN on 3rd)
  - Course 2 (FR3): same
  - Course 3 (FR5): [!] x=28, [!] x=31, [!] x=34, [!] x=37, [?] x=40
- After completing Link 2 FR: **Star** at x=46 (primary reinforcer)
  Place a Super Star item at x=46, y=2 in a [?] block.

### Loop return
- Exit pipe at x=53, y=1 → sub-area → return to x=1 for next trial.

### P-switch duration
10 seconds. Mario must complete Link 2 FR within 10 s of hitting the P-switch.
For FR3 Link 2: 3 blocks in 10 s = easily achievable.
For FR5 Link 2: 5 blocks in 10 s = achievable (~5–7 s at medium speed).

---

## Goal Gradient Demo

Show the goal gradient explicitly:
1. In Link 1 blocks, hit slowly (show lower motivation).
2. When blue coins appear (Link 2 entered), speed up.
3. Race to the star.
4. Say: "I went faster once I saw the blue trail — I was close to the reward."

---

## Instructor Script Notes

1. **CHAIN FR3 FR3**: "I need to hit 3 blocks in Link 1 — that unlocks Link 2."
   Hit 3 blocks slowly. P-switch activates. Blue coins appear.
   "Blue coins! That's my signal — I completed Link 1. And these blue coins
   are themselves a conditioned reinforcer — they mean the star is coming."
   Hit 3 blocks in Link 2 quickly. Collect star.

2. **CHAIN FR5 FR3**: "Longer Link 1 — 5 hits. But Link 2 is still easy."
   Show slower pace in Link 1, then acceleration in Link 2.
   "Goal gradient: I speed up near the terminal reinforcer."

3. **CHAIN FR3 FR5**: "Short Link 1, longer Link 2."
   Show that Link 2 takes more work even after the conditioned reinforcer.
   "The conditioned reinforcer motivates me to enter Link 2, but I still
   have to work harder to get the star."

4. Debrief: "Chained schedules create a motivational gradient.
   The blue trail ONLY functions as a reinforcer because of what follows it.
   Take away the star, and the blue trail loses its power."

---

## Verification Checklist
- [ ] P-switch placed AFTER FR blocks (Link 1 FR completed before P-switch hit)
- [ ] Blue coins appear at correct positions when P-switch is active (test in editor)
- [ ] Link 2 FR blocks have correct count per condition (FR3 or FR5)
- [ ] Super Star at end of Link 2 (terminal reinforcer)
- [ ] Loop pipe returns Mario after star collection
- [ ] P-switch duration (10 s) sufficient for Link 2 completion (test-play timed)
- [ ] All 3 course IDs in INDEX.md with CHAIN condition labels
