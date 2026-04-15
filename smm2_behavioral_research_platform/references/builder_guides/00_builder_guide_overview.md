# SMM2 Behavioral Research Platform — Builder's Guide Overview

These guides give tile-by-tile construction instructions for every level in the
curriculum sequence. Because SMM2 levels must be built manually inside the
Nintendo Switch game editor, these documents are your blueprint.

---

## How to Use These Guides

1. **Boot SMM2** → tap **Course Maker** → **New Course**.
2. Set the global options listed in each guide's **Course Settings** section
   before placing any tiles (game style, theme, time limit, scroll speed).
3. Use the **tile grid** descriptions: the guide gives (x, y) coordinates where
   **x = tile columns from the left edge (1-based)** and
   **y = tile rows from the ground (1 = ground row, numbers increase upward)**.
4. When a guide says **"pipe at (12, 1)"**, that means column 12, sitting on the
   ground (row 1).
5. Sub-areas are built separately in the editor under **Sub-area** tab and
   linked via pipes or doors.
6. **Test-play** every zone before saving. A naive observer (someone who did not
   build it) must be able to play it without dying unexpectedly.

---

## Tile Shorthand Used in These Guides

| Symbol | SMM2 Object |
|---|---|
| `[?]` | ? Block (contains coin or power-up) |
| `[!]` | Used/Empty Block (already hit — delivers nothing) |
| `[B]` | Brick Block |
| `[H]` | Hard Block |
| `[G]` | Ground tile |
| `[P]` | Pipe (green, upward-facing unless noted) |
| `[PL]` | Pipe (left-facing) |
| `[PR]` | Pipe (right-facing) |
| `[$]` | Coin on ground |
| `[SW]` | ON/OFF Switch block |
| `[PS]` | P-Switch |
| `[NB]` | Note Block |
| `[DL]` | Door (left room) |
| `[DR]` | Door (right room) |
| `[F]` | Goal Pole (finish flag) |
| `[CP]` | Checkpoint Flag |
| `[1U]` | Mushroom (power-up; gives Super Mario state) |
| `[Gm]` | Goomba |
| `[Bz]` | Buzzy Beetle |

---

## SMM2 Editor Basics Checklist

- **Game style**: Set first — changing it after placement resets many objects.
- **? block contents**: Long-press a ? block to set what it contains
  (coin = default; Mushroom/Fire Flower = power-up).
- **Coin density in ? blocks**: Place multiple ? blocks in sequence;
  each single-block hit gives 1 coin. To give 0 coins on one block
  (making it a "used block" in baseline before participants touch it),
  use an **empty/used block** (`[!]`).
- **One-way passages**: Use **Arrow signs** or **One-way walls** (from the
  track/rail tile set) to keep participants from backtracking.
- **Pipes as teleporters**: Tap a pipe to connect it to a destination pipe.
  Always test the connection direction (enter from top vs. side).
- **Sub-areas**: Up to 4 sub-areas per course; use them to isolate conditions
  that share the same level timer but need visual separation.
- **Auto-scroll**: Set under Course → Auto-scroll. Leave OFF for all
  research levels in this platform.

---

## File Naming Convention

```
01_demo_positive_reinforcement.md     ← Instructor demonstration level
01_research_positive_reinforcement.md ← Participant research level
02_demo_reinforcement_schedules.md
02_research_reinforcement_schedules.md
...
```

Curriculum order (1–13) matches the programmed instruction sequence in INDEX.md.
