# Level Spec: Amelioration

---

## Phenomenon
Amelioration / Melioration (Herrnstein & Vaughan, 1980; Herrnstein, 1990):
organisms allocate behavior to maximize the **local** (momentary) rate of
reinforcement, not the molar (overall) rate.  At any moment, responding shifts
toward the alternative with the higher current local reinforcement rate — the
organism "ameliorates" the inequality between options by shifting toward the
richer one.

Key predictions that distinguish amelioration from the matching law:
1. **Concurrent FR-FR schedules**: amelioration predicts *exclusive* preference
   for the richer option (because visiting the richer option repeatedly never
   depletes the local rate the way VI schedules do).  The matching law also
   predicts exclusive preference on FR-FR, but for different mechanistic reasons.
2. **Concurrent VI-VI schedules**: amelioration and matching law converge —
   matching emerges because shifting to the leaner option after exhausting the
   richer one's local advantage eventually equalizes local rates.
3. **Within-session dynamics**: amelioration predicts that **run lengths** on
   one alternative will be longer after recently experiencing higher local
   rates there, and that **switching** occurs when the current alternative's
   local rate falls below the other's.

This level contrasts FR-FR (where melioration produces exclusive preference and
matching breaks down) with VI-VI (where melioration produces matching), making
the *mechanism* of matching visible rather than just its outcome.

## Learning Objective
Participants observe:
1. That on concurrent FR-FR schedules, they strongly prefer — and may exclusively
   choose — the richer option, even though the matching law also predicts this.
2. That on concurrent VI-VI schedules, responding distributes proportionally
   (matching), and they can identify this as the result of local-rate equalization.
3. That the **process** of repeatedly choosing the momentarily-richer option
   (melioration) is what produces matching at the molar level on VI schedules.

## Behavioral Target
- **Response**: Choosing left path (B1) or right path (B2) at a fork
- **FR-FR condition**: Left = FR3, Right = FR9 (3:1 richness ratio, fixed)
- **VI-VI condition**: Left = VI3s, Right = VI9s (3:1 richness ratio, variable)
- **Consequence**: Coins proportional to schedule richness
- **Antecedent**: Visible fork; both paths available simultaneously

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Looped fork (100 tile loop) | Same |

---

## Demo Level Design
**Purpose**: Instructor demonstrates the contrast between FR-FR (exclusive
preference, melioration visible as runs on rich side) and VI-VI (distributed
responding, local-rate equalization).

### Layout
```
CONDITION A — Concurrent FR-FR (3:1)
  Fork at center. Loop returns Mario to fork after each path.

  Left path  [RICH]:  ? block every 2 tiles → 1 coin per 3-block group (FR3)
                      Path length: 6 tiles. Reinforcers available: 2 per visit.

  Right path [LEAN]:  ? block every 6 tiles → 1 coin per 9-block group (FR9)
                      Path length: 18 tiles. Reinforcers available: 1 per 3 visits.

  Prediction: instructor will rapidly settle on LEFT exclusively.
  Show: "If I leave left and go right, I get less. So I stay left."

CONDITION B — Concurrent VI-VI (3:1 expected value)
  Same fork. Coin delivery via timed switch that opens/closes at variable intervals.
  Left:  VI3s  (coin available on average every 3 s)
  Right: VI9s  (coin available on average every 9 s)

  Prediction: instructor distributes ~75% left, ~25% right — matching.
  Show: "Even though left is richer, I still sometimes go right —
         because after a few visits, the local rate on left drops
         (I've already collected available coins) and right becomes
         temporarily more attractive."
```

### Mechanics Used
- ? blocks with preset coin/no-coin sequences: FR-FR condition
- P-switch timed doors: approximate VI-VI condition
- Looped return pipes: create repeated discrete choice trials
- Same fork geometry across both conditions: isolates schedule type as IV

### Instructor Script Notes
1. FR-FR condition: "Watch where I go." Play 20 choices.
   Count consecutive left runs: "Did you see me get stuck on left?
   That's exclusive preference. The local rate on left is always higher
   because I never exhaust it — every visit pays off equally."
2. VI-VI condition: "Now the coins appear unpredictably."
   Play 20 choices. "I still prefer left, but now I go right sometimes.
   Why? Because once left stops paying off in the short run, right looks
   better momentarily."
3. Debrief: "On FR-FR, local rates never equalize — melioration produces
   exclusive preference. On VI-VI, local rates do equalize — melioration
   produces matching. Same mechanism, different outcomes."

---

## Practice / Research Level Design
**Purpose**: Participant makes free choices under FR-FR and VI-VI conditions.
Observer codes choice sequences for molar allocation AND local switching patterns.

### Design: Within-subject, two conditions, counterbalanced
```
Condition A: FR-FR (3:1) — 40 choices
Condition B: VI-VI (3:1) — 40 choices
Order counterbalanced: half of participants do A→B, half do B→A.
15-minute break between conditions (load different course ID).
```

### Contingency Parameters — FR-FR Condition
| Parameter | Left (Rich) | Right (Lean) |
|---|---|---|
| Schedule | FR3 | FR9 |
| Coins per reinforced visit | 1 | 1 |
| Path length (tiles) | 6 | 18 |
| Expected reinforcers per 40 choices (exclusive left) | ~13 | 0 |
| Expected reinforcers per 40 choices (matching ~75/25) | ~10 | ~1 |

### Contingency Parameters — VI-VI Condition
| Parameter | Left (Rich) | Right (Lean) |
|---|---|---|
| Schedule | VI3s | VI9s |
| Mean interval (s) | 3 | 9 |
| VI sequences | 1,4,2,5,3,4,1,6,2,4 s | 5,12,7,11,9,8,10,13,6,9 s |
| Path length (tiles) | 6 | 6 (equal — no travel cost bias) |

### Procedural Notes
- Participant instructions: "You'll keep coming back to a fork. Go whichever
  way you want. Try to collect as many coins as possible."
- Do NOT name or describe the schedule conditions.
- Observer logs LEFT or RIGHT at each fork choice (primary DV).
- Observer also logs LEFT_SR or RIGHT_SR when coins are actually delivered.
- Observer logs SHIFT_RICH when participant switches to the currently richer
  option after ≥2 consecutive visits to the other option.
- Observer logs EXCLUSIVE when participant makes ≥10 consecutive choices on one side.
- Observer logs LOCAL_EQ when switching frequency increases and choices appear
  roughly alternating (operationalized as ≤2 consecutive choices on either side
  for ≥5 consecutive choices total).
- 40 choices per condition; 5-minute rest between conditions.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Schedule type | FR-FR (3:1), VI-VI (3:1) |
| Session order | Counterbalanced (A→B or B→A) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| LEFT | Left path chosen at fork | At each choice |
| RIGHT | Right path chosen at fork | At each choice |
| LEFT_SR | Coin collected on left path | On coin contact |
| RIGHT_SR | Coin collected on right path | On coin contact |
| SHIFT_RICH | Switch to the momentarily richer option | After ≥2 visits away |
| EXCLUSIVE | ≥10 consecutive choices on one side | After 10th consecutive |
| LOCAL_EQ | Local rates appear equalized (alternating pattern) | Observer judgment |

---

## Analysis Notes

### Molar analysis (matching)
- Compute B1/(B1+B2) and R1/(R1+R2) per condition
- Fit GML: log(B1/B2) = a·log(R1/R2) + log(b)
- Expected: FR-FR → low a (flat matching, exclusive preference off the line)
            VI-VI → a ≈ 1 (close to strict matching)

### Melioration / local-rate analysis
- **Run-length analysis**: compute average consecutive choices on left vs. right.
  FR-FR prediction: longer runs than VI-VI.
- **Switching after local rate depletion**: does switching occur when the
  chosen option stops delivering (FR-FR: never; VI-VI: yes, after coin window closes)?
- **Local reinforcement rate**: rolling 5-choice window of reinforcers received
  from each alternative. Plot over trial sequence.
  Expected: VI-VI shows oscillating local rates that converge; FR-FR shows
  persistent advantage for left if participant stays left.

### Distinguishing amelioration from matching-law accounts
- The matching law predicts both FR-FR exclusive preference and VI-VI matching
  from a molar description.
- Amelioration/melioration makes the *additional* prediction that switching
  within a session tracks **local** rate fluctuations.
- If switching is correlated with local rate advantage (not just molar ratio),
  this supports a melioration account.
- Test: `P(switch to left | local_rate_left > local_rate_right)` vs.
         `P(switch to left | local_rate_left < local_rate_right)`.
  Melioration predicts the former > the latter.

## Observer Notes
- SHIFT_RICH requires observer to track current run length. Use the Note field
  to record the current run ("after 3 rights, shift to left").
- LOCAL_EQ is the most subjective code; IOA training should use video examples.
  Alternative: compute it post-hoc from the CSV rather than coding live.
- IOA: LEFT/RIGHT choices should achieve 100% agreement (discrete, unambiguous).
  SHIFT_RICH: ≥80% agreement using a 2-choice window.

## Replication Notes
- Course ID (FR-FR condition): XXXX-XXXX-XXXX-XXXX
- Course ID (VI-VI condition): XXXX-XXXX-XXXX-XXXX
- VI sequences are preset (not random) for replication:
  Left VI3s:  1,4,2,5,3,4,1,6,2,4 s
  Right VI9s: 5,12,7,11,9,8,10,13,6,9 s
- Path lengths must be equal in VI-VI condition to remove travel-time bias.
  Verify before data collection.

## Key References
- Herrnstein, R. J., & Vaughan, W. (1980). Melioration and behavioral allocation.
  In J. E. R. Staddon (Ed.), *Limits to Action* (pp. 143–176). Academic Press.
- Herrnstein, R. J. (1990). Behavior, reinforcement and utility.
  *Psychological Science, 1*, 217–224.
- Vaughan, W. (1981). Melioration, matching, and maximization.
  *Journal of the Experimental Analysis of Behavior, 36*, 141–149.
- Davison, M., & McCarthy, D. (1988). *The Matching Law: A Research Review*.
  Lawrence Erlbaum Associates.
