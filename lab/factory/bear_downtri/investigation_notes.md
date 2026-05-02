# Bear DOWN_TRI Cell — Investigation Notes (Session 1)

**Date:** 2026-05-02 night
**Branch:** `backtest-lab`
**Commits:** `6d0bb4d8` (D1) → `149b5826` (D2) → `e8f1e4c5` (D3) → this (D4)
**Verdict:** DEFERRED with provisional filter
**Sessions:** 1 of up-to-3 (Sessions 2-3 NOT recommended; cell completes here)

---

## Hypotheses tested

### H1 — Bear DOWN_TRI has a clean cell-investigation filter

**Status:** ❌ NOT FEASIBLE (Phase 5 produces 0 winners).

The standard 4-step methodology requires winners-vs-rejected
differentiator analysis. With 0 V / 0 P / 0 R in Phase 5 (all 19
combos are WATCH), this cannot run. Forced fallback to lifetime data
only.

### H2 — kill_001 (Bank exclusion) is structurally correct

**Status:** ✅ CONFIRMED but lifetime support is weak.

- Live: 0 of 6 Bank wins (0.0% WR) — strongly consistent with kill_001
- Lifetime: Bank 45.0% vs non-Bank 46.4% — only +1.3pp gap
- Live confirms; lifetime barely supports. The 0/6 may be April 2026
  sub-regime artifact, but kill_001 stays as defensive default.

### H3 — Lifetime data supports a filter even without Phase 5 evidence

**Status:** ✅ PARTIALLY CONFIRMED.

`day_of_month_bucket=wk2` is a +15.0pp lifetime winner; `wk4` is
−17.5pp anti. Verdict A (wk2/wk3 + Bank kill) shows +7.5pp lift on
n=1,446 lifetime matches (39.7% match rate). This is meaningful, but
live data has only 1 match (insufficient validation).

### H4 — Live-vs-lifetime gap inverts vs Bear UP_TRI

**Status:** ✅ STRONGLY CONFIRMED.

Bear UP_TRI: live 94.6% / lifetime 55.7% (+38.9pp inflation).
Bear DOWN_TRI: live 18.2% / lifetime 46.1% (−28.0pp deflation).
Mechanism per Sonnet 4.5: Bear UP_TRI's Phase-5 winners reflect
selection bias inflating live; Bear DOWN_TRI has no Phase-5 winners,
so live data is unfiltered raw signal output hitting unfavorable
conditions.

### H5 — kill_001 should extend to other weak lifetime sectors

**Status:** ❌ NOT YET RECOMMENDED.

Lifetime sector floors: Auto 40.4%, Energy 40.7%, Metal 41.4%. Each
−5 to −6pp below baseline. Verdict C (extend kill to all four) tested
at lifetime: lift only +2.7pp (n=2,087 matched). Lifetime evidence
too weak to justify outright sector ban; live evidence too thin to
support. RECOMMENDATION: monitor; don't extend yet.

### H6 — Direction-relevant features should anti-correlate with wins

**Status:** ❌ MIXED.

DOWN_TRI is contrarian short — bull-aligned features should reduce
WR. Tested:
- `ema_alignment=bull`: Δ −0.7pp (negligible)
- `MACD_signal=bull`: Δ −0.4pp (negligible)
- `higher_highs_intact_flag=True`: Δ **+4.0pp** (POSITIVE — winner
  feature, not anti)

The HHs intact +4pp finding is the most striking — counterintuitive
for a short setup but mechanistically plausible (HHs intact +
descending triangle = building distribution top, perfect short setup).

---

## Surprises

### S1 — Calendar pattern INVERTS vs Bear UP_TRI

Bear UP_TRI's strongest lifetime calendar feature was `wk4` (+7.5pp
WINNER); Bear DOWN_TRI's strongest is `wk2` (+15.0pp WINNER) with
`wk4` as the strongest anti (−17.5pp). Same regime, two cells, two
directions, two completely opposite calendar profiles.

Mechanism hypothesis: month-end institutional flows favor Bear UP_TRI
(month-end rebalancing creates buy-side pressure that turns triangle
breakouts into clean reversal opportunities). Mid-month flows favor
Bear DOWN_TRI (no rebalancing-driven buy support; descending
triangles can break cleanly).

### S2 — `higher_highs_intact_flag=True` is a +4pp WINNER

Counterintuitive. In Choppy UP_TRI cell, this flag was a −10.9pp anti
(HHs intact = continuation setup; Choppy regime kills continuation).
In Bear DOWN_TRI lifetime, HHs intact is a +4pp WINNER.

Mechanism: HHs intact + descending triangle = stock making
higher-highs but failing to break flat resistance. This is **building
distribution top with stuck buyers** — the resistance turns into supply,
support eventually breaks, trapped longs capitulate. Classic
short-setup mechanism.

### S3 — Both live winners fired the same date

IPCALAB (Pharma) + VINATIORGA (Chem) both fired on 2026-04-06. Same
date suggests **single-event-driven win** rather than two independent
edge cases. Adds further n=11 → effectively n=10 unique-day evidence.

### S4 — `nifty_60d_return_pct=low` is ANTI for DOWN_TRI

Bear UP_TRI's strongest filter anchor (`nifty_60d=low`) is
−4.1pp anti for Bear DOWN_TRI. Mechanism: sustained Bear without
consolidation favors UP_TRI (oversold bounces work) and HURTS
DOWN_TRI (continuation shorts get squeezed when sentiment too one-
sided).

This is a clean cross-cell relationship: the SAME feature predicts
opposite outcomes for UP_TRI vs DOWN_TRI in Bear regime.

### S5 — Bank lifetime gap is small (+1.3pp), but live is dramatic (0/6)

kill_001 lifetime evidence is weak; the 0/6 live is what makes the
case. Suggests Bank-specific failure mode in current April 2026
sub-regime (possibly: Bank Bear stocks with descending triangles
=building bases for Bull rotation rather than continuation). Hard to
verify with live n=6.

---

## Decision points (resolved)

### D1 — Verdict: FILTER, KILL extension, or DEFERRED?

**Decision:** DEFERRED with provisional Verdict A filter.

**Rationale:**
- FILTER (deploying Verdict A as TAKE rule): Lifetime support is good
  (+7.5pp on n=1,446) but live can't validate (n=1 match). Premature.
- KILL EXTENSION (Bank+Auto+Energy+Metal): Lifetime evidence too weak
  (+2.7pp lift). Live sample too thin to justify. Sectors hostile
  but not bannable.
- DEFERRED with provisional Verdict A: lifetime supports the filter
  for future trades; live can monitor; production stays conservative
  pending more data.

### D2 — Should Sessions 2-3 proceed?

**Decision:** NO. Cell completes at Session 1 with DEFERRED verdict.

**Rationale:**
- Session 2 is "lifetime validation" — but D2-D3 already used lifetime
  data extensively. No new info would emerge.
- Session 3 is "stratification + final synthesis" — but with 0 Phase 5
  winners, there's nothing additional to stratify or synthesize.
- Cell methodology stalls on lack of winners. Bear UP_TRI's full 3-
  session methodology assumed winners-vs-rejected differentiation;
  doesn't apply here.

### D3 — How conservative should production posture be?

**Decision:** TAKE_SMALL on Verdict A matches; SKIP otherwise.

**Rationale:**
- Even Verdict A's +7.5pp lifetime lift is modest (53.6% WR vs 46.1%
  baseline) — not strong enough for TAKE_FULL
- Live n=11 with 2 wins both filtered OUT by Verdict A (Mon wk1) =
  no live validation
- Conservative TAKE_SMALL caps downside while still acknowledging
  lifetime evidence

---

## Open questions (deferred to re-evaluation triggers)

1. **Does Verdict A produce a real edge in production?**
   Lifetime supports it; live can't validate. Need ≥20 more live
   signals to test.

2. **Is Bear DOWN_TRI's hostile current sub-regime a temporary
   condition or structural?**
   April 2026's 18.2% live WR is far below 46.1% lifetime. Either
   April is exceptionally bad, OR Bear regimes increasingly favor
   UP_TRI bounces over DOWN_TRI continuations (regime evolution).

3. **Should kill_001 extend?**
   Lifetime sector floors (Auto/Energy/Metal) suggest 5-6pp underweight,
   but live evidence too thin. Monitor next 15 signals; if Auto/Energy
   live signals lose 80%+, extend kill_001.

4. **Why do `nifty_60d=low` and `wk4` flip direction across UP_TRI
   vs DOWN_TRI?**
   This is a deep cross-cell finding. The same feature predicts
   opposite outcomes in two cells of the same regime. Worth a
   dedicated cross-cell analysis at regime synthesis stage.

5. **Should the cell investigation methodology evolve when Phase 5
   produces 0 winners?**
   Bear DOWN_TRI exposed a methodology gap. The 5-step factory
   assumes Phase 5 produces ≥5 winners. When it doesn't, lifetime-
   only analysis is the fallback, but it's noticeably weaker.

---

## Files produced this session

| File | Lines | Purpose |
|---|---|---|
| `extract.py` | 312 | D1: Phase 5 + live universe extraction with thin-data assessment |
| `comparison_stats.json` | ~250 | D1 output |
| `differentiators.py` | 327 | D2: lifetime-based differentiator analysis |
| `differentiators.json` | ~600 | D2 output |
| `differentiators_llm_interpretation.md` | 60 | D2 LLM mechanism analysis |
| `filter_test.py` | 277 | D3: candidate verdict back-test |
| `filter_test_results.json` | ~300 | D3 output |
| `playbook.md` | 290 | D4: Production playbook (DEFERRED) |
| `investigation_notes.md` | (this) | D4: hypotheses, surprises, decisions |

---

## Session 1 verdict

**Cell complete; DEFERRED; ready for Bear BULL_PROXY cell next.**

Bear DOWN_TRI cell does not produce a confident production filter.
It produces:
1. A confirmed kill_001 (Bank exclusion) — defensive default
2. A provisional Verdict A filter (wk2/wk3 timing) for non-Bank
   signals — supported by lifetime data, awaiting live validation
3. A clear DEFERRED verdict with re-evaluation triggers
4. Cross-cell findings (calendar inversion vs Bear UP_TRI; HHs flag
   directional ambiguity) for Bear regime synthesis later

This is honest documentation of what the data supports — not what
we hoped to find. The cell methodology stalled on Phase-5 thinness;
lifetime data alone provides moderate evidence but can't substitute
for the winners-vs-rejected differentiation that powers stronger cells.

**Next session:** Bear BULL_PROXY cell (third and final Bear cell).
Apply 5-step methodology with same thin-data discipline.
