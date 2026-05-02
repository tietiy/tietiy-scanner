# Bear DOWN_TRI Cell

## Status

- **Investigation date:** 2026-05-02 night
- **Cell classification:** **DEFERRED** with provisional filter
- **Confidence level:** LOW (data thin; no Phase 5 winners)
- **Sessions completed:** 1 of up-to-3 (Sessions 2-3 NOT recommended;
  cell completes at S1 with DEFERRED verdict)
- **Production verdict:** Maintain kill_001 (Bank exclusion); apply
  PROVISIONAL wk2/wk3 timing filter for non-Bank signals; otherwise
  default to TAKE_SMALL or SKIP

---

## Why DEFERRED

Standard 4-step methodology hits two layers of insufficient evidence:

### Layer 1 — Phase 5 produces 0 winners

| Phase 5 tier | Count |
|---|---|
| VALIDATED | 0 |
| PRELIMINARY | 0 |
| REJECTED | 0 |
| **WATCH** | **19** |

All 19 Phase-4 surviving Bear DOWN_TRI combinations land in WATCH
because none accumulate sufficient live matches. The standard winners-
vs-rejected differentiator analysis used in Bear UP_TRI cell is NOT
FEASIBLE here — there are no winners to differentiate.

### Layer 2 — Live signal sparsity

Live Bear DOWN_TRI universe in current data window (April 2026):

| Metric | Value |
|---|---|
| Total signals | 11 |
| W / L | 2 / 9 |
| Baseline WR | **18.2%** |
| Bank sector signals | 6 (kill_001 cohort, 0 wins) |
| Non-Bank signals | 5 (2 wins, 3 losses → 40% WR) |

Live n=11 is below the n≥15 threshold for filter back-test. The 2
winners (IPCALAB Pharma, VINATIORGA Chem) both fired the same date
(2026-04-06) — no temporal diversity for pattern inference.

### Layer 3 — INVERTED live-vs-lifetime gap

| Metric | Value |
|---|---|
| Live WR | 18.2% |
| Lifetime WR (n=3,640) | **46.1%** |
| Gap | **−28.0pp (live worse than lifetime)** |

This is the OPPOSITE direction of Bear UP_TRI's +38.9pp inflation.
Mechanism per Sonnet 4.5: Bear UP_TRI's Phase-5 winners reflect
selection bias inflating live above lifetime; Bear DOWN_TRI has no
Phase-5 winners, so live data is **unfiltered raw signal output**
hitting unfavorable current sub-regime. The 2 live wins might be the
only Bear DOWN_TRI signals that happened to align with the lifetime
edge conditions in April 2026.

---

## Lifetime evidence (alternative analysis path)

Despite Phase-5 thinness, lifetime data (n=3,640) provides moderate
evidence for cell mechanism + filter design.

### Lifetime sector ranking

| Sector | n | WR |
|---|---|---|
| Pharma | 328 | 52.2% (top) |
| Health | 75 | 52.2% |
| Other | 214 | 51.8% |
| Chem | 316 | 49.1% |
| FMCG | 356 | 47.5% |
| IT | 286 | 47.5% |
| Infra | 254 | 46.9% |
| Bank | 653 | 45.0% |
| CapGoods | 231 | 44.2% |
| Metal | 284 | 41.4% |
| Energy | 340 | 40.7% |
| Auto | 276 | 40.4% (worst) |

Defensives lead; cyclicals lag. Bank is in middle, not extreme — the
0/6 live failure is a current sub-regime artifact, not a structural
Bank rejection. kill_001 stays valid based on live evidence, but
lifetime gap is only +1.3pp non-Bank vs Bank (not dramatic).

### Lifetime feature differential (D2 finding)

Top winner features at lifetime (vs absence WR):

| Feature / level | Δ presence−absence | n_presence |
|---|---|---|
| `day_of_month_bucket=wk2` | **+15.0pp** | 1,012 |
| `day_of_month_bucket=wk3` | +6.7pp | 654 |
| `nifty_60d_return_pct=medium` | +4.1pp | 850 |
| `higher_highs_intact_flag=True` | +4.0pp | 566 |
| `RSI_14=medium` | +2.6pp | 1,200 |
| `nifty_vol_regime=High` | +2.1pp | 1,745 |

Top anti-features at lifetime:

| Feature / level | Δ presence−absence | n_presence |
|---|---|---|
| `day_of_month_bucket=wk4` | **−17.5pp** | 720 |
| `nifty_vol_regime=Low` | −9.8pp | 580 |
| `day_of_week=Mon` | −4.4pp | 720 |
| `nifty_60d_return_pct=low` | −4.1pp | 880 |

**Striking inversion vs Bear UP_TRI:**
- Bear UP_TRI: `wk4` was +7.5pp WINNER, `wk2` was −6.4pp anti
- Bear DOWN_TRI: `wk4` is −17.5pp ANTI, `wk2` is +15.0pp WINNER
- Same regime, opposite calendar profiles. Likely different
  institutional flow patterns drive each direction.

**Counterintuitive finding:** `higher_highs_intact_flag=True` is a
+4.0pp WINNER for Bear DOWN_TRI. Mechanism: stocks with HHs intact +
descending triangle = building distribution top, perfect short setup.
(Was −10.9pp anti-feature for Choppy UP_TRI — same flag, opposite
meaning across cells.)

---

## Provisional production filter (Verdict A from D3)

| Component | Rule |
|---|---|
| Sector exclusion | kill_001 — exclude Bank |
| Calendar filter | Skip wk1 and wk4 — keep ONLY wk2 and wk3 |

### Lifetime evidence for Verdict A

| Cohort | n | WR | Lift over baseline |
|---|---|---|---|
| All Bear DOWN_TRI lifetime | 3,640 | 46.1% | — |
| **Verdict A matched** | **1,446** | **53.6%** | **+7.5pp** |
| Verdict A skipped | 2,194 | 41.3% | −4.8pp |
| Match rate | 39.7% | — | — |

39.7% match rate × +7.5pp lift × n=1,446 = robust lifetime evidence.

### Live evidence for Verdict A

| Cohort | n | WR |
|---|---|---|
| Verdict A matched | 1 | (n too thin to evaluate) |
| Verdict A skipped | 10 | 20.0% |

Live data does NOT validate or refute Verdict A — only 1 of 11 live
signals matches the filter. This confirms DEFERRED status: lifetime
supports the filter, live can't yet validate.

---

## Production Verdict (current state)

| Condition | Action | Sizing |
|---|---|---|
| Bear DOWN_TRI signal in **Bank** sector | **REJECT** | kill_001 |
| Bear DOWN_TRI signal NOT in Bank, week=wk2 or wk3 | **TAKE_SMALL** | half (provisional filter; not yet live-validated) |
| Bear DOWN_TRI signal NOT in Bank, week=wk1 or wk4 | **SKIP** | — |
| Bear DOWN_TRI signal in any sector with mismatch | SKIP | sector mismatch (Auto/Energy/Metal weakest at lifetime) |

This is more conservative than Bear UP_TRI cell. Bear DOWN_TRI
production posture is **TAKE_SMALL at most** until Session 2 lifetime
validation has Phase-5 evidence to consult.

---

## Sample Trades (the 11 live signals)

### The 2 winners

| Symbol | Date | Sector | Day-of-week | Week | Outcome | ema_alignment | MACD_signal |
|---|---|---|---|---|---|---|---|
| IPCALAB.NS | 2026-04-06 | Pharma | Mon | wk1 | DAY6_WIN | mixed | bear |
| VINATIORGA.NS | 2026-04-06 | Chem | Mon | wk1 | DAY6_WIN | bear | bear |

Both winners fired Mon wk1 — wk2/wk3 filter would have SKIPPED both.
Both in defensive sectors (Pharma, Chem) — top-ranked lifetime sectors.
Both with MACD_signal=bear and MACD_histogram_slope=falling (proper
short setup confirmation).

### The 9 losers

| Symbol | Date | Sector | Outcome | Why filtered |
|---|---|---|---|---|
| ADANIGREEN.NS | 2026-04-06 | Energy | STOP_HIT | Mon wk1 (would skip) |
| BSE.NS | 2026-04-06 | Bank | STOP_HIT | Bank — kill_001 |
| JIOFIN.NS | 2026-04-06 | Bank | DAY6_LOSS | Bank — kill_001 |
| MCX.NS | 2026-04-06 | Bank | STOP_HIT | Bank — kill_001 |
| MUTHOOTFIN.NS | 2026-04-06 | Bank | STOP_HIT | Bank — kill_001 |
| PFC.NS | 2026-04-06 | Bank | STOP_HIT | Bank — kill_001 |
| VGUARD.NS | 2026-04-06 | Other | DAY6_LOSS | Mon wk1 (would skip) |
| MANAPPURAM.NS | 2026-04-07 | Bank | DAY6_LOSS | Bank — kill_001 |
| TATAPOWER.NS | 2026-04-08 | Energy | STOP_HIT | Wed wk2 (filter would TAKE_SMALL) |

**Filter coverage on live:**
- 6 of 9 losers correctly filtered out by kill_001 (Bank)
- 2 of 9 correctly filtered by wk1 timing (Energy ADANIGREEN, Other VGUARD)
- 1 of 9 NOT filtered (TATAPOWER Energy wk2 — would be TAKE_SMALL → loss)
- BUT wk2/wk3 filter would also have skipped BOTH WINNERS (Mon wk1)

So Verdict A on live: 0 wins captured / 1 loss captured = 0% matched
WR on n=1. Live filter coverage is structurally compromised because
all 11 signals fired in a 3-day window (Apr 6-8), giving no temporal
diversity. **Live is anecdotal, not statistical evidence.**

---

## Investigation Notes

### What worked

1. **kill_001 (Bank exclusion) is confirmed** — live 0/6 Bank wins +
   lifetime +1.3pp non-Bank vs Bank gap (modest but consistent).

2. **Lifetime data is rich (n=3,640)** — provides solid statistical
   foundation despite Phase-5 thinness. Verdict A timing filter has
   strong lifetime support (+7.5pp on n=1,446).

3. **Calendar inversion vs Bear UP_TRI is genuine**: same regime,
   opposite calendar profiles (Bear UP_TRI loves wk4, Bear DOWN_TRI
   loves wk2). Two cells, two directions, two timing patterns.

4. **Defensive sector preference at lifetime** (Pharma/Health/Other
   lead) matches both live winners (Pharma + Chem).

### What was unexpected

1. **0 Phase 5 winners.** Bear UP_TRI had 87 winners; Bear DOWN_TRI
   has 0. Suggests scanner combination generation favored
   parameter sets that don't accumulate live matches in current
   sub-regime.

2. **`higher_highs_intact_flag=True` is +4pp WINNER** — counterintuitive
   for a short setup. Same flag was −10.9pp anti for Choppy UP_TRI.
   Cross-cell comparison surfaces flag's directional ambiguity.

3. **Live INVERTS vs lifetime** (−28pp) — opposite direction of every
   prior cell's gap. Without Phase-5 selection bias inflating live, raw
   signal output hits unfavorable conditions.

4. **`nifty_60d_return_pct=low` is ANTI** for DOWN_TRI but was the
   F1 anchor for Bear UP_TRI. Mechanism: sustained Bear without
   consolidation = oversold bounces work (UP_TRI), continuation
   shorts get squeezed (DOWN_TRI).

### What was disappointing

1. **No actionable cell verdict beyond DEFERRED.** With 0 Phase-5
   winners and live n=11, can't produce a confident filter.

2. **Verdict A live coverage = 1.** The strongest lifetime filter
   captures only 1 of 11 live signals, providing essentially no
   live-validation power.

3. **All live signals in a 3-day window** (Apr 6-8) — no temporal
   diversity. Fits the cell's "DEFERRED, not enough data" outcome.

### What we don't know

- Whether the wk2/wk3 timing filter actually works in production
  (lifetime supports it, live can't validate)
- Whether the 2 wins were edge or random (n=2 is anecdotal)
- Whether April 2026 is a hostile sub-regime for Bear DOWN_TRI
  specifically (mechanism unclear)
- Whether kill_001 should extend to Auto/Energy/Metal (lifetime
  evidence weak +2.7pp; live sample too thin)

---

## Re-evaluation triggers

The cell should be re-investigated under these conditions:

| Trigger | Action |
|---|---|
| ≥20 additional Bear DOWN_TRI live signals accumulate | Re-run D2-D3 differentiator + filter test with larger n |
| ≥5 of those new signals match wk2/wk3 + non-Bank filter | If matched WR ≥ 50%, upgrade DEFERRED → CANDIDATE |
| ≥10 of those new signals violate wk2/wk3 (in wk1/wk4 + non-Bank) AND lose | Confirms calendar filter; tighten production rule |
| Bear DOWN_TRI live WR exceeds 40% over next 15 signals | Sub-regime shift suspected — re-evaluate |
| Quarterly Phase 5 re-run produces ≥5 VALIDATED Bear DOWN_TRI combos | Run full cell methodology; cell may exit DEFERRED |
| Bear regime ends (transitions to Choppy or Bull) | Re-evaluate cell at next Bear cycle |

Estimated timeline: 6-12 months of additional live data to accumulate
~20 more Bear DOWN_TRI signals (rate ~3-5/month per April 2026).

---

## Update Log

- **v1 (2026-05-02 night, Session 1):** Cell classified DEFERRED.
  0 Phase-5 winners + live n=11 (2W/9L = 18.2%) prevent confident
  filter derivation. Lifetime data (n=3,640, 46.1% baseline)
  supports provisional Verdict A filter (wk2/wk3 timing + kill_001
  Bank exclusion) at +7.5pp lift on n=1,446 lifetime matches.
  Production posture: TAKE_SMALL on Verdict A matches; SKIP otherwise.
  Re-evaluate at quarterly Phase 5 re-run.

  **Sessions 2-3 NOT recommended** — cell methodology blocked by
  lack of Phase-5 winners + thin live data. Move to Bear BULL_PROXY
  cell (third Bear cell) next session.
