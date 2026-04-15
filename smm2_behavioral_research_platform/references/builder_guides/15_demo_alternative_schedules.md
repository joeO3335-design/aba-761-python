# Builder's Guide: Alternative Schedules (ALT) — DEMO Level

**Curriculum position**: 15 of 20
**Phenomenon**: ALT FR FI — whichever requirement is met first triggers reinforcement
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | ~40 tiles per zone (3 zones) |

---

## Three Conditions (3 courses or 3 sequential zones)

| Zone | Condition | FR req | FI req (tiles at 1.33 t/s) | Expected winner |
|---|---|---|---|---|
| A | ALT FR5 FI10s | 5 hits | 10 s ≈ 13 tiles | Variable (near tie) |
| B | ALT FR3 FI20s | 3 hits | 20 s ≈ 27 tiles | FR3 always wins |
| C | ALT FR20 FI5s | 20 hits | 5 s ≈ 7 tiles | FI5 always wins |

---

## Concept: Two Paths to Reinforcement in One Corridor

Rather than a fork, ALT is implemented as a single corridor where:
- **FR path**: ? blocks line the corridor (each hit counts toward FR counter)
- **FI path**: A ground coin is placed at a fixed tile distance (Mario collects it by walking)

Mario walks through the corridor. If he hits enough blocks before reaching
the ground coin → FR won. If he reaches the ground coin first → FI won.
He collects whichever he encounters first; the trial resets.

---

## Zone A: ALT FR5 FI10s (x=1–30)

Ground: y=1, x=1–30

**FR blocks** at y=4 (Mario must jump to hit):
- [!] x=3, [!] x=5, [!] x=7, [!] x=9, [?] x=11 (5th block = coin, FR5 met)

**FI ground coin** at y=1: x=14 (≈10 s of walking from start at 1.33 t/s)
- Actually: 10 s × 1.33 t/s ≈ 13 tiles from start → ground coin at x=14

**What happens**:
- If Mario hits blocks at x=3,5,7,9,11 (without walking to x=14): FR5 wins at x=11.
- If Mario walks past blocks to x=14: FI wins (ground coin at x=14).
- If Mario hits some blocks AND walks: race between FR and FI.

**Loop pipe** at x=28 → return to x=1.

---

## Zone B: ALT FR3 FI20s (x=31–60)

**FR blocks** at y=4:
- [!] x=33, [!] x=35, [?] x=37 (3rd block = coin, FR3 met)

**FI ground coin** at x=58 (20 s × 1.33 ≈ 27 tiles; x=31+27=58)

**What happens**: FR3 blocks are at x=33–37. Mario hits them in ≤3 s.
Ground coin is at x=58 — very far. FR3 ALWAYS wins unless Mario ignores blocks.
Instructor demonstrates: "I always hit the blocks first — FR3 is easier than waiting 20 s."

**Loop pipe** at x=58 (or at x=60 → return).

---

## Zone C: ALT FR20 FI5s (x=61–90)

**FR blocks** at y=4:
- 20 blocks at x=63,65,67,69,...,101 (20 blocks, spaced 2 tiles apart)
- Only the 20th block [?] at x=101 contains a coin; all others [!]
- Note: zone extends to x=102

**FI ground coin** at x=68 (5 s × 1.33 ≈ 7 tiles; x=61+7=68)

**What happens**: Ground coin is at x=68. Only 4 blocks are before it (x=63,65,67).
Mario walks and reaches x=68 before hitting all 20 blocks. **FI always wins.**
Instructor: "I can't hit 20 blocks in 5 seconds — the interval coin appears first."

**Goal Pole** at x=105, y=1–9.

---

## Instructor Script Notes

1. **Zone A (ALT FR5 FI10s)**: "Two ways to earn a coin: hit 5 blocks OR wait 10 s.
   Let me try hitting the blocks." Hit 5 blocks quickly (FR wins).
   Reset. "Now I'll walk right past the blocks." Walk to ground coin (FI wins).
   "Either works — ALT means OR."

2. **Zone B (ALT FR3 FI20s)**: "FR3 is easy; 20 seconds is a long wait."
   Hit 3 blocks. "FR wins every time. The interval barely matters."

3. **Zone C (ALT FR20 FI5s)**: "FR20 is too hard. 5 seconds is very fast."
   Walk without hitting. Ground coin. "FI wins — I don't even bother with the blocks."

4. Debrief: "Alternative schedule = OR-logic. Whichever is less demanding controls.
   This shows that combining two schedules doesn't average them —
   the easier one simply dominates."

---

## Verification Checklist
- [ ] Zone A: 5 FR blocks (4 empty + 1 coin), FI ground coin at ~13 tiles from zone start
- [ ] Zone B: 3 FR blocks (2 empty + 1 coin), FI ground coin at ~27 tiles from zone start
- [ ] Zone C: 20 FR blocks (19 empty + 1 coin at end), FI ground coin at ~7 tiles from start
- [ ] Walk-speed calibration: time Mario walking 10 tiles = ~7.5 s (1.33 t/s)
- [ ] Loop pipe returns Mario to start of each zone
- [ ] Goal pole after Zone C
- [ ] Observer has stopwatch for FI timing confirmation
