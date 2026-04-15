# Builder's Guide: Mixed Schedules (MIX) — DEMO Level

**Curriculum position**: 18 of 20
**Phenomenon**: MIX VI5s EXT — same schedule alternation as MULT but NO discriminative stimuli
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime — NO filter, uniform appearance) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | ~200 tiles (4 alternating segments) |

---

## Critical Design Principle

MIX and MULT must be **visually identical** from the participant's perspective,
with only the SD presence/absence differing:
- **MULT** (spec 17): Night filter = SD1, Sunset filter = SD2 → visible signal
- **MIX** (this spec): No filter change → no signal at component boundaries

To achieve this, the MIX level uses a **single continuous ground corridor** with
NO visual change at segment boundaries. The component structure exists in the
block state only — some blocks yield coins (VI component), others are pre-emptied
(EXT component). The player cannot see which is which from the outside.

---

## Two Courses for Within-Subject Comparison

| Course | Condition | Visual SD | Schedule |
|---|---|---|---|
| Course 1 | MIX VI5s EXT | None (ground, no filter) | Alternating unsignaled |
| Course 2 | MULT VI5s EXT | Night / Sunset filters | Same alternation, signaled |

Run participants in counterbalanced order (half: MIX first; half: MULT first).

---

## Course 1: MIX VI5s EXT

### Layout (x=1–160, continuous ground corridor)
Ground: y=1, x=1–160. No filter. No theme change. Uniform ground daytime appearance.

**4 alternating segments** (VI, EXT, VI, EXT), each 20 tiles:

**Segment 1 (VI5s, x=1–20)**:
Active [?] blocks at y=4: x=4, 10, 16, 20 — yield coins per VI timing.

**Segment 2 (EXT, x=21–40)**:
Empty [!] blocks at y=4: x=24, 28, 32, 36, 40 — NO coins.
Visual: These appear slightly grayed (used-block appearance) even before being hit.
> Note: In SMM2, used/empty blocks look slightly different from unhit [?] blocks.
> This is an unavoidable minor cue. Minimize it by placing fewer pre-emptied blocks
> and mixing them with the active blocks spatially (so the pattern isn't obvious).
> For research purposes: note this limitation in observer guide.

**Segment 3 (VI5s, x=41–60)**:
Active [?] blocks at y=4: x=44, 50, 56, 60

**Segment 4 (EXT, x=61–80)**:
Empty [!] blocks at y=4: x=64, 68, 72, 76, 80

Repeat 2 more alternation pairs (Segments 5–8, x=81–160).

**Goal Pole**: x=162, y=1–9

---

## Course 2: MULT VI5s EXT (For Direct Comparison)

**Use the existing Course A1 from spec 17** (same VI and EXT structure but with
Night/Sunset filters on sub-areas). Reuse that course ID.

The direct comparison between Courses 1 (MIX) and 2 (MULT) uses the same participant
in counterbalanced sessions.

---

## What Observers Measure

- **MIX**: Observer codes RESPONSE for every block hit; SR for every coin; COMP_CHANGE
  when segment boundary is crossed (observer knows from the level map; participant doesn't).
- **Primary DV**: Response rate during EXT segments in MIX (should be HIGH — no SD to suppress)
  vs. EXT segments in MULT (should be LOW — sunset signal suppresses responding).

---

## Instructor Script Notes

1. **MIX Level**: Walk through, hit blocks at random.
   "Some blocks pay off, some don't — but I can't tell which ones before I hit them.
   There's no signal. I keep hitting in the empty sections too."
   Show persisting through EXT segments: "No coins here either... but I still try.
   I have no way to know if this section will suddenly pay off."

2. **MULT Level** (comparison):
   "Same schedule, but now I have a visual signal."
   Show fast discrimination: quickly stop hitting in Sunset; resuming in Night.
   "The signal tells me when to respond. Without it (MIX), I couldn't discriminate."

3. Debrief: "Discriminative stimuli do real work. Without them, behavior doesn't
   efficiently track changing contingencies. The SD is not just a label —
   it functionally controls responding by signaling when responding will pay off."

---

## Verification Checklist
- [ ] Course 1 (MIX): No filter applied to any segment; uniform ground appearance
- [ ] Course 1: Active [?] blocks in VI segments, pre-emptied [!] in EXT segments
- [ ] Block positions visually similar across VI and EXT segments (minimize gray cue)
- [ ] Segment boundaries are not marked by any visual, architectural, or auditory change
- [ ] Observer has level map showing which segments are VI vs. EXT
- [ ] Course 2 (MULT) is the same course as spec 17's Course A1 (reuse IDs)
- [ ] Counterbalancing order recorded in data collection log
- [ ] Both course IDs in INDEX.md with MIX/MULT labels
