# Level Spec: Extinction

---

## Phenomenon
Extinction: withholding the reinforcer that previously maintained a response.
Produces a characteristic pattern including initial extinction burst, emotional
responding, and eventual response decrease.  Spontaneous recovery can be
observed across sessions.

## Learning Objective
Participants observe that a previously reinforced response declines when the
SR+ is withheld, but not immediately — the extinction burst and emotional
responses occur first.  Across sessions they observe spontaneous recovery.

## Behavioral Target
- **Response**: Hitting ? blocks from below
- **Consequence (baseline)**: Coin delivered (CRF)
- **Consequence (extinction)**: No coin (used-block sound, no coin animation)
- **Antecedent**: ? block texture (appears identical in both conditions)

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Short (~60 tiles) | Short (~60 tiles) |

---

## Demo Level Design
**Purpose**: Instructor plays while narrating. Students observe and track
response rate (tallying hits) across 30-second windows.

### Layout
```
Phase 1  — Baseline (CRF)
  10 active ? blocks, spaced 4 tiles apart, each yields 1 coin.
  Play until participant hits all 10 blocks (establishes history).

Phase 2  — Extinction
  Same 10 block positions, but all replaced with pre-used (empty) ? blocks
  that produce the "empty" sound and no coin.
  Visually identical to Phase 1 blocks to the naive observer.
  NOTE: In SMM2, use the "Used Block" which looks like a ? block but gives nothing.
        This is the closest available mechanic to an extinction procedure.
```

### Mechanics Used
- Active ? blocks: baseline reinforcement
- Used Blocks (placed as ? block appearance): extinction condition
- Sub-area transition (pipe) between phases so instructor controls timing

### Instructor Script Notes
1. Phase 1: "I'm going to hit each block. Notice I get a coin every time."
   Hit each block, collect coin, pause briefly to let students tally.
2. Transition to Phase 2 (exit pipe): "Now let's see what happens."
   Do NOT announce that coins have been removed.
3. Hit the first used block: let students observe the empty result.
4. Continue hitting: point out burst if it occurs ("Did the rate go up?"),
   point out emotional responding ("Mario can't do anything about it —
   imagine the frustration").
5. Debrief: "This is extinction. The behavior doesn't stop instantly."

---

## Practice / Research Level Design
**Purpose**: Participant plays independently across multiple sessions.
Spontaneous recovery is measured by session 2 and session 3 comparisons.

### Layout
```
Session 1  — Baseline (CRF)
  20 active ? blocks, 4-tile spacing, all yield 1 coin.
  Participant plays entire level.

Session 2  — Extinction (same day, ≥15 min break)
  Same level appearance, but all blocks replaced with Used Blocks.
  Participant plays entire level.

Session 3  — Spontaneous Recovery (24 hours later, same level as Session 1)
  Active ? blocks restored (CRF).
  Measure whether response rate returns immediately or gradually.

Session 4  — Re-extinction (same day as session 3, ≥15 min break)
  Extinction condition reinstated.
  Typically extinguishes faster than Session 2 (re-extinction effect).
```

### Contingency Parameters
| Parameter | Value |
|---|---|
| Baseline schedule | CRF |
| Reinforcer | Coin (1 per block) |
| Blocks | 20 per session |
| Block spacing | 4 tiles |
| Inter-session break (same day) | ≥15 minutes |
| Inter-session break (across days) | 24 hours |
| Sessions | 4 (baseline → extinction → recovery → re-extinction) |

### Procedural Notes
- Participant instructions (all sessions): "Play through the level and hit the
  blocks."
- Do NOT tell participant the contingency has changed between sessions.
- Observer notes timestamps of first response, last response, and any pauses
  >5 seconds in extinction sessions.
- If participant verbalizes ("the blocks are broken" or similar): note verbatim
  in the Note field; do not confirm or deny.
- Code emotional responding as: aggressive play style (fast repeated hits on
  same block), vocalizations, or stopping and staring.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| Reinforcement condition | CRF (active), Extinction (used blocks) |
| Session | 1 (baseline), 2 (extinction), 3 (recovery), 4 (re-extinction) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESPONSE | Block hit (any block, active or used) | Each hit |
| SR_PLUS | Coin delivered | Each coin (sessions 1, 3 only) |
| EXT_BURST | ≥3 hits within 2 s after first extinction contact | Onset of burst |
| EMOTIONAL | Aggressive repeated hitting, verbalization, stopping | Onset |
| SPONT_RECOVERY | First response in recovery session (session 3) | Immediately |
| NR | Participant walks past a block without hitting | Each pass |

---

## Observer Notes
- Extinction burst is operationally defined as ≥3 responses within 2 seconds
  immediately following the first non-reinforced response.
- Emotional responding is defined as ≥2 hits on the same used block with no
  forward progress, OR audible verbalization.
- Spontaneous recovery magnitude = number of responses in the first 60 s of
  session 3 vs. the last 60 s of session 2.
- IOA: Primary and secondary observers should agree within ±1 response per
  30-second window for rate data.

## Replication Notes
- Course ID (baseline level): XXXX-XXXX-XXXX-XXXX
- Course ID (extinction level): XXXX-XXXX-XXXX-XXXX
  (Two separate uploaded levels are required — they cannot be the same course ID)
- The only visual difference between the two levels is active vs. used blocks.
  Verify this with naive testers before data collection.
