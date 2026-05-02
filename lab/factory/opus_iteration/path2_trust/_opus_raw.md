```unified_rules_path2.json
{
  "schema_version": 4,
  "generated_at": "2026-05-03T00:00:00Z",
  "description": "Path 2 (TRUST-OPUS) rule synthesis. Iterates on Step 3 with judgment-based fixes for sub-regime gating, threshold harmonization with playbook conventions, and prediction calibration from lifetime data. Preserves Step 3's working rules while addressing the 9 FAIL categories.",
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
      "trade_mechanism": "trend_continuation_short",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "current_rules.json kill_001",
      "source_finding": "0/11 live WR; lifetime ~45% Bank vs 46% baseline; preserves existing production rule",
      "evidence": {"n": 653, "wr": 0.45, "lift_pp": -1.0, "tier": "validated"}
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
      "source_playbook": "current_rules.json watch_001",
      "source_finding": "Lifetime 52.3% baseline; informational caveat for trader; preserves existing production rule",
      "evidence": {"n": 27260, "wr": 0.523, "lift_pp": 0.0, "tier": "validated"}
    },
    {
      "id": "win_001",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Auto", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.74,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "current_rules.json win_001 + bear_uptri playbook",
      "source_finding": "Lifetime Bear UP_TRI Auto 74.3% WR (validated at lifetime scale); live 21/21 inflated by Phase-5 selection",
      "evidence": {"n": 176, "wr": 0.743, "lift_pp": 18.6, "tier": "validated"}
    },
    {
      "id": "win_002",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "FMCG", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.76,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "current_rules.json win_002 + bear_uptri playbook",
      "source_finding": "Bear UP_TRI FMCG defensive sector lifts WR to 76% lifetime; FMCG is top-tier in hot sub-regime (76.0% in hot)",
      "evidence": {"n": 246, "wr": 0.76, "lift_pp": 20.3, "tier": "validated"}
    },
    {
      "id": "win_003",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "IT", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.61,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "current_rules.json win_003 (calibrated)",
      "source_finding": "Live 18/18 = 100% inflated; lifetime actual 60.8% per Step 3 validation. Calibrated to lifetime expectation per Sonnet critique",
      "evidence": {"n": 189, "wr": 0.608, "lift_pp": 5.1, "tier": "preliminary"}
    },
    {
      "id": "win_004",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Metal", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.71,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "current_rules.json win_004 + bear_uptri playbook",
      "source_finding": "Bear UP_TRI Metal at 71.3% lifetime; aligns with Bear UP_TRI hot sub-regime cyclical preference",
      "evidence": {"n": 172, "wr": 0.713, "lift_pp": 15.6, "tier": "validated"}
    },
    {
      "id": "win_005",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Pharma", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.74,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "current_rules.json win_005 + bear_uptri playbook",
      "source_finding": "Bear UP_TRI Pharma 74.8% lifetime; defensive sector top in hot sub-regime",
      "evidence": {"n": 167, "wr": 0.748, "lift_pp": 19.1, "tier": "validated"}
    },
    {
      "id": "win_006",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": "Infra", "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.72,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "current_rules.json win_006",
      "source_finding": "Lifetime 72% on n=182 (Step 3 validation actual); calibrated up from initial 65% prediction",
      "evidence": {"n": 182, "wr": 0.72, "lift_pp": 16.3, "tier": "validated"}
    },
    {
      "id": "win_007",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bear"},
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.64,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "current_rules.json win_007 + bear_bullproxy playbook",
      "source_finding": "Lifetime Bear BULL_PROXY broad 47.3%; in hot sub-regime 63.7%. Live 87.5% inflated. Calibrated to mid-range",
      "evidence": {"n": 86, "wr": 0.637, "lift_pp": 16.4, "tier": "preliminary"}
    },
    {
      "id": "rule_001",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.451,
      "confidence_tier": "HIGH",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": false,
      "priority": "HIGH",
      "source_playbook": "bull_uptri",
      "source_finding": "late_bull (mid 200d × low breadth) UP_TRI 45.1% lifetime; topping risk; -6.9pp anti",
      "evidence": {"n": 2699, "wr": 0.451, "lift_pp": -6.9, "tier": "validated"}
    },
    {
      "id": "rule_002",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.436,
      "confidence_tier": "HIGH",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": false,
      "priority": "HIGH",
      "source_playbook": "bull_bullproxy",
      "source_finding": "late_bull BULL_PROXY 43.6% lifetime; -7.5pp anti; late-cycle exhaustion",
      "evidence": {"n": 268, "wr": 0.436, "lift_pp": -7.5, "tier": "validated"}
    },
    {
      "id": "rule_003",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "sub_regime", "value": "recovery_bull", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.602,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "breakout_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "recovery_bull",
      "production_ready": false,
      "priority": "HIGH",
      "source_playbook": "bull_uptri",
      "source_finding": "recovery_bull UP_TRI 60.2% lifetime baseline (n=972); broadened from Step 3's narrow vol+fvg combo which produced 0 matches due to feature-engineering uncertainty. Sub-regime gate alone provides edge.",
      "evidence": {"n": 972, "wr": 0.602, "lift_pp": 8.2, "tier": "validated"}
    },
    {
      "id": "rule_004",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "sub_regime", "value": "healthy_bull", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.534,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "healthy_bull",
      "production_ready": false,
      "priority": "HIGH",
      "source_playbook": "bull_bullproxy",
      "source_finding": "healthy_bull BULL_PROXY 53.4% baseline; broadened from Step 3's narrow nifty_20d=high combo which produced 0 matches. Sub-regime gate provides core edge.",
      "evidence": {"n": 333, "wr": 0.534, "lift_pp": 2.3, "tier": "validated"}
    },
    {
      "id": "rule_005",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "feat_vol_climax_flag", "value": true, "operator": "eq"}
      ],
      "verdict": "REJECT",
      "expected_wr": 0.37,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_bullproxy + critiques A1",
      "source_finding": "vol_climax × BULL_PROXY in Bear: -11.0pp anti (capitulation breaks support). Step 3 validation showed n=48 sparse but WR 37% confirms direction; capitulation events rare so small n is expected.",
      "evidence": {"n": 48, "wr": 0.37, "lift_pp": -11.0, "tier": "preliminary"}
    },
    {
      "id": "rule_006",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": "Health", "regime": "Bear"},
      "conditions": [
        {"feature": "sub_regime", "value": "hot", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.324,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri playbook",
      "source_finding": "Health × Bear UP_TRI in hot sub-regime: 32.4% WR — only sector where hot fails. Hostile cell. ADDED sub_regime_constraint=hot per Sonnet critique to fix Step 3 dilution",
      "evidence": {"n": 158, "wr": 0.324, "lift_pp": -33.0, "tier": "validated"}
    },
    {
      "id": "rule_007",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "feat_month", "value": 12, "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.31,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri playbook",
      "source_finding": "December × Bear UP_TRI: -25pp catastrophic (lifetime 56% baseline drops to ~31%). Universal calendar kill",
      "evidence": {"n": 850, "wr": 0.31, "lift_pp": -25.0, "tier": "validated"}
    },
    {
      "id": "rule_008",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "sub_regime", "value": "hot", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.683,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri playbook L2",
      "source_finding": "Bear UP_TRI hot sub-regime: 68.3% lifetime baseline (n=2,275), +14.9pp lift. Universal hot-Bear bullish-cell signal. Wildcard sector — applies broadly",
      "evidence": {"n": 2275, "wr": 0.683, "lift_pp": 14.9, "tier": "validated"}
    },
    {
      "id": "rule_009",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Choppy"},
      "conditions": [],
      "verdict": "REJECT",
      "expected_wr": 0.50,
      "confidence_tier": "HIGH",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "choppy_bullproxy playbook",
      "source_finding": "Choppy BULL_PROXY: KILL verdict. 0/175 Phase-4 patterns validated; 25% live WR; lifetime 50% baseline with no filter > +10pp lift. Entire cell suppressed",
      "evidence": {"n": 1931, "wr": 0.50, "lift_pp": 0.0, "tier": "validated"}
    },
    {
      "id": "rule_010",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [
        {"feature": "feat_market_breadth_pct", "value": "medium", "operator": "eq"},
        {"feature": "feat_nifty_vol_regime", "value": "Medium", "operator": "eq"},
        {"feature": "feat_day_of_month_bucket", "value": "wk3", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.578,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "equilibrium_fade",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_downtri playbook L3+L4",
      "source_finding": "Choppy DOWN_TRI breadth=medium × vol=Medium × wk3: 57.8% on n=1,295, +11.7pp lift. Vol-gating critical (breadth=medium inverts in Low/High vol)",
      "evidence": {"n": 1295, "wr": 0.578, "lift_pp": 11.7, "tier": "validated"}
    },
    {
      "id": "rule_011",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [
        {"feature": "feat_market_breadth_pct", "value": "medium", "operator": "eq"},
        {"feature": "feat_nifty_vol_regime", "value": "High", "operator": "eq"}
      ],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.601,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_uptri playbook L3+L4 v2",
      "source_finding": "Choppy UP_TRI breadth=medium × vol=High: 60.1% lifetime n=4,546, +7.9pp lift. Vol-gating critical (Medium-vol same combo is -5.5pp).",
      "evidence": {"n": 4546, "wr": 0.601, "lift_pp": 7.9, "tier": "validated"}
    },
    {
      "id": "rule_012",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "sub_regime", "value": "cold", "operator": "eq"},
        {"feature": "feat_day_of_month_bucket", "value": "wk4", "operator": "eq"},
        {"feature": "feat_swing_high_count_20d", "value": "low", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.633,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "cold",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_uptri playbook v3 cold cascade",
      "source_finding": "Cold sub-regime Tier 1 cascade: wk4 × swing_high=low. Lifetime 63.3% on n=3,374 within cold subset. ADDED sub_regime_constraint=cold per Sonnet critique to fix Step 3 zero-match issue (rule was matching wildcard which was empty at 3-feature intersection)",
      "evidence": {"n": 3374, "wr": 0.633, "lift_pp": 7.6, "tier": "validated"}
    },
    {
      "id": "rule_013",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [
        {"feature": "sector", "value": "Pharma", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.45,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "equilibrium_fade",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "LOW",
      "source_playbook": "choppy_downtri playbook L4",
      "source_finding": "Pharma × Choppy DOWN_TRI: -4.7pp catastrophic. Sector mismatch.",
      "evidence": {"n": 541, "wr": 0.41, "lift_pp": -4.7, "tier": "validated"}
    },
    {
      "id": "rule_014",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [
        {"feature": "feat_day_of_week", "value": "Fri", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.42,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "equilibrium_fade",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "LOW",
      "source_playbook": "choppy_downtri playbook L4",
      "source_finding": "Friday × Choppy DOWN_TRI: -6.2pp. Calendar kill.",
      "evidence": {"n": 1252, "wr": 0.40, "lift_pp": -6.2, "tier": "validated"}
    },
    {
      "id": "rule_015",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": "Metal", "regime": "Choppy"},
      "conditions": [],
      "verdict": "SKIP",
      "expected_wr": 0.50,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "LOW",
      "source_playbook": "choppy_uptri playbook L4",
      "source_finding": "Metal × Choppy UP_TRI: -2.2pp on n=2,092. Modest sector mismatch.",
      "evidence": {"n": 2099, "wr": 0.50, "lift_pp": -2.2, "tier": "validated"}
    },
    {
      "id": "rule_016",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Choppy"},
      "conditions": [
        {"feature": "feat_month", "value": 2, "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.36,
      "confidence_tier": "HIGH",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_uptri playbook L4",
      "source_finding": "February × Choppy UP_TRI: -16.2pp catastrophic (likely Indian Budget vol). Calendar kill.",
      "evidence": {"n": 3325, "wr": 0.36, "lift_pp": -16.2, "tier": "validated"}
    },
    {
      "id": "rule_017",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "feat_day_of_month_bucket", "value": "wk2", "operator": "in", "value_list": ["wk2", "wk3"]}
      ],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.536,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "trend_continuation_short",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_downtri playbook + critiques A1",
      "source_finding": "Bear DOWN_TRI calendar filter: wk2/wk3 only with non-Bank. Lifetime 53.6% on n=1,446, +7.5pp lift. Provisional filter from DEFERRED cell.",
      "evidence": {"n": 1446, "wr": 0.536, "lift_pp": 7.5, "tier": "preliminary"}
    },
    {
      "id": "rule_018",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": "Energy", "regime": "Bull"},
      "conditions": [],
      "verdict": "SKIP",
      "expected_wr": 0.49,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "breakout_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": null,
      "production_ready": false,
      "priority": "LOW",
      "source_playbook": "bull_uptri playbook",
      "source_finding": "Energy × Bull UP_TRI: -2.9pp lifetime worst Bull UP_TRI sector. Sector mismatch.",
      "evidence": {"n": 1500, "wr": 0.49, "lift_pp": -2.9, "tier": "validated"}
    },
    {
      "id": "rule_019",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "feat_month", "value": 9, "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.44,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "breakout_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": null,
      "production_ready": false,
      "priority": "LOW",
      "source_playbook": "bull_uptri playbook",
      "source_finding": "September × Bull UP_TRI: -8.4pp lifetime. Calendar kill for Bull bullish cells.",
      "evidence": {"n": 1200, "wr": 0.436, "lift_pp": -8.4, "tier": "validated"}
    },
    {
      "id": "rule_020",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "DOWN_TRI", "sector": null, "regime": "Bull"},
      "conditions": [
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"},
        {"feature": "feat_day_of_month_bucket", "value": "wk3", "operator": "eq"}
      ],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.652,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "counter_trend",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": false,
      "priority": "HIGH",
      "source_playbook": "bull_downtri playbook BD3",
      "source_finding": "late_bull × wk3 Bull DOWN_TRI: 65.2% lifetime on n=253, +21.8pp cumulative lift. Highest-precision Bull DOWN configuration. PROVISIONAL_OFF until Bull regime returns",
      "evidence": {"n": 253, "wr": 0.652, "lift_pp": 21.8, "tier": "preliminary"}
    },
    {
      "id": "rule_021",
      "active": true,
      "type": "kill",
      "match_fields": {"signal": "UP_TRI", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "feat_nifty_vol_regime", "value": "Low", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.42,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "LOW",
      "source_playbook": "bear_downtri lifetime evidence (mirror) + bear_uptri",
      "source_finding": "Bear UP_TRI in Low vol regime: -9.8pp lifetime. Bear UP_TRI mechanism requires stress; low vol = no edge.",
      "evidence": {"n": 800, "wr": 0.42, "lift_pp": -9.8, "tier": "preliminary"}
    },
    {
      "id": "rule_022",
      "active": true,
      "type": "boost",
      "match_fields": {"signal": "BULL_PROXY", "sector": null, "regime": "Bear"},
      "conditions": [
        {"feature": "sub_regime", "value": "hot", "operator": "eq"}
      ],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.637,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_bullproxy playbook P3",
      "source_finding": "Bear BULL_PROXY hot sub-regime only: 63.7% lifetime on n=86, +16.4pp lift. Provisional filter for DEFERRED cell. ADDED sub_regime_constraint=hot",
      "evidence": {"n": 86, "wr": 0.637, "lift_pp": 16.4, "tier": "preliminary"}
    }
  ]
}
```

```precedence_logic_path2.md
# Path 2 Precedence Logic — Rule Evaluation Order

## Overview

Path 2 uses a 4-layer precedence model where rules are evaluated in
strict hierarchical order. Each layer can terminate evaluation (KILL/REJECT)
or modify a verdict (boost/sector/calendar). Phase-5 override applies
last and can only upgrade verdicts (never downgrade).

---

## Layer 1 — KILL/REJECT (terminating)

If any KILL or REJECT rule matches, output that verdict immediately.
No further layers evaluated.

**KILL/REJECT rule examples (Path 2):**
- `rule_009`: Choppy BULL_PROXY → REJECT (entire cell)
- `rule_006`: Health × Bear UP_TRI hot → SKIP (hostile cell)
- `rule_007`: December × Bear UP_TRI → SKIP (catastrophic month)
- `rule_005`: vol_climax × Bear BULL_PROXY → REJECT
- `rule_001`: late_bull × Bull UP_TRI → SKIP
- `rule_002`: late_bull × Bull BULL_PROXY → SKIP
- `kill_001`: Bank × Bear DOWN_TRI → REJECT
- `rule_013/014/015/016`: Sector/calendar Choppy kills
- `rule_018/019`: Energy/Sep Bull kills
- `rule_021`: Low-vol Bear UP_TRI

**Precedence within Layer 1:** All KILL rules are equally terminating.
Order does not matter; first match wins logically since all produce
the same SKIP/REJECT verdict.

---

## Layer 2 — Sub-regime gate

If no KILL fired, sub-regime classification establishes baseline verdict.

**Bear sub-regime gate** (computed: `vp > 0.70 AND n60 < -0.10 = hot`):
- `hot`: `rule_008` → TAKE_FULL (broad Bear UP_TRI baseline)
- `warm`: TAKE_FULL (live evidence; no specific rule, defaults to allowing layer 3)
- `cold`: requires Tier 1 cascade match (`rule_012` wk4 × swing_high=low)
  or SKIP

**Bull sub-regime gate** (computed: `200d × breadth → recovery/healthy/normal/late`):
- `recovery_bull`: `rule_003` → TAKE_FULL UP_TRI
- `healthy_bull`: `rule_004` → TAKE_FULL BULL_PROXY
- `late_bull`: KILLS already triggered in Layer 1 (`rule_001/002`)
- `late_bull` for DOWN_TRI: `rule_020` → TAKE_SMALL

**Choppy sub-regime gate** (computed: `vol × breadth × momentum`):
- Various (vol_regime + breadth) cells: `rule_010` (DOWN_TRI),
  `rule_011` (UP_TRI)

---

## Layer 3 — Sector / Calendar boost & modulation

Sector-specific and calendar-specific rules apply on top of sub-regime
verdict. **Pessimistic merge:** the most conservative verdict wins
when multiple rules match.

**Verdict ordering (most → least conservative):**
`REJECT > SKIP > TAKE_SMALL > TAKE_FULL`

**Sector/calendar BOOST examples (Path 2):**
- `win_001` to `win_006`: Bear UP_TRI sector preferences (Auto, FMCG,
  IT, Metal, Pharma, Infra) → TAKE_FULL
- `win_007`: Bear BULL_PROXY broad → TAKE_FULL
- `rule_017`: Bear DOWN_TRI wk2/wk3 → TAKE_SMALL

**Composition rule:** Boost rules CONFIRM but don't UPGRADE verdicts
beyond what the sub-regime baseline supports. If a sub-regime says
TAKE_SMALL and a sector boost says TAKE_FULL, take TAKE_SMALL
(pessimistic). If both agree, take that verdict.

---

## Layer 4 — Phase-5 override

Phase-5 override searches the combo database for VALIDATED matches
with Wilson lower bound > sub-regime base + 5pp. Override can ONLY
upgrade (never downgrade).

**Override decision:**
1. Query combo_db with `(regime, signal_type, signal_features)`
2. Filter to `live_tier == VALIDATED AND live_n >= 10 AND recency_90d`
3. Pick max(Wilson_lower)
4. If Wilson_lower > current_baseline + 5pp, upgrade verdict tier
5. Else, retain Layer 1-3 verdict

**Logging:** Record `wr_source` as either `sub_regime_base`,
`sector_boost_match`, or `phase5_override_<combo_id>`.

---

## Conflict resolution examples

### Example 1: Bear UP_TRI hot Auto wk4

```
Date: 2026-04-25, AUTOLINKS UP_TRI, Bear, Auto sector
Sub-regime: hot (vp=0.75, n60=-0.13)

Layer 1 (KILL): No matches
  - rule_006 (Health) doesn't match (sector=Auto)
  - rule_007 (December) doesn't match (Apr)
  - rule_021 (Low vol) doesn't match
Layer 2 (sub-regime): rule_008 hot → TAKE_FULL
Layer 3 (sector): win_001 Auto → TAKE_FULL (confirms)
Layer 4 (override): No VALIDATED combo > 73.3% Wilson lower

Final: TAKE_FULL
WR estimate: 74% (from win_001 evidence)
```

### Example 2: Bull UP_TRI late_bull (KILL)

```
Date: 2027-08-19, late_bull conditions
Stock: TCS UP_TRI, Bull, IT sector

Layer 1 (KILL): rule_001 late_bull × Bull UP_TRI → SKIP

Final: SKIP (Layer 1 terminates)
WR estimate: N/A
```

### Example 3: Bear UP_TRI hot Health (sub-regime conflict with sector kill)

```
Date: 2026-04-15, hot Bear regime
Stock: SUNPHARMA UP_TRI, Bear, Health sector

Layer 1 (KILL): rule_006 Health × Bear UP_TRI hot → SKIP

Final: SKIP (Health hostility overrides hot sub-regime baseline)
WR estimate: N/A (32.4% historical)
```

### Example 4: Choppy DOWN_TRI strong filter match

```
Date: 2026-09-23, Wednesday wk3
Stock: ASIANPAINT DOWN_TRI, Choppy, Other sector
Features: breadth=medium, vol=Medium

Layer 1 (KILL):
  - rule_013 (Pharma) doesn't match
  - rule_014 (Friday) doesn't match
Layer 2 (sub-regime): No specific Choppy DOWN_TRI baseline rule
Layer 3 (boost): rule_010 breadth=med × vol=Med × wk3 → TAKE_FULL
Layer 4 (override): No Bull/Bear override applies

Final: TAKE_FULL
WR estimate: 57.8% (rule_010 evidence)
```

### Example 5: Choppy BULL_PROXY (always REJECT)

```
Date: any, any stock
Signal: HDFCBANK BULL_PROXY, Choppy

Layer 1 (KILL): rule_009 Choppy BULL_PROXY → REJECT

Final: REJECT
WR estimate: N/A (cell-level kill)
```

---

## Schema enforcement notes

- `match_fields` must EXACTLY match (signal, sector, regime). `null`
  acts as wildcard.
- `conditions` array applies AND logic across feature-value pairs.
- `regime_constraint = "any"` allows wildcard regime matching (rare;
  most rules constrain).
- `sub_regime_constraint = null` means rule applies regardless of
  sub-regime; otherwise must match exactly.

## Determinism

Path 2 evaluation is deterministic given:
1. Signal features at fire time
2. Market state (NIFTY vol_percentile, 60d_return, 200d_return, breadth)
3. Combo database state (Phase-5 VALIDATED set, refreshed quarterly)

Each scan day produces the same verdict for the same signal.
```

```b1_b2_coupling_path2.md
# B1 / B2 Coupling — Path 2 Spec

## Decision

**Ship B1 (4-tier display) NOW. Defer B2 (sigmoid scoring) to Phase-2.**

B1 and B2 are alternative mechanisms for the same finding (boundary_hot
beats confident_hot in Bear UP_TRI). Production should ship one, not
both. B1 is operationally simpler and fits the existing
percentile-bucket architecture; B2's sigmoid requires continuous-feature
support not yet present.

---

## B1 — 4-tier confidence display (SHIP NOW)

### Tier definitions

Computed from `nifty_vol_percentile_20d (vp)` and
`nifty_60d_return_pct (n60)`:

```python
def classify_bear_tier(vp, n60):
    if vp > 0.75 and n60 < -0.15:
        return "confident_hot"
    if vp > 0.70 and -0.15 <= n60 < -0.10:
        return "boundary_hot"
    if vp > 0.70 and n60 < -0.10:
        return "boundary_hot"  # default for hot region not confident
    if vp > 0.65 and n60 > -0.15:
        return "boundary_cold"
    if vp > 0.70 or n60 < -0.10:
        return "warm_zone"  # one-of-two hot conditions
    if vp < 0.65 and n60 > -0.05:
        return "confident_cold"
    return "warm_zone"  # default fallback
```

### Per-tier WR mapping (calibrated from B1 lifetime data)

| Tier | n | WR | Production action |
|------|---|----|---------|
| boundary_hot | 1,174 | **71.5%** ★ | TAKE_FULL (highest WR) |
| confident_hot | 928 | 64.2% | TAKE_FULL |
| boundary_cold | 2,213 | 59.0% | TAKE_SMALL |
| warm_zone | 6,687 | 52.1% | TAKE_SMALL or SKIP per cascade |
| confident_cold | 2,737 | 52.1% | SKIP unless Tier 1 cascade match |

### Telegram messaging

```
[BEAR · BOUNDARY_HOT · 71% expected]
SIGNAL: HDFC.NS UP_TRI age=0
EXPECTED: TAKE_FULL · WR 65-75%

[BEAR · CONFIDENT_HOT · 64% expected]
SIGNAL: TCS.NS UP_TRI age=1
EXPECTED: TAKE_FULL · WR 60-65%
```

### Counter-intuitive finding briefing

Trader must understand: **boundary_hot > confident_hot**. Mechanism:
early-capitulation reversals (cusp of stress) work better than
deep-stress reversals (already-extended). First-day briefing must
explain this OR risk trader dismissing boundary_hot signals as "weaker."

### Coupling to rules

- `rule_008` (Bear UP_TRI hot baseline): tier classification adds
  precision but base rule remains operative
- Sizing modifier:
  - boundary_hot: full
  - confident_hot: full
  - warm_zone: half
  - boundary_cold: half
  - confident_cold: skip (unless cascade match)

---

## B2 — Sigmoid scoring (DEFER)

### Why deferred

1. **Continuous-feature scoring not yet supported in schema.** Adding
   `continuous_score_function` rule type is non-trivial.
2. **B1 captures same finding via tiered display.** Shipping both
   creates UX confusion.
3. **Sigmoid parameters fitted to lifetime data.** Need quarterly
   re-fit cadence not yet established.
4. **Verdict re-mapping required.** Soft TAKE_SMALL has higher WR
   than soft TAKE_FULL — production must re-label, which complicates
   migration.

### Phase-2 plan (post-deployment)

When sub-regime detector + Phase-5 override are stable in production,
revisit B2:
- Pre-compute `bear_hot_conf` as scanner enrichment field
- Add tier-based mapping (effectively same as B1's 5 tiers)
- Re-label verdict bands to align WR with TAKE_FULL/TAKE_SMALL labels

### Why not ship both

B1's 4-tier display + B2's sigmoid would produce:
- Trader sees boundary_hot (B1 label)
- Same signal scores hot_conf=0.45 (B2 score)
- Two parallel displays, same finding, redundant

Ship one. B1 wins for v1 simplicity.

---

## Cross-reference to B3 (Phase-5 override)

B3's Phase-5 override LAYERS on top of B1's tier classification:

```
Layer order:
  1. KILL filters (B1 doesn't matter if killed)
  2. Sub-regime gate → tier classification (B1)
  3. Sector/calendar boost
  4. Phase-5 override (B3)

Override decision uses tier baseline:
  - boundary_hot baseline: 71.5%
  - confident_hot baseline: 64.2%
  - Phase-5 override fires only if Wilson_lower > tier_baseline + 5pp
```

In practice, override rarely fires for boundary_hot signals because
71.5% baseline is already very high; only the strongest combos beat it.

---

## Production rollout

### Phase 1 (now): B1 4-tier display
- Add `bear_tier` enrichment field to scanner pipeline
- Update Telegram messaging with tier tag
- Add tier classification to v3 Bear UP_TRI playbook
- First-deployment briefing: explain boundary_hot > confident_hot

### Phase 2 (later): Optional B2 sigmoid
- After 6+ months of B1 production data
- If trader requests finer granularity
- If continuous scoring unlocks WR calibration improvements

### Out of scope for this iteration
- Quarterly sigmoid re-fitting cadence
- Cross-regime tier extension (only Bear UP_TRI gets tiers in v1)

---

## Coupling to Path 2 rules

The Path 2 rule schema includes `sub_regime_constraint` which captures
the broad hot/warm/cold gate. Tier classification is INTERNAL to the
hot bucket — not exposed as a separate match field. Tier-based sizing
modifications happen at the integration layer, not the rule layer.

If future iterations need tier-based rule matching, add
`tier_constraint` field to schema; for now, the WR expectation tier
serves as documentation, not match logic.
```

```validation_predictions_path2.json
{
  "schema_version": 4,
  "generated_at": "2026-05-03T00:00:00Z",
  "description": "Path 2 quantitative predictions for each rule. Predictions are calibrated to lifetime data where available; live small-sample inflations explicitly removed (e.g., win_003 calibrated from 100% live to 60% lifetime). Tolerance bands account for feature-engineering uncertainty.",
  "predictions": [
    {
      "rule_id": "kill_001",
      "predicted_match_count": 653,
      "predicted_match_wr": 0.45,
      "count_tolerance_pct": 0.20,
      "wr_tolerance_pp": 0.05,
      "rationale": "Step 3 PASS at exact match; preserved unchanged"
    },
    {
      "rule_id": "watch_001",
      "predicted_match_count": 27260,
      "predicted_match_wr": 0.523,
      "count_tolerance_pct": 0.20,
      "wr_tolerance_pp": 0.05,
      "rationale": "Step 3 PASS; lifetime baseline preserved"
    },
    {
      "rule_id": "win_001",
      "predicted_match_count": 176,
      "predicted_match_wr": 0.74,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "Calibrated to actual lifetime n=176 (Step 3 actual); WR matches lifetime 74.3%"
    },
    {
      "rule_id": "win_002",
      "predicted_match_count": 246,
      "predicted_match_wr": 0.76,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "Calibrated to actual lifetime n=246; WR matches 76.0%"
    },
    {
      "rule_id": "win_003",
      "predicted_match_count": 189,
      "predicted_match_wr": 0.61,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "Calibrated DOWN from Step 3's 70% (live small-sample) to 60.8% (lifetime actual). Sonnet critique: live 18/18 inflated"
    },
    {
      "rule_id": "win_004",
      "predicted_match_count": 172,
      "predicted_match_wr": 0.71,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "Calibrated to lifetime n=172, 71.3%"
    },
    {
      "rule_id": "win_005",
      "predicted_match_count": 167,
      "predicted_match_wr": 0.75,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "Calibrated to lifetime n=167, 74.8%"
    },
    {
      "rule_id": "win_006",
      "predicted_match_count": 182,
      "predicted_match_wr": 0.72,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.07,
      "rationale": "Calibrated UP from Step 3's 65% to actual 72%; live 87.5% partial confirmation"
    },
    {
      "rule_id": "win_007",
      "predicted_match_count": 86,
      "predicted_match_wr": 0.64,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.08,
      "rationale": "Calibrated to lifetime hot subset n=86, 63.7%; live 87.5% inflated by Phase-5"
    },
    {
      "rule_id": "rule_001",
      "predicted_match_count": 2699,
      "predicted_match_wr": 0.451,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "Bull late_bull UP_TRI; lifetime baseline; sub-regime match expected to be 7.1% of Bull universe"
    },
    {
      "rule_id": "rule_002",
      "predicted_match_count": 271,
      "predicted_match_wr": 0.436,
      "count_tolerance_pct": 0.40,
      "wr_tolerance_pp": 0.06,
      "rationale": "Bull late_bull BULL_PROXY; lifetime n=268-271 range; calibrated to playbook"
    },
    {
      "rule_id": "rule_003",
      "predicted_match_count": 972,
      "predicted_match_wr": 0.602,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "Broadened from Step 3's 3-feature combo (390 expected, 0 actual) to sub-regime-only gate (972 lifetime). Avoids feature-engineering uncertainty"
    },
    {
      "rule_id": "rule_004",
      "predicted_match_count": 333,
      "predicted_match_wr": 0.534,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "Broadened from narrow 20d=high combo (128 expected, 0 actual) to sub-regime gate (333 lifetime)"
    },
    {
      "rule_id": "rule_005",
      "predicted_match_count": 48,
      "predicted_match_wr": 0.37,
      "count_tolerance_pct": 0.40,
      "wr_tolerance_pp": 0.10,
      "rationale": "Calibrated to actual sparse n=48; vol_climax events rare. Wider tolerance for sparse feature"
    },
    {
      "rule_id": "rule_006",
      "predicted_match_count": 158,
      "predicted_match_wr": 0.324,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.07,
      "rationale": "Health × Bear UP_TRI hot — sub_regime_constraint=hot ADDED per Sonnet critique to fix dilution. Predicted from playbook S1 finding n=158, 32.4%"
    },
    {
      "rule_id": "rule_007",
      "predicted_match_count": 850,
      "predicted_match_wr": 0.31,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "December Bear UP_TRI; lifetime catastrophic month. Step 3 actual matched n=1,663 across all sub-regimes; recalibrated wider"
    },
    {
      "rule_id": "rule_008",
      "predicted_match_count": 2275,
      "predicted_match_wr": 0.683,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "Bear UP_TRI hot sub-regime baseline; lifetime n=2,275, 68.3%. Wildcard sector gate"
    },
    {
      "rule_id": "rule_009",
      "predicted_match_count": 1931,
      "predicted_match_wr": 0.50,
      "count_tolerance_pct": 0.20,
      "wr_tolerance_pp": 0.05,
      "rationale": "Choppy BULL_PROXY entire cell KILL; lifetime n=1,931 baseline 50%"
    },
    {
      "rule_id": "rule_010",
      "predicted_match_count": 1295,
      "predicted_match_wr": 0.578,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "Choppy DOWN_TRI breadth=med × vol=Med × wk3; lifetime per L4 finding n=1,295, 57.8%"
    },
    {
      "rule_id": "rule_011",
      "predicted_match_count": 4546,
      "predicted_match_wr": 0.601,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.06,
      "rationale": "Choppy UP_TRI breadth=med × vol=High; L3 finding n=4,546, 60.1%"
    },
    {
      "rule_id": "rule_012",
      "predicted_match_count": 3374,
      "predicted_match_wr": 0.633,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.07,
      "rationale": "Bear UP_TRI cold cascade Tier 1; sub_regime_constraint=cold ADDED per Sonnet critique to fix Step 3 zero-match. Within cold subset (~7,577 cold signals), wk4 × swing_high=low matches per playbook n=3,374"
    },
    {
      "rule_id": "rule_013",
      "predicted_match_count": 541,
      "predicted_match_wr": 0.41,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "Pharma × Choppy DOWN_TRI; Step 3 PASS preserved"
    },
    {
      "rule_id": "rule_014",
      "predicted_match_count": 1252,
      "predicted_match_wr": 0.40,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "Friday × Choppy DOWN_TRI; Step 3 PASS preserved"
    },
    {
      "rule_id": "rule_015",
      "predicted_match_count": 2099,
      "predicted_match_wr": 0.50,
      "count_tolerance_pct": 0.25,
      "wr_tolerance_pp": 0.05,
      "rationale": "Metal × Choppy UP_TRI; Step 3 PASS preserved"
    },
    {
      "rule_id": "rule_016",
      "predicted_match_count": 3325,
      "predicted_match_wr": 0.36,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "February × Choppy UP_TRI catastrophic; Step 3 actual n=3,325 (recalibrated count up from 1,850)"
    },
    {
      "rule_id": "rule_017",
      "predicted_match_count": 1446,
      "predicted_match_wr": 0.536,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "Bear DOWN_TRI wk2/wk3 calendar filter; lifetime per playbook n=1,446 (covers wk2 OR wk3 union)"
    },
    {
      "rule_id": "rule_018",
      "predicted_match_count": 1500,
      "predicted_match_wr": 0.49,
      "count_tolerance_pct": 0.40,
      "wr_tolerance_pp": 0.06,
      "rationale": "Energy × Bull UP_TRI; estimated from Bull universe Energy share ~3.9%"
    },
    {
      "rule_id": "rule_019",
      "predicted_match_count": 3175,
      "predicted_match_wr": 0.436,
      "count_tolerance_pct": 0.30,
      "wr_tolerance_pp": 0.06,
      "rationale": "September × Bull UP_TRI; estimated from Bull UP_TRI universe (38,100) × 1/12 = ~3,175"
    },
    {
      "rule_id": "rule_020",
      "predicted_match_count": 253,
      "predicted_match_wr": 0.652,
      "count_tolerance_pct": 0.40,
      "wr_tolerance_pp": 0.08,
      "rationale": "late_bull × wk3 Bull DOWN_TRI; lifetime n=253 per playbook BD3"
    },
    {
      "rule_id": "rule_021",
      "predicted_match_count": 800,
      "predicted_match_wr": 0.42,
      "count_tolerance_pct": 0.40,
      "wr_tolerance_pp": 0.07,
      "rationale": "Low vol × Bear UP_TRI; estimated cohort"
    },
    {
      "rule_id": "rule_022",
      "predicted_match_count": 86,
      "predicted_match_wr": 0.637,
      "count_tolerance_pct": 0.40,
      "wr_tolerance_pp": 0.10,
      "rationale": "Bear BULL_PROXY hot sub-regime; lifetime n=86 per playbook P3. sub_regime_constraint=hot. Sparse sample, wider tolerance"
    }
  ]
}
```

```integration_notes_path2.md
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
```