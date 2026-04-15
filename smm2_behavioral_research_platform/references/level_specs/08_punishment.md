# Level Spec: Punishment

---

## Phenomenon
Punishment: a response decreases in frequency when followed by the contingent
delivery of an aversive stimulus (positive punishment) or the removal of a
positive stimulus (negative punishment / response cost).

## Learning Objective
Participants observe that a previously occurring response decreases when it
produces an aversive consequence, and they can distinguish positive punishment
(aversive added) from negative punishment / response cost (reinforcer removed).

## Behavioral Target
- **Punished response**: Taking a specific path or hitting a specific type of block
- **Positive punishment**: Contact with a Buzzy Beetle (power-up loss / death)
  when going through the punished path
- **Response cost**: Entering a pipe that removes coins already collected
- **Alternative response**: Taking the clearly marked safe path (no punisher)
- **Antecedent**: Forking path; punished route is visually tempting (coins appear
  visible ahead) but leads to punisher

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Super Mario | Super Mario |
| Auto-scroll | Off | Off |
| Level Length | Medium (~100 tiles) | Medium (~100 tiles) |

---

## Demo Level Design
**Purpose**: Instructor demonstrates both punishment types and their effects
on response allocation.

### Layout
```
Section A  — Positive Punishment (power-up loss)
  Fork in the road.
  Left path: visible coins on ground → Buzzy Beetle hidden just past coin cluster.
             Taking this path and contacting Buzzy Beetle = lose power-up.
  Right path: Safe (no coins visible, no hazard).

  Baseline: Instructor takes left path several times, noting response to coins.
  After consistent punishment: Instructor shifts to right path.
  "Notice that I stopped taking the tempting left route."

Section B  — Response Cost (negative punishment)
  Fork in the road.
  Left path: visible coins → entry pipe that removes 10 coins from counter.
  Right path: Safe path with 3 coins.

  Demonstrate left path first → coin loss.
  Then demonstrate right path → stable coin accumulation.
  "Entering that pipe cost me coins. The response (entering the pipe) decreased."

Section C  — Control / Reversal
  Left path hazard or cost removed.
  Show that left path responding returns — demonstrating that it was the
  punisher that suppressed it, not something else about the route.
```

### Mechanics Used
- Buzzy Beetles: positive punisher (aversive added on contact)
- Coin-removing pipe (via sub-area that resets without awarding coin): response cost
- Fork layouts: create discrete choice between punished and unpunished routes
- Super Mario start: allows power-up loss without death for positive punishment section

### Instructor Script Notes
1. Section A, first pass: "I'm going to take the left path — there are coins
   there." Take it. Contact Buzzy. "I lost my power-up."
2. Take it again: "Let me try again..." Contact again.
3. After 2–3 contacts: take right path. "I stopped going left. The punishment
   suppressed that response."
4. Section B: "This time I'll lose coins. Watch my allocation shift."
5. Control: "Now I've removed the punisher. Watch what happens to the left path."
6. Debrief: distinguish positive punishment from response cost; both suppress.

---

## Practice / Research Level Design
**Purpose**: Participant plays independently across punishment and reversal
conditions.

### Design: ABAB reversal
```
Phase A1  — Punishment active (left path has Buzzy Beetle, 10 trials)
Phase B1  — Punishment removed (both paths safe, 10 trials)
Phase A2  — Punishment reinstated (10 trials)
Phase B2  — Punishment removed again (10 trials)
```
Each trial = one fork encounter.

### Contingency Parameters
| Parameter | Value |
|---|---|
| Punisher type | Positive punishment (Buzzy Beetle contact → lose power-up) |
| Starting state | Super Mario (so contact = demotion to Small, not death) |
| Punished path | Left fork |
| Unpunished path | Right fork |
| Left path temptation | 3 visible coins before Buzzy zone |
| Right path coins | 1 coin |
| Trials per phase | 10 (10 fork encounters) |
| Phases | A1, B1, A2, B2 |

### Procedural Notes
- Participant instructions: "Play through the level and collect coins."
- Do NOT mention the punisher or its contingency.
- Observer codes left vs. right choice at each fork as the primary DV.
- A "trial" begins when the participant reaches a fork and ends when they have
  cleared the chosen path and reached the next open corridor.
- If participant contacts Buzzy Beetle in a non-punishment phase (level builder
  error), note and exclude that trial.
- Participant starts each phase as Super Mario (checkpoint restores power-up).

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Punishment condition | Active (A phases), Absent (B phases) |
| Phase | A1, B1, A2, B2 |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| TARGET_RESP | Participant takes the punished (left) path | At fork choice |
| PUNISHER | Buzzy Beetle contact / power-up loss occurs | On contact |
| SUPPRESSED | Participant takes safe (right) path | At fork choice |
| ESCAPE_ATT | Participant starts left path then reverses mid-path | On reversal |
| AGGRESSION | Participant repeatedly walks into Buzzy Beetle | On repeated contact |

---

## Observer Notes
- TARGET_RESP and SUPPRESSED are mutually exclusive per trial — log one per fork.
- ESCAPE_ATT: if participant begins the left path and then turns back before
  reaching the Buzzy zone, code as ESCAPE_ATT with note "aborted left path."
- AGGRESSION: operationally defined as ≥3 contacts with the same Buzzy Beetle
  in one trial without forward progress.
- IOA: Two observers classify fork choice (left vs. right) — trial-by-trial
  agreement.  Target ≥90% agreement before data collection begins.

## Replication Notes
- Course ID (punishment active level): XXXX-XXXX-XXXX-XXXX
- Course ID (punishment removed level): XXXX-XXXX-XXXX-XXXX
- ABAB requires switching between two uploaded course IDs at each phase
  transition.  Brief pause between phases (~2 min) acceptable.
- Confirm Buzzy Beetle patrol range is contained within the left path corridor
  so it never enters the right path.
- Super Mario starting state at each checkpoint is essential — verify with test
  run before data collection.
