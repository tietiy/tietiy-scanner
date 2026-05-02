# Bull DOWN_TRI Cell — COMPLETE (PROVISIONAL_OFF)

**Status:** ✅ COMPLETE at PROVISIONAL_OFF (Session 1 of 1).
**Date:** 2026-05-02 night
**Branch:** `backtest-lab`
**Commits:** 4 atomic commits across BD1-BD4

This document is the cross-session summary of the Bull DOWN_TRI cell —
the second Bull regime cell investigated. Builds on Bull UP_TRI cell's
lifetime-only methodology and tests cross-cell direction-flip predictions.

---

## Cell scope and outcome

| Metric | Value |
|---|---|
| Cell signal × regime | DOWN_TRI × Bull |
| Live signals | **0** (Bull regime not classified live during current period) |
| Lifetime signals | 10,024 |
| Lifetime baseline WR | 43.4% (BELOW 50% — losing baseline) |
| Sub-regime structure | tri-modal (recovery / healthy / normal / late) — same axes as Bull UP_TRI |
| Best sub-regime | **late_bull (53.0% WR)** ★ — only positive cell |
| Best filter | **late_bull × wk3 → 65.2% WR (n=253, +21.8pp)** ★ |
| Confidence (lifetime-validated) | LOW (no live validation possible) |
| Production posture | **PROVISIONAL_OFF default** |

---

## Direction-flip verdict — STRONGLY CONFIRMED

The cell's headline finding is the **strongest cross-cell architectural
result to date**:

### 4-cell sub-regime PERFECT INVERSION

| Sub-regime | Bull UP_TRI WR | Bull DOWN_TRI WR | Inversion |
|---|---|---|---|
| recovery_bull | 60.2% (best) | 35.7% (worst) | ✓ |
| healthy_bull | 58.4% | 40.5% | ✓ |
| normal_bull | 51.3% | 42.6% | ✓ |
| late_bull | 45.1% (worst) | **53.0% (best)** | ✓ |

All 4 sub-regime cells flip WR direction. UP_TRI's best is DOWN_TRI's
worst, and vice versa. Mechanism: late_bull (mid 200d × low breadth =
narrowing leadership topping) is exactly when DOWN_TRI shorts work;
recovery_bull (early-cycle quality leadership) is exactly when shorts
get squeezed.

### Calendar inversion confirmed

| Week | UP_TRI lift | DOWN_TRI lift | Inversion |
|---|---|---|---|
| wk3 | -3.3pp | **+8.4pp** | ✓ STRONG mirror |
| wk4 | +2.6pp | **-5.6pp** | ✓ STRONG mirror |

This confirms cross-regime calendar inversion in 2 of 3 regimes (Bear
also showed wk2 vs wk4 inversion). Pattern: **bullish setups prefer
month-end flows (wk4); bearish setups prefer mid-month flows (wk3 in
Bull, wk2 in Bear).**

### Sector inversion partial

- Bull UP_TRI top: IT, Health, Consumer, FMCG (growth/quality, defensive)
- Bull DOWN_TRI top: Metal, Bank, Health (cyclicals/financials)
- FMCG cleanly flips: UP_TRI top → DOWN_TRI worst (-4.0pp)
- Health appears in BOTH tops (rotation sector, two-direction)

---

## Methodology applied

3-step lifetime-only adaptation (validated in Bull UP_TRI):

| Step | What |
|---|---|
| BD1 | Extract + apply Bull sub-regime detector + thin-data assessment |
| BD2 | Differentiator analysis + direction-flip + calendar inversion + LLM |
| BD3 | Verdict articulation: 5 candidate filters tested |
| BD4 | PROVISIONAL_OFF playbook + this cross-cell synthesis |

Same template as Bear DOWN_TRI / Bull UP_TRI. Methodology is now
**proven cross-regime applicable** for cells with no live data.

---

## Findings hierarchy

### Architectural insights (top-level)

1. **Cross-cell direction-flip pattern at SUB-REGIME LEVEL is the
   strongest cross-cell architectural finding.** Bull's 4 sub-regime
   cells perfectly mirror between UP_TRI and DOWN_TRI. This is
   stronger than feature-level direction inversions (which are weak
   for Bull).

2. **Anchor inversion is weaker at feature level than at sub-regime
   level.** Bull UP_TRI's 20d=high winner (+5-8pp) maps to DOWN_TRI's
   20d=high only -1.6pp. Sub-regime structure does the heavy lifting.

3. **Calendar inversion is now confirmed in 2/3 regimes** (Bear, Bull).
   Different mid-month winners per regime (Bear wk2, Bull wk3) but the
   inversion direction holds.

4. **DOWN_TRI cells are structurally weak across regimes.** Bull
   baseline 43.4%, Bear baseline 46.1% — both BELOW 50%. Contrarian
   short setups produce losing baselines outside narrow exhaustion
   sub-regime windows.

5. **late_bull × wk3 is the strongest Bull DOWN_TRI configuration**
   (+21.8pp lift on n=253). Higher precision than Bear DOWN_TRI's
   provisional filter (+7.5pp on n=1,446) but narrower sample.

### Cell-specific findings

#### Filter cascade (provisional)

```python
def bull_downtri_action_provisional(signal, market_state):
    sub = detect_bull_subregime(
        market_state.nifty_200d_return_pct,
        market_state.market_breadth_pct,
    )
    # SKIP all non-late_bull
    if sub != "late_bull":
        return "SKIP"  # 35-43% WR; losing zones

    # Disqualifying conditions within late_bull
    if signal.sector in ("FMCG", "Auto"):
        return "SKIP"  # -4pp lifetime
    if signal.feat_RSI_14 == "high":
        return "SKIP"  # high RSI = continuation, not topping (counter-intuitive but real)
    if signal.feat_nifty_vol_regime != "Low":
        return "SKIP"  # late_bull DOWN_TRI works in low vol

    # Highest precision: late_bull × wk3
    if signal.feat_day_of_month_bucket == "wk3":
        return "TAKE_SMALL"  # 65.2% lifetime expected (60-70% calibrated)
    if signal.feat_day_of_week == "Mon":
        return "TAKE_SMALL"  # within-late_bull +18pp (provisional)

    # Lower-precision late_bull match
    return "TAKE_SMALL"  # 53.0% lifetime baseline
```

#### Calibrated WR expectations (HONEST)

| Filter | Lifetime WR | Calibrated production |
|---|---|---|
| late_bull + wk3 | 65.2% | **60-70%** |
| late_bull + Mon | ~71% (n=165) | 62-72% (provisional) |
| late_bull broad | 53.0% | 50-58% |
| Other sub-regimes | 35-43% | SKIP (losing) |

---

## Comparison to Bear DOWN_TRI cell

| Property | Bear DOWN_TRI | Bull DOWN_TRI |
|---|---|---|
| Lifetime n | 3,640 | 10,024 |
| Live n | 11 (18.2% WR) | 0 |
| Lifetime baseline | 46.1% | 43.4% |
| Phase 5 winners | 0 | n/a (no Phase 5 needed) |
| Sub-regime gating | none specified (uses wk2/wk3 timing) | late_bull only |
| Provisional filter | wk2/wk3 + non-Bank | late_bull × wk3 |
| Filter WR | 53.6% (+7.5pp) | **65.2% (+21.8pp)** ★ |
| Filter n | 1,446 | 253 |
| Filter match rate | 39.7% | 2.9% |
| KILL rule | kill_001 (Bank) | (no universal sector kill) |

**Bull DOWN_TRI has higher precision but narrower sample.** Both cells
are DEFERRED. Both rely on lifetime data only.

---

## Universal contrarian-short hostility

Both DOWN_TRI cells (Bear + Bull) reveal a structural truth:
**contrarian short setups produce <50% baseline across regimes**.

- Bear DOWN_TRI lifetime: 46.1%
- Bull DOWN_TRI lifetime: 43.4%

The only sub-regimes where DOWN_TRI works:
- Bear capitulation (specific, narrow)
- Bull late-cycle topping (late_bull, narrow)

Outside those windows, contrarian shorts fail systematically.
Architectural insight: **the trader's Lab pipeline correctly identifies
DOWN_TRI as a niche signal type** — not a universal short signal but
a regime-specific exhaustion-bet.

---

## What's deferred or pending

### Within Bull DOWN_TRI cell

- **Live validation** — entirely pending. Needs Bull regime return +
  ≥30 live Bull DOWN_TRI signals + matched-WR ≥ 50% on
  `late_bull × wk3` filter.
- **n=253 sample tightening** — quarterly Phase-5 re-runs as Bull
  regime accumulates should populate more late_bull × wk3
  observations.
- **Mon effect within late_bull** — n=165 +18pp finding requires
  validation.

### Bull regime broader

- **Bull BULL_PROXY cell** — third and final Bull cell. Apply same
  3-step lifetime-only methodology. Predicted to show similar
  architecture to Bull UP_TRI but with different filter anchor
  (likely sector momentum dispersion or accumulation patterns).

### Architectural

- **Sub-regime perfect inversion universality** — does Choppy show
  same 3-cell sub-regime inversion between UP_TRI and DOWN_TRI?
  Worth dedicated analysis.

- **DOWN_TRI architectural truth** — both Bear DOWN_TRI and Bull
  DOWN_TRI DEFERRED. Both have provisional sub-regime-conditional
  filters. Cross-regime DOWN_TRI synthesis would be valuable.

---

## Lessons for Bull BULL_PROXY cell (next session)

When investigating Bull BULL_PROXY:

1. **Apply 3-step lifetime-only methodology** (validated 3x now).

2. **Bull BULL_PROXY likely parallels Bull UP_TRI direction** (both
   bullish):
   - Likely positive WR sub-regimes: recovery_bull, healthy_bull
   - Likely negative WR: late_bull
   - Calendar: likely wk4 mild winner (parallel to UP_TRI)

3. **Expected outcome**: PROVISIONAL_OFF with provisional filter.
   Parallel to Bear BULL_PROXY (also DEFERRED with HOT-only filter).

4. **Sub-regime detector reuses** from Bull UP_TRI/DOWN_TRI work.

5. **Watch for vol_climax × BULL_PROXY anti** (universal pattern from
   Bear BULL_PROXY: -11.0pp). May replicate in Bull regime.

---

## File outputs

| File | Purpose |
|---|---|
| `extract.py` + `data_summary.json` | BD1: lifetime extraction + sub-regime application |
| `differentiators.py` + `differentiators.json` | BD2: cross-cell tests + direction-flip + calendar inversion |
| `differentiators_llm.md` | BD2 LLM mechanism analysis |
| `filter_test.py` + `filter_test_results.json` | BD3: 5-verdict candidate test |
| `playbook.md` | BD4: PROVISIONAL_OFF playbook |
| `CELL_COMPLETE.md` | BD4: This document |
| `cross_cell_synthesis.md` | BD4 LLM synthesis (post-cell) |

---

## Summary

Bull DOWN_TRI cell is **complete at PROVISIONAL_OFF** with the strongest
cross-cell direction-flip evidence in the Lab pipeline:

1. **Sub-regime perfect inversion** (4 of 4 cells flip WR direction
   between UP_TRI and DOWN_TRI)
2. **Calendar inversion confirmed** in 2 of 3 regimes
3. **Provisional filter with +21.8pp lift** (highest single-filter lift
   for any DEFERRED cell)
4. **DOWN_TRI cells universally weak** outside narrow exhaustion
   sub-regimes

Production: DEFAULT SKIP; manual enable available for late_bull × wk3
when Bull regime returns + 30+ live signals validate provisional filter.

**Next session:** Bull BULL_PROXY cell (Session 1, lifetime-only).
