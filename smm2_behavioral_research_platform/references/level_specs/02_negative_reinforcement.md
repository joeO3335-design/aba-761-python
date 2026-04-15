# Level Spec: Negative Reinforcement

---

## Phenomenon
Negative reinforcement: a response increases in frequency when it terminates
(escape) or prevents (avoidance) an aversive stimulus.  Two sub-paradigms are
demonstrated in separate level sections.

## Learning Objective
Participants distinguish escape (aversive already present; behavior removes it)
from avoidance (aversive signaled but not yet delivered; behavior prevents it),
and observe that both produce response-rate increases via SR– contingencies.

## Behavioral Target
- **Escape response**: Jumping on a Goomba (removes the aversive stimulus)
- **Avoidance response**: Jumping to an elevated platform before a Goomba
  reaches Mario (prevents contact)
- **Consequence**: Aversive stimulus removed or prevented
- **Antecedent (escape)**: Goomba in contact range on ground level
- **Antecedent (avoidance)**: Warning signal (coin arrow or on-screen Goomba
  walking toward Mario at a distance)

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Medium (~80 tiles) | Medium (~80 tiles) |

---

## Demo Level Design
**Purpose**: Instructor plays while narrating. Students observe.

### Layout
```
Section A — Escape
  Ground corridor with Goombas placed every 8 tiles walking toward Mario.
  No elevated platforms. Only way to progress: stomp each Goomba.
  [ G ][ ][ ][ G ][ ][ ][ G ]  (G = Goomba patrol zone)

Section B — Avoidance
  Ground corridor with Goombas PLUS elevated platform escape route.
  Warning: coin arrow pointing up appears 6 tiles before each Goomba zone.
  Mario can jump to platform BEFORE Goomba arrives to avoid contact.
  [^][ ][ ][ G ]  <- ^ = coin arrow (warning signal), platform above
  [ ][ ][===][ ]  <- === = elevated platform above Goomba path

Section C — Control (no aversive)
  Open corridor, no Goombas, coins on ground. Baseline walk-through.
```

### Mechanics Used
- Goombas: aversive stimuli (contact = power-up loss for Super Mario,
  death for Small Mario — use Super Mario start for demo)
- Coin arrows: warning signals for avoidance section
- Elevated platforms: avoidance response topography
- Stomping: escape response topography

### Instructor Script Notes
1. Section A: "Mario can only move forward by stomping the Goomba. Stomping
   *removes* the aversive — that's escape."
2. Section B: "Now there's a warning signal — the coins pointing up. Mario can
   jump to the platform *before* the Goomba arrives. That's avoidance."
3. Section C: "No aversive, no elevated route needed. Notice response rate
   toward platforms drops to zero."
4. Key concept: "Both escape and avoidance strengthen behavior via SR– — the
   removal or prevention of something aversive."

---

## Practice / Research Level Design
**Purpose**: Participant plays independently. Observer codes with companion app.

### Layout
```
Zone 1  Escape trials (10 Goombas, no platform option, must stomp to progress)
Zone 2  Avoidance trials (10 Goombas + platform escape available)
        Warning signal appears 4 tiles before each Goomba zone
Zone 3  Mixed (5 escape-only + 5 avoidance-available, randomized order)
```

### Contingency Parameters
| Parameter | Value |
|---|---|
| Aversive stimulus | Goomba (contact = lose power-up) |
| Starting state | Super Mario (so contact = demotion, not death) |
| Escape response | Stomp Goomba |
| Avoidance response | Jump to elevated platform before Goomba contact |
| Warning signal onset | 4 tiles (≈ 2 seconds walk) before Goomba zone |
| Goomba patrol range | 3 tiles, reversing |
| Trials per zone | 10 |
| Inter-trial interval | 6 open tiles between each Goomba |

### Procedural Notes
- Participant instructions: "Play through the level. Avoid losing your power-up
  if you can."
- Do NOT use the words "escape" or "avoidance."
- Observer codes each Goomba encounter as one trial.
- If participant dies and restarts from checkpoint, note in session log and
  re-code from checkpoint on.
- Place a checkpoint flag at the Zone 1 / Zone 2 boundary.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Paradigm | Escape, Avoidance, Mixed |
| Warning signal | Present (avoidance zones), Absent (escape zones) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| ESCAPE | Mario stomps Goomba (escape response) | On stomp contact |
| AVOIDANCE | Mario jumps to platform before Goomba contact | When platform reached |
| AVERSIVE | Goomba contact results in power-up loss | On hit |
| SR_MINUS | Aversive removed or prevented (outcome confirmed) | After stomp or platform landing |
| NR | Mario contacts Goomba without escape/avoidance | On hit without response |

---

## Observer Notes
- An AVOIDANCE response requires platform reached *before* Goomba contact.
  If Goomba contacts Mario on the way up, code as AVERSIVE, not AVOIDANCE.
- Log SR_MINUS immediately after ESCAPE or AVOIDANCE is confirmed.
- Watch for partial avoidance (Mario begins to jump but still contacts Goomba).
  Code these as AVERSIVE with note "partial avoidance attempt."
- IOA: Observers should agree on Goomba contact events within ±0.5 seconds.

## Replication Notes
- Course ID: XXXX-XXXX-XXXX-XXXX
- Goomba patrol speed in SMB1 style is fixed — confirm no speed modifiers applied.
- Super Mario starting state is critical; Small Mario starting state conflates
  punishment (death) with negative reinforcement.
