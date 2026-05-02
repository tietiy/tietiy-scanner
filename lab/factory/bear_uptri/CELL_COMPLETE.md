# Bear UP_TRI Cell — COMPLETE

**Status:** ✅ COMPLETE across 3 sessions (5-step methodology)
**Date completed:** 2026-05-02 night
**Branch:** `backtest-lab`
**Commits:** 12 atomic commits across Sessions 1-3

This document is the cross-session summary of the Bear UP_TRI cell
investigation. It captures methodology, headline findings, architectural
insights, and reference material for future Bear cells (DOWN_TRI,
BULL_PROXY) and future regime work (Bull).

---

## Cell scope and outcome

| Metric | Value |
|---|---|
| Cell signal × regime | UP_TRI × Bear |
| Live signals | 74 (April 2026) |
| Live W/L/F | 70 / 4 / 0 |
| Live baseline WR | **94.6%** |
| Lifetime signals | 15,151 |
| Lifetime baseline WR | **55.7%** |
| Live-vs-lifetime gap | **+38.9pp** (largest in Lab) |
| Phase 5 validation rate | 100% (87/87 evaluable) |
| Sub-regime structure | TRI-modal: hot / warm / cold |
| Confidence (lifetime-validated) | HIGH (sub-regime gated) |
| Production posture | TAKE_FULL in hot/warm; cold cascade |

---

## Methodology applied

The validated 5-step factory methodology:

| Step | What | Sessions |
|---|---|---|
| 1. Live cell investigation | extract / differentiators / filter_test / playbook v1 | Session 1 (B1-B4) |
| 2. Lifetime validation | cell_validation against 15k signals | Session 2 (L1) |
| 3. Comprehensive lifetime search | 2-feat + 3-feat combinatorial; identify dominant patterns | Session 2 (L2) |
| 4. Stratification | sector × calendar × sub-regime | Session 3 (S1) |
| 5. Synthesis + sub-regime gating | detector + production posture | Session 3 (S2-S3) |

This cell is the **reference template** for Bear DOWN_TRI and Bear
BULL_PROXY cells. Apply the same 5-step pipeline; expect different
findings but similar architectural patterns (sub-regime structure,
calendar effects, sector mismatch rules).

---

## Findings hierarchy

### Architectural insights (top-level — apply to all future cells)

1. **Per-regime sub-regime structure exists.** Bear is tri-modal
   (hot/warm/cold); Choppy is tri-modal (quiet/balance/stress) but with
   different axes. Future Bull cells should expect 2-3 sub-regimes.

2. **Vol_percentile is a candidate universal primary axis** but may be
   a confound for non-Choppy regimes. Sonnet 4.5 critique recommends
   testing regime-native primaries first (Bear: drawdown depth; Bull:
   trend persistence).

3. **Secondary axis is regime-specific.** Choppy uses cross-sectional
   breadth; Bear uses longitudinal 60d_return; Bull predicted to use
   leadership concentration. These may be alternative coordinates over
   a shared "regime commitment" factor.

4. **Live-vs-lifetime gaps are decomposable.** Bear UP_TRI's +38.9pp
   gap = +12.6pp sub-regime + +26.3pp Phase-5 selection bias. Future
   cells should report this decomposition explicitly.

5. **Anti-features identified in patterns-vs-patterns must be
   lifetime-cross-validated.** Both Choppy V2 and Bear S2 found that
   patterns-derived anti-features INVERT at lifetime scale (`wk4` was
   labeled anti, lifetime is +10.5pp winner). Production must NOT use
   patterns-derived anti-features as SKIP rules without lifetime check.

6. **Phase-5 hierarchy override.** Sub-regime detectors provide
   unconditional base-rate predictions; Phase-5 validation is a
   downstream conditional filter. Don't bake Phase-5 logic into
   detector — keep detector outputs as priors that Phase logic updates.

### Cell-specific findings (apply to Bear UP_TRI production only)

#### Sub-regime structure

| Sub-regime | Definition | Lifetime % | Lifetime WR |
|---|---|---|---|
| hot | vol > 0.70 AND 60d < −0.10 | 15% | 68.3% |
| warm | vol > 0.70 AND −0.10 ≤ 60d < 0 (NEW per S2) | TBD | live 95.2% on n=42 |
| cold | vol ≤ 0.70 OR 60d ≥ 0 | 85% (incl. warm) | 53.4% |

Mechanism (per Sonnet 4.5):
- **hot** = late-stage capitulation, high vol + deep decline → buy-the-crash edge
- **warm** = volatile bottoming, high vol + shallow decline → pattern-quality edge
- **cold** = grinding decay, low vol + slow bleed → trend-following edge

#### Top winner features (lifetime, ranked by delta)

| Feature / level | Δ presence−absence | Confidence |
|---|---|---|
| `swing_high_count_20d=low` | +23.3pp | HIGH (largest lifetime lift) |
| `nifty_60d_return_pct=low` | +14.1pp | HIGH (regime anchor; F1 filter) |
| `inside_bar_flag=True` | +4.9pp | WEAK |
| `multi_tf_alignment_score` (within hot) | +9.5pp | MEDIUM (S1 within-hot finding) |
| `range_compression_60d` (within hot) | +9.3pp | MEDIUM (S1 within-hot finding) |

#### Refuted anti-features (B2 patterns-derived → REFUTED at lifetime)

| Feature / level | B2 said | Lifetime delta | Verdict |
|---|---|---|---|
| `day_of_month_bucket=wk4` | anti −68.6pp | **+10.5pp WINNER** | REFUTED — INVERTED |
| `ema_alignment=bear` | anti −10.9pp | **+3.9pp** | REFUTED — INVERTED |
| `nifty_vol_regime=Medium` | anti −12.1pp | −2.1pp | WEAK |
| `consolidation_quality=loose` | anti −8.1pp | −1.0pp | NEUTRAL |

#### Cold sub-regime cascade (simplified v3)

| Tier | Filter | n | WR | Action |
|---|---|---|---|---|
| 1 | `wk4 AND swing_high=low` | 3,374 | 61.4% | TAKE_FULL |
| SKIP | (no Tier 1 match) | 9,502 | ~50% | SKIP |

(v1.1's Tier 2 and Tier 3 removed per S1 + S2 critique.)

#### Sector mismatch rules

- **AVOID Bear UP_TRI in Health** (hot WR = 32.4%; the only sector
  where hot sub-regime FAILS).
- **Prefer Chem / Other / FMCG / Pharma / Auto** (74-80% in hot).
- **Bank / IT / Energy** are tier-2 sectors (60-65% in hot).

#### Calendar mismatch rules

- **AVOID December** (−25pp lifetime — catastrophic, regardless of
  sub-regime).
- **Prefer April / Oct / Jul / Mar** (+10-14pp).
- **wk4 of any month** confers calendar lift (per L2 dominance).

---

## Production deployment guidance

### Inputs from upstream

The Bear UP_TRI cell consumes these inputs from the existing scanner /
brain pipeline:
- Per-signal features (114-feature library)
- Phase-5 validation status
- NIFTY universe-level features (`nifty_vol_percentile_20d`,
  `nifty_60d_return_pct`)
- Stock regime classification (must be `Bear`)
- Date / sector

### Outputs to downstream

Per Bear UP_TRI signal, the cell emits:
- `action`: TAKE_FULL / TAKE_SMALL / SKIP
- `sizing_modifier`: 1.0 / 0.5 / 0.0 (or 0.8 for day-correlation cap)
- `subregime_label`: hot / warm / cold
- `subregime_confidence`: 0-100 (geometric)
- `expected_wr_range`: narrative ("65-75%" etc.)
- `decision_reasons`: list of triggered rules (audit trail)

### Decision flow at signal time

```python
def bear_uptri_action(signal, market_state, phase_status):
    # Mismatch rules first (defensive)
    if signal.sector == "Health":
        return ("SKIP", "Health sector hostile to Bear UP_TRI even in hot")
    if signal.month == 12:
        return ("SKIP", "December catastrophic month for Bear UP_TRI")

    sub = detect_bear_subregime(market_state.vol_percentile_20d,
                                     market_state.nifty_60d_return)

    # Phase-5 hierarchy override
    if phase_status == "PHASE_5_VALIDATED":
        sizing = "full" if sub in ("hot", "warm") else "half"
        return ("TAKE", sizing, f"Phase-5 override; sub-regime={sub}")

    # Standard cascade
    if sub == "hot":
        # Apply trader heuristics
        if signal.repeat_name_within_6d:
            return ("TAKE_SMALL", "hot but repeat-name cap")
        if signal.same_day_count >= 3:
            return ("TAKE_FULL_80", "hot but day-correlation cap")
        return ("TAKE_FULL", "hot Bear UP_TRI baseline")

    if sub == "warm":
        return ("TAKE_FULL", "warm Bear UP_TRI (live evidence n=42 95% WR)")

    # cold
    if signal.feat_day_of_month_bucket == "wk4" and \
       signal.feat_swing_high_count_20d in ("low",):
        return ("TAKE_FULL", "cold Tier 1: wk4 × swing_high=low (63.3% lifetime)")

    return ("SKIP", "cold sub-regime, no Tier 1 match — edge collapses")
```

### Honest WR calibration for trader expectations

| Sub-regime | Lifetime expectation | Live observation (April 2026) | Trader-facing WR |
|---|---|---|---|
| hot | 68.3% | 93.8% (32 signals) | **65-75% expected at scale** |
| warm | UNTESTED at scale | 95.2% (42 signals) | **70-90% expected (small lifetime sample)** |
| cold + Tier 1 | 61.4% | UNTESTED in current live | **58-65% expected** |
| cold no match | ~49% | UNTESTED | **SKIP** |

**Critical:** The 94.6% live WR reflects (a) Phase-5 selection bias
and (b) April 2026 being a particularly clean hot/warm Bear period.
**Trader should expect 65-75% as the realistic production WR**, not
94.6%. Emotional preparation matters — drawdowns will feel larger when
you've been operating at near-perfect WR for a window.

---

## Comparison to Choppy UP_TRI cell

| Property | Choppy UP_TRI (v2) | Bear UP_TRI (v3) |
|---|---|---|
| Live signals | 91 | 74 |
| Live WR | 35% baseline; F1 58% (n=20) | 94.6% |
| Lifetime baseline | 52.3% | 55.7% |
| Live-vs-lifetime gap | F1: +23pp → +1.7pp | +38.9pp |
| Phase 5 validation rate | 26% | 100% |
| Sub-regime structure | tri-modal (quiet/balance/stress) | tri-modal (hot/warm/cold) |
| Sub-regime axes | vol × breadth | vol × 60d_return |
| Filter strategy | F1 cell-derived (live-tuned) | Sub-regime gated |
| Cell verdict | Filter narrow, sub-regime adaptive | Broad-band in hot/warm; cascade in cold |
| Lifetime-dominant patterns | breadth=med × vol=High × MACD bull (+10pp) | wk4 × swing_high=low (+7.6pp) |

**Key insight:** Different cell shapes for different cohorts. Choppy
required NARROW filtering (F1 captures 22% at +23pp lift); Bear is
BROAD-BAND in favorable sub-regime but needs gating in unfavorable
sub-regime.

---

## What's deferred or pending

### Within Bear UP_TRI cell

- **Warm sub-regime lifetime validation.** Current evidence is single-
  window (live n=42 at 95% WR). Need quarterly Phase-5 re-runs to
  populate lifetime warm cohort. Once n_warm ≥ 200 lifetime, validate
  expected WR range (70-90%).
- **Within-hot/warm refinement live test.** S1 found `multi_tf_alignment`
  + `range_compression_60d` add +9.5pp on top of hot. Live n too small
  to confirm.
- **Sector × sub-regime live test.** S1 stratification is lifetime; no
  live confirmation that Health UP_TRI in hot fails (only n=42 lifetime
  evidence).

### Bear regime broader

- **Bear DOWN_TRI cell** — apply 5-step methodology. Per T3 plan:
  expect DEFERRED outcome (live n=11, 18% WR). Sub-regime structure may
  differ from UP_TRI.
- **Bear BULL_PROXY cell** — third Bear cell. Live n=13 at 84.6% WR;
  expect HIGH live confidence with significant lifetime gap (parallel
  to Bear UP_TRI). Sub-regime structure unknown.
- **Bear regime-wide L1-L5** — comprehensive lifetime exploration
  across all 3 Bear cells (analogous to Choppy synthesis.md).

### Architectural

- **Vol_percentile universality test** — Sonnet recommended. Compare
  feature importance across regimes; confirm or refute vol as
  universal primary.
- **Bear detector v2 with warm zone** — pending lifetime validation of
  warm sub-regime.
- **Production sub-regime caching layer** — runs once per scan day,
  outputs `output/current_subregime.json`. Not yet implemented.

---

## Lessons for Bear DOWN_TRI cell (next session)

When investigating Bear DOWN_TRI:

1. **Apply 5-step methodology** as validated here. Each session
   produces 4 atomic commits; total ~3 sessions.

2. **Expect a different sub-regime structure than Bear UP_TRI.**
   DOWN_TRI is contrarian short signal in a Bear market — going DOWN
   in DOWN. Sub-regime axes likely involve: drawdown velocity (not
   depth), liquidity regime, sector dispersion.

3. **Be ready for a cell DEFERRED verdict** (per T3 plan; live n=11 is
   thin). DEFERRED is a legitimate outcome — see Choppy DOWN_TRI cell
   for reference.

4. **Live-vs-lifetime gap may invert direction.** Bear DOWN_TRI live
   18.2% vs lifetime 46.1% → live is WORSE than lifetime by −27.9pp.
   Investigate why current live is in a hostile sub-regime even though
   we'd expect Bear DOWN_TRI to be the natural Bear setup.

5. **Phase-5 validation rate may be lower** for DOWN_TRI than UP_TRI
   (already showed 0/25 → all WATCH). Differentiator analysis needs
   different methodology when no patterns validate.

6. **Sub-regime detector sharing** — the Bear detector built here
   should be reusable for Bear DOWN_TRI (same regime, same market
   state classification). Just apply the existing
   `detect_bear_subregime()` function.

7. **Calendar/sector rules likely differ** — DOWN_TRI may have
   different month-of-year and sector behavior than UP_TRI. Run S1-style
   stratification fresh.

---

## File outputs across all 3 sessions

### Session 1 (Live cell investigation)

| File | Purpose |
|---|---|
| `extract.py` + `comparison_stats.json` | B1: Phase 5 group extraction |
| `differentiators.py` + `differentiators.json` | B2: feature differentiator scoring |
| `differentiators_llm_interpretation.md` | B2 LLM mechanism analysis |
| `filter_test.py` + `filter_test_results.json` | B3: candidate filter back-test |
| `playbook.md` v1 | B4: Production playbook (live-derived) |
| `investigation_notes.md` | B4: hypotheses, surprises, open questions |
| `playbook_synth.py` + `_playbook_narrative.md` | B4 LLM narrative helper |
| `test_filter.py` | 7 unit tests |

### Session 2 (Lifetime validation)

| File | Purpose |
|---|---|
| `lifetime/extract.py` + `data_summary.json` | L1a: lifetime segmentation |
| `lifetime/cell_validation.py` + `cell_validation.json` | L1b: cell findings tested at scale |
| `lifetime/comprehensive_search.py` + outputs | L2: 2-feat + 3-feat search |
| `lifetime/sub_regime_llm_analysis.md` | L2 Sonnet sub-regime interpretation |
| `lifetime/synthesis.md` | L3: Lifetime synthesis (replaces v1) |
| `playbook.md` v1.1 | L3: Production-facing update |

### Session 3 (Stratification + detector + finalization)

| File | Purpose |
|---|---|
| `lifetime/stratified_search.py` + `stratified_findings.json` | S1: sector × calendar × sub-regime |
| `lifetime/stratified_llm_analysis.md` | S1 Sonnet stratified interpretation |
| `../bear/subregime/detector.py` + `detector.json` | S2: Bear bimodal/tri-modal detector |
| `../bear/subregime/comparison.md` | S2: Bear vs Choppy architecture |
| `../bear/subregime/architecture_critique.md` | S2 Sonnet architecture critique |
| `../bear/subregime/critique.py` | S2 LLM helper |
| `playbook.md` v3 (FINAL) | S3: Final production playbook |
| `CELL_COMPLETE.md` | S3: This document |
| `../bear/PRODUCTION_POSTURE.md` | S3: Wave 5 brain handoff specification |

---

## Summary

Bear UP_TRI cell is the strongest cohort across the entire Lab pipeline
(100% Phase 5 validation, 94.6% live WR), but the +38.9pp live-vs-
lifetime gap is the largest in the Lab and decomposes into +12.6pp
sub-regime + +26.3pp Phase-5 selection bias.

The cell is HIGH-confidence for production deployment with sub-regime
gating: TAKE_FULL in hot/warm sub-regimes (65-75% calibrated WR);
cascade-gated in cold sub-regime (Tier 1 wk4 × swing_high=low at 61.4%
WR; everything else SKIP). Sector and calendar mismatch rules apply
universally (AVOID Health UP_TRI even in hot; AVOID December).

Cell complete and ready for Wave 5 brain integration. Next: Bear
DOWN_TRI cell.
