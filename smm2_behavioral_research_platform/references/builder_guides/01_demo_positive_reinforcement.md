# Builder's Guide: Positive Reinforcement — DEMO Level

**Curriculum position**: 1 of 13
**Phenomenon**: Positive Reinforcement (CRF → FR3 → VR3 → Extinction)
**Audience**: Instructor demonstration; students observe

---

## Course Settings

| Setting | Value |
|---|---|
| Game Style | Super Mario Bros. (SMB1) |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None (Small Mario) |
| Level Length | ~140 tiles wide |

---

## Level Overview

Four sequential zones separated by visible pipe "gates." Instructor walks
through each zone left-to-right explaining the schedule. A goal pole ends
the level after the Extinction zone.

```
[START] → [ZONE 1: CRF] → [PIPE GATE] → [ZONE 2: FR3] → [PIPE GATE]
        → [ZONE 3: VR3] → [PIPE GATE] → [ZONE 4: EXT] → [FINISH]
```

Total width: ~140 tiles. Each zone is ~25 tiles wide; pipe gates are 2 tiles.

---

## Tile-by-Tile Instructions

### Global Ground Layer (full level width)

Place solid ground tiles along the entire bottom row (y=1) from x=1 to x=140.
The editor fills ground automatically if you use the paintbrush in ground mode.

---

### Zone 1: CRF (Continuous Reinforcement — FR1)
**x = 1 to 25**

**Purpose**: Every block hit yields a coin. Establishes the behavior.

**Zone label sign** (x=3, y=4): Place a **Sign** tile; write "ZONE 1: CRF — Every block pays off!"

**? Blocks** — place at y=4 (4 tiles above ground), spaced 2 tiles apart:
- x=5 [?] coin
- x=7 [?] coin
- x=9 [?] coin
- x=11 [?] coin
- x=13 [?] coin
- x=15 [?] coin
- x=17 [?] coin
- x=19 [?] coin
- x=21 [?] coin
- x=23 [?] coin

Total: **10 ? blocks**, each gives 1 coin. **10 reinforcers available.**

**Pipe gate** (x=25–26):
- x=25, y=1–3: solid wall of Hard Blocks [H] (3 high)
- x=26, y=1–3: solid wall of Hard Blocks [H]
- x=25–26, y=4: open gap (walk-through height at y=4–5)
- Place a **one-way gate arrow** pointing right so Mario can only move forward.

---

### Zone 2: FR3 (Fixed Ratio 3)
**x = 27 to 55**

**Purpose**: Every 3rd block hit yields a coin. Two unreinforced blocks before each coin.

**Zone label sign** (x=29, y=4): "ZONE 2: FR3 — Every 3rd block pays off"

**Block sequence** — 9 blocks in groups of 3 (hit 1,2 = nothing; hit 3 = coin):
Place at y=4, x positions:

Group A (hits 1–3):
- x=31 [!] empty block (pre-loaded as used/empty — NO coin)
- x=33 [!] empty block
- x=35 [?] coin

Group B (hits 4–6):
- x=37 [!] empty block
- x=39 [!] empty block
- x=41 [?] coin

Group C (hits 7–9):
- x=43 [!] empty block
- x=45 [!] empty block
- x=47 [?] coin

> **SMM2 Tip**: Use a **Used Block** (`[!]` — the gray block) for the non-reinforced
> positions, not a ? block. This makes it clear visually that those blocks don't
> pay off, and prevents participants from hitting them multiple times hoping for a coin.
> Alternatively, use ? blocks that contain nothing (not supported directly in SMM2
> for coins; use Used Blocks instead).

One additional ? block at x=49 as a partial group demonstration (FR3 in progress):
- x=49 [!] empty
- x=51 [!] empty
(leave no coin at x=53 — partial ratio, no reinforcement)

**Pipe gate** at x=54–55 (same construction as Zone 1 gate).

---

### Zone 3: VR3 (Variable Ratio — mean 3)
**x = 56 to 86**

**Purpose**: Unpredictable reinforcement; average 1 coin per 3 hits.
Sequence used: [1,3,5,2,4,3,1,5,2,3] (from parameters.json)
— means: reinforce after 1 hit, then after 3 more, then after 5 more, etc.

**Zone label sign** (x=58, y=4): "ZONE 3: VR3 — Unpredictable! Average every 3rd"

Build the block sequence according to the VR sequence ratios.
Total blocks to place = sum of sequence = 1+3+5+2+4+3+1+5+2+3 = **29 blocks**
Reinforced blocks: **10** (one at the end of each ratio run)

Place blocks at y=4, x positions (consecutive, 2 tiles apart):

| Block # | x | Type | Ratio step |
|---|---|---|---|
| 1 | 60 | [?] coin | End of VR=1 (reinforce immediately) |
| 2 | 62 | [!] | VR=3, hit 1 |
| 3 | 64 | [!] | VR=3, hit 2 |
| 4 | 66 | [?] coin | VR=3, hit 3 (reinforce) |
| 5 | 68 | [!] | VR=5, hit 1 |
| 6 | 70 | [!] | VR=5, hit 2 |
| 7 | 72 | [!] | VR=5, hit 3 |
| 8 | 74 | [!] | VR=5, hit 4 |
| 9 | 76 | [?] coin | VR=5, hit 5 (reinforce) |
| 10 | 78 | [?] coin | End of VR=2: hit 1 reinforce (VR=2 means 1 unreinforced then coin; place [!] then [?]) |

> Adjust: VR=2 means 2 hits per reinforcer: one [!] at x=78, [?] at x=80.

Rebuild table correctly per sequence [1,3,5,2,4,3,1,5,2,3]:

| Ratio | # non-reinforced before coin | Blocks placed (x positions) |
|---|---|---|
| 1 | 0 | [?] at x=60 |
| 3 | 2 | [!] x=62, [!] x=64, [?] x=66 |
| 5 | 4 | [!] x=68, [!] x=70, [!] x=72, [!] x=74, [?] x=76 |
| 2 | 1 | [!] x=78, [?] x=80 |
| 4 | 3 | [!] x=82, [!] x=84, [!] x=86, [?] x=88 (adjust zone end) |
| 3 | 2 | [!] x=90, [!] x=92, [?] x=94 — push zone to x=95 |
| 1 | 0 | [?] x=96 |
| 5 | 4 | [!] x=98, [!] x=100, [!] x=102, [!] x=104, [?] x=106 |
| 2 | 1 | [!] x=108, [?] x=110 |
| 3 | 2 | [!] x=112, [!] x=114, [?] x=116 |

> **Zone 3 ends ~x=118.** Adjust level total width to ~145 tiles.

**Pipe gate** at x=118–119.

---

### Zone 4: Extinction
**x = 120 to 142**

**Purpose**: No coins delivered regardless of hitting. Demonstrates extinction burst and cessation.

**Zone label sign** (x=122, y=4): "ZONE 4: EXTINCTION — Blocks are empty"

Place **10 Used Blocks** [!] at y=4:
- x=124, 126, 128, 130, 132, 134, 136, 138, 140, 142

> All blocks are pre-emptied (used). No coins. Instructor keeps hitting to show
> extinction — eventually stops.

**Finish / Goal Pole**:
- x=144, y=1–8: Place goal pole (tall post with flag at top)
- Flag tile at y=9

---

## Instructor Notes for Demo

1. **Zone 1 (CRF)**: Hit every block. Say: *"Every single hit pays off — this is continuous reinforcement."*
2. **Zone 2 (FR3)**: Hit the sequence. Say: *"Two misses then a hit. The ratio is fixed at 3 responses per reward."*
3. **Zone 3 (VR3)**: Hit through the sequence. Say: *"Sometimes I get rewarded after 1 hit, sometimes after 5 — but on average, every 3 hits. Notice I keep going even when it takes longer."*
4. **Zone 4 (Extinction)**: Hit 4–5 blocks, pause, maybe hit 2 more, then stop. Say: *"The blocks are empty now. I tried harder at first — that's the extinction burst. Then I stopped — that's extinction."*

---

## Verification Checklist

- [ ] 10 ? blocks in Zone 1, all yield coins
- [ ] Zone 2 has exactly 2 empty blocks before each coin block (3 groups)
- [ ] Zone 3 blocks follow VR sequence [1,3,5,2,4,3,1,5,2,3] exactly
- [ ] Zone 4 has 10 used blocks, all pre-emptied (no coins)
- [ ] Pipe gates between all zones (one-way right)
- [ ] Goal pole at far right
- [ ] Test-played by naive observer before data collection
- [ ] Course ID recorded in INDEX.md after upload
