# Integration Notes — v4 Ruleset Production Deployment

This document describes the production deployment plan for the v4
ruleset (14 new rules + 9 existing harmonized = 23 total).

## 1. Ship Order

### Phase A — Week 1: v4 schema published, v3 continues

- Existing 9 v3 rules continue to evaluate signals in production
- v4 schema specification published (this package)
- Validation: v4 prediction file generated; reviewed against
  enriched_signals.parquet (105,987 signals)
- No production behavior change

### Phase B — Weeks 1-3: HIGH priority rules deployed in parallel

Deploy the 5 HIGH priority new rules + 9 existing rules in v4
evaluator running PARALLEL with v3:

**HIGH priority rules (5):**
- rule_001: late_bull SKIP for Bull UP_TRI
- rule_002: late_bull SKIP for Bull BULL_PROXY
- rule_003: recovery_bull × vol=Med × fvg_low TAKE_FULL Bull UP_TRI
- rule_004: healthy_bull × 20d=high TAKE_FULL Bull BULL_PROXY
- rule_005: vol_climax × BULL_PROXY REJECT in Bear
- rule_006: vol_climax × BULL_PROXY REJECT in Bull-late_bull
- rule_007: Health × UP_TRI × Bear AVOID

**Parallel evaluation:**
- v3 evaluator writes verdict to existing `signal.action` field
- v4 evaluator writes verdict to NEW `signal.v4_action` field (shadow)
- Both verdicts logged with `signal.v4_discrepancy_flag` if they differ
- Telegram digest continues to use v3 verdict
- Daily report compares v3 vs v4 verdict distributions

### Phase C — Weeks 3-5: MEDIUM priority rules added

Deploy 5 MEDIUM rules to v4 evaluator (still parallel mode):

- rule_008: December × Bear UP_TRI SKIP
- rule_009: February × Choppy UP_TRI SKIP
- rule_010: Choppy BULL_PROXY REJECT
- rule_011: Bear DOWN_TRI wk2/wk3 filter
- rule_012: Bear UP_TRI cold cascade Tier 1

Continue parallel evaluation. Discrepancy rate target: <5% by end of
week 5.

**Cutover decision at end of week 5:**
- If discrepancy rate <5% AND WR delta <3pp on overlapping signals →
  cutover v4 as primary; v3 retired
- If criteria fail → extend parallel by 2 weeks; investigate
  discrepancies

### Phase D — Months 2+: LOW priority rules after live validation

LOW priority rules ship `production_ready: false` initially:

- rule_013: Bull UP_TRI × Energy SKIP
- rule_014: Bull UP_TRI/PROXY × Sep SKIP
- rule_015: Choppy DOWN_TRI × Pharma SKIP
- rule_016: Choppy DOWN_TRI × Friday SKIP
- rule_017: Choppy UP_TRI × Metal SKIP

Activation criteria per rule:
- ≥30 live signals matching the rule
- Live observed WR within ±5pp of predicted_match_wr
- No adverse trader feedback (e.g., trader manually overrode rule
  >3 times in cohort)

Monthly review of LOW priority rules; flip `production_ready` to true
as criteria are met.

---

## 2. Sub-regime detector requirements

Pre-cutover work required for HIGH priority rules:

### Choppy 3-axis detector (per C1)

- Add `nifty_20d_return_pct` as 3rd detector axis
- 27-cell tri-modal classification (vol × breadth × momentum)
- Tertile thresholds: -1.32% / +0.72% (lifetime-derived)
- Required for: rule_009 (Choppy UP_TRI Feb), rule_010 (Choppy BULL_PROXY)
- Required for any future Choppy rule activation

### N=2 composite hysteresis (per C3)

- Single state variable: `previous_subregime_label`
- N=2 days same label required before flipping production tag
- Bootstrap: NULL on regime change; conservative fallback for first 2
  days
- State file: `output/subregime_state.json` with 7-day staleness check
- Apply to: Choppy 3-axis detector outputs

### Bull sub-regime detector

- Required for: rule_001, rule_002, rule_003, rule_004, rule_006
  (5 of 7 HIGH rules)
- Inputs: `nifty_200d_return_pct`, `market_breadth_pct`
- Outputs: recovery_bull / healthy_bull / normal_bull / late_bull
- Function: `detect_bull_subregime()` per `bull_uptri.md` BU1
- Where: pre-market composer, once per scan day
- Output: `current_subregime.json` field `Bull.label`

**This is PRODUCTION_POSTURE Gap 2** for Bull regime. Cannot ship HIGH
rules 1-4 without it.

### Bear 4-tier classifier (per B1)

- Tier function: `classify_bear_tier(vp, n60)` →
  {confident_hot, boundary_hot, boundary_cold, confident_cold}
- Required for: enhanced display of `win_001`-`win_007` and `rule_007`,
  `rule_008`, `rule_011`, `rule_012`
- Where: pre-market composer + per-signal enrichment
- Output: signal `bear_tier` field

---

## 3. Phase-5 override mechanism

### Architecture

- **Combo database:** `lab/output/combinations_live_validated.parquet`
  (5,057 rows, ~3MB; partition by regime × signal)
- **Wilson lower bound:** pre-computed per combo at Phase 5 build time;
  stored as column in parquet
- **Recency check:** `live_window_recent_90d` boolean precomputed per
  combo

### Lookup performance

- Per-signal lookup: ~5-10ms (parquet partitioned index)
- Memory footprint: 3MB total
- Refresh cadence: quarterly (Phase 5 re-run)

### Override decision

- Trigger: Wilson 95% lower > sub-regime base + 5pp
- Selection (multi-match): max(Wilson_lower)
- Logging: `override_triggered`, `combo_matches_count`, `wr_source`
  per signal

### Audit and drift detection

Daily report tracks:
- Override fire rate (combos by frequency)
- Override-vs-base WR delta on resolved signals (drift signal)
- Combos losing VALIDATED tier (recency expiry)

---

## 4. Schema migration plan (v3 → v4)

### Breaking change with parallel evaluation

v4 is a **breaking change** from v3 schema. Migration path:

1. **Week 1:** v4 evaluator implemented; v3 continues primary
2. **Weeks 2-5:** parallel evaluation; v4 in shadow
3. **Week 5:** cutover decision (criteria below)
4. **Week 5+:** v4 primary; v3 retired

### Cutover criteria (go/no-go)

ALL must pass:

- **Discrepancy rate < 5%**: % of signals where v3 and v4 verdicts
  disagree must be <5%
- **WR delta < 3pp**: on signals where verdicts agree, v3 and v4
  predicted WR must be within 3pp
- **No catastrophic divergence**: zero signals where v3 says TAKE_FULL
  and v4 says REJECT (or vice versa) without documented reason
- **Trader sign-off**: trader has reviewed parallel period and signed
  off on v4 behavior
- **Monitoring stable**: 7 consecutive days of stable parallel logs
  with no errors

### Rollback procedure

If cutover fails:
1. Revert primary evaluator to v3
2. Continue parallel evaluation in v4
3. Investigate discrepancy root causes
4. Fix v4 rules / detectors / composition logic
5. Restart parallel period (4-week minimum before next cutover attempt)

If cutover succeeds but issues surface within 2 weeks:
1. Re-enable v3 as primary (rollback)
2. Retain v4 logs for forensic analysis
3. Investigate; redeploy with fix

### Schema version support

- v3 retired immediately on successful cutover (no dual-active period
  beyond parallel)
- v4 reads compatible with v3 archived data via translation layer
- Future v5 (post B2 sigmoid) will use same migration pattern

---

## 5. Cutover criteria summary

| Criterion | Threshold | Measurement |
|---|---|---|
| Discrepancy rate (v3 vs v4) | < 5% | (signals where verdicts differ) / (total signals) |
| WR delta on agreeing verdicts | < 3pp | mean(\|v3_wr - v4_wr\|) where verdicts agree |
| Catastrophic divergence | 0 instances | TAKE_FULL ↔ REJECT pairs |
| Trader sign-off | yes/no | manual review meeting |
| Parallel duration | ≥ 4 weeks | calendar days in parallel mode |
| Monitoring stability | 7 days no errors | error count in scanner logs |

---

## 6. Open production gaps

These gaps may BLOCK HIGH/MEDIUM rules deployment:

### Gap A: Bull sub-regime detector not in production

**Blocks:** rule_001, rule_002, rule_003, rule_004, rule_006

**Resolution:** Implement `detect_bull_subregime()` in pre-market
composer per `bull_uptri.md` BU1 specification. Inputs are existing
features (`nifty_200d_return_pct`, `market_breadth_pct`). Estimated
effort: 2-4 hours engineering.

**Status:** PRODUCTION_POSTURE Gap 2 (open)

### Gap B: Choppy 3-axis detector not in production

**Blocks:** rule_009 (Choppy UP_TRI Feb), rule_010 (Choppy BULL_PROXY)
operate on existing 2-axis Choppy classification; the 3-axis upgrade
is desirable but not blocking. However composite hysteresis is
required for stability.

**Resolution:** Add `nifty_20d_return_pct` 3rd axis + N=2 hysteresis;
ship together per critique SUMMARY decision.

**Status:** Open; estimated 4-8 hours.

### Gap C: Phase-5 override database not deployed

**Blocks:** Layer 4 override mechanism (does not block any rule
directly, but degrades calibration accuracy)

**Resolution:** Deploy `combinations_live_validated.parquet` to
production scanner; integrate lookup in evaluator. Wilson lower
bounds pre-computed.

**Status:** Open; estimated 2-3 hours.

### Gap D: Bear 4-tier classifier not in production

**Blocks:** B1 tiered display (degrades to binary hot/cold display
if missing)

**Resolution:** Implement tier function; integrate into Telegram
digest formatting; trader briefing on counter-intuitive tier ordering.

**Status:** Open; estimated 2 hours.

### Gap E: `month` and `day_of_week` features not surfaced

**Blocks:** rule_008 (December), rule_009 (February), rule_014
(September), rule_016 (Friday)

**Resolution:** Pre-compute calendar features as scanner enrichment
fields. Trivial transformations of signal date.

**Status:** Likely already in `enriched_signals.parquet`; verify
production scanner exposes via `feat_month`, `feat_day_of_week`.
Estimated effort: 1 hour verification + rename if needed.

### Gap F: `feat_vol_climax_flag` boolean handling

**Blocks:** rule_005, rule_006

**Resolution:** Verify production scanner exposes `feat_vol_climax_flag`
as boolean (not string). Rule schema uses `value: true` (boolean).

**Status:** verify; estimated 30 min.

---

## 7. Deployment timeline summary

| Week | Activity |
|---|---|
| 1 | v4 schema published; v3 continues; predictions reviewed |
| 1-2 | Bull sub-regime detector ships; Bear 4-tier classifier ships; Phase-5 DB deployed |
| 2 | HIGH priority rules + existing 9 deployed in v4 (parallel mode) |
| 3 | MEDIUM priority rules deployed (parallel mode); Choppy 3-axis + hysteresis ships |
| 4 | Parallel monitoring; discrepancy investigation if needed |
| 5 | Cutover decision; if pass, v4 becomes primary |
| 5-8 | Stabilization period; monitor live WR vs predicted; trader feedback |
| 8+ | LOW priority rules activation per individual criteria; B2 sigmoid Phase 2 review at 2027-Q1 |

**Total deployment window: 5 weeks parallel + cutover + 3 weeks
stabilization = 8 weeks to full v4 operation.**

LOW priority rules activate incrementally over months 2-6 as live
validation completes. B2 sigmoid evaluation at 6-month mark.
