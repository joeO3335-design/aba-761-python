# Builder's Guide: Shaping — DEMO Level

**Curriculum position**: 6 of 20
**Phenomenon**: Shaping — 5 successive approximations, forward chaining, Donut platform
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None (Small Mario) |
| Level Length | ~160 tiles |

---

## Level Overview

Five progressive zones, each requiring a slightly harder jump to reach a coin.
Each zone is separated by a one-way pipe. Once criterion is met (3 successes),
the next zone opens.

```
[Step 1: Platform approach] → [Step 2: Small jump] → [Step 3: Gap clear]
→ [Step 4: Moving platform] → [Step 5: Precision corridor] → [FINISH]
```

---

## Step 1: Platform Approach (x=1 to 25)
**Difficulty**: Low — walk up a staircase to a coin block.

Build ascending staircase:
- x=5, y=1: ground
- x=7, y=2: 1 staircase block
- x=9, y=3: 2 staircase blocks
- x=11, y=4: 3 staircase blocks
- x=13, y=4: [?] coin block (3 high)

Mario walks up stairs and hits the coin block. No jump required.
Criterion: 3 successful coin collections.

**One-way pipe gate** at x=23: opens to Step 2.

---

## Step 2: Small Jump (x=26 to 55)

**Difficulty**: Moderate — must make a small jump to reach a coin block.

Ground at y=1. Gap at x=32–34 (3-tile gap, y=1 missing → pit).
Coin block [?] at x=37, y=4 — requires jump from x=36 to reach it.

Platform sequence:
- Ground x=26–31
- Pit x=32–34 (no ground tiles — instant death if fallen into)
- Ground x=35–55
- [?] coin at x=37, y=4

> For safety during demo, make the pit only 1 tile wide (x=33 only) and add a
> 1-block-wide ledge. Expand gap for later runs if needed.

**One-way pipe gate** at x=53.

---

## Step 3: Gap Clear (x=56 to 90)

**Difficulty**: High — longer gap (4-tile) must be cleared with a running jump.

Ground x=56–68. Gap x=69–72 (4 tiles). Ground x=73–90.
Coin [?] at x=75, y=5 (requires jump + height from running start).

Ensure Mario needs a running jump (at least 3 tiles of approach) to clear the gap.

**One-way pipe gate** at x=88.

---

## Step 4: Moving Platform (x=91 to 130)

**Difficulty**: Very High — must time jump to land on a moving Donut Lift platform.

**Donut Lift**: Place a **Donut Lift** platform at x=104, y=4. Set to move horizontally
between x=100 and x=115 (rail path or auto-move).
- In SMM2: Use a Donut Lift (SMB1 game style) — it falls after Mario stands on it
  for ~2 seconds.
- Set movement: oscillate 10 tiles.

Pit: x=98–120 (22-tile gap) — only traversable via Donut Lift.
Coin [?] at x=117, y=6 (above far ground, requires riding Donut Lift to reach height).

Time limit for Donut Lift ride: ~2 seconds before it starts to fall. Mario must
jump to coin block before lift falls. If Mario rides too long, lift falls → pit.

**One-way pipe gate** at x=128.

---

## Step 5: Precision Corridor (x=131 to 160)

**Difficulty**: Terminal — narrow corridor requires precise movement to avoid hazards.

**Corridor**: 2 tiles wide (y=2–3), ceiling at y=4, floor at y=1. Width x=131–155.
**Hazard**: Buzzy Beetles patrol the corridor (cannot stomp in low ceiling).
- Beetle at x=138, y=2 — patrol range 2 tiles.
- Beetle at x=147, y=2 — patrol range 2 tiles.
Mario must time movement between beetle patrols to pass without contact.

Coin [?] at x=152, y=3 (at end of corridor, after both beetles).

**Goal Pole**: x=158, y=1–6 (shorter, fits narrow area).

---

## Backslide Rule

After **3 consecutive failures** on any step, the instructor returns to the previous
step for 3 more successful trials before re-attempting the harder step.

For the demo level, instructor deliberately fails Step 3 twice to show backslide,
then succeeds on 3rd attempt. "I need 3 in a row before advancing."

---

## Instructor Script Notes

1. Step 1: "I walk up — no jump needed. Easy. 3 successes." Complete 3 times.
2. Step 2: "Now I need a small jump." Jump to coin. "Criterion — 3 in a row."
3. Step 3: "Bigger gap." Miss once. "Failed — but I try again." Succeed twice more.
   "Got my 3 in a row — advance."
4. Step 4: "Moving platform — I need to time it." Land on Donut Lift, reach coin.
5. Step 5: "Precision required." Navigate beetles. Collect coin.
6. Debrief: "Shaping = differentially reinforcing successive approximations.
   We started with what Mario already could do (walking) and gradually required
   closer and closer approximations to the terminal behavior (precision navigation)."

---

## Verification Checklist
- [ ] 5 zones with progressive difficulty
- [ ] Each zone has exactly 1 coin block reachable by the required approximation
- [ ] Donut Lift in Step 4 moves correctly and falls after ~2 s
- [ ] Precision corridor in Step 5: beetles fit within 2-tile-high space
- [ ] One-way pipe gates between all steps
- [ ] Goal pole at end
- [ ] Test-played: confirm all steps are completable by naive observer
