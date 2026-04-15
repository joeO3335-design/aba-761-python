# Builder's Guide: Negative Reinforcement — DEMO Level

**Curriculum position**: 4 of 20
**Phenomenon**: Negative Reinforcement — Escape, Avoidance, Mixed
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | **Super Mario** (mushroom active) |
| Level Length | ~180 tiles (3 zones) |

> **Critical**: Participant must start as Super Mario (has taken 1 mushroom).
> Goomba contact removes the power-up (downsizes to Small Mario) — this is the
> aversive consequence (power-up loss = punishing contact, avoidance = keeping
> Super Mario state).

---

## Level Overview

Three zones: Escape → Avoidance → Mixed. Each zone has Goombas on patrol.
Mario must respond (jump on Goomba OR escape the zone) to terminate aversive contact.

```
[START — Super Mario] → [ESCAPE ZONE] → [CP] → [AVOIDANCE ZONE] → [CP] → [MIXED ZONE] → [FINISH]
```

---

## Zone 1: Escape (x=1 to 50)

**Concept**: Aversive stimulus (Goomba) is **already present** at trial start.
Mario must stomp the Goomba to escape the aversive.

### Layout

Ground: y=1, x=1–50.

**Platform tunnel**: Create a confined corridor 3 tiles high to ensure Goomba contact
is likely if Mario doesn't act:
- Ceiling tiles: [H] hard blocks at y=4, x=1–50 (continuous ceiling).
- This creates a 3-tile tall corridor (y=1–3) where Mario cannot jump over Goombas.

**Goomba placement** (10 trials):
Place **Goombas** at x=5, 10, 15, 20, 25, 30, 35, 40, 45, 50.
Each Goomba patrols a 3-tile range (±3 tiles from start position).
Set Goomba patrol: long-press Goomba → wing = off; behavior = patrol.

**Escape response**: Stomp (jump on) the Goomba. Goomba is defeated. Aversive removed.
Mario continues to next Goomba.

> If Mario is hit (fails to stomp): he downsizes to Small Mario. Place a **power-up
> mushroom** in a hidden block [?] at y=2 somewhere in zone 1 (x=25) so Mario can
> restore Super state for continued demonstration.

**Checkpoint flag**: x=48, y=1.

---

## Zone 2: Avoidance (x=52 to 120)

**Concept**: Aversive stimulus is **signaled in advance** (warning stimulus).
Mario can avoid contact entirely by acting before Goomba reaches him.

### Warning Stimulus
In SMM2, the warning signal is implemented as a **visual contrast**: Goombas in this
zone are preceded by a **coin trail** (coins on the ground) that appears ~4 tiles
before the Goomba's position. Mario sees coins → knows Goomba is ahead → can jump
over or prepare.

Alternatively: the **Goomba starts off-screen** and a sound/visual cue is created by
a [?] block that drops a coin automatically when Mario approaches (ON/OFF switch
mechanism). For simplicity: use the coin trail approach.

### Layout

Ground: y=1, x=52–120. Open ceiling (no tunnel).

**Coin trails** (warning stimulus, 4 tiles before each Goomba):
- Coins at: x=54,55,56,57 (warning) + Goomba at x=60
- Coins at: x=64,65,66,67 + Goomba at x=70
- Coins at: x=74,75,76,77 + Goomba at x=80
- Coins at: x=84,85,86,87 + Goomba at x=90
- Coins at: x=94,95,96,97 + Goomba at x=100
- Coins at: x=104,105,106,107 + Goomba at x=110
- Coins at: x=114,115,116,117 + Goomba at x=120

> **Avoidance response**: Mario sees coins (warning SD) → jumps early → clears Goomba
> without contact. Power-up preserved (negative reinforcement = avoidance successful).
> If Mario ignores warning and contacts Goomba: power-up lost (aversive consequence).

Goombas face left (toward Mario). Set patrol range minimal so they don't move far.

**Checkpoint flag**: x=118, y=1.

---

## Zone 3: Mixed (x=122 to 175)

**Concept**: 50% escape trials (Goomba already present, no warning) and 50% avoidance
trials (coin-trail warning, Goomba following). Observer must track which trial type occurs.

### Layout

Ground: y=1, x=122–175. Half-height ceiling optional.

Alternate escape and avoidance trials:
- x=125: Goomba (no warning coins) → ESCAPE trial
- x=133: Coins at 133–136, Goomba at 138 → AVOIDANCE trial
- x=143: Goomba at 143 (no warning) → ESCAPE trial
- x=151: Coins at 151–154, Goomba at 156 → AVOIDANCE trial
- x=161: Goomba at 161 (no warning) → ESCAPE trial
- x=169: Coins at 169–172, Goomba at 174 → AVOIDANCE trial

> Instructor demonstrates different response patterns: active stomp (escape) vs.
> early jump (avoidance). Both remove/prevent aversive.

**Goal Pole**: x=178, y=1–9

---

## Starting Power-Up Note

Place a **Mushroom** in the very first block (x=3, y=4 [?] block → set contents to
Mushroom). This gives Mario the Super state immediately if he wasn't already Super.
For the research level, set starting power-up to **Super Mario** in course settings
so every session starts consistently.

---

## Instructor Script Notes

1. **Escape Zone**: "A Goomba is right here — I'm already in danger. I need to stomp
   it to get safe again. My stomp removes the aversive — that's negative reinforcement."
2. **Avoidance Zone**: "See the coins? That's my warning. A Goomba is coming.
   If I jump NOW, before it reaches me, I avoid contact completely."
   Jump before coins end. "I never got hurt — I prevented the aversive. Still
   negative reinforcement, but through avoidance."
3. **Mixed Zone**: "Sometimes I see a warning, sometimes I don't.
   Watch how my behavior changes." Show both response types.
4. Debrief: "Negative reinforcement = the removal or prevention of an aversive
   strengthens the behavior that caused it. Not punishment — I'm not being punished;
   I'm being trained to respond to remove something bad."

---

## Verification Checklist
- [ ] Course starts as Super Mario (course settings → power-up)
- [ ] Zone 1: 10 Goombas in enclosed corridor, stomp = escape response
- [ ] Zone 2: Coin trails 4 tiles before each of 7 Goombas, open corridor
- [ ] Zone 3: 3 escape + 3 avoidance trials alternating
- [ ] Mushroom available in Zone 1 (x=25) as recovery power-up
- [ ] Checkpoint flags after Zones 1 and 2
- [ ] Goal pole at end
- [ ] Test-played by naive observer (confirm Goomba patrol ranges)
- [ ] Course ID recorded in INDEX.md
