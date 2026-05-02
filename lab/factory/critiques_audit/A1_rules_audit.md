# A1 — Rules Audit Across 9 Cells (Step 1.5)

**Date:** 2026-05-03
**Scope:** Bear (3) + Bull (3) + Choppy (3) = 9 cells; comparison vs
`data/mini_scanner_rules.json` (schema v3, current production).
**Mandate:** documentation only; no edits to mini_scanner_rules.json or
scanner code. Output feeds Step 3 (Opus rule synthesis).

Note: the session prompt referenced 10 cells; production has 9
(3 signal types × 3 regimes). Audit covers all 9.

---

## A. Rules extracted per cell

### Bear UP_TRI (HIGH-confidence sub-regime gated)

**Sub-regime detector** (`vol_percentile_20d × nifty_60d_return_pct`):

```python
if vp > 0.70:
    if n60 < -0.10: "hot"   # 15% lifetime, 68.3% WR
    elif n60 < 0:   "warm"  # NEW from S2 critique; live 95.2% on n=42
    else:           "cold"
else:               "cold"  # 49-55% unfiltered
```

**Per sub-regime actions:**
| Sub-regime | Action default | Calibrated WR |
|---|---|---|
| hot | TAKE_FULL | 65-75% (lifetime 68.3%) |
| warm | TAKE_FULL | 70-90% (live evidence) |
| cold | Tier 1 cascade or SKIP | 49-55% unfiltered |

**Cold cascade (simplified to 2 tiers):**
- TIER 1: `wk4 AND swing_high_count_20d=low` → TAKE_FULL (63.3% WR, n=3,374)
- Other: SKIP

**Within-hot/warm refinement:**
- `multi_tf_alignment_score` non-default + `range_compression_60d` low-medium → +9.5pp

**Sector mismatch rules:**
- AVOID Health (32.4% in hot — hostile cell)
- TAKE_SMALL Energy (55% in hot)
- TAKE_FULL Chem/Other/FMCG/Pharma/Auto (74-80% in hot/warm)

**Calendar mismatch rules:**
- SKIP December (-25pp catastrophic)
- TAKE_FULL April/Oct/Jul (+10-14pp)
- TAKE_SMALL Nov/Jun

**Phase-5 hierarchy override:**
- Phase-5 validated → execute regardless; sub-regime informs sizing
- Non-Phase-5 → strict sub-regime cascade

**Trader heuristics:**
- Repeat name <6 days → TAKE_SMALL
- 3+ same-day → 80% sizing (correlation cap)

### Bear DOWN_TRI (DEFERRED + provisional)

**Provisional Verdict A:**
- KILL Bank (kill_001 already in production)
- TAKE_SMALL on wk2/wk3 + non-Bank
- SKIP wk1/wk4

**Lifetime evidence:** +7.5pp lift on n=1,446 (39.7% match rate)

**Sector preferences (lifetime):**
- TOP: Pharma (52.2%), Health (52.2%), Other (51.8%)
- BOTTOM: Auto (40.4%), Energy (40.7%), Metal (41.4%)

**Top winner features:**
- `wk2` (+15.0pp); `wk3` (+6.7pp); `nifty_60d_return=medium` (+4.1pp)
- `higher_highs_intact_flag=True` (+4.0pp; INVERTED vs Choppy UP_TRI)

**Anti-features:**
- `wk4` (-17.5pp); `nifty_vol=Low` (-9.8pp); `Mon` (-4.4pp)

### Bear BULL_PROXY (DEFERRED + provisional)

**Provisional Verdict A:**
- DEFAULT: SKIP all
- IF hot sub-regime (vol > 0.70 AND n60 < -0.10): TAKE_SMALL (calibrated 65-75%)
- IF cold: SKIP

**Sub-regime split:** hot 9.7% (63.7% WR), cold 90.3% (45.5% WR)

**Top winner features:**
- `nifty_60d_return=low` (+17.9pp — strongest)
- `52w_high_distance=high` (+14.4pp; NEAR low / FAR from highs)
- `vol_climax_flag=False` (+11.0pp)
- `inside_bar_flag=False` (+9.4pp; INVERTED vs Bear UP_TRI which prefers True)

**Anti-features:**
- `vol_climax_flag=True` (-11.0pp; STRONGEST; UNIVERSAL across regimes)
- `nifty_vol=Medium` (-7.2pp; U-shaped vol response)
- `52w_high_distance=low` (-11.2pp; near highs is BAD)

### Bull UP_TRI (PROVISIONAL_OFF)

**Sub-regime detector** (`nifty_200d_return × market_breadth_pct`):

| Sub-regime | Definition | n | % | WR |
|---|---|---|---|---|
| recovery_bull | low 200d AND low breadth | 972 | 2.6% | **60.2%** |
| healthy_bull | mid 200d AND high breadth | 4,764 | 12.5% | 58.4% |
| normal_bull | else | 29,110 | 76.4% | 51.3% |
| late_bull | mid 200d AND low breadth | 2,699 | 7.1% | 45.1% (AVOID) |

**Hard SKIPs:**
- late_bull → SKIP
- Month=Sep (-8.4pp); Month=Apr (-5.6pp)
- Sector=Energy (-2.9pp)
- `nifty_vol=High` (-2.0pp anti for Bull; INVERTED vs Bear hot)
- wk3 (-3.3pp)

**Best filters:**
- recovery_bull × vol=Medium × fvg_low → 74.1% (n=390)
- recovery_bull × vol=Medium → 69.6-72.8%
- healthy_bull × RSI=med × wk4 → 68.1%
- normal_bull × RSI=med × 20d=high → 58.8%

**Universal anchors:**
- `nifty_20d_return=high` (Bull recency anchor; NOT 200d which is sub-regime axis)

### Bull DOWN_TRI (PROVISIONAL_OFF)

**Provisional Verdict B:**
- IF sub-regime != late_bull → SKIP
- IF sector ∈ {FMCG, Auto} → SKIP
- IF nifty_vol != Low → SKIP
- IF RSI=high → SKIP
- IF wk3 → TAKE_SMALL (~65% calibrated)
- IF Mon → TAKE_SMALL (~62-72%)

**Sub-regime inversion (vs Bull UP_TRI):**
| Sub-regime | UP_TRI WR | DOWN_TRI WR |
|---|---|---|
| recovery_bull | 60.2% | 35.7% (PERFECT INVERSION) |
| healthy_bull | 58.4% | 40.5% |
| normal_bull | 51.3% | 42.6% |
| late_bull | 45.1% | 53.0% |

**Hard SKIPs:**
- recovery_bull/healthy_bull (35-40% WR)
- wk4 (-8.2pp; mirror of UP_TRI's wk4 winner)
- nifty_vol=Medium (-4.4pp)
- RSI=high (-3.1pp; counter-intuitive)

### Bull BULL_PROXY (PROVISIONAL_OFF)

**Provisional Verdict A:**
- IF vol_climax → SKIP (UNIVERSAL)
- IF late_bull → SKIP
- IF wk1 OR wk3 → SKIP
- IF sector ∈ {Bank, Metal} → SKIP
- IF healthy_bull AND nifty_20d=high → TAKE_FULL (62.5%, n=128)
- IF recovery_bull AND wk4 → TAKE_FULL (~75%, n=24)
- IF wk4 alone → TAKE_SMALL (60.8%, n=707)

**Direction-aligned with Bull UP_TRI** (recovery/healthy best; late worst).

**52w_high_distance INVERTS** vs Bear BULL_PROXY:
- Bear: high WINNER (+14.4pp; far from highs)
- Bull: low WINNER (+8.0pp; near highs / breakout-of-resistance)

### Choppy UP_TRI (CANDIDATE — TAKE_SMALL only)

**Original F1 (cell-derived; lifetime-weak):**
- `ema_alignment=bull AND coiled_spring=medium` → +1.7pp lifetime; deploy as TAKE_SMALL only

**Promoted lifetime pattern (v2):**
- `breadth=medium AND vol=High AND MACD bull` → 62.5% (n=3,318, +10.2pp)
- `breadth=medium AND vol=High` → 60.1% (n=4,546, +7.9pp)
- Vol-gating critical: same `breadth=medium` is +7.9pp in High-vol but **−5.5pp in Medium-vol** (FLIPS)

**Hard SKIPs:**
- Sector=Metal (-2.2pp on n=2,092)
- Month=Feb (-16.2pp; catastrophic, likely Indian Budget vol)

**Calendar:**
- TOP: Sep +11.7pp, Mar +10.0pp, Oct +7.3pp; wk4 +4.8pp; wk3 -3.9pp

### Choppy DOWN_TRI (CANDIDATE — upgraded from DEFERRED)

**Best filter:**
- `breadth=medium AND vol=Medium AND wk3 AND bank_nifty_20d=medium` → 57.8% (n=1,295, +11.7pp)
- 2-feat anchor: `breadth=medium AND vol=Medium` → 55.2% (n=1,727, +9.1pp)

**Hard SKIPs:**
- Sector=Pharma (-4.7pp catastrophic), Metal (-1.8pp), Bank (-1.3pp)
- Friday (-6.2pp)
- wk4 (-7.1pp)
- Month=Sep (-12.7pp), Mar (-10.6pp)

**Best month:** Feb +16.2pp (n=711) — INVERSE of Choppy UP_TRI's Feb hostility

### Choppy BULL_PROXY (KILL — REJECT all)

**Production verdict:** REJECT all Choppy BULL_PROXY signals
unconditionally. Best lifetime combo +9.2pp (sub-threshold for
promotion; +10pp required).

**Best (still-rejected) lifetime combo:**
- `breadth=high AND multi_tf_alignment=high AND consolidation_quality=none` → 58.8% (n=325, +9.2pp)

**Sector reach collapse:** only FMCG (n=224) and Bank (n=349) meet
n≥200 — structurally weak signal in Choppy.

---

## B. Cross-cell rule consistency check

### Universal patterns (consistent across cells)

| Pattern | Cells confirming | Mechanism |
|---|---|---|
| `vol_climax_flag=True` is anti-BULL_PROXY | Bear -11.0pp, Bull -4.4pp | Capitulation breaks support reversal |
| Sub-regime tri-modal structure | All 9 cells | Universal architectural pattern |
| `wk4` aligns with bullish direction | Bull UP_TRI +2.6pp, Bear UP_TRI +7.5pp, Bull BULL_PROXY +13.7pp | Month-end institutional flows favor longs |
| Calendar inversion across direction | Bear (wk4 vs wk2), Bull (wk4 vs wk3) | UP_TRI ≠ DOWN_TRI calendar timing |

### Direction-flip pattern (UP_TRI vs DOWN_TRI within same regime)

| Element | Same-regime inversion |
|---|---|
| Bull sub-regime WR | Perfect 4-cell inversion (recovery/healthy best for UP; late best for DOWN) |
| Bear sub-regime WR | UP_TRI hot 68% / DOWN_TRI lifetime 46% baseline |
| Calendar | wk4 ↔ wk2 (Bear); wk4 ↔ wk3 (Bull) |
| RSI=high | Mild winner UP_TRI / anti DOWN_TRI |
| `nifty_60d_return=low` | Winner UP_TRI / anti DOWN_TRI (Bear regime) |

### Cross-regime patterns that DON'T transfer (regime-specific)

| Element | Regime variance |
|---|---|
| Sub-regime axes | Choppy: vol×breadth; Bear: vol×60d_return; Bull: 200d×breadth |
| Anchor feature | Bear UP_TRI: 60d=low; Bull UP_TRI: 20d=high; Choppy: breadth=medium |
| `nifty_vol_regime=High` | Bear UP_TRI: hot tier; Bull UP_TRI: ANTI; Choppy UP_TRI: required |
| `inside_bar_flag` | Bear UP_TRI: True winner; Bear BULL_PROXY: False winner |
| `52w_high_distance=high` | Bear BULL_PROXY: WINNER (far); Bull BULL_PROXY: ANTI (INVERTED) |
| Sector top | Bear UP_TRI: defensives; Bull UP_TRI: growth; Bear DOWN_TRI: Pharma; Bull DOWN_TRI: Metal |

### Direct contradictions (same field, opposite verdict, same context)

| Field | Cell A | Cell B | Contradiction? |
|---|---|---|---|
| `nifty_60d_return=low` | Bear UP_TRI: +14pp WIN | Bear DOWN_TRI: -4pp ANTI | NO — different signal direction |
| `inside_bar_flag=True` | Bear UP_TRI: WIN | Bear BULL_PROXY: ANTI | NO — different cell mechanisms |
| `wk4` | Bear UP_TRI: WIN +7.5pp | Bear DOWN_TRI: ANTI -17.5pp | NO — direction inversion |
| `breadth=medium × vol=High` | Choppy UP_TRI: WIN +7.9pp | Choppy UP_TRI Medium-vol: -5.5pp | YES (within-cell vol-conditional inversion — must apply vol gate) |
| `breadth=high` | Choppy BULL_PROXY: lifetime modest +6pp | Choppy UP_TRI: ANTI in April live | NO — sub-regime artifact |

**One important within-cell conditional**: Choppy UP_TRI's `breadth=medium`
flips sign by vol bucket. Production must apply `vol_regime` first-class
gate. Not a contradiction — a required compound rule.

---

## C. Comparison vs current `mini_scanner_rules.json`

### Currently in production (schema v3, 7 boost + 1 kill + 1 watch)

| Rule | Type | Cell coverage |
|---|---|---|
| kill_001: Bank × DOWN_TRI | KILL | Bear DOWN_TRI (live 0/6) + lifetime modest |
| watch_001: UP_TRI × Choppy n=36 31% WR | WATCH | Choppy UP_TRI v1 (now downgraded) |
| win_001: UP_TRI × Auto × Bear (21/21) | BOOST | Bear UP_TRI hot/warm |
| win_002: UP_TRI × FMCG × Bear (19/19) | BOOST | Bear UP_TRI hot/warm |
| win_003: UP_TRI × IT × Bear (18/18) | BOOST | Bear UP_TRI hot/warm |
| win_004: UP_TRI × Metal × Bear (15/15) | BOOST | Bear UP_TRI hot/warm |
| win_005: UP_TRI × Pharma × Bear (13/13) | BOOST | Bear UP_TRI hot/warm |
| win_006: UP_TRI × Infra × Bear (~10.5/12) | BOOST | Bear UP_TRI hot/warm |
| win_007: BULL_PROXY × Bear (~14/16, sector=null) | BOOST | Bear BULL_PROXY hot |

All 7 boost_patterns are regime=Bear. All map to Bear UP_TRI/BULL_PROXY
hot/warm cells (the highest-conviction live evidence). None contradict
Lab cell findings.

### Lab findings IN production (consistency check)

| Lab finding | Production status |
|---|---|
| Bear UP_TRI sector top: Auto/FMCG/IT/Metal/Pharma | ✓ win_001-005 cover all |
| Bear BULL_PROXY hot is +16.4pp lift | ✓ win_007 (n=16, 87.5% live) |
| kill_001 Bank × DOWN_TRI is correct | ✓ in rules (live 0/6 confirms) |
| Choppy UP_TRI has weak edge | ✓ watch_001 (informational warn) |

### Lab findings NOT in production (gaps)

| Lab finding | Severity | Action |
|---|---|---|
| **Bear UP_TRI Health AVOID** (32.4% in hot) | HIGH | New kill_pattern needed: AVOID Health × Bear_UPTRI |
| **December SKIP Bear UP_TRI** (-25pp catastrophic) | HIGH | New kill_pattern: SKIP Bear_UPTRI in Dec |
| **vol_climax × BULL_PROXY = REJECT** (Bear -11pp, Bull -4.4pp) | HIGH | Universal kill_pattern (UNIVERSAL across regimes) |
| **Choppy BULL_PROXY = REJECT** (KILL verdict) | HIGH | Universal kill_pattern: BULL_PROXY × Choppy regime |
| **Bear DOWN_TRI calendar filter** (wk2/wk3 only, +7.5pp) | MEDIUM | Boost or filter rule |
| **Bull cell rules** (recovery/healthy/late_bull gating) | MEDIUM | All 3 Bull cells (deferred until Bull regime returns + sub-regime detector ships) |
| **Energy × Bull_UPTRI = SKIP** (-2.9pp) | MEDIUM | Kill_pattern; bundles with Bull rules |
| **Choppy UP_TRI Metal SKIP** (-2.2pp on n=2,092) | LOW | Kill_pattern (modest lift) |
| **Choppy UP_TRI Feb SKIP** (-16.2pp catastrophic) | MEDIUM | Calendar kill_pattern |
| **Choppy DOWN_TRI Pharma SKIP** (-4.7pp) | LOW | Kill_pattern |
| **Choppy DOWN_TRI Friday SKIP** (-6.2pp) | LOW | Calendar kill_pattern |
| **Choppy DOWN_TRI wk3 boost** (+11.7pp on n=1,295) | MEDIUM | Boost_pattern |
| **Bear UP_TRI cold cascade** (wk4 × swing_high=low) | MEDIUM | Boost_pattern (sub-regime-conditional) |

### Overlaps between Lab and production rules

| Rule | Lab evidence | Production rule |
|---|---|---|
| Auto×UP_TRI×Bear | 21/21 live | win_001 |
| FMCG×UP_TRI×Bear | 19/19 live + Lab top sector in hot | win_002 |
| IT×UP_TRI×Bear | 18/18 live + Lab top sector | win_003 |

These match exactly between Lab and production. Healthy alignment.

### Key contradictions between Lab and production

**ZERO direct contradictions found.** Production rules are a strict
SUBSET of Lab findings. Production is currently more conservative than
Lab evidence supports. The gap is missing rules, not wrong rules.

---

## D. Cross-regime kill rule audit

| Candidate kill | Source | Universal? | Recommended add? |
|---|---|---|---|
| Bank × DOWN_TRI | live 0/11 + lifetime | NO (Bear-specific) | Already in (kill_001) |
| Energy × Bull_UPTRI | Lab -2.9pp | NO (Bull-specific) | YES (S3 finding) |
| vol_climax × BULL_PROXY | Bear -11pp + Bull -4.4pp | YES (universal) | YES (S5 finding; both regimes) |
| BULL_PROXY × Choppy | KILL verdict (live 25% WR + lifetime sub-threshold) | NO (Choppy-specific) | YES (Choppy KILL needs rule) |
| Health × Bear_UPTRI | 32.4% in hot, deeply hostile | NO (Bear-specific) | YES (Bear UP_TRI cell finding) |
| Pharma × Choppy_DOWNTRI | -4.7pp | NO (Choppy-specific) | YES (modest, low priority) |
| Metal × Choppy_UPTRI | -2.2pp | NO (Choppy-specific) | YES (modest, low priority) |
| Sep × Bull_UPTRI | -8.4pp | NO (calendar-conditional) | YES |
| Dec × Bear_UPTRI | -25pp catastrophic | NO (calendar-conditional) | YES (HIGH priority) |
| Feb × Choppy_UPTRI | -16.2pp | NO (calendar-conditional) | YES |
| Friday × Choppy_DOWNTRI | -6.2pp | NO (day-of-week) | YES (low priority) |
| late_bull × Bull_UPTRI/BULL_PROXY | -7-7.5pp | NO (sub-regime conditional) | YES (requires sub-regime detector ship) |

**12 new kill rules recommended** (8 medium-high priority, 4 low).

**1 universal kill** (vol_climax × BULL_PROXY) — applies across regimes.

---

## E. Cross-regime architectural framework consistency

### Sub-regime axes per regime (from Lab synthesis)

| Regime | Axes | Tri-modal structure |
|---|---|---|
| Choppy | `vol × breadth` | stress / equilibrium / quiet |
| Bear | `vol × 60d_return` | hot / warm / cold |
| Bull | `200d × breadth` | recovery / healthy / normal / late |

**Consistency:** all three regimes have tri-modal (or quad-modal for
Bull) sub-regime structure with regime-specific axes. Universal
ARCHITECTURAL pattern, regime-specific FEATURES.

### Direction-flip pattern (universal)

UP_TRI vs DOWN_TRI inversion within same regime:
- Bull regime: PERFECT 4-cell inversion confirmed
- Bear regime: directional inversion confirmed (UP_TRI hot vs DOWN_TRI broad)
- Choppy regime: partial inversion confirmed (UP_TRI Sep+ vs DOWN_TRI Sep-)

### Calendar inversion (2 of 3 regimes)

| Regime | UP_TRI prefers | DOWN_TRI prefers | Inversion |
|---|---|---|---|
| Bear | wk4 (+7.5pp) | wk2 (+15pp) | ✓ STRONG |
| Bull | wk4 (+2.6pp) | wk3 (+8.4pp) | ✓ CONFIRMED |
| Choppy | wk4 (+4.8pp) | wk3 (+11.7pp) | ✓ CONFIRMED |

3 of 3 regimes confirm calendar inversion across direction. **Universal
pattern with regime-specific timing.**

### Rule consistency with framework

All 9 cell rules align with the framework. No cell findings break
universal patterns. Bull DOWN_TRI's perfect sub-regime inversion is
the strongest cross-cell architectural finding. Cells produce a
**coherent, unified rule set** when viewed through the
regime × direction × sub-regime axes.

---

## F. Verdict summary

**Methodology consistency: HEALTHY.** No systematic contradictions
between cells. All 9 cells produce internally consistent rules that
align with the cross-regime architectural framework.

**Production rules consistency: HEALTHY.** Zero contradictions between
production rules and Lab findings. Production is a strict subset of
Lab evidence.

**Rule completeness: GAP-DOCUMENTED.** ~12 missing rules in production
(8 medium-high priority, 4 low). Most are kill_patterns or
sub-regime-conditional boost_patterns. None are blocking.

**Pattern coverage: STRONG.** Universal patterns documented (vol_climax
anti-BULL_PROXY, calendar inversion, sub-regime tri-modal structure).
Regime-specific axes documented and non-overlapping.

**Step 3 readiness: READY.** The rules audit produces a clean input
package for Opus rule synthesis:
- 9 cell playbooks with extracted rules
- 1 mini_scanner_rules.json snapshot
- Universal vs regime-specific pattern map
- 12 rule gaps with priority + evidence
- 0 contradictions to resolve

---

## G. Recommended new rules (priority-ranked, for Step 3 input)

### HIGH priority (5)

1. **Universal vol_climax × BULL_PROXY = REJECT** — applies all regimes
2. **Choppy BULL_PROXY = REJECT** — entire cell KILL verdict
3. **Bear UP_TRI × Health = AVOID** (32.4% hot, hostile sector)
4. **Bear UP_TRI × December = SKIP** (-25pp catastrophic month)
5. **Choppy UP_TRI × Feb = SKIP** (-16.2pp catastrophic; Indian Budget)

### MEDIUM priority (5)

6. **Bull UP_TRI × Energy = SKIP** (-2.9pp; ships with Bull rules)
7. **Bear DOWN_TRI calendar filter** (wk2/wk3 only; +7.5pp boost)
8. **Choppy DOWN_TRI wk3 × breadth=medium × vol=Medium = TAKE_FULL** (+11.7pp)
9. **Bear UP_TRI cold cascade boost** (wk4 × swing_high=low; +13pp lift)
10. **late_bull = SKIP** for Bull UP_TRI/BULL_PROXY (requires sub-regime detector)

### LOW priority (4)

11. **Choppy DOWN_TRI × Pharma = SKIP** (-4.7pp)
12. **Choppy DOWN_TRI × Friday = SKIP** (-6.2pp)
13. **Choppy UP_TRI × Metal = SKIP** (-2.2pp)
14. **Bull UP_TRI/PROXY × Sep = SKIP** (-8.4pp)

---

## H. Naming inconsistencies / schema notes for Step 3

**Field name mismatches:**
- Lab uses `nifty_vol_regime` / `nifty_60d_return_pct` / `market_breadth_pct` — production scanner has `nifty_vol`, `ret20`. Production schema needs harmonization (Gap 2 in PRODUCTION_POSTURE).
- `feat_day_of_month_bucket` (Lab) vs scanner doesn't tag day-of-month at all (would need to add).
- Sub-regime classification (`hot/warm/cold`, `recovery/healthy/normal/late`) is Lab-only — production scanner has no sub-regime layer.

**Pre-Step-3 schema decision:** Opus will likely need to recommend
schema extensions to mini_scanner_rules.json supporting:
- `month` / `day_of_month_bucket` / `day_of_week` matching
- `sub_regime` matching (per-regime nested namespace)
- `vol_regime` matching (Low/Medium/High)
- `nifty_60d_return_bucket` (low/medium/high)

These schema additions are data-pipeline work as much as rules-file
work. Surface to Step 3 as input.

---

## I. LLM critique adjustments (post-Sonnet 4.5 review)

Critique output: `_a1_llm.md`. 7 specific challenges; 6 accepted as
material adjustments to the audit conclusions.

### Accepted adjustments

**1. "0 contradictions" claim hides mechanistic differences.**
Same signal type can require opposite trading logic across regimes
(Bear DOWN_TRI = trend-fade in stress; Choppy DOWN_TRI = mean-reversion
in equilibrium). Step 3 must annotate each rule with its trading
mechanism (mean-reversion / breakout-continuation / regime-transition)
to surface implicit logic conflicts.

**2. vol_climax × BULL_PROXY is NOT universal — sub-regime conditional.**
Bear -11pp is universal in Bear; Bull -4.4pp is concentrated in late_bull
sub-regime (neutral/positive in recovery/healthy). Reclassified as
"REJECT in Bear AND Bull-late_bull" — schema must support sub-regime
conditional matching.

**3. Schema architecture — 2-tier, not 6-field expansion.**
Replace the proposed 6-flat-field schema with:
- `match_fields = {signal, sector, regime, conviction_tag}` (no expansion)
- `conditions = [{feature: value}, ...]` (AND-gated array of arbitrary
  feature-value pairs)

This supports Bear UP_TRI cold cascade as
`conditions: [{day_of_month_bucket: "wk4"}, {swing_high_bucket: "low"}]`
without polluting top-level schema. Calendar helpers become utility
functions; sub-regime becomes a runtime-derived feature available to
the conditions array.

**4. Priority ranking IS upside-down. Reranked.**

Original HIGH (catastrophe avoidance) demoted; sub-regime edge drivers
promoted:

NEW HIGH priority (sub-regime edge + universal hygiene):
1. **late_bull = SKIP for Bull UP_TRI/BULL_PROXY** — biggest edge driver
   (74% WR vs 45% WR; 30pp swing in highest-frequency Bull cells)
2. **recovery_bull × vol=Med × fvg_low = TAKE_FULL** for Bull UP_TRI
   (74% WR cell; biggest precision unlock)
3. **healthy_bull × 20d=high = TAKE_FULL** for Bull BULL_PROXY (62.5%, n=128)
4. **Universal vol_climax × BULL_PROXY = REJECT in Bear AND
   Bull-late_bull** (corrected from "universal")
5. **Bear UP_TRI × Health = AVOID** (32.4% in hot)

NEW MEDIUM (catastrophe avoidance + scaffolding):
6. **Bear UP_TRI × December = SKIP** (-25pp catastrophic)
7. **Choppy UP_TRI × Feb = SKIP** (-16.2pp catastrophic)
8. **Choppy BULL_PROXY = REJECT** (KILL verdict — but cleanup; cell is
   already low-frequency)
9. **Bear DOWN_TRI calendar filter** (wk2/wk3 only)
10. **Bear UP_TRI cold cascade** (wk4 × swing_high=low)

NEW LOW (sector/day-of-week micro-rules):
11. Bull UP_TRI × Energy = SKIP
12. Bull UP_TRI/PROXY × Sep = SKIP
13. Choppy DOWN_TRI × Pharma/Friday/wk4 = SKIP
14. Choppy UP_TRI × Metal = SKIP

**5. Rule precedence model required (currently absent).**

Step 3 must define explicit evaluation order:

```
1. REJECT/KILL filters fire first (cell-level kills, vol_climax,
   catastrophic calendar)
2. Sub-regime gating (recovery/healthy/late, hot/warm/cold)
3. Sector/calendar micro-vetos (Health AVOID, wk-pattern boosts)
```

Each layer is AND-gated. Conflict resolution is by hierarchy, not
score-weighting. The rules audit didn't define this; Step 3 must.

**6. Worked examples required for Opus.**

Audit alone doesn't validate that rules compose correctly. Step 3
needs ≥5 worked end-to-end examples covering the cross-product of
regime × signal × sub-regime, each showing:
- raw signal features (date, sector, regime, sub-regime, vol, etc.)
- rule evaluation trace (which rules fired, in what order)
- final verdict
- justification

Worked examples will be authored as part of SUMMARY.md (sub-block SY).

**7. Structural vs parametric rule split.**

Rules should be classified into:
- **Structural** (truly universal logic): vol_climax × BULL_PROXY anti
  pattern, sub-regime tri-modal gating mechanism, calendar inversion
  template
- **Parametric** (universal template, cell-specific parameters): each
  cell's sub-regime axes (Bear: vol×60d, Bull: 200d×breadth, Choppy:
  vol×breadth), each cell's sector preferences

Conflating these as "universal" obscures that Bull has no "hot"
sub-regime and Bear has no "recovery" sub-regime. Step 3 should
generate separate structural-rules.json and parametric-cell-tables.json.

### Item rejected

**LLM critique #1 implicit suggestion to redo the entire framing as
"trading mechanism" classification.** This would require re-running the
9 cell investigations with mechanism annotation. Out of scope for
A1 audit. Captured as input to Step 3 instead.

---

## J. Step 3 input package (revised)

Step 3 (Opus) will receive:

1. **9 cell playbooks** (lab/factory/{regime}_{signal}/playbook.md)
2. **3 regime synthesis docs** (lab/factory/{bear,bull,choppy}/synthesis*.md)
3. **2 PRODUCTION_POSTURE docs** (bear, bull)
4. **Cross-regime architectural framework** (synthesized via this audit)
5. **Bull production verification report** (lab/factory/bull_verification/)
6. **Bull critique resolution** (lab/factory/bull_critiques/SUMMARY.md
   — Step 1)
7. **This audit** (A1_rules_audit.md + _a1_llm.md)
8. **Pre-existing rules** (data/mini_scanner_rules.json)
9. **6 remaining critique resolutions** (C1-C3, B1-B3 — to be authored
   in this session)
10. **5+ worked examples** for runtime validation (to be authored in SY)

Opus should produce:
- Unified rules.json schema (2-tier: match_fields + conditions)
- Structural rules file (universal patterns)
- Parametric cell tables (cell-specific axes + thresholds)
- Rule precedence model documentation
- Test vectors validating against worked examples

---

## K. Final verdict (revised post-LLM)

| Aspect | Verdict |
|---|---|
| Methodology consistency (cells internal) | HEALTHY (0 *direct* contradictions; mechanistic differences flagged for Step 3) |
| Production rules consistency (vs Lab) | HEALTHY (production is strict subset) |
| Rule completeness | GAP_DOCUMENTED (14 missing rules: 5 HIGH, 5 MEDIUM, 4 LOW after re-prioritization) |
| Universal vs regime-specific patterns | DOCUMENTED (3 truly structural; rest parametric) |
| Schema design | RECOMMENDED 2-tier (match + conditions) — Step 3 to validate |
| Rule precedence | UNDEFINED — Step 3 deliverable |
| Worked examples | NOT YET AUTHORED — SY deliverable |
| Step 3 readiness | READY-WITH-CAVEATS (Step 3 must produce precedence model + worked examples + 2-tier schema)

A1 closes here. C1-C3, B1-B3 follow next; SY consolidates.
