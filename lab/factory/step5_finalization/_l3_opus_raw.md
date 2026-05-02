```barcode_format_v1.md
# Barcode Format v1 — Production Scanner Signal Encoding

## Purpose

The barcode is a self-contained JSON object emitted at signal-fire-time.
It captures the runtime decision (regime + sub-regime classification,
rule matches, verdict, confidence, calibrated WR, cap statuses) for a
single signal. One barcode per signal. Barcodes are the runtime
equivalent of a Lab cell verdict.

## Top-level structure

```
{
  "barcode_version": 1,
  "barcode_id": "<signal_id>",         # mirrors signal_history.id
  "schema_link": "unified_rules_v4_1_post_L2.json",

  "signal_ref": { ... },               # core identifying fields
  "regime_state": { ... },             # regime + sub_regime + market vol
  "rule_match": { ... },               # matched rules + verdict
  "confidence": { ... },               # tier + calibrated WR + band
  "caps": { ... },                     # name/date/sector concentration
  "execution": { ... },                # entry/stop/target if taken
  "context": { ... }                   # optional: scanner version, notes
}
```

## Required fields

### Top level

| Field | Type | Description |
|-------|------|-------------|
| `barcode_version` | int | Schema version (currently `1`) |
| `barcode_id` | string | Matches `signal_history.id` (e.g. `"2026-04-29-UBL-UP_TRI"`) |
| `schema_link` | string | Rules file name barcode was generated against |
| `generated_at` | string | ISO-8601 UTC timestamp of barcode emission |

### `signal_ref` (required)

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | e.g. `"UBL.NS"` |
| `signal` | string | `"UP_TRI"` / `"DOWN_TRI"` / `"BULL_PROXY"` |
| `direction` | string | `"LONG"` / `"SHORT"` |
| `date` | string (ISO-8601) | Scan date |
| `sector` | string | e.g. `"Consumer"` |

### `regime_state` (required)

| Field | Type | Description |
|-------|------|-------------|
| `regime` | string | `"Bull"` / `"Bear"` / `"Choppy"` |
| `sub_regime` | string | e.g. `"hot"`, `"cold"`, `"warm"`, `"recovery_bull"`, `"healthy_bull"`, `"late_bull"`, `"breadth_medium"` |
| `regime_score` | int | Underlying regime composite score |
| `vol_q` | string | `"Low"` / `"Average"` / `"High"` |
| `breadth_q` | string \| null | `"low"` / `"medium"` / `"high"` (null if N/A for cell) |
| `week_of_month` | int | 1–5 (used for wk3-gated rules) |

### `rule_match` (required)

| Field | Type | Description |
|-------|------|-------------|
| `cell` | string | e.g. `"bear_uptri"`, `"choppy_bullproxy"` |
| `cell_status` | string | `"LIVE"` / `"DEFERRED"` / `"PROVISIONAL_OFF"` / `"CANDIDATE"` / `"KILL"` |
| `matched_rule_ids` | array<string> | Rule IDs from v4.1 that fired (0–N) |
| `dominant_rule_id` | string \| null | Primary rule driving verdict (null if no match) |
| `verdict` | string | `"TAKE_FULL"` / `"TAKE_SMALL"` / `"WATCH"` / `"SKIP"` / `"REJECT"` |
| `verdict_reason` | string | Short human-readable rationale |

### `confidence` (required)

| Field | Type | Description |
|-------|------|-------------|
| `tier` | string | `"confident_hot"` / `"boundary_hot"` / `"confident_cold"` / `"boundary_cold"` (B1 4-tier) — or `"n/a"` |
| `confidence_label` | string | `"HIGH"` / `"MEDIUM"` / `"LOW"` (from rule) |
| `calibrated_wr` | float | 0.0–1.0 |
| `wr_band_low` | float | 0.0–1.0 (lower CI) |
| `wr_band_high` | float | 0.0–1.0 (upper CI) |
| `expected_wr_source` | string | `"rule"` / `"calibration"` / `"prior"` |

### `caps` (required)

| Field | Type | Description |
|-------|------|-------------|
| `name_cap_status` | string | `"OK"` / `"REPEAT"` (same symbol fired in last 6 days) |
| `date_cap_status` | string | `"OK"` / `"CORRELATED"` (>N signals same day) |
| `sector_concentration_status` | string | `"OK"` / `"OVER"` (sector cap exceeded) |
| `caps_passed` | bool | Convenience: all three == `"OK"` |

## Optional fields

### `execution` (present when `verdict ∈ {TAKE_FULL, TAKE_SMALL}`)

| Field | Type | Description |
|-------|------|-------------|
| `entry` | float | |
| `stop` | float | |
| `target_price` | float | |
| `atr` | float | |
| `position_size_mult` | float | 1.0 for TAKE_FULL, 0.5 for TAKE_SMALL |
| `trade_mechanism` | string | From matched rule (e.g. `"momentum_continuation"`) |

### `context` (always optional, may be `{}`)

| Field | Type | Description |
|-------|------|-------------|
| `scanner_version` | string | e.g. `"v2.0"` |
| `notes` | string \| null | Free-text annotation |
| `shadow_mode` | bool | True if this barcode was emitted in shadow phase |
| `kill_reasons` | array<string> | If `verdict == REJECT`, list of kill rule IDs |

## Field ordering convention

Within each object, order fields by:
1. Identity (id, version)
2. Classification (regime, cell, rule)
3. Decision (verdict, tier)
4. Numerics (wr, prices)
5. Status flags (caps)
6. Free-form context last

This makes barcodes greppable / scannable in raw form.

## Self-documentation strategy

Each barcode is interpretable without an external lookup:

1. `schema_link` names the rules file the decision was made against.
2. `matched_rule_ids[]` + `dominant_rule_id` provide the audit trail.
3. `verdict_reason` is a human-readable string a trader can read in
   Telegram without consulting the rules file.
4. `cell_status` exposes whether the cell is LIVE/DEFERRED/etc., so the
   trader knows the trustworthiness regime.
5. `confidence.tier` + `calibrated_wr` + `wr_band_*` together form a
   complete confidence statement.
6. `caps_passed` boolean is the single-glance gate; the three sub-flags
   give detail on which cap (if any) tripped.

## Backward compatibility

- The barcode does NOT replace `signal_history.json`. It augments it.
- `barcode_id` == `signal_history.id` — 1:1 join key.
- Phase A (shadow): barcode written to parallel `barcodes/<date>.jsonl`,
  signal_history unchanged.
- Phase B (link): signal_history row gets an additional field
  `barcode_ref` pointing at the barcode file/offset.
- Phase C (consolidate): selected barcode fields (verdict, tier,
  calibrated_wr, caps_passed) are copied into signal_history for query
  convenience; full barcode remains in barcode store.

Existing signal_history fields (`regime`, `regime_score`, `vol_q`,
`grade`, etc.) remain valid — barcode `regime_state` is a richer
overlay, not a replacement.
```

```barcode_examples.json
{
  "examples": [
    {
      "_label": "Bear UP_TRI hot — TAKE_FULL with sector boost",
      "barcode_version": 1,
      "barcode_id": "2026-04-29-UBL-UP_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-04-29T03:17:00Z",
      "signal_ref": {
        "symbol": "UBL.NS",
        "signal": "UP_TRI",
        "direction": "LONG",
        "date": "2026-04-29",
        "sector": "Consumer"
      },
      "regime_state": {
        "regime": "Bear",
        "sub_regime": "hot",
        "regime_score": -2,
        "vol_q": "Average",
        "breadth_q": "low",
        "week_of_month": 5
      },
      "rule_match": {
        "cell": "bear_uptri",
        "cell_status": "LIVE",
        "matched_rule_ids": ["BU_HOT_BASE", "BU_SEC_LEAD_BOOST"],
        "dominant_rule_id": "BU_HOT_BASE",
        "verdict": "TAKE_FULL",
        "verdict_reason": "bear_uptri hot base + sector leading boost"
      },
      "confidence": {
        "tier": "confident_hot",
        "confidence_label": "HIGH",
        "calibrated_wr": 0.62,
        "wr_band_low": 0.55,
        "wr_band_high": 0.69,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "execution": {
        "entry": 1477.2,
        "stop": 1375.27,
        "target_price": 1681.06,
        "atr": 49.73,
        "position_size_mult": 1.0,
        "trade_mechanism": "bear_relief_continuation"
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": null,
        "shadow_mode": false
      }
    },
    {
      "_label": "Bear UP_TRI cold — TAKE_FULL via cascade",
      "barcode_version": 1,
      "barcode_id": "2026-04-22-INFY-UP_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-04-22T03:18:00Z",
      "signal_ref": {
        "symbol": "INFY.NS",
        "signal": "UP_TRI",
        "direction": "LONG",
        "date": "2026-04-22",
        "sector": "IT"
      },
      "regime_state": {
        "regime": "Bear",
        "sub_regime": "cold",
        "regime_score": -4,
        "vol_q": "High",
        "breadth_q": "low",
        "week_of_month": 4
      },
      "rule_match": {
        "cell": "bear_uptri",
        "cell_status": "LIVE",
        "matched_rule_ids": ["BU_COLD_CASCADE"],
        "dominant_rule_id": "BU_COLD_CASCADE",
        "verdict": "TAKE_FULL",
        "verdict_reason": "bear_uptri cold cascade rule (vol_high + sec_leading)"
      },
      "confidence": {
        "tier": "confident_cold",
        "confidence_label": "HIGH",
        "calibrated_wr": 0.58,
        "wr_band_low": 0.49,
        "wr_band_high": 0.66,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "execution": {
        "entry": 1432.5,
        "stop": 1351.0,
        "target_price": 1601.5,
        "atr": 38.2,
        "position_size_mult": 1.0,
        "trade_mechanism": "bear_cold_cascade"
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": null,
        "shadow_mode": false
      }
    },
    {
      "_label": "Bull UP_TRI recovery_bull — TAKE_FULL with filter",
      "barcode_version": 1,
      "barcode_id": "2026-05-12-RELIANCE-UP_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-05-12T03:15:00Z",
      "signal_ref": {
        "symbol": "RELIANCE.NS",
        "signal": "UP_TRI",
        "direction": "LONG",
        "date": "2026-05-12",
        "sector": "Energy"
      },
      "regime_state": {
        "regime": "Bull",
        "sub_regime": "recovery_bull",
        "regime_score": 3,
        "vol_q": "Average",
        "breadth_q": "medium",
        "week_of_month": 2
      },
      "rule_match": {
        "cell": "bull_uptri",
        "cell_status": "PROVISIONAL_OFF",
        "matched_rule_ids": ["BLU_RECOVERY_FILTER"],
        "dominant_rule_id": "BLU_RECOVERY_FILTER",
        "verdict": "TAKE_FULL",
        "verdict_reason": "bull_uptri recovery_bull, vol_confirm + rs_strong filter passed"
      },
      "confidence": {
        "tier": "boundary_hot",
        "confidence_label": "MEDIUM",
        "calibrated_wr": 0.54,
        "wr_band_low": 0.46,
        "wr_band_high": 0.61,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "execution": {
        "entry": 2810.0,
        "stop": 2701.0,
        "target_price": 3028.0,
        "atr": 52.3,
        "position_size_mult": 1.0,
        "trade_mechanism": "bull_continuation"
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": "PROVISIONAL_OFF cell — monitor",
        "shadow_mode": false
      }
    },
    {
      "_label": "Bull DOWN_TRI late_bull × wk3 — TAKE_SMALL",
      "barcode_version": 1,
      "barcode_id": "2026-06-17-HDFCBANK-DOWN_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-06-17T03:20:00Z",
      "signal_ref": {
        "symbol": "HDFCBANK.NS",
        "signal": "DOWN_TRI",
        "direction": "SHORT",
        "date": "2026-06-17",
        "sector": "Financials"
      },
      "regime_state": {
        "regime": "Bull",
        "sub_regime": "late_bull",
        "regime_score": 5,
        "vol_q": "Average",
        "breadth_q": "high",
        "week_of_month": 3
      },
      "rule_match": {
        "cell": "bull_downtri",
        "cell_status": "PROVISIONAL_OFF",
        "matched_rule_ids": ["BLD_LATE_WK3"],
        "dominant_rule_id": "BLD_LATE_WK3",
        "verdict": "TAKE_SMALL",
        "verdict_reason": "bull_downtri late_bull × wk3 narrow window"
      },
      "confidence": {
        "tier": "boundary_cold",
        "confidence_label": "LOW",
        "calibrated_wr": 0.48,
        "wr_band_low": 0.39,
        "wr_band_high": 0.56,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "execution": {
        "entry": 1685.5,
        "stop": 1742.0,
        "target_price": 1572.5,
        "atr": 22.1,
        "position_size_mult": 0.5,
        "trade_mechanism": "late_bull_topfade"
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": "TAKE_SMALL — provisional cell",
        "shadow_mode": false
      }
    },
    {
      "_label": "Bull BULL_PROXY healthy_bull × 20d=high — TAKE_FULL",
      "barcode_version": 1,
      "barcode_id": "2026-07-08-TCS-BULL_PROXY",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-07-08T03:16:00Z",
      "signal_ref": {
        "symbol": "TCS.NS",
        "signal": "BULL_PROXY",
        "direction": "LONG",
        "date": "2026-07-08",
        "sector": "IT"
      },
      "regime_state": {
        "regime": "Bull",
        "sub_regime": "healthy_bull",
        "regime_score": 4,
        "vol_q": "Average",
        "breadth_q": "high",
        "week_of_month": 2
      },
      "rule_match": {
        "cell": "bull_bullproxy",
        "cell_status": "PROVISIONAL_OFF",
        "matched_rule_ids": ["BLP_HEALTHY_20DHIGH"],
        "dominant_rule_id": "BLP_HEALTHY_20DHIGH",
        "verdict": "TAKE_FULL",
        "verdict_reason": "bull_bullproxy healthy × 20d_breadth high"
      },
      "confidence": {
        "tier": "confident_hot",
        "confidence_label": "MEDIUM",
        "calibrated_wr": 0.56,
        "wr_band_low": 0.48,
        "wr_band_high": 0.63,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "execution": {
        "entry": 4012.0,
        "stop": 3855.0,
        "target_price": 4326.0,
        "atr": 71.2,
        "position_size_mult": 1.0,
        "trade_mechanism": "bull_proxy_breakout"
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": null,
        "shadow_mode": false
      }
    },
    {
      "_label": "Choppy UP_TRI breadth=med × vol=High — TAKE_FULL",
      "barcode_version": 1,
      "barcode_id": "2026-03-11-MARUTI-UP_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-03-11T03:18:00Z",
      "signal_ref": {
        "symbol": "MARUTI.NS",
        "signal": "UP_TRI",
        "direction": "LONG",
        "date": "2026-03-11",
        "sector": "Auto"
      },
      "regime_state": {
        "regime": "Choppy",
        "sub_regime": "breadth_medium",
        "regime_score": 2,
        "vol_q": "High",
        "breadth_q": "medium",
        "week_of_month": 2
      },
      "rule_match": {
        "cell": "choppy_uptri",
        "cell_status": "CANDIDATE",
        "matched_rule_ids": ["CU_BREADTH_MED_VOL_HIGH"],
        "dominant_rule_id": "CU_BREADTH_MED_VOL_HIGH",
        "verdict": "TAKE_FULL",
        "verdict_reason": "choppy_uptri breadth=medium × vol=High candidate rule"
      },
      "confidence": {
        "tier": "boundary_hot",
        "confidence_label": "MEDIUM",
        "calibrated_wr": 0.52,
        "wr_band_low": 0.44,
        "wr_band_high": 0.60,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "execution": {
        "entry": 12450.0,
        "stop": 12005.0,
        "target_price": 13340.0,
        "atr": 198.5,
        "position_size_mult": 1.0,
        "trade_mechanism": "choppy_breakout"
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": "CANDIDATE cell — track outcomes",
        "shadow_mode": false
      }
    },
    {
      "_label": "Choppy BULL_PROXY — REJECT (cell killed)",
      "barcode_version": 1,
      "barcode_id": "2026-03-19-ITC-BULL_PROXY",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-03-19T03:14:00Z",
      "signal_ref": {
        "symbol": "ITC.NS",
        "signal": "BULL_PROXY",
        "direction": "LONG",
        "date": "2026-03-19",
        "sector": "Consumer"
      },
      "regime_state": {
        "regime": "Choppy",
        "sub_regime": "breadth_low",
        "regime_score": 1,
        "vol_q": "Average",
        "breadth_q": "low",
        "week_of_month": 3
      },
      "rule_match": {
        "cell": "choppy_bullproxy",
        "cell_status": "KILL",
        "matched_rule_ids": ["CBP_KILL_ALL"],
        "dominant_rule_id": "CBP_KILL_ALL",
        "verdict": "REJECT",
        "verdict_reason": "choppy_bullproxy cell entirely killed (Lab L2)"
      },
      "confidence": {
        "tier": "n/a",
        "confidence_label": "LOW",
        "calibrated_wr": 0.0,
        "wr_band_low": 0.0,
        "wr_band_high": 0.0,
        "expected_wr_source": "rule"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": "Rejected at cell level",
        "shadow_mode": false,
        "kill_reasons": ["CBP_KILL_ALL"]
      }
    },
    {
      "_label": "Choppy DOWN_TRI Friday — SKIP",
      "barcode_version": 1,
      "barcode_id": "2026-05-08-AXISBANK-DOWN_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-05-08T03:19:00Z",
      "signal_ref": {
        "symbol": "AXISBANK.NS",
        "signal": "DOWN_TRI",
        "direction": "SHORT",
        "date": "2026-05-08",
        "sector": "Financials"
      },
      "regime_state": {
        "regime": "Choppy",
        "sub_regime": "breadth_medium",
        "regime_score": 2,
        "vol_q": "Average",
        "breadth_q": "medium",
        "week_of_month": 2
      },
      "rule_match": {
        "cell": "choppy_downtri",
        "cell_status": "CANDIDATE",
        "matched_rule_ids": ["CD_FRIDAY_SKIP"],
        "dominant_rule_id": "CD_FRIDAY_SKIP",
        "verdict": "SKIP",
        "verdict_reason": "choppy_downtri rule requires wk3, today is Friday wk2 — skip"
      },
      "confidence": {
        "tier": "n/a",
        "confidence_label": "LOW",
        "calibrated_wr": 0.0,
        "wr_band_low": 0.0,
        "wr_band_high": 0.0,
        "expected_wr_source": "rule"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": true
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": "Day-of-week filter",
        "shadow_mode": false
      }
    },
    {
      "_label": "Bear UP_TRI hot — caps tripped (sector OVER)",
      "barcode_version": 1,
      "barcode_id": "2026-04-30-DABUR-UP_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-04-30T03:17:00Z",
      "signal_ref": {
        "symbol": "DABUR.NS",
        "signal": "UP_TRI",
        "direction": "LONG",
        "date": "2026-04-30",
        "sector": "Consumer"
      },
      "regime_state": {
        "regime": "Bear",
        "sub_regime": "hot",
        "regime_score": -2,
        "vol_q": "Average",
        "breadth_q": "low",
        "week_of_month": 5
      },
      "rule_match": {
        "cell": "bear_uptri",
        "cell_status": "LIVE",
        "matched_rule_ids": ["BU_HOT_BASE"],
        "dominant_rule_id": "BU_HOT_BASE",
        "verdict": "WATCH",
        "verdict_reason": "Rule matched but Consumer sector cap exceeded — downgrade to WATCH"
      },
      "confidence": {
        "tier": "confident_hot",
        "confidence_label": "HIGH",
        "calibrated_wr": 0.62,
        "wr_band_low": 0.55,
        "wr_band_high": 0.69,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "OK",
        "date_cap_status": "OK",
        "sector_concentration_status": "OVER",
        "caps_passed": false
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": "Already 3 Consumer LONGs today",
        "shadow_mode": false
      }
    },
    {
      "_label": "Name repeat — REPEAT cap status, downgrade",
      "barcode_version": 1,
      "barcode_id": "2026-04-30-UBL-UP_TRI",
      "schema_link": "unified_rules_v4_1_post_L2.json",
      "generated_at": "2026-04-30T03:17:00Z",
      "signal_ref": {
        "symbol": "UBL.NS",
        "signal": "UP_TRI",
        "direction": "LONG",
        "date": "2026-04-30",
        "sector": "Consumer"
      },
      "regime_state": {
        "regime": "Bear",
        "sub_regime": "hot",
        "regime_score": -2,
        "vol_q": "Average",
        "breadth_q": "low",
        "week_of_month": 5
      },
      "rule_match": {
        "cell": "bear_uptri",
        "cell_status": "LIVE",
        "matched_rule_ids": ["BU_HOT_BASE"],
        "dominant_rule_id": "BU_HOT_BASE",
        "verdict": "SKIP",
        "verdict_reason": "UBL fired 1 day ago — name cap REPEAT, skip"
      },
      "confidence": {
        "tier": "confident_hot",
        "confidence_label": "HIGH",
        "calibrated_wr": 0.62,
        "wr_band_low": 0.55,
        "wr_band_high": 0.69,
        "expected_wr_source": "calibration"
      },
      "caps": {
        "name_cap_status": "REPEAT",
        "date_cap_status": "OK",
        "sector_concentration_status": "OK",
        "caps_passed": false
      },
      "context": {
        "scanner_version": "v2.0",
        "notes": "6-day name cap",
        "shadow_mode": false
      }
    }
  ]
}
```

```integration_spec.md
# Production Scanner — Barcode Integration Spec

## 1. Scan flow placement

Current production scanner pipeline (simplified):

```
load_data → compute_regime → screen_signals → grade_signals
         → compute_caps → write_signal_history → telegram_emit
```

Barcode generation slots in **between `compute_caps` and
`write_signal_history`**:

```
... → grade_signals → compute_caps
                    → BARCODE_BUILD       ← new
                    → write_signal_history
                    → write_barcode_store  ← new
                    → telegram_emit (uses barcode for formatting)
```

Rationale: by the time `compute_caps` finishes, all inputs needed for
the barcode (regime/sub_regime, matched rules, calibrated WR, cap
statuses) are available. Barcode is built once, then used by both the
persistence layer and the Telegram formatter.

## 2. Module ownership

New module: `tie_tiy/scanner/barcode.py`

Public API:

```python
def build_barcode(
    signal: SignalRow,            # current signal_history row
    regime_state: RegimeState,    # output of compute_regime
    rule_engine: RuleEngine,      # loaded from unified_rules_v4_1_post_L2.json
    caps_result: CapsResult,      # output of compute_caps
    calibrator: Calibrator,       # WR calibration model
    scanner_version: str,
) -> dict:                        # the barcode JSON object


def write_barcode(barcode: dict, store_path: Path) -> None:
    """Append-only JSONL to barcodes/<YYYY-MM-DD>.jsonl"""
```

`build_barcode` is **pure** (no I/O), so it is unit-testable against the
validation_test_cases fixtures.

## 3. Storage strategy

Phase A (shadow): one JSONL file per scan day at
`data/barcodes/<YYYY-MM-DD>.jsonl`. One barcode per line.

Phase B (linked): `signal_history.json` rows gain a `barcode_ref`
field: `"barcodes/2026-04-29.jsonl#<line_offset>"`. Allows fast
lookup without flat-scan.

Phase C (consolidated): selected barcode fields promoted into
`signal_history.json` as first-class columns:

- `verdict` (from `rule_match.verdict`)
- `confidence_tier` (from `confidence.tier`)
- `calibrated_wr` (from `confidence.calibrated_wr`)
- `caps_passed` (from `caps.caps_passed`)
- `dominant_rule_id` (from `rule_match.dominant_rule_id`)

The full barcode remains in the JSONL store for audit/replay.

## 4. Performance budget

Target: **< 5 ms per signal** for `build_barcode`, **< 2 ms** for
`write_barcode`. Production scan typically emits < 200 signals/day, so
total barcode overhead < 1.4 s per scan run (negligible vs. screening
time).

Concretely:
- Rule matching is already done upstream (rule engine pass during
  screening); `build_barcode` only formats results.
- Calibrated WR lookup is an O(1) dict access against precomputed
  `calibration.json`.
- JSONL append is buffered.

## 5. Rollout plan

### Phase A — Shadow write (week 1–2)
- Deploy `barcode.py`, write barcodes to JSONL store.
- Telegram + signal_history unchanged.
- Diff barcode contents against expected daily — verify schema,
  no scanner regressions.

### Phase B — Link + Telegram switch (week 3–4)
- `signal_history.json` gains `barcode_ref` field.
- Telegram formatter switched to consume barcode (`verdict_reason`,
  `calibrated_wr`, `caps_passed`).
- Old per-field formatting kept as fallback.

### Phase C — Consolidate (week 5+)
- Promote selected barcode fields into `signal_history.json`.
- Remove now-redundant fields (e.g. `grade`, `bear_bonus`,
  `grade_A` may be derivable from `confidence.tier` + boost rules).
- Keep barcode JSONL as canonical audit log.

### Rollback
Phase A is fully additive — disabling barcode write removes one
function call, no other change. Phase B/C have backward-compatible
flags (`USE_BARCODE_FOR_TELEGRAM=false` etc.).

## 6. Testing

Unit tests live in `tests/scanner/test_barcode.py` and consume
`L3_opus_output/validation_test_cases.json` directly. Each test case
asserts deep equality between `build_barcode(input)` and `expected`.
```

```validation_test_cases.json
{
  "test_cases": [
    {
      "_label": "TC1: Bear UP_TRI hot, sector leading — TAKE_FULL with boost",
      "input": {
        "signal": {
          "id": "2026-04-29-UBL-UP_TRI",
          "symbol": "UBL.NS",
          "signal": "UP_TRI",
          "direction": "LONG",
          "date": "2026-04-29",
          "sector": "Consumer",
          "entry": 1477.2,
          "stop": 1375.27,
          "target_price": 1681.06,
          "atr": 49.73
        },
        "regime_state": {
          "regime": "Bear",
          "sub_regime": "hot",
          "regime_score": -2,
          "vol_q": "Average",
          "breadth_q": "low",
          "week_of_month": 5
        },
        "features": {
          "vol_confirm": true,
          "rs_strong": true,
          "sec_leading": true
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["BU_HOT_BASE", "BU_SEC_LEAD_BOOST"],
        "dominant_rule_id": "BU_HOT_BASE",
        "verdict": "TAKE_FULL",
        "tier": "confident_hot",
        "caps_passed": true,
        "position_size_mult": 1.0
      }
    },
    {
      "_label": "TC2: Bear UP_TRI cold, cascade rule",
      "input": {
        "signal": {
          "id": "2026-04-22-INFY-UP_TRI",
          "symbol": "INFY.NS",
          "signal": "UP_TRI",
          "direction": "LONG",
          "date": "2026-04-22",
          "sector": "IT"
        },
        "regime_state": {
          "regime": "Bear",
          "sub_regime": "cold",
          "regime_score": -4,
          "vol_q": "High",
          "breadth_q": "low",
          "week_of_month": 4
        },
        "features": {
          "vol_confirm": true,
          "rs_strong": true,
          "sec_leading": true
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["BU_COLD_CASCADE"],
        "dominant_rule_id": "BU_COLD_CASCADE",
        "verdict": "TAKE_FULL",
        "tier": "confident_cold",
        "caps_passed": true,
        "position_size_mult": 1.0
      }
    },
    {
      "_label": "TC3: Bull UP_TRI recovery_bull, filter pass",
      "input": {
        "signal": {
          "id": "2026-05-12-RELIANCE-UP_TRI",
          "symbol": "RELIANCE.NS",
          "signal": "UP_TRI",
          "direction": "LONG",
          "date": "2026-05-12",
          "sector": "Energy"
        },
        "regime_state": {
          "regime": "Bull",
          "sub_regime": "recovery_bull",
          "regime_score": 3,
          "vol_q": "Average",
          "breadth_q": "medium",
          "week_of_month": 2
        },
        "features": {
          "vol_confirm": true,
          "rs_strong": true
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["BLU_RECOVERY_FILTER"],
        "dominant_rule_id": "BLU_RECOVERY_FILTER",
        "verdict": "TAKE_FULL",
        "tier": "boundary_hot",
        "caps_passed": true,
        "position_size_mult": 1.0,
        "cell_status": "PROVISIONAL_OFF"
      }
    },
    {
      "_label": "TC4: Bull DOWN_TRI late × wk3 — TAKE_SMALL",
      "input": {
        "signal": {
          "id": "2026-06-17-HDFCBANK-DOWN_TRI",
          "symbol": "HDFCBANK.NS",
          "signal": "DOWN_TRI",
          "direction": "SHORT",
          "date": "2026-06-17",
          "sector": "Financials"
        },
        "regime_state": {
          "regime": "Bull",
          "sub_regime": "late_bull",
          "regime_score": 5,
          "vol_q": "Average",
          "breadth_q": "high",
          "week_of_month": 3
        },
        "features": {
          "vol_confirm": false,
          "rs_strong": false
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["BLD_LATE_WK3"],
        "dominant_rule_id": "BLD_LATE_WK3",
        "verdict": "TAKE_SMALL",
        "tier": "boundary_cold",
        "caps_passed": true,
        "position_size_mult": 0.5
      }
    },
    {
      "_label": "TC5: Choppy BULL_PROXY — REJECT (cell killed)",
      "input": {
        "signal": {
          "id": "2026-03-19-ITC-BULL_PROXY",
          "symbol": "ITC.NS",
          "signal": "BULL_PROXY",
          "direction": "LONG",
          "date": "2026-03-19",
          "sector": "Consumer"
        },
        "regime_state": {
          "regime": "Choppy",
          "sub_regime": "breadth_low",
          "regime_score": 1,
          "vol_q": "Average",
          "breadth_q": "low",
          "week_of_month": 3
        },
        "features": {},
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["CBP_KILL_ALL"],
        "dominant_rule_id": "CBP_KILL_ALL",
        "verdict": "REJECT",
        "tier": "n/a",
        "caps_passed": true,
        "cell_status": "KILL"
      }
    },
    {
      "_label": "TC6: Choppy DOWN_TRI Friday wk2 — SKIP",
      "input": {
        "signal": {
          "id": "2026-05-08-AXISBANK-DOWN_TRI",
          "symbol": "AXISBANK.NS",
          "signal": "DOWN_TRI",
          "direction": "SHORT",
          "date": "2026-05-08",
          "sector": "Financials"
        },
        "regime_state": {
          "regime": "Choppy",
          "sub_regime": "breadth_medium",
          "regime_score": 2,
          "vol_q": "Average",
          "breadth_q": "medium",
          "week_of_month": 2
        },
        "features": {
          "day_of_week": "Friday"
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["CD_FRIDAY_SKIP"],
        "dominant_rule_id": "CD_FRIDAY_SKIP",
        "verdict": "SKIP",
        "tier": "n/a",
        "caps_passed": true
      }
    },
    {
      "_label": "TC7: Sector cap exceeded — downgrade TAKE_FULL → WATCH",
      "input": {
        "signal": {
          "id": "2026-04-30-DABUR-UP_TRI",
          "symbol": "DABUR.NS",
          "signal": "UP_TRI",
          "direction": "LONG",
          "date": "2026-04-30",
          "sector": "Consumer"
        },
        "regime_state": {
          "regime": "Bear",
          "sub_regime": "hot",
          "regime_score": -2,
          "vol_q": "Average",
          "breadth_q": "low",
          "week_of_month": 5
        },
        "features": {
          "vol_confirm": true,
          "rs_strong": true
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OVER"
        }
      },
      "expected": {
        "matched_rule_ids": ["BU_HOT_BASE"],
        "dominant_rule_id": "BU_HOT_BASE",
        "verdict": "WATCH",
        "tier": "confident_hot",
        "caps_passed": false
      }
    },
    {
      "_label": "TC8: Name repeat — SKIP regardless of rule match",
      "input": {
        "signal": {
          "id": "2026-04-30-UBL-UP_TRI",
          "symbol": "UBL.NS",
          "signal": "UP_TRI",
          "direction": "LONG",
          "date": "2026-04-30",
          "sector": "Consumer"
        },
        "regime_state": {
          "regime": "Bear",
          "sub_regime": "hot",
          "regime_score": -2,
          "vol_q": "Average",
          "breadth_q": "low",
          "week_of_month": 5
        },
        "features": {
          "vol_confirm": true,
          "rs_strong": true
        },
        "caps_result": {
          "name_cap_status": "REPEAT",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["BU_HOT_BASE"],
        "dominant_rule_id": "BU_HOT_BASE",
        "verdict": "SKIP",
        "tier": "confident_hot",
        "caps_passed": false
      }
    },
    {
      "_label": "TC9: No rule matched — default WATCH",
      "input": {
        "signal": {
          "id": "2026-08-04-COALINDIA-UP_TRI",
          "symbol": "COALINDIA.NS",
          "signal": "UP_TRI",
          "direction": "LONG",
          "date": "2026-08-04",
          "sector": "Energy"
        },
        "regime_state": {
          "regime": "Bear",
          "sub_regime": "warm",
          "regime_score": -1,
          "vol_q": "Low",
          "breadth_q": "medium",
          "week_of_month": 1
        },
        "features": {
          "vol_confirm": false,
          "rs_strong": false,
          "sec_leading": false
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": [],
        "dominant_rule_id": null,
        "verdict": "WATCH",
        "tier": "n/a",
        "caps_passed": true
      }
    },
    {
      "_label": "TC10: Multiple rules matched — dominant by priority",
      "input": {
        "signal": {
          "id": "2026-07-08-TCS-BULL_PROXY",
          "symbol": "TCS.NS",
          "signal": "BULL_PROXY",
          "direction": "LONG",
          "date": "2026-07-08",
          "sector": "IT"
        },
        "regime_state": {
          "regime": "Bull",
          "sub_regime": "healthy_bull",
          "regime_score": 4,
          "vol_q": "Average",
          "breadth_q": "high",
          "week_of_month": 2
        },
        "features": {
          "vol_confirm": true,
          "rs_strong": true,
          "sec_leading": true,
          "breadth_20d": "high"
        },
        "caps_result": {
          "name_cap_status": "OK",
          "date_cap_status": "OK",
          "sector_concentration_status": "OK"
        }
      },
      "expected": {
        "matched_rule_ids": ["BLP_HEALTHY_20DHIGH", "BLP_SEC_LEAD_BOOST"],
        "dominant_rule_id": "BLP_HEALTHY_20DHIGH",
        "verdict": "TAKE_FULL",
        "tier": "confident_hot",
        "caps_passed": true,
        "position_size_mult": 1.0
      }
    }
  ]
}
```