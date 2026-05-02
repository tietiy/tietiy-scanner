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
