# Bear UP_TRI Cell

## Status

- **Investigation date:** 2026-05-02
- **Evidence base:** Phase 5 outputs — 64 VALIDATED + 23 PRELIMINARY = 87
  winners; **0 REJECTED** (100% Phase 5 validation rate); 405 WATCH for
  context.
- **Live signal universe:** 74 historical Bear UP_TRI signals (April 2026)
  → 70W / 4L / 0F → **94.6% baseline WR**.
- **Confidence level:** **HIGH for current sub-regime / LOW for universal
  Bear** — see "Risk: regime-shift fragility" below. The 94.6% live WR is
  the strongest cohort across the entire Lab, but the +38.9pp gap from
  55.7% lifetime baseline is the largest regime-shift artifact in the
  data.

---

## Setup

What market conditions create the opportunity?

- **Stock regime:** Bear (sustained downtrend; lower-highs lower-lows
  market structure)
- **Signal type:** UP_TRI (ascending triangle breakout pattern)
- **Market context:** Live data window (April 2026) is uniformly
  `nifty_vol_regime=High` (100%) and `nifty_60d_return_pct=low` for ~50%
  of winning patterns. The cell exploits a sustained stress sub-regime
  where capitulation-reversal setups overshoot to the upside on
  short-covering and exhaustion-buying.

The mechanism (synthesized from differentiator analysis + Sonnet 4.5
interpretation):

> Bear-market compression-to-breakout reversal under stress. Ascending
> triangles in Bear regimes represent forced consolidation against
> resistance while higher lows form — typically institutional accumulation
> or short-covering into defined supply. The breakout occurs when sellers
> exhaust at the apex, triggering capitulation reversal with defined risk
> (triangle base as stop). High volatility acts as catalyst, not headwind:
> bears overcommit into triangle resistance, breakout creates short-squeeze
> + FOMO entry cascade.

---

## Trigger

What activates this cell?

1. Scanner fires a UP_TRI signal on a stock
2. Stock's regime classification = Bear
3. Hold horizon recommendation: **D5 default** (Phase 4 distribution
   skews D6/D10/D15 across winners; live data is D6-dominant)

---

## Filter Conditions (the unlock)

### Headline finding: NO filter improves on the 94.6% baseline

The 6-candidate filter back-test (B3) found that all proposed filters
either reduced precision OR cut match rate without precision gain.
Skipped subsets often have HIGHER WR than matched subsets — anti-features
do NOT cleanly separate the 4 losses from the 70 winners.

| Filter | matched_wr | match_rate | skipped_wr |
|---|---|---|---|
| F1: nifty_60d_return=low | 93.8% | 43% | 95.2% |
| F6: F1 + consolidation_quality=none | 92.9% | 38% | 95.7% |
| F3: F1 + skip wk4 + skip ema_bear | 90.9% | 30% | 96.2% |
| F5: inside_bar_flag=True | 84.6% | 18% | 96.7% |
| F2: nifty_60d=low + inside_bar=True | 66.7% | 4% | 95.8% |
| F4: F2 + swing_high_low | 66.7% | 4% | 95.8% |

**Conclusion:** Bear UP_TRI in the current sub-regime is **broad-band
edge**, not narrow-band. The cell does not require a filter at the
production scanner layer — all signals can be treated as TAKE_FULL
candidates within the current sub-regime.

### Defensive sub-regime anchor (for future re-validation)

If a defensive filter is required (e.g., to detect when the cell exits
its current sub-regime), use:

- **F1: `nifty_60d_return_pct=low`** — captures 43% of winners; serves
  as a regime anchor confirming sustained Bear stress. When this feature
  no longer matches, the cell is exiting its current sub-regime and
  filter performance should be re-evaluated.

### Disqualifying conditions (provisional, NOT validated by live losses)

The B2 differentiator analysis identified anti-features (over-represented
in WATCH). These have NOT been validated against the 4 live losses (which
do not cluster on these features), so they are documented but **not
deployed as production SKIP rules**:

- `day_of_month_bucket=wk4` — 0% in winners vs 69% in WATCH (suspiciously
  large gap; likely Phase 4 selection artifact)
- `nifty_vol_regime=Medium` — never appears in winners; consistent with
  sub-regime hypothesis (current data is uniform High vol)
- `ema_alignment=bear` — never appears in winners; counter-intuitively
  rare given Bear regime — suggests winners form at inflection points,
  not within established bear continuation

---

## Evidence

| Metric | Live (April 2026, n=74) | Lifetime (15yr, n=15,151) |
|---|---|---|
| Baseline WR | **94.6%** | 55.7% |
| Live-vs-lifetime gap | +38.9pp | — |
| F1 matched WR | 93.8% (n=32) | (untested at lifetime — Session 2) |
| Phase 5 validation rate | 100% (87/87) | — |
| Phase 4 tier in winners | 45 S / 15 A / 4 B | — |

**Cross-check vs Phase 5 findings:**
- Phase 5 produced 64 VALIDATED + 23 PRELIMINARY = 87 winners
- Phase 5 baseline: 92-95% (matches our 94.6% live WR)
- Phase 4 walk-forward test_wr in winners: 72.1% (VALIDATED) / 66.4%
  (PRELIMINARY) — both above the 55.7% lifetime baseline by +10-16pp
- S-tier dominance in winners (45 of 64) is **opposite of Choppy UP_TRI**,
  where S/A all REJECTED. Bear UP_TRI rewards highest-edge backtest
  patterns — likely because Bear is the regime the scanner / analyzer
  was originally tuned to detect.

---

## Production Verdict

| Condition | Action | Sizing |
|---|---|---|
| Bear UP_TRI signal fires (any setup) | **TAKE_FULL** | full position |
| Bear UP_TRI signal fires + F1 (`nifty_60d=low`) confirms sub-regime | **TAKE_FULL** | full position |
| Bear UP_TRI signal fires but F1 fails | **TAKE_FULL with regime caveat** | full position; flag in journal that sub-regime may be shifting |
| Same name fires UP_TRI twice within 6 days | **TAKE_SMALL** | half size; first failure mode observed (OIL.NS) |
| Multiple Bear UP_TRI signals on same date | **TAKE all but cap correlation** | size each at 80% of normal to manage day-correlated risk |
| Triangle structural KILL (per analyzer KILL barcode) | **REJECT** | filter at scanner |

This is the only cell in the Lab where the production verdict is
"TAKE_FULL on essentially all signals" — reflecting Bear UP_TRI's
broad-band edge in the current sub-regime.

---

## Sample Trades (live, April 2026)

### Wins (sample — 7 of 70)

| Symbol | Date | Sector | Outcome | nifty_60d_return |
|---|---|---|---|---|
| APLAPOLLO.NS | 2026-04-01 | Metal | DAY6_WIN | low (−13%) |
| APOLLOTYRE.NS | 2026-04-01 | Auto | DAY6_WIN | low (−13%) |
| LTTS.NS | 2026-04-01 | IT | DAY6_WIN | low (−13%) |
| PAGEIND.NS | 2026-04-01 | FMCG | DAY6_WIN | low (−13%) |
| ONGC.NS | 2026-04-01 | Energy | DAY6_WIN | low (−13%) |
| BAJFINANCE.NS | 2026-04-09 | Bank | DAY6_WIN | low (−9%) |
| ADANIPORTS.NS | 2026-04-09 | Infra | DAY6_WIN | low (−9%) |

### Losses (all 4)

| Symbol | Date | Sector | ema_alignment | wk_bucket | Notes |
|---|---|---|---|---|---|
| OIL.NS | 2026-04-01 | Energy | mixed | wk1 | repeat signal — see below |
| OIL.NS | 2026-04-06 | Energy | mixed | wk1 | same name as above; failed twice |
| COROMANDEL.NS | 2026-04-09 | Chem | mixed | wk2 | day-clustered loss |
| JKCEMENT.NS | 2026-04-09 | Infra | mixed | wk2 | day-clustered loss |

**Patterns in losses:**
- All 4 have `ema_alignment=mixed` (not `bull`)
- 0 of 4 in wk4 — refutes the wk4 anti-feature hypothesis on losses
- 3 of 4 occurred on just two dates (2026-04-01, 2026-04-09) — suggests
  date-correlation risk more than feature mismatch
- OIL.NS appearing twice (both losses) — repeat-name failure mode

---

## Trader-facing narrative

### What this cell feels like mechanically

Bear UP_TRI works when the market is in sustained stress (100% High vol
regime in April) and the broader index has been bleeding for 60 days.
It's a capitulation-fade setup: you're catching the first sharp bounce
after a protracted downtrend when sellers exhaust and short-covering
ignites. The edge is *not* narrow — winners don't cluster on specific
consolidation patterns or alignment states. Instead, the cell captures
broad-band mean reversion in a bear market that's temporarily oversold
across the entire index.

### When to take the trade

Wait for the signal on a day when Nifty 60-day return is deeply negative
(low bucket) and volatility regime reads High. The inside bar flag
(present in 18% of winners at 85% WR) is a useful geometric confirmation
but not required — most winners fire without it. Avoid overthinking EMA
alignment or consolidation quality; in this regime, mixed/poor technical
structure is the norm and does not predict failure. Take the signal if
the macro backdrop is stress and the 60-day chart is ugly.

### When to be cautious / size down

Cut size on repeat signals in the same name within a tight window (OIL.NS
lost twice in 6 days, both on `ema_alignment=mixed`). Be wary of Energy
and Chemicals if they've already had a recent failed bounce — sector-
specific exhaustion may override index-level edge. If a signal fires on
a date when multiple other Bear UP_TRI trades are live, consider
correlation risk; two of four losses occurred on the same day (April 9).
Don't add size just because the cell is hot — regime edges compress fast.

### Risk: regime-shift fragility

The 94.6% win rate is a *regime artifact*, not a structural edge. April's
100% High vol environment created uniform conditions that the cell
exploited; lifetime WR of 55.7% reflects normal mixed-regime noise. When
vol regime shifts back to Medium or Low, or when Nifty exits the 60-day
drawdown zone, this cell will revert to coin-flip odds. The +38.9pp gap
is the largest in the Lab — it will mean-revert hard. Trade it now, but
assume it expires when macro stress eases.

### Exit discipline

Default hold is 3–5 days for the initial mean-reversion pop; bear rallies
are fast and shallow. Trail stops under the signal-day low or the prior
swing low, whichever is tighter. If the stock reclaims its 20-day EMA,
take profit — bear UP_TRI is a bounce trade, not a reversal trade. Exit
immediately if Nifty vol regime downgrades to Medium mid-trade; the
regime that created the edge is gone.

*— Mechanism narrative synthesized via Claude Sonnet 4.5 from cell findings*

---

## Investigation Notes

### What worked

1. **Phase 5 validation was uniform** — 87 of 87 evaluable patterns
   validated. No discrimination signal at the patterns layer.
2. **Live universe is broadly winning** — 70 of 74 signals won across 11
   sectors with no clear sector concentration. Auto, Bank, IT, FMCG,
   Other, Pharma, Health all 100% WR.
3. **`nifty_60d_return_pct=low` is the dominant winner anchor** —
   appears in 53% of winners vs 0.5% of WATCH (+52pp differentiator). It
   confirms the mechanism (sustained Bear stress) and serves as the
   defensive sub-regime anchor.
4. **Phase 4 S-tier dominance in winners** — opposite of Choppy UP_TRI,
   where S/A all REJECTED. Bear UP_TRI is the regime the scanner was
   structurally tuned for.

### What was unexpected

1. **No filter improves on 94.6% baseline.** Initial expectation was a
   2-3 feature filter would emerge analogous to Choppy F1; instead, the
   cell is broad-band — losses scatter evenly across all candidate
   filter splits.
2. **Anti-features don't validate against losses.** B2 surfaced
   `day_of_month_bucket=wk4` as a 69pp anti-feature signal, but 0 of the
   4 live losses occurred in wk4. The wk4 signal is likely a Phase 4
   selection artifact, not a real production rule.
3. **3 of 4 losses cluster on 2 dates.** Date-correlation risk emerged
   as a stronger production concern than feature-based filter
   discrimination.
4. **OIL.NS lost twice in 6 days.** Repeat-name failure mode is novel —
   not previously seen in Choppy cells.

### What was disappointing

1. **No actionable filter for production scanner.** Cell verdict is "no
   filter discrimination available at current data" — which is honest but
   provides less production value than a Choppy F1-style filter would.
2. **+38.9pp regime-shift gap is alarming.** The largest in the Lab.
   Lifetime validation in Session 2 will likely surface significant
   weakening; cell may need to be re-classified as regime-shift adaptive.
3. **94.6% is too high to discriminate.** With only 4 losses across 74
   signals, statistical separation isn't possible at this n. Cell needs
   another 100-200 live signals across multiple sub-regimes to surface
   internal structure.

### Open questions for future investigation

1. Does the cell sustain 90%+ WR across 100+ additional Bear UP_TRI
   signals in 2026-Q3+, or does WR collapse toward lifetime 55.7% as
   sub-regime evolves?
2. What does a "Medium-vol Bear" or "Low-vol Bear" sub-regime look
   like, and what's the cell's WR in those conditions?
3. The 4 losses all have `ema_alignment=mixed` — but so do 50%+ of the
   70 winners. Is there a *secondary* feature that distinguishes
   mixed-EMA winners from mixed-EMA losers?
4. OIL.NS lost twice — does the cell have a "second-attempt" failure
   mode, where a stock that fails its first Bear UP_TRI is more likely
   to fail subsequent attempts within a tight window?
5. Bear UP_TRI Phase 4 walk-forward edge was +13-19pp. Why does live
   produce +38.9pp lift over lifetime baseline? Is this current April
   2026 a "hot" sub-regime, or did Phase 4 train_wr underestimate the
   true Bear UP_TRI edge?

### Data gaps that limit confidence

- Live universe is exclusively April 2026 (single regime sub-character)
- 74 signals → only 4 losses → wide CIs on per-feature loss-cluster
  inference
- All 74 signals are `nifty_vol_regime=High`; can't validate filter on
  Medium/Low vol cohorts
- Sector concentration of losses (3 of 4 in Energy/Chem/Infra) too small
  to call sector mismatch rules

---

## Lifetime Validation (Session 2 — added 2026-05-02 night)

**Session 1's broad-band finding HOLDS in current sub-regime; lifetime
data confirms sub-regime structure and surfaces filter cascade for cold
sub-regime.** Authoritative source:
[`lifetime/synthesis.md`](lifetime/synthesis.md).

### Key lifetime findings

1. **Lifetime baseline 55.7% confirmed** (predicted, exact). Live-vs-
   lifetime gap +38.9pp confirmed as largest in Lab.

2. **Bear is BIMODAL, not tri-modal** (different from Choppy):
   - stress (43%) + balance (34%) dominate; quiet ~1%
   - Hot sub-regime (vol_percentile > 0.70 AND nifty_60d_return < −0.10):
     15% of lifetime, 68.3% WR (+14.9pp over cold's 53.4%)

3. **Live's 94.6% mostly Phase-5 selection bias.** Even within the hot
   sub-regime, lifetime is 68.3% — not 94.6%. The 26pp residual gap
   reflects Phase 5 picking the best patterns within the favorable
   sub-regime, plus an "extra hot within hot" April 2026 condition.

4. **F1 (nifty_60d=low) CONFIRMED at lifetime** as a modest filter:
   matched n=2,436 (16%), WR=67.4%, lift +11.8pp.

5. **B2 anti-features REFUTED at lifetime** (same Choppy V2 lesson):
   - `wk4`: predicted anti, lifetime is +10.5pp WINNER (Phase 4
     selection artifact — analyzer's combinatorial search excluded wk4
     entries from surviving combinations)
   - `ema_alignment=bear`: similarly inverted (+3.9pp at lifetime)
   - Production should NOT use any of B2's anti-features as SKIP rules.

6. **Filter cascade for cold sub-regime** surfaced from L2 combinatorial
   search:
   - PRIMARY:   `wk4 AND swing_high_count_20d=low` — 63.3% WR, n=3,845, +7.6pp
   - SECONDARY: `breadth=low AND ema50_slope=low AND swing_high=low` — 61.8%, n=4,555, +6.2pp
   - TERTIARY:  `wk4` alone — ~63% WR
   - Without filter, cold sub-regime collapses to 53% WR.

7. **WATCH patterns are GENUINELY weaker** (refutes S1 prediction):
   lifetime test_wr 65.0% vs VALIDATED 72.1% (Δ +7.1pp). Phase 5
   discrimination is real even within the 100% validation cohort.

### Revised production posture (v1.1)

#### When in hot sub-regime (current April 2026 condition)

| Condition | Action | Sizing |
|---|---|---|
| Bear UP_TRI signal in hot sub-regime | **TAKE_FULL** | full position |
| Repeat name within 6 days | TAKE_SMALL | half (S1 trader heuristic) |
| 3+ same-day Bear UP_TRI signals | 80% sizing | day-correlation cap |

#### When sub-regime exits hot (deployment-ready cascade)

Sub-regime detection (production gating):
```python
def is_hot_bear(nifty_vol_percentile_20d, nifty_60d_return_pct):
    return (nifty_vol_percentile_20d > 0.70
            and nifty_60d_return_pct < -0.10)
```

| Condition (NOT hot) | Action | Lifetime evidence |
|---|---|---|
| `wk4 AND swing_high_count_20d=low` matches | TAKE_FULL | 63.3% WR, n=3845 |
| `breadth=low AND ema50_slope=low AND swing_high=low` matches | TAKE_SMALL | 61.8% WR, n=4555 |
| `wk4` matches (no other match) | TAKE_SMALL | ~63% WR |
| No filter match | **SKIP** | ~53% WR; edge collapses |

#### Expected behavior when sub-regime exits hot

| Transition | Expected WR |
|---|---|
| Vol drops to Medium/Low, returns stay negative | 54-56% |
| Returns recover to flat/positive, vol stays high | 50-53% (false Bear) |
| Both degrade together | 50-52% (Bear regime ending) |

### Confidence delta

| Finding | S1 (live) | S2 (lifetime-validated) |
|---|---|---|
| 94.6% WR in current sub-regime | HIGH | HIGH (sub-regime gated) |
| 94.6% as universal Bear edge | LOW | **REFUTED** |
| F1 as filter anchor | UNCLEAR | **CONFIRMED** (+11.8pp lifetime) |
| `wk4` is anti-feature | flagged April-specific | **REFUTED — wk4 is winner anchor** |
| `ema_alignment=bear` is anti | live n.s. | **REFUTED — winner anchor** |
| Hot sub-regime exists | hypothesized | CONFIRMED (15% lifetime, +14.9pp) |
| Bear is multi-modal | hypothesized | CONFIRMED bimodal |
| Filter cascade required for cold | not surfaced | NEW — 3-tier cascade |

---

## Update Log

- **v1 (2026-05-02 night):** Initial cell investigation. 87 winners /
  0 rejected / 405 watch. Live 94.6% WR, +38.9pp gap from lifetime
  55.7% baseline. NO filter improves baseline — cell verdict is
  TAKE_FULL on all signals within current sub-regime. F1
  (`nifty_60d_return_pct=low`) reserved as defensive sub-regime anchor.
  Major risk: regime-shift fragility flagged for Session 2 lifetime
  validation.

- **v1.1 (2026-05-02 night, Session 2):** Lifetime validation confirms
  Session 1 broad-band finding is sub-regime-specific. Bear is BIMODAL
  (not tri-modal). Hot sub-regime: 15% of lifetime, 68.3% WR (+14.9pp);
  current April 2026 is 100% hot. Live's 94.6% mostly Phase-5 selection
  bias on top of hot sub-regime. F1 CONFIRMED at lifetime (+11.8pp).
  B2 anti-features REFUTED (wk4 is actually a +10.5pp winner). Filter
  cascade designed for cold sub-regime: wk4 × swing_high=low (63.3%) →
  breadth=low × ema50=low × swing=low (61.8%) → wk4 alone (~63%) → SKIP.
  Sub-regime detection logic added (`is_hot_bear()`). Confidence delta
  table added. See `lifetime/synthesis.md`.
