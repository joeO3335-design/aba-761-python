# SMM2 Behavioral Research Platform — Level Spec Index

All levels use SMB1 game style unless otherwise noted.
Course IDs are populated after uploading completed levels to SMM2.

---

## Curriculum Sequence (Programmed Instruction Order)

| # | Phenomenon | Spec File | Key Mechanic | Demo Level ID | Research Level ID |
|---|---|---|---|---|---|
| 1 | Positive Reinforcement | [01_positive_reinforcement.md](01_positive_reinforcement.md) | ? blocks → coins | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 2 | Reinforcement Schedules | [03_reinforcement_schedules.md](03_reinforcement_schedules.md) | FR/VR/FI/VI zones | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 3 | Extinction | [04_extinction.md](04_extinction.md) | Active vs used blocks | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 4 | Negative Reinforcement | [02_negative_reinforcement.md](02_negative_reinforcement.md) | Goomba escape/avoidance | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 5 | Punishment | [08_punishment.md](08_punishment.md) | Buzzy Beetle fork | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 6 | Shaping | [05_shaping.md](05_shaping.md) | Progressive jump difficulty | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 7 | Stimulus Control | [06_stimulus_control.md](06_stimulus_control.md) | Night vs sunset SD | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 8 | Generalization | [07_generalization.md](07_generalization.md) | Cross-theme probe | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 9 | Behavioral Chaining | [09_chaining.md](09_chaining.md) | P-switch → switch → bridge | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 10 | Matching Law | [10_matching_law.md](10_matching_law.md) | Concurrent coin-density fork | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 11 | Explore / Exploit | [11_explore_exploit.md](11_explore_exploit.md) | Hidden block branches + timer | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 12 | Behavioral Momentum | [12_behavioral_momentum.md](12_behavioral_momentum.md) | Rich vs. lean track + disruptor | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |
| 13 | Amelioration | [13_amelioration.md](13_amelioration.md) | Concurrent FR-FR vs. VI-VI fork | XXXX-XXXX-XXXX-XXXX | XXXX-XXXX-XXXX-XXXX |

---

## Files in This Directory

| File | Purpose |
|---|---|
| [TEMPLATE.md](TEMPLATE.md) | Blank spec template for new phenomena |
| [parameters.json](parameters.json) | Machine-readable IV parameters for all levels (used by analysis notebooks) |
| `01_positive_reinforcement.md` through `11_explore_exploit.md` | Full level specs |

---

## Quick Reference: Companion App Phenomena Keys

These keys match the `phenomenon_key` field in the companion app and the
exported CSV `phenomenon` column.

| CSV Key | Label |
|---|---|
| `positive_reinforcement` | Positive Reinforcement |
| `negative_reinforcement` | Negative Reinforcement |
| `reinforcement_schedules` | Reinforcement Schedules |
| `extinction` | Extinction |
| `shaping` | Shaping |
| `stimulus_control` | Stimulus Control / Discrimination |
| `generalization` | Generalization |
| `punishment` | Punishment |
| `chaining` | Behavioral Chaining |
| `matching_law` | Matching Law |
| `explore_exploit` | Exploration vs. Exploitation |
| `behavioral_momentum` | Behavioral Momentum |
| `amelioration` | Amelioration |

---

## Replication Checklist (before data collection)

- [ ] Level built and test-played by naive observer (not the builder)
- [ ] Course ID recorded in this index
- [ ] Block/coin placement verified with stopwatch (for interval schedules)
- [ ] Starting power-up state confirmed at each checkpoint
- [ ] Observer trained to IOA criterion (≥80% agreement on pilot coding)
- [ ] Companion app phenomena.json verified to match current level design
- [ ] Screen recording software running and timestamp-synced
- [ ] Participant instructions script printed and available

---

## Data Flow

```
SMM2 Level played
      │
      ├── Screen recording (MP4) — timestamped
      │
      ├── Companion app (live coding) → data/raw/{pid}_{level}_{session}.csv
      │
      └── SMM2 built-in stats (clear rate, death map) — manually entered
                                                       → data/raw/smm2_builtin_stats.csv

All three streams share wall_time as the sync key.

Processed data → data/processed/
Analysis       → notebooks/
Figures        → reports/figures/
```
