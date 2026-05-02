# C3 — Choppy Transition-State Whipsaw

**Date:** 2026-05-03
**Sonnet's concern:** "Choppy detector may flip-flop between sub-regimes
day-to-day at boundary conditions, creating whipsaw production behavior
(signal flagged hot one day, cold next, hot again)."

**Verdict: ⚠️ GAP_DOCUMENTED — whipsaw is severe (33% of days are flip days; 38% of episodes are 1-day); N=2 hysteresis recommended (eliminates all 1-day jitter).**

---

## A. Hypothesis

Sub-regime classification at the daily level is sensitive to small
input perturbations. If breadth_pct hovers near a threshold, classification
may flip across consecutive days.

Quantification needed: how often does flip happen? What's the dwell
time distribution? Is whipsaw confined to specific sub-regime pairs or
universal?

---

## B. Investigation

### Setup

Sub-regime classification (current 2-axis: vol × breadth) applied
day-by-day to lifetime Choppy data:
- 1,142 distinct Choppy days (2011-03-30 → 2026-04-29)
- Daily breadth tertile thresholds [0.456, 0.597] from C2 baseline

### Whipsaw frequency

| Metric | Value |
|---|---|
| Total Choppy days | 1,142 |
| Total sub-regime flips | **378** |
| Flips per 100 days | **33.1** |
| Total episodes | 379 |
| Mean episode duration | 3.0 days |
| Median episode duration | 2 days |
| Single-day episodes | **145** (38% of all episodes) |
| Episodes <5 days | **302** (80% of all episodes) |
| X-Y-X 1-day jitter pattern | 61 occurrences |
| Maximum episode duration | 25 days |

**Whipsaw is severe.** ~1 in 3 Choppy days is a flip day. 38% of
sub-regime "episodes" last only 1 day before flipping back. Mean
episode duration of 3 days means production trader experiences
sub-regime tag changes nearly daily.

### Sub-regime distribution (raw classification)

| Sub-regime | Days | % |
|---|---|---|
| Medium_low | 191 | 16.7% |
| Medium_medium | 190 | 16.6% |
| Medium_high | 154 | 13.5% |
| High_medium | 119 | 10.4% |
| Low_low | 116 | 10.2% |
| High_low | 114 | 10.0% |
| High_high | 104 | 9.1% |
| Low_high | 85 | 7.4% |
| Low_medium | 69 | 6.0% |

All 9 cells have meaningful sample (>6%). Whipsaw is universal across
all cells, not concentrated.

### Top flip pairs

| Prev sub-regime | New sub-regime | Count |
|---|---|---|
| Medium_medium | Medium_high | 36 |
| High_medium | High_high | 26 |
| Medium_high | Medium_medium | 26 |
| High_low | High_medium | 26 |
| Medium_low | Medium_medium | 23 |
| Medium_medium | Medium_low | 21 |
| Low_low | Low_medium | 17 |
| High_high | High_medium | 17 |
| Low_medium | Low_low | 17 |
| High_medium | High_low | 16 |

**All top flip pairs share the same vol_regime, differ only in
breadth.** Whipsaw is dominated by breadth boundary crossings (the
continuous breadth_pct grazes the tertile thresholds).

This confirms breadth tertile thresholds (C2 finding: thresholds
[0.456, 0.597]) are the primary whipsaw driver. With breadth in
tertile bands ~14% of the time near each threshold, classification
flips frequently.

### Cross-reference vs S4 (regime-level jitter)

S4 finding (Step 1): regime classifier (Bull/Bear/Choppy) shows
17 single-day jitters in 12 years (1.4/year, very rare).

C3 finding (this critique): sub-regime classifier within Choppy
shows 61 1-day jitters in 1,142 days = ~12.6/year. **9x more
sub-regime jitter than regime jitter.**

This is consistent: regime classifier uses slope ≥ ±0.005 on a 10-day
EMA50 window (slow, smoothed). Sub-regime classifier uses tertile
buckets on a daily breadth measurement (fast, point-in-time). The
finer the granularity, the more whipsaw.

---

## C. Hysteresis design proposal

### Option A — N-day confirmation

Stay in current sub-regime until raw classification changes for N
consecutive days.

| N | Total flips | % of original | Single-day jitters | % days reclassified |
|---|---|---|---|---|
| 1 (no hysteresis) | 378 | 100% | 145 | 0% |
| **2** | **203** | **54%** | **0** | 29% |
| 3 | 130 | 34% | 0 | 45% |
| 5 | 53 | 14% | 0 | 61% |
| 7 | 27 | 7% | 0 | 72% |

**N=2 eliminates ALL 1-day jitter** while keeping 54% of legitimate
flips. 29% of raw classifications get re-mapped to "stay in previous
sub-regime."

N=3 is more aggressive (34% of flips remain; 45% reclassified).
Trades more whipsaw reduction for slower regime transition response.

### Option B — Rolling-mean smoothing

Smooth `breadth_pct` via N-day rolling mean BEFORE bucketing.

| Window | Total flips | % of original | Single-day jitters |
|---|---|---|---|
| 5d | 273 | 72% | 58 |
| 10d | 216 | 57% | 47 |

**Option B is less effective than Option A.** Even 10d smoothing
leaves 47 single-day jitters because vol_regime can also flip
contributing to sub-regime change.

### Option C — Phase-5 evidence override

Per session brief: let live data dominate. Sub-regime classification
becomes a base-rate; live signal tier overrides.

This is a different mechanism than smoothing — it doesn't reduce
whipsaw in the classification, it reduces whipsaw's IMPACT on trading
decisions. Captured separately in B3 (Bear Phase-5 override) which
applies same architecture to Bear.

### Recommendation: Option A with N=2

**Why N=2:**
1. Eliminates ALL 1-day jitter (145 → 0)
2. Halves total flips (378 → 203)
3. Operationally simple (require 2 consecutive days of new
   classification before flipping the tag)
4. Doesn't over-smooth (still allows 203 legitimate transitions)

N=3 is acceptable as more conservative variant. >N=3 risks
over-smoothing real regime transitions.

---

## D. Production integration approach

```python
def smooth_subregime_classification(
    raw_subregimes: list[str],
    confirmation_days: int = 2,
):
    """Apply N-day hysteresis to raw sub-regime classifications."""
    if not raw_subregimes:
        return []
    smoothed = [raw_subregimes[0]]
    pending = None
    pending_count = 0
    for i in range(1, len(raw_subregimes)):
        if raw_subregimes[i] == smoothed[-1]:
            pending = None
            pending_count = 0
        else:
            if pending == raw_subregimes[i]:
                pending_count += 1
            else:
                pending = raw_subregimes[i]
                pending_count = 1
            if pending_count >= confirmation_days:
                smoothed.append(raw_subregimes[i])
                pending = None
                pending_count = 0
                continue
        smoothed.append(smoothed[-1])
    return smoothed
```

This requires production scanner to **maintain state across scan days**
— specifically, the previous-day sub-regime tag and current pending
candidate. Currently scanner is stateless-per-scan (S1 finding).

**Minimal state addition:** persist `current_subregime` and
`pending_subregime_count` to a tiny JSON file (`subregime_state.json`)
read at scan start, written at scan end.

**Risk:** state corruption (e.g., bot restart mid-week) could leave
pending count stale. Mitigation: state has a 7-day staleness check;
if state file is older than 7 days, reset to raw classification.

---

## E. Cross-reference with C1 + C2

C1 recommends adding `nifty_20d_return_pct` as 3rd axis (27 cells
instead of 9). With finer cell granularity, whipsaw frequency will
likely INCREASE (more boundaries to cross). Hysteresis becomes more
important.

**Combined recommendation:** ship hysteresis (N=2) BEFORE adding
3rd axis, OR apply hysteresis to each axis independently. Otherwise
the new 27-cell detector will whipsaw worse than the current 9-cell.

C2 recommended keeping 33/67 split — partly because optimal split
varies by signal type. With hysteresis, threshold sensitivity
matters less (boundary-grazing days don't immediately flip
classification).

---

## F. Failure modes considered

### Failure mode 1: Hysteresis delays legitimate regime transitions

**Considered:** Real Choppy → Bull transition takes 30 days. Hysteresis
N=2 adds 1-2 days to detection lag. Trader exits Choppy cells 2 days
late; misses 2 days of edge.

**Reality:** acceptable. Choppy → Bull transition is upstream of
sub-regime change (regime classifier handles this). Sub-regime
hysteresis is purely within-Choppy whipsaw smoothing.

### Failure mode 2: Hysteresis state corruption

**Considered:** Scanner crashes; subregime_state.json becomes stale;
production resumes with wrong sub-regime tag.

**Reality:** Mitigated by 7-day staleness check + restart-safe reset
to raw classification.

### Failure mode 3: Hysteresis hides real regime decay

**Considered:** Legitimate gradual decay (sub-regime drifting from
hot → warm) gets smoothed away; trader doesn't see regime change
until much later.

**Reality:** N=2 only smooths flicker (2-day confirmation), not slow
drift. Slow drift creates 5+ consecutive days of new classification
which always pass hysteresis.

---

## G. Verdict

**GAP_DOCUMENTED with hysteresis recommendation.**

Sub-regime whipsaw is severe (33% of days are flip days). Production
without hysteresis exposes traders to daily sub-regime tag changes.

**Recommended action:** Apply N=2 hysteresis to Choppy sub-regime
detector (and Bear/Bull detectors when those ship to production).
Eliminates 1-day jitter; halves total flips.

**Production integration:** add minimal state file (subregime_state.json)
maintained across scans. Bundles with other architectural delivery
(C1 momentum addition, Gap 2 sub-regime detector ship).

---

## H. Investigation summary

| Aspect | Finding |
|---|---|
| Choppy days analyzed | 1,142 |
| Sub-regime flips | 378 (33% of days are flip days) |
| Episodes with duration ≤1 day | 145 (38% of all episodes) |
| Episodes with duration <5 days | 302 (80% of all episodes) |
| X-Y-X 1-day jitter pattern | 61 occurrences |
| Top flip pairs | All same-vol, breadth-only (14 of top 14) |
| N=2 hysteresis result | 0 single-day jitter; 54% of flips remain; 29% days reclassified |
| Recommended hysteresis | N=2 |
| Compare vs S4 (regime-level jitter) | 9x more sub-regime jitter than regime jitter |
| Production code change | YES — add `subregime_state.json` + smoothing logic |
| Risk if not addressed | Daily-level whipsaw in production trading decisions |

Sonnet's concern was correct and material. Choppy sub-regime detector
without hysteresis is operationally hostile.
