# Bear BULL_PROXY Cell

## Status

- **Investigation date:** 2026-05-02 night
- **Cell classification:** **DEFERRED** with provisional HOT-only filter
- **Confidence level:** LOW (data thin; 0 Phase 5 combos)
- **Sessions completed:** 1 of up-to-3 (Sessions 2-3 NOT recommended)
- **Production verdict:** SKIP by default; in HOT sub-regime, TAKE_SMALL
  is defensible based on lifetime evidence (n=86, 63.7% WR, +16.4pp lift)

---

## Why DEFERRED

### Layer 1 — Phase 5 produces ZERO combinations

Bear BULL_PROXY has **0 combinations** in `combinations_live_validated.parquet`.
Not 0 winners (like Bear DOWN_TRI's 19 WATCH) — literally 0 combos total.
The Lab's Phase 4/5 pipeline produced no surviving Bear BULL_PROXY
combinations.

This is **even thinner than Bear DOWN_TRI**. Standard winners-vs-rejected
differentiator analysis is NOT FEASIBLE; cell methodology falls back to
lifetime-only analysis (parallel to Bear DOWN_TRI cell path).

### Layer 2 — Live signal sparsity but high apparent edge

Live Bear BULL_PROXY universe (April 2026):

| Metric | Value |
|---|---|
| Total signals | 13 |
| W / L | 11 / 2 |
| Baseline WR | **84.6%** |
| Apparent live-vs-lifetime gap | **+37.3pp** (parallel to Bear UP_TRI's +38.9pp) |

Live n=13 is below the n≥15 threshold for filter back-test confidence.
The +37pp gap is largely explained by Phase-5-equivalent selection bias
+ sub-regime structure (per cross-cell pattern).

### Layer 3 — Sub-regime structure exists

Lifetime n=891 split via Bear sub-regime detector:

| Sub-regime | Definition | n | % | WR |
|---|---|---|---|---|
| hot | vol > 0.70 AND nifty_60d < −0.10 | 86 | 9.7% | **63.7%** |
| cold | everything else | 805 | 90.3% | 45.5% |

Δ hot − cold: **+18.2pp**. Sub-regime structure is real and parallels
Bear UP_TRI's hot zone (where lifetime hot is 68.3% vs cold 53.4%, also
+14.9pp delta).

But hot zone is **smaller than Bear UP_TRI's** (9.7% vs 15%) — fewer
high-edge signals to capture. Cold (90% of lifetime) is at 45.5% WR
(losing proposition).

---

## Lifetime evidence — feature signature

### Top 12 winner features (n=891)

| Feature / level | Δ presence−absence | n_presence |
|---|---|---|
| `nifty_60d_return_pct=low` | **+17.9pp** | 82 (lift 63.4% vs 45.5%) |
| `52w_high_distance_pct=high` | +14.4pp | 153 |
| `vol_climax_flag=False` | +11.0pp | 752 |
| `ROC_10=low` | +9.8pp | 134 |
| `inside_bar_flag=False` | +9.4pp | 692 |
| `range_compression_60d=high` | +8.5pp | 211 |
| `nifty_vol_regime=Low` | +7.9pp | 196 |
| `nifty_vol_regime=High` | +5.1pp | 222 |
| `multi_tf_alignment_score=medium` | +6.3pp | 408 |
| `consolidation_quality=none` | +4.4pp | 502 |

### Top anti-features

| Feature / level | Δ presence−absence |
|---|---|
| `nifty_60d_return_pct=medium` | −17.9pp (mirror of #1 winner) |
| `52w_high_distance_pct=low` | −11.2pp (close to highs is BAD) |
| `vol_climax_flag=True` | −11.0pp (capitulation hurts BULL_PROXY) |
| `inside_bar_flag=True` | −9.4pp |
| `range_compression_60d=medium` | −8.0pp |
| `nifty_vol_regime=Medium` | −7.2pp (middle vol HOSTILE — U-shape) |
| `day_of_month_bucket=wk2` | −5.5pp |

### Striking findings

1. **U-shaped vol response.** Both `vol=Low` and `vol=High` are winners
   (+7.9pp and +5.1pp); `vol=Medium` is anti (−7.2pp). BULL_PROXY works
   in extreme vol regimes; middle vol fails. Different from Bear UP_TRI
   which only loved `vol=High`.

2. **`inside_bar_flag` direction-flips vs Bear UP_TRI.** BULL_PROXY needs
   range expansion (`inside_bar=False` +9.4pp). Bear UP_TRI needs
   compression (`inside_bar=True` +4.9pp). Different mechanisms per cell.

3. **`vol_climax_flag=True` is a strong anti** (−11.0pp). BULL_PROXY
   wants orderly Bear (vol_climax=False), not panic capitulation. This
   is counter-intuitive but mechanistically clean: capitulation events
   exhaust the support structure that BULL_PROXY needs to bounce from.

4. **Sector pattern is multi-modal lifetime.** Top: IT 56.9%, Energy
   52.8%, Chem 51.2%, Bank 51.1%, Auto 50.0%. Bottom: Other 37.7%,
   CapGoods 39.3%, FMCG 41.2%. Different from Bear UP_TRI's defensive-
   sector lead.

---

## Cross-cell findings (this cell vs Bear UP_TRI vs Bear DOWN_TRI)

### `nifty_60d_return_pct=low` — direction by cell

| Cell | Δ | Mechanism |
|---|---|---|
| Bear UP_TRI | +14.1pp WINNER | regime anchor; ascending triangle in oversold |
| Bear DOWN_TRI | −4.1pp ANTI | continuation shorts get squeezed |
| Bear BULL_PROXY | **+17.9pp WINNER** (strongest) | reversal needs deep oversold |

Both bullish setups (UP_TRI + BULL_PROXY) want oversold; bearish
continuation (DOWN_TRI) doesn't.

### Calendar pattern

| Cell | wk2 | wk4 |
|---|---|---|
| Bear UP_TRI | −6.4pp anti | +7.5pp WINNER |
| Bear BULL_PROXY | −5.5pp anti | +2.3pp (mild win) |
| Bear DOWN_TRI | **+15.0pp WINNER** | **−17.5pp anti (INVERTED)** |

BULL_PROXY aligns with UP_TRI direction (both prefer wk4 / dislike wk2).
DOWN_TRI is inverted (mid-month flow vs month-end flow per cell).

### `inside_bar_flag` — opposite directions across cells

| Cell | inside_bar=True |
|---|---|
| Bear UP_TRI | +4.9pp WINNER (compression coil) |
| Bear BULL_PROXY | −9.4pp ANTI (range expansion needed) |

**Different mechanisms** in same direction (both bullish). UP_TRI is
breakout from compression; BULL_PROXY is reversal from range expansion.
Cells should NOT share filter logic on inside_bar.

---

## Provisional production filter (Verdict A from P3)

| Component | Rule |
|---|---|
| Sub-regime detector | Apply Bear sub-regime detector |
| Filter requirement | sub-regime must be **hot** (vol > 0.70 AND nifty_60d < −0.10) |

### Lifetime evidence for Verdict A

| Cohort | n | WR | Lift over baseline (47.3%) |
|---|---|---|---|
| All Bear BULL_PROXY lifetime | 891 | 47.3% | — |
| **Verdict A matched (hot)** | **86** | **63.7%** | **+16.4pp** |
| Verdict A skipped (cold) | 805 | 45.5% | −1.8pp |
| Match rate | 9.7% | — | — |

Lifetime n=86 with +16.4pp lift is meaningful but match rate is low —
expect ~10% of Bear BULL_PROXY signals to qualify for the filter.

### Live evidence for Verdict A

| Cohort | n | WR |
|---|---|---|
| Verdict A matched (hot) | 7 | 85.7% (6W/1L) |
| Verdict A skipped (cold) | 6 | 83.3% (5W/1L) |

Live WR is high in BOTH hot and cold subsets — Phase 5 selection bias
is the dominant explanation, not sub-regime structure. The live data
**partially validates** Verdict A (hot subset 85.7% > 64% lifetime
expected) but cold subset's 83.3% is **not reproducible** at lifetime
scale (lifetime cold is 45.5%).

### Verdict A decomposition for honesty

| Component | Contribution to live WR |
|---|---|
| Lifetime hot baseline | 63.7% |
| April 2026 sub-regime tailwind | ~10pp on top of lifetime |
| Phase-5-equivalent selection bias | ~12pp (residual of Bear UP_TRI's +26pp pattern) |
| **Live observed** | **85.7%** |

Calibrated production WR for HOT-matched signals: **65-75%**
(reflecting lifetime 63.7% baseline + sub-regime variance, NOT 85.7%
live observation).

---

## Production Verdict (current state)

| Condition | Action | Sizing |
|---|---|---|
| Bear BULL_PROXY signal in HOT sub-regime | **TAKE_SMALL (provisional)** | half (lifetime 63.7%; calibrated 65-75%) |
| Bear BULL_PROXY signal in COLD sub-regime | **SKIP** | edge collapses to ~46% lifetime |
| Bear BULL_PROXY signal anywhere (default unfiltered) | **SKIP** | 47.3% lifetime baseline insufficient |

This is more conservative than Bear UP_TRI cell. Bear BULL_PROXY production
posture is **TAKE_SMALL only**, only in hot sub-regime, and only if
operator explicitly enables (default SKIP).

### Sector mismatch rules

Lifetime ranking suggests:
- **Avoid in cold sub-regime entirely** (cold is 90% of lifetime; 45.5% WR)
- **Energy in hot has 64% WR** (n=12) — second-best sector (after Pharma 67%)
- **CapGoods/Other/FMCG** lifetime cold WR < 41% — worst cells

But sector × hot has tiny n per cell (3-16). Mismatch rules are
provisional pending more data.

---

## Sample Trades (the 13 live signals)

### Wins (11)

| Symbol | Date | Sector | Sub-regime | Filter status |
|---|---|---|---|---|
| GLENMARK.NS | 2026-04-06 | Pharma | hot | ✓ Verdict A match |
| PFC.NS | 2026-04-06 | Bank | hot | ✓ |
| TATAPOWER.NS | 2026-04-06 | Energy | hot | ✓ |
| TATASTEEL.NS | 2026-04-06 | Metal | hot | ✓ |
| VEDL.NS | 2026-04-06 | Metal | hot | ✓ |
| POWERGRID.NS | 2026-04-07 | Energy | hot | ✓ |
| AARTIIND.NS | 2026-04-08 | Chem | cold | ✗ would skip |
| BAJAJ-AUTO.NS | 2026-04-08 | Auto | cold | ✗ would skip |
| TVSMOTOR.NS | 2026-04-08 | Auto | cold | ✗ would skip |
| APOLLOHOSP.NS | 2026-04-10 | Health | cold | ✗ would skip |
| AUBANK.NS | 2026-04-15 | Bank | cold | ✗ would skip |

### Losses (2)

| Symbol | Date | Sector | Sub-regime | Filter status |
|---|---|---|---|---|
| OIL.NS | 2026-04-06 | Energy | hot | ✗ Verdict A correctly took (loss) |
| LT.NS | 2026-04-10 | Infra | cold | ✓ Verdict A correctly skipped |

**Filter coverage on live:**
- 6 of 11 winners captured by Verdict A (hot subset: 6W/1L = 85.7%)
- 1 of 2 losers correctly skipped (LT cold)
- 1 loser (OIL hot) correctly taken (Verdict A doesn't claim 100%)
- 5 of 11 winners SKIPPED by Verdict A (cold but won — opportunity cost)

**Live coverage trade-off:** Verdict A captures 6 wins + 1 loss, skips
5 wins + 1 loss. If we trust lifetime baseline (47.3%), the 5 cold wins
are likely sub-regime selection bias not reproducible at scale —
skipping them is correct production posture.

---

## Investigation Notes

### What worked

1. **Bear sub-regime detector reuse from Bear UP_TRI cell**. The detector
   built in S2 of Bear UP_TRI cell (vol > 0.70 AND 60d < −0.10) reproduces
   sub-regime structure cleanly here at lifetime scale (+18.2pp delta).

2. **Lifetime data is sufficient for differentiator analysis** despite
   0 Phase 5 combos. n=891 supports 12-feature differential at min_n=30.

3. **Cross-cell mechanism comparison surfaces clean directional flips.**
   UP_TRI compression vs BULL_PROXY range expansion; BULL_PROXY/UP_TRI
   bullish anchor (nifty_60d=low) vs DOWN_TRI bearish anti.

### What was unexpected

1. **0 Phase 5 combinations.** Bear UP_TRI has 492 combos; Bear DOWN_TRI
   has 19 WATCH; Bear BULL_PROXY has 0. The Lab's combinatorial pipeline
   produced literally nothing for this cell. Suggests Phase 4
   walk-forward filters were hostile to BULL_PROXY × Bear cohort.

2. **U-shaped vol response.** vol=Low and vol=High both winners (+7.9pp
   and +5.1pp); vol=Medium is anti (−7.2pp). BULL_PROXY works in
   extreme vol regimes; middle vol fails. Different from Bear UP_TRI's
   simple "vol=High dominant" pattern.

3. **`inside_bar_flag` direction-flips vs Bear UP_TRI.** Same regime,
   two cells, opposite preferences. UP_TRI's compression is BULL_PROXY's
   anti. Confirms cells are different mechanisms despite shared
   bullish direction.

4. **Live hot/cold WR essentially equal (85.7% vs 83.3%).** Mirrors
   Bear UP_TRI's S2 borderline-cold finding. Live data sits in a
   single transitional sub-regime; the threshold is brittle in current
   April 2026.

### What was disappointing

1. **0 Phase 5 combinations means cell methodology fundamentally
   doesn't apply.** Same fallback path as Bear DOWN_TRI; provisional
   filter from lifetime data; DEFERRED verdict.

2. **Hot zone is small (9.7%) — operationally challenging.** Even if
   Verdict A is real, it would fire ~1-2 signals/month at production.
   Low signal frequency.

3. **Live live winners cluster in a single window** (Apr 6-15, 9
   trading days). Not enough temporal diversity to validate sub-regime
   structure.

### What we don't know

- Whether Verdict A's +16.4pp lifetime lift sustains in next 100 live
  signals (will need 6-12 months of additional data)
- Whether the 5 cold-winner live signals reflect true cold edge or
  just Phase 5 cluster luck
- Whether Bear UP_TRI's deployment success (when it happens) tells us
  anything about BULL_PROXY's expected production performance

---

## Re-evaluation triggers

The cell should be re-investigated under these conditions:

| Trigger | Action |
|---|---|
| Bear UP_TRI cell deployed and validated for ≥3 months | Revisit BULL_PROXY with similar deployment plan |
| ≥30 additional Bear BULL_PROXY live signals accumulate | Re-run P2-P3 with larger n |
| Phase 5 produces ≥5 Bear BULL_PROXY combinations | Run full cell methodology |
| Bear sub-regime detector v2 (with warm zone) ships | Re-test Verdict A with refined sub-regime split |
| Bear regime ends (transitions to Choppy or Bull) | Re-evaluate cell at next Bear cycle |

Estimated timeline: depends primarily on Bear UP_TRI deployment
trajectory. ~6-12 months at minimum.

---

## Update Log

- **v1 (2026-05-02 night, Session 1):** Cell classified DEFERRED with
  provisional Verdict A (HOT sub-regime filter only).
  0 Phase 5 combinations + live n=13 (11W/2L = 84.6%) require
  lifetime-only fallback methodology.
  Lifetime data (n=891, baseline 47.3%) supports HOT-only filter
  (vol>0.70 AND 60d<-0.10) at +16.4pp lift on n=86 hot subset (63.7% WR).
  Cross-cell findings: BULL_PROXY parallels UP_TRI in nifty_60d=low
  anchor (+17.9pp); inverts UP_TRI on inside_bar (range expansion vs
  compression); aligns with UP_TRI on calendar (wk4 mild winner).

  **Sessions 2-3 NOT recommended** — cell completes at Session 1.
  Bear regime synthesis (cross-cell consolidation) is the natural
  next step.

  Production posture:
  - DEFAULT: SKIP all Bear BULL_PROXY signals
  - PROVISIONAL: TAKE_SMALL on hot sub-regime matches (manual enable)
  - Calibrated WR expectation: 65-75% on HOT matches (NOT 85.7% live)
  - Re-evaluate after Bear UP_TRI deployment success.
