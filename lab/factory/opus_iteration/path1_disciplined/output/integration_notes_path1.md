# Integration Notes — Path 1 (Disciplined)

**Date:** 2026-05-03
**Scope:** 8-week deployment plan, schema migration, cutover criteria
for Path 1's 24-rule unified rule set.

---

## Why bucket threshold registry is required

`path1_thresholds_explicit.md` is the AUTHORITATIVE source for Lab
feature library + sub-regime detector thresholds. Step 3's 38% PASS
rate was largely driven by the validation harness using 33/67 tertile
splits while Lab analyses used fixed thresholds (e.g., breadth<0.30,
swing_high<2, fvg<2).

**Production must persist `path1_thresholds_explicit.md` as a
versioned config file.** Both rule generation (Lab → rules.json) and
rule evaluation (production matcher) must read from the same threshold
registry. Drift between Lab and production thresholds is the #1 risk
for Step 3-style failures.

### Persistence approach

1. Commit `lab/output/feature_thresholds_v4.json` as machine-readable
   threshold registry derived from `path1_thresholds_explicit.md`
2. Production scanner enrichment pipeline reads thresholds at scan time
3. Rule conditions in unified_rules_path1.json reference numeric
   thresholds directly (preferred) OR bucket labels that map to the
   registry (acceptable for categorical features only)

### Schema for the registry

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-03T00:00:00Z",
  "feature_library": {
    "feat_market_breadth_pct": {"low": 0.30, "high": 0.60, "type": "continuous"},
    "feat_swing_high_count_20d": {"low": 2, "high": 3, "type": "integer"},
    "feat_nifty_vol_regime": {"values": ["Low", "Medium", "High"], "type": "categorical"},
    ...
  },
  "subregime_detectors": {
    "bear": {
      "axes": ["nifty_vol_percentile_20d", "nifty_60d_return_pct"],
      "hot_thresholds": {"vp": 0.70, "n60": -0.10},
      ...
    },
    "bull": {
      "axes": ["nifty_200d_return_pct", "market_breadth_pct"],
      "p_low_high": [0.05, 0.20],
      "s_low_high": [0.60, 0.80],
      ...
    },
    ...
  }
}
```

---

## Why sub_regime_constraint is critical

Step 3 rule_007 (Health × Bear UP_TRI) FAILED because the rule had no
sub_regime_constraint. Result: rule matched all 311 lifetime Bear Health
UP_TRI signals at 48.6% (Bear Health baseline) instead of the intended
~158 hot subset at 32.4% (the actual hostile cohort).

Path 1 mandate: **every rule whose Lab finding specifies a sub-regime
MUST carry sub_regime_constraint as a top-level field**, not just as a
condition. The condition redundancy
(`{"feature": "sub_regime", "value": "hot", "operator": "eq"}`) is for
audit trail; the top-level field is the production gate.

### Affected rules in Path 1

Rules with sub_regime_constraint set:
- win_007 (hot)
- rule_001 (late_bull)
- rule_002 (late_bull)
- rule_003 (recovery_bull)
- rule_004 (healthy_bull)
- rule_006 (late_bull)
- rule_007 (hot)
- rule_012 (cold)

Rules WITHOUT sub_regime_constraint (intentional — match across
sub-regimes):
- All sector boost rules (win_001-006) — Bear UP_TRI sector boost
  applies in any sub-regime; hot/warm just amplifies sizing
- All calendar kill rules (rule_008, rule_009, rule_014, rule_018)
- Calendar boost (rule_011)

---

## Phase-5 override mechanism (B3) integration

Phase-5 override is the Layer 4 modulator in precedence_logic. Production
integration:

### Combo database

Source: `lab/output/combinations_live_validated.parquet` (5,057 rows;
82 VALIDATED, 60 PRELIMINARY, 252 REJECTED, rest WATCH).

### Lookup at scan time

```python
def lookup_phase5_override(signal, market_state, combo_db):
    matching = combo_db.query(
        regime=signal.regime,
        signal_type=signal.signal,
        feature_match=signal.features,
    )
    validated = [
        c for c in matching
        if c.live_tier == "VALIDATED"
        and c.live_n >= 10
        and c.live_window_recent_90d
    ]
    if not validated:
        return None
    best = max(validated, key=lambda c: c.wilson_lower_95)
    return best
```

### Override decision

```python
def apply_override(base_wr, override_combo):
    if override_combo is None:
        return base_wr, "sub_regime_base"
    if override_combo.wilson_lower_95 > base_wr + 0.05:
        return override_combo.wilson_lower_95, f"phase5_{override_combo.combo_id}"
    return base_wr, "sub_regime_base"
```

### Wilson lower bound pre-computation

Pre-compute `wilson_lower_95` per combo at Phase-5 build time. Stored
as parquet column. No runtime computation.

### Recency check

`live_window_recent_90d` is precomputed bool. Combos lose VALIDATED
tier if no matches in last 90 days.

---

## 8-week deployment plan

### Week 1: Schema migration v3 → v4 (parallel)

- Deploy unified_rules_path1.json alongside existing
  mini_scanner_rules.json
- Production scanner reads from BOTH; emits parallel decisions
- Decision divergence logged for audit; no behavioral change

### Week 2: Threshold registry persistence

- Commit `feature_thresholds_v4.json` as authoritative
- Update scanner enrichment pipeline to read from registry
- Validate that registry matches Lab analyses (cross-check on 5
  worked examples from Step 1.5+2 SY)

### Week 3: Sub-regime detector deployment

- Bear sub-regime detector deployed to pre-market composer
- Bull sub-regime detector deployed (when Bull regime active)
- `current_subregime.json` writes confirmed in scan logs
- Telegram digest extended with sub-regime label + WR range

### Week 4: HIGH priority rules go live

- 5 HIGH priority NEW rules + 9 EXISTING rules activated
  (rule_001-007, win_001-007, kill_001, watch_001)
- Shadow mode: log decisions but don't act
- Compare shadow decisions to manual trader review

### Week 5: MEDIUM priority rules go live

- 5 MEDIUM rules activated (rule_008, rule_009, rule_010, rule_011,
  rule_012)
- Shadow mode continues
- Step 4 validation report runs; PASS rate target ≥80%

### Week 6: Phase-5 override integrated

- Combo database deployment complete
- Override lookup integrated into Layer 4
- Wilson lower bound calibration validated against B3 spec

### Week 7: Live cutover for HIGH+MEDIUM rules

- Exit shadow mode for production_ready=true rules
- Trader briefed on calibrated WR expectations (e.g., Bear UP_TRI
  hot 65-75%, NOT 94.6%)
- Monitor live WR vs predicted for 2 weeks

### Week 8: LOW priority rules promotion

- 5 LOW rules (rule_013, rule_014, rule_015, rule_016, rule_017,
  rule_018) promoted to production_ready=true if shadow mode
  validates predictions
- Path 2 comparison initiated (Path 1 vs Path 2 head-to-head)

---

## Schema migration: v3 → v4 details

### Breaking changes

- `regime_alignment` field removed (was unused, active=false in v3)
- `boost_patterns` / `kill_patterns` / `warn_patterns` arrays
  consolidated into single `rules` array with `type` field
- `sub_regime_constraint` top-level field added
- `conditions` array supports arbitrary feature-value-operator triples

### Backward compatibility

Existing v3 rules (kill_001, watch_001, win_001-007) re-emitted with:
- Empty `conditions` array (since v3 had no conditions)
- `sub_regime_constraint=null` (except win_007 which adds 'hot' gate)
- `match_fields` populated from old top-level signal/sector/regime fields

### Parallel evaluation

For 2 weeks (Weeks 1-2 of deployment), both v3 and v4 evaluators run
on every signal. Divergence is logged. v4 cuts over only when:
- Divergence rate < 2% across 100+ signals
- All divergences are explainable by intentional v4 changes (e.g.,
  sub_regime_constraint adding gating)

---

## Cutover criteria

### Criteria for HIGH priority rule cutover (Week 7)

- Shadow PASS rate ≥80% on Step 4 validation
- 0 divergences in win_001-007 outputs vs v3 (compatibility check)
- Trader signs off on calibrated WR expectations
- Telegram digest tested in test channel for ≥10 trading days

### Criteria for LOW priority rule promotion (Week 8)

- Shadow PASS rate ≥75% on LOW rules (lower bar; LOW is fine-tuning)
- No catastrophic decisions in shadow log (no SKIP-ed wins / TAKE-d
  catastrophic losses)
- Live WR per rule matches predicted band ±10pp

### Criteria for Path 1 vs Path 2 selection (Week 8+)

- Path 1 PASS rate
- Path 2 PASS rate
- Trader preference (interpretability)
- Maintenance complexity (Path 1 is more constrained = simpler to
  maintain)

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Threshold registry drift between Lab and production | HIGH | Single source of truth (feature_thresholds_v4.json); CI check on Lab analyses |
| Sub-regime detector failure on edge cases | MEDIUM | Fail-closed: unknown → SKIP cascade |
| Phase-5 override database staleness | MEDIUM | 90-day recency check; quarterly Phase-5 re-runs |
| LOW priority rules over-restricting in production | LOW | production_ready=false initially; promote only after shadow validation |
| Trader surprise from calibrated WR (Bear UP_TRI 65-75% vs live 94.6%) | MEDIUM | Pre-cutover briefing; expected drawdown distributions communicated |
| December freeze missed (rule_008) | LOW | Calendar test in shadow mode |
| Health × Bear UP_TRI hot kill missed (rule_007) | MEDIUM | Sub-regime detector test; rule_007 specifically validated |

---

## Maintenance

### Quarterly Phase-5 re-runs

- Refresh combinations_live_validated.parquet
- Update Wilson lower bounds
- Reclassify combos as VALIDATED / PRELIMINARY / WATCH / REJECTED
  based on accumulated live data
- Detect drift in cell baseline WRs

### Annual rule audit

- Re-run validation harness on all 24 rules
- Identify rules where actual count/WR drifts >20% from prediction
- Decide: deactivate, refit, or reclassify priority

### Bear sub-regime detector refit

- Detector axes are 0.70 vol percentile + -0.10 60d_return
- These are fixed thresholds; if Bear regime structure shifts,
  detector may misclassify
- Consider rolling 12-month percentile recomputation in v2

---

## Summary

Path 1 deploys 24 rules across 8 weeks with shadow mode → live cutover
gating. Sub-regime constraint is a top-level field (not just
condition) for all sub-regime-gated rules. Threshold registry
(`feature_thresholds_v4.json`) is the single source of truth for both
Lab and production. Phase-5 override layers in at Week 6 with B3
mechanism. LOW priority rules ship as production_ready=false initially
and promote in Week 8 after shadow validation.

Path 1's mandate is explicit constraints; this deployment plan
operationalizes that mandate.
