```unified_rules_v4.json
{
  "schema_version": 4,
  "generated_at": "2026-05-03T00:00:00Z",
  "description": "Step 3 Opus synthesis: 14 new rules + 9 existing rules harmonized into 2-tier schema (match_fields + conditions array). Sub-regime gated; pessimistic merge composition; Phase-5 override upgrade-only.",
  "rules": [
    {
      "id": "kill_001",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "DOWN_TRI",
        "sector": "Bank",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "REJECT",
      "expected_wr": 0.0,
      "confidence_tier": "HIGH",
      "trade_mechanism": "trend_fade",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_downtri",
      "source_finding": "Bank x DOWN_TRI live 0/11 WR; lifetime confirms; existing production rule",
      "evidence": {
        "n": 11,
        "wr": 0.0,
        "lift_pp": -11.12,
        "tier": "preliminary"
      }
    },
    {
      "id": "watch_001",
      "active": true,
      "type": "watch",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": null,
        "regime": "Choppy"
      },
      "conditions": [],
      "verdict": "WATCH",
      "expected_wr": 0.314,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_uptri",
      "source_finding": "Apr 17 cluster 11W/24L/1F (n=36, WR 31%) - informational warning",
      "evidence": {
        "n": 36,
        "wr": 0.314,
        "lift_pp": -3.6,
        "tier": "preliminary"
      }
    },
    {
      "id": "win_001",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "Auto",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.72,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Auto UP_TRI Bear 21/21 live; Auto in hot sub-regime 74.3% lifetime",
      "evidence": {
        "n": 21,
        "wr": 1.0,
        "lift_pp": 18.3,
        "tier": "validated"
      }
    },
    {
      "id": "win_002",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "FMCG",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.74,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "FMCG UP_TRI Bear 19/19 live; FMCG in hot 76.0% lifetime",
      "evidence": {
        "n": 19,
        "wr": 1.0,
        "lift_pp": 20.3,
        "tier": "validated"
      }
    },
    {
      "id": "win_003",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "IT",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.7,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "IT UP_TRI Bear 18/18 live; defensive growth in Bear stress",
      "evidence": {
        "n": 18,
        "wr": 1.0,
        "lift_pp": 14.3,
        "tier": "validated"
      }
    },
    {
      "id": "win_004",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "Metal",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.68,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Metal UP_TRI Bear 15/15 live; cyclical bounce in stress",
      "evidence": {
        "n": 15,
        "wr": 1.0,
        "lift_pp": 12.3,
        "tier": "validated"
      }
    },
    {
      "id": "win_005",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "Pharma",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.72,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Pharma UP_TRI Bear 13/13 live; Pharma in hot 74.8% lifetime",
      "evidence": {
        "n": 13,
        "wr": 1.0,
        "lift_pp": 19.1,
        "tier": "validated"
      }
    },
    {
      "id": "win_006",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "Infra",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.65,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_uptri",
      "source_finding": "Infra UP_TRI Bear ~10.5/12 live (87.5%)",
      "evidence": {
        "n": 12,
        "wr": 0.875,
        "lift_pp": 9.3,
        "tier": "preliminary"
      }
    },
    {
      "id": "win_007",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "BULL_PROXY",
        "sector": null,
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.65,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "hot",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_bullproxy",
      "source_finding": "BULL_PROXY Bear hot ~14/16 live (87.5%); lifetime hot 63.7% n=86",
      "evidence": {
        "n": 16,
        "wr": 0.875,
        "lift_pp": 16.4,
        "tier": "preliminary"
      }
    },
    {
      "id": "rule_001",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": null,
        "regime": "Bull"
      },
      "conditions": [
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.45,
      "confidence_tier": "HIGH",
      "trade_mechanism": "breakout_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_uptri",
      "source_finding": "late_bull Bull UP_TRI 45.1% WR vs recovery_bull 60.2% (30pp swing); largest Bull edge driver",
      "evidence": {
        "n": 2699,
        "wr": 0.451,
        "lift_pp": -6.9,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_002",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "BULL_PROXY",
        "sector": null,
        "regime": "Bull"
      },
      "conditions": [
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.436,
      "confidence_tier": "HIGH",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_bullproxy",
      "source_finding": "late_bull Bull BULL_PROXY 43.6% WR; -7.5pp anti; late-cycle exhaustion",
      "evidence": {
        "n": 268,
        "wr": 0.436,
        "lift_pp": -7.5,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_003",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": null,
        "regime": "Bull"
      },
      "conditions": [
        {"feature": "sub_regime", "value": "recovery_bull", "operator": "eq"},
        {"feature": "feat_nifty_vol_regime", "value": "Medium", "operator": "eq"},
        {"feature": "feat_fvg_unfilled_above_count", "value": "low", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.72,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "breakout_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "recovery_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_uptri",
      "source_finding": "recovery_bull x vol=Medium x fvg_low: 74.1% lifetime WR, n=390, +22pp lift over 52% baseline",
      "evidence": {
        "n": 390,
        "wr": 0.741,
        "lift_pp": 22.1,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_004",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "BULL_PROXY",
        "sector": null,
        "regime": "Bull"
      },
      "conditions": [
        {"feature": "sub_regime", "value": "healthy_bull", "operator": "eq"},
        {"feature": "feat_nifty_20d_return_pct", "value": "high", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.62,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "healthy_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_bullproxy",
      "source_finding": "healthy_bull x nifty_20d=high: 62.5% lifetime WR, n=128, +11.4pp lift",
      "evidence": {
        "n": 128,
        "wr": 0.625,
        "lift_pp": 11.4,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_005",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "BULL_PROXY",
        "sector": null,
        "regime": "Bear"
      },
      "conditions": [
        {"feature": "feat_vol_climax_flag", "value": true, "operator": "eq"}
      ],
      "verdict": "REJECT",
      "expected_wr": 0.36,
      "confidence_tier": "HIGH",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_bullproxy",
      "source_finding": "vol_climax x BULL_PROXY in Bear: -11.0pp anti; capitulation breaks support reversal mechanism",
      "evidence": {
        "n": 139,
        "wr": 0.363,
        "lift_pp": -11.0,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_006",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "BULL_PROXY",
        "sector": null,
        "regime": "Bull"
      },
      "conditions": [
        {"feature": "feat_vol_climax_flag", "value": true, "operator": "eq"},
        {"feature": "sub_regime", "value": "late_bull", "operator": "eq"}
      ],
      "verdict": "REJECT",
      "expected_wr": 0.4,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Bull",
      "sub_regime_constraint": "late_bull",
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bull_bullproxy",
      "source_finding": "vol_climax x BULL_PROXY in Bull-late_bull: -7.5pp anti; universal pattern (Bear -11pp; Bull weaker)",
      "evidence": {
        "n": 80,
        "wr": 0.395,
        "lift_pp": -7.5,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_007",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "Health",
        "regime": "Bear"
      },
      "conditions": [],
      "verdict": "SKIP",
      "expected_wr": 0.32,
      "confidence_tier": "HIGH",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "HIGH",
      "source_playbook": "bear_uptri",
      "source_finding": "Health Bear UP_TRI 32.4% in hot sub-regime; only sector where hot fails; structurally hostile",
      "evidence": {
        "n": 158,
        "wr": 0.324,
        "lift_pp": -23.3,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_008",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": null,
        "regime": "Bear"
      },
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
      "priority": "MEDIUM",
      "source_playbook": "bear_uptri",
      "source_finding": "December Bear UP_TRI: -25pp catastrophic month; year-end illiquidity",
      "evidence": {
        "n": 850,
        "wr": 0.307,
        "lift_pp": -25.0,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_009",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": null,
        "regime": "Choppy"
      },
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
      "source_playbook": "choppy_uptri",
      "source_finding": "February Choppy UP_TRI: -16.2pp catastrophic on n=3,338; likely Indian Budget volatility",
      "evidence": {
        "n": 3338,
        "wr": 0.361,
        "lift_pp": -16.2,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_010",
      "active": true,
      "type": "kill",
      "match_fields": {
        "signal": "BULL_PROXY",
        "sector": null,
        "regime": "Choppy"
      },
      "conditions": [],
      "verdict": "REJECT",
      "expected_wr": 0.5,
      "confidence_tier": "HIGH",
      "trade_mechanism": "support_bounce_reversal",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "choppy_bullproxy",
      "source_finding": "Entire cell KILL verdict: 0/175 Phase-4 patterns validated; live 25% WR; lifetime peak combo +9.2pp sub-threshold",
      "evidence": {
        "n": 1931,
        "wr": 0.5,
        "lift_pp": 0.0,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_011",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "DOWN_TRI",
        "sector": null,
        "regime": "Bear"
      },
      "conditions": [
        {"feature": "feat_day_of_month_bucket", "value": ["wk2", "wk3"], "operator": "in"}
      ],
      "verdict": "TAKE_SMALL",
      "expected_wr": 0.536,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "trend_fade",
      "regime_constraint": "Bear",
      "sub_regime_constraint": null,
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_downtri",
      "source_finding": "Bear DOWN_TRI wk2/wk3 timing filter: 53.6% WR n=1,446 (+7.5pp lift over 46.1% baseline)",
      "evidence": {
        "n": 1446,
        "wr": 0.536,
        "lift_pp": 7.5,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_012",
      "active": true,
      "type": "boost",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": null,
        "regime": "Bear"
      },
      "conditions": [
        {"feature": "sub_regime", "value": "cold", "operator": "eq"},
        {"feature": "feat_day_of_month_bucket", "value": "wk4", "operator": "eq"},
        {"feature": "feat_swing_high_count_20d", "value": "low", "operator": "eq"}
      ],
      "verdict": "TAKE_FULL",
      "expected_wr": 0.62,
      "confidence_tier": "MEDIUM",
      "trade_mechanism": "mean_reversion",
      "regime_constraint": "Bear",
      "sub_regime_constraint": "cold",
      "production_ready": true,
      "priority": "MEDIUM",
      "source_playbook": "bear_uptri",
      "source_finding": "Cold Bear UP_TRI cascade Tier 1: wk4 x swing_high=low: 63.3% WR n=3,374 (+13pp lift over cold baseline)",
      "evidence": {
        "n": 3374,
        "wr": 0.633,
        "lift_pp": 13.0,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_013",
      "active": false,
      "type": "kill",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "Energy",
        "regime": "Bull"
      },
      "conditions": [],
      "verdict": "SKIP",
      "expected_wr": 0.49,
      "confidence_tier": "LOW",
      "trade_mechanism": "breakout_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": null,
      "production_ready": false,
      "priority": "LOW",
      "source_playbook": "bull_uptri",
      "source_finding": "Energy Bull UP_TRI: -2.9pp lifetime; worst Bull UP_TRI sector",
      "evidence": {
        "n": 2400,
        "wr": 0.491,
        "lift_pp": -2.9,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_014",
      "active": false,
      "type": "kill",
      "match_fields": {
        "signal": null,
        "sector": null,
        "regime": "Bull"
      },
      "conditions": [
        {"feature": "feat_month", "value": 9, "operator": "eq"},
        {"feature": "signal", "value": ["UP_TRI", "BULL_PROXY"], "operator": "in"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.436,
      "confidence_tier": "LOW",
      "trade_mechanism": "breakout_continuation",
      "regime_constraint": "Bull",
      "sub_regime_constraint": null,
      "production_ready": false,
      "priority": "LOW",
      "source_playbook": "bull_uptri",
      "source_finding": "September Bull UP_TRI/BULL_PROXY: -8.4pp catastrophic month",
      "evidence": {
        "n": 1850,
        "wr": 0.436,
        "lift_pp": -8.4,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_015",
      "active": false,
      "type": "kill",
      "match_fields": {
        "signal": "DOWN_TRI",
        "sector": "Pharma",
        "regime": "Choppy"
      },
      "conditions": [],
      "verdict": "SKIP",
      "expected_wr": 0.413,
      "confidence_tier": "LOW",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": false,
      "priority": "LOW",
      "source_playbook": "choppy_downtri",
      "source_finding": "Pharma Choppy DOWN_TRI: -4.7pp lifetime catastrophic sector mismatch",
      "evidence": {
        "n": 600,
        "wr": 0.413,
        "lift_pp": -4.7,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_016",
      "active": false,
      "type": "kill",
      "match_fields": {
        "signal": "DOWN_TRI",
        "sector": null,
        "regime": "Choppy"
      },
      "conditions": [
        {"feature": "feat_day_of_week", "value": "Fri", "operator": "eq"}
      ],
      "verdict": "SKIP",
      "expected_wr": 0.398,
      "confidence_tier": "LOW",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": false,
      "priority": "LOW",
      "source_playbook": "choppy_downtri",
      "source_finding": "Friday Choppy DOWN_TRI: -6.2pp lifetime; weekend risk-off avoidance",
      "evidence": {
        "n": 1200,
        "wr": 0.398,
        "lift_pp": -6.2,
        "tier": "lifetime"
      }
    },
    {
      "id": "rule_017",
      "active": false,
      "type": "kill",
      "match_fields": {
        "signal": "UP_TRI",
        "sector": "Metal",
        "regime": "Choppy"
      },
      "conditions": [],
      "verdict": "SKIP",
      "expected_wr": 0.482,
      "confidence_tier": "LOW",
      "trade_mechanism": "regime_transition",
      "regime_constraint": "Choppy",
      "sub_regime_constraint": null,
      "production_ready": false,
      "priority": "LOW",
      "source_playbook": "choppy_uptri",
      "source_finding": "Metal Choppy UP_TRI: -2.2pp lifetime on n=2,092",
      "evidence": {
        "n": 2092,
        "wr": 0.482,
        "lift_pp": -2.2,
        "tier": "lifetime"
      }
    }
  ],
  "notes": {
    "schema_version": "v4 — 2-tier (match_fields + conditions array). Migration from v3 BREAKING; 2-week parallel evaluation window required.",
    "rule_count": "17 active rules (5 HIGH new + 5 MEDIUM new + 7 existing) + 5 LOW production_ready=false (deferred to Phase D).",
    "composition": "Pessimistic merge: SKIP > TAKE_SMALL > TAKE_FULL. KILL/REJECT terminates. See precedence_logic.md.",
    "mechanism_per_cell": {
      "Bear_UP_TRI": "mean_reversion",
      "Bull_UP_TRI": "breakout_continuation",
      "Choppy_UP_TRI": "regime_transition",
      "Bear_DOWN_TRI": "trend_fade",
      "Bull_DOWN_TRI": "counter_trend",
      "Choppy_DOWN_TRI": "regime_transition",
      "Bear_BULL_PROXY": "support_bounce_reversal",
      "Bull_BULL_PROXY": "support_bounce_reversal",
      "Choppy_BULL_PROXY": "KILL_no_mechanism"
    },
    "wr_calibration_note": "expected_wr is calibrated lifetime baseline + sub-regime tier (per B1 framework), NOT live observed. Live observations include Phase-5 selection bias not reproducible at scale.",
    "deferred_rules": "rule_013 (Bull Energy), rule_014 (Bull Sep), rule_015 (Choppy Pharma DOWN), rule_016 (Choppy Friday DOWN), rule_017 (Choppy Metal UP) marked production_ready=false; activate after live validation per integration_notes.md Phase D."
  }
}
```

```precedence_logic.md
# Precedence Logic — v4 Rule Evaluation

This document defines how the v4 rule engine evaluates a signal against
the 23-rule corpus to produce a single verdict with a calibrated WR
estimate.

## Overview — 4-Layer Evaluation

Rules evaluate in strict order. Layer 1 is terminating; layers 2-4 are
non-terminating but compose pessimistically (most conservative wins).
Layer 4 is upgrade-only.

```
Signal arrives
  ↓
Layer 1: KILL / REJECT (terminating)
  ↓ (if no terminating match)
Layer 2: Sub-regime gate (establish baseline)
  ↓
Layer 3: Sector / Calendar pessimistic merge
  ↓
Layer 4: Phase-5 override (upgrade-only)
  ↓
Final verdict + calibrated WR
```

---

## Layer 1 — KILL/REJECT (terminating)

**Rule types:** `type=kill` with `verdict=REJECT` or `verdict=SKIP`
that are unconditional (no sub-regime gate, or sub-regime IS the kill).

**Behavior:** First match wins. No further evaluation. Output verdict
and stop.

**Examples in v4 corpus:**
- `kill_001` — Bank × DOWN_TRI × Bear → REJECT
- `rule_005` — vol_climax × BULL_PROXY × Bear → REJECT
- `rule_006` — vol_climax × BULL_PROXY × Bull-late_bull → REJECT
- `rule_007` — Health × UP_TRI × Bear → SKIP (32.4% lifetime; AVOID)
- `rule_008` — December × UP_TRI × Bear → SKIP (-25pp catastrophic)
- `rule_009` — February × UP_TRI × Choppy → SKIP (-16.2pp Budget vol)
- `rule_010` — BULL_PROXY × Choppy → REJECT (entire cell KILL)
- `rule_001` — late_bull × UP_TRI × Bull → SKIP
- `rule_002` — late_bull × BULL_PROXY × Bull → SKIP

**Implementation:** Iterate `kill` rules in priority order
(HIGH → MEDIUM → LOW). Match on `match_fields` AND all `conditions`.
First match terminates evaluation.

---

## Layer 2 — Sub-regime gate

**Rule types:** Implicit (the sub-regime classifier itself).

**Behavior:** Sub-regime classification establishes baseline verdict
eligibility. The classifier outputs a tier label which feeds into
Layer 3 matching:

| Sub-regime tier | Default verdict eligibility | Calibrated WR floor |
|---|---|---|
| Bear hot / boundary_hot | TAKE_FULL | 65-75% |
| Bear confident_hot | TAKE_FULL | 60-65% |
| Bear warm | TAKE_FULL | 70-90% (deferred until lifetime cohort accumulates) |
| Bear cold + Tier 1 cascade | TAKE_FULL | 60-65% |
| Bear cold (no cascade) | SKIP | 49-55% |
| Bull recovery_bull | TAKE_FULL eligible | 60-72% |
| Bull healthy_bull | TAKE_FULL eligible | 58-66% |
| Bull normal_bull | TAKE_SMALL eligible | 51-58% |
| Bull late_bull | SKIP (terminated at L1 via rule_001/002) | n/a |
| Choppy high_medium_flat | TAKE_FULL eligible | 58-65% |
| Choppy other 3-axis cells | TAKE_SMALL or SKIP per cell | varies |

**Boundary tier handling (per B1):**

The B1 finding states `boundary_hot` (just-into-hot) WR = 71.5% beats
`confident_hot` (deep-hot) WR = 64.2%. The 4-tier classifier exposes
this:

```
confident_hot:   TAKE_FULL @ 60-65%
boundary_hot:    TAKE_FULL @ 65-75% (highest WR — counterintuitive)
boundary_cold:   TAKE_SMALL @ 55-60% (transitional)
confident_cold:  SKIP / cascade @ ≤55%
```

**Hysteresis (Choppy):** N=2 composite confirmation prevents whipsaw.
First 2 days of new sub-regime label use previous CONFIRMED label (or
conservative fallback if NULL bootstrap).

---

## Layer 3 — Sector / Calendar pessimistic merge

**Rule types:** `type=boost` with `verdict=TAKE_FULL/TAKE_SMALL`,
`type=kill` with `verdict=SKIP` that are NOT sub-regime-only kills.

**Behavior:** Non-terminating. All matching rules collected.
Pessimistic composition rule:

```
SKIP > TAKE_SMALL > TAKE_FULL
```

The MOST CONSERVATIVE verdict among all matching rules wins.

**Boost rules CONFIRM but do NOT UPGRADE.** A TAKE_FULL boost rule
matching a sub-regime that's already eligible for TAKE_FULL produces
TAKE_FULL (no change). A TAKE_FULL boost matching a TAKE_SMALL
sub-regime eligibility STAYS at TAKE_SMALL (boost does not upgrade).

**Composition table:**

| Sub-regime baseline | Sector/Cal rule | Final |
|---|---|---|
| TAKE_FULL | (no rule) | TAKE_FULL |
| TAKE_FULL | TAKE_FULL boost | TAKE_FULL (confirmed) |
| TAKE_FULL | TAKE_SMALL | TAKE_SMALL (downgrade) |
| TAKE_FULL | SKIP | SKIP (downgrade) |
| TAKE_SMALL | TAKE_FULL boost | TAKE_SMALL (NO upgrade — Layer 3 cannot upgrade) |
| TAKE_SMALL | SKIP | SKIP |
| SKIP | (any) | SKIP |

---

## Layer 4 — Phase-5 override (upgrade-only)

**Rule types:** Not in v4 rule corpus directly; lookup in
`combinations_live_validated.parquet`.

**Behavior:** Phase-5 override CAN upgrade verdict (e.g.,
TAKE_SMALL → TAKE_FULL) when feature-specific live evidence exceeds
sub-regime base rate. Cannot downgrade.

**Trigger conditions (ALL required):**
1. `live_n >= 10`
2. `live_tier == "VALIDATED"`
3. Wilson 95% lower bound > Layer-3 verdict's calibrated WR + 5pp
4. Combo data within last 90 days (recency check)

**Selection (multiple matches):** Pick combo with highest Wilson
lower bound.

**Output:** Final verdict + override-aware calibrated WR. Telegram
should display both:
```
Calibrated WR: 76% (Phase-5 override on inside_bar=True, n=27, Wilson 76.6%)
Sub-regime base: 71.5% (boundary_hot)
```

---

## Worked Conflict Examples

### Example 1: Bear UP_TRI × Health (Layer 1 termination)

```
Signal: HDFC.NS UP_TRI in Bear regime, Health sector, vp=0.78, n60=-0.13

Layer 1 evaluation:
  - rule_007 (Health × UP_TRI × Bear) MATCHES → SKIP
  - TERMINATE

Final verdict: SKIP
Calibrated WR: 32% (n/a; signal blocked)
Reason: "Health sector hostile in Bear UP_TRI (32.4% lifetime in hot)"
```

### Example 2: Bull UP_TRI recovery_bull × Sep (pessimistic merge)

```
Signal: TCS.NS UP_TRI in Bull regime, IT sector, recovery_bull sub-regime,
        vol=Medium, fvg_low=true, month=September, wk4

Layer 1: No KILL match (rule_001 late_bull doesn't apply; rule_014 Sep
         is production_ready=false in initial deployment)

Layer 2: recovery_bull → TAKE_FULL eligible (60-72%)

Layer 3:
  - rule_003 (recovery_bull × vol=Med × fvg_low) → TAKE_FULL boost
  - rule_014 (Sep Bull UP_TRI) → SKIP (if active)
  Pessimistic merge:
    - If rule_014 active: SKIP wins
    - If rule_014 inactive (initial Phase B deployment): TAKE_FULL

Layer 4: No Bull VALIDATED combos (cell PROVISIONAL_OFF) → no override

Final verdict (Phase B): TAKE_FULL @ 72% calibrated
Final verdict (Phase D, after rule_014 active): SKIP
Reason (Phase D): "September Bull catastrophic month (-8.4pp); pessimistic merge"
```

### Example 3: Bear UP_TRI hot × Phase-5 override

```
Signal: TATA.NS UP_TRI in Bear regime, Metal sector, hot sub-regime
        (vp=0.73, n60=-0.12), feat_inside_bar=True

Layer 1: No KILL match (Metal not Health; not December)

Layer 2: hot → boundary_hot tier (vp 0.73 just-inside; n60 -0.12 just-inside)
         Calibrated baseline 71.5% (boundary_hot per B1)

Layer 3:
  - win_004 (Metal × UP_TRI × Bear) → TAKE_FULL boost
  Final after L3: TAKE_FULL @ 71.5%

Layer 4: Phase-5 override search
  - Combo (inside_bar_flag=True, Bear UP_TRI) VALIDATED, n=13, live_wr=92.3%,
    Wilson lower=66.7%
  - Override trigger check: 66.7% < 71.5% + 5pp = 76.5%? YES, 66.7% is
    BELOW 76.5%, so override does NOT trigger.
  - Sub-regime base wins.

Final verdict: TAKE_FULL @ 71.5% (boundary_hot)
WR source: sub_regime_boundary_hot (NOT phase5_override)
Reason: "Bear UP_TRI boundary_hot tier; Metal sector confirms; Phase-5 base
         insufficient to upgrade beyond sub-regime"
```

---

## Implementation pseudocode

```python
def evaluate_signal(signal, market_state, combo_db):
    # Layer 1: KILL terminating
    for rule in kill_rules_by_priority(active=True):
        if matches(signal, rule):
            return Verdict(rule.verdict, rule.expected_wr, "kill", rule.id)

    # Layer 2: Sub-regime gate
    sub_regime = detect_subregime(signal.regime, market_state)
    base_verdict, base_wr = sub_regime_baseline(sub_regime, signal.signal)

    if base_verdict == "SKIP":
        return Verdict("SKIP", base_wr, "sub_regime_skip", sub_regime)

    # Layer 3: Sector / Calendar pessimistic merge
    matched_rules = [r for r in non_kill_rules(active=True) if matches(signal, r)]
    final_verdict = base_verdict
    final_wr = base_wr
    triggered_ids = []

    for rule in matched_rules:
        if rule.verdict == "SKIP":
            return Verdict("SKIP", rule.expected_wr, "pessimistic_skip", rule.id)
        if rule.verdict == "TAKE_SMALL" and final_verdict == "TAKE_FULL":
            final_verdict = "TAKE_SMALL"
            final_wr = min(final_wr, rule.expected_wr)
        # TAKE_FULL boost: confirms, no upgrade
        triggered_ids.append(rule.id)

    # Layer 4: Phase-5 override (upgrade-only)
    override = find_phase5_override(signal, combo_db, base_wr)
    if override and override.wilson_lower > final_wr + 0.05:
        final_verdict = "TAKE_FULL"  # upgrade
        final_wr = override.wilson_lower
        return Verdict(final_verdict, final_wr, "phase5_override",
                       override.combo_id)

    return Verdict(final_verdict, final_wr, "composed", triggered_ids)
```

---

## Edge cases and tie-breaking

1. **Multiple Layer 1 matches:** Iterate by priority HIGH → MEDIUM → LOW.
   First match wins. Within same priority, by `id` lexicographic order.

2. **Multiple Layer 3 matches with same verdict:** Confirms the verdict;
   pick highest `expected_wr` for display.

3. **Sub-regime "unknown" (missing features):** Fail-closed → SKIP with
   reason="sub_regime_unknown".

4. **Conflicting Phase-5 overrides:** Pick max(Wilson_lower).

5. **Activation gate (first 10 days of regime change):** Shadow mode
   per Bull/Bear PRODUCTION_POSTURE; signals logged but not promoted.
   Verdicts shown as "SHADOW" in Telegram.
```

```b1_b2_coupling_analysis.md
# B1 + B2 Coupling Analysis

## Background

B1 (Bear warm-zone display) recommended a 4-tier confidence display
that surfaces boundary_hot vs confident_hot WR difference (71.5% vs
64.2%). B2 (Bear hard-threshold cliffs) recommended a continuous
sigmoid `hot_conf` score that smooths the same boundary effect.

Per Step 1.5+2 SUMMARY decision: **ship B1 (tiered) now; defer B2
(sigmoid) to Phase 2**. This document addresses the production gap
explicitly.

---

## 1. Production gap acknowledgment

Without B2's continuous sigmoid scoring, production retains a **cliff
effect at sub-regime boundaries**:

- Signal A: `vp=0.71, n60=-0.11` → boundary_hot (just-inside) → TAKE_FULL @ 71.5%
- Signal B: `vp=0.69, n60=-0.09` → boundary_cold (just-outside) → TAKE_SMALL @ 55-60%

A 2pp difference in vol_percentile and 2pp in 60d_return produces a
~12-15pp swing in displayed WR. This is the cliff B2 was designed to
eliminate.

B1's 4-tier display narrows the cliff (5 buckets vs 2) but does not
eliminate it. Boundary cells remain discrete buckets with hard tier
walls.

---

## 2. Trade-off analysis

### B1 (tiered) — what we ship

**Pros:**
- Aligns with existing percentile-bucket architecture (no new feature
  type to support)
- Trader sees uncertainty visibly via 4 distinct labels
  (confident_hot / boundary_hot / boundary_cold / confident_cold)
- Surfaces the counterintuitive `boundary_hot > confident_hot`
  finding directly in the UI
- Verdicts remain binary at sub-regime boundaries (TAKE_FULL vs
  TAKE_SMALL vs SKIP)

**Cons:**
- 5-tier walls retain cliff effect at each boundary (smaller cliffs
  than 2-tier, but still discrete)
- Tier labels can confuse trader (boundary_hot label sounds weaker
  than confident_hot, but is actually higher WR)
- WR estimates within a tier have no within-bucket gradient

### B2 (sigmoid) — deferred to Phase 2

**Pros:**
- Smooth WR gradient eliminates discrete cliffs entirely
- Single continuous `hot_conf` score per signal
- Future-proof for additional features (multivariate sigmoid)

**Cons:**
- Requires production support for continuous-feature scoring (rule
  schema change v4 → v5)
- Requires `bear_hot_conf` enrichment field added to scanner data
  pipeline (production engineering work)
- Sigmoid parameters (centers 0.70/-0.10, widths 0.05/0.03) are
  fitted to lifetime data; need quarterly re-fit cadence
- Verdict-bucket re-mapping needed (per B2 finding: soft TAKE_SMALL
  band has higher WR than soft TAKE_FULL band — labels need renaming)
- More complex trader briefing required

### Counter-argument

B1's binary-at-boundary verdicts may actually be operationally
preferable to B2's continuous gradient: traders make discrete TAKE/
SKIP decisions, not continuous size-up-by-X% decisions. Smooth verdict
gradient may not improve outcomes if trader translates to discrete
sizing buckets anyway.

This argues for B1 being a **stable production state**, not just an
intermediate.

---

## 3. B1-only production behavior recommendation

### Telegram tier display

Each Bear UP_TRI signal in Telegram shows tier label:

```
[BEAR · 🔥 BOUNDARY_HOT · WR 65-75%]
SIGNAL: HDFC.NS UP_TRI age=0
sub-regime: boundary_hot (vp=0.72, n60=-0.11)
Calibrated: 71.5% / Live observed: 94.6% / Sub-regime base: 71.5%

Action: TAKE_FULL
```

### 4-tier verdict mapping

| Tier | Verdict | Calibrated WR | Notes |
|---|---|---|---|
| confident_hot | TAKE_FULL | 60-65% | Deep stress; depth-of-stress is mid-tier |
| **boundary_hot** | **TAKE_FULL** | **65-75%** | **Highest WR (counterintuitive); early capitulation** |
| boundary_cold | TAKE_SMALL | 55-60% | Transitional; partial ingredient match |
| confident_cold | SKIP / apply Tier 1 cascade | ≤55% | Apply wk4 × swing_high=low if available |

### Calibrated WR alongside live observed (per B3)

Production must display BOTH calibrated and live observed WR per the
B3 framework:

```
Calibrated (sub-regime gated):     71.5%   ← what to expect
Live observed (n=74):              94.6%   ← reflects Phase-5 selection bias
Phase-5 override (if applicable):  76.6%   ← override candidate
```

This honesty is critical: live 94.6% is NOT reproducible at
production scale. Trader must understand the gap. Telegram footer or
PWA tooltip explains:

> "Live WR includes selection bias from validated patterns.
> Calibrated WR is the lifetime baseline + sub-regime tier — what
> the system expects in steady-state production."

### Trader briefing items

First-deployment briefing must explain:

1. **boundary_hot > confident_hot is real, not a typo.** Mechanism:
   early-stage capitulation reversals (cusp of hot) work better than
   deep-stress reversals (already-extended downtrends with overcrowded
   shorts).

2. **Calibrated WR < Live WR is expected.** The gap (e.g., 71.5% vs
   94.6%) is selection bias. Position-size on calibrated, not live.

3. **Tier labels carry counter-intuitive ordering.** "Boundary"
   sounds weaker than "Confident" but is actually higher WR.

---

## 4. Phase-2 trigger criteria for promoting B2 sigmoid

B2 should be promoted from Phase 2 to production when ONE of:

### Criterion A: Verdict-tier mismatch frequency exceeds threshold

After 6 months live operation:
- Track per-signal: tier classification, action taken, outcome
- Compute "tier accuracy" = % of trades where tier prediction matches
  realized cohort WR within ±5pp
- If tier accuracy < 70% (i.e., >30% of cohorts perform outside
  predicted band), tier walls are too coarse → promote B2

### Criterion B: Trader-observed cliff complaints

If trader reports >5 specific instances per quarter of "this signal
just barely missed boundary_hot but performed identically to
boundary_hot signals in actual outcome" — empirical confirmation that
the cliff is operational friction → promote B2.

### Criterion C: New continuous features added

If production adds NIFTY-level continuous features that benefit from
sigmoid scoring (e.g., `nifty_drawdown_depth`, `term_structure_signal`),
the sigmoid framework becomes broadly useful → promote B2 with v5
schema migration.

### Criterion D: 6-month minimum operational time

Regardless of A/B/C, defer B2 promotion for **at least 6 months
post-v4 cutover**. Stable v4 baseline is required before measuring
cliff impact. Earlier promotion risks confounding sigmoid effect with
v4 schema migration effects.

### Recommended decision date

**Phase-2 review checkpoint: 2027-Q1** (assuming v4 ships 2026-Q3).

By 2027-Q1, production should have:
- ≥6 months of v4 operation
- ≥1000 Bear UP_TRI signals across multiple sub-regime episodes
- Tier-accuracy data
- Live + calibrated WR comparison data
- Trader feedback log

Decision matrix at checkpoint:
- All criteria A, B, C, D pass → promote B2 to v5 schema
- Only D + (A or B) → revisit at 2027-Q3
- Only D → defer indefinitely; B1 is stable production state

---

## Summary

Ship B1 (4-tier display) now. Defer B2 (sigmoid) to Phase 2 with a
2027-Q1 review checkpoint. Production gap (cliff at tier boundaries)
is acknowledged but bounded: the B1 display narrows cliffs from 2
buckets to 5 and surfaces uncertainty visibly. B2's continuous
gradient is a UX improvement that may or may not translate to better
trade outcomes given discrete trader decision-making. Six months of
v4 operational data will tell us whether B2 is worth the schema
migration cost.
```

```validation_predictions.json
{
  "schema_version": 4,
  "predictions": [
    {
      "rule_id": "kill_001",
      "predicted_match_count": 653,
      "predicted_match_count_min": 522,
      "predicted_match_count_max": 784,
      "predicted_match_wr": 0.45,
      "predicted_match_wr_min": 0.40,
      "predicted_match_wr_max": 0.50,
      "predicted_lift_vs_baseline": -0.011,
      "source_playbook": "bear_downtri",
      "source_evidence": "Bank x DOWN_TRI x Bear lifetime n=653; live 0/11 confirms kill direction"
    },
    {
      "rule_id": "watch_001",
      "predicted_match_count": 27072,
      "predicted_match_count_min": 21658,
      "predicted_match_count_max": 32486,
      "predicted_match_wr": 0.523,
      "predicted_match_wr_min": 0.473,
      "predicted_match_wr_max": 0.573,
      "predicted_lift_vs_baseline": 0.0,
      "source_playbook": "choppy_uptri",
      "source_evidence": "All Choppy UP_TRI lifetime n=27,072; warning is informational"
    },
    {
      "rule_id": "win_001",
      "predicted_match_count": 280,
      "predicted_match_count_min": 224,
      "predicted_match_count_max": 336,
      "predicted_match_wr": 0.72,
      "predicted_match_wr_min": 0.67,
      "predicted_match_wr_max": 0.77,
      "predicted_lift_vs_baseline": 0.183,
      "source_playbook": "bear_uptri",
      "source_evidence": "Auto x UP_TRI x Bear hot lifetime ~280 signals; Auto in hot 74.3% lifetime"
    },
    {
      "rule_id": "win_002",
      "predicted_match_count": 320,
      "predicted_match_count_min": 256,
      "predicted_match_count_max": 384,
      "predicted_match_wr": 0.74,
      "predicted_match_wr_min": 0.69,
      "predicted_match_wr_max": 0.79,
      "predicted_lift_vs_baseline": 0.203,
      "source_playbook": "bear_uptri",
      "source_evidence": "FMCG x UP_TRI x Bear hot lifetime cohort; FMCG in hot 76.0%"
    },
    {
      "rule_id": "win_003",
      "predicted_match_count": 250,
      "predicted_match_count_min": 200,
      "predicted_match_count_max": 300,
      "predicted_match_wr": 0.70,
      "predicted_match_wr_min": 0.65,
      "predicted_match_wr_max": 0.75,
      "predicted_lift_vs_baseline": 0.143,
      "source_playbook": "bear_uptri",
      "source_evidence": "IT x UP_TRI x Bear hot lifetime cohort"
    },
    {
      "rule_id": "win_004",
      "predicted_match_count": 200,
      "predicted_match_count_min": 160,
      "predicted_match_count_max": 240,
      "predicted_match_wr": 0.68,
      "predicted_match_wr_min": 0.63,
      "predicted_match_wr_max": 0.73,
      "predicted_lift_vs_baseline": 0.123,
      "source_playbook": "bear_uptri",
      "source_evidence": "Metal x UP_TRI x Bear hot lifetime cohort"
    },
    {
      "rule_id": "win_005",
      "predicted_match_count": 180,
      "predicted_match_count_min": 144,
      "predicted_match_count_max": 216,
      "predicted_match_wr": 0.72,
      "predicted_match_wr_min": 0.67,
      "predicted_match_wr_max": 0.77,
      "predicted_lift_vs_baseline": 0.191,
      "source_playbook": "bear_uptri",
      "source_evidence": "Pharma x UP_TRI x Bear hot lifetime; Pharma in hot 74.8%"
    },
    {
      "rule_id": "win_006",
      "predicted_match_count": 150,
      "predicted_match_count_min": 120,
      "predicted_match_count_max": 180,
      "predicted_match_wr": 0.65,
      "predicted_match_wr_min": 0.60,
      "predicted_match_wr_max": 0.70,
      "predicted_lift_vs_baseline": 0.093,
      "source_playbook": "bear_uptri",
      "source_evidence": "Infra x UP_TRI x Bear hot lifetime cohort"
    },
    {
      "rule_id": "win_007",
      "predicted_match_count": 86,
      "predicted_match_count_min": 69,
      "predicted_match_count_max": 103,
      "predicted_match_wr": 0.65,
      "predicted_match_wr_min": 0.60,
      "predicted_match_wr_max": 0.70,
      "predicted_lift_vs_baseline": 0.164,
      "source_playbook": "bear_bullproxy",
      "source_evidence": "Bear BULL_PROXY hot lifetime n=86, 63.7% WR"
    },
    {
      "rule_id": "rule_001",
      "predicted_match_count": 2699,
      "predicted_match_count_min": 2159,
      "predicted_match_count_max": 3239,
      "predicted_match_wr": 0.451,
      "predicted_match_wr_min": 0.401,
      "predicted_match_wr_max": 0.501,
      "predicted_lift_vs_baseline": -0.069,
      "source_playbook": "bull_uptri",
      "source_evidence": "late_bull Bull UP_TRI lifetime n=2,699 at 45.1% WR"
    },
    {
      "rule_id": "rule_002",
      "predicted_match_count": 268,
      "predicted_match_count_min": 214,
      "predicted_match_count_max": 322,
      "predicted_match_wr": 0.436,
      "predicted_match_wr_min": 0.386,
      "predicted_match_wr_max": 0.486,
      "predicted_lift_vs_baseline": -0.075,
      "source_playbook": "bull_bullproxy",
      "source_evidence": "late_bull Bull BULL_PROXY lifetime n=268 at 43.6% WR"
    },
    {
      "rule_id": "rule_003",
      "predicted_match_count": 390,
      "predicted_match_count_min": 312,
      "predicted_match_count_max": 468,
      "predicted_match_wr": 0.741,
      "predicted_match_wr_min": 0.691,
      "predicted_match_wr_max": 0.791,
      "predicted_lift_vs_baseline": 0.221,
      "source_playbook": "bull_uptri",
      "source_evidence": "recovery_bull x vol=Med x fvg_low: n=390, WR 74.1% lifetime"
    },
    {
      "rule_id": "rule_004",
      "predicted_match_count": 128,
      "predicted_match_count_min": 102,
      "predicted_match_count_max": 154,
      "predicted_match_wr": 0.625,
      "predicted_match_wr_min": 0.575,
      "predicted_match_wr_max": 0.675,
      "predicted_lift_vs_baseline": 0.114,
      "source_playbook": "bull_bullproxy",
      "source_evidence": "healthy_bull x nifty_20d=high: n=128, WR 62.5% lifetime"
    },
    {
      "rule_id": "rule_005",
      "predicted_match_count": 139,
      "predicted_match_count_min": 111,
      "predicted_match_count_max": 167,
      "predicted_match_wr": 0.363,
      "predicted_match_wr_min": 0.313,
      "predicted_match_wr_max": 0.413,
      "predicted_lift_vs_baseline": -0.110,
      "source_playbook": "bear_bullproxy",
      "source_evidence": "vol_climax x BULL_PROXY x Bear: -11.0pp anti, lifetime cohort"
    },
    {
      "rule_id": "rule_006",
      "predicted_match_count": 80,
      "predicted_match_count_min": 64,
      "predicted_match_count_max": 96,
      "predicted_match_wr": 0.395,
      "predicted_match_wr_min": 0.345,
      "predicted_match_wr_max": 0.445,
      "predicted_lift_vs_baseline": -0.075,
      "source_playbook": "bull_bullproxy",
      "source_evidence": "vol_climax x BULL_PROXY x Bull-late_bull: -7.5pp anti"
    },
    {
      "rule_id": "rule_007",
      "predicted_match_count": 158,
      "predicted_match_count_min": 126,
      "predicted_match_count_max": 190,
      "predicted_match_wr": 0.324,
      "predicted_match_wr_min": 0.274,
      "predicted_match_wr_max": 0.374,
      "predicted_lift_vs_baseline": -0.233,
      "source_playbook": "bear_uptri",
      "source_evidence": "Health Bear UP_TRI in hot 32.4%; AVOID hostile sector"
    },
    {
      "rule_id": "rule_008",
      "predicted_match_count": 850,
      "predicted_match_count_min": 680,
      "predicted_match_count_max": 1020,
      "predicted_match_wr": 0.307,
      "predicted_match_wr_min": 0.257,
      "predicted_match_wr_max": 0.357,
      "predicted_lift_vs_baseline": -0.250,
      "source_playbook": "bear_uptri",
      "source_evidence": "December Bear UP_TRI -25pp catastrophic"
    },
    {
      "rule_id": "rule_009",
      "predicted_match_count": 3338,
      "predicted_match_count_min": 2670,
      "predicted_match_count_max": 4006,
      "predicted_match_wr": 0.361,
      "predicted_match_wr_min": 0.311,
      "predicted_match_wr_max": 0.411,
      "predicted_lift_vs_baseline": -0.162,
      "source_playbook": "choppy_uptri",
      "source_evidence": "February Choppy UP_TRI -16.2pp on n=3,338 (Indian Budget vol)"
    },
    {
      "rule_id": "rule_010",
      "predicted_match_count": 1931,
      "predicted_match_count_min": 1545,
      "predicted_match_count_max": 2317,
      "predicted_match_wr": 0.50,
      "predicted_match_wr_min": 0.45,
      "predicted_match_wr_max": 0.55,
      "predicted_lift_vs_baseline": 0.0,
      "source_playbook": "choppy_bullproxy",
      "source_evidence": "Entire Choppy BULL_PROXY cell n=1,931, baseline 50%, KILL verdict"
    },
    {
      "rule_id": "rule_011",
      "predicted_match_count": 1446,
      "predicted_match_count_min": 1157,
      "predicted_match_count_max": 1735,
      "predicted_match_wr": 0.536,
      "predicted_match_wr_min": 0.486,
      "predicted_match_wr_max": 0.586,
      "predicted_lift_vs_baseline": 0.075,
      "source_playbook": "bear_downtri",
      "source_evidence": "Bear DOWN_TRI wk2/wk3 filter: n=1,446, 53.6% WR, +7.5pp"
    },
    {
      "rule_id": "rule_012",
      "predicted_match_count": 3374,
      "predicted_match_count_min": 2699,
      "predicted_match_count_max": 4049,
      "predicted_match_wr": 0.633,
      "predicted_match_wr_min": 0.583,
      "predicted_match_wr_max": 0.683,
      "predicted_lift_vs_baseline": 0.130,
      "source_playbook": "bear_uptri",
      "source_evidence": "Cold cascade Tier 1: wk4 x swing_high=low: n=3,374, 63.3% WR"
    },
    {
      "rule_id": "rule_013",
      "predicted_match_count": 2400,
      "predicted_match_count_min": 1920,
      "predicted_match_count_max": 2880,
      "predicted_match_wr": 0.491,
      "predicted_match_wr_min": 0.441,
      "predicted_match_wr_max": 0.541,
      "predicted_lift_vs_baseline": -0.029,
      "source_playbook": "bull_uptri",
      "source_evidence": "Energy Bull UP_TRI -2.9pp lifetime"
    },
    {
      "rule_id": "rule_014",
      "predicted_match_count": 1850,
      "predicted_match_count_min": 1480,
      "predicted_match_count_max": 2220,
      "predicted_match_wr": 0.436,
      "predicted_match_wr_min": 0.386,
      "predicted_match_wr_max": 0.486,
      "predicted_lift_vs_baseline": -0.084,
      "source_playbook": "bull_uptri",
      "source_evidence": "September Bull UP_TRI/BULL_PROXY -8.4pp"
    },
    {
      "rule_id": "rule_015",
      "predicted_match_count": 600,
      "predicted_match_count_min": 480,
      "predicted_match_count_max": 720,
      "predicted_match_wr": 0.413,
      "predicted_match_wr_min": 0.363,
      "predicted_match_wr_max": 0.463,
      "predicted_lift_vs_baseline": -0.047,
      "source_playbook": "choppy_downtri",
      "source_evidence": "Pharma Choppy DOWN_TRI -4.7pp"
    },
    {
      "rule_id": "rule_016",
      "predicted_match_count": 1200,
      "predicted_match_count_min": 960,
      "predicted_match_count_max": 1440,
      "predicted_match_wr": 0.398,
      "predicted_match_wr_min": 0.348,
      "predicted_match_wr_max": 0.448,
      "predicted_lift_vs_baseline": -0.062,
      "source_playbook": "choppy_downtri",
      "source_evidence": "Friday Choppy DOWN_TRI -6.2pp"
    },
    {
      "rule_id": "rule_017",
      "predicted_match_count": 2092,
      "predicted_match_count_min": 1674,
      "predicted_match_count_max": 2510,
      "predicted_match_wr": 0.482,
      "predicted_match_wr_min": 0.432,
      "predicted_match_wr_max": 0.532,
      "predicted_lift_vs_baseline": -0.022,
      "source_playbook": "choppy_uptri",
      "source_evidence": "Metal Choppy UP_TRI -2.2pp on n=2,092"
    }
  ]
}
```

```integration_notes.md
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
```