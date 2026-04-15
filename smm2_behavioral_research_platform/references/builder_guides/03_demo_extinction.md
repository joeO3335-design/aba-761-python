# Builder's Guide: Extinction — DEMO Level

**Curriculum position**: 3 of 20
**Phenomenon**: Extinction — baseline CRF → extinction → spontaneous recovery → re-extinction
**Audience**: Instructor demonstration (4 sessions across same or separate days)

---

## Course Settings
| Setting | Value |
|---|---|
| Game Style | SMB1 |
| Theme | Ground (daytime) |
| Time Limit | Unlimited |
| Auto-scroll | Off |
| Starting Power-Up | None (Small Mario) |
| Level Length | ~90 tiles |

---

## Important: Four Separate Course Files

Extinction requires 4 sessions in sequence. Each session is a **separate uploaded
course** with the same layout but different block states:

| Session | Condition | Block state | Upload as |
|---|---|---|---|
| 1 | Baseline (CRF) | All 20 blocks active [?] | Course A |
| 2 | Extinction | All 20 blocks empty [!] | Course B |
| 3 | Spontaneous Recovery (CRF) | All 20 blocks active [?] | Course C (= Course A, re-upload) |
| 4 | Re-extinction | All 20 blocks empty [!] | Course D (= Course B, re-upload) |

> **Shortcut**: Build one course with active blocks (Session 1) and one with empty
> blocks (Session 2). Re-use them for Sessions 3 and 4. Just re-enter the course ID
> in INDEX.md as duplicates.

---

## Layout (all sessions — identical visual arrangement)

### Ground: y=1, x=1–90 (full width)

### Blocks: y=4, x=5 to 83, spaced 4 tiles apart

20 blocks at: x = 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65, 69, 73, 77, 81

- **Session 1 & 3 (CRF)**: All 20 blocks are active [?] blocks containing 1 coin each.
- **Session 2 & 4 (Extinction)**: All 20 blocks are empty/used [!] blocks.

### Checkpoint Flag: x=45, y=1 (midpoint)

### Goal Pole: x=87, y=1–9

---

## SMM2 Build Steps

### Session 1 / Session 3 Course (CRF — active blocks):
1. Fill y=1 with ground from x=1–90.
2. Place 20 [?] blocks at y=4, positions listed above.
3. Long-press each [?] block → set contents to **Coin (default)**.
4. Place checkpoint flag at x=45.
5. Place goal pole at x=87.
6. Test-play: hit every block, confirm 20 coins.
7. Upload → record Course ID.

### Session 2 / Session 4 Course (Extinction — empty blocks):
1. **Clone the CRF course** (or rebuild identically).
2. Replace all [?] blocks with [!] **Used Blocks**.
3. Visual appearance: all blocks appear already-hit (gray/dark).
4. Test-play: hit every block, confirm 0 coins delivered.
5. Upload → record Course ID.

---

## Instructor Script Notes

**Session 1 (Baseline CRF)**:
"I'm going to hit every block I see. Every one pays off — continuous reinforcement."
Hit all 20 blocks. Count aloud or point out each coin.

**Session 2 (Extinction)**:
"Today — same level, same blocks. But something changed."
Hit first few blocks. "Nothing. Keep trying." Continue hitting.
Show extinction burst: hit several in rapid succession.
Show emotional behavior: pause dramatically, express frustration.
Eventually stop hitting. "I've stopped. This is extinction."

**Between sessions 2 and 3** (if same day): 15-minute break minimum.

**Session 3 (Spontaneous Recovery)**:
"It's been a while. Let me try again." Begin hitting.
Show that coins appear again. "It recovered! The behavior came back
even without any re-training. That's spontaneous recovery."

**Session 4 (Re-extinction)**:
"Now let's remove it again." Hit blocks, no coins.
"Notice it extinguishes FASTER this time. This is re-extinction —
extinction history speeds up the next extinction."

---

## Verification Checklist
- [ ] 20 blocks in each course, identical tile positions
- [ ] Session 1/3 courses: all blocks active, each yields 1 coin
- [ ] Session 2/4 courses: all blocks pre-emptied, no coins
- [ ] Checkpoint flag at midpoint
- [ ] Goal pole at end
- [ ] Both courses test-played before data collection
- [ ] All 4 course IDs recorded in INDEX.md
- [ ] If across days: 24h minimum between sessions 2 and 3
