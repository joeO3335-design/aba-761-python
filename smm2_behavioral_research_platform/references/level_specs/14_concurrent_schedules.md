# Level Spec: Concurrent Schedules (CONC)

---

## Phenomenon
Concurrent schedules (CONC) arrange two or more independent reinforcement schedules
simultaneously, each associated with a distinct operandum. The organism allocates
responses freely between alternatives at any time (Catania, 1966; Herrnstein, 1961).

Key properties distinguishing CONC from other compound schedules:
1. **Simultaneous availability**: Both schedules are always "on"; no stimulus signals
   which is richer at any moment (unless a Concurrent Multiple is arranged).
2. **Independent operation**: Each schedule runs its own clock/counter regardless of
   responding on the other alternative.
3. **Free switching**: The organism can change operanda at will; there is no forced
   transition and no changeover delay (COD) in the basic CONC arrangement.
4. **Changeover Delay (COD)**: When a COD is imposed, reinforcement cannot be
   collected immediately after switching — this prevents exclusive preference due to
   adventitious immediate switching.

CONC is the paradigmatic preparation for the Matching Law (see spec 10), but as a
standalone phenomenon it teaches the basic mechanics of simultaneous choice before
the quantitative matching framework is introduced.

Conditions demonstrated:
- **CONC FR FR**: Both alternatives are fixed-ratio. Exclusive preference for the
  richer FR is expected (no temporal depletion to equalize rates).
- **CONC VI VI**: Both alternatives are variable-interval. Matching emerges as
  organisms distribute responses proportionally to reinforcement rates.
- **CONC with COD**: Adding a 2-response changeover delay reduces switching and
  eliminates adventitious preference for the side most recently reinforced.

## Learning Objective
Participants:
1. Experience making simultaneous free choices between two independently scheduled
   alternatives.
2. Observe their own allocation pattern under FR-FR vs. VI-VI arrangements.
3. Understand the role of the COD in stabilizing choice.
4. Distinguish CONC from ALT (where reinforcement goes to whichever completes first).

## Behavioral Target
- **Response**: Choose left path (B1) or right path (B2) at a central fork
- **CONC FR3 FR9**: Left=FR3 (rich), Right=FR9 (lean), 3:1 ratio
- **CONC VI3s VI9s**: Left=VI3s, Right=VI9s, 3:1 ratio
- **COD condition**: 2-response changeover delay imposed on all switching
- **Consequence**: Coins proportional to schedule richness
- **Antecedent**: Visible fork; both paths always available; loop returns to fork

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

### Layout
```
SECTION A — CONC FR3 FR9 (no COD)
  Symmetric fork. Loop returns Mario to fork after each path.

  Left path  [FR3]:  3 ? blocks, 1 coin per trip (FR3)
                     Path length: 6 tiles.

  Right path [FR9]:  9 ? blocks, 1 coin per 3 trips (FR9)
                     Path length: 18 tiles.

  Expected: instructor rapidly settles on LEFT exclusively.

SECTION B — CONC VI3s VI9s (no COD)
  Same fork. VI coin availability approximated by P-switch-timed gates.
  Left:  coin available every ~3 s on average
  Right: coin available every ~9 s on average
  Expected: instructor distributes ~75% left / ~25% right.

SECTION C — CONC VI3s VI9s WITH COD (2-response delay)
  Same fork. After switching sides, first 2 block hits yield nothing
  (represented by 2 used blocks immediately after the fork junction).
  Expected: slightly less switching; matching still emerges.
```

### Mechanics
- ? block sequences: FR-FR section
- P-switch-timed coin gates: VI-VI section
- Used blocks at changeover entry: COD simulation
- Looped pipes: discrete-trial choice structure
- Identical fork geometry across all sections

### Instructor Script Notes
1. CONC FR-FR: "Both paths are always available. I can switch freely.
   Watch where I go." — Show exclusive left preference.
   "I never go right because left always pays off — no depletion."
2. CONC VI-VI: "Now rewards appear unpredictably on each side independently.
   Watch me start distributing." — Show ~75/25 split.
3. COD condition: "If I add a penalty for switching — 2 wasted hits —
   watch how my switching rate drops, but matching still holds."
4. Debrief: "CONC means both are always on. The organism allocates.
   The ratio of allocation equals the ratio of reinforcement rates.
   That's the Matching Law in action."

---

## Practice / Research Level Design

### Design: Within-subject, three conditions, counterbalanced
```
Condition A: CONC FR3 FR9 (no COD) — 40 choices
Condition B: CONC VI3s VI9s (no COD) — 40 choices
Condition C: CONC VI3s VI9s + COD — 40 choices
Order counterbalanced across participants (Latin square, 6 orders).
15-minute break between conditions.
```

### Contingency Parameters — CONC FR3 FR9
| Parameter | Left (FR3) | Right (FR9) |
|---|---|---|
| Schedule | FR3 | FR9 |
| Path length (tiles) | 6 | 18 |
| Coins per completed ratio | 1 | 1 |
| Reinforcement rate (exclusive) | 1 per 3 responses | 1 per 9 responses |

### Contingency Parameters — CONC VI3s VI9s
| Parameter | Left (VI3s) | Right (VI9s) |
|---|---|---|
| Schedule | VI3s | VI9s |
| Mean interval (s) | 3 | 9 |
| VI sequences | 1,4,2,5,3,4,1,6,2,4 s | 5,12,7,11,9,8,10,13,6,9 s |
| Path length (tiles) | 6 | 6 (equal) |

### COD Condition
- 2 used blocks immediately after the changeover point on each side
- First 2 hits after switching yield nothing (COD = 2 responses)
- Coded as CHANGEOVER event; subsequent responses coded normally

### Procedural Notes
- Participant instructions: "Keep coming back to the fork. Go whichever way you want.
  Try to collect as many coins as possible."
- Do NOT describe schedules or the COD.
- Observer codes: L_RESP / R_RESP at each response; L_SR / R_SR at each coin;
  SWITCH when changeover occurs; CHANGEOVER for each COD response.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Schedule type | FR-FR, VI-VI |
| COD | Absent, Present (2 responses) |
| Richness ratio | 3:1 (fixed across conditions) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| L_RESP | Response on left alternative | Each left hit/step |
| R_RESP | Response on right alternative | Each right hit/step |
| L_SR | Coin on left | On coin contact, left |
| R_SR | Coin on right | On coin contact, right |
| SWITCH | Changeover from one side to the other | At the fork, when direction changes |
| CHANGEOVER | Response during COD (wasted hit) | Each of first 2 hits post-switch |
| NR | Pause ≥3 s at fork with no response | At pause onset |

---

## Analysis Notes
- **Matching**: Compute B_L/(B_L+B_R) vs. R_L/(R_L+R_R). Test deviation from
  strict matching (a=1, b=1 in GML).
- **Undermatching** expected under FR-FR (exclusive preference off the matching line).
- **COD effect**: Compare switching frequency and matching fit with vs. without COD.
  COD should increase matching fit (reduce bias toward the more recently reinforced side).
- **Changeover rate**: COD condition should show fewer SWITCHes per session.

## Observer Notes
- SWITCH is coded when Mario enters the other path's corridor at the fork.
- CHANGEOVER is coded for each response during the COD window (max 2 per switch).
- Under FR-FR, if participant makes ≥20 consecutive L_RESP, code EXCLUSIVE (companion
  app note field).

## Replication Notes
- Course ID (CONC FR-FR): XXXX-XXXX-XXXX-XXXX
- Course ID (CONC VI-VI no COD): XXXX-XXXX-XXXX-XXXX
- Course ID (CONC VI-VI + COD): XXXX-XXXX-XXXX-XXXX
- VI sequences must be identical across sessions for replication (see parameters.json).
- Path lengths MUST be equal in VI-VI conditions (travel time bias).

## Key References
- Herrnstein, R. J. (1961). Relative and absolute strength of response as a function
  of frequency of reinforcement. *Journal of the Experimental Analysis of Behavior, 4*, 267–272.
- Catania, A. C. (1966). Concurrent operants. In W. K. Honig (Ed.),
  *Operant Behavior* (pp. 213–270). Appleton-Century-Crofts.
- Shull, R. L., & Pliskoff, S. S. (1967). Changeover delay and concurrent schedules.
  *Journal of the Experimental Analysis of Behavior, 10*, 517–527.
- Baum, W. M. (1974). On two types of deviation from the matching law.
  *Journal of the Experimental Analysis of Behavior, 22*, 231–242.
