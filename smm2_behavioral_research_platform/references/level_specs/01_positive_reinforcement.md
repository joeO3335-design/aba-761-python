# Level Spec: Positive Reinforcement

---

## Phenomenon
Positive reinforcement: a response increases in frequency when followed by the
delivery of a stimulus (SR+).

## Learning Objective
Participants observe or experience that a specific operant response (moving
forward, jumping into a block) reliably produces a pleasant consequence (coin,
power-up), and that response rate increases across the session.

## Behavioral Target
- **Response**: Hitting a ? block from below (1 per trial)
- **Consequence**: Coin or Super Mushroom dispensed from block
- **Antecedent**: ? block visible directly above walkable surface

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Short (~50 tiles) | Short (~50 tiles) |

---

## Demo Level Design
**Purpose**: Instructor plays while narrating. Students observe.

### Layout
```
Section A — CRF (Continuous Reinforcement)
  [?][?][?][?][?]   <- 5 blocks in a row, each gives 1 coin
  [ ][ ][ ][ ][ ]   <- walkable ground

Section B — Extinction probe (last 2 blocks empty/used-block texture)
  [!][!][?][?][?]   <- first 2 are empty blocks (no coin), last 3 active
  [ ][ ][ ][ ][ ]
```
Note: Use Used Block texture ([!]) for the extinction probe blocks so they are
visually distinct.

### Mechanics Used
- ? blocks: primary SR+ delivery mechanism
- Used Block: signal that reinforcement is unavailable (extinction condition probe)
- Coins dispensed directly (not through pipes or doors) for immediacy

### Instructor Script Notes
1. Before playing: "Notice what happens every time Mario hits a block."
2. Hit each active ? block, pause briefly after each coin: "The coin is the
   reinforcer — it follows the response immediately."
3. At the extinction probe blocks: "Now watch what happens when the behavior
   produces nothing. Does the rate change?"
4. Debrief: elicit the three-term contingency (antecedent → behavior → consequence).

---

## Practice / Research Level Design
**Purpose**: Participant plays independently. Observer codes with companion app.

### Layout
```
Zone 1  [CRF baseline — 10 active ? blocks, evenly spaced, every 5 tiles]
Zone 2  [FR3 — 1 coin per 3rd block hit; blocks clustered in sets of 3]
Zone 3  [VR3 — average 1 coin per 3 hits; unpredictable spacing]
Zone 4  [Extinction — all blocks are Used Blocks, no SR+ available]
```
Transition between zones is marked by a change in background color (use SMM2
sub-area night filter) so the instructor can track zone without cueing participant.

### Contingency Parameters
| Parameter | Value |
|---|---|
| Schedule Zone 1 | CRF (FR1) |
| Schedule Zone 2 | FR3 |
| Schedule Zone 3 | VR3 (mean = 3, range 1–5) |
| Schedule Zone 4 | Extinction |
| Reinforcer | Coin (1 per delivery) |
| Blocks per zone | 10 |
| Tile spacing between blocks | 5 |

### Procedural Notes
- Participant instructions: "Play through the level at your own pace. Try to
  collect as much as you can."
- Do NOT mention schedule names or reinforcement contingencies.
- Observer stands or sits where they can see the screen without blocking it.
- Code each ? block hit as RESPONSE; code each coin dispensed as SR_PLUS.
- Session ends when participant reaches the end flag or after 10 minutes,
  whichever comes first.
- Run 3 sessions (separate plays of the same level) to capture within-session
  and between-session trend data.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Schedule of reinforcement | CRF, FR3, VR3, Extinction |
| Zone order | Fixed (CRF → FR3 → VR3 → EXT) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESPONSE | Participant hits a ? block | On each block contact |
| SR_PLUS | Coin/mushroom dispensed | Immediately after coin appears |
| NR | Participant walks past an active block | When block is passed without hit |
| ERROR | Participant hits Used Block (zone 4) | Any hit in extinction zone |

---

## Observer Notes
- Distinguish RESPONSE (block hit) from walking under a block without hitting it.
- In VR3 zone, log SR_PLUS only on trials that actually produce a coin.
- Post-reinforcement pause is visible as Mario stopping momentarily — note in
  the Note field if observed.
- IOA: Second observer should agree on block hits within ±1 second of wall time.

## Replication Notes
- Course ID: XXXX-XXXX-XXXX-XXXX  (to be filled after upload)
- Built on SMM2 v3.0.2 or later (earlier versions lack Used Block color distinction)
- VR3 sequence used in research version: 1,3,5,2,4,3,1,5,2,3 (preset, not
  truly random, for replication)
