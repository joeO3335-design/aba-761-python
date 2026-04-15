# Builder's Guide: Tandem Schedules (TAND) — DEMO Level

**Curriculum position**: 20 of 20
**Phenomenon**: TAND FR FR — sequential requirements, NO signal at transition (contrast with CHAIN)
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
| Level Length | ~60 tiles per trial (same geometry as CHAIN) |

---

## Three Courses + CHAIN Comparison

| Course | Condition | Comp 1 | Comp 2 | Signal at C1→C2 |
|---|---|---|---|---|
| Course T1 | TAND FR3 FR3 | FR3 | FR3 | **None** |
| Course T2 | TAND FR5 FR3 | FR5 | FR3 | **None** |
| Course T3 | TAND FR3 FI8s | FR3 | FI8s (~10 s) | **None** |
| Course C1 | CHAIN FR3 FR3 | FR3 | FR3 | Yes (blue coins) |

> Course C1 is identical to CHAIN Course 1 (spec 19). Build TAND first, then clone
> and add P-switch for CHAIN. This makes the TAND vs. CHAIN comparison clean.

---

## TAND Layout (all TAND courses — identical geometry to CHAIN but NO P-switch)

### Ground and Structure (x=1–60)
Ground: y=1, x=1–60.

**Blocks all at y=4 in a single unbroken sequence.**
No P-switch. No blue coins. No signal of any kind between Component 1 and Component 2.

### Course T1: TAND FR3 FR3
- 6 blocks total: [!] x=5, [!] x=8, [!] x=11, [!] x=14, [!] x=17, [?] x=20
  (6th block = coin)
- From participant's view: 6 identical blocks in a row, coin in the 6th.
- NO indication that the first 3 constitute "Component 1" and the last 3 "Component 2."
- Observer codes COMP1_DONE after 3rd hit; COMP2_DONE after 6th hit = TERM_SR.

### Course T2: TAND FR5 FR3
- 8 blocks: [!] x=5, [!] x=7, [!] x=9, [!] x=11, [!] x=13 (Component 1 = FR5)
  then [!] x=16, [!] x=19, [?] x=22 (Component 2 = FR3, coin on 8th)
- Observer codes COMP1_DONE after 5th hit; COMP2_DONE / TERM_SR after 8th hit.

### Course T3: TAND FR3 FI8s
- Component 1 = FR3: [!] x=5, [!] x=8, [!] x=11 (3 empty blocks)
  After 3rd hit: Component 1 done (observer starts FI clock).
- Component 2 = FI8s: coin block [?] at x=30 (behind a gate).
  Gate at x=18–19 (Hard block wall). Gate opens at 8 s (observer opens via ON/OFF switch).
  Mario waits at gate until 8 s elapses; gate opens silently (no P-switch, no visual cue of timer).
  Coin behind gate at x=22.

> **Key contrast with CONJ FR3 FI8s**: In CONJ, both run simultaneously from trial start.
> In TAND FR3 FI8s, the FI clock starts ONLY AFTER FR3 is completed. Sequential, not simultaneous.
> In TAND, gate opens 8 s after FR3 completion — no signal.
> Compare to CHAIN: In CHAIN FR3 FI8s, the P-switch activation (signal) marks FR3 completion
> AND starts the visible blue-coin timer. In TAND, no signal, no visible timer.

### Loop Return
- Exit pipe at x=53, y=1 → sub-area → return to x=1.

---

## The Critical Difference from CHAIN

| Feature | CHAIN | TAND |
|---|---|---|
| Visual change at link transition | YES (blue coins appear) | NO |
| Conditioned reinforcer | YES (blue coins function as CR) | NO |
| Goal gradient expected | YES (faster in Link 2) | NO (flat IRT expected) |
| Motivation in Component 1 | Higher (CR reinforces C1 completion) | Lower |
| Trial completion speed | Faster | Slower |

To demonstrate this contrast:
1. Run CHAIN FR3 FR3 first. Show acceleration.
2. Run TAND FR3 FR3 immediately after. Show flat pace.

---

## Instructor Script Notes

1. **TAND FR3 FR3**:
   "Same setup as the Chained schedule — 6 blocks, coin in the 6th."
   Hit all 6 at steady pace. Collect coin.
   "Did you notice anything special at block 3? No? Neither did I.
   Nothing signals that I've completed the first requirement. No conditioned reinforcer."
   "My pace was consistent throughout. No acceleration."

2. **Switch to CHAIN FR3 FR3**:
   "Same layout — BUT now watch block 3."
   Hit 3 blocks. Blue coins appear. Accelerate.
   "See the blue trail? That's the conditioned reinforcer for completing Link 1.
   It motivates me to race to the star. My pace increased — that's the goal gradient."

3. **TAND FR5 FR3**:
   "5 blocks then 3 — still no signal at block 5."
   Hit 8 blocks at even pace. Coin on 8th.
   "Without the signal, there's no gradient. I pace myself evenly."

4. **TAND FR3 FI8s**:
   "3 blocks, then I wait 8 seconds for the gate."
   Hit 3 blocks. Wait at gate. No blue trail, no countdown. Gate silently opens at 8 s.
   "I wait, but I have no idea how long. No signal. Compare this to Chained FR3 FI8s
   where the P-switch would visibly tell me when the interval is up."

5. Debrief: "Tandem = sequential requirements WITHOUT conditioned reinforcers.
   Chained = sequential requirements WITH conditioned reinforcers (SD changes at each link).
   The SD changes in Chained are not just informational — they're motivational.
   Without them (Tandem), the organism still completes the chain, but less efficiently."

---

## Verification Checklist
- [ ] TAND courses: NO P-switch, NO blue coins, NO visual signal at component transition
- [ ] T1 (TAND FR3 FR3): 6 blocks, coin on 6th, no signal after 3rd
- [ ] T2 (TAND FR5 FR3): 8 blocks, coin on 8th, no signal after 5th
- [ ] T3 (TAND FR3 FI8s): FR3 empty blocks, then SILENT gate (no P-switch), coin behind gate
- [ ] CHAIN FR3 FR3 course (reuse from spec 19): P-switch + blue coins at link transition
- [ ] Observer has hit-count tracker for COMP1_DONE and COMP2_DONE coding
- [ ] Observer has stopwatch for FI8s component in T3 (starts at COMP1_DONE)
- [ ] Both TAND and CHAIN courses test-played; timing verified for FI8s gate
- [ ] All course IDs recorded in INDEX.md with TAND/CHAIN labels
- [ ] TAND and CHAIN courses for FR3 FR3 are clones of each other (identical except P-switch)
