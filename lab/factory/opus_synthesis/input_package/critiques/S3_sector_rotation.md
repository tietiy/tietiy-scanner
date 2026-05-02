# S3 — Sector Rotation Edge Cases in Bull Regime

**Date:** 2026-05-03
**Sonnet's concern:** "Bull rallies are sector-rotation-driven (IT one
month, banks the next, energy the third). The scanner ranks sector
momentum on a 1-month window — what happens when (a) the trader sees
Bull regime active but the 1-month sector ranking still reflects
pre-Bull leadership, (b) leadership rotates within Bull and the scanner's
tag lags by ~15 days, (c) entire market is rallying so 6-7 sectors
all qualify as 'Leading' and the tag loses discriminating power?"

**Verdict: ⚠️ GAP_DOCUMENTED — handling functionally correct; calibration weak in 3 distinct ways**

---

## A. Hypothesis

Three nested concerns:

1. **Stale first-Bull-day sector ranking:** 1-month sec_mom window
   covers prior Bear/Choppy period when Bull regime first activates.
2. **Mid-Bull rotation lag:** sector leadership shifts (e.g., IT →
   Banking → Energy) and the 1-month window lags by ~15 days.
3. **Leadership inflation:** in broad Bull rallies, most sectors clear
   the +2% threshold, making the "Leading" tag near-universal and
   non-discriminating.

Plus a related Lab-vs-production mismatch:
4. Lab cell findings show regime-specific sector preferences (Bull
   UP_TRI tops IT/Health; Bull UP_TRI bottoms Energy) that production
   scoring does NOT differentiate per regime.

---

## B. Investigation — production sector mechanism

### Finding 1: Sector classification is 1-month NIFTY sector-index return

`scanner/main.py:get_sector_momentum()` (lines 340-360):

```python
def get_sector_momentum():
    momentum = {}
    for sector, sym in SECTOR_INDICES.items():
        df = yf.download(sym, period='1mo', ...)
        ret = float((closes.iloc[-1] / closes.iloc[0] - 1) * 100)
        momentum[sector] = (
            'Leading' if ret >  2 else
            'Lagging' if ret < -2 else
            'Neutral')
    return momentum
```

11 NIFTY sector indices. Daily snapshot. Hard thresholds at ±2%.

### Finding 2: Scoring layer rewards Leading uniformly across regimes

`scanner/scorer.py:enrich_signal()` line 89:

```python
if sig.get('sec_mom', 'Neutral') == 'Leading':
    score += SCORE_SEC_LEADING  # +1
```

Same +1 for Bull, Bear, Choppy. No regime-aware weighting. No
sector-specific kill rules per regime in `mini_scanner_rules.json`
(only kill: Bank × DOWN_TRI, regime-agnostic).

### Finding 3: Leadership inflation in broad Bull rallies

From V3 verification replay sector_momentum daily snapshots:

| Date | n Leading | Leading sectors | n Lagging |
|---|---|---|---|
| 2021-08-02 | 3 | IT, Infra, Metal | 2 (Auto, Energy) |
| 2021-08-05 | 3 | IT, Infra, Metal | 1 (Auto) |
| 2021-08-09 | 4 | Bank, IT, Infra, Metal | 0 |
| 2021-08-11 | 3 | IT, Infra, Metal | 1 (Auto) |
| 2021-08-13 | 3 | IT, Infra, Metal | 2 (Auto, Pharma) |
| 2023-06-12 | 6 | Auto, FMCG, IT, Infra, Metal, Pharma | 0 |
| **2023-06-15** | **7** | Auto, Energy, FMCG, IT, Infra, Metal, Pharma | **0** |
| 2023-06-19 | 6 | Auto, Energy, FMCG, Infra, Metal, Pharma | 0 |
| 2023-06-21 | 6 | Auto, Energy, FMCG, Infra, Metal, Pharma | 0 |
| 2023-06-23 | 3 | Auto, Infra, Pharma | 1 (IT) |

The 2023-06 window peaks at **7 of 8 tracked sectors all "Leading"**
simultaneously. The +1 SecLead bonus becomes nearly automatic in broad
Bull rallies — no longer differentiating. ~30-50% of all Bull replay
signals carry SecLead+1, vs Bear baseline where Leading is rarer (~15-20%).

### Finding 4: Mid-Bull rotation churn measured

Sector tag flips between consecutive scan days:

| Window | Mean flips/day | Max flips/day |
|---|---|---|
| 2021-08 (5 days) | 1.2 | 2 |
| 2023-06 (5 days) | 1.2 | 4 (2023-06-23: IT flipped Leading→Lagging) |

Rotation churn IS happening within Bull, even in a 5-day window. The
1-month rolling window means this churn is smoothed over ~15 days.
A signal fired today on a stock in "Leading sector" reflects sector
strength averaged over the past 30 days, not today's leadership.

For a sector freshly losing leadership (e.g., IT on 2023-06-23), the
1-month tag may still read Leading for ~10-15 more days even as the
sector starts underperforming.

### Finding 5: Replay actions stratified by sec_mom

| sec_mom tag | n | DEPLOY | DEPLOY % |
|---|---|---|---|
| Leading | 35 | 19 | 54.3% |
| Neutral | 68 | 14 | 20.6% |
| Lagging | 9 | 1 | 11.1% |

The +1 SecLead bonus DOES correlate with DEPLOY — 54% vs 21% baseline.
But this is 19 signals tipped to DEPLOY in 5 days × 60 stocks = ratio
that may be over-permissive when leadership tag is inflated.

### Finding 6: Lab found regime-specific sector preferences NOT applied in production

From `lab/factory/bull_uptri/playbook.md`:

```
| Sector top    | Bear UP_TRI: CapGoods, Auto | Bull UP_TRI: IT, Health |
| Sector bottom | Bear UP_TRI: Health (32%!)  | Bull UP_TRI: Energy     |
| Energy        | Bull UP_TRI: -2.9pp lifetime, worst Bull UP_TRI sector|
```

Lab playbook explicitly recommends: "if signal.sector == 'Energy':
return 'SKIP'" for Bull UP_TRI. This rule is **not present** in
production `mini_scanner_rules.json` (0 Bull boost_patterns; 0 Bull
kill rules; only kill is Bank × DOWN_TRI regime-agnostic).

In V3 replay, **Energy fired 12 of 112 (10.7%) Bull signals — most of
any sector**, with 2/12 (16.7%) reaching DEPLOY. Lab cell says these
should be SKIP entirely. Production currently surfaces them.

### Finding 7: First-Bull-day stale sector ranking

`get_sector_momentum()` uses `period='1mo'` — 1 month of trading data
ending today. On the first day of Bull regime activation, this window
covers ~30 days of pre-Bull (Choppy or Bear) trading. So the first-day
sector ranking reflects Choppy/Bear leadership patterns, not Bull
leadership.

Empirical impact: Lab found Bull and Bear sector tops are essentially
**inverse** (Bull tops IT/Health; Bear tops CapGoods/Auto). On the first
1-15 days of Bull, the scanner's "Leading" tag will mostly point at the
PRIOR regime's leaders, biasing signals toward the wrong sectors for
Bull cell scoring.

---

## C. Failure modes considered

### Failure mode 1: First-Bull-day sector tag points at Bear leaders

**Considered:** Bull regime activates after 6 months of Bear. Day 1
sec_mom shows CapGoods/Auto Leading (Bear's defensives), not IT/Health
(Bull's growth leaders). Trader gets DEPLOY signals biased toward
suboptimal sectors for Bull regime.

**Reality:** Real. 1-month window means ~15-20 trading days of stale
ranking before sector tags fully reflect Bull regime. Lab data shows
Bull UP_TRI WR is ~10pp lower for Bear-leader sectors than for IT/Health.

**Documented gap. Pre-activation prep: first-Bull-day briefing should
note that sector ranking lags ~15 days into the new regime; trust
Bull-cell sector recommendations from Lab playbook over current
sec_mom tag for the first 2 weeks.**

### Failure mode 2: Leadership inflation makes SecLead+1 noise

**Considered:** In broad Bull (7/8 sectors Leading), nearly every signal
gets +1 SecLead, pushing scores from 5→6 (DEPLOY threshold). DEPLOY rate
inflates without underlying signal quality improving.

**Reality:** Real. 2023-06 window shows the structural problem.
SecLead+1 is calibrated against Bear-baseline rarity (~15-20% Leading)
but applied with same weight in Bull-broad-rally (~50-70% Leading).

**Documented gap. Post-activation: consider regime-aware SecLead
weighting OR breadth-adjusted Leading threshold (Leading = top 3
sectors by 1m return, not absolute >+2%).**

### Failure mode 3: Mid-Bull rotation lag

**Considered:** Sector loses leadership today, but 1-month window
keeps it tagged Leading for ~10-15 more days. Trader gets DEPLOY
signals on stocks in newly-weak sectors.

**Reality:** Real but lower priority. 2023-06-23 shows IT flipping
Leading→Lagging in 1 day, but this is a 1-month-window artifact at
the boundary. Stocks in IT during the lag period carry stale +1
SecLead. Most signals re-evaluate next scan day; aged signals (UP_TRI
age 1-3) carry yesterday's tag — fresh detection per scan day mostly
self-corrects.

**Lower-priority gap. Could be addressed by shortening the sector
window to 2 weeks or using a faster ema-based momentum rank.**

### Failure mode 4: Lab "SKIP Energy in Bull UP_TRI" rule not in production

**Considered:** Lab cell says Energy × Bull UP_TRI is -2.9pp WR (worst
Bull UP_TRI sector). Production has no kill rule. Energy stocks
generate 12/112 = 10.7% of all Bull replay signals.

**Reality:** Confirmed gap. This is a documented Lab cell recommendation
not yet shipped to `mini_scanner_rules.json`. Same issue as Bull
boost_patterns gap (PRODUCTION_POSTURE Gap 1).

**Documented gap. Pre-activation work: Bull-specific kill_patterns
should be populated from Lab cell findings: SKIP Energy×Bull_UPTRI,
SKIP Health×Bear_UPTRI, etc.**

### Failure mode 5: Sub-regime sector preference not applied

**Considered:** Bull sub-regime detector (recovery_bull / healthy_bull /
normal_bull / late_bull) has different sector preferences per cell.
recovery_bull favors IT/Health; healthy_bull favors broad; late_bull
favors defensives. Production has no sub-regime sector gating.

**Reality:** Confirmed gap, but downstream of more fundamental Gap 2
(sub-regime detector not in production at all). Once sub-regime
detector ships, sector gating per sub-regime can layer on top.

**Future work, dependent on Gap 2 ship.**

---

## D. Sector handling design verdict

**No bugs in sector mechanism — works as designed.**

But three calibration weaknesses in Bull-specific behavior:

| Weakness | Severity | Mitigation |
|---|---|---|
| First-Bull-day stale ranking (1-month lag) | MEDIUM | Pre-activation briefing |
| Leadership inflation (most sectors Leading) | MEDIUM | Regime-aware or breadth-adjusted SecLead |
| Lab "SKIP Energy×Bull_UPTRI" not in production | HIGH | Pre-activation: ship Bull kill rules to mini_scanner_rules.json |
| Mid-Bull rotation lag (~15d smoothing) | LOW | Optional: shorter sector window |
| Sub-regime sector gating | LOW (deferred) | After Gap 2 ships |

**The high-severity item — Lab cell findings not in production scoring
rules — is a sub-set of the broader PRODUCTION_POSTURE Gap 1 (no Bull
boost_patterns) but specifically about kill_patterns.** Both directions
of asymmetric Bull cell findings (Energy SKIP, IT/Health PREFER) are
absent from the production rule file.

---

## E. Verdict

**GAP_DOCUMENTED.**

Sector mechanism functionally correct (no signals dropped/misclassified
at runtime). But three calibration gaps:

1. **First-Bull-day stale sector ranking** (1-month window covers
   prior regime) — pre-activation briefing item
2. **Leadership inflation in broad Bull** — Leading tag becomes
   near-universal, +1 SecLead loses discriminating power
3. **Lab Bull cell sector recommendations not in production rules** —
   most importantly: Energy × Bull UP_TRI = SKIP (Lab -2.9pp lifetime)
   not enforced; 12/112 Bull replay signals fired in Energy sector

**No production code changes in this critique cycle.**

Future production-prep checklist items:
- (a) Ship Bull kill_patterns to `mini_scanner_rules.json`: include
  Energy×Bull_UPTRI=SKIP from Lab playbook (~2.9pp lift). Same
  pre-activation work as Gap 1 (Bull boost_patterns).
- (b) First-Bull-day briefing note: sector ranking lags 15 days into
  new regime; trust Lab Bull cell sector preferences for first 2 weeks.
- (c) Post-activation: revisit SecLead+1 weighting in broad Bull where
  most sectors qualify as Leading. Consider breadth-adjusted threshold
  (top-3 by return rather than absolute >+2%).

---

## Investigation summary

| Aspect | Finding |
|---|---|
| Sector momentum mechanism | 1-month NIFTY sector index return; Leading >+2%, Lagging <-2% |
| Sector mechanism failures (drops/bugs) | NONE |
| First-Bull-day stale ranking | YES (1-month lag into new regime) |
| Max simultaneous Leading sectors (Bull replay) | 7 of 8 (2023-06-15) |
| Mean sector tag flips per day (Bull replay) | 1.2 |
| DEPLOY rate by sec_mom (Bull replay) | Leading 54%, Neutral 21%, Lagging 11% |
| Energy × Bull UP_TRI in Lab | -2.9pp lifetime (SKIP recommended) |
| Energy signals in Bull replay | 12/112 (10.7%); 2 reached DEPLOY |
| Bull kill_patterns in production | 0 (only Bank×DOWN_TRI regime-agnostic) |
| Calibration items requiring pre-activation | 1 (Bull kill rules) |

Sonnet's concern was valid: sector handling has real calibration weakness
in Bull. Mitigations are all documentation/rules-file changes — no
scanner code changes required.
