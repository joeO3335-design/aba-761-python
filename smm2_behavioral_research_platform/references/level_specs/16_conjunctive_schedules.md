# Level Spec: Conjunctive Schedules (CONJ)

---

## Phenomenon
A Conjunctive schedule (CONJ) requires that **both** component schedule requirements
be satisfied before reinforcement is delivered (Ferster & Skinner, 1957). Neither
component alone is sufficient.

Formally, **CONJ FR n FI t** means:
- The organism must emit n responses (FR component), AND
- A minimum of t seconds must have elapsed since the last reinforcement (FI component).
- Reinforcement occurs only when **both** conditions are simultaneously met.
- If FR is completed before FI elapses, the organism must wait (or continue responding)
  until the interval is up.
- If FI elapses before FR is complete, the organism must keep responding until n
  responses are made.

CONJ is the AND-logic complement to ALT (OR-logic) and contrasts with CONC (two
independent schedules, free choice). It is also related to DRH (differential
reinforcement of high rate), since rapid responding may complete the FR early but
still must wait for the interval — producing a forced pause.

Key predictions:
1. **Response rate is lower than pure FR n** because the organism wastes energy
   responding before the interval is up.
2. **Post-reinforcement pausing is longer than pure FI t** because the organism must
   also meet the FR before the next SR.
3. **Patterned pausing**: If the organism learns the FI duration, it may pause, then
   respond rapidly to meet FR just before t elapses (optimized CONJ performance).
4. **CONJ FR FI vs. FR FI alone**: The conjunction slows overall rate and elongates
   inter-reinforcement intervals.

## Learning Objective
Participants:
1. Experience the "both requirements" contingency — responding before the interval
   is up produces no reinforcement.
2. Observe their own post-FR waiting behavior and how it differs from pure FR.
3. Understand that CONJ FI FR and CONJ FR FI differ only in which requirement tends
   to be the binding constraint.

## Behavioral Target
- **Response**: Hitting ? blocks (FR component counter)
- **Interval component**: Elapsed time since last reinforcement (FI component)
- **CONJ FR3 FI8s**: Need 3 hits AND 8 seconds since last SR
- **CONJ FR3 FI3s**: Interval is easy; FR3 is typically the binding constraint
- **CONJ FR8 FI3s**: FR is hard; FI is easy; organism waits then bursts
- **Consequence**: Coin delivered only when both FR and FI requirements are met
- **Antecedent**: Row of ? blocks; both requirements hidden from participant

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | ~80 tiles per zone | Same |

---

## Demo Level Design

### Approximating CONJ in SMM2

**FR component**: ? blocks in a line. Each hit = 1 response. The nth block is a
coin-bearing ? block; all others are used blocks (no coin from individual hits).

**FI component**: The coin-bearing ? block is **locked behind a gate** that only
opens after t seconds. The gate is a timed ON/OFF switch activated by a P-switch
dropped at trial onset:
- Instructor triggers a P-switch at the start of each trial (sets the interval clock).
- After t seconds, the P-switch expires and the gate opens.
- The coin block is accessible only when the gate is open (FI met).
- The coin block only produces a coin after n hits (FR met).

If Mario hits the gate while it is closed, nothing happens (FR being met before FI).
If Mario waits for the gate but hasn't hit n blocks, nothing happens (FI met before FR).
Only when the gate is open AND Mario has hit the required number of blocks does
the coin appear.

### Layout
```
ZONE A — CONJ FR3 FI8s
  Blocks at x=5,7,9 (used, used, used). Gate (P-switch door) at x=11.
  Behind gate: one [?] coin block at x=13.
  P-switch trigger platform at start: instructor/participant hits P-switch to start FI.
  P-switch duration = 8 s → gate opens at 8 s.
  To earn coin: hit 3 blocks (FR3 met) AND wait for gate (FI8s met).

ZONE B — CONJ FR3 FI3s
  Same layout, P-switch duration = 3 s.
  FR3 almost always completes before FI3s; participant must then wait 3 seconds.
  Observation: "I finished my hits but had to wait for the gate."

ZONE C — CONJ FR8 FI3s
  8 used blocks followed by gate at 3 s.
  Participant hits 3 blocks, gate opens (FI met), but must still hit 5 more (FR8 binds).
  Observation: "The gate opened but I still had to keep hitting."
```

### Instructor Script Notes
1. Zone A: "I need to hit 3 blocks AND wait 8 seconds. Let me hit the blocks first."
   Hit 3 blocks quickly, then stand at gate. "The gate is still closed. I already
   did my ratio — now I wait for the interval."
2. Zone B: "Now the interval is only 3 seconds." Hit blocks; gate opens first.
   "The gate opened before I finished! I still needed to hit more."
3. Zone C: "Hard ratio, short interval." Wait as gate opens. "Gate's open, but I'm
   only halfway through my hits. The gate being open doesn't help if I haven't
   hit enough."
4. Debrief: "CONJ means AND — both requirements. Whichever takes longer controls
   the inter-reinforcement interval. This slows rate compared to either schedule alone."

---

## Practice / Research Level Design

### Design: Within-subject, three CONJ conditions, compared to pure FR and pure FI controls
```
Phase 1 (control): Pure FR3 — 20 trials
Phase 2 (control): Pure FI8s — 20 trials
Phase 3: CONJ FR3 FI8s — 20 trials
Phase 4: CONJ FR3 FI3s — 20 trials
Phase 5: CONJ FR8 FI3s — 20 trials
Order of Phases 3–5 counterbalanced; Phases 1–2 always first.
```

### Contingency Parameters
| Condition | FR Req | FI Req | Binding Constraint | Expected IRF interval |
|---|---|---|---|---|
| Pure FR3 | 3 | — | FR | Short (pace-limited) |
| Pure FI8s | — | 8 s | FI | ~8 s |
| CONJ FR3 FI8s | 3 | 8 s | FI (interval longer) | ~8 s, elongated by FR |
| CONJ FR3 FI3s | 3 | 3 s | FR or tied | Moderate |
| CONJ FR8 FI3s | 8 | 3 s | FR (ratio longer) | Pace-limited but >FR8 alone |

### Procedural Notes
- Participant instructions: "Hit the blocks and collect coins. The gate will open
  at some point — there's no other explanation given."
- Observer codes: RESP for each block hit; FR_MET when nth hit made; FI_MET
  when interval elapses (stopwatch from P-switch activation); BOTH_MET + SR when coin
  collected; WAIT_FI if FR completed before FI; WAIT_FR if FI elapses before FR.
- Observer activates stopwatch when participant hits P-switch at start of each trial.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| FR component | 3, 8 |
| FI component (s) | 3, 8 |
| Binding constraint | FR, FI, tied |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESP | Block hit (increments FR counter) | Each hit |
| FR_MET | FR component completed (nth hit) | After nth hit |
| FI_MET | Interval requirement elapsed | At t seconds (stopwatch) |
| BOTH_MET | Both met — SR delivered | At coin contact |
| SR | Coin collected | At coin contact |
| WAIT_FI | FR done, waiting for interval | FR_MET logged before FI_MET |
| WAIT_FR | FI done, still hitting for FR | FI_MET logged before FR_MET |

---

## Analysis Notes
- **Inter-reinforcement interval (IRI)**: Mean time between consecutive SRs per
  condition. Expected: CONJ IRI > max(pure FR IRI, pure FI IRI).
- **Response rate**: Responses per minute by condition. Expected: lower in CONJ
  than pure FR (pausing after FR component met but before FI elapses).
- **Binding constraint frequency**: Proportion of trials where FR_MET preceded
  FI_MET vs. vice versa. Characterizes which component dominated behavior.
- **Pause duration**: Time between FR_MET and coin delivery (= FI wait time when
  FR binds). Diagnostic for optimized CONJ performance.

## Observer Notes
- WAIT_FI and WAIT_FR are mutually exclusive per trial; code whichever ordering occurs.
- Both met simultaneously (±0.5 s) counts as BOTH_MET without WAIT code.
- IOA for FI_MET uses ±2 s window; FR_MET should be 100%.

## Replication Notes
- Course ID (CONJ FR3 FI8s): XXXX-XXXX-XXXX-XXXX
- Course ID (CONJ FR3 FI3s): XXXX-XXXX-XXXX-XXXX
- Course ID (CONJ FR8 FI3s): XXXX-XXXX-XXXX-XXXX
- P-switch duration determines FI. In SMM2, P-switch lasts exactly 10 s by default.
  For FI8s, observer manually codes FI_MET at 8 s; coin block is only accessible
  after gate opens at 10 s (or use sub-area timing). For precision, recommend 10 s
  FI to match P-switch duration exactly.

## Key References
- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of Reinforcement*.
  Appleton-Century-Crofts. (pp. 694–723, conjunctive schedules)
- Hearst, E. (1958). The behavioral effects of some temporally defined schedules
  of reinforcement. *Journal of the Experimental Analysis of Behavior, 1*, 45–55.
- Shull, R. L. (1970). The response-reinforcement dependency in fixed-interval
  schedules. *Journal of the Experimental Analysis of Behavior, 14*, 55–60.
