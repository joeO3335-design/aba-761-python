# VB-MAPP Assessment — walkthrough

A hands-on tour of the **📈 VB-MAPP Assessment** page in Repertiores, using the
seeded **"VB-MAPP Demo"** student. It scores the 170 VB-MAPP milestones
(Sundberg, 2008) — 3 levels × 16 skill areas — **0 / ½ / 1** across up to four
test administrations, and links milestones to your existing cold-probe system.

> The demo data is safe to delete (see the last section). It does not touch any
> real student.

---

## 0. Open the page

1. Start the app from the repo root: `streamlit run Repertiores/app.py`
   (or it's already running at **http://localhost:8535**).
2. In the sidebar **Student** dropdown, pick **VB-MAPP Demo**.
3. Click **📈 VB-MAPP Assessment** in the sidebar nav (just under EFL Assessment).

You'll land on a page headed *VB-MAPP Milestones · VB-MAPP Demo*, showing the
child's name, DOB (2022-09-15), and current age.

---

## 1. Test administrations

The **Test administrations** grid records the *date / tester / notes* for each of
the four columns on the Milestones Master Scoring Form. The demo has:

| Test | Date | Tester | Notes |
|---|---|---|---|
| 1st | 2026-02-10 | J. Ott | Baseline. |
| 2nd | 2026-05-28 | J. Ott | Follow-up after a teaching block. |

Edit any cell inline. Blank date = that test wasn't run.

---

## 2. Score the milestones (the grid)

Milestones are split into three tabs — **Level 1 (45) · Level 2 (60) · Level 3 (65)**.
Each row is one milestone:

- **Code** — the VB-MAPP label (`1-M` … `15-M`)
- **Area** — e.g. Mand, Tact, VP-MTS
- **Skill** — the milestone criterion
- **Live (from probes)** — auto-derived (see §4)
- **Test 1–4** — pick **— / 0 / ½ / 1** for each administration

Try it: open **Level 1**, find **Tact · 4-M** and change its **Test 2** score.
The score scale matches the VB-MAPP exactly: `1` = full credit, `½` = partial,
`0` = scored but absent, `—` = not tested. Hover a milestone's score cell to pick.

Nothing is saved until you press **💾 Save VB-MAPP assessment** at the bottom, so
you can explore freely and just not save.

---

## 3. Read the Master Form snapshot

Scroll to **Master Form snapshot**. The metric tiles roll your 0/½/1 scores up to
total points, exactly like the paper Master Scoring Form. For the demo:

- **Test 1 → 65.5 / 170** (`L1 43/45 · L2 22/60 · L3 0/65`)
- **Test 2 → 71.5 / 170** — the teaching block added **+6.0** points

The **By area** expander breaks each area's points down per test — useful for
spotting which repertoires moved and which stalled (here, Echoic, Mand, and Tact
gained between tests; Level 3 is still untested).

---

## 4. Link milestones to cold probes ("Live")

This is the integration with the rest of Repertiores. Scroll to **Milestone detail**:

1. In the **Milestone** dropdown choose **`Mand-5`** (`L1 · Mand · 5-M — Emits 10
   different mands…`). You'll see its objective and the **1-point / ½-point**
   criteria spelled out.
2. Notice it says *Already linked: 1 cold-probe target* — "Mands 'cookie'
   independently", status **Mastered**.
3. Go back to the **Level 1** grid: the **Live (from probes)** column for
   **Mand-5** now reads **`1 · 1/1 mastered`** — the score *derived from the
   cold-probe data*, independent of what you typed in the Test columns.

The demo also links **`Tact-6`** to an *In Acquisition* target, so its Live column
shows **`½ · 0/1 mastered`**. The rule:

| Linked cold-probe targets | Live score |
|---|---|
| all Mastered | **1** |
| some Mastered or In Acquisition | **½** |
| none progressing | **0** |
| none linked | **—** |

### Push a milestone into a probe program

Still in **Milestone detail**, pick any milestone and use **📝 Track this
milestone as a cold-probe target**:

- The **Operant** pre-fills from the area (Mand→Mand, VP-MTS→Visual Performance,
  Reading/Writing/Math→Academics, …).
- Edit the description, set **Mastery N**, and click **➕ Add as cold-probe
  target**.

It creates a normal Repertiores target tagged with `vbmapp_milestone_code`, so it
shows up in **Collect Cold Probe Data** / **Verbal Behavior Programming** like any
other — and once its probes hit mastery, this milestone's **Live** column updates
automatically.

---

## 5. Save

Press **💾 Save VB-MAPP assessment**. The grid + test metadata persist to
`Repertiores/data/vbmapp_assessments.json`, keyed by `student_id`. Re-open the
page anytime to continue or start the next administration.

---

## Typical workflow

1. **Baseline** — run Test 1, score every area to the child's ceiling (stop an
   area after ~3 consecutive `0`s), record date/tester.
2. **Program** — for emerging areas, push the next milestone(s) into cold-probe
   targets via *Track this milestone*.
3. **Teach & probe** — collect cold-probe data on those targets in the existing
   pages; watch the **Live** column move.
4. **Re-assess** — quarterly, run Test 2/3/4; the snapshot shows growth in points
   per level.

---

## Removing the demo

The demo lives only in these files under `Repertiores/data/`:
`students.json` (the `VB-MAPP Demo` row), `vbmapp_assessments.json`,
`targets.json` (2 rows tagged `demo_vbmapp`), and `probes.json` (their probes).

To remove it: delete the **VB-MAPP Demo** student on **Student Home** (this also
clears its targets/probes), then delete its record from
`data/vbmapp_assessments.json`. Pre-seed backups are in `data/backups/*.pre_demo.json`.

---

## Scope note

This page covers the **Milestones Assessment only** (170 milestones). The VB-MAPP
Barriers (24) and Transition (18) assessments, the ~900-skill Task Analysis, and
the Placement/IEP-goal chapters are **not** included — the source material for
those wasn't part of this build. Milestone content: Sundberg, M. L. (2008),
*VB-MAPP*; EESA subtest by Barbara E. Esch.
