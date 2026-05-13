# 05 — Validation Methodology

This is the load-bearing section. The new classifier ships only after all six validations pass. Any single FAIL = redesign or reject.

## Validation 1 — Cohort Preservation Test (mandatory, gating)

### Setup
1. Pull Nifty daily OHLCV for 2024-01-01 → 2026-05-13 from yfinance.
2. Compute v2 features (F1-F9) for every trading day in window.
3. Run v2 classifier per `04_decision_logic.md`. Output: a regime label per trading day.
4. Reload `output/signal_history.json` and re-tag each of the 281 resolved signals with v2 regime (based on signal's `date` field).
5. Re-compute cohort stats per signal type × v2 regime.

### Pass criteria (all 5 must hold)

| # | Criterion | Threshold |
|---|---|---|
| C1 | Original UP_TRI×Bear signals (n=96) that remain in some Bear-family state (Bear OR Bear-Recovery) | **≥ 80%** (≥ 77 of 96) |
| C2 | WR of (UP_TRI ∩ Bear-family) under v2 | **≥ 85%** (≤ 10pp drop from 94.7%) |
| C3 | Signals that moved OUT of Bear-family have a documented regime-transition explanation (i.e., they fell in the last 2-3 days of a Bear regime as it transitioned) | qualitative: at least 80% of out-movers should land in Bear-Recovery, not Bull or Choppy |
| C4 | New cohort UP_TRI × Bull-Recovery — record WR + n. Pass if either (a) n < 5 (no false attribution) or (b) WR > 60% (legitimate new cohort) | qualitative |
| C5 | Total signals preserved (every resolved signal has exactly one v2 regime label assigned) | **100%** (no NaN regimes) |

### Pass interpretation

- If C1, C2, C3 pass → v2 classifier preserves the validated edge. PROCEED.
- If C4 surfaces a new positive cohort → bonus (v2 not only preserves edge, it surfaces new edge).
- If any of C1-C3, C5 fail → FAIL. Either:
  - Loosen Bear gate thresholds in `04_decision_logic.md` and retry (up to 5 iterations)
  - OR reject v2 and re-design state space

### Implementation
Single Python script. Reads `signal_history.json` + `yfinance` Nifty. ~3 hours to write.

---

## Validation 2 — Visual Sanity Check (mandatory, gating)

### Setup
Plot last 60 trading days of Nifty close with v2 regime label overlay (colored bands by regime).

### Pass criteria (subjective, requires operator review)
1. Operator inspects chart for 10 minutes.
2. Operator confirms each regime band aligns with visual market state.
3. Operator can articulate (one sentence per transition) why each transition occurred.

### Pass interpretation
- If operator says "this matches what I see" → PASS.
- If operator says "this regime fires too often/rarely" or "this transition is in the wrong place" → tune thresholds + re-plot.

### Implementation
~2 hours: matplotlib chart with shaded regime regions. Save as PNG in `doc/regime_v2_design/sanity_plot.png` for review.

### Why this matters
A classifier that passes statistical tests but produces visually-nonsensical regime maps will lose operator trust within a week. The visual test is the smell test.

---

## Validation 3 — Transition Reasonableness (mandatory, gating)

### Setup
Count v2 regime transitions in the last 12 months (Nifty 2025-05-01 to 2026-05-01).

Identify **known inflection points** (events where Nifty moved >5% in 5 days, or visually-obvious trend changes). For each inflection, check whether v2 emitted a regime transition within ±5 trading days.

### Pass criteria

| # | Criterion | Threshold |
|---|---|---|
| T1 | Total regime transitions over 12 months | **≥ 6 AND ≤ 20** (sanity: not too few, not too many) |
| T2 | Known inflection points captured | **≥ 75%** within ±5 trading days |
| T3 | False transitions (transitions that immediately reverse within 5 days) | **≤ 20%** of total transitions |

### Pass interpretation
- T1 too low → classifier is too sticky; loosen persistence rules or threshold gates
- T1 too high → too noisy; tighten persistence rules
- T2 < 75% → classifier misses real regime changes; redesign or add features
- T3 > 20% → whipsaw; tighten persistence rules

### Implementation
~3 hours: script that lists transitions + cross-references against a hand-curated list of known events (provided in `doc/regime_v2_design/known_inflections.md`, to be authored during this phase).

---

## Validation 4 — Side-by-Side Shadow Run (mandatory, gating)

### Setup
Run v2 classifier in parallel with v1 (current `get_nifty_info()`) for **2 weeks minimum** (10 trading days).

Both labels are logged to `output/regime_features.json` (v2) and the existing `regime_debug.json` (v1).

Production consumers (brain, bridge, mini_scanner_rules) **continue to read v1**. v2 is logged-only during this window.

### Daily comparison
Each day, log:
- v1 label
- v2 label
- agreement flag
- which classifier is "more right" (operator's hindsight judgment)

### Pass criteria

| # | Criterion | Threshold |
|---|---|---|
| S1 | Agreement rate (days both classifiers emit the same label) | Inform, not gate; expect 50-80% given new states |
| S2 | Cases where v2 catches a regime transition v1 misses | ≥ 1 documented case (proves v2 adds value) |
| S3 | Cases where v1 catches a transition v2 misses | should be ZERO (proves v2 doesn't lose information) |
| S4 | Days where v2 emits a clearly-wrong label | ≤ 1 in 10 trading days |

### Pass interpretation
- S2 ≥ 1 + S3 = 0 + S4 ≤ 1 → PASS. v2 strictly dominates v1.
- S3 ≥ 1 → FAIL. v2 has missed a transition v1 caught — redesign.
- S4 > 1 → FAIL. v2 is producing nonsense too often.

### Implementation
- Day 0: deploy v2 classifier as a parallel writer (does not affect production). ~4 hours.
- Days 1-10: daily 10-minute operator review of the two labels.
- Day 11: tally results, PASS/FAIL decision.

### Why 2 weeks
- Too short (3-5 days): unlikely to span a regime transition.
- Too long (4+ weeks): operator loses interest; window stretches.
- 2 weeks (10 trading days): covers one regime transition probabilistically; manageable operator attention.

---

## Validation 5 — Cohort-Wise Predictive Power (mandatory, gating)

### Setup
For each (signal_type × v2_regime) cohort, compute on resolved signals:
- n (sample size)
- WR
- avg_pnl_pct
- WR variance (= standard error of WR estimate)

Compare against (signal_type × v1_regime) cohort stats.

### Pass criteria

| # | Criterion | Description |
|---|---|---|
| P1 | New classifier creates LOWER intra-cohort variance than v1 | v2 cohorts should be tighter clusters of similar-WR signals |
| P2 | Preserves all currently-known winners | UP_TRI×Bear (94.7%), BULL_PROXY×Bear (87.5%), UP_TRI×Metal (88.2%) survive as recognizable cohorts |
| P3 | Identifies at least one new candidate positive-edge cohort | e.g., UP_TRI × Bull-Recovery WR > 60% with n ≥ 10 |
| P4 | DOWN_TRI structural failure preserved | DOWN_TRI in any v2 regime should still show losing aggregate (no false signal that DOWN_TRI is fixable by relabeling) |

### Pass interpretation
P1, P2, P4 are gating. P3 is bonus (nice-to-have, not required).

### Implementation
~2 hours: re-aggregation script that runs after Validation 1.

---

## Validation 6 — Rollback Trigger Definition

This is the **PASS/FAIL committee** spec. Before v2 ships, the team commits to these specific failure modes.

### Hard rollback triggers (v2 is REJECTED, return to v1)

| # | Trigger | Detection method |
|---|---|---|
| R1 | Validation 1 fails (Bear-family preservation < 80%) | Cohort preservation script output |
| R2 | Validation 3 fails T2 (< 75% of inflections caught) | Transition reasonableness script |
| R3 | Validation 4 fails S3 (v2 missed transition v1 caught) | Operator-observed in shadow window |
| R4 | Validation 4 fails S4 (v2 emits nonsense > 1 in 10 days) | Operator-observed |
| R5 | Validation 5 fails P2 (proven winners not preserved) | Cohort re-aggregation script |

### Soft rollback triggers (v2 redeployed after threshold tuning)

| # | Trigger | Tune what |
|---|---|---|
| R6 | Validation 1 partial fail (preservation 70-80%) | Loosen Bear gate slope threshold; retest |
| R7 | Validation 3 T1 too few transitions (< 6 in 12mo) | Loosen persistence rules |
| R8 | Validation 3 T1 too many (> 20 in 12mo) | Tighten persistence; add whipsaw guards |

### Pre-deployment commitment

Before promoting v2 to authoritative (changing brain/bridge/mini_scanner to read `regime_features.json`), the team writes a signed memo:

> "Validation 1-5 ran on [date]. Results: [PASS/FAIL per validation]. Decision: PROMOTE / RETUNE / REJECT. Threshold values used: [list]. If retune: [parameter changes]. Operator signature."

This memo lives at `doc/regime_v2_design/promotion_decision_<date>.md`. Without this memo, v2 stays in shadow indefinitely.

---

## Total validation effort

| Validation | Effort |
|---|---|
| V1 Cohort Preservation | 3h script + 1h analysis = **4h** |
| V2 Visual Sanity | 2h script + 0.5h review = **2.5h** |
| V3 Transition Reasonableness | 3h script + 2h hand-curated inflections + 1h analysis = **6h** |
| V4 Side-by-Side Shadow Run (2 weeks) | 4h deploy + 0h daily monitoring + 2h tally = **6h elapsed** + 10 days |
| V5 Cohort-Wise Predictive Power | 2h script + 1h analysis = **3h** |
| V6 Rollback Trigger Memo | 1h | 
| **Total** | **~23h of work** + 10-day shadow window |

## When v2 ships (the promotion criterion)

All five validations pass AND the promotion memo is signed. Specifically:
- V1: Bear-family preservation ≥ 80%, WR ≥ 85%
- V2: operator approves visual chart
- V3: 6-20 transitions in 12mo, 75%+ inflections caught, ≤ 20% false transitions
- V4: v2 ≥ v1 over 10 trading days; no missed transitions; ≤ 1 nonsense day
- V5: all known winners preserved (P2)
- V6: memo signed

Then and only then: flip brain_derive._derive_regime_watch() to read `regime_features.json` instead of `weekly_intelligence_latest.json`. v1 continues writing in parallel for one more month as belt-and-suspenders.

## What we will NOT do during validation

- No academic statistical tests beyond what's specified (chi-squared etc. add nothing to the rollback decision; the cohort-preservation + visual + operator-shadow stack is sufficient).
- No backtest of trading P&L with v2 labels (this is a regime classifier validation, not a strategy backtest; if cohort preservation holds, P&L preservation follows mechanically).
- No comparison against external services (TradingView regime indicators, third-party classifiers). Out of scope.
