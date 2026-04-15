# Builder's Guide: Behavioral Chaining — DEMO Level

**Curriculum position**: 9 of 20
**Phenomenon**: Behavioral Chaining — 4-link forward chain (P-switch → ON/OFF switch → P-switch 2 → flag)
**Audience**: Instructor demonstration

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None |
| Level Length | ~120 tiles |

---

## Chain Structure

| Link | Response | Conditioned SR (SD for next link) | Next link SD |
|---|---|---|---|
| 1 | Hit P-switch 1 | Blue coin trail appears | Coin trail on ground |
| 2 | Hit ON/OFF switch | Red/Blue barrier disappears | Open corridor |
| 3 | Hit P-switch 2 | Note-block bridge appears over pit | Bridge visible |
| 4 | Cross bridge to goal flag | Level complete fanfare | — |

P-switch duration: 10 seconds each.

---

## Full Layout

### Opening Corridor (x=1–15)
- Ground: y=1, x=1–15
- Open space: no obstacles, Mario walks to P-switch 1

### Link 1: P-switch 1 (x=16)
- P-switch at x=16, y=1 (on the ground, Mario runs over it to activate)
- When activated: Blue coins appear (a trail of blue coins spawns)
  — Use P-switch mechanics: place blue coins on the ground that appear when P-switch is active

> **P-switch blue coins**: In SMM2, placing blue coins on the ground near a P-switch
> makes them appear when the P-switch activates. Place blue coins at x=20–40
> along the ground. These are Link 1's conditioned SR.

### Blue Coin Trail (x=20–40)
- Blue coins at y=1: x=20,22,24,26,28,30,32,34,36,38,40
- These coins only appear when P-switch 1 is active

### Link 2: ON/OFF Switch (x=42)
- ON/OFF switch at x=42, y=1 (Mario runs into it to toggle)
- Before activation: Red ON/OFF blocks form a wall at x=45–47, y=1–5 (barrier)
- After activation: barrier becomes Blue (passable) OR disappears
  — In SMM2: ON/OFF switch toggles red/blue blocks. Set red blocks as wall.
  After toggle, Mario can pass through blue blocks (they become solid floor, not wall)
  — Alternative: Place hard blocks at x=45–46; use ON/OFF switch to remove them via
  a sub-area mechanism. For simplicity: use standard ON/OFF switch + red blocks.

Place red ON/OFF blocks at x=45, y=1–4 (4-high wall).
After ON/OFF switch hit: blocks change state → Mario can pass.

### Open Corridor (x=46–65)
- Ground: y=1, x=46–65
- Open space — Mario can now pass (Link 2 completed)
- Sign showing "LINK 3" (demo level)

### Link 3: P-switch 2 (x=67)
- Second P-switch at x=67, y=1
- Pit: x=70–82 (13-tile gap, instant death without bridge)
- When P-switch 2 activated: Note blocks appear over the pit at y=1, x=70–82
  (forming a bridge — in SMM2, P-switch converts coins to bricks; place coins at pit level)

> Place coins at y=1, x=70–82 (on the ground over the pit). When P-switch 2 activates,
> these coins become bricks that Mario can walk on.
> Note: pit needs a floor below the coin level. Place coins at y=2; real ground at y=0
> is absent (pit). The bricks form a bridge at y=2.

Adjusted: place pit by removing ground tiles x=70–82 at y=1. Place coins at y=2
(floating). P-switch → coins become bricks at y=2 → Mario can walk across.

P-switch 2 duration: 10 s. Mario must cross the 13-tile bridge before P-switch expires.
At walk speed 1.33 t/s: 13 tiles / 1.33 = ~10 s. Tight! Encourage running.

### Link 4: Cross Bridge and Flag (x=83–90)
- Ground resumes at x=83, y=1
- Short approach corridor
- **Goal Pole** at x=88, y=1–9

---

## Partial Chain Training (Research Level)

For the research level, the chain is introduced link by link across trials:
- Trials 1–3: Only Link 4 available (just walk to flag)
- Trials 4–6: Links 3–4 (hit P-switch 2, cross bridge, flag)
- Trials 7–9: Links 2–4 (ON/OFF switch, P-switch 2, flag)
- Trials 10–15: Full chain (all 4 links)

Build 4 separate courses for training:
| Course | Links available | What's pre-done |
|---|---|---|
| Course A | 4 only | P-switches already activated; bridge already up; barrier already open |
| Course B | 3–4 | P-switch 1 already activated; barrier open |
| Course C | 2–4 | P-switch 1 already activated |
| Course D | 1–4 | Full chain — nothing pre-activated |

---

## Instructor Script Notes

1. Start: "There are 4 steps I need to do in order."
2. Hit P-switch 1: "Blue coins appear — that's my signal to proceed." Follow trail.
3. Hit ON/OFF switch: "The barrier opens — Link 2 done." Pass through.
4. Hit P-switch 2: "Bridge appears!" Cross quickly.
5. Reach flag: "Complete!"
6. Debrief: "Each link's completion produced a conditioned reinforcer — a stimulus change
   that signaled and reinforced doing the next step. Remove any link and the chain breaks."

---

## Verification Checklist
- [ ] P-switch 1 activates blue coin trail (test in editor)
- [ ] ON/OFF switch + red blocks form wall; toggle opens passage
- [ ] P-switch 2 converts ground coins to brick bridge over pit
- [ ] Goal pole reachable from bridge within P-switch 2 duration (test run it)
- [ ] Research level: 4 partial-chain courses built (A–D)
- [ ] All course IDs recorded in INDEX.md
