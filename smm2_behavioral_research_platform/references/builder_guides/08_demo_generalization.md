# Builder's Guide: Generalization — DEMO Level

**Curriculum position**: 8 of 20
**Phenomenon**: Stimulus Generalization — training on Night/Ground, probe across 4 themes
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Varies by segment (5 themes) |
| Filter | Night (training only); none on probe segments |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | ~120 tiles (5 segments) |

---

## Level Structure

5 segments via sub-areas:
1. Training (Ground / Night) — CRF reinforced
2. Probe 1 (Underground) — Extinction probe
3. Probe 2 (Water/Ocean) — Extinction probe
4. Probe 3 (Castle) — Extinction probe
5. Probe 4 (Airship) — Extinction probe

Each segment = 5 ? blocks (training: active; probes: pre-emptied).

---

## Segment 1: Training — Ground/Night (Sub-area 1)

Settings: Theme = **Ground**, Filter = **Night**

- Ground: y=1, x=1–25
- [?] blocks at y=4: x=5, 9, 13, 17, 21 — all yield coins (CRF)
- Exit pipe at x=24 → Sub-area 2 (Probe 1)

---

## Segment 2: Probe 1 — Underground (Sub-area 2)

Settings: Theme = **Underground** (auto-applies dark cave background), Filter = None

- Ground: y=1, x=1–25
- [!] Used blocks at y=4: x=5, 9, 13, 17, 21 — no coins (extinction probe)
- Similarity to training: high (same block types, different background color/theme)
- Exit pipe at x=24 → Sub-area 3

---

## Segment 3: Probe 2 — Water/Ocean (Sub-area 3)

Settings: Theme = **Water (Beach/Ocean)**, Filter = None

Same layout as above: 5 [!] used blocks at y=4.

---

## Segment 4: Probe 3 — Castle (Sub-area 4)

Settings: Theme = **Castle**, Filter = None

Same layout: 5 [!] used blocks at y=4.

---

## Segment 5: Probe 4 — Airship (Sub-area 5)

Settings: Theme = **Airship**, Filter = None

Same layout: 5 [!] used blocks at y=4.
Goal pole at x=26, y=1–9.

---

## Similarity Gradient (from parameters.json)
| Theme | Similarity to Training |
|---|---|
| Underground | 0.75 (similar underground feel) |
| Water | 0.50 |
| Castle | 0.25 |
| Airship | 0.10 (most dissimilar) |

Observer codes responses per probe segment. Expected: most responding in Underground
(most similar to training), fewest in Airship (most dissimilar).

---

## Instructor Script Notes

1. Training: "I'll hit every block — it pays off in night on the ground."
   Hit all 5. 5 coins.
2. Probe 1 (Underground): "New environment." Hit a few blocks. "Nothing."
   Continue hitting. "Still nothing — but I hit several times before stopping.
   The underground looks a little like night ground, so I generalized."
3. Probe 2 (Water): "Even more different." Fewer hits before stopping.
4. Probe 3 (Castle): "Less familiar." Minimal hits.
5. Probe 4 (Airship): "Nothing like training." 0–1 hits then stop.
6. Debrief: "I responded most where the stimulus was most similar to training.
   Less similar → fewer responses. That's a generalization gradient."

---

## Verification Checklist
- [ ] Training segment: Night filter, Ground theme, 5 active [?] blocks
- [ ] Probe segments 1–4: No filter, correct themes (Underground/Water/Castle/Airship)
- [ ] All probe segments: 5 pre-emptied [!] blocks (no coins)
- [ ] Block positions identical across all 5 segments (y=4, x=5,9,13,17,21)
- [ ] Pipes connect all 5 sub-areas in sequence
- [ ] Goal pole in Probe 4 segment
- [ ] Test-played: confirm theme change is visible on each transition
