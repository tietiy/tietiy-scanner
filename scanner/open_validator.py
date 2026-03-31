{
  "shadow_mode": true,
  "rules": {
    "min_score": {
      "active": false,
      "threshold": 7,
      "sa_threshold": 5,
      "description": "Minimum score to pass. SA = second attempt threshold"
    },
    "min_rr": {
      "active": false,
      "threshold": 2.0,
      "description": "Minimum R:R ratio required"
    },
    "regime_alignment": {
      "active": false,
      "description": "UP_TRI Bull/Neutral only. DOWN_TRI Bear/Neutral only"
    },
    "require_volume": {
      "active": false,
      "description": "vol_confirm must be true"
    },
    "grade_gate": {
      "active": false,
      "allowed": ["A", "B", "C"],
      "description": "Only listed grades pass"
    },
    "clean_air": {
      "active": false,
      "description": "Clean air above target required"
    },
    "delivery_volume": {
      "active": false,
      "description": "Phase 3 — delivery_pct filter. Do not activate yet"
    }
  }
}
