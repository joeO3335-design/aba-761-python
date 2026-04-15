# Level Spec: Behavioral Momentum

---

## Phenomenon
Behavioral momentum (Nevin, 1974; Nevin & Grace, 2000): behavior reinforced
in a rich context acquires greater resistance to change — analogous to physical
momentum.  Two properties define the metaphor:

- **Mass** = baseline reinforcement rate in the stimulus context (rich vs. lean)
- **Velocity** = current response rate
- **Momentum** = mass × velocity → predicts persistence under disruption

Key predictions:
1. Behavior in a rich-reinforcement context will persist longer under disruption
   than behavior in a lean-reinforcement context.
2. The ratio of post-disruption to pre-disruption response rate will be higher
   in the rich context.
3. Disruptors that work through the same mechanism as reinforcement (e.g., free
   reinforcers) are the most potent disruptors of behavioral momentum.

## Learning Objective
Participants observe that the history of reinforcement — not just current
contingencies — determines how resistant behavior is to disruption, and can
articulate the mass/velocity/momentum metaphor.

## Behavioral Target
- **Response**: Hitting ? blocks from below within a designated track
- **Rich context**: Track where CRF has been in effect (high reinforcement rate)
- **Lean context**: Track where FR10 has been in effect (low reinforcement rate)
- **Disruption**: Free reinforcers delivered at the start of the disruption zone
  (pre-feeding / satiation analog), followed by extinction of block-hitting
- **Consequence**: Coins (SR+) during baseline; nothing during disruption/extinction

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Long (~200 tiles) | Long (~200 tiles) |

---

## Demo Level Design
**Purpose**: Instructor establishes differential reinforcement history in two
tracks, then applies a disruptor, and students observe differential persistence.

### Layout
```
[ START ]
    │
    ├── RICH TRACK (upper path, bright sky theme)
    │     Baseline: 20 ? blocks, every 2 tiles = CRF (20 reinforcers)
    │     → Disruption zone: 5 free coins dispensed (free SR+)
    │       then 10 used blocks (extinction)
    │
    └── LEAN TRACK (lower path, underground theme sub-area)
          Baseline: 20 ? blocks, every 10 tiles = FR10 (2 reinforcers)
          → Disruption zone: 5 free coins dispensed (free SR+)
            then 10 used blocks (extinction)

Both tracks rejoin at a central corridor after the disruption zone.
One-way pipes prevent switching between tracks mid-session.
```

### Mechanics Used
- ? blocks at high density (CRF) vs. low density (FR10): operationalize mass
- Free-coin pipe sub-area: delivers 5 coins passively (satiation disruptor)
- Used blocks after free coins: extinction phase
- Different themes (ground vs. underground): visual cue for track identity
- One-way pipes: enforce track assignment per run

### Instructor Script Notes
1. Before play: "I'm going to walk through two different tracks. Pay attention
   to how often I get coins on each one."
2. Rich track baseline: hit every block, collect coin. "This track pays off every
   single time — very rich history."
3. Lean track baseline: hit every 10th block. "This track pays off much less often."
4. Disruption zone (both tracks): walk through free coins. "Now I'm getting coins
   for free — I don't have to do anything. Let's see what happens to my block-hitting."
5. Extinction in rich track: continue hitting used blocks. "I keep hitting — the
   history keeps me going even though nothing is paying off."
6. Extinction in lean track: stop sooner. "I stop faster here — less momentum."
7. Debrief: "The rich history created more behavioral mass. More mass = more
   momentum = more resistance to change."

---

## Practice / Research Level Design
**Purpose**: Participant establishes reinforcement history in both tracks across
baseline sessions, then experiences disruption. Observer codes persistence.

### Design: Multielement / Alternating treatments
```
Phase 1 — Baseline (sessions 1–3, alternated across sessions)
  Session A: Rich track only (CRF, 30 blocks)
  Session B: Lean track only (FR10, 30 blocks)
  Session C: Rich track only
  (Alternate to equate exposure time)

Phase 2 — Disruption (sessions 4–6, both tracks in same session)
  Participant plays rich track → disruption zone → extinction
  Then plays lean track → disruption zone → extinction
  (Order counterbalanced across participants)
```

### Contingency Parameters
| Parameter | Rich Track | Lean Track |
|---|---|---|
| Baseline schedule | CRF (FR1) | FR10 |
| Blocks per baseline session | 30 | 30 |
| Reinforcers per baseline session | 30 | 3 |
| Disruption type | Free SR+ (5 coins passive) | Free SR+ (5 coins passive) |
| Extinction blocks post-disruption | 15 | 15 |
| Sessions | 3 baseline + 3 disruption | Same |

### Procedural Notes
- Participant instructions: "Play through the level and collect as many coins as you can."
- Do NOT identify the two tracks or the disruption.
- Observer codes each block hit as RESP_RICH or RESP_LEAN based on active track.
- Observer codes FREE_SR when passive coins are dispensed (disruption onset).
- Observer codes PERSIST when participant hits a used block (continues after disruption).
- Observer codes SUPPRESS when participant stops and stands still for ≥3 s or
  exits the track without hitting remaining blocks.
- Primary DV: **resistance to change ratio** = (responses during extinction) /
  (responses during baseline), computed separately for rich and lean tracks.
- Expected result: resistance ratio rich > resistance ratio lean.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Reinforcement rate (mass) | Rich (CRF), Lean (FR10) |
| Phase | Baseline, Disruption/Extinction |
| Disruptor type | Free SR+ (satiation), Extinction only (control) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESP_RICH | Block hit in rich track | Each hit |
| RESP_LEAN | Block hit in lean track | Each hit |
| SR_PLUS | Coin delivered (baseline) | Each coin |
| FREE_SR | Passive coin delivered (disruption) | Each free coin |
| DISRUPTOR | Disruptor zone entered | Zone onset |
| PERSIST | Block hit in extinction zone | Each hit post-disruption |
| SUPPRESS | Participant stops responding in extinction zone | Onset of ≥3 s pause or exit |

---

## Analysis Notes
- **Resistance to change ratio**: `r = responses_extinction / responses_baseline`
  Computed for rich and lean separately. Expected: `r_rich > r_lean`.
- **Log resistance**: `log(r_rich / r_lean)` quantifies the momentum effect size.
- Compare across disruptor types if multiple disruption conditions used.
- Can model with Nevin's (1992) equation: `log(B_d / B_0) = -b·d·r^-a`
  where d = disruptor magnitude, a = sensitivity, b = disruptor efficacy, r = reinforcement rate.

## Observer Notes
- PERSIST and SUPPRESS are mutually exclusive per extinction zone visit.
  Code whichever occurs first; if participant resumes after suppression, code
  PERSIST again.
- Log disruptor onset (DISRUPTOR) as the moment the first free coin appears.
- IOA: Both observers should agree on RESP_RICH vs. RESP_LEAN coding (track
  assignment) and on PERSIST vs. SUPPRESS outcome per extinction zone.

## Replication Notes
- Course ID (rich baseline): XXXX-XXXX-XXXX-XXXX
- Course ID (lean baseline): XXXX-XXXX-XXXX-XXXX
- Course ID (disruption — rich track): XXXX-XXXX-XXXX-XXXX
- Course ID (disruption — lean track): XXXX-XXXX-XXXX-XXXX
- Free coin delivery must be passive (Mario walks through coin area without
  hitting blocks) — verify that coins are on ground, not in blocks.
- FR10 placement: 1 active block per 10-tile segment, remaining 9 as ground.
  Count tiles carefully before building.

## Key References
- Nevin, J. A. (1974). Response strength in multiple schedules. *Journal of the
  Experimental Analysis of Behavior, 21*, 389–408.
- Nevin, J. A., & Grace, R. C. (2000). Behavioral momentum and the law of effect.
  *Behavioral and Brain Sciences, 23*, 73–90.
- Mace, F. C., et al. (1988). Behavioral momentum in the treatment of noncompliance.
  *Journal of Applied Behavior Analysis, 21*, 123–141.
