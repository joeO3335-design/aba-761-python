# Builder's Guide: Positive Reinforcement — RESEARCH Level

**Curriculum position**: 1 of 13
**Phenomenon**: Positive Reinforcement (CRF → FR3 → VR3 → Extinction)
**Audience**: Participant data collection; observer codes responses

---

## Course Settings

| Setting | Value |
|---|---|
| Game Style | Super Mario Bros. (SMB1) |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None (Small Mario) |
| Level Length | ~145 tiles wide |

---

## Key Differences from Demo Level

The research level is **structurally identical** to the demo level.
The only differences are:

1. **No zone label signs** — do not place text signs identifying the schedule.
   Participants should discover the contingency, not be told it.
2. **Taller walls between zones** — 5 blocks high instead of 3, so participants
   cannot see the next zone until they pass through the gate.
3. **One-way pipe at each gate** — place a **pipe that exits into the next zone**
   rather than an open gap. This creates a brief transition moment and prevents
   participants from walking backward to rehit blocks.

---

## Exact Block Layout

### Zone 1: CRF (x=1 to 26)

Ground: y=1, x=1–26

? Blocks at y=4:
- x=5, 7, 9, 11, 13, 15, 17, 19, 21, 23 — all contain **1 coin each**

Pipe gate (exit pipe):
- Entry pipe at x=24, y=1 (facing up, Mario enters from top)
- Exit pipe in Zone 2 at x=28, y=1 (facing up, Mario exits top)

---

### Zone 2: FR3 (x=28 to 57)

Ground: y=1, x=28–57

Block sequence at y=4 (same as demo, no labels):
- x=31 [!], x=33 [!], x=35 [?] coin
- x=37 [!], x=39 [!], x=41 [?] coin
- x=43 [!], x=45 [!], x=47 [?] coin
- x=49 [!], x=51 [!], x=53 [!] (partial ratio — no coin; participant walks past)

Pipe gate:
- Entry pipe at x=56, y=1; exit pipe in Zone 3 at x=60, y=1

---

### Zone 3: VR3 (x=60 to 120)

Ground: y=1, x=60–120

Block sequence at y=4 per VR sequence [1,3,5,2,4,3,1,5,2,3]:

| x | Type | Notes |
|---|---|---|
| 62 | [?] coin | VR=1 |
| 64 | [!] | VR=3 |
| 66 | [!] | VR=3 |
| 68 | [?] coin | VR=3 |
| 70 | [!] | VR=5 |
| 72 | [!] | VR=5 |
| 74 | [!] | VR=5 |
| 76 | [!] | VR=5 |
| 78 | [?] coin | VR=5 |
| 80 | [!] | VR=2 |
| 82 | [?] coin | VR=2 |
| 84 | [!] | VR=4 |
| 86 | [!] | VR=4 |
| 88 | [!] | VR=4 |
| 90 | [?] coin | VR=4 |
| 92 | [!] | VR=3 |
| 94 | [!] | VR=3 |
| 96 | [?] coin | VR=3 |
| 98 | [?] coin | VR=1 |
| 100 | [!] | VR=5 |
| 102 | [!] | VR=5 |
| 104 | [!] | VR=5 |
| 106 | [!] | VR=5 |
| 108 | [?] coin | VR=5 |
| 110 | [!] | VR=2 |
| 112 | [?] coin | VR=2 |
| 114 | [!] | VR=3 |
| 116 | [!] | VR=3 |
| 118 | [?] coin | VR=3 |

Total blocks: 29 | Reinforced: 10 | Average ratio: 2.9 ≈ VR3 ✓

Pipe gate:
- Entry pipe at x=119, y=1; exit pipe in Zone 4 at x=123, y=1

---

### Zone 4: Extinction (x=123 to 145)

Ground: y=1, x=123–145

Used blocks at y=4 — all pre-emptied:
- x=125, 127, 129, 131, 133, 135, 137, 139, 141, 143

**Goal Pole**: x=146, y=1–9

---

## Observer Setup

The observer codes each block hit as a **RESPONSE** event using the companion app
(`positive_reinforcement` phenomenon selected). When a coin is delivered, log
**SR_PLUS**. When no coin is delivered, the block hit is still coded as **RESPONSE**.

Companion app event codes for this phenomenon:
- `RESPONSE` — any block hit
- `SR_PLUS` — coin delivered
- `SR_OMIT` — response with no reinforcement (EXT blocks)

The app will timestamp all events. Observer should not announce schedule
transitions to the participant.

---

## Verification Checklist

- [ ] No text signs in any zone
- [ ] 10 active ? blocks in Zone 1 (CRF), all yield coins
- [ ] Zone 2: exactly pattern [!][!][?] repeated 3 times; partial group at end
- [ ] Zone 3: 29 blocks, 10 reinforced per VR sequence (verify count)
- [ ] Zone 4: 10 used blocks, pre-emptied
- [ ] Pipe gates connect zones in one direction only (cannot go back)
- [ ] Goal pole present
- [ ] Test-played by naive observer; no accidental deaths
- [ ] Course ID recorded in INDEX.md after upload
