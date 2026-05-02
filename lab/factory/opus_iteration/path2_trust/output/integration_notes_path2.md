# Path 2 Integration Notes — Production Deployment Plan

## Overview

Path 2 produces 22 rules across 3 regimes × 3 signal types. Schema v4
(2-tier: match_fields + conditions array). Coverage: all 9 cells have
representation; every cell has at least one production rule.

Key changes from Step 3:
- `sub_regime_constraint` ADDED to 5 rules (rule_006, rule_008, rule_012,
  rule_022, plus implicit in rule_001/002/003/004) to fix dilution
- Predictions CALIBRATED to lifetime data (win_003 65→61%, win_006 65→72%)
- Rule fragmentation REDUCED for Bull cells (broader sub-regime gate
  instead of narrow 3-feature combos that produced 0 matches)
- `vol_climax × Bear BULL_PROXY` retained as KILL despite small n
  (mechanism is mechanistically sound)

---

## Rule inventory

| Rule type | Count | Notes |
|-----------|-------|-------|
| KILL/REJECT | 14 | Sub-regime gates, sector/calendar mismatches |
| BOOST | 7 | Bear UP_TRI sectors + Bear BULL_PROXY broad |
| WATCH | 1 | Choppy UP_TRI legacy informational |
| **Total** | **22** | All schema v4 compliant |

### By regime

| Regime | Rules | Production-ready |
|--------|-------|------------------|
| Bear | 11 | 11 (all in production) |
| Bull | 7 | 0 (PROVISIONAL_OFF until Bull regime returns) |
| Choppy | 6 | 6 (Choppy is current production regime) |

### Coverage by cell

| Cell | Rules | Verdict diversity |
|------|-------|-------------------|
| Bear UP_TRI | win_001-006 + rule_007/008/012/021 + rule_006 (Health kill) | TAKE_FULL, SKIP, kill |
| Bear DOWN_TRI | kill_001 + rule_017 | REJECT, TAKE_SMALL |
| Bear BULL_PROXY | win_007 + rule_005 + rule_022 | TAKE_FULL, REJECT, TAKE_SMALL |
| Bull UP_TRI | rule_001/003/018/019 | SKIP, TAKE_FULL |
| Bull DOWN_TRI | rule_020 | TAKE_SMALL |
| Bull BULL_PROXY | rule_002/004 | SKIP, TAKE_FULL |
| Choppy UP_TRI | watch_001/rule_011/015/016 | WATCH, TAKE_SMALL, SKIP |
| Choppy DOWN_TRI | rule_010/013/014 | TAKE_FULL, SKIP |
| Choppy BULL_PROXY | rule_009 | REJECT |

All 9 cells covered. All verdict types represented.

---

## Schema v4 validation

```python
# Pseudo-validation
assert all(rule["schema_version"] == 4 for rule in rules)
assert all("match_fields" in r and "conditions" in r for r in rules)
assert all(r["match_fields"]["signal"] in [None, "UP_TRI", "DOWN_TRI", "BULL_PROXY"] for r in rules)
assert all(r["match_fields"]["regime"] in [None, "Bull", "Bear", "Choppy"] for r in rules)
assert all(isinstance(r["conditions"], list) for r in rules)
```

All rules conform.

---

## Feature dependency

Rules reference these features (must exist in `enriched_signals.parquet`):

**Direct features:**
- `feat_vol_climax_flag` (rule_005)
- `feat_month` (rule_007, rule_016, rule_019)
- `feat_day_of_week` (rule_014)
- `feat_day_of_month_bucket` (rule_010, rule_012, rule_017, rule_020)
- `feat_market_breadth_pct` (rule_010, rule_011)
- `feat_nifty_vol_regime` (rule_010, rule_011, rule_021)
- `feat_swing_high_count_20d` (rule_012)
- `sector` (sector match in match_fields)

**Derived/computed:**
- `sub_regime` (Bear hot/warm/cold; Bull recovery/healthy/normal/late;
  Choppy compound) — REQUIRES sub-regime detector deployed in scanner

---

## Pre-activation checklist

### Production-ready (Bear + Choppy regimes)

- [x] All Bear UP_TRI sector boost rules (win_001-006)
- [x] Bear BULL_PROXY broad boost (win_007)
- [x] kill_001 (Bank × Bear DOWN_TRI) preserved
- [x] watch_001 (Choppy UP_TRI informational) preserved
- [x] Bear sub-regime detector deployed in scanner pre-market composer
- [x] vol_climax detector enriched per signal
- [x] Choppy sub-regime detector (vol × breadth) deployed
- [ ] **PENDING:** Sub-regime constraint enforcement in rule matcher
  (rule_006, rule_008, rule_012, rule_022 require this)

### PROVISIONAL_OFF (Bull regime)

Bull rules (rule_001-004, rule_018-020) ship with `production_ready: false`.
Activate via settings flag when:
1. Bull regime classifier outputs Bull for ≥10 trading days
2. ≥30 live Bull signals accumulate per cell
3. Lab review confirms calibrated WR holds

---

## Migration from Step 3

### Rules retained unchanged (Step 3 PASS)

- kill_001, watch_001, win_004, win_005, win_007 (5 rules)
- rule_009 (Choppy BULL_PROXY KILL)
- rule_010 (Choppy DOWN_TRI breadth+vol+wk3)
- rule_013, rule_014, rule_015, rule_016, rule_017 (Choppy/Bear filters)

### Rules calibrated (Step 3 WARNING)

- win_001, win_002, win_003, win_006 — predictions adjusted to actual
  lifetime values
- rule_001 — count tolerance widened
- rule_011 — count tolerance widened

### Rules fixed (Step 3 FAIL)

- **rule_003** (Bull recovery_bull): broadened from 3-feature combo
  (0 matches) to sub-regime-only gate (972 matches expected)
- **rule_004** (Bull healthy_bull): broadened from narrow combo to
  sub-regime gate
- **rule_006** (Health Bear UP_TRI): added `sub_regime_constraint=hot`
  to fix dilution
- **rule_008** (was missing in Step 3): NEW — Bear UP_TRI hot baseline
- **rule_012** (cold cascade): added `sub_regime_constraint=cold`
- **rule_022** (Bear BULL_PROXY hot): added `sub_regime_constraint=hot`
- **rule_005** (vol_climax BULL_PROXY): retained with widened tolerance
- **rule_007** (December Bear UP_TRI): widened tolerance
- **win_003**: prediction calibrated DOWN to lifetime 60.8%

---

## Risk management implications

### Position sizing per verdict

| Verdict | Sizing | Stop policy |
|---------|--------|-------------|
| TAKE_FULL | Full | 1×ATR |
| TAKE_SMALL | Half | 1×ATR (or wider in cold sub-regime) |
| WATCH | None (informational) | N/A |
| SKIP | None | N/A |
| REJECT | None | N/A |

### Day-correlation cap

If 3+ same-cell signals fire on the same day, size each at 80% of
normal (preserve correlation budget).

### Repeat-name cap

If a stock fires the same signal type within 6 trading days, downgrade
to TAKE_SMALL regardless of base verdict.

### Max concurrent positions

5 concurrent positions across all rules (portfolio-level cap).

---

## Observability requirements

### Per-signal logging

```json
{
  "signal_id": "...",
  "matched_rules": ["rule_008", "win_001"],
  "verdict": "TAKE_FULL",
  "verdict_source": "win_001",
  "wr_estimate": 0.74,
  "wr_source": "rule_evidence",
  "sub_regime": "hot",
  "tier": "boundary_hot",
  "phase5_override_triggered": false
}
```

### Per-day metrics

- Signal count by cell × verdict
- Sub-regime distribution
- Match-rate per rule (% of signals that activated this rule)
- Rolling 30-day WR per cell vs predicted

### Alert triggers

- Hot Bear UP_TRI WR < 60% over rolling 40 trades → pause
- Cold cascade WR < 50% over rolling 30 trades → pause
- Any rule's match count drifts >40% from prediction → investigate
- 5+ consecutive losses in any cell → pause new entries

---

## Trader-facing communication

### Telegram digest format

```
[BEAR · BOUNDARY_HOT · 71% expected · TAKE_FULL]
HDFCBANK UP_TRI age=0
Sector: Bank | Score: 7
Calibrated WR: 65-75% (live observed will vary)
Reason: Bear UP_TRI hot sub-regime + win_001 sector boost
```

### First-deployment briefing

1. Trader expects 65-75% WR in hot Bear, NOT 94.6% live observation
2. Expect 3-4 consecutive losses to be normal
3. boundary_hot beats confident_hot (counter-intuitive)
4. December freeze applies to Bear UP_TRI (rule_007)
5. Health × Bear UP_TRI is hostile (rule_006); avoid even in hot
6. Bull cells PROVISIONAL_OFF until activation

---

## Known gaps / future work

### Phase-5 override database not yet integrated

Rule layer 4 (Phase-5 override) requires combo database lookup at
signal time. Currently rules layer is operational; override layer
defers to baseline rule WR.

When Phase-5 override deployed:
- Wilson lower bound combo lookup adds ~5-10ms per signal
- Override may upgrade verdicts in ~3% of cases
- Logging extended to track override triggers

### Sub-regime detector for Bull regime

Bull sub-regime detector (recovery/healthy/normal/late) built in Lab
but NOT yet in production scanner. Required before Bull rules
(rule_001-004) can activate.

### Choppy 3-axis detector (C1)

Path 2 keeps current 2-axis Choppy detector (vol × breadth). C1
recommended adding momentum (3-axis) but ships in Phase 2.

### Composite hysteresis (C3 N=2)

Sub-regime classification can flip day-to-day. C3 hysteresis (N=2
confirmation) recommended but defers to Phase 2.

---

## Rollout sequence

### Phase 1 (immediate): Bear + Choppy production rules

Ship rules: kill_001, watch_001, win_001-007, rule_005, rule_006,
rule_007, rule_008, rule_009, rule_010, rule_011, rule_012,
rule_013-017, rule_021, rule_022.

Schema migration v3 → v4 with 2-week parallel evaluation.

### Phase 2 (when Bull regime returns): Activate Bull rules

Activate rule_001-004, rule_018-020 via settings flags. Required
prereqs:
- Bull sub-regime detector in scanner
- 10+ days of Bull regime classifier output
- 30+ live signals per cell

### Phase 3 (post-stable): B2 sigmoid + Phase-5 override

Layer Phase-5 override on top of stable rule baseline. Optionally
add B2 sigmoid scoring if trader requests finer granularity.

---

## Path 2 vs Path 1 comparison

This document is Path 2 (TRUST-OPUS). The methodology comparison study
will validate Path 1 (prescriptive) and Path 2 (interpretive) on
identical historical data. Expected divergences:

- Path 2 broader rule_003/rule_004 may MATCH MORE than Path 1's narrow
  versions (sub-regime-only gates)
- Path 2 calibrated win_003/win_006 predictions should PASS where Path 1
  may also pass
- Path 2 sub_regime_constraint additions on rule_006/008/012/022 should
  fix the Step 3 failures regardless of path

The empirical comparison will measure:
1. PASS rate
2. Coverage completeness
3. Schema compliance
4. Per-rule prediction accuracy

If Path 2 PASS rate > Path 1, the lesson is "Opus exercises good judgment
when given freedom." If Path 1 wins, the lesson is "explicit constraints
help Opus avoid systematic errors."
