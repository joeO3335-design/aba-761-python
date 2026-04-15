# Builder's Guide: Concurrent Schedules (CONC) — DEMO Level

**Curriculum position**: 14 of 20
**Phenomenon**: CONC FR FR, CONC VI VI, COD effect
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
| Level Length | Looped fork (3 separate courses) |

---

## Three Courses

| Course | Condition |
|---|---|
| Course 1 | CONC FR3 FR9 (no COD) |
| Course 2 | CONC VI3s VI9s (no COD) |
| Course 3 | CONC VI3s VI9s + COD (2-response delay) |

All courses share the same fork geometry. Only coin contents and COD blocks differ.

---

## Fork Structure (all courses — identical geometry)

- Approach: x=1–15, ground y=1, 15 tiles
- Fork divider: Hard block [H] at x=16, y=1–5 (5-high wall)
  - Gap above (y=6): Mario can jump to upper path
  - Gap below (y=1): Mario walks into lower path
- **Upper path** (Left): y=5–7, x=16–28 (12 tiles)
- **Lower path** (Right): y=1–3, x=16–28 (12 tiles)
- **Both paths equal length**: 12 tiles each — no travel-time bias
- Loop pipe: x=30 on each path → sub-area → return to x=1

---

## Course 1: CONC FR3 FR9 (no COD)

### Left path (FR3): Upper
[?] blocks at y=6: x=18 [!], x=21 [!], x=24 [?]coin
→ 3 blocks per trip; coin on 3rd (FR3)

### Right path (FR9): Lower
[!] blocks at y=2: x=18,19,20,21,22,23,24,25,26 (9 blocks)
[?] coin block at y=2: x=27 (9th block = coin)
→ 9 blocks per trip; coin on 9th (FR9)

> Right path length must accommodate 9 blocks. Extend right path to x=28–34 if needed
> (18 tiles total, same as Amelioration spec). Left path stays at 6 tiles.
> **Note**: This means paths are NOT equal length for FR-FR. That's intentional —
> FR9 naturally takes more responses, making it leaner. For the COD demo (Course 3),
> use VI-VI with equal paths.

---

## Course 2: CONC VI3s VI9s (no COD)

### Both paths equal length: 6 tiles each

**Left path**: 1 [?] coin block at x=22, y=6 (behind a P-switch gate)
- P-switch gate: ON/OFF blocks at x=20, y=6–7 block the coin block initially.
- Observer opens gate per VI3s sequence using stopwatch.
- When gate is open: coin block is accessible. If Mario visits and gate is open → coin.
- After coin collected, gate closes; reopens after next interval.

**Right path**: Same mechanism. 1 [?] coin block at x=22, y=2.
- Observer opens gate per VI9s sequence independently.

**Observer tool**: Two stopwatches (or phone timers). At session start, start both.
Left timer counts down VI3s sequence values; right timer counts VI9s sequence values.
Open/close gates by toggling ON/OFF switch at appropriate times.

**VI3s sequence**: [1,4,2,5,3,4,1,6,2,4] s
**VI9s sequence**: [5,12,7,11,9,8,10,13,6,9] s

> **Simpler demo approach**: Skip the gate mechanism. Instead, place ground coins at
> fixed positions along each path. Left path: coin at tile 4 (closer → arrives sooner).
> Right path: coin at tile 9 (farther → takes longer). This approximates faster VI on left.

---

## Course 3: CONC VI3s VI9s + COD (2-response delay)

Same as Course 2, but:
- At the start of each path (x=17,18), place 2 **empty [!] blocks** at y=6 (left) and y=2 (right).
- These 2 blocks must be hit before Mario can access the coin block.
- First 2 hits after switching = COD responses (wasted, no coin).
- After hitting 2 COD blocks: coin block is accessible.

> The 2 COD blocks are always empty [!]. They simulate the changeover delay —
> the first 2 responses after switching yield nothing.

---

## Instructor Script Notes

1. **CONC FR3 FR9**: "Both paths always available. I can switch freely.
   Left: 3 blocks per coin. Right: 9 blocks per coin."
   Make ~20 choices. Show exclusive left preference.
   "I never go right — the local rate on left is always better."

2. **CONC VI3s VI9s**: "Now coins appear unpredictably. Left every ~3 s, right every ~9 s."
   Make ~20 choices. Show ~75/25 distribution.
   "I still prefer left but visit right sometimes. That's matching."

3. **CONC VI3s VI9s + COD**: "Now switching costs 2 wasted hits."
   Make ~20 choices. "I switch less often — the changeover delay makes frequent
   switching too costly. But I still end up matching overall."

4. Debrief: "CONC means both schedules are always on, always available.
   COD prevents adventitious reinforcement of switching. The Matching Law
   describes the allocation that emerges."

---

## Verification Checklist
- [ ] Both paths equal length in VI-VI courses (Course 2 and 3)
- [ ] Course 1: FR3 left (coin on 3rd block per trip), FR9 right (coin on 9th block per trip)
- [ ] Course 2: VI gate mechanism or ground-coin approximation in place
- [ ] Course 3: 2 COD empty blocks at path entry on both sides
- [ ] Loop pipes return Mario to fork
- [ ] All 3 course IDs recorded in INDEX.md
- [ ] Observer has VI sequence cards for Courses 2 and 3
