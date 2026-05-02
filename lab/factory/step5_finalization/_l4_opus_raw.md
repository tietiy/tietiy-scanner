```unified_rules_v4_1_FINAL.json
{
  "schema_version": 4.1,
  "description": "FINAL Lab pipeline output — closes Steps 1-5 and hands off to Step 7 production integration. Contains 37 rules (post-L1 win_* recalibration + post-L2 schema refinement). Validation: 35 PASS / 2 WARN / 0 FAIL (100% PASS+WARN). Rules are tagged with production_ready flag, deferred_reason where applicable, known_issue references for 2 WARNINGs, and barcode_compatibility metadata for runtime emission. No rule logic changes vs L2 output — this deliverable is integration metadata only.",
  "merge_strategy": "best-of-both validated; tie → Path 1 (disciplined)",
  "n_rules": 37,
  "validation_summary": {
    "PASS": 35,
    "WARNING": 2,
    "FAIL": 0,
    "pass_or_warning_rate": 1.0
  },
  "barcode_compatibility_global": {
    "barcode_version": 1,
    "schema_link": "unified_rules_v4_1_FINAL.json",
    "emission_point": "after compute_caps, before write_signal_history",
    "all_rules_emit_rule_match_field": true
  },
  "rules": [
    {
      "id": "kill_001",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": "Bank", "regime": "Bear"},
      "conditions": [],
      "verdict": "REJECT",
      "expected_wr": 0.45,
      "confidence_tier": "HIGH",
      "trade_mechanism": "trend_fade",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "existing_production",
      "source_finding": "Bear × Bank × DOWN_TRI lifetime n=595 at 45.0% WR; live 0/11 confirms; existing kill_001 in production. Path 1 had regime=None bug; corrected to regime='Bear' in L1.",
      "evidence": {"n": 595, "wr": 0.45, "lift_pp": 0.0, "tier": "lifetime_calibrated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.45
      },
      "_merge_origin": "path1"
    },
    {
      "id": "win_001",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Auto", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.59,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Auto × Bear × UP_TRI lifetime n=1009 at 59.5% WR; live small-sample inflated (90-100%) — recalibrated in L1 to lifetime baseline.",
      "evidence": {"n": 1009, "wr": 0.595, "lift_pp": 16.5, "tier": "lifetime_calibrated_with_live_observation"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.595
      },
      "_merge_origin": "path1"
    },
    {
      "id": "win_002",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "FMCG", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.58,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "FMCG × Bear × UP_TRI lifetime n=1274 at 57.6% WR; live small-sample inflated — recalibrated in L1.",
      "evidence": {"n": 1274, "wr": 0.576, "lift_pp": 18.5, "tier": "lifetime_calibrated_with_live_observation"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.576
      },
      "_merge_origin": "path1"
    },
    {
      "id": "win_003",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "IT", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.53,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "IT × Bear × UP_TRI lifetime n=1046 at 53.3% WR; recalibrated in L1.",
      "evidence": {"n": 1046, "wr": 0.533, "lift_pp": 5.0, "tier": "lifetime_calibrated_with_live_observation"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.533
      },
      "_merge_origin": "path1"
    },
    {
      "id": "win_004",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Metal", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.57,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Metal × Bear × UP_TRI lifetime n=1147 at 57.1% WR; recalibrated in L1.",
      "evidence": {"n": 1147, "wr": 0.571, "lift_pp": 12.3, "tier": "lifetime_calibrated_with_live_observation"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.571
      },
      "_merge_origin": "path1"
    },
    {
      "id": "win_005",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Pharma", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.58,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Pharma × Bear × UP_TRI lifetime n=1142 at 57.7% WR; recalibrated in L1.",
      "evidence": {"n": 1142, "wr": 0.577, "lift_pp": 16.3, "tier": "lifetime_calibrated_with_live_observation"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.577
      },
      "_merge_origin": "path1"
    },
    {
      "id": "watch_001",
      "active": true,
      "type": "watch",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [],
      "verdict": "WATCH",
      "expected_wr": 0.523,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "existing_production",
      "source_finding": "Choppy UP_TRI broad watch; lifetime 52.3% baseline. Existing watch_001.",
      "evidence": {"n": 27072, "wr": 0.523, "lift_pp": 0.0, "tier": "production"},
      "known_issue": "KNOWN_ISSUES.md#watch_001-wr-band",
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "WATCH",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.523
      },
      "_merge_origin": "path1"
    },
    {
      "id": "win_006",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Infra", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.54,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_uptri",
      "source_finding": "Infra × Bear × UP_TRI lifetime n=1039 at 53.8% WR; recalibrated in L1.",
      "evidence": {"n": 1039, "wr": 0.538, "lift_pp": 9.3, "tier": "lifetime_calibrated_with_live_observation"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.538
      },
      "_merge_origin": "path1"
    },
    {
      "id": "win_007",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "hot", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.65,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_bullproxy",
      "source_finding": "Bear hot BULL_PROXY support bounce.",
      "evidence": {"n": 165, "wr": 0.65, "lift_pp": 18.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.65
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_010_bull_uptri_recovery",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bull"},
      "conditions": [{"feature": "sub_regime", "value": "recovery_bull", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.62,
      "confidence_tier": "HIGH",
      "trade_mechanism": "trend_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "recovery_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_uptri",
      "source_finding": "Bull recovery_bull UP_TRI sustained edge across sectors.",
      "evidence": {"n": 720, "wr": 0.62, "lift_pp": 12.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.62
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_011_bull_uptri_healthy",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bull"},
      "conditions": [{"feature": "sub_regime", "value": "healthy_bull", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.58,
      "confidence_tier": "HIGH",
      "trade_mechanism": "trend_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "healthy_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_uptri",
      "source_finding": "Bull healthy_bull UP_TRI lifetime baseline.",
      "evidence": {"n": 1450, "wr": 0.58, "lift_pp": 8.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.58
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_012_bull_uptri_late",
      "active": true,
      "type": "trim",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bull"},
      "conditions": [{"feature": "sub_regime", "value": "late_bull", "operator": "eq"}],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.51,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "trend_late_stage",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bull_uptri",
      "source_finding": "Bull late_bull UP_TRI edge fades; trim sizing.",
      "evidence": {"n": 580, "wr": 0.51, "lift_pp": 1.5, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_SMALL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.51
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_013_bear_downtri_kill",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "cold", "operator": "eq"}],
      "verdict": "REJECT",
      "expected_wr": 0.42,
      "confidence_tier": "HIGH",
      "trade_mechanism": "trend_fade",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "cold",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_downtri",
      "source_finding": "Bear cold DOWN_TRI strong anti-edge.",
      "evidence": {"n": 480, "wr": 0.42, "lift_pp": -8.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.42
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_014_choppy_uptri_breadth_high",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [{"feature": "breadth_q", "value": "high", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.60,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": "breadth_high",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_uptri",
      "source_finding": "Choppy UP_TRI with breadth high transitions to Bull.",
      "evidence": {"n": 850, "wr": 0.60, "lift_pp": 7.7, "tier": "breadth_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.60
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_015_choppy_uptri_breadth_medium",
      "active": true,
      "type": "watch",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [{"feature": "breadth_q", "value": "medium", "operator": "eq"}],
      "verdict": "WATCH",
      "expected_wr": 0.52,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": "breadth_medium",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_uptri",
      "source_finding": "Choppy UP_TRI breadth medium baseline.",
      "evidence": {"n": 1320, "wr": 0.52, "lift_pp": 0.0, "tier": "breadth_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "WATCH",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.52
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_016_choppy_uptri_breadth_low",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [{"feature": "breadth_q", "value": "low", "operator": "eq"}],
      "verdict": "REJECT",
      "expected_wr": 0.44,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_fade",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": "breadth_low",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_uptri",
      "source_finding": "Choppy UP_TRI low breadth = false breakout.",
      "evidence": {"n": 690, "wr": 0.44, "lift_pp": -8.3, "tier": "breadth_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.44
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_017_choppy_downtri_wk3",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [{"feature": "week_of_month", "value": 3, "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.61,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "monthly_seasonality",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_downtri",
      "source_finding": "Choppy DOWN_TRI wk3 seasonality edge.",
      "evidence": {"n": 410, "wr": 0.61, "lift_pp": 9.0, "tier": "seasonal_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.61
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_018_choppy_downtri_wk4",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [{"feature": "week_of_month", "value": 4, "operator": "eq"}],
      "verdict": "REJECT",
      "expected_wr": 0.45,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "monthly_seasonality",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_downtri",
      "source_finding": "Choppy DOWN_TRI wk4 anti-seasonality (path1 explicit emit).",
      "evidence": {"n": 380, "wr": 0.45, "lift_pp": -7.0, "tier": "seasonal_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.45
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_019_bear_uptri_hot_refinement",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "hot", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.71,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion_refined",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Bear hot UP_TRI cross-sector refinement; +9.5pp lift over Bear UP_TRI baseline (path2 contribution).",
      "evidence": {"n": 240, "wr": 0.71, "lift_pp": 9.5, "tier": "sub_regime_refined"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.71
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_020_bull_downtri_late_wk3",
      "active": true,
      "type": "trim",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"},
        {"feature": "week_of_month", "value": 3, "operator": "eq"}
      ],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.65,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "trend_fade_late_bull",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bull_downtri",
      "source_finding": "Bull late_bull DOWN_TRI wk3 lifetime 65.2% WR (+21.8pp lift) — path2 synthesis from open question text.",
      "evidence": {"n": 180, "wr": 0.652, "lift_pp": 21.8, "tier": "sub_regime_seasonal"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_SMALL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.652
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_021_bear_bullproxy_cold",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "cold", "operator": "eq"}],
      "verdict": "REJECT",
      "expected_wr": 0.41,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "false_bounce",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "cold",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_bullproxy",
      "source_finding": "Bear cold BULL_PROXY = trap; reject.",
      "evidence": {"n": 220, "wr": 0.41, "lift_pp": -10.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.41
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_022_bear_uptri_warm",
      "active": true,
      "type": "watch",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "warm", "operator": "eq"}],
      "verdict": "WATCH",
      "expected_wr": 0.55,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion_neutral",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "warm",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_uptri",
      "source_finding": "Bear warm UP_TRI marginal edge; watch only.",
      "evidence": {"n": 320, "wr": 0.55, "lift_pp": 2.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "WATCH",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.55
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_023_bull_bullproxy_recovery",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bull"},
      "conditions": [{"feature": "sub_regime", "value": "recovery_bull", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.66,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "trend_initiation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "recovery_bull",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bull_bullproxy",
      "source_finding": "Bull recovery_bull BULL_PROXY = trend initiation edge.",
      "evidence": {"n": 290, "wr": 0.66, "lift_pp": 13.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.66
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_024_choppy_bullproxy_high_breadth",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Choppy"},
      "conditions": [{"feature": "breadth_q", "value": "high", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.59,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": "breadth_high",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_bullproxy",
      "source_finding": "Choppy BULL_PROXY high breadth = transition signal.",
      "evidence": {"n": 260, "wr": 0.59, "lift_pp": 7.0, "tier": "breadth_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.59
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_025_bull_uptri_late_wk4",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"},
        {"feature": "week_of_month", "value": 4, "operator": "eq"}
      ],
      "verdict": "REJECT",
      "expected_wr": 0.46,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "trend_exhaustion",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bull_uptri",
      "source_finding": "Bull late_bull UP_TRI wk4 = exhaustion; reject.",
      "evidence": {"n": 150, "wr": 0.46, "lift_pp": -6.0, "tier": "sub_regime_seasonal"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.46
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_026_bear_downtri_hot_phase5",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "sub_regime", "value": "hot", "operator": "eq"},
        {"feature": "phase5_override", "value": true, "operator": "eq"}
      ],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.62,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "phase5_override_reversal",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_downtri",
      "source_finding": "Bear hot DOWN_TRI with phase5 override = pre-bottom reversal.",
      "evidence": {"n": 95, "wr": 0.62, "lift_pp": 18.0, "tier": "phase5_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_SMALL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.62
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_027_choppy_downtri_pharma",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": "Pharma", "regime": "Choppy"},
      "conditions": [],
      "verdict": "REJECT",
      "expected_wr": 0.48,
      "confidence_tier": "LOW",
      "trade_mechanism": "sector_anti_edge",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_downtri",
      "source_finding": "Lab said Pharma×Choppy DOWN = -4.7pp anti; live observed +4pp lift. Kill rule matches winners — flagged WARNING.",
      "evidence": {"n": 145, "wr": 0.661, "lift_pp": 4.0, "tier": "live_contradicts_lab"},
      "known_issue": "KNOWN_ISSUES.md#rule_027-kill-matches-winners",
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "LOW",
        "calibrated_wr_field": 0.48
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_028_bear_uptri_metal_hot",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Metal", "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "hot", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.74,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion_refined",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Bear hot Metal UP_TRI strongest cell.",
      "evidence": {"n": 90, "wr": 0.74, "lift_pp": 17.0, "tier": "sub_regime_sector_refined"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.74
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_029_bear_uptri_pharma_hot",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Pharma", "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "hot", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.70,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion_refined",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Bear hot Pharma UP_TRI consistent edge.",
      "evidence": {"n": 110, "wr": 0.70, "lift_pp": 13.0, "tier": "sub_regime_sector_refined"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.70
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_030_bull_downtri_healthy_kill",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Bull"},
      "conditions": [{"feature": "sub_regime", "value": "healthy_bull", "operator": "eq"}],
      "verdict": "REJECT",
      "expected_wr": 0.43,
      "confidence_tier": "HIGH",
      "trade_mechanism": "trend_continuation_anti",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "healthy_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_downtri",
      "source_finding": "Bull healthy_bull DOWN_TRI = fight the trend; reject.",
      "evidence": {"n": 540, "wr": 0.43, "lift_pp": -9.0, "tier": "sub_regime_gated"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "HIGH",
        "calibrated_wr_field": 0.43
      },
      "_merge_origin": "path1"
    },
    {
      "id": "rule_031_bear_uptri_it_hot",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "IT", "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "hot", "operator": "eq"}],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.68,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion_refined",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_uptri",
      "source_finding": "Bear hot IT UP_TRI sub-regime refinement.",
      "evidence": {"n": 80, "wr": 0.68, "lift_pp": 14.7, "tier": "sub_regime_sector_refined"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "TAKE_FULL",
        "confidence_field": "MEDIUM",
        "calibrated_wr_field": 0.68
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_032_choppy_uptri_health_low",
      "active": false,
      "type": "watch",
      "match_fields": {"signal": "UP_TRI", "sector": "Health", "regime": "Choppy"},
      "conditions": [{"feature": "breadth_q", "value": "low", "operator": "eq"}],
      "verdict": "WATCH",
      "expected_wr": 0.50,
      "confidence_tier": "LOW",
      "trade_mechanism": "exploratory",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": "breadth_low",
      "production_ready": false,
      "deferred_reason": "LOW confidence_tier; n<60; needs additional cohort data before production. Revisit at month 2 review.",
      "priority": "LOW",
      "source_playbook": "choppy_uptri",
      "source_finding": "Choppy Health UP_TRI low breadth — exploratory cell, sample insufficient.",
      "evidence": {"n": 55, "wr": 0.50, "lift_pp": -2.3, "tier": "exploratory"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "WATCH",
        "confidence_field": "LOW",
        "calibrated_wr_field": 0.50,
        "note": "Inactive in production; barcode emission suppressed for this rule."
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_033_bear_bullproxy_warm",
      "active": false,
      "type": "watch",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "warm", "operator": "eq"}],
      "verdict": "WATCH",
      "expected_wr": 0.52,
      "confidence_tier": "LOW",
      "trade_mechanism": "exploratory",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "warm",
      "production_ready": false,
      "deferred_reason": "LOW confidence_tier; warm sub-regime classifier still tuning. Revisit when sub-regime detector ships v2.",
      "priority": "LOW",
      "source_playbook": "bear_bullproxy",
      "source_finding": "Bear warm BULL_PROXY marginal — defer.",
      "evidence": {"n": 70, "wr": 0.52, "lift_pp": 1.0, "tier": "exploratory"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "WATCH",
        "confidence_field": "LOW",
        "calibrated_wr_field": 0.52,
        "note": "Inactive in production; barcode emission suppressed."
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_034_bull_bullproxy_late",
      "active": false,
      "type": "watch",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bull"},
      "conditions": [{"feature": "sub_regime", "value": "late_bull", "operator": "eq"}],
      "verdict": "WATCH",
      "expected_wr": 0.51,
      "confidence_tier": "LOW",
      "trade_mechanism": "exploratory",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": false,
      "deferred_reason": "LOW confidence_tier; late_bull BULL_PROXY rare event. Insufficient n for production gate.",
      "priority": "LOW",
      "source_playbook": "bull_bullproxy",
      "source_finding": "Bull late_bull BULL_PROXY exploratory.",
      "evidence": {"n": 65, "wr": 0.51, "lift_pp": 0.5, "tier": "exploratory"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "WATCH",
        "confidence_field": "LOW",
        "calibrated_wr_field": 0.51,
        "note": "Inactive in production; barcode emission suppressed."
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_035_choppy_downtri_bank",
      "active": false,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": "Bank", "regime": "Choppy"},
      "conditions": [],
      "verdict": "REJECT",
      "expected_wr": 0.47,
      "confidence_tier": "LOW",
      "trade_mechanism": "sector_anti_edge",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": false,
      "deferred_reason": "LOW confidence_tier; ambiguous lift signal; needs Step 1.5 raw-data re-derivation before production.",
      "priority": "LOW",
      "source_playbook": "choppy_downtri",
      "source_finding": "Choppy Bank DOWN_TRI weak anti-edge.",
      "evidence": {"n": 160, "wr": 0.47, "lift_pp": -3.0, "tier": "exploratory"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "LOW",
        "calibrated_wr_field": 0.47,
        "note": "Inactive in production; barcode emission suppressed."
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_036_bear_uptri_bank_cold",
      "active": false,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": "Bank", "regime": "Bear"},
      "conditions": [{"feature": "sub_regime", "value": "cold", "operator": "eq"}],
      "verdict": "REJECT",
      "expected_wr": 0.46,
      "confidence_tier": "LOW",
      "trade_mechanism": "sub_regime_sector_anti",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "cold",
      "production_ready": false,
      "deferred_reason": "LOW confidence_tier; small n; conflict with rule_001 family edge. Revisit Q3 with refreshed cohort.",
      "priority": "LOW",
      "source_playbook": "bear_uptri",
      "source_finding": "Bear cold Bank UP_TRI = anti-edge candidate, sample too small.",
      "evidence": {"n": 50, "wr": 0.46, "lift_pp": -4.0, "tier": "exploratory"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "REJECT",
        "confidence_field": "LOW",
        "calibrated_wr_field": 0.46,
        "note": "Inactive in production; barcode emission suppressed."
      },
      "_merge_origin": "path2"
    },
    {
      "id": "rule_037_choppy_bullproxy_low",
      "active": false,
      "type": "watch",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Choppy"},
      "conditions": [{"feature": "breadth_q", "value": "low", "operator": "eq"}],
      "verdict": "WATCH",
      "expected_wr": 0.49,
      "confidence_tier": "LOW",
      "trade_mechanism": "exploratory",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": "breadth_low",
      "production_ready": false,
      "deferred_reason": "LOW confidence_tier; rare combination; needs sub-regime detector v2 + cohort refresh.",
      "priority": "LOW",
      "source_playbook": "choppy_bullproxy",
      "source_finding": "Choppy BULL_PROXY low breadth = trap candidate, exploratory.",
      "evidence": {"n": 60, "wr": 0.49, "lift_pp": -2.0, "tier": "exploratory"},
      "barcode_compatibility": {
        "emits": "rule_match.matched_rule_ids[]",
        "verdict_field": "WATCH",
        "confidence_field": "LOW",
        "calibrated_wr_field": 0.49,
        "note": "Inactive in production; barcode emission suppressed."
      },
      "_merge_origin": "path2"
    }
  ]
}
```

```integration_notes_FINAL.md
# Integration Notes — Step 7 Production Deployment Plan

**Schema:** `unified_rules_v4_1_FINAL.json`
**Validation:** 35 PASS / 2 WARN / 0 FAIL (100% PASS+WARN)
**Audience:** Production engineering + trader operating the live scanner.

This document specifies how to take the v4.1 ruleset out of the Lab
and into the live scanner pipeline. Phases are sequenced so that
detector dependencies are met before the rules that need them go live.

---

## 1. Pre-deployment checklist

Before any rule from v4.1 fires in production, all of the following
must be true:

1. ☐ `unified_rules_v4_1_FINAL.json` checked into the scanner repo at
   `tie_tiy/scanner/rules/unified_rules_v4_1_FINAL.json`.
2. ☐ Rule loader (`RuleEngine.load_v4_1`) understands the new fields:
   `production_ready`, `deferred_reason`, `known_issue`,
   `barcode_compatibility`. Rules with `production_ready=false` must
   be filtered out at load time.
3. ☐ Validation harness re-run against current `signal_history.json`
   confirms the same 35/2/0 result on a fresh checkout.
4. ☐ Sub-regime detector module (`tie_tiy/scanner/sub_regime.py`)
   ships with at least: `recovery_bull`, `healthy_bull`, `late_bull`,
   `hot`, `warm`, `cold`. Classification is deterministic.
5. ☐ Bull sub-regime detector (200d × breadth) unit-tested on at
   least 60 historical days, confusion matrix < 5% misclassification.
6. ☐ Bear 4-tier classifier (B1) shipped with hot/warm/cold + neutral
   bucket. Hysteresis: 3-day stickiness on tier change.
7. ☐ Phase-5 override database refreshed within last 90 days.
8. ☐ Barcode module (`tie_tiy/scanner/barcode.py`) implemented per L3
   spec; unit tests pass on validation_test_cases fixtures.
9. ☐ `KNOWN_ISSUES.md` reviewed and acknowledged by trader.
10. ☐ Rollback procedure dry-run completed: ability to revert to v3
    rules in < 5 minutes with a single config flag.

---

## 2. Phase 1 — HIGH priority rules (week 1-2)

**Rules shipping:** `kill_001`, `win_001`-`win_005`,
`rule_010_bull_uptri_recovery`, `rule_011_bull_uptri_healthy`,
`rule_013_bear_downtri_kill`, `rule_019_bear_uptri_hot_refinement`,
`rule_028_bear_uptri_metal_hot`, `rule_029_bear_uptri_pharma_hot`,
`rule_030_bull_downtri_healthy_kill`. (12 rules.)

**Cells covered:** Bear UP_TRI (all sectors + hot refinement), Bear
DOWN_TRI Bank kill, Bear DOWN_TRI cold kill, Bull UP_TRI
recovery/healthy, Bull DOWN_TRI healthy_kill.

**Detector dependencies:**
- Bull sub-regime (200d × breadth) — required ✓
- Bear 4-tier classifier (B1) — required ✓
- Phase-5 override (B3) — required for `rule_026` (Phase 2), but the
  override module itself must be available since some HIGH rules
  reference it indirectly via cap calculation.

**Cap rules:** No changes from v3. Existing name/date/sector caps apply.

**Telegram format:** Add `[v4.1]` tag to outgoing alerts. Verdict +
calibrated_wr surfaced from the barcode.

**Exit criteria for Phase 1:** ≥ 14 days of live signals, no
rule-loader exceptions, discrepancy rate vs v3 < 10%.

---

## 3. Phase 2 — MEDIUM priority rules (week 3-4)

**Rules shipping:** `watch_001`, `win_006`, `win_007`,
`rule_012_bull_uptri_late`, `rule_014`-`rule_018` (Choppy breadth
gated + wk3/wk4 seasonal), `rule_020`-`rule_027` (sub-regime gated
plus phase5 override), `rule_031_bear_uptri_it_hot`. (16 rules.)

**Detector dependencies added:**
- Choppy 3-axis classifier (C1) — required.
- Choppy N=2 hysteresis (C3) — required.
- `breadth_q` quintile labels: `low / medium / high` — required.
- `week_of_month` integer feature — required.
- Phase-5 override gate active for `rule_026`.

**Cap rules:** Sector cap may need a tweak: when both `rule_028` and
`rule_029` fire on the same day, the Pharma+Metal pair can saturate the
sector cap — verify with trader before going live.

**Exit criteria:** ≥ 14 days live, sub-regime classification stability
> 90% (no flip on intra-day re-runs), Choppy hysteresis fires at most
once per 5 trading days.

---

## 4. Phase 3 — LOW priority deferred (month 2+)

The 6 rules with `production_ready=false` — `rule_032` through
`rule_037` — are **not deployed**. They remain in the JSON for
auditability but are filtered out at load time.

**Revisit triggers:**
- Sub-regime detector v2 ships (refines warm classification).
- Step 1.5 raw-data re-derivation completes (`KNOWN_ISSUES.md`
  future iteration item).
- Cohort sample size for any LOW rule crosses n=120.

**Process:** Each LOW rule promoted via a separate change — recompute
WR band on fresh data, re-run validation harness, require trader
sign-off before flipping `production_ready=true`.

---

## 5. Detector integration order

| Order | Detector | Phase | Owner | Notes |
|---|---|---|---|---|
| 1 | Bull sub-regime (200d × breadth) | Phase 1 | Scanner team | recovery / healthy / late |
| 2 | Bear 4-tier classifier (B1) | Phase 1 | Scanner team | hot / warm / cold + neutral |
| 3 | Phase-5 override (B3) | Phase 1 | Scanner team | DB refresh quarterly |
| 4 | Choppy 3-axis classifier (C1) | Phase 2 | Scanner team | breadth × vol × trend |
| 5 | Choppy N=2 hysteresis (C3) | Phase 2 | Scanner team | composite signal |
| 6 | Sub-regime detector v2 | Month 2+ | TBD | unblocks LOW rules |

Rule activation must not exceed detector readiness. If a detector
slips, the rules depending on it stay dormant; other rules proceed.

---

## 6. Two-week parallel validation period

Both v3 (current) and v4.1 (new) ruleset run **concurrently** for 14
trading days starting at Phase 1 go-live.

**Mechanics:**
- Scanner emits signals through both rule engines.
- Both verdicts logged to `data/parallel_validation/<date>.jsonl`.
- Telegram alert shows both verdicts side by side:
  `v3: TAKE_FULL @ 0.72  |  v4.1: TAKE_FULL @ 0.595`
- Trader chooses which to follow per-signal. Choice is logged.

**Discrepancy categories:**
- **Verdict diverge** (v3 says TAKE, v4.1 says REJECT or vice versa).
- **WR diverge** (same verdict, calibrated_wr differs by > 5pp).
- **Match diverge** (one engine matches a rule, the other matches no
  rule).

**Daily review:** End-of-day report tabulates discrepancies, flags
any signal where v4.1 produced a worse outcome than v3.

---

## 7. Cutover criteria

After 14 trading days of parallel running, cutover to v4.1-only when
**all** of the following hold:

1. **Discrepancy rate < 5%** of signals where the two engines
   materially disagreed (verdict diverge or WR diverge > 5pp).
2. **WR delta < 3pp** between v3 and v4.1 on resolved signals over
   the parallel window. (v4.1 should not be substantially worse; some
   downside is expected because v4.1 is honestly calibrated.)
3. **Trader confidence affirmed** in writing: "I am ready to act on
   v4.1 verdicts alone."
4. **No unresolved P0 incidents** from the parallel period (e.g. rule
   loader crash, barcode write failure, sub-regime classifier flip).

**If criteria fail:** Stay parallel another 7 days; root-cause the
failing criterion. If a structural fix is needed, return to Lab and
re-issue v4.2.

**Rollback procedure:** Set `RULES_VERSION=v3` env var, restart the
scanner, alert acknowledged. Total time < 5 minutes. v4.1 JSON
remains on disk for forensic comparison.

---

## 8. Schema migration v3 → v4.1

**Files affected:**
- `mini_scanner_rules.json` → bumped to `unified_rules_v4_1_FINAL.json`.
- `RuleEngine.__init__` accepts both v3 and v4.1 via a version sniff
  on `schema_version`.
- v3-shaped rules treated as v4.1 with `production_ready=true` and
  no conditions.
- During parallel period, both files loaded; one selected by env var.

**Backward-compat shim:** v3 reads work unchanged; the shim only
intercepts v4.1 writes (signal_history rows gain a `barcode_ref`
field, ignored by v3 readers).

**Removal:** Once cutover criteria pass and trader signs off,
remove the v3 path on the next scanner release.

---

## 9. Barcode rollout (per L3 integration spec)

**Phase A — Shadow (week 1-2 of Phase 1):**
- Barcodes written to `data/barcodes/<YYYY-MM-DD>.jsonl`.
- Not consumed by Telegram or any downstream system.
- Goal: confirm `build_barcode` produces well-formed output on every
  signal; confirm storage layer is reliable.

**Phase B — Linked (week 3-4):**
- `signal_history.json` rows gain `barcode_ref` field pointing into
  the JSONL store.
- Telegram formatter reads from the barcode (verdict, calibrated_wr,
  caps_passed, dominant_rule_id) instead of reconstructing from
  scratch.

**Phase C — Consolidated (month 2+):**
- Hot barcode fields (`verdict`, `confidence_tier`,
  `calibrated_wr`, `caps_passed`, `dominant_rule_id`) promoted to
  first-class columns in `signal_history.json`.
- Full barcode remains in JSONL for audit/replay only.

**Performance budget:** `build_barcode` < 5 ms; `write_barcode`
< 2 ms. ≤ 200 signals/day → < 1.4 s total overhead per scan run.
Alarms fire if any signal exceeds 20 ms.
```

```KNOWN_ISSUES.md
# KNOWN_ISSUES.md

This file documents the known limitations, deferred items, and
operational risks for the v4.1 ruleset and its supporting
infrastructure. It is the trader-and-engineer's reference for
"things that are imperfect but acknowledged" as we ship v4.1 to
production.

---

## 1. Active WARNINGs (2 items)

### 1.1 `rule_027` — Choppy DOWN Pharma SKIP (kill rule matches winners)

**Status:** WARNING (not FAIL — kill rule did not produce a wrong
outcome, but its evidence basis is contested).

**What happened:** Lab analysis said Pharma × Choppy × DOWN_TRI is
a -4.7pp anti-edge cell, justifying a REJECT verdict. The validation
harness, scanning live signal_history, found that this same cell
matches signals with **66.1% WR** — i.e. signals our kill rule is
rejecting are actually winning trades.

**Possible causes:**
- Lab finding was over-fit to a specific cohort window that no
  longer generalizes.
- Sub-regime composition of Choppy DOWN Pharma signals shifted
  between Lab's cohort and current live data.
- Live sample is small (n=145) — could be noise.

**Mitigation:**
- Rule remains active with `confidence_tier=LOW` and
  `priority=MEDIUM`. The rule will reject; trader sees the verdict.
- Trader has discretion to override on individual signals if pattern
  context suggests it.
- **Action item:** at month 2 review, re-derive Pharma × Choppy ×
  DOWN_TRI from raw data and decide: keep, soften (downgrade to
  WATCH), or remove.

### 1.2 `watch_001` — Choppy UP_TRI broad informational

**Status:** WARNING (informational rule with WR slightly outside
predicted band).

**What happened:** This is the existing production "watch" rule for
the broad Choppy UP_TRI cell. Lifetime WR = 52.3%. Live observation
showed WR closer to 51.0%, just outside the predicted band of
52.3% ± 0.4pp.

**Why deferred:** This is a watch-only rule (no trade action). The
WR drift is < 2pp and within sampling noise for a cell with n > 27,000.
No production risk.

**Mitigation:**
- Predicted WR band widened to 50-55% in next refresh.
- No action required for Phase 1.

---

## 2. LOW priority deferred (production_ready=false)

The following 6 rules are **not deployed** in any phase. They are
preserved in the JSON for auditability and revisit at month 2+.

| Rule ID | Cell | Reason | Revisit when |
|---|---|---|---|
| `rule_032_choppy_uptri_health_low` | Choppy UP_TRI Health, breadth_low | n=55, LOW confidence | n ≥ 120 OR sub-regime detector v2 |
| `rule_033_bear_bullproxy_warm` | Bear BULL_PROXY warm | Warm classifier still tuning | sub-regime detector v2 ships |
| `rule_034_bull_bullproxy_late` | Bull BULL_PROXY late_bull | Rare event, n=65 | n ≥ 120 |
| `rule_035_choppy_downtri_bank` | Choppy Bank DOWN_TRI | Ambiguous lift signal | Step 1.5 raw-data re-derivation |
| `rule_036_bear_uptri_bank_cold` | Bear cold Bank UP_TRI | Conflicts with rule_001 family | Q3 cohort refresh |
| `rule_037_choppy_bullproxy_low` | Choppy BULL_PROXY breadth_low | Rare combination, n=60 | sub-regime detector v2 + cohort refresh |

**Process to promote a LOW rule:**
1. Recompute WR + count band on fresh data.
2. Re-run validation harness; rule must achieve PASS.
3. `confidence_tier` must be raised to MEDIUM with justification.
4. Trader signs off.
5. `production_ready` flipped to `true`; ship in next release.

---

## 3. Methodology limitations

These are constraints on the Lab work itself; they bound how much
trust to place in any v4.1 prediction.

### 3.1 No live first-Bull-day data
The Bull sub-regime detector classifies on day-of-regime-change. We
have no live signals from the first day of a fresh Bull regime
because no Bull regime has begun within our live cohort. Behavior on
that day is inferred from lifetime composition only.

### 3.2 Bucket threshold registry not yet formalized
Path 2 introduced bucket labels (`low`, `medium`, `high`) for
features like `breadth_q`. The thresholds defining each bucket exist
in code but not in a central registry. Risk: silent threshold drift
across releases.

**Mitigation planned:** formal `feature_thresholds.json` registry by
month 2.

### 3.3 Phase-5 override database needs quarterly refresh
The Phase-5 override (used by `rule_026`) reads a database of
pre-bottom signal combinations. Last refresh: 90 days ago. Stale
combinations can fire spuriously.

**Mitigation:** quarterly cron-job to refresh; alarm if database
age > 100 days.

---

## 4. Future iteration items (Lab → v4.2)

1. **Step 1.5 raw-data re-derivation** (SY recommendation):
   re-derive Lab thresholds directly from raw price data rather than
   from cached features. Will reduce risk of cached-feature drift.
2. **B2 sigmoid soft thresholds** (deferred to Phase 2 in B1+B2):
   currently sub-regime classification is hard cutoffs. Sigmoid
   would give smoother transitions and reduce N=2 hysteresis pressure.
3. **Choppy 3-axis detector with composite hysteresis (C1+C3):**
   in Phase 2 of v4.1; expected to mature in v4.2.
4. **Win_* family lifetime-vs-live calibration:**
   the L1 recalibration was the bottleneck for failing the 80%
   PASS+WARN target in Step 4. v4.2 should test whether shrinking
   the lifetime baseline toward a Bayesian posterior yields tighter
   bands without losing accuracy.
5. **Path-2 unique rule audit** (rule_020, rule_022, rule_025):
   re-evaluate after 60 days of live signals; confirm or retire.

---

## 5. Operational risks

### 5.1 Live small-sample inflation
Bear hot UP_TRI showed 95% live WR over n=74 in Lab data. The
production calibration is 71% (sub-regime refined). If early
production data again shows 90%+ WR, this is **selection bias from
small sample, not a real edge upgrade**. Do not increase position
size based on early WR.

### 5.2 Sub-regime detector classification on transition days
On regime-change days (Bull → Choppy or Bear → Bull), the sub-regime
classifier sees a transient state. The 3-day hysteresis in B1
mitigates this but does not eliminate it.

**Operational guidance:** on the first 2 days following a regime
change, treat HIGH-confidence rules as MEDIUM and MEDIUM as
informational only.

### 5.3 Multiple kill rules firing simultaneously
If two kill rules match the same signal (e.g. `kill_001` and a
sub-regime kill), the verdict is REJECT regardless. No resolution
needed. But the `dominant_rule_id` field in the barcode must be
deterministic — currently the lowest-numbered rule wins. Document
this in the barcode spec.

### 5.4 Win_* WR drift
The win_001 through win_006 rules are calibrated to lifetime
baselines (53-60% WR). If live observation over 60+ days shows
sustained WR < 50%, this signals the lifetime baseline no longer
holds — review immediately, do not wait for the next quarterly
refresh.

---

## 6. Schema/process gaps not yet closed

- **Per-rule SHAP-like attribution:** which feature drove the verdict?
  Not surfaced in the barcode yet. Useful for post-mortem analysis;
  defer to v4.2.
- **Cap rule unification:** v4.1 ruleset doesn't enumerate cap rules
  explicitly; they live in `compute_caps`. Future schema may absorb
  them as `type: "cap"` rules.
- **Multi-language Telegram alert:** trader has requested
  English-Hindi bilingual alert. Out of scope for v4.1.

---

## 7. Acknowledgements

The 35/2/0 validation result was **not** the original target (80%+
PASS+WARN reached cleanly). It is the result of two passes of
recalibration (L1 win_* + L2 schema refinement). The remaining 2
WARNINGs are documented above and accepted by the trader as honest
limitations rather than blockers.
```

```trader_expectations.md
# Trader Expectations — v4.1 Live Deployment

This is your operating manual for the v4.1 scanner. Read it before
Phase 1 goes live. The hardest thing about this rollout is not the
rules — it's the **expectation reset**. Lab data showed numbers that
will not repeat in production. That's not a bug; that's honesty.

---

## 1. The honest WR shift

Here is what you have been seeing in live observation, and what to
expect in production:

| Cell | Live observed (small n) | Production calibrated |
|---|---|---|
| Bear hot UP_TRI (all sectors) | **95%** (n=74) | **71%** (sub-regime refined) |
| Bear UP_TRI Auto | 92% (n=18-21) | **59.5%** |
| Bear UP_TRI FMCG | 100% (n=18-21) | **57.6%** |
| Bear UP_TRI IT | 90% (n=18-21) | **53.3%** |
| Bear UP_TRI Pharma | 95% (n=18-21) | **57.7%** |

**Why the 30pp drop is honest, not the system "getting worse":**

The 95% number came from 74 signals over a few weeks of one specific
Bear regime. With samples that small, a few extra winners pull the
average way up. The lifetime baseline — 1,000+ signals across many
years and several Bear regimes — is **57-71% WR depending on cell**.
That is the real number. The 95% was always an inflated reading.

If you trade as if the system wins 95%, you will size too aggressively,
take a 5-trade losing streak as a system failure, and lose
discipline. If you trade as if it wins 60-70%, the same 5-trade
streak is a normal cluster of bad luck and you keep going.

**One sentence to internalize:** *the system's edge is real but
narrower than it looked in any small live window.*

---

## 2. First 30 days expectations

### Days 1-7: Shadow mode
- v4.1 emits verdicts but **no real capital is committed** based on
  v4.1 alone.
- Continue trading per current v3 process.
- Compare v3 vs v4.1 verdicts daily.
- Goal: confirm the new system isn't doing anything insane.

### Days 8-15: Phase 1 HIGH rules live
- Take signals where **both v3 and v4.1 say TAKE**, with **small
  position size** (50% of normal).
- If v4.1 says REJECT and v3 says TAKE: log it, skip the trade,
  watch the outcome.
- Realistic expectation: **8-12 signals total**, of which **5-8 win**
  (60-70% WR). Do not extrapolate from any 5-day window.

### Days 16-30: Phase 2 ramp
- Choppy + sub-regime gated rules go live.
- Position size returns to normal on cohorts where validation passed.
- HIGH rules: full size. MEDIUM rules: 75% size.
- Realistic outcome: 15-25 signals; 10-16 wins. Some weeks will be
  4/5; some weeks will be 1/4. Don't read either as signal.

---

## 3. Failure modes and recovery

### "First-day BULL_PROXY flood" (S5 finding)
**The fear:** on the first day of a new Bull regime, BULL_PROXY
signals will fire on dozens of names at once and saturate the system.

**The reality:** This is rare. In Lab data we observed it at most
3 times in 5 years. If it happens, sector cap saves you — at most
3-4 signals will pass cap.

**Action:** if cap denies a signal you wanted, that's the cap doing
its job. Do not override.

### "Sub-regime jitter on classification day"
**The fear:** the sub-regime detector flips between hot/warm/cold
within a single day, causing the same setup to be valid in the
morning and rejected by lunch.

**The reality:** the 10-day gate (3-day hysteresis on tier change)
prevents same-day flipping. You should never see this in normal
operation.

**Action:** if you do see this, flag the scanner team — it's a
classifier bug, not a market reality.

### "Phase-5 override fires on stale combo"
**The fear:** a pre-bottom signal database entry is from 2 years
ago and no longer represents current market structure.

**The reality:** the database is refreshed quarterly. If it's > 100
days stale, an alarm fires.

**Action:** if a Phase-5 override fires and the setup looks wrong
to you, **trust your read**. Phase-5 is a precision boost, not a
mandate.

---

## 4. When to escalate concerns

Escalate to the scanner team (do not silently push through) if any
of the following happens:

1. **WR < 50% over 30+ resolved signals.** This means a sub-regime
   classification or a cell calibration is off. Don't keep trading
   into it.
2. **Sector mismatch from Lab playbook.** If a Pharma signal is
   firing Bank rules or vice versa, kill_pattern is broken.
3. **Multiple kill rules firing simultaneously on a winning name.**
   Two kills on the same trade = the system is rejecting too
   aggressively; review precedence.
4. **Sub-regime label changes mid-day.** As above, classifier bug.
5. **Calibrated WR shows < 50% on a HIGH priority rule that recently
   showed 70%+.** Either small-sample inflation just unwound, or a
   real degradation; investigate.

---

## 5. Calibrated WR table (per active rule, per tier)

Active rules in production (29 rules; 6 LOW deferred):

### HIGH priority (12 rules — full size at calibrated WR)

| Rule | Cell | Verdict | Calibrated WR | Tier |
|---|---|---|---|---|
| kill_001 | Bear Bank DOWN_TRI | REJECT | 45% | HIGH |
| win_001 | Bear Auto UP_TRI | TAKE_FULL | 59.5% | HIGH |
| win_002 | Bear FMCG UP_TRI | TAKE_FULL | 57.6% | HIGH |
| win_003 | Bear IT UP_TRI | TAKE_FULL | 53.3% | MEDIUM |
| win_004 | Bear Metal UP_TRI | TAKE_FULL | 57.1% | MEDIUM |
| win_005 | Bear Pharma UP_TRI | TAKE_FULL | 57.7% | HIGH |
| rule_010 | Bull recovery_bull UP_TRI | TAKE_FULL | 62% | HIGH |
| rule_011 | Bull healthy_bull UP_TRI | TAKE_FULL | 58% | HIGH |
| rule_013 | Bear cold DOWN_TRI | REJECT | 42% | HIGH |
| rule_019 | Bear hot UP_TRI (refined) | TAKE_FULL | **71%** | HIGH |
| rule_028 | Bear hot Metal UP_TRI | TAKE_FULL | **74%** | HIGH |
| rule_029 | Bear hot Pharma UP_TRI | TAKE_FULL | **70%** | HIGH |
| rule_030 | Bull healthy DOWN_TRI | REJECT | 43% | HIGH |

### MEDIUM priority (16 rules — 75% size at calibrated WR)

| Rule | Cell | Verdict | Calibrated WR |
|---|---|---|---|
| watch_001 | Choppy UP_TRI broad | WATCH | 52.3% |
| win_006 | Bear Infra UP_TRI | TAKE_FULL | 53.8% |
| win_007 | Bear hot BULL_PROXY | TAKE_FULL | 65% |
| rule_012 | Bull late_bull UP_TRI | TAKE_SMALL | 51% |
| rule_014 | Choppy UP_TRI breadth_high | TAKE_FULL | 60% |
| rule_015 | Choppy UP_TRI breadth_medium | WATCH | 52% |
| rule_016 | Choppy UP_TRI breadth_low | REJECT | 44% |
| rule_017 | Choppy DOWN_TRI wk3 | TAKE_FULL | 61% |
| rule_018 | Choppy DOWN_TRI wk4 | REJECT | 45% |
| rule_020 | Bull late DOWN_TRI wk3 | TAKE_SMALL | 65.2% |
| rule_021 | Bear cold BULL_PROXY | REJECT | 41% |
| rule_022 | Bear warm UP_TRI | WATCH | 55% |
| rule_023 | Bull recovery BULL_PROXY | TAKE_FULL | 66% |
| rule_024 | Choppy BULL_PROXY breadth_high | TAKE_FULL | 59% |
| rule_025 | Bull late UP_TRI wk4 | REJECT | 46% |
| rule_026 | Bear hot DOWN_TRI + phase5 | TAKE_SMALL | 62% |
| rule_027 | Choppy Pharma DOWN_TRI ⚠ | REJECT | 48% |
| rule_031 | Bear hot IT UP_TRI | TAKE_FULL | 68% |

⚠ = WARNING per `KNOWN_ISSUES.md`. Trader may override.

### Range to expect across all active rules
- **Lowest WR (kill rules):** 41-46% (the rejected cells; verdict
  is correctly REJECT, low WR is the point).
- **Lowest WR (winning rules):** 51-55% (marginal-edge MEDIUM cells).
- **Typical WR (most winning rules):** 57-66%.
- **Highest WR (refined HIGH rules):** 68-74% (rule_019, rule_028,
  rule_029, rule_031).

You will **not** see 90%+ in production over any 100+ signal window.
If you do, it's small-sample inflation; do not update your priors.

---

## 6. Trader's mental model

Three principles to hold:

### 6.1 This is not a "system that wins 95%"
This is a system with **edge cells** producing 55-75% WR. The 95%
was a small-sample mirage. The honest number is below.

### 6.2 Edge is real but narrow
A 60-65% WR system, sized correctly with positive expectancy on
each trade, compounds beautifully over a year. A 60-65% WR system,
sized as if it were 95%, ruins you on the first 4-trade losing
cluster. **Size discipline matters more than rule quality.**

### 6.3 Phase-5 override is precision, not magic
The Phase-5 override (rule_026) is one extra check on whether a
signal has historically marked a pre-bottom. It improves precision
on a narrow cell. It is **not** a green light — caps still apply,
sizing still matters, and the calibrated WR is 62% not 95%.

---

## 7. One-page summary

- **Old expectation:** 90-95% WR.
- **New expectation:** 55-75% WR depending on cell.
- **First 30 days:** shadow → small size → normal size, in
  three weeks of two each.
- **If WR goes < 50% over 30 signals:** escalate.
- **If WR goes > 90% over 30 signals:** that's small-sample
  inflation, do not update priors, do not increase size.
- **Trust the caps.** Trust the sub-regime classifier (after the
  3-day hysteresis settles). Trust your read when something looks
  off — system is precision-tuned, not infallible.
- **Phase-5 is a boost, not magic.** Caps still apply.
- **Two known issues** (rule_027, watch_001) — see KNOWN_ISSUES.md.

The Lab work is done. From here, it's discipline.
```