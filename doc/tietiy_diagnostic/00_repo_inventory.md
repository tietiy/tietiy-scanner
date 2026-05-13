# 00 — Repo Inventory

Generated 2026-05-13 during deep diagnostic.

## Top-level layout (`/Users/abhisheklalwani/code/tietiy-scanner/`)

| Path | Role |
|---|---|
| `scanner/` | Production code (44 files at the top level + 5 sub-packages) |
| `scanner/brain/` | Brain layer (8 modules — derive, reason, verify, output, etc.) |
| `scanner/bridge/` | Bridge composer layer (alerts, composers, core, learner, queries, rules, templates) |
| `data/` | `fno_universe.csv`, `mini_scanner_rules.json` |
| `output/` | Live truth state (`signal_history.json`, `bridge_state.json`, `brain/*`, etc.) |
| `output/brain/` | Brain operational outputs (7 JSON views) |
| `output/backups/` | Dated archives 2026-04-24 → 2026-04-28 |
| `output/bridge_state_history/` | Per-day L1/L2/L4 SDR archives |
| `lab/factory/` | Per-regime × per-signal differentiator analyses (bear_*, bull_*) |
| `lab/analyses/` | Investigation runners (inv_001…inv_013, phase1b/2/3/4/5) |
| `scripts/` | Smoke tests, migrations |
| `shadow_ops/` | Read-only inspection scripts |
| `doc/` | 19 canonical docs incl. `session_context.md`, `fix_table.md`, `brain_design_v1.md` |
| `.github/workflows/` | 28 workflow YAMLs (morning_scan, eod_master, brain, brain_digest, etc.) |

## Counts

- 313 Python files (excluding `.venv/`, `.git/`, `.pytest_cache/`)
- 19 markdown docs in `doc/`
- 8 brain modules in `scanner/brain/` (`brain_cli`, `brain_input`, `brain_derive`, `brain_reason`, `brain_verify`, `brain_state`, `brain_output`, `brain_telegram`)
- 7 operational brain outputs in `output/brain/` (`cohort_health`, `regime_watch`, `portfolio_exposure`, `ground_truth_gaps`, `unified_proposals`, `reasoning_log`, `decisions_journal`)
- 28 GitHub Actions workflows
- `output/signal_history.json` = 560 KB (290 records, schema v5, dates 2026-04-01 → 2026-04-29; file mtime 2026-05-04)

## Brain-related files

```
scanner/brain/brain_cli.py
scanner/brain/brain_input.py
scanner/brain/brain_derive.py        (4 derived views generator)
scanner/brain/brain_reason.py        (LLM gates: cohort_promotion_judge, regime_shift_detector, exposure_correlation_analyzer)
scanner/brain/brain_verify.py        (deterministic guards before LLM)
scanner/brain/brain_state.py
scanner/brain/brain_output.py        (writes unified_proposals.json + dual-write to proposed_rules.json)
scanner/brain/brain_telegram.py      (renders digest)
doc/brain_design_v1.md               (canonical design doc)
.github/workflows/brain.yml          (22:00 IST daily fire)
.github/workflows/brain_digest.yml   (22:05 IST daily digest)
output/brain/cohort_health.json      (Wilson-bounded cohort tiers W/M/Candidate)
output/brain/unified_proposals.json  (queued approval items)
output/brain/reasoning_log.json      (LLM rationale audit)
output/brain/regime_watch.json       (current regime + stability)
output/brain/portfolio_exposure.json (open-position concentration warnings)
output/brain/ground_truth_gaps.json
output/brain/decisions_journal.json
```

## Key signal/regime/scoring files (the diagnostic targets)

```
scanner/scanner_core.py     (signal detection — UP_TRI, DOWN_TRI, BULL_PROXY, SA)
scanner/scorer.py           (score + exit-rule + target + position-size)
scanner/mini_scanner.py     (shadow-mode rules + kill_patterns enforcement)
scanner/main.py             (orchestrator, contains get_nifty_info regime classifier at line 257)
scanner/journal.py          (signal_history.json owner)
scanner/outcome_evaluator.py (resolves OPEN signals to terminal outcomes)
data/mini_scanner_rules.json (kill_001 + watch_001 + 7 boost_patterns)
output/regime_debug.json    (daily regime classifier log per RA1)
```
