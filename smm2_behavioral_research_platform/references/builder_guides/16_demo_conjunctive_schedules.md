# Builder's Guide: Conjunctive Schedules (CONJ) — DEMO Level

**Curriculum position**: 16 of 20
**Phenomenon**: CONJ FR FI — both requirements must be met before reinforcement
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
| Level Length | ~50 tiles per zone (3 zones) |

---

## Core Mechanic: P-switch Gate + FR Blocks

The FI component is approximated using a **P-switch** at trial start:
- P-switch activates → door/gate opens after 10 s (P-switch duration)
- FR component: blocks that must be hit before accessing the coin
- Coin is **behind the gate** (locked until P-switch opens it)
- Both conditions must be met: gate open AND n blocks hit

**P-switch in SMM2**: When Mario activates a P-switch, it runs for exactly 10 s.
During this 10 s, blue coins on the ground appear and certain blocks change state.
Use this to approximate FI10s.

For FI8s: place gate at a position that requires 8 s of walking from the P-switch.
Gate = ON/OFF blocks; P-switch flips them. Mario must walk (uses FI-like timing) AND hit blocks (FR).

---

## Zone A: CONJ FR3 FI10s (using P-switch)

### Layout (x=1–40)
Ground: y=1, x=1–40

**P-switch** at x=3, y=1 (Mario hits it at the start of the trial).
P-switch duration: 10 s.

**FR blocks** at y=4: x=7 [!], x=10 [!], x=13 [?] coin
(3 blocks; coin on 3rd = FR3 met)

**P-switch gate**: ON/OFF switch-activated blocks at x=20–21, y=1–4.
When P-switch is active, the gate opens (ON/OFF switch connected to P-switch).
The coin block at x=13 is actually at x=24 (behind gate).

> Revised layout:
> - FR blocks (pre-gate): x=7 [!], x=10 [!], x=13 [!] (3rd block is empty — just counters)
> - Gate at x=16–17 (ON/OFF blocks, closed until P-switch opens)
> - Coin block at x=20 [?] (accessible only after gate opens AND Mario passes through)
>
> Wait — this doesn't enforce FR *before* coin. Let me restructure:
> - FR blocks at y=4: x=7 [!], x=10 [!], x=13 [?] coin
> - But the coin block at x=13 is inside a **walled chamber** (enclosed with Hard blocks)
> - The chamber entrance is sealed by an ON/OFF block gate (closed initially)
> - P-switch at x=3 → when activated and 10 s elapses, gate opens
> - Mario must hit P-switch (starts FI clock) → hit 3 blocks (FR3) → wait for gate to open → enter chamber for coin

**Revised layout**:
```
x=1–4:   Open corridor (P-switch at x=3)
x=5–15:  3 FR blocks at y=4 (x=6 [!], x=9 [!], x=12 [!] — empty, count the hits)
x=13:    Gate entrance — ON/OFF blocks at y=1–4 (gate closed; opens at P-switch expiry)
x=14–22: Chamber behind gate — coin block at x=18 [?]
```

**Timing**: P-switch at x=3. Mario hits it and walks to FR blocks.
Hitting 3 blocks takes ~3–5 s. Gate opens at 10 s (P-switch expires).
If Mario hits 3 blocks quickly (FR met first): must wait at gate until 10 s.
Shows: WAIT_FI — FR done, FI not yet done.

If Mario walks slowly and gate opens before 3 blocks: must keep hitting.
Shows: WAIT_FR — FI done, FR not yet done.

---

## Zone B: CONJ FR3 FI3s

Same layout. P-switch duration: unfortunately, SMM2 P-switch is fixed at 10 s.
Approximation: place the coin block closer to the P-switch (~4 tiles from start).
Mario can reach the coin in 3 s (3 tiles × 1.33 s/tile ≈ 2.3 s) = "FI3s."
Gate opens quickly; FR3 is the binding constraint.

**Adjusted layout**:
- P-switch at x=3
- FR blocks: x=5 [!], x=7 [!], x=9 [?] coin (FR3, close together)
- No gate needed — coin is at x=9 (accessible after ~3 s of walking AND 3 hits)
- Observer uses stopwatch to confirm timing

---

## Zone C: CONJ FR8 FI3s

- FR blocks: x=5–19 (8 blocks, spaced 2 tiles: x=5,7,9,11,13,15,17,19)
  Only x=19 is [?] coin; x=5–17 are [!] empty.
- FI ground coin at x=7 (3 s from start ≈ 4 tiles, x=3+4=7)

"FI" component: ground coin at x=7. Mario reaches it in 3 s (3 tiles from zone start).
But there's also the FR8 requirement: must hit 8 blocks to reach the actual [?] coin.
If Mario collects the ground coin (FI met), that's a bonus but NOT the CONJ reinforcer —
the CONJ reinforcer (big star/special coin) is only behind the 8th block.

> Clarify: The CONJ reinforcer is a **Super Star** or colored coin at x=21 [?].
> The FI ground coin is a secondary "FI-met" indicator, not the primary reinforcer.
> The primary reinforcer (star) is only given when BOTH are met: 3 s passed AND 8 blocks hit.

**Zone C practical**: Walk-through without hitting (FI ground coin collected at x=7).
Then continue hitting 8 blocks (FR8 binding). Star at x=21 after 8th hit.

---

## Instructor Script Notes

1. **CONJ FR3 FI10s**: Hit P-switch. Hit 3 blocks fast. Stand at gate.
   "I did my hits — but the gate isn't open yet. I have to wait."
   Gate opens at 10 s. Collect coin.
   "Both conditions had to be met. I was early on FR, late on FI."

2. **CONJ FR3 FI3s**: "Now the interval is short." Gate opens at ~3 s.
   "The gate opened before I finished! I still needed to hit."
   "FR3 is the binding constraint here."

3. **CONJ FR8 FI3s**: "Long ratio, short interval." Reach ground coin quickly.
   "FI met — but I still need 8 hits." Keep hitting.
   "FR8 is the binding constraint."

4. Debrief: "Conjunctive = AND. Both required. Whichever is harder controls
   the rate. This slows response rate below what either schedule alone would produce."

---

## Verification Checklist
- [ ] Zone A: P-switch at x=3, gate mechanism at ~10 s, FR3 blocks before gate
- [ ] Zone B: FR3 binding constraint (coin accessible after 3 s + 3 hits)
- [ ] Zone C: FR8 blocks + early FI ground coin, star only after 8th hit
- [ ] P-switch duration calibrated (10 s standard)
- [ ] Observer has stopwatch for FI timing
- [ ] Loop pipe returns Mario to start of each zone
- [ ] All course IDs recorded in INDEX.md
