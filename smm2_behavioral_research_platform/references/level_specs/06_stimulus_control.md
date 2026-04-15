# Level Spec: Stimulus Control / Discrimination

---

## Phenomenon
Stimulus control: a response occurs more frequently in the presence of one
stimulus (SD, discriminative stimulus) than in the presence of another
(S-delta).  Discrimination training establishes differential responding through
differential reinforcement.

## Learning Objective
Participants observe that responding is reinforced in the presence of the SD
and extinguished (or punished) in the presence of the S-delta, and that over
trials responding comes under the control of the antecedent stimulus.

## Behavioral Target
- **Response**: Hitting a ? block from below
- **SD**: Blue background / night sky (coins in blocks)
- **S-delta**: Orange background / sunset sky (blocks are empty)
- **Consequence in SD**: Coin delivered (SR+)
- **Consequence in S-delta**: No coin (extinction)

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground (Night = SD; Sunset = S-delta) | Same |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Long (~200 tiles, alternating zones) | Same |

---

## Demo Level Design
**Purpose**: Instructor plays while narrating. Students track hit rate during
SD vs. S-delta segments.

### Layout
```
Zone 1  SD (night sky, blue background)
  5 active ? blocks, evenly spaced. Each yields 1 coin.

Zone 2  S-delta (sunset sky, orange — via sub-area with filter)
  5 used (empty) blocks in identical positions. No coin.

Zone 3  SD
  5 active ? blocks.

Zone 4  S-delta
  5 empty blocks.

Zone 5  SD
  5 active ? blocks.

Zone 6  S-delta
  5 empty blocks.

[Zones alternate; 6 zones total = 3 SD + 3 S-delta]
Sky/background changes at each zone transition (ground pipe → sub-area or
SMM2 background filter change).
```

### Mechanics Used
- Night filter (SD): distinguishes reinforcement available zones
- No filter / sunset (S-delta): extinction zones
- Identical block layout across conditions: controls for spatial confounds
- Sub-area transitions or background filters mark zone boundaries

### Instructor Script Notes
1. First SD zone: "Blue sky — watch what happens when I hit the blocks."
   Hit each block, collect coin.
2. First S-delta zone: "The sky changed. Let's see..." Hit blocks — no coins.
   "No reinforcement here."
3. After 2 full cycles: pause. "By now, have you noticed you could predict
   which zone would pay off? The background is the discriminative stimulus."
4. Debrief: "Behavior came under stimulus control — the SD signals reinforcement
   is available; the S-delta signals it isn't."

---

## Practice / Research Level Design
**Purpose**: Participant plays independently. Observer tracks discrimination
accuracy (responding in SD vs. S-delta) over trials.

### Layout
```
8 alternating zones (4 SD, 4 S-delta), randomized order per session
using one of 3 pre-set orders:

Order A: SD, Sdelta, SD, Sdelta, SD, Sdelta, SD, Sdelta
Order B: Sdelta, SD, Sdelta, SD, Sdelta, SD, Sdelta, SD
Order C: SD, SD, Sdelta, Sdelta, SD, Sdelta, SD, Sdelta

Each zone has 5 blocks.  Total: 40 blocks per session.
```

### Contingency Parameters
| Parameter | Value |
|---|---|
| SD | Night background (blue) |
| S-delta | Sunset background (orange) |
| SR+ | 1 coin per block in SD |
| S-delta consequence | Extinction (no coin) |
| Blocks per zone | 5 |
| Zones per session | 8 (4 SD, 4 S-delta) |
| Zone order | Counterbalanced across 3 orders |

### Procedural Notes
- Participant instructions: "Play through and collect coins."
- Do NOT identify the SD or S-delta explicitly.
- Observer codes every block hit, categorizing it as SD or S-delta zone.
- Primary DV: discrimination index = (hits in SD / total hits in SD zones) −
  (hits in S-delta / total hits in S-delta zones).  Perfect discrimination = 1.0.
- Run 3 sessions to track acquisition of stimulus control.
- Between-session comparison: does S-delta responding decrease over sessions?

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Stimulus type | SD (night), S-delta (sunset) |
| Session | 1, 2, 3 |
| Zone order | A, B, or C (counterbalanced) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| SD_PLUS | SD zone presented (zone onset) | At zone entry |
| SD_MINUS | S-delta zone presented (zone onset) | At zone entry |
| RESP_SD_PLUS | Block hit in SD zone | Each hit |
| RESP_SD_MINUS | Block hit in S-delta zone (error) | Each hit |
| SR_PLUS | Coin received | Each coin dispensed |
| CORRECT | Participant passes through S-delta zone without hitting any block | At zone exit |

---

## Observer Notes
- Log SD_PLUS or SD_MINUS at zone entry (when background changes), then log
  individual hits as RESP_SD_PLUS or RESP_SD_MINUS.
- CORRECT is only logged if the participant passes the entire S-delta zone
  without a single block hit.
- Discrimination index should approach 1.0 by session 3 for most participants.
  Lower values may indicate failure of the background cue to function as SD.
- IOA: Two observers categorize each hit as SD or S-delta; agree within zone
  (not time-based).

## Replication Notes
- Course ID (Order A): XXXX-XXXX-XXXX-XXXX
- Course ID (Order B): XXXX-XXXX-XXXX-XXXX
- Course ID (Order C): XXXX-XXXX-XXXX-XXXX
- Confirm that background filter change is perceptually salient before data
  collection (test with 3 naive observers).
- Do not use SMW or NSMBU style for this level — background filter options
  differ across styles; SMB1 provides most consistent night/sunset contrast.
