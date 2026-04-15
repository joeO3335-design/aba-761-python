# Builder's Guide: Amelioration — DEMO Level

**Curriculum position**: 13 of 20
**Phenomenon**: Amelioration/Melioration — CONC FR-FR vs. VI-VI, local-rate equalization
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
| Level Length | Looped fork (two separate courses) |

---

## Two Separate Courses

| Course | Condition | Schedule |
|---|---|---|
| Course A | FR-FR (3:1) | Left=FR3, Right=FR9 |
| Course B | VI-VI (3:1) | Left=VI3s, Right=VI9s |

---

## Course A: Concurrent FR-FR (3:1)

### Fork Layout (same for both courses)
- Approach: x=1–15, ground y=1
- Fork at x=16 (Hard block divider)
- Upper path (Left): y=4–6, x=16–28 (6 tiles path)
- Lower path (Right): y=1–3, x=16–40 (18 tiles path — **longer to implement FR9**)
- Loop: both exits → sub-area → return to x=1

### Left Path (FR3) — 6 tiles
[?] blocks at y=5: x=18, 22, 26 — 3 blocks total.
After every 3 hits (one per trip if Mario hits all 3): 1 coin delivered.
FR3 = 3 blocks per trip, 1 coin per 3 blocks.

Alternatively: use only 1 [?] coin block + 2 [!] empty blocks.
Place: x=18 [!], x=22 [!], x=26 [?]coin — coin on every 3rd block (FR3 per trip).

> Each trip through left path = 3 hits → 1 coin. This simulates FR3 at 1 coin/trip.

### Right Path (FR9) — 18 tiles
Much longer path to implement FR9:
[?] blocks at y=2: x=18,20,22,24,26,28,30,32,34 — 9 blocks.
Only the 9th block is active [?] with coin: x=34 [?]coin; all others [!].
Each trip = 9 hits → 1 coin at end. But this takes 3 trips (9+9+9=27) to match 1 coin...

**Simplified implementation**: Right path = 18 tiles long.
- Place 9 empty blocks [!] and 1 [?] coin block.
- The trip delivers 1 coin every third visit (across 3 trips of the right path).
- Alternatively: right path trip yields 1/3 coin on average → use P-switch timing:
  coin available only every 3rd trip. Track via observer.

> **Simplest approach for demo**: Right path has 1 [?] coin block at x=34 (after 9 blocks).
> That coin is only available every 3 visits (simulated by placing the coin behind
> a gate that opens with an ON/OFF switch — observer toggles it every 3rd visit).
> For demo purposes: just make right path visually longer and explain "right pays off
> less frequently." Instructor can manage the gate manually for demo.

### Loop Pipes
Both path exits → shared sub-area exit pipe → main area x=5, y=1.

---

## Course B: Concurrent VI-VI (3:1)

Same fork structure. Left and right paths: **equal length, 6 tiles each**.

### VI Approximation

VI schedules are approximated by P-switch-timed coin gates:
- A coin is "available" on each path after a variable interval.
- In SMM2: place a locked door behind each path. Observer opens the correct door
  (makes coin accessible) according to the VI sequence.

For demo: place 1 visible [?] coin block behind a locked mechanism:
- Left path coin is "reloaded" every 1–6 s (VI3s mean) between visits.
- Right path coin is "reloaded" every 5–13 s (VI9s mean) between visits.
- Observer tracks availability using a stopwatch and signals availability by
  toggling an ON/OFF switch (opening/closing the coin gate) per the preset sequence.

**Left VI3s sequence**: [1,4,2,5,3,4,1,6,2,4] s (from parameters.json)
**Right VI9s sequence**: [5,12,7,11,9,8,10,13,6,9] s

#### Practical Demo Implementation
For the instructor demo, simplify:
- Left path: coin available every ~3 s (instructor can see the timer; coin refreshes)
- Right path: coin available every ~9 s
- Use a visible ground coin on the left/right path; instructor removes it manually
  between availability windows (or uses the editor to pre-load coins at fixed tile positions)

---

## Instructor Script Notes

**Course A (FR-FR)**:
"Left path: 3 blocks, 1 coin each trip. Right path: longer, pays off less often."
Make ~20 choices. "I stayed left almost every time — exclusive preference.
Because the local rate on left is always better: every trip pays. Right rarely pays.
Melioration = I go where local rate is highest."

**Course B (VI-VI)**:
"Now both paths pay off unpredictably. Left averages 3 seconds, right averages 9 seconds."
Make ~20 choices. "Notice I went right a few times. Why?
After visiting left several times quickly, the left coin wasn't available yet.
Right became momentarily richer. I 'ameliorated' by switching."
"My allocation: about 75% left / 25% right. That's matching — the same mechanism
(local-rate chasing) that produces matching on VI-VI."

Debrief: "FR-FR: local rate on left never depletes — exclusive preference.
VI-VI: local rates equalize over time — matching. Same mechanism (melioration),
different schedules → different outcomes."

---

## Verification Checklist
- [ ] Course A: Left path 6 tiles, FR3 (3 blocks → 1 coin/trip)
- [ ] Course A: Right path 18 tiles, FR9 (effectively 1 coin per ~3 trips)
- [ ] Course B: Both paths 6 tiles (equal path length — critical for VI comparison)
- [ ] Course B: VI timing mechanism prepared (P-switch gates or observer-managed)
- [ ] VI sequences noted on paper for observer reference (left: 1,4,2,5,3,4,1,6,2,4 s)
- [ ] Loop pipes return Mario to fork after each choice
- [ ] Both course IDs recorded in INDEX.md
