# Level Spec: Shaping

---

## Phenomenon
Shaping (successive approximation): reinforcing progressively closer
approximations to a terminal behavior until the full target response is achieved.

## Learning Objective
Participants experience or observe that complex behavior can be built from
simpler components by differentially reinforcing successive approximations,
and that each new criterion raises the bar while extinguishing earlier,
simpler forms of the response.

## Behavioral Target
- **Terminal behavior**: Completing a multi-step precision jump sequence
  (low platform → medium platform → high platform → moving platform)
- **Starting behavior**: Simply moving forward (stepping onto low platform)
- **Consequence**: Coin delivered for meeting the current criterion
- **Antecedent**: Visual boundary marker (colored pipe) signals current criterion zone

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Long (~180 tiles) | Long (~180 tiles) |

---

## Demo Level Design
**Purpose**: Instructor plays while narrating. Students observe criterion shifts.

### Layout
```
Step 1  — Walk forward and step onto a 1-tile-high platform
  Low platform, coins dispensed via hidden block above if Mario stands on it.
  Criterion: simply reach platform (any method accepted).

Step 2  — Jump to a 3-tile-high platform
  Requires a small jump. Only the higher landing yields coin.
  Walking up a slope alternative is walled off by a 1-tile gap.

Step 3  — Clear a 5-tile gap with a medium jump
  No slope alternative. Must jump and clear the gap.
  Coin appears only on the far platform.

Step 4  — Land on a moving platform (Donut Lift)
  Platform disappears 2 seconds after landing — must jump quickly to the next
  surface. Coin on next stable surface.

Step 5  — Navigate a tight precision jump corridor
  1-tile-wide path with 1-tile-wide platforms at varying heights.
  Coin at the end of the corridor.
```

### Mechanics Used
- Platform height variation: controls response difficulty
- Hidden blocks above criterion-meeting positions: deliver SR+
- One-way gates between steps: prevent regression

### Instructor Script Notes
1. Step 1: "Right now I'll reinforce any forward progress."
2. Step 2: "Now the criterion has shifted — just walking doesn't pay off. I need
   a small jump."
3. Step 3: "The criterion tightens again — now I need a full jump across a gap."
4. Step 4: "And now I need to land precisely and keep moving."
5. Step 5: "This is the terminal behavior — something that would have been
   impossible to reinforce at the start, but we got here step by step."
6. Debrief: point out extinction of previous approximation at each step.

---

## Practice / Research Level Design
**Purpose**: Participant plays independently. Observer codes approximation-level
achieved and criterion shifts over trials.

### Layout
```
Module A  — Step 1 (CRF for platform approach)
  Hidden block triggers coin when Mario stands on platform.
  One-way door to Module B opens after 3 successful trials.

Module B  — Step 2 (reinforce jump to 3-tile platform only)
  Coins appear only if landing is on high platform.
  One-way door to Module C opens after 3 successful trials.

Module C  — Step 3 (reinforce gap clear)
  Coins appear only on far side of 5-tile gap.
  One-way door to Module D opens after 3 successful trials.

Module D  — Step 4 (moving platform)
  Donut Lift sequence, coin on stable landing.
  One-way door to Module E opens after 3 successful trials.

Module E  — Step 5 (precision corridor)
  Terminal behavior. Coin at end.
  Flagpole ends session.
```

### Contingency Parameters
| Parameter | Value |
|---|---|
| SR+ | 1 coin per successful approximation |
| Criterion shift trigger | 3 consecutive successful trials in current step |
| Steps | 5 |
| Maximum trials per step | 10 (if criterion not met in 10, step is repeated) |
| Backslide rule | If participant fails 3 consecutive trials, return to previous step |

### Procedural Notes
- Participant instructions: "Try to reach the end of the level. The path will
  become clearer as you go."
- Do NOT describe the steps or criterion in advance.
- Observer tracks current step and codes each attempt.
- A "trial" = one attempt to complete the current criterion section
  (ends in success or failure).
- Failure = falling into pit, failing to clear gap, or falling off moving platform.
- Success = reaching the coin on the other side.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Step (approximation level) | 1–5 |
| Criterion shift trigger | 3 consecutive successes |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESPONSE | Any attempt at the current criterion | Trial onset |
| SR_APPROX | Coin received (criterion met) | On coin delivery |
| FAIL | Failure on current criterion (fall, miss, gap fail) | On failure event |
| CRITERION | Criterion shift — moving to next step | When one-way door opens |
| STEP_UP | Observer records which step is now active | After CRITERION |

---

## Observer Notes
- Each trial is one attempt. Log RESPONSE at trial onset (when Mario begins the
  criterion section), then either SR_APPROX (success) or FAIL.
- Use the Note field on STEP_UP to record the step number (e.g., "step 3 → 4").
- Watch for extinction of lower approximations: does participant still attempt
  the previously-reinforced behavior when no longer reinforced? Code as FAIL.
- IOA: Observers should agree on trial outcome (success vs. failure) within
  each trial; no timing required for agreement.

## Replication Notes
- Course ID: XXXX-XXXX-XXXX-XXXX
- All one-way doors must be confirmed one-way before data collection (test with
  naive player).
- Donut Lift disappearance timing is fixed in SMM2 at 2 seconds — no adjustment
  needed; this is a replication-stable parameter.
