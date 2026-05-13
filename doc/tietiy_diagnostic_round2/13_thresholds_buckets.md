# 13 — Thresholds and Bucket Engine

Sources:
- `scanner/bridge/rules/thresholds.py` (85 LOC)
- `scanner/bridge/core/bucket_engine.py` (478 LOC)

## Central thresholds (`thresholds.py`)

Single source of truth for all bridge numeric constants. Selected highlights:

```python
COHORT_STRONG_N             = 10      # n required for strong cohort
COHORT_STRONG_WR            = 0.75    # WR required for strong cohort
COHORT_MODERATE_N           = 5
COHORT_MODERATE_WR          = 0.65
COHORT_MODERATE_SECTOR_WR   = 0.65    # sector_recent_30d WR floor
COHORT_THIN_FALLBACK_N      = 5
COHORT_THIN_FALLBACK_SECTOR_WR = 0.70
COHORT_THIN_FALLBACK_REGIME_WR = 0.65

VALIDITY_MIN_RR             = 1.5
VALIDITY_MAX_AGE_DAYS_DEFAULT = 1
VALIDITY_MAX_AGE_DOWN_TRI   = 0       # DOWN_TRI age=0 only per backtest

BOOST_TIER_A_MIN_N          = 15
BOOST_TIER_A_MIN_WR         = 0.95    # Tier A near-perfect
BOOST_TIER_B_MIN_N          = 10
BOOST_TIER_B_MIN_WR         = 0.80

BOOST_DEMOTION_WR           = 0.70    # rolling-window WR floor for demotion
BOOST_DEMOTION_WINDOW_N     = 10

GAP_CAVEAT_THRESHOLD_PCT    = 2.0

SECTOR_RECENT_WINDOW_DAYS   = 30
REGIME_BASELINE_MIN_N       = 20
```

All numerics live in one file. Changing a threshold is a single edit; all bridge modules pick up the change on next compose. Good architecture.

## Bucket engine decision tree (`bucket_engine.py`)

Pure orchestration, 4 gates, first match wins.

### Gate 1 — KILL_MATCH (from evidence)
If `evidence['kill_match']` is populated (set by `evidence_collector` after `kill_matcher.check_match`), bucket = **SKIP**. Renders kill_id + cohort label + WR/PnL evidence.

### Gate 2 — VALIDITY
Calls `validity_checker.check(signal)`. Validates:
- `rr >= 1.5` (`VALIDITY_MIN_RR`)
- `age_days <= 1` (or `<= 0` for DOWN_TRI per `VALIDITY_MAX_AGE_DOWN_TRI`)
- `entry_valid` flag at L2 (only matters post-open)

Fails → bucket = **SKIP** with `gate=GATE_2_VALIDITY`.

### Gate 3 — BOOST_MATCH (from evidence)
If `evidence['boost_match'].tier == 'A'` → **TAKE_FULL**.
If `evidence['boost_match'].tier == 'B'` → **TAKE_SMALL**.

Otherwise fall through to Gate 4.

### Gate 4 — EVIDENCE CONSENSUS
Reads `evidence['exact_cohort']`, `evidence['sector_recent_30d']`, `evidence['regime_baseline']`, plus counter-evidence flags (`cluster_warnings`, `anti_pattern_check`).

```
if ec.n >= 10 AND ec.wr >= 0.75 AND no warnings → TAKE_SMALL  (strong cohort)
elif ec.n >= 5 AND ec.wr >= 0.65 AND sec.n >= 5 AND sec.wr >= 0.65 AND no warnings → WATCH (moderate cohort)
elif ec.n < 5 AND sec.wr >= 0.70 AND reg.wr >= 0.65 → WATCH (thin fallback)
else → SKIP (default; reports specific reason)
```

## Misclassification audit

Walking the live data through the gates:

**UP_TRI × Bear × Auto** (the textbook winning cohort):
- Gate 1 KILL: no match → pass.
- Gate 2 VALIDITY: r:r needs to be ≥ 1.5 — for UP_TRI×Bear, target=`entry + 2×risk` so r:r=2.0 by construction → pass.
- Gate 3 BOOST: matches `win_001` (UP_TRI×Auto×Bear, Tier A, conviction=TAKE_FULL) → **TAKE_FULL** ✓ correct.

**UP_TRI × Choppy × Bank** (the current portfolio's heavy concentration, 28.6% WR loss cohort):
- Gate 1 KILL: no match (kill_001 is DOWN_TRI×Bank).
- Gate 2 VALIDITY: UP_TRI age=0, target=None (because get_exit_rule returns 'Day6' for non-Bear UP_TRI). `rr` is therefore None or 0 → **SKIP via Gate 2 validity fail** (assuming validity_checker treats None rr as fail).

Actually this is interesting — UP_TRI×Choppy signals will SKIP at Gate 2 if r:r computation requires a real target. But the live signal history shows 35 UP_TRI×Choppy signals were TAKEN (per pattern_miner). So either:
1. The bridge wasn't routing those signals yet (bucket_engine post-dates them).
2. The trader/operator was overriding the SKIP.
3. The bridge passes through `rr` differently than I'm inferring.

This needs verification in a follow-up pass.

**DOWN_TRI × Bank** (the killed cohort):
- Gate 1 KILL: matches `kill_001` → **SKIP** with kill_001 reason. ✓ Working.

## Verdict

**The bucket engine is architecturally sound.** 4 gates, first-match, evidence-driven. The thresholds are well-organized and audit-friendly. 

The main concern: **the bridge's bucket assignments are not what gates the actual trade execution** — the trader reads the bridge brief and decides manually. Signals that bucket as SKIP may still be taken by the operator. And the validity check's effect on rr=None signals (UP_TRI×Choppy targets none) needs verification because the live data shows many such signals were resolved as trades.

## Buckets that look misclassified

- **None at the bucket-assignment level.** The logic is correct given the inputs.
- **Several at the input level.** The "boost match" rules (`win_001..win_007`) include `win_007 BULL_PROXY in Bear regime`. If a BULL_PROXY×Bear×Bank signal fires, it would hit Gate 3 BOOST and bucket TAKE_FULL — but BULL_PROXY×Bank live data shows 50% WR / +2.24% PnL (cohort_health.json) at n=6. The boost is a sector-wildcard, so it would include Bank. Not catastrophic but a minor over-promotion.

- **prop_005 from the deterministic rule_proposer** proposes to kill BULL_PROXY entirely. If approved blindly, this would prevent any BULL_PROXY signal from passing Gate 1 — including the boost-eligible BULL_PROXY×Bear cohort. **This is the dangerous proposal I flagged in §08** — its broad scope would destroy a profitable cohort.
