# Level Spec: Mixed Schedules (MIX)

---

## Phenomenon
A Mixed schedule (MIX) is structurally identical to a Multiple schedule — two or
more component schedules alternate in time — except that **no discriminative stimulus
signals which component is currently in effect** (Ferster & Skinner, 1957).

The organism cannot predict which schedule is operating from environmental cues;
it must infer the current component from the pattern of reinforcement it has
recently experienced.

Key properties:
1. **Unsignaled alternation**: Components change on the same temporal schedule as
   MULT, but the stimulus remains identical across components.
2. **No behavioral contrast**: Without SDs, the contrast effects seen in MULT are
   absent or greatly attenuated.
3. **Response patterning**: Under MULT VI EXT, organisms quickly learn to respond
   only during the VI component (SD control). Under MIX VI EXT, responding may
   persist during EXT components because there is no signal to suppress it.
4. **MIX vs. MULT comparison** is the cleanest experimental design for demonstrating
   the *functional* role of discriminative stimuli in controlling responding.
5. **Within-session learning**: Some organisms may develop local rate adjustment
   within MIX sessions, using the pattern of recent reinforcers as a proxy SD.
   This is "adventitious" stimulus control.

Classic result (Ferster & Skinner; Reynolds, 1961): MULT shows sharp discrimination
and contrast; MIX shows undifferentiated responding across components.

## Learning Objective
Participants:
1. Experience responding under schedule alternation without cues about which is active.
2. Observe their own behavior under MIX — likely undifferentiated across components.
3. Compare MIX to MULT (same schedule parameters) to understand the role of the SD.

## Behavioral Target
- **Response**: Hitting ? blocks from below
- **MIX VI5s EXT**: Components alternate every ~20 s; both use identical ground theme
- **MIX VI5s VI5s**: Control condition; both identical schedule + identical stimuli
- **Direct comparison**: MIX VI5s EXT vs. MULT VI5s EXT (from spec 17)
- **Consequence**: Coins in VI component; nothing in EXT component
- **Antecedent**: Identical visual appearance regardless of which component is active

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground (daytime) | Ground (daytime) |
| Filter | None (identical throughout) | None (identical throughout) |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Long (~200 tiles); alternating hidden zones | Same |

---

## Demo Level Design

### Implementation: Hidden component alternation

Since MIX uses identical stimuli, the component change must be invisible to the
participant. Use consecutive segments that look identical but alternate between:
- Segment type A: ? blocks that yield coins (VI component)
- Segment type B: Pre-emptied used blocks (EXT component)

The key is that **both segment types look the same** from the player's perspective —
identical block placement, spacing, and ground texture. Only the internal block
state differs (live vs. used).

```
ZONE — MIX VI5s EXT (unsignaled alternation)
  Segment 1 (tiles 1–20):  VI5s active — ? blocks at x=2,4,6,8,10,12,14,16,18,20
                            Blocks yield coins per VI sequence.
  Segment 2 (tiles 21–40): EXT — Used blocks at x=22,24,26,28,30,32,34,36,38,40
                            All blocks look identical to Segment 1.
  Segment 3 (tiles 41–60): VI5s active (same as Segment 1)
  Segment 4 (tiles 61–80): EXT (same as Segment 2)
  ... continues

Visual result: Player sees an unbroken corridor of identical ? blocks.
Half deliver coins (VI); half are empty (EXT). No visual cue distinguishes them.
```

> **SMM2 implementation note**: In the editor, used blocks (empty blocks) and ?
> blocks appear visually different *in the editor*, but they appear similarly gray
> after a ? block has been hit. For the *research* level, use pre-emptied blocks
> for EXT segments so they appear slightly gray even at the start. This is an
> unavoidable minor difference; the critical thing is that no background filter
> or theme change signals the component boundary.

### Instructor Script Notes
1. "Watch carefully — I'll walk through and hit every block."
   Play through. "Notice I hit blocks in every segment, but coins only appeared
   sometimes. I didn't know which blocks would pay off."
2. "This is Mixed schedule — the schedule changes, but I get no signal.
   I have to keep hitting because I can't tell when it's EXT."
3. Compare directly: "Now watch the Multiple schedule version."
   Switch to MULT. "Night means VI; sunset means EXT. I stop hitting in sunset."
4. Debrief: "The SD is what makes the difference. Without it, I persist through
   extinction. That's why discriminative stimuli matter for behavioral efficiency."

---

## Practice / Research Level Design

### Design: Within-subject, MULT vs. MIX direct comparison
```
Condition A: MIX VI5s EXT  — 4 alternations (80 s active)
Condition B: MULT VI5s EXT — 4 alternations (80 s active)
Order counterbalanced (half: A→B; half: B→A)
10-minute break between conditions.
```
This within-subject comparison isolates the SD as the variable.

### Contingency Parameters — MIX VI5s EXT
| Parameter | VI Component | EXT Component |
|---|---|---|
| Visual stimulus | Ground day (no filter) | Ground day (no filter — identical) |
| Schedule | VI5s | Extinction |
| Mean interval (s) | 5 | n/a |
| VI sequence (s) | 2,7,4,8,5,6,3,9,4,6 | n/a |
| Blocks per segment | 10 | 10 (pre-emptied, look identical) |
| Segment duration (approx) | 20 s | 20 s |

### Procedural Notes
- Participant instructions: "Walk through the level and hit blocks to collect coins."
  (Identical instructions for both MIX and MULT conditions.)
- Observer codes RESP for each block hit; SR for each coin; NR for each 3-s pause;
  COMP_CHANGE when the component switches (observer knows from the level map;
  participant cannot see it).
- Post-session: participant is asked "Did you notice any pattern in when coins appeared?"
  Record verbatim response.

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| SD present | MULT (SD present), MIX (no SD) |
| VI component schedule | VI5s (held constant) |
| EXT component | Same block layout, pre-emptied |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| RESPONSE | Block hit (either component) | Each hit |
| SR | Coin delivered (VI component only) | On coin contact |
| PAUSE | ≥3 s no response | Pause onset |
| BURST | ≥3 hits within 2 s after an SR | On third hit |
| NR | Nil (no response) period logged by observer | Observer judgment |
| COMP_CHANGE | Component switches (observer-coded, not visible to participant) | On segment boundary |

---

## Analysis Notes
- **Key comparison**: Response rate during EXT component in MIX vs. MULT conditions.
  Prediction: EXT-component responding is higher in MIX than MULT (no SD to suppress).
- **Discrimination index**: Same formula as MULT spec.
  MIX prediction: near 0 (undifferentiated); MULT prediction: near 1.
- **Response persistence during EXT**: Mean responses per EXT segment in MIX;
  compare to mean responses per EXT segment in MULT (should be lower in MULT).
- **Within-session learning in MIX**: Does EXT-component responding decrease as
  participants experience more alternations? Regression of RESP_rate on EXT_segment_number.
- **Self-report**: Qualitative analysis of participants' verbal reports about
  noticing the pattern — correlate with behavioral discrimination index.

## Observer Notes
- COMP_CHANGE is coded by the observer from the session map (not visible to participant).
  Observer notes current component (VI or EXT) in the Note field with each RESP event.
- SR in MIX EXT components should not occur; any coin collected in an EXT segment
  is a recording error — verify block placement before session.
- IOA: RESPONSE and SR codes should achieve 100%; COMP_CHANGE requires inter-observer
  level-map agreement before session.

## Replication Notes
- Course ID (MIX VI5s EXT): XXXX-XXXX-XXXX-XXXX
- Course ID (MULT VI5s EXT — control; same as spec 17): XXXX-XXXX-XXXX-XXXX
- Block placement between MIX and MULT must be spatially identical (same tile positions).
  Only the background filter and pre-emptied vs. live block states differ.
- Pre-emptied blocks must be confirmed before session start (have an observer test-play).

## Key References
- Ferster, C. B., & Skinner, B. F. (1957). *Schedules of Reinforcement*.
  Appleton-Century-Crofts. (pp. 633–693, mixed schedules)
- Reynolds, G. S. (1961). An analysis of interactions in a multiple schedule.
  *Journal of the Experimental Analysis of Behavior, 4*, 107–117.
- Mackintosh, N. J. (1974). *The Psychology of Animal Learning*. Academic Press.
  (Chapter 7, discrimination learning and multiple schedules)
