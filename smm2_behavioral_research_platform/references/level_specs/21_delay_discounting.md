# Level Spec: Delay Discounting

---

## Phenomenon
Delay discounting refers to the finding that the subjective value of a reinforcer
decreases as the delay to its receipt increases (Rachlin & Green, 1972; Mazur, 1987;
Ainslie, 1975). When choosing between a smaller-sooner (SS) reinforcer and a
larger-later (LL) reinforcer, preference shifts from LL to SS as the LL delay
grows — even when the LL amount is objectively larger and the choice would
maximize total reinforcement if waited for.

The form of the discount function is well-captured by Mazur's (1987) hyperbolic
equation:

> **V = A / (1 + k·D)**

where:
- **V** = subjective (discounted) value of the delayed reinforcer
- **A** = objective amount of the reinforcer
- **D** = delay to receipt
- **k** = discount rate (individual-difference parameter; higher k = steeper
  discounting = more "impulsive")

Hyperbolic discounting predicts **preference reversal**: early (when both options are
distant), the LL reward appears preferable. As time passes and both options draw
near, the SS reward's value rises faster than the LL's (steeper near-delay slope),
producing a crossover. This reversal is the signature phenomenon that distinguishes
hyperbolic from exponential discounting models.

Key predictions:
1. **Indifference point** (D_50% = delay at which SS and LL are chosen equally often)
   scales with amount ratio: larger LL amounts tolerate longer delays before
   SS is preferred.
2. **Magnitude effect**: k decreases with absolute amount — participants discount
   large amounts less steeply than small amounts (Kirby, 1997; Green & Myerson, 2004).
3. **Individual differences in k** correlate with clinically relevant behaviors:
   substance use, gambling, obesity, ADHD (Bickel et al., 1999; Madden & Bickel, 2010).

## Learning Objective
Participants:
1. Experience direct choice between an immediate smaller reinforcer and a delayed
   larger reinforcer across a range of delays.
2. Observe their own choice proportion shift from LL-preference (short delays)
   to SS-preference (long delays).
3. Have their individual discount rate (k) estimated from their choice data via
   hyperbolic fit — providing a personalized, quantitative impulsivity index.
4. Understand the preference-reversal prediction of hyperbolic discounting.

## Behavioral Target
- **Response**: Choice between SS (left) and LL (right) at a visible fork
- **Smaller-Sooner (SS)**: 1 coin immediately after a 1-tile corridor (<1 s delay)
- **Larger-Later (LL)**: 5 coins after traversing a variable-length delay corridor
  (3, 10, 20, 40, or 60 seconds of walking)
- **Consequence**: Coin(s) delivered on arrival at the end of each path
- **Antecedent**: Visible fork with both path lengths fully visible before the choice
  (participants can see the LL corridor length as the "delay" cue)

---

## SMM2 Level Settings
| Parameter | Demo Level | Research Level |
|---|---|---|
| Game Style | SMB1 | SMB1 |
| Theme | Ground (daytime) | Ground (daytime) |
| Time Limit | None | None |
| Starting Power-Up | Small Mario | Small Mario |
| Auto-scroll | Off | Off |
| Level Length | Looped fork with variable LL corridor | Same |

---

## Demo Level Design

### Layout
```
  [ START ] → approach corridor (5 tiles)
       │
       ├── Fork (divider at x=10)
       │
       ├──── LEFT PATH [SS]: 1-tile corridor → 1 coin → loop pipe
       │     (1 coin delivered in ~1 s)
       │
       └──── RIGHT PATH [LL]: variable-length corridor → 5 coins → loop pipe
             (5 coins delivered after walking delay corridor)

  Five separate courses (one per LL delay condition):
    Course A: LL corridor = 4 tiles  (~3 s)
    Course B: LL corridor = 13 tiles (~10 s)
    Course C: LL corridor = 27 tiles (~20 s)
    Course D: LL corridor = 53 tiles (~40 s)
    Course E: LL corridor = 80 tiles (~60 s)
```

Loop pipes return Mario to the approach corridor after each choice. Each return
= 1 new trial. 20 trials per condition.

### Mechanics Used
- Symmetric fork with hard-block divider
- Short SS corridor with 1 ? coin block
- Variable-length LL corridor (5 courses built) with 5 ? coin blocks clustered
  at the corridor end
- Loop pipes for discrete-trial structure
- Walk speed ≈ 1.33 tiles/s used to calibrate delay-to-tile conversion

### Instructor Script Notes
1. Short LL delay (Course A, ~3 s): "Left = 1 coin fast. Right = 5 coins in 3 seconds.
   I pick right every time — the extra wait is nothing."
2. Medium LL delay (Course C, ~20 s): "Right = 5 coins but I wait 20 seconds.
   Now I sometimes pick left — the delay is starting to matter."
3. Long LL delay (Course E, ~60 s): "5 coins in 60 seconds vs. 1 coin right now.
   I pick left more often. The delayed reward has lost most of its value."
4. Preference-reversal note: "If I were told 'choose 5 coins in 60 s OR 1 coin in 59 s,'
   I'd pick LL — the 1-second advantage isn't worth 4 coins. But 1 coin NOW vs. 5 coins
   in 60 s? Many prefer the 1 coin. That's preference reversal — small time shifts change
   the choice."

---

## Practice / Research Level Design

### Design: Within-subject, 5 delay conditions, counterbalanced
```
Condition A: LL delay ≈ 3 s  — 20 trials
Condition B: LL delay ≈ 10 s — 20 trials
Condition C: LL delay ≈ 20 s — 20 trials
Condition D: LL delay ≈ 40 s — 20 trials
Condition E: LL delay ≈ 60 s — 20 trials
Order counterbalanced (Latin square, 5×5 = 5 orders).
10-minute break between conditions.
```

### Contingency Parameters
| Parameter | SS (Left) | LL (Right) |
|---|---|---|
| Reward amount (coins) | 1 | 5 |
| Path length (tiles) | 1 | 4 / 13 / 27 / 53 / 80 (varies by condition) |
| Delay to reward (s, at 1.33 t/s) | ~1 | 3 / 10 / 20 / 40 / 60 |
| Reward type | Regular coin | 5 regular coins (cluster at end) |
| Trials per condition | 20 | 20 |

### Expected Proportion of LL Choices (hypothetical group mean, k ≈ 0.1)
| Condition | LL Delay (s) | V_LL (A/(1+kD)) | P(LL) predicted |
|---|---|---|---|
| A | 3  | 5/1.3 = 3.85 | >0.95 (strong LL preference) |
| B | 10 | 5/2.0 = 2.50 | ~0.85 |
| C | 20 | 5/3.0 = 1.67 | ~0.60 (near indifference) |
| D | 40 | 5/5.0 = 1.00 | ~0.45 (SS ties LL) |
| E | 60 | 5/7.0 = 0.71 | ~0.25 (strong SS preference) |

### Procedural Notes
- Participant instructions: "You'll see two paths at a fork. Go whichever way you like.
  Try to collect as many coins as you can. You'll return to the fork after each trip
  and make another choice."
- Do NOT describe the delay structure or the amount trade-off explicitly.
- Observer codes: `SS_CHOICE` or `LL_CHOICE` at each fork decision;
  `SS_SR` / `LL_SR` when coin(s) collected; `IMPULSIVE_REVERSAL` if participant
  switches from a longer pattern of LL-choices to SS-choices within a session
  (within-session discount-rate estimation).
- Each condition is a separate course (5 courses uploaded with distinct IDs).

---

## Variables

### Independent Variables
| Variable | Values |
|---|---|
| LL delay (s) | 3, 10, 20, 40, 60 |
| SS amount | 1 coin (fixed) |
| LL amount | 5 coins (fixed) |
| Session order | Counterbalanced (5 orders) |

### Dependent Variables (Companion App Events)
| Event Code | Definition | When to Log |
|---|---|---|
| SS_CHOICE | Chose left (smaller-sooner) path | At fork decision |
| LL_CHOICE | Chose right (larger-later) path | At fork decision |
| SS_SR | 1 coin collected on SS path | On coin contact |
| LL_SR | 5 coins collected on LL path | On final coin contact |
| IMPULSIVE_REVERSAL | Switched from ≥3 consecutive LL to SS within session | At reversal onset |
| WAIT_PAUSE | ≥3 s stationary in LL corridor (hesitation) | At pause onset |
| ABANDON_LL | Started LL path, reversed to loop pipe before collecting coins | At exit without SR |

---

## Analysis Notes

### Discount-Rate Estimation
1. **Per-participant, per-condition**: Compute P(LL choice) = count(LL_CHOICE) / total choices.
2. **Fit hyperbolic function** to P(LL) vs. delay using logistic regression:
   P(LL | D) = 1 / (1 + exp(−(β₀ + β₁ · log(V_LL − V_SS))))
   where V_LL = A_LL / (1 + k·D), V_SS = A_SS (delay ≈ 0).
3. **Extract k** via nonlinear least squares: fit V_LL / V_SS = (A_LL/A_SS)/(1+kD)
   to the choice-proportion data. The indifference point D_50% satisfies:
   A_LL / (1 + k·D_50%) = A_SS → k = (A_LL/A_SS − 1) / D_50%
   With A_LL=5, A_SS=1: **k = 4 / D_50%**.

### Individual Differences
- Compute k per participant.
- Compare to published distributions (e.g., Kirby's Monetary Choice Questionnaire norms).
- Correlate with self-report measures if collected (Barratt Impulsiveness Scale).

### Model Comparison
- Fit hyperbolic: V = A/(1+kD)
- Fit exponential: V = A·exp(−kD)
- Compare AIC/BIC; hyperbolic typically fits better (Mazur, 1987; Myerson & Green, 1995).

### Preference Reversal Test
- If session length permits, present a "distant-pair" condition:
  SS = 1 coin in 30 s, LL = 5 coins in 60 s
- Compare to "near-pair":
  SS = 1 coin in 1 s, LL = 5 coins in 31 s
- Hyperbolic prediction: participant prefers LL in distant-pair, SS in near-pair
  (despite identical 30-s delay difference).
- Exponential prediction: preference should be stable across pair types.

## Observer Notes
- SS_CHOICE and LL_CHOICE are unambiguous (fork direction); target 100% IOA.
- ABANDON_LL captures rare hesitation-and-retreat behavior; useful DV for very long delays.
- WAIT_PAUSE during LL corridor is not a choice reversal — Mario is still on LL path.
  Code separately to avoid confusion.

## Replication Notes
- Course IDs (one per delay condition):
  - Condition A (3 s): XXXX-XXXX-XXXX-XXXX
  - Condition B (10 s): XXXX-XXXX-XXXX-XXXX
  - Condition C (20 s): XXXX-XXXX-XXXX-XXXX
  - Condition D (40 s): XXXX-XXXX-XXXX-XXXX
  - Condition E (60 s): XXXX-XXXX-XXXX-XXXX
- Walk-speed calibration critical: verify Mario covers 10 tiles in ~7.5 s at session start.
  LL corridor tile counts are derived from this calibration (4 tiles ≈ 3 s, etc.).
  If calibration drifts, recompute tile counts before data collection.
- Path length for SS must be exactly 1 tile (trivially short) to preserve "immediate"
  framing. Do not add enemies or obstacles to SS path.
- LL corridor must be a straight, featureless walk (no enemies, no coins along the
  corridor) so that the delay is purely temporal, not effortful.

## Key References
- Mazur, J. E. (1987). An adjusting procedure for studying delayed reinforcement.
  In M. L. Commons, J. E. Mazur, J. A. Nevin, & H. Rachlin (Eds.),
  *Quantitative Analyses of Behavior: Vol. 5. The Effect of Delay and of Intervening
  Events on Reinforcement Value* (pp. 55–73). Erlbaum.
- Rachlin, H., & Green, L. (1972). Commitment, choice, and self-control.
  *Journal of the Experimental Analysis of Behavior, 17*, 15–22.
- Ainslie, G. (1975). Specious reward: A behavioral theory of impulsiveness
  and impulse control. *Psychological Bulletin, 82*, 463–496.
- Kirby, K. N. (1997). Bidding on the future: Evidence against normative discounting
  of delayed rewards. *Journal of Experimental Psychology: General, 126*, 54–70.
- Green, L., & Myerson, J. (2004). A discounting framework for choice with delayed
  and probabilistic rewards. *Psychological Bulletin, 130*, 769–792.
- Madden, G. J., & Bickel, W. K. (Eds.). (2010). *Impulsivity: The Behavioral and
  Neurological Science of Discounting*. American Psychological Association.
- Bickel, W. K., Odum, A. L., & Madden, G. J. (1999). Impulsivity and cigarette
  smoking: Delay discounting in current, never, and ex-smokers.
  *Psychopharmacology, 146*, 447–454.
