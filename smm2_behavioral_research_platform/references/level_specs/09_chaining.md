# Level Spec: Behavioral Chaining

---

## Phenomenon
Behavioral chaining: a complex sequence of behaviors is established in which
each response produces the discriminative stimulus for the next response, and
the terminal response produces the terminal reinforcer.  Both forward and
backward chaining structures are demonstrated.

## Learning Objective
Participants observe that a multi-step sequence can be acquired as a functional
unit, that each link serves simultaneously as the SR+ for the previous link
and the SD for the next, and that breaking any link disrupts the entire chain.

## Behavioral Target
- **Terminal behavior (chain complete)**: Reaching and activating the goal flag
  after completing a 4-step obstacle sequence
- **Chain structure**:
  - Link 1: Hit P-switch (activates coin trail on ground)
  - Link 2: Follow coin trail to activate door switch (opens barrier)
  - Link 3: Pass through now-open barrier to reach second P-switch
  - Link 4: Hit second P-switch to lower bridge, cross bridge to flagpole
- **Terminal SR+**: Level complete fanfare + star count
- **Each link's SR+/SD**: Visual and audio feedback of each sub-goal completion

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Castle | Castle |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Medium (~120 tiles) | Medium (~120 tiles) |

---

## Demo Level Design
**Purpose**: Instructor demonstrates the full chain, then demonstrates chain
disruption to show the interconnected structure.

### Layout
```
Start
  [P-Switch]  — Link 1
  When hit: blue coin trail appears on ground ahead

Link 1 → Link 2
  [Blue coins on ground leading to ON/OFF door switch]

  [ON/OFF Switch]  — Link 2
  When hit: barrier wall removed

Link 2 → Link 3
  [Pass through now-open barrier]
  [Second P-Switch visible ahead]

  [P-Switch 2]  — Link 3
  When hit: bridge of note blocks lowers over a pit

Link 3 → Link 4
  [Cross the note-block bridge]
  [Flagpole at end]

  [Flagpole]  — Terminal SR+
```

### Mechanics Used
- P-switch: activates time-limited environmental change (Link 1 and Link 3)
- ON/OFF switch: toggles barrier (Link 2)
- Note block bridge: passable surface created by switch (Link 4 path)
- Castle theme: aesthetically appropriate for sequential puzzle structure
- Flagpole: terminal reinforcer delivery

### Instructor Script Notes
1. Walk through the chain smoothly first: "Watch the whole sequence."
2. Second run: narrate each link: "Link 1 — I hit the P-switch. That coin trail
   is now the SD for Link 2 — it tells me where to go."
3. "Link 2 — I hit the ON/OFF switch. The door opening is the SR+ for Link 2
   and the SD for Link 3."
4. Third run: demonstrate chain disruption — stop after Link 1 and let P-switch
   timer expire. "Link 1 completed, but I didn't move to Link 2 in time. The
   chain broke."
5. Debrief: "The chain is only as strong as its weakest link."

---

## Practice / Research Level Design
**Purpose**: Participant acquires the chain; observer tracks link-by-link
completion rates across trials.

### Design: Forward chaining with task analysis
```
Trial 1–3:   Only Link 1 available, reinforced when P-switch hit
Trial 4–6:   Links 1–2 available (one-way door opens after Link 1)
Trial 7–9:   Links 1–3 available
Trial 10+:   Full 4-link chain available
(Graduated introduction matches forward chaining procedure)
```

### Contingency Parameters
| Parameter | Value |
|---|---|
| Chain length | 4 links |
| Chaining method | Forward chaining |
| P-switch active duration | 10 seconds (SMB1 default) |
| ON/OFF switch toggle | Permanent until next trial |
| Link 1 SR+ | Blue coins appear on ground |
| Link 2 SR+ | Barrier wall disappears |
| Link 3 SR+ | Bridge appears over pit |
| Terminal SR+ | Flagpole (level complete) |
| Trials 1–3 | Link 1 only reinforced |
| Trials 4–6 | Links 1–2 |
| Trials 7–9 | Links 1–3 |
| Trials 10+ | Full chain |

### Procedural Notes
- Participant instructions: "Find the way to the end of the level."
- Do NOT describe the links or the chain structure.
- Each "trial" = one run of the level from start (reset via death or restart).
- Observer codes each link attempted and outcome (complete vs. break).
- Chain break = any interruption between links that prevents forward progress
  (P-switch timer expiring, barrier not opened, falling in pit).
- Session ends after 15 trials or 15 minutes.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Links available | 1, 1–2, 1–3, 1–4 (full chain) |
| Trial block | 1–3, 4–6, 7–9, 10+ |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| LINK_1 | P-switch 1 hit | On switch contact |
| LINK_2 | ON/OFF switch hit | On switch contact |
| LINK_3 | P-switch 2 hit | On switch contact |
| LINK_4 | Bridge crossed, flagpole reached | On flagpole contact |
| CHAIN_COMPLETE | All 4 links completed in sequence | On flagpole |
| CHAIN_BREAK | Any link missed or timer expired | On break event |

---

## Observer Notes
- A CHAIN_BREAK should always include the Note "link X" (e.g., "link 2 break")
  indicating at which link the chain broke.
- LINK events are logged in real time as each sub-goal is reached.
- CHAIN_COMPLETE is logged in addition to LINK_4 when the full sequence succeeds.
- Latency between links (time from LINK_N to LINK_N+1) is captured by elapsed_s
  differences in the CSV — no separate coding needed.
- IOA: Two observers agree on which link broke in chain-break trials;
  agree on total links completed per trial.

## Replication Notes
- Course ID: XXXX-XXXX-XXXX-XXXX
- Graduated introduction (forward chaining across trial blocks) requires either
  (a) separate course IDs for each trial block, or (b) level segments separated
  by locked doors that the instructor opens remotely.
  Option (b) is preferred — use one course ID, instructor controls door opening.
- P-switch duration is fixed at 10 s in SMB1 style — verify before building.
- The note-block bridge must span the full pit width — test with Small Mario.
