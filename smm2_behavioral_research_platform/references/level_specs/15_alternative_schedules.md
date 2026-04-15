# Level Spec: Alternative Schedules (ALT)

---

## Phenomenon
An Alternative schedule (ALT) arranges two component schedules simultaneously;
reinforcement is delivered when **either** component is satisfied first (Ferster &
Skinner, 1957; Findley, 1958). The organism need not satisfy both — the first
component met triggers the reinforcer, and both component clocks reset.

Formally, **ALT FR n FI t** means:
- A ratio counter increments with each response.
- An interval clock runs from trial onset.
- Whichever finishes first — n responses OR t seconds — delivers the coin and resets both.

Key predictions:
1. Under **ALT FR FI**, the FI component will rarely (or never) be the one that
   triggers reinforcement if the ratio requirement is small enough to be completed
   before the interval elapses — the organism effectively stays on the FR sub-schedule.
2. When the FR is large or the FI is short, the FI becomes the operative schedule.
3. Increasing the FI while holding FR constant shifts behavior toward more responses
   (FR dominates). Decreasing the FI shifts toward fewer responses (FI dominates).
4. This asymmetry teaches the concept of **schedule interaction** — the two
   components are not independent; the easier one always "wins."

ALT contrasts with CONJ (where BOTH must be satisfied) and with CONC (where the
organism actively chooses between two operanda).

## Learning Objective
Participants:
1. Experience that when two requirements race against each other, behavior is shaped
   by whichever requirement is least demanding.
2. Observe how the "winning" schedule changes as parameters are adjusted.
3. Distinguish ALT (OR-logic) from CONJ (AND-logic).

## Behavioral Target
- **Response**: Hitting ? blocks from below (each hit = 1 response, increments FR counter)
- **Interval component**: Time since last reinforcement (clock runs during play)
- **ALT FR5 FI10s**: Reinforcement when Mario hits 5 blocks OR 10 seconds elapses
- **ALT FR3 FI20s**: FR3 almost always wins (short ratio vs. long interval)
- **ALT FR20 FI5s**: FI5s almost always wins (long ratio vs. short interval)
- **Consequence**: Coin on whichever component is satisfied first
- **Antecedent**: Row of ? blocks; timer visible via on-screen clock mechanism

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground | Ground |
| Time Limit | None (manual timing by observer) | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | ~90 tiles (3 zones) | ~90 tiles (3 zones) |

---

## Demo Level Design

### Approximating ALT in SMM2

SMM2 does not have a built-in interval timer that delivers reinforcement automatically.
The ALT interval component is **approximated** by having the instructor or observer
deliver a coin manually (via a pipe that releases coins) every t seconds, OR by
placing a coin on the ground at a fixed distance that Mario reaches passively after t
seconds of walking.

**Practical implementation**:
- The FR component = ? blocks in a row (each hit counts as 1 response)
- The FI component = a coin at the end of a fixed-length corridor that Mario
  reaches after approximately t seconds of walking at normal speed
  (Normal walk speed ≈ 1 tile/0.75 s → 10 tiles ≈ 7.5 s ≈ FI 8s)
- Whichever Mario contacts first (FR block stack OR ground coin) = reinforcement.
- After either is triggered, the entire zone resets via a loop pipe.

### Layout
```
ZONE A — ALT FR5 FI10s
  Start at left. ? blocks at positions 2,4,6,8,10 (FR5 if hit rapidly).
  Ground coin at position 14 (≈10 s at walk speed from start).
  If Mario hits 5 blocks before reaching tile 14: FR wins (coin from block 5).
  If Mario reaches tile 14 before hitting 5 blocks: FI wins (ground coin).
  Loop pipe at tile 16 returns to zone start.

ZONE B — ALT FR3 FI20s
  3 ? blocks close together (x=2,4,6). Ground coin far away (x=28 ≈ 20 s).
  FR3 almost always wins; Mario collects coin from block 3, never reaches ground coin.
  Observation: "The ratio is so easy, the interval never matters."

ZONE C — ALT FR20 FI5s
  20 ? blocks spread out (x=2 to x=40). Ground coin at x=7 (≈5 s).
  Mario reaches the ground coin long before hitting 20 blocks.
  Observation: "The interval is so short, my hitting doesn't matter."
```

### Instructor Script Notes
1. Zone A: "I need to hit 5 blocks OR wait 10 seconds. Let's see which happens first."
   Hit 5 blocks quickly. "FR won. The ratio was easier."
2. Zone B: "Now only 3 blocks, but the interval is 20 seconds."
   Hit 3 blocks immediately. "FR wins every time — I don't even have to think about
   the interval."
3. Zone C: "Now 20 blocks, but the interval is only 5 seconds."
   Walk without hitting. Coin appears. "FI won — 5 seconds passed before I could
   hit 20 blocks."
4. Debrief: "ALT means whichever comes first. The easier requirement dominates.
   Understanding this explains why compound schedules don't always have the effects
   you'd predict from either component alone."

---

## Practice / Research Level Design

### Design: Within-subject, three ALT conditions, counterbalanced
```
Condition A: ALT FR5 FI10s  — 20 trials
Condition B: ALT FR3 FI20s  — 20 trials
Condition C: ALT FR20 FI5s  — 20 trials
Order counterbalanced (6 orders, Latin square).
10-minute break between conditions.
```

### Contingency Parameters
| Condition | FR Req | FI Req | Expected winner | Path length |
|---|---|---|---|---|
| ALT FR5 FI10s | 5 hits | 10 s | Variable (near tie) | 16 tiles |
| ALT FR3 FI20s | 3 hits | 20 s | FR3 (ratio very easy) | 30 tiles |
| ALT FR20 FI5s | 20 hits | 5 s | FI5s (interval very short) | 30 tiles |

### Procedural Notes
- Participant instructions: "Walk through the level and collect coins any way you can.
  Hit the blocks or just walk forward — your choice."
- Observer codes: RESP_FR for each block hit; FI_MET when interval elapses (observer
  calls this using stopwatch); FR_MET when nth hit completes ratio; SR when coin
  collected; FIRST_FR or FIRST_FI to indicate which component triggered that trial's SR.
- Observer must use a stopwatch from the start of each trial to code FI_MET reliably.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| FR requirement | 3, 5, 20 |
| FI requirement (s) | 5, 10, 20 |
| FR-FI balance | FR easy/FI hard; Near tie; FR hard/FI easy |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESP_FR | Block hit (increments FR counter) | Each hit |
| FI_MET | Interval requirement elapsed | When t seconds pass (stopwatch) |
| FR_MET | FR requirement completed | After nth hit |
| SR | Coin collected (whichever component triggered) | On coin contact |
| FIRST_FR | FR was the operative component (won the race) | After each SR |
| FIRST_FI | FI was the operative component (won the race) | After each SR |
| NR | No block hit during interval (passive walk) | Observer judgment |

---

## Analysis Notes
- **Dominant schedule**: Proportion of trials where FR vs. FI was first; plot by condition.
  Expected: FIRST_FR >> FIRST_FI in ALT FR3 FI20s; reversed in ALT FR20 FI5s.
- **Response rate**: Average hits per trial by condition. Expected: FR3 condition
  produces highest rate (participant hits to trigger FR); FR20 condition lowest.
- **Latency to reinforcement**: Time from trial onset to SR. Expected: FI5s condition
  fastest (participant waits; floor at 5 s); FR3 condition may be faster if Mario
  can hit 3 blocks in <5 s.
- **ALT as parameter**: Vary FR and FI values across participants; map the boundary
  at which FI begins to dominate.

## Observer Notes
- **FIRST_FR / FIRST_FI** is a trial-level code logged once per SR event.
  If the coin came from a ? block hit, log FIRST_FR; if from the ground coin
  (interval path), log FIRST_FI.
- Observer must call FI_MET at the correct second using a stopwatch.
  IOA for FI_MET uses a 2-second window (±2 s agreement).
- FR_MET is unambiguous (nth block hit) and should achieve 100% IOA.

## Replication Notes
- Course ID (ALT FR5 FI10s): XXXX-XXXX-XXXX-XXXX
- Course ID (ALT FR3 FI20s): XXXX-XXXX-XXXX-XXXX
- Course ID (ALT FR20 FI5s): XXXX-XXXX-XXXX-XXXX
- Walk-speed calibration: verify at each session that normal walk speed is
  ~0.75 s/tile. Time Mario walking 10 tiles without hitting anything.
  If timing drifts, adjust tile distances before data collection.

## Key References
- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of Reinforcement*.
  Appleton-Century-Crofts. (pp. 724–737, alternative schedules)
- Findley, J. D. (1958). Preference and switching under concurrent scheduling.
  *Journal of the Experimental Analysis of Behavior, 1*, 123–144.
- Rachlin, H., & Baum, W. M. (1972). Effects of alternative reinforcement.
  *Journal of the Experimental Analysis of Behavior, 18*, 231–241.
