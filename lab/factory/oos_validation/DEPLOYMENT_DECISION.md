# DEPLOYMENT DECISION — Walk-Forward OOS Validation

**Date:** 2026-05-03
**Commit chain:** W1-W3 (`1619dcf4` → `ed74bc1a`)
**Decision case:** **CASE 2** (post-Sonnet adjustment) — DEPLOY 2
high-confidence survivors

---

## Decision logic

Per session brief decision tree:

| Case | Trigger | Verdict |
|---|---|---|
| 1 | ≥5 SURVIVORS overlap with backtest READY_TO_SHIP | DEPLOY survivors small |
| **2** | **2-4 SURVIVORS overlap (post-Sonnet: 2)** | **DEPLOY high-confidence survivors only** |
| 3 | 0-1 SURVIVORS or no overlap | DON'T DEPLOY; rebuild approach |
| 4 | All 37 SURVIVORS | INVESTIGATE — likely data leakage |

**Falls in CASE 2.** 2 rules pass tightened SURVIVOR bar
(mean_lift > 8pp, pct_positive > 75%, n >= 10 — Sonnet's
recommendation) AND backtest READY_TO_SHIP.

---

## The 2 rules to ship

### 1. `kill_001` — Bear × Bank × DOWN_TRI = REJECT

| Field | Value |
|---|---|
| Verdict | REJECT |
| Match fields | signal=DOWN_TRI, sector=Bank, regime=Bear |
| Conditions | (none) |
| Sub-regime | (any Bear sub-regime) |
| Walk-forward | -7.1pp mean lift, 80 windows with match, kills losers consistently |
| Backtest | n=11 in April; 0/11 wins (0% WR confirms kill) |
| Already in production | YES (existing kill_001) |
| Calibrated WR (matched signals) | 45% |
| Trade mechanism | trend_fade kill |

### 2. `rule_019_bear_uptri_hot_refinement` — Bear UP_TRI hot = TAKE_FULL

| Field | Value |
|---|---|
| Verdict | TAKE_FULL |
| Match fields | signal=UP_TRI, regime=Bear |
| Conditions | sub_regime == 'hot' |
| Sub-regime constraint | hot |
| Walk-forward | +17.2pp mean lift, 23 windows with match, 78% positive, **n=191 mean** |
| Backtest | n=52 in April, 94% WR (hot Bear sub-regime tailwind) |
| Already in production | NO (new) |
| Calibrated WR | 71% (lifetime hot baseline) |
| Trade mechanism | mean-reversion refined (Bear hot stress capitulation bounce) |

---

## Rules NOT to deploy (despite Lab + backtest READY_TO_SHIP)

Per Sonnet's tightened critique:

| rule | Why not |
|---|---|
| `win_001` (Auto × Bear × UP_TRI) | n=28 borderline; circular production-history validation; redundant with rule_019 hot refinement |
| `win_002` (FMCG × Bear × UP_TRI) | Recent_Δ +2.6pp barely positive; not a survivor by tight bar |
| `win_004` (Metal × Bear × UP_TRI) | n=32 mean; Bear hot tailwind only |
| `win_005` (Pharma × Bear × UP_TRI) | Sector divergence vs rule_029 IT hot indicates "hot sector" framework is unstable |
| `win_007` (Bear BULL_PROXY hot) | n=8 windows = ~480 days = statistical artifact |
| `rule_022_bear_uptri_warm` | WATCH informational; not a TAKE rule |
| `rule_028_bear_uptri_metal_hot` | n=6 windows, sample too narrow |

## Rules to FLAG / RECALL (already in production)

| rule | Action | Reason |
|---|---|---|
| `win_003` (IT × Bear × UP_TRI) | **RECALL or REDUCE CAPITAL** | Already live; recent_Δ -14.1pp; degradation trend |
| `win_005` (Pharma × Bear × UP_TRI) | MONITOR | Sector divergence (vs IT) suggests hot-sector framework collapsing |

---

## Phase 1 deployment specification

### Scope
- **2 new rules** to add to mini_scanner_rules.json:
  - `kill_001` (already exists; fix regime constraint to 'Bear' explicitly)
  - `rule_019_bear_uptri_hot_refinement` (NEW)

### Position sizing
- **25% of normal capital** (per session brief CASE 2)
- For trader at 5% per trade max → 1.25% per Phase 1 signal initially
- Scale to full 5% only after kill-switch criteria satisfied

### Kill-switch thresholds (per-rule)

| Trigger | Action |
|---|---|
| Per-rule WR < 50% over rolling 20 signals | HALT that rule |
| Per-rule WR < 60% over rolling 30 signals | REDUCE to 12.5% capital |
| Aggregate Phase 1 WR < 55% over rolling 30 signals | PAUSE Phase 1 entirely |
| Drawdown from Phase 1 start > 10% | PAUSE Phase 1; review |
| Bear regime exits + Bull/Choppy persists 30+ days | PAUSE rule_019 (sub-regime gated) |

### Evaluation window
- **60 days live** before any expansion decision
- Daily WR tracking + weekly review
- 60-day evaluation gate:
  - Aggregate WR ≥ 65% AND drawdown < 8%: scale to 50% capital
  - Aggregate WR 55-65%: hold at 25% for another 60 days
  - Aggregate WR < 55%: STOP Phase 1; revisit per session brief
    CASE 3 instructions (rebuild approach)

### Pre-deployment checklist

- [ ] Update `mini_scanner_rules.json`: add rule_019; fix kill_001
      regime constraint to 'Bear' explicitly
- [ ] Verify scanner can compute `sub_regime` field on per-signal basis
      (Bear hot detector already in `lab/factory/bear/subregime/detector.py`;
      port to production scanner)
- [ ] Add Telegram messaging for matched rule + calibrated WR
- [ ] Add daily WR tracking dashboard (kill-switch monitoring)
- [ ] Add Phase 1 experimental labeling visible to trader
- [ ] 7-day shadow mode before live capital
- [ ] Define **specific** stop criteria the trader will act on (not
      just numbers that sound rigorous — Sonnet's PB4 caution)

---

## What this validates / refutes

### Validates
- **Lab's mechanistic finding** (Bear UP_TRI hot sub-regime is real
  edge): rule_019's +17.2pp lift across 23 windows with n=191 mean is
  the broadest-sample evidence in the entire Lab pipeline.
- **Existing kill_001**: confirmed across 80 windows of 15-yr lifetime.
- **Sub-regime gating concept**: rule_019 outperforms because of hot
  sub-regime gate, not despite it.

### Refutes
- **Lab's "8 READY_TO_SHIP" claim**: walk-forward validates 3, of which
  Sonnet drops 1 → 2 final survivors. **62% false-positive rate** in
  Lab's backtest.
- **"Hot sector" framework**: rule_029 (Pharma) and rule_031 (IT) show
  opposite recent trends → sector boost rules are not stable edge.
- **Lab's Bull cells**: rule_010/011/012/023 all show negative or
  flat lift in walk-forward; either insufficient data or genuine
  refutation of Bull approach.
- **Calendar-conditional rules** (rule_017 wk3, rule_018 wk4, etc.):
  most have insufficient sample even across 15 years; not deployable.

### Open questions
- **Bull rules**: cannot validate without Bull-regime-only walk-forward;
  rerun with regime filter as future work.
- **rule_022 warm Bear**: WATCH classification; not a TAKE rule but
  could add color in Telegram messaging.
- **Recent decay** in win_007 / rule_029 / win_003: regime drift signal
  to monitor in production.

---

## Honest framing (from Sonnet)

> "Walk-forward didn't validate Lab's work; it **debugged** it.
> 37 rules tested, 15 years of data, 2 clean survivors. That's
> humbling but honest. Deploying all 8 of Lab's READY_TO_SHIP rules
> would be repeating Lab's over-fit mistake with walk-forward
> lipstick on. Accept the 2-rule outcome."

The 5 weeks of Lab work + $25.12 in AI spend produced:
- 2 production-ready rules with strong walk-forward validation
- 35 hypotheses for future investigation when more data accumulates
- A reusable methodology (regime sub-regime detection, lifetime
  calibration, dual-Opus prompting comparison)
- Empirical confirmation of Opus's "circular validation" diagnosis

That's the real deliverable. Not 37 rules.

---

## POST-W4 SONNET CRITIQUE ADJUSTMENTS

Sonnet 4.5 final review (full critique: `_w4_critique.md`). Verdict:
**DEPLOY with 6 modifications.** Without modifications, premature.

### Probability assessment (Sonnet)

| Outcome | P | 60-day return |
|---|---|---|
| Success | 25% | +5% to +8% |
| Modest win | 15% | +1% to +3% |
| Breakeven | 30% | -1% to +1% |
| Modest loss | 20% | -2% to -5% |
| Disaster | 10% | -8% or worse |

**Base case: 40% meaningful positive return (>+3% over 60 days)**,
assuming the 6 mitigations below are applied.

### 6 mitigations Sonnet mandates pre-deployment

1. **Add regime confirmation lag.** Only fire rule_019 if regime has
   been Bear for ≥5 consecutive days. Prevents transition-day misfires
   when sub_regime classifier lags real market dynamics.

2. **Add vol decay check.** sub_regime="hot" AND vol_percentile
   declining over last 3 days. Confirms bounce phase, not initial
   panic.

3. **Run 30-day scanner simulation** on 2025 data with production
   code. Verify sub_regime labels match walk-forward assumptions —
   otherwise scanner implementation bugs invisibly invalidate
   walk-forward conclusions.

4. **Revise kill-switches** (current ones noise-prone; Wilson math):
   - Per-rule: WR < 40% over 30 signals (was: <50% over 20)
   - Aggregate Phase 1: WR < 50% over 50 signals (was: <55% over 30)
   - Drawdown 10% threshold KEPT (capital-preservation, not statistical)
   - DROP "12.5% middle tier" — useless mid-stream cuts; instead at
     30 signals if WR 40-55%, EXTEND eval another 30 signals at
     same 25% size

5. **Recall win_003 NOW** (currently in production at full sizing).
   Reduce to 1% sizing, flag "under review" for 30 days. Walk-forward
   shows -14pp recent decay; expensive to confirm with 5 more signals
   at full size when degradation evidence is already structural.

6. **Behavioral friction beyond text labels.** Sonnet: "[PHASE 1
   EXPERIMENTAL] becomes invisible after 2 weeks (smoking-warning
   habituation effect)." Stronger options:
   - Separate Telegram channel for Phase 1 signals
   - Manual confirmation per Phase 1 trade (`/confirm_019_SYMBOL`)
   - Daily aggregate summary at market open (keeps eval frame salient)
   - PWA color-coding (amber/orange for Phase 1)

### Reframe 60-day evaluation gate

Sonnet: "60 days produces only 20-30 total signals. Cannot distinguish
71% rule from 55% rule with confidence. Reframe as 'disaster check +
early warning' not 'validation.'"

**Adjusted gate:**
- 60 days = disaster check (no catastrophic loss; rules fire as expected)
- 90 days / 50 signals = true validation gate
- Scaling decision moves to 90-day mark, not 60

### Comparative deployment options (Sonnet's framing)

| Option | P(meaningful win) |
|---|---|
| Full 8-rule Lab "READY_TO_SHIP" | 20% |
| Opus 5-rule recommendation | 35% |
| **2-rule Phase 1 (this plan WITH 6 mitigations)** | **40%** |
| Discretionary (no rules) | 50% |
| No deployment (continue paused) | 0% |

**The 2-rule Phase 1 is second-best after discretionary, but the only
option that produces durable learning** (validated kill-switches +
regime framework tested in production).

---

## Final verdict

**DEPLOY rule_019 + kill_001 with the 6 mitigations applied.**

Without mitigations: premature, 25% success probability.
With mitigations: defensible 40% chance at building durable edge.

The 6 mitigations are mostly engineering (lag/decay checks, scanner
simulation, kill-switch revisions). Behavioral friction is the
trickiest — easy to specify, hard to maintain over weeks.

**Trader's morning action** (per Opus deep dive FINAL_SYNTHESIS):
write 1-page Deployment Contract specifying exactly these 2 rules,
the mitigations, the kill-switch thresholds, and the 90-day evaluation
gate. If contract can't be written in 30 minutes, step away from
quantitative trading 90 days.
