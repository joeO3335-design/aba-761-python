# Level Spec: Multiple Schedules (MULT)

---

## Phenomenon
A Multiple schedule (MULT) presents two or more component schedules in succession,
each signaled by a distinct **discriminative stimulus** (SD). Only one component is
in effect at a time; when the SD changes, so does the schedule (Ferster & Skinner, 1957).

Key properties:
1. **Alternating components**: Components alternate in time (fixed or random duration).
2. **Correlated SDs**: Each component has a unique antecedent stimulus; behavior comes
   under stimulus control of these SDs.
3. **Behavioral contrast**: If one component is enriched, responding in the other
   component often decreases (negative contrast); if one is impoverished, responding
   in the other increases (positive contrast). Contrast is the signature phenomenon
   studied with MULT.
4. **MULT vs. MIX**: MULT has SDs; Mixed (MIX) has the same schedule alternation
   but *without* discriminative stimuli. Comparing MULT and MIX reveals the role
   of the SD in shaping responding.

Classic MULT example: **MULT VI EXT** — responding is reinforced on VI schedule
during one SD, extinguished during another. Behavioral contrast predicts that
responding during the VI component increases when the EXT component is added.

This level focuses on **MULT VI EXT** as the prototypical case, with the
night/sunset visual distinction (already used in Stimulus Control) as the SD pair.

## Learning Objective
Participants:
1. Experience differential responding under two correlated SDs.
2. Observe behavioral contrast — that enriching or impoverishing one component
   affects responding in the other.
3. Distinguish MULT (SD-signaled schedule change) from MIX (unsignaled change).

## Behavioral Target
- **Response**: Hitting ? blocks from below
- **Component 1 (SD1 = Night background)**: VI5s schedule — ? blocks pay off
  on average every 5 seconds
- **Component 2 (SD2 = Sunset background)**: EXT schedule — ? blocks never pay off
- **Contrast manipulation**: Baseline MULT VI EXT → Enrich Component 2 to VI5s →
  Return to EXT (observe contrast effects on Component 1 responding)
- **Consequence**: Coins in VI component; nothing in EXT component
- **Antecedent**: Background filter (night or sunset) as discriminative stimulus

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Filter | Night (SD1), Sunset (SD2) | Same |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Long (~200 tiles); alternating sub-areas | Same |

---

## Demo Level Design

### Implementation via Sub-areas
SMM2 sub-areas can have different filters applied. The main area uses Night filter
(SD1); Sub-area 1 uses Sunset filter (SD2). Mario moves between them via pipes,
creating the alternating MULT component structure.

```
MAIN AREA — Night filter (SD1): VI5s
  ? blocks distributed with VI timing (preset sequence).
  Every ~5 s of play, one block delivers a coin.
  Pipe at end connects to Sub-area 1.

SUB-AREA 1 — Sunset filter (SD2): EXT
  ? blocks present but all pre-emptied (used blocks).
  No coins regardless of hitting.
  Pipe at end returns to Main Area.

Pattern: SD1 (VI5s, 20 s) → SD2 (EXT, 20 s) → SD1 → SD2 → ...
Each sub-area segment = 20 s of playtime (approximately 15 tiles at walk speed).

CONTRAST PHASE (Research level only):
  Sub-area 2 — Sunset filter (SD2): VI5s (enrich the EXT component).
  Use to demonstrate positive contrast: responding in SD1 should increase
  when SD2 is changed from EXT to VI5s? No — negative contrast:
  if SD2 improves, SD1 responding decreases.
```

### Mechanics Used
- Night filter on main area: SD1 visual cue
- Sunset filter on sub-area: SD2 visual cue
- VI timing via preset ? block sequence (same as stimulus_control and generalization levels)
- Pre-emptied blocks in SD2: EXT component
- Pipes connecting areas: simulate component alternation
- One-way arrows: prevent backtracking within a component

### Instructor Script Notes
1. SD1 (Night): "Look — it's night time. This is when coins are available."
   Hit several blocks. "Sometimes I get coins, sometimes I don't — it's a VI
   schedule. The night sky signals 'keep responding.'"
2. SD2 (Sunset): Enter pipe. "Now it's sunset. Different stimulus." Hit blocks.
   "Nothing. This is extinction. The sunset signals 'don't bother.'"
3. "Notice how I respond quickly in night and slow down in sunset?
   The stimulus controls my behavior."
4. Contrast demo: "If I now make sunset also pay off, watch what happens to
   my night responding." Switch to enriched version. "My night rate drops!
   That's behavioral contrast — the comparison to the other component matters."
5. Debrief: "Multiple schedule = alternating components, each with its own SD.
   The organism learns to discriminate. Contrast shows that behavior in one
   component is influenced by what happens in the other."

---

## Practice / Research Level Design

### Design: ABA Reversal (contrast manipulation)
```
Phase A1 — Baseline: MULT VI5s EXT (15 trials per component = 30 component exposures)
  SD1 (Night): VI5s active
  SD2 (Sunset): EXT

Phase B  — Contrast: MULT VI5s VI5s (15 trials per component)
  SD1 (Night): VI5s active
  SD2 (Sunset): VI5s active (enrich the formerly lean component)
  Expected: responding in SD1 DECREASES (negative contrast)

Phase A2 — Return: MULT VI5s EXT (15 trials per component)
  Expected: responding in SD1 RETURNS to baseline or exceeds it
```

### Contingency Parameters — MULT VI5s EXT
| Parameter | SD1 (Night, VI5s) | SD2 (Sunset, EXT) |
|---|---|---|
| Background filter | Night | Sunset |
| Schedule | VI5s | Extinction |
| Mean interval (s) | 5 | n/a |
| VI sequence (s) | 2,7,4,8,5,6,3,9,4,6 | n/a |
| Blocks per segment | 10 | 10 (all used) |
| Segment duration (approx) | 20 s | 20 s |

### Procedural Notes
- Participant instructions: "Walk through the level and hit blocks to collect coins."
- Do NOT describe the schedule conditions or the visual stimuli as signals.
- Observer codes SD1 or SD2 each time Mario enters a new component (segment).
- Observer codes RESP_1 / RESP_2 for each block hit in the respective component.
- Observer codes SR_1 for each coin in SD1; OMIT_2 for each hit in SD2 (no coin).
- Observer codes PAUSE at start of SD2 segment if Mario pauses ≥2 s before hitting.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| SD1 component schedule | VI5s (held constant) |
| SD2 component schedule | EXT (baseline), VI5s (contrast phase) |
| Phase | A1 baseline, B contrast, A2 return |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| SD1 | Mario enters Night (SD1) segment | On background change |
| SD2 | Mario enters Sunset (SD2) segment | On background change |
| RESP_1 | Block hit during SD1 segment | Each hit |
| RESP_2 | Block hit during SD2 segment | Each hit |
| SR_1 | Coin delivered in SD1 | On coin contact |
| OMIT_2 | Hit in SD2 with no coin (EXT) | Each hit |
| PAUSE | ≥2 s pause at segment onset | Pause onset |

---

## Analysis Notes
- **Response rate by component**: Responses/minute in SD1 and SD2 by phase.
  Expected: SD2 rate drops rapidly (extinction); SD1 rate stable then elevated
  (positive contrast vs. SD2 EXT).
- **Behavioral contrast index**: (SD1 rate in A1) vs. (SD1 rate in B, enriched SD2).
  Negative contrast: SD1 rate decreases when SD2 is enriched.
  Positive contrast: SD1 rate increases when SD2 is impoverished (A2 vs. B).
- **Discrimination index**: (RESP_1 rate − RESP_2 rate) / (RESP_1 rate + RESP_2 rate).
  Values near 1 = strong discrimination; near 0 = no discrimination.
- **SD2 rate decay**: Within SD2 EXT segments, plot responses over exposure.
  Expected: rapid extinction of SD2 responding across segments.

## Observer Notes
- SD1/SD2 transitions are coded when Mario exits one pipe and enters the next area.
- OMIT_2 is coded for every block hit in an EXT segment regardless of Mario's state.
- PAUSE is important for contrast analysis; ensures pausing isn't confounded with
  response rate changes.
- IOA: SD1/SD2 codes should achieve 100% (unambiguous visual cue).

## Replication Notes
- Course ID (MULT VI5s EXT — baseline): XXXX-XXXX-XXXX-XXXX
- Course ID (MULT VI5s VI5s — contrast): XXXX-XXXX-XXXX-XXXX
- VI sequence must be identical across all SD1 segments (no random re-drawing).
- Sunset and Night filters must be set before any blocks are placed in SMM2.
- Verify sub-area pipe connections before uploading.

## Key References
- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of Reinforcement*.
  Appleton-Century-Crofts. (pp. 556–632, multiple schedules)
- Reynolds, G. S. (1961). Behavioral contrast. *Journal of the Experimental
  Analysis of Behavior, 4*, 57–71.
- Bloomfield, T. M. (1967). Some temporal properties of behavioral contrast.
  *Journal of the Experimental Analysis of Behavior, 10*, 159–164.
- McSweeney, F. K., & Melville, C. L. (1993). Behavioral contrast for key pecking
  as a function of component duration. *Animal Learning & Behavior, 21*, 285–293.
