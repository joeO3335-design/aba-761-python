# Level Spec: Generalization

---

## Phenomenon
Stimulus generalization: a response trained in the presence of one stimulus
occurs in the presence of other, physically similar stimuli — without explicit
training — along a generalization gradient.

## Learning Objective
Participants observe that a response trained under one set of antecedent
conditions transfers to novel stimuli that share features with the training
stimulus, and that transfer decreases as stimulus similarity decreases
(generalization gradient).

## Behavioral Target
- **Response**: Hitting a ? block from below
- **Training stimulus (SD)**: Night sky background + blue-tinted ground theme
- **Generalization stimuli (G1–G4)**: Same block layout but progressively
  different backgrounds (underground → water → castle → airship)
- **Consequence**: Coins present in all zones (no differential reinforcement —
  tests generalization without discrimination)

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground (training) + 4 others | Same |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Long (~250 tiles) | Same |

---

## Demo Level Design
**Purpose**: Instructor establishes the trained response, then tests
generalization across themes.

### Layout
```
Phase 1  — Training (Ground / Night sky, 10 trials)
  10 active ? blocks, CRF. Instructor hits each block, collecting coin.
  "This is our training environment."

Phase 2  — Generalization probes (non-reinforced OR same-CRF)
  Sub-area 1  Underground theme  (most similar to ground)
  Sub-area 2  Water theme
  Sub-area 3  Castle theme
  Sub-area 4  Airship theme     (least similar to ground)
  Each sub-area: 5 blocks in same positions as training.
  Same CRF schedule — all probe zones also reinforced to avoid confounding
  generalization with extinction.
```

Note: In the research version, probe zones are tested with a non-reinforced
probe design (extinction in probe, CRF in re-training).  In the demo, all zones
remain reinforced to keep the demonstration clean.

### Mechanics Used
- Sub-areas with different themes: operationalize stimulus similarity gradient
- Same block placement across all themes: controls for spatial novelty
- Pipes with theme transitions: mark zone boundaries

### Instructor Script Notes
1. Training: "Watch what I do in this environment." Hit all 10 blocks.
2. Sub-area 1 (underground): "Now we're in a different environment — same layout,
   though. Does the behavior transfer?" Hit blocks.
3. Sub-areas 2–4: continue, noting that responding occurs in all themes.
4. Debrief: "Generalization — the response trained here transferred to novel
   environments. Would it transfer equally to a completely unrelated game?"

---

## Practice / Research Level Design
**Purpose**: Tests generalization gradient using unreinforced probes sandwiched
between reinforced re-training trials.

### Design: Multiple-probe across themes
```
Training block  (5 CRF trials, ground/night)
Probe  — Underground (5 trials, NO coins — extinction probe)
Re-training  (5 CRF trials, ground/night)
Probe  — Water theme (5 trials, no coins)
Re-training  (5 CRF trials)
Probe  — Castle theme (5 trials, no coins)
Re-training  (5 CRF trials)
Probe  — Airship theme (5 trials, no coins)
```

### Contingency Parameters
| Parameter | Value |
|---|---|
| Training stimulus | Ground theme, night sky filter |
| Generalization stimuli | Underground, Water, Castle, Airship (SMB1 style) |
| Schedule in training blocks | CRF |
| Schedule in probe blocks | Extinction (no coins) |
| Trials per block | 5 |
| Trial = | 1 block hit opportunity |
| Blocks per block segment | 5 |
| Probe design | Multiple unreinforced probes with re-training between |

### Contingency Parameters — Similarity Ranking
| Stimulus | Similarity to Training | Rationale |
|---|---|---|
| Ground/Night (training) | 1.00 | Identical |
| Underground | 0.75 | Same side-scroller, dark, enclosed |
| Water | 0.50 | Different physics, different colors |
| Castle | 0.25 | Hazards present, dark, hostile theme |
| Airship | 0.10 | Moving background, very different feel |

### Procedural Notes
- Participant instructions: "Play through the level and hit blocks to collect
  coins." (No mention of the theme changes.)
- Participant is NOT told that probe blocks yield no coins.
- Observer codes response rate per block in each segment.
- Primary DV: proportion of blocks hit in each probe theme relative to training.
- Expected gradient: underground > water > castle > airship.
- Run 2 sessions to assess consistency of gradient.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Stimulus theme | Ground (training), Underground, Water, Castle, Airship |
| Block type | Training (CRF), Probe (extinction) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| TRAIN_STIM | Training segment entered | Zone onset |
| GEN_STIM | Probe segment entered | Zone onset; use Note for theme name |
| RESPONSE | Block hit | Each hit |
| SR_PLUS | Coin received (training segments only) | Each coin |
| NR | Block passed without hit | Each missed block |

---

## Observer Notes
- Use the Note field on GEN_STIM to record the current probe theme
  (e.g., "water").
- Primary measure: hits / available blocks in each probe zone.
- Generalization gradient is the plot of hit proportion across similarity levels.
- IOA: Count total hits per zone — two observers must agree within ±1 hit per zone.
- If participant never hits blocks in any probe theme, check that training was
  adequate (≥90% hit rate in training blocks) before interpreting.

## Replication Notes
- Course ID: XXXX-XXXX-XXXX-XXXX
- Verify SMB1 style is used — theme textures differ across SMM2 styles.
- Block positions must be pixel-identical across all segments; use copy-paste
  within SMM2 editor to ensure this.
- The similarity ranking (0.10–1.00) is theoretical; empirical ranking may
  differ.  Report observed gradient, not assumed similarity, in analyses.
