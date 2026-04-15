# Builder's Guide: Behavioral Momentum — DEMO Level

**Curriculum position**: 12 of 20
**Phenomenon**: Behavioral Momentum — Rich (CRF) vs. Lean (FR10) track + disruptor
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (rich track) / Underground sub-area (lean track) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | ~200 tiles per track |

---

## Important: Four Separate Courses Needed

| Course | Description |
|---|---|
| Course 1 | Rich track baseline (CRF, 30 blocks) |
| Course 2 | Lean track baseline (FR10, 30 blocks) |
| Course 3 | Rich track disruption + extinction (free SR + 15 used blocks) |
| Course 4 | Lean track disruption + extinction (free SR + 15 used blocks) |

---

## Course 1: Rich Track Baseline

**Theme**: Ground, daytime (bright sky)

### Layout (x=1–120)
Ground: y=1, x=1–120

**30 [?] blocks** at y=4, every 4 tiles:
x = 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65, 69, 73, 77, 81,
    85, 89, 93, 97, 101, 105, 109, 113, 117, 121

Each block yields 1 coin (CRF). **30 reinforcers**.

**Goal Pole**: x=123, y=1–9

---

## Course 2: Lean Track Baseline

**Theme**: **Underground** (via sub-area or by setting the main area to Underground theme)

### Layout (x=1–120)
Ground: y=1, x=1–120

**30 blocks** at y=4, every 4 tiles (same positions as Course 1).

**FR10 pattern**: Every 10th block is active [?] with coin; remaining 9 are empty [!].
- Active [?] blocks (3 reinforcers total from every 10): x=41, 81, 121
  Actually: 30 blocks / 10 = 3 reinforcers at blocks 10, 20, 30 in sequence.
  Block 10 = x=41 [?] coin; block 20 = x=81 [?] coin; block 30 = x=121 [?] coin.
  All others (x=5–37, x=45–77, x=85–117): [!] empty blocks.

> Wait — the spec says FR10 means 1 reinforcer per 10 responses (30 blocks → 3 reinforcers).
> To keep it visually consistent with Course 1, place [!] blocks everywhere except
> positions 10, 20, 30 in the block sequence.

**Goal Pole**: x=123, y=1–9

---

## Course 3: Rich Track — Disruption + Extinction

**Theme**: Ground, daytime (same as Course 1)

### Layout
First 30 tiles: **Disruption zone** — free coins on ground
- 5 ground coins ([$] tiles) at y=1: x=5, 10, 15, 20, 25
- No blocks to hit (Mario walks through, collects coins passively)
- Sign (demo): "Free coins — you don't have to do anything!"

x=30 to 90: **Extinction zone**
- 15 **empty [!] blocks** at y=4, spaced 4 tiles:
  x=30, 34, 38, 42, 46, 50, 54, 58, 62, 66, 70, 74, 78, 82, 86

**Goal Pole**: x=90, y=1–9

> Observer codes PERSIST for each hit on the 15 extinction blocks;
> SUPPRESS when Mario stops and pauses ≥3 s.

---

## Course 4: Lean Track — Disruption + Extinction

**Theme**: Underground (same as Course 2)

Identical structure to Course 3:
- 5 ground coins at x=5,10,15,20,25
- 15 empty [!] blocks at x=30,34,...,86
- Goal pole at x=90

---

## Instructor Script Notes

1. **Rich baseline**: "CRF — every hit pays. Rich history." Hit all 30 blocks.
   "Lots of reinforcement. This track has 'mass.'"
2. **Lean baseline**: "FR10 — only every 10th pays. Lean history."
   Hit blocks; few coins. "Low mass here."
3. **Rich disruption + extinction**: Walk through free coins. "Free coins!
   Now the blocks are empty. Watch how long I keep hitting anyway..."
   Hit extinction blocks: hit 10 out of 15. "I keep going — momentum!"
4. **Lean disruption + extinction**: Walk through free coins. "Same free coins.
   But now the lean track..." Hit extinction blocks: stop at 3–5.
   "I stop much faster — less momentum."
5. Debrief: "More reinforcement history = more mass = more momentum = more resistance
   to change. Same disruptor; different outcomes based on past reinforcement."

---

## Verification Checklist
- [ ] Course 1: 30 active [?] blocks on Ground/day theme
- [ ] Course 2: 27 empty + 3 active [?] blocks (at positions 10,20,30) on Underground theme
- [ ] Course 3: 5 ground coins (passive) + 15 empty blocks, Ground/day theme
- [ ] Course 4: 5 ground coins (passive) + 15 empty blocks, Underground theme
- [ ] All 4 course IDs recorded in INDEX.md
- [ ] Test-played: verify FR10 coins appear at correct block positions (10th, 20th, 30th)
- [ ] Test-played: verify ground coins in disruption zone are collectible by walking (not in blocks)
