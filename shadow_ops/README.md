# shadow_ops/

Forward-time process-validation harness for the audited rule library
(rule_019, rule_031, kill_001). Implements consultant Round 10 framework.

shadow_ops produces a deterministic, append-only audit trail of every
classification, signal, fill, and outcome, comparable bit-for-bit to the
audit pipeline's `enriched_signals.parquet` for any historical signal.

The cohort-level question shadow_ops answers: *do the audited rules
(rule_019: 71% expected_wr, etc.) actually produce the calibrated outcomes
when applied forward day-by-day on fresh data?*

## Architecture

See `doc/shadow_ops_v1_architecture.md` for the full specification (16
sections). The README is operator-facing; the arch doc is the design
reference.

## Module map

| Module | Purpose |
| --- | --- |
| `data_ingest.py` | Daily yfinance refresh of 188-symbol OHLC + Nifty index parquets in `lab/cache/`. |
| `regime_classifier.py` | Computes `regime` (slope/EMA50 mirror of scanner) + `sub_regime` (via canonical `add_derived_features`). |
| `schemas.py` | 5 event dataclasses: `ScanEvent`, `CandidateSignal`, `TradeCard`, `LifecycleEvent`, `FillSimulation`. |
| `journal.py` | Append-only JSONL writer + reader with `event_id` uniqueness, atomic appends, checksum sidecars. |
| `daily_scan.py` | Per-day scan orchestrator: detect signals, match active rules, emit candidates + trade cards + scan event. |
| `lifecycle.py` | Day-by-day evaluator. Audit-faithful T+1 OPEN entry, no gap-fill, 6-day inclusive D1-D6 hold. |
| `read_model.py` | Regenerates `trade_cards_current.jsonl` (derived view) from the immutable event log. |
| `daily_report.py` | Operator's daily markdown digest written to `<run_dir>/reports/<eval_date>.md`. |
| `alerts.py` | Structured alert emission (CRITICAL/WARNING/INFO) + acknowledgment sidecar. |
| `pre_scan_check.py` | 8 preconditions verified before each daily scan. Blocks on failure. |
| `end_of_shadow.py` | Campaign-level review markdown at `<run_dir>/review.md`. |
| `bootstrap.py` | Initialize a fresh campaign — writes `run_config.json` + emits BOOTSTRAP_COMPLETE alert. |

## Daily operator workflow

```bash
# Bootstrap once at campaign start:
python -m shadow_ops.bootstrap \
    --run-dir /path/to/campaign \
    --campaign-id "shadow_2026Q2" \
    --start-date 2026-05-06 \
    --operator <name> \
    --notes "first 30-day shadow"

# Daily, per trading day:
python -m shadow_ops.pre_scan_check --run-dir /path/to/campaign && \
python -m shadow_ops.daily_scan      --run-dir /path/to/campaign && \
python -m shadow_ops.lifecycle       --run-dir /path/to/campaign && \
python -m shadow_ops.daily_report    --run-dir /path/to/campaign

# At campaign end:
python -m shadow_ops.end_of_shadow   --run-dir /path/to/campaign
```

The `&&` chain ensures any failure halts subsequent steps. `pre_scan_check`
exits non-zero on any precondition violation (rules drift, stale cache,
unacknowledged CRITICAL alerts, etc.).

## Campaign lifecycle

1. **Bootstrap** (`shadow_ops.bootstrap`): one-time. Creates `run_dir`, writes
   `run_config.json` freezing rules SHA + git SHA + audit-faithful constants.
   Refuses if `run_dir` already has a config or events. See arch doc §3.5.

2. **Daily operation** (30+ trading days, per consultant Round 10): operator
   runs the 4-command chain above each trading day. Cards proposed today get
   evaluated through their D1-D6 lifecycle on subsequent days.

3. **Termination** (`shadow_ops.end_of_shadow`): operator generates the
   campaign-level review at any point (typically after ~30 days). Review
   surfaces decision-support flags: trading days observed, cards observed,
   WR delta from audit, unacknowledged CRITICAL alerts. Operator decides
   deploy / extend / abort.

## File layout (run_dir contents)

```
<run_dir>/
├── run_config.json                    # frozen at bootstrap; never modified
├── run_config.json.tmp                # transient — ignore
├── alerts.jsonl                       # append-only operational alerts
├── alerts_acknowledgments.jsonl       # ack sidecar for CRITICAL alerts
├── scan_events.jsonl                  # one per daily scan
├── scan_events.jsonl.checksum         # tamper-evidence sidecar
├── candidate_signals.jsonl            # one per signal matching any active rule
├── candidate_signals.jsonl.checksum
├── trade_cards.jsonl                  # PROPOSED snapshots only (append-only)
├── trade_cards.jsonl.checksum
├── lifecycle_events.jsonl             # state transitions (PROPOSED→ACTIVE→...)
├── lifecycle_events.jsonl.checksum
├── fill_simulations.jsonl             # ENTRY / STOP / TARGET / EXPIRY fills
├── fill_simulations.jsonl.checksum
├── trade_cards_current.jsonl          # DERIVED view (regenerated from events)
├── trade_cards_current.jsonl.checksum
├── reports/
│   └── <eval_date>.md                 # daily reports, one per scan day
├── review.md                          # end-of-shadow campaign review
└── review.md.checksum
```

The `.jsonl` event log files are the source of truth and are append-only.
`trade_cards_current.jsonl` and `review.md` are derived views — operator
should never edit them directly. Re-run `read_model` or `end_of_shadow` to
regenerate.

## Troubleshooting (alert types)

When `pre_scan_check` blocks or `daily_scan` reports issues, alerts are
written to `<run_dir>/alerts.jsonl`. Common types:

| Alert type | Severity | Operator action |
| --- | --- | --- |
| `BOOTSTRAP_COMPLETE` | INFO | none — ambient marker for campaign start |
| `DATA_INGEST_PARTIAL` | WARNING | inspect `failed_symbols` context; rerun `data_ingest` if transient |
| `DATA_INGEST_FAILURE` | CRITICAL | major failure (e.g., index update failed); investigate before next scan |
| `DATA_INGEST_STALE` | WARNING | parquet older than expected; rerun `data_ingest` |
| `REGIME_CLASSIFIER_ERROR` | CRITICAL | classification raised; check Nifty parquet integrity, then ack |
| `SCAN_PARTIAL` | WARNING | some symbols skipped; review `symbols_skipped` |
| `SCAN_ERROR` | CRITICAL | scan halted; investigate, then ack |
| `KILL_001_CLUSTER` | WARNING | ≥2 kill_001 suppressions (sectoral distress diagnostic — informational) |
| `LIFECYCLE_ERROR` | WARNING | per-card error during lifecycle eval; check context |
| `LIFECYCLE_DAY_GAP` | WARNING | operator missed lifecycle days — backfill the missing eval_dates first |
| `CHECKSUM_MISMATCH` | CRITICAL | journal file's sidecar SHA mismatched (tamper-evidence) |
| `PARQUET_SHA_DRIFT` | WARNING | a fill's recorded parquet SHA doesn't match current file (data revision) |
| `PRE_SCAN_CHECK_FAILURE` | CRITICAL | one or more preconditions failed; fix and re-run |
| `PRE_SCAN_CHECK_BYPASSED` | WARNING | `--force` used; ambient marker |

To acknowledge a CRITICAL alert (so `pre_scan_check` unblocks):

```bash
python -m shadow_ops.alerts ack \
    --run-dir /path/to/campaign \
    --alert-id alert_2026-05-06_001 \
    --reason "investigated, transient yfinance hiccup, retried" \
    --by abhishek
```

## Audit-faithful contract

shadow_ops mirrors the canonical lab simulator
(`lab/infrastructure/signal_replayer.py:compute_d6_outcome`) bit-for-bit:

- **Entry**: T+1 OPEN unconditional. No breakout confirmation, no T+2/T+3
  fallback, no NO_FILL state in v1.
- **Hold window**: 6 trading days inclusive (D1 entry-with-intraday-check
  through D6 exit-at-OPEN).
- **Stop / target**: exits at literal stop / target price. **No gap-fill**
  in v1 — gap-throughs exit at the limit, not the gap-down/up open.
- **Same-day stop+target**: STOP wins (conservative; matches canonical loop
  order).
- **PnL anchored to PROPOSED entry** (not actual D1 fill), rounded to 2
  decimals at storage. W/L/F classification (DAY6_WIN/LOSS/FLAT) uses
  unrounded pnl with ±0.5% threshold.
- **2R target**: `target = entry + 2.0 * (entry - stop)` for LONG.

The audit's calibrated WRs (rule_019 71%, rule_031 68%, kill_001 45%) were
computed under these exact mechanics. Any divergence breaks audit-WR
comparability — out of v1 scope.

## See also

- `doc/shadow_ops_v1_architecture.md` — design specification
- `doc/consultant_briefings/round_10_rule031_supplement.pdf` — Round 10
  framework that motivated shadow_ops
- `lab/factory/step5_finalization/L4_opus_output/unified_rules_v4_1_FINAL.json` — rule library
- `lab/infrastructure/signal_replayer.py:compute_d6_outcome` — canonical simulator that shadow mirrors
