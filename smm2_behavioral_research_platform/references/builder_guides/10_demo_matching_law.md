# Builder's Guide: Matching Law — DEMO Level

**Curriculum position**: 10 of 20
**Phenomenon**: Matching Law — Concurrent schedules with 5 coin-density conditions
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
| Level Length | Looped fork (~80 tiles per loop) |

---

## Level Overview

A symmetric looping fork. Mario repeatedly returns to the fork after each choice.
Observer codes LEFT or RIGHT at each choice. Run through 5 conditions (separate
uploads or sub-areas), each with a different left:right coin ratio.

| Condition | Left coins/trip | Right coins/trip | Ratio |
|---|---|---|---|
| A | 3 | 1 | 3:1 |
| B | 2 | 2 | 1:1 |
| C | 1 | 3 | 1:3 |
| D | 5 | 1 | 5:1 |
| E | 1 | 5 | 1:5 |

---

## Fork Layout (same structure for all conditions)

### Approach Corridor (x=1–15)
Ground: y=1, x=1–15. Flat. Mario walks to fork.

### Fork Junction (x=16)
At x=16: Hard block divider splits path:
- Upper gap at y=5 → left path
- Lower gap at y=1 → right path

### Left Path (Upper) — x=17 to 40
- Upper path: y=4–6 corridor, 3 tiles tall
- Entry: gap at x=16, y=5 (Mario jumps up to enter)
- [?] blocks with coins — quantity varies by condition (see below)
- Exit pipe at x=40, y=5 → Sub-area loop → Main area x=1

### Right Path (Lower) — x=17 to 40
- Lower path: y=1–3 corridor, 3 tiles tall
- Entry: ground level at x=16, y=1
- [?] blocks with coins — quantity varies by condition
- Exit pipe at x=40, y=1 → Sub-area loop → Main area x=1

### Path Length
Both paths: exactly **8 tiles long** (x=17–24 for blocks, x=25–40 for corridor).
**Equal travel time** for left and right — this eliminates travel-time bias on matching.

---

## Coin Placement by Condition

For each condition, adjust only the coin-bearing [?] blocks:

### Condition A (3:1) — Left=3, Right=1
Left path blocks at y=5: x=19 [?]coin, x=21 [?]coin, x=23 [?]coin
Right path blocks at y=2: x=21 [?]coin (only 1)

### Condition B (1:1) — Left=2, Right=2
Left: x=20 [?]coin, x=22 [?]coin
Right: x=20 [?]coin, x=22 [?]coin

### Condition C (1:3) — Left=1, Right=3
Left: x=21 [?]coin (only 1)
Right: x=19 [?]coin, x=21 [?]coin, x=23 [?]coin

### Condition D (5:1) — Left=5, Right=1
Left: x=18,19,20,21,22 [?]coin (5 consecutive blocks, each 1 coin)
Right: x=21 [?]coin (1 coin)

### Condition E (1:5) — Left=1, Right=5
Left: x=21 [?]coin (1 coin)
Right: x=18,19,20,21,22 [?]coin (5 consecutive)

---

## Loop Return Pipe

From left path exit pipe and right path exit pipe:
- Both connect to a single sub-area (1 tile area)
- Sub-area has one exit pipe that sends Mario back to main area x=5, y=1
- Mario walks from x=5 to fork at x=16 → makes next choice

Each trip through either path = 1 trial. 30 choices per session.

---

## Building 5 Condition Courses

Build one "base" course with the fork structure, loop pipe, and no coin blocks
(just used blocks in all positions). Then clone 5 times and add coins per
each condition's table above. Upload all 5 and record course IDs.

---

## Instructor Script Notes

1. Condition A (3:1): "Left pays 3 coins, right pays 1." Make choices.
   "I go left ~75% of the time. That matches — 3/(3+1) = 75%."
2. Condition B (1:1): "Equal payoff." Make choices. "I go about 50/50."
3. Condition D (5:1): "Strong preference for left." Make choices. "~83% left."
4. Debrief: "The proportion of my choices matched the proportion of reinforcement.
   B_L/(B_L+B_R) = R_L/(R_L+R_R). That's the Matching Law."

---

## Verification Checklist
- [ ] Both paths exactly 8 tiles (equal path length)
- [ ] 5 condition courses built with correct coin counts
- [ ] Loop pipe returns Mario to start after each choice (test in editor)
- [ ] Hard block divider forces unambiguous left vs. right choice
- [ ] All 5 course IDs recorded in INDEX.md (with conditions A–E labeled)
- [ ] Test-played: 10 choices in each condition, coins verified
