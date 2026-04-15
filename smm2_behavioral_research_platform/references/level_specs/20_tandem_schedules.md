# Level Spec: Tandem Schedules (TAND)

---

## Phenomenon
A Tandem schedule (TAND) arranges two or more component schedule requirements in
sequence, but **without any discriminative stimulus change at the transition between
components** (Ferster & Skinner, 1957). The organism must complete all requirements
before earning reinforcement, but receives no signal when one requirement is met and
the next begins.

Formally, **TAND FR n FI t** means:
- The organism must emit n responses (FR component), AND THEN
- A minimum of t seconds must elapse (FI component),
- WITHOUT any stimulus change marking the FR→FI transition.
- Only after both requirements are met (in order, silently) does reinforcement occur.

Key properties:
1. **Ordered requirements, no cues**: Like CHAIN, requirements are sequential and
   ordered. Unlike CHAIN, no conditioned reinforcer marks the transition.
2. **No conditioned reinforcers**: Without SD changes, completing component 1
   provides no conditioned reinforcement. The organism persists without feedback.
3. **Lower responding in initial component than CHAIN**: Because the link 1 completion
   produces no conditioned reinforcer, motivation to complete Link 1 quickly is lower.
4. **TAND vs. CHAIN comparison**: The critical manipulation is whether a stimulus
   change occurs at link transitions. TAND = no change (no CR); CHAIN = change
   (CR present). This comparison isolates the role of conditioned reinforcement.
5. **TAND vs. CONJ**: Both require multiple conditions before reinforcement.
   CONJ is simultaneous (both must be met regardless of order); TAND is sequential
   (must complete in order).

## Learning Objective
Participants:
1. Experience the sequential requirements of TAND without feedback at transitions.
2. Observe that completing Link 1 does not feel different from still being in Link 1
   (no conditioned reinforcer).
3. Compare TAND to CHAIN directly: understand that the SD at link transitions in
   CHAIN has real motivational consequences.

## Behavioral Target
- **Response**: Hitting ? blocks (FR component) followed by a waiting period (FI component)
- **TAND FR3 FI8s**: Must hit 3 blocks, THEN wait 8 seconds; no signal at the transition
- **TAND FR3 FR3**: Must hit 3 blocks, THEN hit 3 more blocks; no cue signals the
  transition between the two FR requirements
- **Consequence**: Coin delivered only after both components satisfied
- **Antecedent**: Uniform environment throughout both components (no SD change)

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | ~60 tiles per tandem trial | Same |

---

## Demo Level Design

### Implementation: Silent component transition

For TAND FR3 FR3:
- First 3 ? blocks: Link 1 requirement (FR3). After the 3rd hit, nothing visible changes.
- Next 3 ? blocks: Link 2 requirement (FR3). After the 6th total hit, coin delivered.
- The 4th block's first hit triggers the coin delivery.

In SMM2, implement as:
- Blocks 1–3: used blocks (no coin from individual hits)
- Blocks 4–6: block 6 contains the coin (FR3 from entry into "link 2")
- From participant's view, it is simply 6 blocks with a coin in the 6th.
- There is no visual, auditory, or environmental signal that the first 3 blocks
  completed a "link."

For TAND FR3 FI8s:
- 3 used blocks → coin-gate locked for 8 s → coin becomes available after 8 s wait
- No signal when 3 blocks are done; coin gate timing is silent.

### Layout
```
TAND FR3 FR3:
  Blocks at x=2,4,6 (Link 1 — used, no coin).
  Blocks at x=8,10 (Link 2 — used, no coin).
  Block at x=12 (Link 2 terminal — contains coin, FR3 of Link 2 met).
  From participant view: 6 identical blocks, coin in 6th.

TAND FR3 FI8s:
  Blocks at x=2,4,6 (Link 1 — used, no coin after hits).
  Locked gate at x=8 (P-switch initiated silently by observer at trial start).
  Gate opens after 8 s. Coin behind gate (x=10).
  No blue trail, no visual change at block 3 (contrast with CHAIN FR3 FR3).
```

### CHAIN vs. TAND Direct Comparison
Run participants through both CHAIN FR3 FR3 (spec 19) and TAND FR3 FR3 in the
same session. Key observable difference:
- **CHAIN**: After hitting block 3, blue coins appear. Mario speeds up.
- **TAND**: After hitting block 3, nothing changes. Mario may pause, slow, or
  continue at same pace.

### Instructor Script Notes
1. TAND demo: "I'll hit all 6 blocks to get the coin. Watch carefully."
   Hit blocks 1–3. "Did anything happen? No. The environment looks the same."
   Hit blocks 4–6. Coin appears. "Only at the very end."
2. "Now compare to Chained." Switch to CHAIN demo. Hit 3 blocks. Blue trail.
   "See the difference? Blue coins appeared! That's my signal I completed Link 1.
   It motivates me to keep going and finish Link 2."
3. "In Tandem, there's no conditioned reinforcer — just a silent requirement.
   In Chained, the SD at the transition IS a conditioned reinforcer."
4. Debrief: "Tandem = sequential + no cue. Chained = sequential + cue (conditioned SR).
   The cue matters for motivation and response rate."

---

## Practice / Research Level Design

### Design: Within-subject, TAND vs. CHAIN, three FR combinations
```
Condition A: TAND FR3 FR3 — 20 trials
Condition B: CHAIN FR3 FR3 — 20 trials (spec 19; same level, blue trail added)
Condition C: TAND FR5 FR3 — 20 trials
Condition D: TAND FR3 FI8s — 20 trials
Counterbalanced order (Conditions A and B always as a pair).
```

### Contingency Parameters
| Condition | Comp 1 Req | Comp 2 Req | Signal at C1→C2 | Terminal SR |
|---|---|---|---|---|
| TAND FR3 FR3 | FR3 | FR3 | None | Coin at 6th hit |
| CHAIN FR3 FR3 | FR3 | FR3 | Yes (blue trail) | Coin at 6th hit |
| TAND FR5 FR3 | FR5 | FR3 | None | Coin at 8th hit |
| TAND FR3 FI8s | FR3 | FI8s | None | Coin after 3 hits + 8 s |

### Procedural Notes
- Participant instructions: "Hit the blocks in the level to collect coins."
  (Identical to CHAIN instructions — the manipulation is between-level.)
- Observer codes: RESPONSE for each block hit; COMP1_DONE when nth hit completes
  Component 1 (observer tracks from level map); COMP2_DONE when Component 2 completes;
  TERM_SR when coin is collected; PAUSE for ≥3 s no response; RESET if Mario
  dies/resets before terminal SR.
- Observer must track component transitions silently (from level map) — participant
  receives no signal.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Component 1 requirement | FR3, FR5 |
| Component 2 requirement | FR3, FI8s |
| SD at component transition | Present (CHAIN), Absent (TAND) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESPONSE | Block hit (either component) | Each hit |
| COMP1_DONE | Component 1 requirement met (observer-coded) | After nth hit / interval |
| COMP2_DONE | Component 2 requirement met | After terminal response/interval |
| TERM_SR | Primary reinforcer delivered | On coin contact |
| PAUSE | ≥3 s no response | Pause onset |
| RESET | Trial reset (death or timeout) | On reset |

---

## Analysis Notes
- **Key CHAIN vs. TAND comparison**:
  - Response rate in Component 1 of CHAIN FR3 FR3 vs. TAND FR3 FR3.
    Prediction: faster responding in CHAIN (conditioned reinforcer motivates).
  - Trial completion rate: CHAIN faster.
  - Post-COMP1_DONE pause: longer in TAND (no signal that Link 1 is done;
    participant may not know to accelerate).
- **Goal gradient under TAND**: Compare response rate before vs. after COMP1_DONE.
  Prediction: no acceleration (no gradient without conditioned reinforcer);
  contrast with CHAIN which shows gradient.
- **IRT analysis**: Inter-response times across component blocks.
  TAND prediction: flat IRT pattern. CHAIN prediction: IRT decreases after L1_SR.
- **Efficiency**: Total time from trial onset to TERM_SR; CHAIN should be faster.

## Observer Notes
- COMP1_DONE and COMP2_DONE are **observer-inferred codes** — the participant
  receives no signal. Observer tracks from the level map (knows which blocks are
  Link 1 vs. Link 2).
- For TAND FR3 FI8s: COMP1_DONE = after 3rd hit; COMP2_DONE = after 8 s from
  COMP1_DONE (or from trial start if interval begins at onset — clarify before session).
  Use stopwatch from COMP1_DONE for FI8s.
- IOA: RESPONSE codes 100% expected; COMP1_DONE requires both observers to agree on
  hit count (use the level map as ground truth).

## Replication Notes
- Course ID (TAND FR3 FR3): XXXX-XXXX-XXXX-XXXX
- Course ID (TAND FR5 FR3): XXXX-XXXX-XXXX-XXXX
- Course ID (TAND FR3 FI8s): XXXX-XXXX-XXXX-XXXX
- TAND FR3 FR3 and CHAIN FR3 FR3 levels must be physically identical except for
  the blue coin trail (P-switch activation at block 3 in CHAIN; absent in TAND).
  Build TAND first, then clone and add P-switch for CHAIN.

## Key References
- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of Reinforcement*.
  Appleton-Century-Crofts. (pp. 631–643, tandem schedules)
- Kelleher, R. T. (1966). Chaining and conditioned reinforcement.
  In W. K. Honig (Ed.), *Operant Behavior* (pp. 160–212). Appleton-Century-Crofts.
- Gollub, L. R. (1977). Conditioned reinforcement: Schedule effects.
  In W. K. Honig & J. E. R. Staddon (Eds.), *Handbook of Operant Behavior*.
  Prentice-Hall.
