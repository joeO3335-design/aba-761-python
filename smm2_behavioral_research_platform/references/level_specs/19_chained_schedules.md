# Level Spec: Chained Schedules (CHAIN)

---

## Phenomenon
A Chained schedule (CHAIN) arranges two or more component schedules in sequence,
where completing the schedule requirement in each link produces:
1. A **conditioned reinforcer** (the discriminative stimulus signaling the next link), and
2. Access to the **next link's schedule**.

Only the terminal link produces a **primary reinforcer** (Ferster & Skinner, 1957;
Kelleher & Gollub, 1962).

Key properties:
1. **Sequential, not simultaneous**: Unlike CONC, links are traversed one at a time
   in order.
2. **Conditioned reinforcers**: The SD for each subsequent link functions as a
   conditioned reinforcer for completing the previous link.
3. **Terminal link governs preference**: In a concurrent-chains procedure, organisms
   prefer the chain that leads more quickly (fewer/easier links) to the terminal
   reinforcer. The terminal link's schedule determines the conditioned reinforcing
   value of each initial-link SD.
4. **Strength decreases across links from terminal**: Responding is strongest in the
   terminal link (closest to primary reinforcer) and weakest in the initial link
   (farthest). This gradient is the "goal gradient."
5. **CHAIN vs. TAND**: Chained has unique SDs per link (conditioned reinforcers);
   Tandem has the same or no SDs (no conditioned reinforcement within the compound).

Distinct from **Behavioral Chaining** (spec 09), which refers to linking discrete
responses into a behavior chain. Chained *schedules* link response requirements
(ratios, intervals) with conditioned reinforcers between links.

## Learning Objective
Participants:
1. Experience the two-link CHAIN FR FR and observe how the conditioned reinforcer
   (SD for Link 2) functions as a reinforcer for Link 1 behavior.
2. Observe the goal gradient — responding accelerates as Mario approaches the
   terminal reinforcer.
3. Distinguish CHAIN from TAND — understand that the SD in CHAIN has added
   conditioned reinforcing value.

## Behavioral Target
- **Response**: Hitting ? blocks (one response = one block hit)
- **CHAIN FR3 FR3**: Link 1 = FR3; completing it produces SD2 (coin trail appears);
  Link 2 = FR3 under SD2; completing it produces primary reinforcer (large coin)
- **CHAIN FR5 FR3**: Longer initial link, shorter terminal link
- **CHAIN FR3 FR5**: Shorter initial link, longer terminal link
- **Conditioned reinforcer**: Visual change (background color shift or new element
  appearing) signals entry into Link 2
- **Primary reinforcer**: Star or large coin at end of terminal link

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | ~60 tiles per chain | Same |

---

## Demo Level Design

### Layout
```
CHAIN FR3 FR3:

LINK 1 — SD1 (ground, daytime — initial link context)
  ? blocks at x=2, 4, 6 (FR3 requirement).
  After 3rd hit: Blue coin trail appears (P-switch activates) → this is SD2 (CRF for Link 2).
  The blue coin trail IS the conditioned reinforcer.

LINK 2 — SD2 (blue coin trail active — terminal link context)
  ? blocks at x=10, 12, 14 (FR3 requirement under SD2).
  After 3rd hit in Link 2: Large coin / Star delivered (PRIMARY reinforcer).
  P-switch expires; return to Link 1 via loop pipe.

Visual change between links: When P-switch activates, blue coin trail appears.
This is visible, distinctive, and marks the onset of Link 2.
```

> Note: P-switch in SMM2 lasts 10 seconds. Time Link 2 so that 3 hits can be completed
> within 10 s (easily done). If time runs out before Link 2 is completed, the chain
> breaks (no primary reinforcer). This creates urgency in the terminal link.

### Three conditions for demo
1. **CHAIN FR3 FR3**: Balanced links. Both require same effort.
2. **CHAIN FR5 FR3**: Long initial, short terminal. Goal gradient visible — slow
   in Link 1, fast in Link 2.
3. **CHAIN FR3 FR5**: Short initial, long terminal. Conditioned reinforcer value
   of SD2 may decrease because terminal link is more effortful.

### Instructor Script Notes
1. "I'm starting in Link 1 — notice the plain background."
   Hit 3 blocks. Blue coins appear. "See the blue trail? That's my signal that
   I've earned access to Link 2. It's also a reward in itself — a conditioned reinforcer."
2. "Now I'm in Link 2 — I need 3 more hits to get the real prize."
   Hit 3 blocks. Star appears. "There's my primary reinforcer."
3. Long initial link demo: "When Link 1 is long, I go slowly at first.
   Then once I get the blue trail, I speed up — I'm close to the reward."
4. "This acceleration toward the reinforcer is the goal gradient."
5. Debrief: "Chained schedules create a chain of conditioned reinforcers.
   The blue trail is only a reinforcer because of what follows it.
   Without the primary reinforcer at the end, the blue trail would lose its value."

---

## Practice / Research Level Design

### Design: Within-subject, three CHAIN conditions + TAND comparison
```
Condition A: CHAIN FR3 FR3 — 20 trials
Condition B: CHAIN FR5 FR3 — 20 trials
Condition C: CHAIN FR3 FR5 — 20 trials
Condition D: TAND FR3 FR3 — 20 trials (comparison to spec 20)
Order counterbalanced; conditions A–C always before D.
```

### Contingency Parameters
| Condition | Link 1 Req | Link 2 Req | SD Change at Link 1 Completion | Terminal SR |
|---|---|---|---|---|
| CHAIN FR3 FR3 | FR3 | FR3 | Yes (blue coins appear) | Large coin/Star |
| CHAIN FR5 FR3 | FR5 | FR3 | Yes | Large coin/Star |
| CHAIN FR3 FR5 | FR3 | FR5 | Yes | Large coin/Star |
| TAND FR3 FR3 | FR3 | FR3 | No (no visual change) | Large coin/Star |

### Procedural Notes
- Participant instructions: "Hit blocks in this level. You'll eventually earn a special
  reward at the end of each run."
- Do NOT describe the links or the blue trail as signals.
- Observer codes: L1_RESP for each response in Link 1; L1_SR when SD2 appears (blue
  trail) — this is the conditioned reinforcer; L2_RESP for each response in Link 2;
  TERM_SR when primary reinforcer is delivered; CHAIN_BREAK if P-switch expires before
  Link 2 is completed.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Link 1 schedule | FR3, FR5 |
| Link 2 schedule | FR3, FR5 |
| SD at link transition | Present (CHAIN), Absent (TAND) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| L1_RESP | Response in Link 1 | Each block hit in Link 1 |
| L1_SR | Conditioned reinforcer onset (SD2 appears) | When P-switch activates |
| L2_RESP | Response in Link 2 | Each block hit in Link 2 |
| L2_SR | Secondary conditioned SR (if 3-link chain) | n/a for 2-link |
| TERM_SR | Primary (terminal) reinforcer delivered | When star/large coin collected |
| CHAIN_BREAK | Chain broken (timeout or error) | If P-switch expires before terminal SR |

---

## Analysis Notes
- **Goal gradient**: Plot response rate (or inter-response time) by link position
  across trials. Expected: IRT decreases (rate increases) in Link 2 vs. Link 1
  under CHAIN conditions.
- **Link 1 rate by condition**: Compare L1_RESP rate across conditions where Link 2
  differs (FR3 vs. FR5). Prediction: L1 rate higher when Link 2 is easier (faster
  access to terminal SR).
- **CHAIN vs. TAND**: Compare overall trial completion rate and response rate in
  Link 1 under CHAIN FR3 FR3 vs. TAND FR3 FR3. Prediction: CHAIN faster (conditioned
  reinforcer in Link 1 provides additional motivation).
- **Chain breaks**: Rate of CHAIN_BREAK by condition — longer chains should produce
  more breaks.

## Observer Notes
- L1_SR is logged when the P-switch visually activates (blue coins appear on screen),
  not when Mario hits the P-switch.
- TERM_SR is logged when the primary reinforcer appears (star sparkle / large coin).
- CHAIN_BREAK: if P-switch times out before all Link 2 blocks are hit, log CHAIN_BREAK
  and note trial number. The trial is then invalid for TERM_SR.
- IOA: L1_RESP and L2_RESP require both observers to agree on which link Mario is in.
  Use the P-switch activation (L1_SR) as the unambiguous link-transition marker.

## Replication Notes
- Course ID (CHAIN FR3 FR3): XXXX-XXXX-XXXX-XXXX
- Course ID (CHAIN FR5 FR3): XXXX-XXXX-XXXX-XXXX
- Course ID (CHAIN FR3 FR5): XXXX-XXXX-XXXX-XXXX
- P-switch must be accessible to participant (placed in Link 1 start area).
- P-switch duration must be calibrated to allow Link 2 completion with time to spare.
  For FR5 Link 2: 5 hits in 10 s is achievable; verify with test play.
- Primary reinforcer: use a Star (invincibility star) for maximum salience.

## Key References
- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of Reinforcement*.
  Appleton-Century-Crofts. (pp. 595–631, chained schedules)
- Kelleher, R. T., & Gollub, L. R. (1962). A review of positive conditioned
  reinforcement. *Journal of the Experimental Analysis of Behavior, 5*, 543–597.
- Hull, C. L. (1932). The goal-gradient hypothesis. *Psychological Review, 39*, 25–43.
- Autor, S. M. (1969). The strength of conditioned reinforcers as a function of
  frequency and probability of reinforcement. In D. P. Hendry (Ed.),
  *Conditioned Reinforcement*. Dorsey Press.
