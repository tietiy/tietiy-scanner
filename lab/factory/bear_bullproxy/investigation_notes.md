# Bear BULL_PROXY Cell — Investigation Notes (Session 1)

**Date:** 2026-05-02 night
**Branch:** `backtest-lab`
**Commits:** `4ffb3456` (P1) → `3034d55d` (P2) → `8fef3f3b` (P3) → this (P4)
**Verdict:** DEFERRED with provisional HOT-only filter (Verdict A)
**Sessions:** 1 of up-to-3 (Sessions 2-3 NOT recommended)

---

## Hypotheses tested

### H1 — Bear BULL_PROXY has Phase-5-validated combinations

**Status:** ❌ STRONGLY REFUTED.

Phase 5 has **0 Bear BULL_PROXY combinations** in
`combinations_live_validated.parquet`. Worse than Bear DOWN_TRI's 19
WATCH; Bear UP_TRI's 492 total. The Lab's combinatorial pipeline
produced literally nothing for this cell, and standard
winners-vs-rejected differentiator analysis is fundamentally not
feasible.

### H2 — Live 84.6% WR is real edge

**Status:** 🟡 PARTIAL.

Live 11W/2L = 84.6% IS real, but mostly inflated:
- Lifetime baseline: 47.3% (n=891)
- Hot sub-regime structural lift: +16.4pp at lifetime
- April 2026 sub-regime tailwind: ~10pp
- Phase-5-equivalent selection bias: ~12pp

Calibrated production WR for HOT-matched signals: **65-75%** (NOT 84.6%).
Same decomposition pattern as Bear UP_TRI cell.

### H3 — Bear sub-regime detector reuses cleanly

**Status:** ✅ CONFIRMED.

The Bear detector built in Bear UP_TRI Session 2 (vol > 0.70 AND
60d_return < −0.10 → hot) applies to BULL_PROXY without modification.
Lifetime hot/cold split produces +18.2pp delta — comparable to UP_TRI's
+14.9pp delta.

### H4 — BULL_PROXY mechanism parallels Bear UP_TRI (both bullish)

**Status:** ✅ MOSTLY CONFIRMED.

Both cells share `nifty_60d_return_pct=low` as primary winner anchor:
- Bear UP_TRI: +14.1pp lift
- Bear BULL_PROXY: +17.9pp lift (strongest in cell)

Bear DOWN_TRI inverts (−4.1pp anti). Confirms bullish/bearish direction
is the architectural divider.

### H5 — Calendar pattern aligns with Bear UP_TRI direction

**Status:** ✅ PARTIAL CONFIRMATION.

| Cell | wk2 | wk4 |
|---|---|---|
| Bear UP_TRI | −6.4pp anti | +7.5pp WINNER |
| Bear BULL_PROXY | **−5.5pp anti** | +2.3pp (mild) |
| Bear DOWN_TRI | +15.0pp WINNER | −17.5pp ANTI (INVERTED) |

BULL_PROXY's wk2/wk4 directional pattern aligns with UP_TRI (both
bullish setups dislike wk2, like wk4). DOWN_TRI is inverted.

### H6 — `inside_bar_flag` direction-flips vs Bear UP_TRI

**Status:** ✅ STRONGLY CONFIRMED.

| Cell | inside_bar=True |
|---|---|
| Bear UP_TRI | +4.9pp WINNER (compression coil) |
| Bear BULL_PROXY | −9.4pp ANTI (range expansion) |

Same regime, two bullish cells, OPPOSITE preferences on the same flag.
Mechanism: UP_TRI is breakout from compression (loves coiling);
BULL_PROXY is reversal from range expansion (range bar matters more).

This is a clean architectural finding — cells should NOT share filter
logic on inside_bar.

### H7 — `vol_climax_flag=True` reduces WR

**Status:** ✅ STRONGLY CONFIRMED.

`vol_climax_flag=True` is a −11.0pp ANTI in Bear BULL_PROXY (37.0% vs
48.0% absent). Mechanism: panic capitulation events exhaust the
support structure that BULL_PROXY's reversal mechanism needs.

### H8 — Sub-regime structure exists (parallel to UP_TRI)

**Status:** ✅ CONFIRMED.

Lifetime hot 9.7% / cold 90.3% split with +18.2pp delta. Bi-modal
(simpler than UP_TRI's tri-modal). Hot zone is **smaller** than UP_TRI
(9.7% vs 15%) — fewer high-edge signals to capture.

---

## Surprises

### S1 — 0 Phase 5 combinations

The most striking finding. Bear UP_TRI has 492 Phase 5 combos with
100% validation rate; Bear DOWN_TRI has 19 WATCH (0 V/P/R); Bear
BULL_PROXY has 0 combos at all.

The progression suggests Phase 4 walk-forward filtering became
increasingly hostile to BULL_PROXY × Bear combinations. Possibly:
- Phase 4 selection criteria filtered out BULL_PROXY's range-
  expansion signature
- BULL_PROXY's higher lifetime variability (more extreme vol-bucket
  responses) disqualified more combinations
- Sample n=891 lifetime is too small for combinatorial discovery

### S2 — U-shaped vol regime response

Both `vol=Low` (+7.9pp) and `vol=High` (+5.1pp) are winners; `vol=Medium`
is anti (−7.2pp). BULL_PROXY works in extreme vol regimes; middle vol
fails. This is **different from Bear UP_TRI's simple "vol=High dominant"
pattern**.

Mechanism hypothesis: BULL_PROXY's reversal mechanism works in two
modes:
- **Low vol Bear**: orderly decline; clean support level; institutional
  bottom-fishing creates support holds
- **High vol Bear**: extreme stress; short squeezes drive rapid bounces
- **Medium vol Bear**: neither extreme; reversals get squeezed by
  remaining momentum

### S3 — Live hot vs cold equal (85.7% vs 83.3%)

Mirrors Bear UP_TRI's S2 finding (borderline cold behaves like hot in
live). The 6 cold live signals (Apr 8, 10, 15) sit in 60d_return
−0.06 to −0.08 — borderline cold zone that may belong to "warm"
sub-regime.

### S4 — `inside_bar_flag` direction-flip

Same regime, two cells, opposite preferences. Cells should not share
filter logic on inside_bar. Generalizes to: **same-feature directional
flips across cells are real and mechanistically explained** (UP_TRI
compression vs BULL_PROXY expansion).

### S5 — `vol_climax_flag=True` is anti

Counter-intuitive but mechanistically clean. Capitulation events look
like they should HELP a bull-rejection setup (price has bottomed) but
actually HURT it (the support structure is destroyed in the climax).
BULL_PROXY needs orderly Bear, not panic Bear.

---

## Decision points (resolved)

### D1 — Verdict: FILTER, KILL, or DEFERRED?

**Decision:** DEFERRED with provisional Verdict A (HOT-only filter).

**Rationale:**
- FILTER (deploying as TAKE_FULL): not justified given thin live data
  and 0 Phase 5 combos
- KILL (LLM recommendation): too aggressive given lifetime hot zone
  (n=86, 63.7% WR, +16.4pp lift) is real and provides edge
- DEFERRED with provisional filter: capture lifetime hot zone insight,
  defer to Bear UP_TRI deployment first

### D2 — Should Sessions 2-3 proceed?

**Decision:** NO. Cell completes at Session 1.

**Rationale:** Same as Bear DOWN_TRI:
- 0 Phase 5 combos prevents standard methodology
- Lifetime data exhausted in P2-P3
- Live data too thin
- Bear UP_TRI is strictly better — focus engineering there
- Re-evaluate after Bear UP_TRI deployment success

### D3 — How conservative should production posture be?

**Decision:** Default SKIP; provisional TAKE_SMALL on HOT only (manual
enable).

**Rationale:**
- 90% of lifetime is cold (45.5% WR — losing proposition)
- Even hot zone is calibrated 65-75% (not 84.6% live)
- Bear UP_TRI takes priority for production deployment effort
- Preserve optionality without committing capital

---

## Open questions (deferred to re-evaluation triggers)

1. **Does Verdict A produce real edge in production?**
   Lifetime supports it (+16.4pp on n=86); live partial validation
   (6/7 hot wins). Need 30+ more live signals.

2. **Why 0 Phase 5 combinations?**
   Phase 4 walk-forward filtering produced no surviving combos.
   Worth investigating whether the filter logic excluded
   BULL_PROXY's natural feature signature.

3. **Does the U-shaped vol response generalize to Bull regime?**
   Bear BULL_PROXY's vol=Low and vol=High both work. Bull regime's
   BULL_PROXY (when Bull data accumulates) may show different pattern.

4. **Should warm sub-regime exist for BULL_PROXY?**
   Bear UP_TRI's warm zone (S2 finding) hasn't been tested for
   BULL_PROXY. Live data suggests it might (cold borderline at 83%);
   needs lifetime warm cohort to populate.

5. **Cross-cell mechanism architecture.**
   The cells now show:
   - Same nifty_60d=low anchor: bullish (UP_TRI, BULL_PROXY) vs bearish
     (DOWN_TRI)
   - Different inside_bar preferences: compression (UP_TRI) vs expansion
     (BULL_PROXY)
   - Different calendar profiles: month-end (UP_TRI/BULL_PROXY) vs
     mid-month (DOWN_TRI)

   This 3-cell × 3-feature pattern is the foundation for Bear regime
   synthesis (next session). Bull regime cells should expect to share
   anchor features but show new mechanism flips.

---

## Files produced this session

| File | Purpose |
|---|---|
| `extract.py` + `comparison_stats.json` | P1: data extraction with halt-condition surfacing |
| `differentiators.py` + `differentiators.json` | P2: lifetime-based differentiator analysis |
| `differentiators_llm_interpretation.md` | P2 Sonnet 4.5 mechanism analysis |
| `filter_test.py` + `filter_test_results.json` | P3: 4-verdict back-test |
| `playbook.md` | P4: Production playbook (DEFERRED) |
| `investigation_notes.md` | (this) |

---

## Session 1 verdict

**Cell complete; DEFERRED with provisional HOT-only filter; ready
for Bear regime synthesis.**

Bear BULL_PROXY does not produce a confident production filter at
Session 1. It produces:
1. A confirmed sub-regime structure (hot/cold bi-modal; +18.2pp delta)
2. A provisional Verdict A filter (HOT-only) supported by lifetime
   data (n=86, 63.7% WR, +16.4pp lift)
3. Default SKIP production posture; manual enable for hot only
4. Strong cross-cell findings (calendar + inside_bar direction flips;
   nifty_60d=low anchor for bullish setups)
5. Clear DEFERRED verdict with re-evaluation triggers

This completes Bear regime cell investigation:
- **Bear UP_TRI:** ✅ COMPLETE (3 sessions; production-ready with sub-
  regime gating)
- **Bear DOWN_TRI:** DEFERRED with provisional Verdict A (kill_001 +
  wk2/wk3 timing)
- **Bear BULL_PROXY:** DEFERRED with provisional Verdict A (HOT-only)

**Next session:** Bear regime synthesis — cross-cell consolidation,
unified production decision flow, comparison to Choppy regime.
