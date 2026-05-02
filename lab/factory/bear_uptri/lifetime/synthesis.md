# Bear UP_TRI — Lifetime Validation Synthesis (Session 2)

**Date:** 2026-05-02 (continued)
**Branch:** `backtest-lab`
**Scope:** 15,151 W/L/F Bear UP_TRI signals over 15-yr backtest (2011-2026)
**Method:** L1 cell-validation + L2 comprehensive combinatorial search

This document consolidates Session 2 lifetime findings and replaces the
"broad-band edge" framing from Session 1's playbook v1 with a more
nuanced sub-regime-aware production posture.

---

## Headline findings

1. **Live-vs-lifetime gap +38.9pp confirmed.** Live 94.6% / lifetime 55.7%.
   Largest gap in Lab. Mostly explained by **Phase 5 selection bias** (the
   74 live signals were Phase-5 winners) plus an "extra hot within hot"
   April 2026 sub-regime; only ~15pp explained by sub-regime structure.

2. **Bear is BIMODAL, not tri-modal** (different from Choppy):
   - stress sub-regime: 43% of lifetime, mixed WR by breadth
   - balance sub-regime: 34% of lifetime
   - quiet sub-regime: 1% — essentially absent (quiet markets don't
     produce Bear setups)

3. **Hot sub-regime structurally lifts +14.9pp** but lifetime hot is
   only 68.3% WR, not 94.6%:
   - Hot (nifty_60d=low × nifty_vol=High): n=2,275 (15%), 68.3% WR
   - Cold (everything else): n=12,876 (85%), 53.4% WR

4. **Session 1's "no filter" finding is sub-regime-specific.** In current
   hot sub-regime, signals are broad-band (94.6% across all features). At
   lifetime scale, multiple filter families improve baseline by +6-8pp:
   - `wk4 × swing_high=low`: 63.3% WR, n=3,845, +7.6pp
   - `breadth=low × ema50_slope=low × swing_high=low`: 61.8% WR, n=4,555, +6.2pp

5. **B2 anti-features all REFUTED at lifetime.** Same Choppy-V2 lesson:
   - `wk4` was Phase 4 selection artifact; lifetime shows wk4 is +10.5pp
     WINNER (not anti)
   - `ema_alignment=bear` similarly inverted (+3.9pp)
   - `nifty_vol_regime=Medium` only weak negative (-2.1pp)

6. **WATCH patterns are GENUINELY weaker** (refutes Session 1 prediction).
   Lifetime test_wr: VALIDATED 72.1% / PRELIMINARY 66.4% / WATCH 65.0%.
   The Δ +7.1pp confirms VALIDATED patterns have real structural edge,
   not just live observation.

---

## L1 — Cell findings validation

### F1 (`nifty_60d_return_pct=low`) at lifetime

| Cohort | n | WR | Lift over baseline |
|---|---|---|---|
| Live (April 2026) | 32 | 93.8% | (baseline already 94.6%) |
| Lifetime | 2,436 | 67.4% | **+11.8pp over 55.7%** |

F1 is **CONFIRMED at lifetime** as a modest filter. It is NOT a
high-precision lifetime filter (67.4% << 90%) but it does provide real
discrimination: matched +11.8pp over baseline; skipped subset 53.4% WR.

### Top 5 winner features at lifetime

| Feature / level | Δ presence−absence | Verdict |
|---|---|---|
| `swing_high_count_20d=low` | **+23.3pp** | **CONFIRMED** (strongest lifetime lift) |
| `nifty_60d_return_pct=low` | +14.1pp | CONFIRMED |
| `inside_bar_flag=True` | +4.9pp | WEAK |
| `multi_tf_alignment_score=low` | +3.9pp | WEAK |
| `consolidation_quality=none` | +1.1pp | NEUTRAL |

**Ranking inversion:** B2 ranked `nifty_60d_return_pct=low` as the
strongest winner (+52pp differentiator vs WATCH). At lifetime,
`swing_high_count_20d=low` is the stronger lifetime feature (+23.3pp
presence vs absence). The B2 ranking was distorted by the 0-REJECTED
group; lifetime data is the more reliable signal.

### Top 5 anti-features at lifetime — MOSTLY REFUTED

| Feature / level | Δ presence−absence | Verdict |
|---|---|---|
| `day_of_month_bucket=wk4` | +10.5pp | **REFUTED — INVERTED** |
| `nifty_vol_regime=Medium` | −2.1pp | WEAK (only one with right direction) |
| `ema_alignment=bear` | +3.9pp | **REFUTED — INVERTED** |
| `ROC_10=medium` | +1.2pp | NEUTRAL |
| `consolidation_quality=loose` | −1.0pp | NEUTRAL |

**Key lesson (re-confirmed from Choppy V2):** Anti-features identified
in patterns-vs-patterns differential (B2) need lifetime cross-validation
before deployment. `wk4=0% in winners` was a Phase 4 selection artifact
(analyzer's combinatorial search excluded wk4 entries); at lifetime,
wk4 is actually a +10.5pp winner. Production should NOT use any of
these anti-features as SKIP rules.

### WATCH patterns — genuinely weaker (predicted under-observed; refuted)

| Group | Lifetime test_wr |
|---|---|
| VALIDATED | 72.1% |
| PRELIMINARY | 66.4% |
| WATCH | **65.0%** |

VALIDATED minus WATCH = +7.1pp lifetime test_wr. The 405 WATCH patterns
are not just under-observed in live data — they have measurably lower
backtest performance than the 87 winners. This suggests Phase 5's
discrimination is real even within the 100% validation cohort.

---

## L2 — Comprehensive lifetime search

### Top family: `day_of_month_bucket=wk4` × X

7 of top 15 lifetime combinations anchor on wk4. The strongest:

| Filter | n | WR | Lift |
|---|---|---|---|
| `wk4 AND swing_high_count_20d=low` | 3,845 | 63.3% | +7.6pp |
| `wk4 AND compression_duration=low` | 3,849 | 63.2% | +7.6pp |
| `wk4 AND swing_low_count_20d=low` | 3,802 | 63.1% | +7.4pp |

Mechanism (per Sonnet 4.5): month-end institutional rebalancing creates
better UP_TRI reversal opportunities regardless of vol/breadth state.

### Alternative family: `breadth=low × ema50_slope=low`

| Filter | n | WR | Lift |
|---|---|---|---|
| `breadth=low AND ema50_slope=low AND swing_high=low` | 4,555 | 61.8% | +6.2pp |
| `breadth=low AND ema50_slope=low` | 4,559 | 61.8% | +6.1pp |

Captures "Bear conditions lite" — broader gate than wk4.

### Hot sub-regime markers (≥85% lifetime WR)

8 markers found, all with small samples (n=102-122). Common features:
`market_breadth_pct=high` OR `day_of_month_bucket=wk2` OR
`nifty_vol_regime=Low`.

**Critical**: NONE of the hot markers match live April 2026's
characteristics (`nifty_60d=low × nifty_vol=High`). The lifetime "hot"
markers are different sub-regimes than the live "hot" condition.

This means **Live's 94.6% is NOT reproducible** by any 2-3 feature
combination at lifetime scale. The 94.6% is genuinely a Phase-5
selection bias artifact — even within the structurally-favorable sub-
regime that current data sits in, individual signal quality varied
historically and produced lifetime hot of only 68.3%.

---

## Bear regime structural model (per Sonnet 4.5 + L1+L2 evidence)

### Bimodal Bear

```
STRESS BEAR (43%) ────┐
                      ├── Hot sub-regime
                      │     - vol_percentile > 0.70
                      │     - 60d_return < -0.10
                      │     - low/medium breadth
                      │     - low swing complexity
                      │     - lifetime WR: 68.3%
                      │     - mechanism: late-stage capitulation
                      └── stress__low_breadth: 60.0% (largest, n=5247)
                          stress__med_breadth: 50.7% (HOSTILE)

BALANCE BEAR (34%) ───┐
                      ├── Cold sub-regime
                      │     - vol_percentile 0.30-0.70
                      │     - lifetime WR: ~54%
                      │     - mechanism: noisy mid-Bear
                      ├── balance__low_breadth: 54.6%
                      └── balance__med_breadth: 53.9%

QUIET BEAR (1%) ──────── Essentially absent
                          (quiet markets don't generate Bear setups)
```

### Sub-regime transitions and expected behavior

| Current state | Expected WR | Action |
|---|---|---|
| Hot Bear (vol high + return low) | 65-95% (live-like) | TAKE_FULL |
| Stress + breadth med (hostile) | ~50% | filter required (e.g., wk4) |
| Balance Bear | ~54% | filter required |
| Cold + recovering | 50-53% | likely Choppy/Bull misclassified — SKIP |

When current data exits hot:
- Vol drops to Medium/Low → expect 54-56% WR
- 60d return improves to medium/high → expect 50-53% (false Bear labels)
- Both degrade → 50-52% (coin flip; Bear regime ending)

---

## Production posture (revised, v1.1)

### Current sub-regime: "hot Bear" (April 2026 100% in hot)

| Condition | Action | Sizing |
|---|---|---|
| Bear UP_TRI signal in hot sub-regime | TAKE_FULL | full (94.6% live, 68.3% lifetime hot) |
| Bear UP_TRI signal + repeat name within 6 days | TAKE_SMALL | half (S3 finding) |
| Bear UP_TRI signal + 3+ same-day signals | 80% sizing | day-correlation cap |

### When sub-regime exits hot (deployment-ready filter cascade)

| Condition | Action | Sizing |
|---|---|---|
| Bear UP_TRI + `wk4 AND swing_high=low` | TAKE_FULL | full (lifetime 63.3%, +7.6pp) |
| Bear UP_TRI + `breadth=low AND ema50_slope=low AND swing_high=low` | TAKE_SMALL | half (lifetime 61.8%, +6.2pp) |
| Bear UP_TRI + only `wk4` | TAKE_SMALL | half (lifetime ~63%) |
| Bear UP_TRI without any filter match | SKIP | edge collapses to ~52% |

### Sub-regime detection (production gating)

Production scanner needs to detect when current state exits hot. Per T1
detector + L1 thresholds:

```python
def is_hot_bear(nifty_vol_percentile_20d, nifty_60d_return_pct):
    return (nifty_vol_percentile_20d > 0.70
            and nifty_60d_return_pct < -0.10)

def bear_uptri_action(signal):
    if is_hot_bear(...):
        return "TAKE_FULL"  # Session 1 broad-band finding holds
    # Cold sub-regime: filter cascade
    if matches(signal, "wk4 AND swing_high=low"):
        return "TAKE_FULL"
    if matches(signal, "breadth=low AND ema50_slope=low AND swing_high=low"):
        return "TAKE_SMALL"
    if matches(signal, "wk4"):
        return "TAKE_SMALL"
    return "SKIP"
```

---

## Confidence delta (Session 1 → Session 2)

| Finding | S1 confidence | S2 confidence |
|---|---|---|
| Bear UP_TRI 94.6% live edge | HIGH (current sub-regime) | HIGH (current sub-regime) |
| Bear UP_TRI 94.6% as universal Bear | LOW | **REFUTED** (lifetime 55.7%) |
| F1 (nifty_60d=low) is filter anchor | UNCLEAR | **CONFIRMED at lifetime** (+11.8pp) |
| wk4 is anti-feature | flagged as April-2026-specific | **REFUTED — wk4 is winner anchor** |
| Hot sub-regime exists | hypothesized | CONFIRMED (+14.9pp lift, 15% of lifetime) |
| Bear is multi-modal | hypothesized | CONFIRMED bimodal (not tri-modal like Choppy) |
| WATCH patterns under-observed | predicted | **REFUTED** — genuinely weaker |
| Filter required for production | not surfaced | NEW — required when sub-regime exits hot |

---

## Open questions for Session 3

1. **Sector × sub-regime stratification**: which sectors work best in hot
   sub-regime vs cold? L1 surfaced sector ranges (Health 48.6% → CapGoods
   59.6%) but didn't cross with sub-regime.

2. **Year-on-year sub-regime distribution**: 2021 was hostile (25.3% WR).
   Was that a year of mostly cold sub-regime, or did the hot sub-regime
   itself fail in 2021?

3. **Bear sub-regime detector**: Choppy used vol_percentile × breadth.
   Bear may need vol_percentile × 60d_return (the L1 hot definition) as
   primary axes. Build dedicated detector module in Session 3.

4. **Live data coverage of cold sub-regime**: 0 live signals in cold
   right now. The cold filter cascade hasn't been live-validated. Need
   quarterly Phase-5 re-runs once cold-regime live signals appear.

5. **Cross-cell synthesis**: how does Bear UP_TRI's hot/cold split
   compare to Choppy's stress/balance/quiet? Are these the same axes
   manifesting differently per regime, or fundamentally different
   structures?

---

## Session 2 file outputs

| File | Generated by | Purpose |
|---|---|---|
| `lifetime/extract.py` + `data_summary.json` | L1a | Lifetime segmentation |
| `lifetime/cell_validation.py` + `cell_validation.json` | L1b | S1 findings tested at scale |
| `lifetime/comprehensive_search.py` + `comprehensive_combinations_top20.json` + `.parquet` | L2 | 2-feat + 3-feat search |
| `lifetime/sub_regime_llm_analysis.md` | L2 | Sonnet 4.5 sub-regime interpretation |
| `lifetime/synthesis.md` | L3 (this) | L1+L2 consolidation + revised production posture |
| `playbook.md` v1.1 | L3 | Production-facing update |

---

## Update Log

- **v1 (2026-05-02 night, Session 2):** Initial Session 2 synthesis.
  Bear is bimodal (not tri-modal). Hot sub-regime structurally lifts
  +14.9pp (15% of lifetime). Live's 94.6% is mostly Phase-5 selection
  bias on top of hot sub-regime. wk4 anti-feature REFUTED — actually
  the strongest lifetime winner anchor. Filter cascade designed for
  cold sub-regime (when current state exits hot). Production posture
  revised v1.1.
