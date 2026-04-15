# Level Spec: Reinforcement Schedules

---

## Phenomenon
Schedules of reinforcement: the pattern or rule governing which instances of a
response produce a reinforcer.  Four basic schedules are demonstrated: FR, VR,
FI, and VI.  Each produces a characteristic pattern of responding (rate and
pause structure).

## Learning Objective
Participants observe and experience that the schedule governing reinforcement
delivery — not the reinforcer itself — determines response rate and pause
structure.  They can predict cumulative record shape from schedule type.

## Behavioral Target
- **FR/VR Response**: Hitting ? blocks from below
- **FI/VI Response**: Pressing a timed switch (P-switch) then collecting
  coins that appear for a fixed or variable interval window
- **Consequence**: Coin delivery
- **Antecedent**: Visible ? block (ratio) or illuminated P-switch (interval)

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Long (~200 tiles, 4 zones) | Long (~200 tiles, 4 zones) |

---

## Demo Level Design
**Purpose**: Instructor plays while narrating. Students observe and sketch
cumulative records in real time.

### Layout
```
Zone FR  — Fixed Ratio
  Groups of 3 ? blocks separated by empty space.
  Every 3rd hit (end of each group) yields 1 coin.
  Remaining 2 hits yield empty used-blocks.
  Pattern: [?][?][?] [gap] [?][?][?] [gap] …  (10 groups = 30 blocks)

Zone VR  — Variable Ratio
  Single ? blocks at irregular spacings (1, 3, 5, 2, 4, 3, 1, 5, 2, 3).
  Each block has 1/mean probability of producing a coin (pre-set sequence).
  Preset sequence (mean VR3): blocks 1,4,7,10 produce coins; rest empty.

Zone FI  — Fixed Interval
  P-switch at start of zone. Pressing it opens a coin door for exactly 5 seconds.
  After 5 s door closes. Another P-switch 12 tiles later opens next window.
  Coins are available inside the door only during the window.
  Responses before interval ends are possible but produce nothing extra.

Zone VI  — Variable Interval
  Same P-switch/door structure but interval lengths vary:
  3, 7, 4, 8, 5, 6, 3, 9, 4, 6 seconds (mean VI = 5.5 s).
  Sequence is preset and fixed across all research sessions.
```

### Mechanics Used
- ? blocks with used-block fills for ratio schedule control
- P-switches + coin doors for interval schedule simulation
- Sub-areas (night filter tint) to visually demarcate zones

### Instructor Script Notes
1. FR zone: "One reinforcer for every three responses. Notice the brief pause
   after each coin — that's the post-reinforcement pause. Then rapid responding."
2. VR zone: "Still averages one reinforcer per three responses, but unpredictable.
   Notice: almost no pausing. The next reinforcer could always be the very next hit."
3. FI zone: "A reinforcer is available after a fixed time has passed. Early
   responses produce nothing. Watch for the scallop — slow start, faster near
   the end of each interval."
4. VI zone: "Variable interval. Steady, moderate rate — no post-reinforcement
   pause, no scallop. The next interval could always be almost over."
5. Have students draw cumulative record curves as you play.

---

## Practice / Research Level Design
**Purpose**: Participant plays independently. Observer codes with companion app.

### Layout
Same 4-zone structure as demo.  Zones separated by 1-way doors so participant
cannot backtrack.

### Contingency Parameters
| Parameter | Value |
|---|---|
| FR value | FR3 |
| VR mean | VR3 (sequence: 1,3,5,2,4,3,1,5,2,3 from start) |
| FI value | FI5s |
| VI mean | VI5.5s (sequence: 3,7,4,8,5,6,3,9,4,6 s) |
| Reinforcer | 1 coin per delivery |
| Blocks per ratio zone | 30 (10 reinforcement opportunities) |
| P-switch cycles per interval zone | 10 |
| Zone order | Fixed: FR → VR → FI → VI |

### Procedural Notes
- Participant instructions: "Play through the level and collect as many coins
  as you can."
- Do NOT name the schedules.
- Observer logs every block hit (RESPONSE) and every coin received (SR_PLUS).
- For FI/VI zones: log RESPONSE at each P-switch press, SR_PLUS when coin door
  opens and coins are collected.
- POST_SR_PAUSE: log when participant visually stops moving for ≥1 second
  immediately after a coin is collected in FR zone.
- Session ends at the end flag or 15 minutes, whichever comes first.
- Run 2 sessions per participant (identical level, same day) to examine
  within-subject consistency.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Schedule type | FR3, VR3, FI5s, VI5.5s |
| Zone order | Fixed (FR → VR → FI → VI) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESPONSE | Block hit or P-switch press | Each occurrence |
| SR_PLUS | Coin delivered | Each coin dispensed |
| POST_SR_PAUSE | ≥1 s stop immediately after SR+ | Onset of pause |
| BURST | ≥3 responses in <2 s | Onset of burst |
| NR | P-switch available but not pressed (interval zone) | If >10 s elapses without press |

---

## Observer Notes
- POST_SR_PAUSE is most visible in FR zone; rare in VR.
- In FI zone, look for scallop: slow initial responding accelerating near
  interval end.  Code accelerating run as BURST.
- IOA: Two observers should agree on RESPONSE events within ±0.5 s.
- For POST_SR_PAUSE, IOA criterion: both observers agree pause occurred and
  agree on onset within ±1 s.

## Replication Notes
- Course ID: XXXX-XXXX-XXXX-XXXX
- VR and VI sequences are preset (not random) to ensure cross-site replication.
  Do not alter block/switch placement without updating parameters.json.
- P-switch coin-door timing in SMB1 style: confirm door stays open for the
  specified number of seconds before building — test with stopwatch.
