# Target Bank — walkthrough

A quick tour of the **🏦 Target Bank** in Repertiores. The bank is a shared
library of reusable target templates: write a target once, then drop it into any
learner's program. A narrated screencast is at
[media/target_bank_demo_narrated.mp4](media/target_bank_demo_narrated.mp4).

---

## 0. Open it

Sidebar → **🏦 Target Bank**. (It's roster-wide, not per-student.)

## 1. Find targets

The bank holds hundreds of entries. Narrow them three ways, which combine:

- **Operant** — multiselect (Mand, Tact, Listener, …)
- **Skill list** — multiselect of the named lists in scope
- **Search description** — free text (e.g. `touch`, `dog`, `fruit punch`)

The caption shows **N of M entries shown**. The table lists Operant · List ·
Target · Cons. Y (consecutive-Y mastery criterion).

## 2. Select

- Tick rows individually, or
- **✓ Select all shown** to grab everything in the current filter, or
- **Clear selection** to reset.

Selections persist across filter changes, so you can search `touch`, select all,
then search `point`, select all, and carry both sets forward. The caption tracks
"X of N shown checked · Y selected in total."

## 3. Import into a learner

1. Pick the learner in **Add to student**.
2. Click **➕ Add N to \<student\>** — the selected templates are copied into that
   learner's targets as **In Acquisition**, with their mastery-N.

They immediately appear in that learner's **Verbal Behavior Programming** and
**Collect Cold Probe Data** pages, ready to probe.

## 4. Curate the bank

**🗑️ Delete N from bank** removes the selected templates from the shared library
(it does *not* touch targets already imported into learners).

## Where bank entries come from

On a learner's operant page (Verbal Behavior Programming → an operant), check
targets and press **💾 Save N to bank** to add them as reusable templates. So the
bank grows from real targets you've already written, and flows back out to new
learners.

---

## About the demo video

The screencast imports a filtered set into the disposable **VB-MAPP Demo**
student to show the success path, then those imports are removed automatically —
no real learner data is changed. Pre-demo backup:
`data/backups/targets.<timestamp>.pre_bankdemo.json`.
