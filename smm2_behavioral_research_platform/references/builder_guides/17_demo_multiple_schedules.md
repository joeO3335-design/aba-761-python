# Builder's Guide: Multiple Schedules (MULT) — DEMO Level

**Curriculum position**: 17 of 20
**Phenomenon**: MULT VI5s EXT — Night SD (VI active) vs. Sunset SΔ (EXT) with behavioral contrast
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (filter varies: Night / Sunset) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | Sub-area structure, ~200 tiles total |

---

## Relationship to Stimulus Control Level (07)

This level uses the **same visual SD structure** as the Stimulus Control level
(Night = SD, Sunset = SΔ) but now focuses on **behavioral contrast** — how
enriching or impoverishing one component affects responding in the other.

Reuse the Stimulus Control demo level structure (alternating Night/Sunset sub-areas)
but implement an **ABA reversal** across 3 sessions:

---

## Phase Structure (3 Separate Courses)

| Course | Phase | SD1 (Night) | SD2 (Sunset) | Prediction |
|---|---|---|---|---|
| Course A1 | A1 Baseline | VI5s (active) | EXT (empty blocks) | Discrimination |
| Course B | B Contrast | VI5s (active) | VI5s (active) | Negative contrast in SD1 |
| Course A2 | A2 Return | VI5s (active) | EXT (empty blocks) | SD1 rate recovers |

---

## Course A1 / A2: MULT VI5s EXT (Baseline)

**Structure**: 4 Night sub-areas + 4 Sunset sub-areas, alternating (same as Stimulus Control #07).

**Night sub-areas (SD1, VI5s)**:
- Ground: y=1, x=1–25
- VI5s blocks: ? blocks at y=4, x=5,9,13,17,21 using preset VI sequence
  VI sequence: [2,7,4,8,5,6,3,9,4,6] s (convert to tile distances: multiply by 1.33 t/s)
  Block positions approximate the VI intervals:
  - 2 s × 1.33 = ~3 tiles → x=4
  - 7 s × 1.33 = ~9 tiles → x=13
  - 4 s × 1.33 = ~5 tiles → x=20
  Place active [?] coin blocks at these positions.
- Exit pipe → Sunset sub-area

**Sunset sub-areas (SD2, EXT)**:
- Ground: y=1, x=1–25
- 10 empty [!] blocks at y=4: x=3,5,7,9,11,13,15,17,19,21
  (Same visual appearance as Night blocks but pre-emptied)
- Exit pipe → next Night sub-area

---

## Course B: MULT VI5s VI5s (Contrast Phase)

**Same structure** but NOW the Sunset sub-areas ALSO have active [?] coin blocks.

**Sunset sub-areas (SD2, now VI5s)**:
- Replace pre-emptied [!] blocks with active [?] blocks
- Same VI5s schedule and sequence as Night sub-areas
- **Expected**: When SD2 becomes richer, SD1 responding DECREASES (negative contrast)

---

## Observer Tracking for Behavioral Contrast

Observer codes **RESP_1** during Night segments and **RESP_2** during Sunset segments.
Between courses: compare RESP_1 rate in A1 vs. B vs. A2.

Primary contrast measure:
- A1 baseline SD1 rate = R_A1
- B phase SD1 rate = R_B (should decrease — negative contrast)
- A2 return SD1 rate = R_A2 (should return to ≈ R_A1 or exceed it)

---

## Instructor Script Notes

1. **Course A1 (MULT VI5s EXT)**:
   "Night = coins available (VI5s). Sunset = nothing."
   Play through 2 full alternations. "See how I respond in night but stop in sunset?
   That's discrimination from the multiple schedule."

2. **Course B (MULT VI5s VI5s)**:
   "Now I've made BOTH components pay off."
   Play through 2 alternations. "Notice my night responding is LOWER than before.
   That's behavioral contrast — when sunset became richer, I distributed more to it
   and my night rate dropped."

3. **Course A2 (Return)**:
   "Back to sunset = nothing." Play.
   "My night rate comes back up — or even overshoots baseline."
   "Removing the richer comparison made night seem even better in comparison."

4. Debrief: "Multiple schedules show that what happens in one component
   affects behavior in the other. Behavior isn't just controlled by the current
   contingency — the comparison matters."

---

## Verification Checklist
- [ ] Course A1/A2: Night sub-areas have active VI5s blocks; Sunset sub-areas pre-emptied
- [ ] Course B: Both Night and Sunset sub-areas have active VI5s blocks
- [ ] Night filter applied to all Night sub-areas; Sunset filter to all Sunset sub-areas
- [ ] VI sequence identical across all Night sub-areas and all Sunset sub-areas (in B)
- [ ] Pipes connect sub-areas in alternating order (Night → Sunset → Night → ...)
- [ ] Observer briefed to code RESP_1 vs. RESP_2 by background color
- [ ] All 3 course IDs recorded in INDEX.md with phase labels (A1, B, A2)
