# L3 Opus Barcode Design — Sonnet 4.5 Critique

**Date:** 2026-05-03

# Production Barcode Format Critique

## 1. Format compactness

**Current design is reasonable but has redundancy.** At ~300 signals/day × 365 days, assuming ~800 bytes per barcode (typical for the sample structure), you're looking at ~88 MB/year uncompressed. The main bloat comes from repeated regime/scanner metadata that's identical across all signals on the same scan day.

**Extract scan-level metadata to a daily header.** Move `regime_state` (except `week_of_month`), `scanner_version`, and `schema_link` into a single header object written once per `<YYYY-MM-DD>.jsonl` file. Each barcode references the header implicitly. This cuts ~120 bytes per barcode. For `symbol`, store the exchange suffix (`.NS`) in the header's market config; barcodes store bare tickers.

**Field-level optimizations are marginal.** The `confidence` block could store `wr_band_low/high` as deltas from `calibrated_wr` (saves ~8 bytes), but at 300 signals/day this is only ~900 bytes. Not worth the readability cost. The current structure is fine for multi-year archives with gzip (which will compress repeated field names aggressively).

## 2. Field naming clarity

**Three ambiguous names need fixing.** `cell_status` conflates rule-set lifecycle state with runtime verdict; rename to `rule_set_status` for clarity. `confidence_label` vs. `tier` is confusing—both describe confidence but from different taxonomies; rename `confidence_label` → `rule_confidence` (source: matched rule metadata). `caps_passed` is a boolean summary, but traders need to know *which* cap fired; rename to `caps_all_clear` and keep the existing `*_status` fields for diagnostics.

**Verdict fields lack trace-back.** `verdict_reason` is a human string, but there's no structured link to *which condition* in the dominant rule triggered the verdict. Add `verdict_condition_id` (e.g., `"BU_HOT_BASE.cond_2"`) so traders can jump directly to the rule JSON clause without parsing prose.

**Execution block terminology is domain-specific.** `trade_mechanism` (e.g., `"bear_relief_continuation"`) is jargon. Add a sibling field `trade_mechanism_label` with plain English: `"Counter-trend bounce in bearish regime"`. Cost: 40 bytes, value: new traders can read archives without a glossary.

## 3. Edge cases that might break

**No matched rules → incomplete barcode.** If `matched_rule_ids = []`, then `dominant_rule_id = null`, `verdict = "REJECT"` (per implicit fallback), but `confidence.tier` has no source rule. The spec says tier can be `"n/a"`, but `calibrated_wr` is required—what value? **Fix:** Add a `verdict_source` field (`"rule"` / `"fallback"` / `"override"`). When `"fallback"`, populate `calibrated_wr` from cell-level historical prior (e.g., base rate for `bear_uptri` across all rules), and set `tier = "n/a"`.

**Multiple rules with conflicting verdicts.** The spec mentions `matched_rule_ids` is 0–N, but only one `dominant_rule_id`. What if `BU_HOT_BASE` says `TAKE_FULL` but `BU_SEC_LEAD_BOOST` says `WATCH`? **Current design implies rule priority is pre-resolved by RuleEngine**, but the barcode doesn't capture *why* one rule dominated. Add `matched_rules_summary`: `[{"id": "BU_HOT_BASE", "verdict": "TAKE_FULL", "priority": 100}, ...]`. Traders can audit conflicts.

**Corrupt sub-regime classification.** If `sub_regime = "hot"` but `regime_score = +3` (bull score), the barcode encodes contradictory state. **Add a validation flag:** `regime_state.validation_status` (`"OK"` / `"WARNING"` / `"INCONSISTENT"`). If incons
