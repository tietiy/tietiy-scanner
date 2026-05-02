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
