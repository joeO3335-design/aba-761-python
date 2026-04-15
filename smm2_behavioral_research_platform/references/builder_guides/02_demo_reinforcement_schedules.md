# Builder's Guide: Reinforcement Schedules — DEMO Level

**Curriculum position**: 2 of 20
**Phenomenon**: Reinforcement Schedules (FR3 → VR3 → FI5s → VI5.5s)
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None (Small Mario) |
| Level Length | ~200 tiles |

---

## Level Overview

Four consecutive zones, each demonstrating one schedule. Separated by labeled
one-way pipe gates. Goal pole after Zone 4.

```
[START] → [FR3 ZONE] → [pipe] → [VR3 ZONE] → [pipe]
        → [FI5 ZONE] → [pipe] → [VI5.5 ZONE] → [FINISH]
```

---

## Zone 1: FR3 (Fixed Ratio 3) — x=1 to 40

**Zone sign** (x=3, y=4): "FR3 — Hit every 3rd block"

Place groups of 3 at y=4. Pattern: [!][!][?] repeating.

| Group | Positions (x) | Types |
|---|---|---|
| 1 | 5, 7, 9 | [!] [!] [?] coin |
| 2 | 13, 15, 17 | [!] [!] [?] coin |
| 3 | 21, 23, 25 | [!] [!] [?] coin |
| 4 | 29, 31, 33 | [!] [!] [?] coin |
| 5 | 37, 39, 41 | [!] [!] [?] coin |

Total: 15 blocks, 5 reinforcers. Post-SR pause platform at y=1 after each group.

**Pipe gate** at x=43–44: Hard block wall y=1–5, open at y=6. One-way right arrow.

---

## Zone 2: VR3 (Variable Ratio 3) — x=45 to 110

**Zone sign** (x=47, y=4): "VR3 — Unpredictable! Average every 3rd"

Sequence: [1,3,5,2,4,3,1,5,2,3] — same as positive reinforcement demo.
Total blocks: 29, reinforcers: 10.

Block positions at y=4 (same table as 01_demo_positive_reinforcement.md Zone 3):
Start at x=50. Every block spaced 2 tiles apart.

Place per VR sequence ratios (non-reinforced = [!], reinforced = [?] coin):
- VR1: [?] at x=50
- VR3: [!] x=52, [!] x=54, [?] x=56
- VR5: [!] x=58, [!] x=60, [!] x=62, [!] x=64, [?] x=66
- VR2: [!] x=68, [?] x=70
- VR4: [!] x=72, [!] x=74, [!] x=76, [?] x=78
- VR3: [!] x=80, [!] x=82, [?] x=84
- VR1: [?] x=86
- VR5: [!] x=88, [!] x=90, [!] x=92, [!] x=94, [?] x=96
- VR2: [!] x=98, [?] x=100
- VR3: [!] x=102, [!] x=104, [?] x=106

**Pipe gate** at x=108–109.

---

## Zone 3: FI5s (Fixed Interval 5 seconds) — x=110 to 160

**Zone sign** (x=112, y=4): "FI5 — Wait 5 seconds, then first hit pays"

**Concept**: The block only delivers a coin if Mario hits it AFTER 5 seconds have
elapsed since the last reinforcement. In SMM2, this is approximated by:
1. Spacing blocks so walking to each takes ~5 seconds naturally.
2. Placing a ground coin at a position exactly 5 s of walking from the start of each interval.
3. Observer notes the timing.

**Practical implementation**: Place 8 groups of 2 blocks each:
- Group has 1 used block (premature hit) and 1 ? coin block (the "correct" timing hit)
- Separate groups by a long open corridor (~7 tiles = ~5 s at walk speed)

| Group | Pre-interval block | Coin block | Corridor after |
|---|---|---|---|
| 1 | x=114 [!] | x=116 [?] | tiles 117–123 (7 tiles) |
| 2 | x=124 [!] | x=126 [?] | tiles 127–133 |
| 3 | x=134 [!] | x=136 [?] | tiles 137–143 |
| 4 | x=144 [!] | x=146 [?] | tiles 147–153 |
| 5 | x=154 [!] | x=156 [?] | ends zone |

Total: 10 blocks, 5 reinforcers. The [!] blocks represent the "scallop" — hitting
too early yields nothing; the [?] blocks represent the correct FI timing.

> **Instructor note**: Walk slowly and deliberately. The scallop pattern (slow
> start, accelerating finish of each interval) won't be visible in a single demo;
> describe it verbally. "If I hit this block too early, nothing. I have to wait."

**Pipe gate** at x=158–159.

---

## Zone 4: VI5.5s (Variable Interval 5.5 seconds) — x=160 to 200

**Zone sign** (x=162, y=4): "VI5.5 — Unpredictable interval, average 5.5 s"

VI sequence: [3,7,4,8,5,6,3,9,4,6] seconds (from parameters.json).
Approximate tile positions using walk speed (~1.33 tiles/s):

| Interval (s) | Tiles | Block x (running total) |
|---|---|---|
| 3 s | ~4 tiles | x=166 [?] coin |
| 7 s | ~9 tiles | x=177 [?] coin |
| 4 s | ~5 tiles | x=184 [?] coin |
| 8 s | ~11 tiles | x=197 [?] coin |
| 5 s | ~7 tiles | (+extend level) |

> Place ground coins at the appropriate tile positions for the full VI sequence.
> Mario collecting a ground coin = VI interval elapsed. After collecting, Mario
> continues walking and finds the next ground coin at the next interval distance.

Alternatively: place ? blocks at each interval position. The 10-element VI sequence
gives 10 reinforcers.

**Goal Pole**: x=202, y=1–9

---

## Instructor Notes

1. **FR3**: "Fixed means always the same. 3 responses per coin, every time."
   Show post-SR pause: "Notice I pause after each coin — that's the post-reinforcement pause."
2. **VR3**: "Variable means it changes. Sometimes 1 hit, sometimes 5, but average 3."
   Show steady responding without pause. "No post-SR pause — because I don't know when
   the next reward is coming!"
3. **FI5**: "Fixed interval — I have to wait 5 seconds, then the FIRST hit pays."
   Show the scallop: wait, then hit. "Watch the timing — early hits do nothing."
4. **VI5.5**: "Variable interval — I never know when it will be available."
   Show steady moderate responding. "I keep going at a medium pace."
5. Debrief: Draw cumulative record sketch. "FR=steep+pauses. VR=steep+no pauses.
   FI=scallop. VI=steady moderate. Same average rate, different patterns."

---

## Verification Checklist
- [ ] FR3 zone: exactly [!][!][?] pattern × 5 groups
- [ ] VR3 zone: 29 blocks, 10 reinforcers, sequence [1,3,5,2,4,3,1,5,2,3]
- [ ] FI5 zone: 5 pairs of [!] + [?], ~7-tile corridors between groups
- [ ] VI5.5 zone: ground coins/blocks at correct tile distances
- [ ] Zone signs present (demo level only)
- [ ] Pipe gates between zones (one-way right)
- [ ] Goal pole at end
- [ ] Test-played by naive observer
