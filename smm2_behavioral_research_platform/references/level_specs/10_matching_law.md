# Level Spec: Matching Law

---

## Phenomenon
The matching law (Herrnstein, 1961): when an organism can respond on two or
more concurrently available schedules of reinforcement, the proportion of
responses allocated to each alternative matches the proportion of reinforcers
obtained from that alternative.

  B1 / (B1 + B2)  =  R1 / (R1 + R2)

The generalized matching law (Baum, 1974) accounts for bias and sensitivity:

  log(B1/B2) = a·log(R1/R2) + log(b)

## Learning Objective
Participants allocate responses between two simultaneously available paths.
Observer data allow fitting the GML and estimating sensitivity (a) and bias (b).
Participants observe that response allocation tracks reinforcement allocation,
not just which alternative "feels" better.

## Behavioral Target
- **Response**: Choosing left path (B1) or right path (B2) at a fork
- **Left path SR+**: Coins dispensed at a higher scheduled rate (rich schedule)
- **Right path SR+**: Coins dispensed at a lower scheduled rate (lean schedule)
- **Antecedent**: Simultaneous fork — both paths visually available

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Looped (participant returns to fork repeatedly) | Same |

---

## Demo Level Design
**Purpose**: Instructor demonstrates response allocation shift as reinforcement
ratios change across schedule conditions.

### Layout
```
Central fork (repeated via pipe loop back to start after each path)

Left path   [Rich]
  Coins placed every 2 tiles (high density)
  Path length: 8 tiles → return pipe to fork

Right path  [Lean]
  Coins placed every 6 tiles (low density)
  Path length: 8 tiles → return pipe to fork

[Fork area: one-tile-wide junction, participant moves left or right]
[Paths are symmetric in length and obstacle difficulty]
[Both paths lead to return pipe at end that brings Mario back to fork]
```

### Schedule Conditions (3 rounds of 20 choices each)
| Condition | Left (R1) | Right (R2) | R1:R2 Ratio |
|---|---|---|---|
| A | FR1 (dense) | FR3 (sparse) | 3:1 |
| B | FR2 | FR2 | 1:1 |
| C | FR3 (sparse) | FR1 (dense) | 1:3 |

### Mechanics Used
- Coin placement density: operationalizes schedule richness
- Return pipes: create a concurrent VI-like structure via repeated discrete trials
- Symmetric path length: removes travel time as a confound

### Instructor Script Notes
1. Condition A: "Left path has more coins per length. Let's watch where I go."
   Play 10 choices. "Notice I prefer left — makes sense."
2. Condition B: "Now both paths equal." Play 10 choices. "My allocation spreads out."
3. Condition C: "Now right is richer." Play 10 choices. "Allocation shifts to right."
4. Debrief: "The proportion of choices matched the proportion of reinforcers.
   This is the matching law."

---

## Practice / Research Level Design
**Purpose**: Participant makes free choices across multiple ratio conditions.
Response allocation data are collected for GML fitting.

### Design: Within-subject, counterbalanced ratio conditions
```
Session 1: Condition A (Left rich 3:1)  — 30 choices
Session 2: Condition B (Equal 1:1)       — 30 choices
Session 3: Condition C (Right rich 1:3) — 30 choices
Session 4: Condition D (Left rich 5:1)  — 30 choices
Session 5: Condition E (Right rich 1:5) — 30 choices

Order counterbalanced across participants using Latin square.
```

### Contingency Parameters
| Condition | Left coins per path traversal | Right coins per path traversal | Ratio |
|---|---|---|---|
| A | 3 | 1 | 3:1 |
| B | 2 | 2 | 1:1 |
| C | 1 | 3 | 1:3 |
| D | 5 | 1 | 5:1 |
| E | 1 | 5 | 1:5 |

| Parameter | Value |
|---|---|
| Choices per session | 30 |
| Path length (both) | 8 tiles |
| Return pipe | Yes (loops to fork) |
| Inter-choice interval | None (immediate return via pipe) |
| Sessions | 5 (one per condition) |
| Session order | Counterbalanced (Latin square) |

### Procedural Notes
- Participant instructions: "You'll keep coming back to a fork. Go whichever
  way you want each time."
- Do NOT mention reinforcement ratios.
- Observer logs LEFT or RIGHT at each fork choice — this is the primary DV.
- Also log which path yielded coins (LEFT_SR or RIGHT_SR) after each traversal.
- One "trial" = one complete path traversal (fork choice → return to fork).
- Change coin placement between sessions by switching course IDs.
- Allow 5-minute break between sessions.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Reinforcement ratio (R1:R2) | 3:1, 1:1, 1:3, 5:1, 1:5 |
| Session | 1–5 |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| LEFT | Participant takes left path at fork | At fork choice |
| RIGHT | Participant takes right path at fork | At fork choice |
| LEFT_SR | Coin collected on left path | On coin contact |
| RIGHT_SR | Coin collected on right path | On coin contact |
| SCHED_SWITCH | New session/condition beginning | At session start |
| EXCLUSIVE | Participant makes ≥10 consecutive choices on one side | After 10th consecutive |

---

## Analysis Notes
From the exported CSV, compute per session:
- B1 = count of LEFT events
- B2 = count of RIGHT events
- R1 = count of LEFT_SR events
- R2 = count of RIGHT_SR events
- Matching ratio = B1/(B1+B2) vs. R1/(R1+R2)
- GML fit: log(B1/B2) ~ a * log(R1/R2) + log(b)
  - Sensitivity a < 1.0 = undermatching
  - Sensitivity a > 1.0 = overmatching
  - Bias b ≠ 1.0 = systematic side preference

## Observer Notes
- Log LEFT or RIGHT at the moment the participant commits to one side
  (both feet past the fork junction).
- EXCLUSIVE is a supplementary observation — log if it occurs, but it is not
  the primary DV.
- IOA: Two observers classify each fork choice as LEFT or RIGHT; target
  100% agreement (discrete, unambiguous event).
- If participant stops at fork for >5 seconds, note in the Note field as
  "hesitation" — may indicate indifference near equal schedules.

## Replication Notes
- Course IDs (one per condition):
  - Condition A: XXXX-XXXX-XXXX-XXXX
  - Condition B: XXXX-XXXX-XXXX-XXXX
  - Condition C: XXXX-XXXX-XXXX-XXXX
  - Condition D: XXXX-XXXX-XXXX-XXXX
  - Condition E: XXXX-XXXX-XXXX-XXXX
- Verify path lengths are tile-identical before data collection.
- Count coins placed in each path with a test run before each session.
