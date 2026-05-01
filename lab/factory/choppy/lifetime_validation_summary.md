# Choppy Regime Lifetime Validation Summary

**Investigation date:** 2026-05-02
**Validation scope:** Cross-checking live-derived Choppy cell findings against 35,496 lifetime Choppy signals from `enriched_signals.parquet`.

---

## Headline finding

**Live-derived rules largely DO NOT generalize to lifetime scale.** The Choppy cells were calibrated on 102 live signals (April 2026, uniformly high-vol Choppy sub-regime). When tested against 15-yr lifetime data spanning multiple Choppy sub-regimes:

- **F1 filter's lift collapses from +23pp (live) to +1.7pp (lifetime)**
- **3 of 4 universal anti-features are REFUTED** — actually slightly POSITIVE at lifetime
- BULL_PROXY KILL verdict survives (the only finding that confirms cleanly)

The implication: live findings captured an April 2026 hostile-Choppy sub-regime exploit, not a structural Choppy edge. **Production deployment should treat Choppy cell rules as regime-shift adaptive, not lifetime-validated.**

---

## V1 — F1 / F4 lifetime validation

### Numbers

| Metric | Live (April 2026) | Lifetime (15yr) |
|---|---|---|
| UP_TRI × Choppy total signals | 91 | 27,072 (excl OPEN) |
| Baseline WR | 34.9% | **52.3%** |
| F1 match rate | 22.0% (20/91) | 28.0% (7,569/27,072) |
| F1 matched WR | 57.9% | **54.0%** |
| F1 lift over baseline | **+23.0pp** | **+1.7pp** |
| F4 match rate | 6.6% (6/91) | 10.0% (2,712/27,072) |
| F4 matched WR | 66.7% | 55.3% |
| F4 lift over baseline | +31.7pp | **+3.0pp** |

### Verdict

- **F1 verdict: WEAKENED** — match rate generalizes (filter targets the same signals) but the WR edge over baseline largely vanishes. The 23pp live lift was a regime-shift exploit. At lifetime scale F1 is essentially noise (+1.7pp on n=7,569).
- **F4 verdict: WEAKENED** — same pattern, modest +3pp lift.

### Interpretation

F1 likely identifies the sub-set of UP_TRI×Choppy signals that survive HOSTILE Choppy sub-regimes. In April 2026 (uniformly hostile), the average WR was 35%, F1 selected the 22% that pulled to 58%. At 15-yr aggregate where Choppy is a mix of hostile and friendly sub-regimes (avg WR 52%), F1 picks the same archetype but the lift compresses because the friendly sub-regimes don't reward F1's selectivity proportionally.

**F1 is a regime-shift adaptive filter, not a structural Choppy edge filter.**

---

## V2 — Universal anti-features lifetime validation

### Numbers

Anti-features were claimed across all 3 Choppy cells. Lifetime test (across 35,290 Choppy signals, all signal types):

| Anti-feature | Lifetime WR present | WR absent | Discrimination | Verdict |
|---|---|---|---|---|
| `higher_highs_intact_flag=True` | 52.2% | 50.6% | **−1.6pp** (inverted) | **REFUTED** |
| `ema20_distance_pct=high` | 52.8% | 50.2% | **−2.7pp** (inverted) | **REFUTED** |
| `MACD_histogram_slope=falling` | 49.8% | 52.2% | +2.4pp | WEAK |
| `market_breadth_pct=high` | 52.4% | 50.4% | **−2.1pp** (inverted) | **REFUTED** |

3 of 4 anti-features show NEGATIVE discrimination at lifetime scale, meaning the "anti-feature" is actually a slightly POSITIVE feature at lifetime. The live finding that these features rejected (0% winners, 12-19% rejected) inverted at scale.

### Per signal type

- **UP_TRI Choppy**: same pattern — 3 of 4 REFUTED, 1 WEAK
- **DOWN_TRI Choppy**: 4 of 4 WEAK (all anti-feature claims show small but consistent negative effect; weakest evidence)
- **BULL_PROXY Choppy**: REFUTED for `higher_highs_intact=True` (+6.9pp WR PRESENT) and `market_breadth=high` (+7.9pp WR PRESENT). Strongly inverted.

### Verdict

The "universal Choppy anti-features" claim from the live-derived synthesis playbook does not survive lifetime validation. The mechanism narrative ("Choppy kills momentum-extended setups") was coherent for April 2026 but doesn't describe Choppy regime universally.

**Lifetime data suggests the inverse**: in normal Choppy regimes, momentum-extended stocks (high market breadth, intact HHs, extended above EMA20) actually have a slight WIN-rate edge. April 2026 was atypical.

---

## V3 — BULL_PROXY KILL verdict lifetime re-investigation

### Numbers

| Metric | Live | Lifetime |
|---|---|---|
| n | 8 | 1,931 |
| Baseline WR | 25% | 49.6% |
| Validated patterns | 0 of 175 | n/a |

Lifetime filter back-test (8 candidates):

| Filter | n_match | Lifetime WR | Lift | Verdict |
|---|---|---|---|---|
| F1: ema_bull AND coiled=medium | 776 | 50.1% | +0.5pp | no edge |
| F2: ema_alignment=bull | 850 | 49.9% | +0.3pp | no edge |
| F4: market_breadth_pct=high | 611 | 55.1% | +5.5pp | MARGINAL |
| F5: higher_highs_intact_flag=True | 629 | 54.3% | +4.7pp | no edge |
| **F6: ema_bull + coiled=medium + market_breadth=high** | **286** | **56.5%** | **+6.9pp** | MARGINAL |
| F7: forbid extended momentum (KILL hypothesis) | 959 | 48.3% | −1.3pp | no edge |

**Sector breakdown** (n≥50 sectors):
- Energy: 58.1% WR (+8.5pp lift, n=128)
- Auto: 54.5% (+4.9pp, n=149)
- FMCG: 54.2% (+4.6pp, n=224)
- Infra: 39.6% (−10.0pp, n=187) — strong negative
- Other: 42.4%, IT: 43.3%, Pharma: 46.5%

### Verdict

**KILL CONFIRMED at lifetime scale** — no filter beats the +10pp lift threshold on n≥50. Best filter (F6 compression+breadth) reaches +6.9pp on n=286 — MARGINAL but below the standard.

The compression-coil narrow-exception hypothesis from the V2 differentiator analysis (that `ema_bull + coiled=medium` could resurrect Choppy BULL_PROXY) does **NOT replicate at lifetime** — F1 lifts only +0.5pp on 776 lifetime matches.

**Sector-conditional**: Energy + Auto + FMCG are above-baseline; Infra and Other are deeply negative. A sector-conditional BULL_PROXY filter could be explored, but no single sector clears +10pp.

KILL verdict at production level: **REJECT all Choppy BULL_PROXY signals** — confirmed.

---

## Confidence-level changes

Comparing live-derived confidence vs lifetime-validated confidence:

| Cell | Live Confidence | Lifetime Confidence | Change |
|---|---|---|---|
| Choppy UP_TRI (F1 filter) | MEDIUM (live n=20 matched, +23pp lift) | **LOW** (lift +1.7pp at scale; regime-adaptive only) | DOWNGRADED |
| Choppy DOWN_TRI | DEFERRED (live n=3) | DEFERRED (no change) | unchanged |
| Choppy BULL_PROXY (KILL) | HIGH (0/175 validated) | **HIGH** (no lifetime filter found) | confirmed |
| Choppy regime universal anti-features | MEDIUM | **REFUTED** | downgraded to NULL |

Overall regime confidence: was MEDIUM → now **LOW-MEDIUM** for active filters; HIGH for KILL verdict only.

---

## Implications for production deployment

### Status of cell findings

1. **F1 filter for Choppy UP_TRI**: not production-ready as a stable edge filter. Two options:
   - (a) Deploy as **regime-shift adaptive filter** with explicit caveat that lift varies by sub-regime; track live performance closely
   - (b) Withdraw F1 from production; default Choppy UP_TRI to TAKE_SMALL or SKIP

2. **Universal anti-features**: do NOT use as universal kill conditions. They were April 2026 artifacts.

3. **BULL_PROXY KILL**: production-ready. REJECT all Choppy BULL_PROXY signals.

4. **DOWN_TRI**: unchanged DEFERRED status.

### Production posture (recommended)

**Conservative interpretation of validation results:**
- Choppy regime as a whole has no clean lifetime-validated "edge filter"
- The cleanest finding is the BULL_PROXY KILL (1 negative rule)
- Live April 2026 findings (F1, anti-features) tell us about a specific sub-regime, not Choppy overall
- Default action for any Choppy signal that doesn't match a confirmed rule: **TAKE_SMALL or SKIP**

### Quarterly re-validation triggers

When live signal accumulation produces ≥30 more Choppy UP_TRI signals in different sub-regimes:
- Re-run V1 with sub-regime-conditional analysis (split by `nifty_vol_regime`)
- Determine whether F1's lift returns when next hostile-Choppy sub-regime arrives
- If F1's lift recurs in another hostile Choppy → confirms regime-adaptive utility
- If F1's lift doesn't recur → withdraw F1 from production

---

## Methodology lessons for future cells

### What this validation taught us

1. **Live evidence alone is insufficient** for Choppy regime cells. April 2026 baselines (35%) differ dramatically from 15-yr lifetime baselines (52%). Live findings need lifetime cross-check before production deployment.

2. **Lift over baseline is regime-conditional**. A filter producing +23pp lift in hostile sub-regime may produce +2pp lift in friendly sub-regime. The "lift" metric must be interpreted with sub-regime context.

3. **Anti-features can invert** between live and lifetime. Live winners-vs-rejected differentiator analysis is informative for live patterns but does NOT prove lifetime structural truth.

4. **KILL verdicts validate more reliably** than TAKE filters. Negative findings (cohort doesn't work) are more robust than positive findings (filter works).

5. **Match rate generalizes; WR edge does not**. F1 matched 22% live and 28% lifetime — similar selectivity. But matched WR's 23pp lift collapsed to 1.7pp. The filter targets the same signals; what changes is whether those signals are the right ones to pick in current regime.

### Future cell methodology recommendations

For all subsequent regime cells (Bear, Bull when activated):

1. **Always run lifetime validation BEFORE shipping cell to production**. The 4-step methodology (extract, differentiate, filter test, playbook) needs a 5th step: lifetime cross-check.

2. **Sub-regime-conditional analysis** for any regime that spans multiple sub-regimes (Choppy is high-vol/low-vol; Bear is mild/severe; Bull is early/late). Lift should be reported per sub-regime, not aggregate.

3. **Skepticism toward live findings with extreme dispersion**. Anti-features at 0% winners vs 12-19% rejected suggested a strong signal — but it was sub-regime-specific. Universal claims need universal evidence.

4. **Conservative production defaults**. When in doubt, skip. The cost of missing edges is opportunity; the cost of taking false edges is real losses.

---

## Cross-INV alignment with Phase 2/3/4 findings

- Phase 2 lifetime-Choppy importance ranked `ema_alignment` rank 1 — V1 confirms this at lifetime ema_bull patterns are above baseline in WR. Phase 2 importance and lifetime WR are consistent.
- Phase 3 lifetime UP_TRI×Choppy×D5 baseline = 49.4% — V1 shows 52.3% (slight discrepancy due to D6 horizons included; Phase 3 was strictly D5).
- Phase 4 produced 1,085 UP_TRI×Choppy survivors at high test_wr; Phase 5 dropped most to WATCH/REJECTED. The V1 finding that F1 lift collapses at scale is consistent with this — Phase 4's edge claim doesn't survive scale.
- INV-013 D2 dominance for DOWN_TRI: Choppy DOWN_TRI lifetime baseline 46.1% — substantively below Choppy UP_TRI 52.3%. DOWN_TRI is a harder cohort even before filtering.

---

## Update Log

- **v1 (2026-05-02):** Initial lifetime validation surfaced significant disagreement between live findings (April 2026) and lifetime data (15yr). F1 filter weakened from +23pp to +1.7pp. Universal anti-features 3 of 4 REFUTED. BULL_PROXY KILL verdict confirmed.
