# Builder's Guide: Stimulus Control — DEMO Level

**Curriculum position**: 7 of 20
**Phenomenon**: Stimulus Control / Discrimination (SD Night vs. SΔ Sunset)
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground |
| Filter | Alternates: **Night** (SD) and **Sunset** (SΔ) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | ~200 tiles (8 zones) |

---

## Level Overview

8 alternating zones: 4 Night (SD, CRF active) and 4 Sunset (SΔ, extinction).
Zone order is fixed for demo: SD, SΔ, SD, SΔ, SD, SΔ, SD, SΔ (Zone order A).

Each zone is a **sub-area** with a different filter applied. Pipes connect zones.

```
Sub-area 1 (Night → SD)  → pipe → Sub-area 2 (Sunset → SΔ) → pipe
Sub-area 3 (Night → SD)  → pipe → Sub-area 4 (Sunset → SΔ) → ...
```

---

## Building Sub-areas with Different Filters

1. In the SMM2 level editor, tap **Sub-area** at top of screen.
2. Create Sub-area 1. Set filter: Night.
3. Create Sub-area 2. Set filter: Sunset.
4. Repeat for Sub-areas 3–8 (alternating Night/Sunset).

> **Filter must be set before placing blocks.** Changing filter after placement
> may shift block appearances.

---

## Each SD Zone (Night filter) — 5 blocks, CRF

Layout for all 4 Night zones (identical):
- Ground: y=1, x=1–25
- [?] Blocks at y=4: x=5, 9, 13, 17, 21 — each contains 1 coin
- Exit pipe at x=24, y=1 → connects to next sub-area (SΔ zone)

---

## Each SΔ Zone (Sunset filter) — 5 blocks, Extinction

Layout for all 4 Sunset zones (identical):
- Ground: y=1, x=1–25
- **Used blocks** [!] at y=4: x=5, 9, 13, 17, 21 — no coins
- Exit pipe at x=24, y=1 → connects to next sub-area (SD zone)

---

## Pipe Connection Sequence

| From | To | Pipe location |
|---|---|---|
| Main area start | Sub-area 1 (Night) | Main x=5, y=1 → SA1 entry |
| SA1 exit | SA2 (Sunset) | SA1 x=24 → SA2 entry |
| SA2 exit | SA3 (Night) | SA2 x=24 → SA3 entry |
| SA3 exit | SA4 (Sunset) | etc. |
| SA7 exit | SA8 (Sunset) | last zone → goal pole area |

---

## Goal Pole
Final sub-area (SA8, Sunset zone): place goal pole at x=26, y=1–9.

---

## Instructor Script Notes

1. **Night zone**: "It's night — I can see the blue sky. This is when coins appear."
   Hit all 5 blocks. "Every hit pays off in night."
2. **Sunset zone**: "Now sunset — orange sky." Hit blocks. "Nothing."
   Stop hitting quickly. "I learned fast — sunset means extinction."
3. Show increasing speed of discrimination: "By the 3rd night zone, I start hitting
   right away. By 3rd sunset, I barely bother." Demonstrate.
4. Debrief: "The background color is the discriminative stimulus. Night = SD (coins
   available). Sunset = SΔ (no coins). My behavior came under stimulus control —
   I only respond when it pays off."

---

## Verification Checklist
- [ ] 4 Night sub-areas: each has 5 active [?] blocks with coins
- [ ] 4 Sunset sub-areas: each has 5 empty [!] blocks
- [ ] Pipes connect all 8 sub-areas in alternating order (SD → SΔ → SD → ...)
- [ ] Night filter applied to sub-areas 1, 3, 5, 7
- [ ] Sunset filter applied to sub-areas 2, 4, 6, 8
- [ ] Goal pole in final sub-area
- [ ] Test-played: confirm filter change is visible on each pipe transition
