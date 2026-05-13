# TIE TIY — Master Project Inventory

**Generated:** 2026-05-13 (read-only inventory)
**Working directory:** `/Users/abhisheklalwani/code/tietiy-scanner`
**Disk footprint:** repo 645 MB · .git 116 MB · lab/ 31 MB · output/ 14 MB · Claude project memory 70 MB

This file is an exhaustive inventory only — no interpretation, no recommendations.

---

## Section 1 — Repository State Snapshot

### 1.1 Branch info
- **Active branch:** `main`
- **HEAD:** `ac6ae254 Stop check 05:12 IST`
- **Tracking:** `origin/main` (in sync — same SHA)
- **Local branches present (6):**

| Branch | HEAD | Tracking | Total commits | Last commit |
|---|---|---|---|---|
| `main` (current) | `ac6ae254` | `origin/main` (sync) | 5,781 | 2026-05-13 05:12 UTC — "Stop check 05:12 IST" |
| `backtest-lab` | `23d6d8fe` | `origin/backtest-lab` ahead 9 | 4,135 | 2026-05-05 00:57 IST — "Phase 3.6: embargo_sensitivity audit on rule_019 …" |
| `rule_031_audit` | `c87d70a8` | (no tracking) | 4,143 | 2026-05-05 03:10 IST — "rule_031 Audit 7: drift_vs_rule_019 …" |
| `shadow_ops_v1` | `64efa9f4` | `origin/shadow_ops_v1` (sync) | 4,149 | 2026-05-05 19:43 IST — "shadow_ops Step 11: bootstrap + README + architecture doc consolidation" |
| `v2-integration` | `c913ebcd` | (no tracking) | 4,328 | 2026-05-04 02:01 IST — "Phase 2: integrate V2 code pack on v2-integration branch" |
| `vp-leakage-fix` | `ae519fb6` | (no tracking) | 4,137 | 2026-05-05 03:29 IST — "doc: version-control consultant briefings (Round 9 + Round 10)" |

### 1.2 Working tree state
- **Modified (tracked):** none
- **Staged:** none
- **Untracked dirs (4):** `doc/plan_review/`, `doc/tietiy_2_0_design/`, `doc/tietiy_mindmap/`, `lab/`
- **Untracked files in those dirs:**
  - `doc/plan_review/ADVERSARIAL_REVIEW.md` (32 KB, 433 lines)
  - `doc/tietiy_2_0_design/` — 8 files (01-07 + MASTER_DESIGN), 108 KB total
  - `doc/tietiy_mindmap/` — 11 files (01-10 + MASTER_MINDMAP), 220 KB total
  - `lab/cache/*.parquet` — 197 stock parquet caches (~30 MB)
  - `lab/logs/*.log` — 11 investigation run logs (~260 total lines)
  - `lab/cache/llm/cost_log.jsonl` (also subject of stash@{1})

### 1.3 Stash list (2)

| Stash | On branch | Message | Files | Lines |
|---|---|---|---|---|
| `stash@{0}` | shadow_ops_v1 | "CC diagnostic outputs" | **29 markdown files** | +3,646 |
| `stash@{1}` | backtest-lab | "phase2-prep: dirty files preserved for later sort" | 1 file: `lab/cache/llm/cost_log.jsonl` | +20 |

**Stash@{0} contents (the previously-presumed-missing docs):**
- `doc/tietiy_2_0_feasibility/` — 9 files: `01_portable_modules`, `02_shadow_ops_relationship`, `03_plug_and_play_design`, `04_v5_gate_architecture`, `05_brain_dashboard_wiring`, `06_self_learning_scope`, `07_bull_setup_validation_framework`, `08_risk_inventory_and_effort`, `MASTER_FEASIBILITY`
- `doc/tietiy_diagnostic/` — 9 files: `00_repo_inventory`, `01_canonical_state`, `02_down_tri_mechanics`, `03_down_tri_subpopulations`, `04_regime_detector_mechanics`, `05_regime_detector_test`, `06_brain_layer_state`, `07_stop_target_mechanics`, `MASTER_FINDINGS`
- `doc/tietiy_diagnostic_round2/` — 11 files: `08_pattern_miner_analysis`, `09_auto_analyst_analysis`, `10_chain_validator_analysis`, `11_weekly_intelligence_reports`, `12_watch_matcher_phase1`, `13_thresholds_buckets`, `14_branches_and_wip`, `15_output_directory_audit`, `16_mini_scanner_rules_audit`, `17_zone_readiness`, `MASTER_FINDINGS_R2`

---

## Section 2 — Branch Comparison

### 2.1 Overall branch divergence

| Branch | Commits unique to branch | Commits in main but not in branch | Last touched |
|---|---|---|---|
| `main` | — | — | 2026-05-13 (live) |
| `shadow_ops_v1` | **220** | 1,852 | 2026-05-05 (8 days idle) |
| `backtest-lab` | **206** | 1,852 | 2026-05-05 (8 days idle) |
| `rule_031_audit` | **214** | 1,852 | 2026-05-05 (8 days idle) |
| `vp-leakage-fix` | **208** | 1,852 | 2026-05-05 (8 days idle) |
| `v2-integration` | **1** | 1,454 | 2026-05-04 (9 days idle) |

### 2.2 File-level differences (count of files unique to each branch vs main)

| Branch | Files-on-branch-not-main | Pattern |
|---|---|---|
| `shadow_ops_v1` | **1,334 files** | shadow_ops/ (~13 modules + tests), full lab/ tree (1,300+ cache+investigation files), consultant_briefings PDFs, updated doc/tiy.md, doc/shadow_ops_v1_architecture.md (1,406 LOC) |
| `backtest-lab` | **1,272 files** | full lab/ tree + LLM cache JSONs |
| `rule_031_audit` | **1,316 files** | full lab/ tree + rule_031-specific audit findings |
| `vp-leakage-fix` | **1,305 files** | full lab/ tree + consultant_briefings PDFs (Round 9 + Round 10) |
| `v2-integration` | **126 files** | dqf_validation workflow, config/{dqf,regime_v2,rule_registry}, doc/{DEPLOYMENT_CHECKLIST, PATCH_NOTES_V2, black_swan_protocol}, lab/deployment_validator/, output/brain/history/2026-05-04→06, output/backups for May 4/11/12 |

### 2.3 Files that exist ONLY on shadow_ops_v1 (key items)

- `doc/consultant_briefings/README.md`
- `doc/consultant_briefings/round_09_phase3_vp_fix.pdf`
- `doc/consultant_briefings/round_10_rule031_supplement.pdf`
- `doc/shadow_ops_v1_architecture.md`
- `doc/tiy.md` (newer than main version)
- `shadow_ops/` tree:
  - `bootstrap.py`, `daily_scan.py`, `lifecycle.py`, `regime_classifier.py`, `journal.py`, `schemas.py`, `read_model.py`, `daily_report.py`, `alerts.py`, `pre_scan_check.py`, `end_of_shadow.py`, `data_ingest.py`
  - `shadow_ops/tests/` — 13 test files
- `lab/` tree (shared with other branches):
  - Top-level: `AUTO_RUN_STATUS.md`, `COMBINATION_ENGINE_FEATURE_SPEC.md`, `COMBINATION_ENGINE_PLAN.md`, `DECISIONS_LOG.md`, `FINDINGS_LOG.md`, `LAB_PIPELINE_COMPLETE.md`, `PROMOTION_PROTOCOL.md`, `README.md`, `ROADMAP.md`
  - `lab/analyses/` — 11 investigation findings (INV-001 to INV-013), 5 Phase docs (PHASE-01 to PHASE-05), 18 runner scripts, ANALYZER_findings
  - `lab/cache/llm/` — 1,300+ LLM response JSON cache files
  - `lab/infrastructure/` — feature extractor / signal replayer
  - `lab/factory/` — 14 cohort subdirectories (bear, bull, choppy × signal types + opus_iteration/synthesis + production_backtest + oos_validation)

### 2.4 Files unique to v2-integration

- Workflow: `.github/workflows/dqf_validation.yml`
- Config: `config/dqf_config.yaml`, `config/regime_config_v2.yaml`, `config/rule_registry.json`
- Docs: `doc/DEPLOYMENT_CHECKLIST.md`, `doc/PATCH_NOTES_V2.md`, `doc/black_swan_protocol.md`
- Code: `lab/deployment_validator/deployment_validator.py`, `harness_audit.py`, `run_dqf.py`
- Brain history: 2026-05-04, 05, 06 snapshots
- Output backups: signal_history + signal_archive for 2026-04-25/27/28, 2026-05-02/11/12

---

## Section 3 — All Documentation Inventory

### 3.1 doc/ subdirectories (current branch = main)

| Path | Files | Total size | Last modified | Git status |
|---|---|---|---|---|
| `doc/plan_review/` | 1 | 32 KB | 2026-05-13 16:18 | UNTRACKED (created today) |
| `doc/project_inventory/` | 0 + this file | (this file) | 2026-05-13 (now) | UNTRACKED |
| `doc/tietiy_2_0_design/` | 8 | 108 KB | (created in prior CC session) | UNTRACKED |
| `doc/tietiy_mindmap/` | 11 | 220 KB | 2026-05-13 11:07-11:19 | UNTRACKED (created today AM) |

### 3.2 doc/ top-level files (committed)

| File | Size | Last modified |
|---|---|---|
| `doc/brain_design_v1.md` | 42,859 B | 2026-04-29 02:54 |
| `doc/bridge_design_v1.md` | 61,002 B | 2026-04-28 19:23 |
| `doc/daily_checkin_template.md` | 210 B | 2026-04-25 |
| `doc/engineering_dock.md` | 16,199 B | 2026-04-25 |
| `doc/fix_table.md` | 51,880 B | 2026-04-28 22:29 |
| `doc/master_audit_2026-04-27.md` | 71,754 B | 2026-04-28 22:29 |
| `doc/pre_wave5_resume_build_table_v1.md` | 24,414 B | 2026-04-28 22:48 |
| `doc/project_anchor_v1.md` | 71,033 B | 2026-04-28 22:09 |
| `doc/reconciliation_ritual.md` | 4,657 B | 2026-04-25 |
| `doc/regression_log.md` | 161 B | 2026-04-25 |
| `doc/roadmap.md` | 2,560 B | 2026-04-25 |
| `doc/session_context.md` | 24,428 B | 2026-04-29 10:50 |
| `doc/tiy.md` | 13,417 B | 2026-05-13 01:34 |
| `doc/wave_execution_log_2026-04-23` | 7,313 B | 2026-04-25 |
| `doc/wave2_migration_log_20260423_021333.md` | 3,995 B | 2026-04-25 |
| `doc/wave5_m08_log_20260423_024400.md` | 1,014 B | 2026-04-25 |
| `doc/wave5_prerequisites_2026-04-27.md` | 12,847 B | 2026-04-28 23:54 |

### 3.3 Docs that exist on shadow_ops_v1 but not main

- `doc/consultant_briefings/README.md`
- `doc/consultant_briefings/round_09_phase3_vp_fix.pdf`
- `doc/consultant_briefings/round_10_rule031_supplement.pdf`
- `doc/shadow_ops_v1_architecture.md`

### 3.4 Docs that exist on v2-integration but not main

- `doc/DEPLOYMENT_CHECKLIST.md`
- `doc/PATCH_NOTES_V2.md`
- `doc/black_swan_protocol.md`

### 3.5 Docs only in stash@{0} (never committed to any branch)

- `doc/tietiy_2_0_feasibility/` — 9 files (~2,500 lines)
- `doc/tietiy_diagnostic/` — 9 files (~1,050 lines)
- `doc/tietiy_diagnostic_round2/` — 11 files (~1,100 lines)

---

## Section 4 — Orphan References

### 4.1 The 4 docs the adversarial review flagged as missing

| Doc directory | Found on main? | Found on any branch? | Found in any stash? | Status |
|---|---|---|---|---|
| `doc/tietiy_diagnostic/` | NO | NO | **YES — stash@{0}** | Saved as stash on shadow_ops_v1 only |
| `doc/tietiy_diagnostic_round2/` | NO | NO | **YES — stash@{0}** | Same stash |
| `doc/tietiy_2_0_feasibility/` | NO | NO | **YES — stash@{0}** | Same stash |
| `doc/tietiy_2_0_design/` | UNTRACKED on main | NO | NO | Files exist in working tree, never committed |

### 4.2 L99 research outputs — where are they?

| Item | Location | Size | Date |
|---|---|---|---|
| TIE_TIY_Swing_Scanner_Full_Blueprint.pdf | `~/Downloads/` | 30 KB, 20 pages | 2026-05-04 03:43 |
| TIETIY_Rule031_Audit_Supplement.pdf | `~/Downloads/` | 15 KB, 6 pages | 2026-05-05 03:14 |
| round_09_phase3_vp_fix.pdf | shadow_ops_v1 + vp-leakage-fix branches at `doc/consultant_briefings/` | — | (on branch only) |
| round_10_rule031_supplement.pdf | shadow_ops_v1 + vp-leakage-fix branches at `doc/consultant_briefings/` | — | (on branch only) |

**No L99 outputs as markdown in any repo location.** All L99 deliverables are PDFs only; none have been transcribed into the repo.

### 4.3 Scripts referenced by workflows — all present

Grep over `.github/workflows/*.yml` for `python … scanner/` references → all referenced scripts exist on disk in `scanner/` (verified per-file). The grep tool's `sed` conversion produced false-positive "MISSING" output (it transformed `.py` to `/py`); actual file checks confirm all exist.

### 4.4 References in CLAUDE.md

All identifiers in CLAUDE.md (`bridge_state.json`, `bridge_telegram_eod.py`, `bridge.py`, `eod_master.yml`, `eod.py`, `fix_table.md`, `outcome_evaluator.py`, `postopen.py`, `postopen.yml`, `premarket.py`, `proposed_rules.json`, `roadmap.md`, `session_context.md`, `signal_history.json`, `telegram_bot.py`) → all exist.

### 4.5 References in MASTER_MINDMAP.md to scanner/ files

Cross-checked all `scanner/...` paths — every one exists on disk.

### 4.6 Things existing that aren't referenced anywhere obvious

- `scripts/_run_smoke_brain_*.py` — 5 smoke test runners (28-29 April timestamps) — referenced only by themselves, not by any workflow.
- `scripts/wave2_migration.py`, `wave5_m08_migration.py` — one-shot migrations, retained.
- `scripts/test_anthropic_api.py` — ad-hoc API sanity check.
- `scripts/analyze_full.py` — full analysis script (27 April).
- `quarantine/backup_20260411_053552/`, `quarantine/wave2_20260423_021333/`, `quarantine/wave5_20260423_024400/` — three preserved backup folders, not referenced.
- `backups/2026-04-18-pre-phase2/` — pre-phase2 snapshot folder.
- `backups/signal_history.2026-04-17-*.json` — 4 pre-rejection-migration snapshots.
- `output/analysis/` — 5 JS bundles (overview/signals/segmentation/post_mortem/advanced) — referenced by `analysis.html` only.
- `eod_update.yml.bak` — disabled workflow.

---

## Section 5 — Lab and Experimental Work

### 5.1 lab/ (currently untracked on main; tracked on backtest-lab/shadow_ops_v1/etc.)

**Size:** 31 MB (~30 MB is cache)

| Subdirectory | Contents | Status on main |
|---|---|---|
| `lab/cache/` | 197 stock parquets (15-year OHLCV) | untracked |
| `lab/cache/llm/` | LLM response cache (count: 0 on main; ~1,300 on backtest-lab) | untracked / branch-only |
| `lab/logs/` | 11 investigation run logs | untracked |
| `lab/analyses/` | INV-001 to INV-013 findings + 5 Phase docs + 18 runner scripts | branch-only |
| `lab/factory/` | 14 cohort subdirectories | branch-only |
| `lab/infrastructure/` | feature extractor, signal replayer | branch-only |
| `lab/deployment_validator/` | only on v2-integration | branch-only |

### 5.2 lab/factory/ subdirectory file counts (per shadow_ops_v1)

| Subdir | Files |
|---|---|
| `bear/` | 0 |
| `bear_bullproxy/` | 2 |
| `bear_downtri/` | 2 |
| `bear_uptri/` | 5 |
| `bull/` | 0 |
| `bull_bullproxy/` | 2 |
| `bull_downtri/` | 2 |
| `choppy/` | 0 |
| `choppy_bullproxy/` | 3 |
| `choppy_uptri/` | 7 |
| `oos_validation/` | 2 |
| `opus_iteration/` | 1 |
| `opus_synthesis/` | 1 |
| `production_backtest/` | 1 |

### 5.3 lab/analyses key files

- `ANALYZER_findings.md`
- `INV-001_findings.md` through `INV-013_findings.md` (8 of 13 numbers in use: 001, 002, 003, 006, 007, 010, 012, 013)
- `PHASE-01_feature_extraction.md` … `PHASE-05_live_validation.md`
- Runner scripts per investigation (`inv_001_runner.py`, etc.)

### 5.4 lab/ top-level documents (shadow_ops_v1)

- `AUTO_RUN_STATUS.md`
- `COMBINATION_ENGINE_FEATURE_SPEC.md`
- `COMBINATION_ENGINE_PLAN.md`
- `DECISIONS_LOG.md`
- `FINDINGS_LOG.md`
- `LAB_PIPELINE_COMPLETE.md`
- `PROMOTION_PROTOCOL.md`
- `README.md`
- `ROADMAP.md`

### 5.5 shadow_ops/ on main vs shadow_ops_v1

- **main:** `shadow_ops/` directory contains only `tests/` subdir + `__pycache__/`. No production modules.
- **shadow_ops_v1:** Full implementation — 13 modules in `shadow_ops/`, 13 test files in `shadow_ops/tests/`, plus `doc/shadow_ops_v1_architecture.md`.

### 5.6 Other experimental dirs

- `quarantine/` — three preserved old snapshots (backup_20260411, wave2_20260423, wave5_20260423)
- `src/tietiy/` — empty (only `__pycache__/`), placeholder for future packaging
- `tests/` — top-level pytest tree, currently empty visible content (only `__pycache__/`)
- `shadow_ops/tests/` on main — exists but only `__pycache__/`

---

## Section 6 — Forgotten or Cached Work

### 6.1 ~/.claude project memory for tietiy-scanner

Path: `/Users/abhisheklalwani/.claude/projects/-Users-abhisheklalwani-code-tietiy-scanner/`
**Size: 70 MB**

| Item | Size | Date | Note |
|---|---|---|---|
| `2461e34b-…6f0c578c8268.jsonl` | **1.57 MB** | 2026-05-13 17:03 (now) | Today's CC session (this conversation) |
| `91a4e01d-…1611319f75.jsonl` | **69.2 MB** | 2026-05-05 20:54 | Previous mega-session (May 5 — likely the 36-hour planning) |
| `2461e34b-…6f0c578c8268/` (dir) | small | 2026-05-13 10:55 | Session state dir |
| `91a4e01d-…1611319f75/` (dir) | small | 2026-04-26 10:38 | Older session state |

**Other Claude project directories present:**
- `~/.claude/projects/-Users-abhisheklalwani-code-foundation-backtest/` — 16 MB
- `~/.claude/projects/-Users-abhisheklalwani-code-tradingview-mcp/` — 40 KB
- `~/.claude/projects/-Users-abhisheklalwani/` — 4 KB

### 6.2 ~/.claude global areas (project-agnostic but may contain tietiy refs)

| Path | Contents | Last modified |
|---|---|---|
| `~/.claude/paste-cache/` | **482 files**, 3.4 MB | actively updated |
| `~/.claude/plans/modular-tumbling-honey.md` | 3,635 B | 2026-04-27 20:59 |
| `~/.claude/tasks/` | 3 task dirs (2461e34b, 8f2abc68, 91a4e01d) | up to 2026-05-13 11:20 |
| `~/.claude/sessions/15241.json` | 299 B | 2026-05-13 17:03 |
| `~/.claude/sessions/2908.json` | 331 B | 2026-05-05 19:46 |
| `~/.claude/history.jsonl` | 216 KB | 2026-05-13 17:00 |
| `~/.claude/file-history/` | 3 session-keyed subdirs with versioned snapshots (`*@v2`) | active |
| `~/.claude/stats-cache.json` | 1.3 KB | 2026-05-13 |
| `~/.claude/backups/` | exists | 2026-05-13 16:43 |
| `~/.claude/downloads/` | exists, empty-ish | 2026-05-07 00:24 |

### 6.3 /private/tmp/claude-501 session dir
- `/private/tmp/claude-501/-Users-abhisheklalwani-code-tietiy-scanner/2461e34b-ab66-4328-8da5-6f0c578c8268/` exists (today's session temp area)

### 6.4 ~/Downloads tietiy artifacts
- `TIE_TIY_Swing_Scanner_Full_Blueprint.pdf` — 30 KB, 20 pages, 2026-05-04 03:43
- `TIETIY_Rule031_Audit_Supplement.pdf` — 15 KB, 6 pages, 2026-05-05 03:14
- (No other matches across Documents/Desktop)

### 6.5 /tmp scan
- No tietiy-related files in `/tmp/`
- `/private/tmp/claude-501` has session dir as noted above

### 6.6 Hidden / cache dirs
- `~/.anthropic` — not present
- `~/.claude-cache` — not present
- `~/Library/Application Support/Claude` — search results truncated; not separately enumerated here
- Repo `.claude/settings.local.json` — present (no permissions readable in this scan)

### 6.7 Backup / archive files in repo
- `output/backups/signal_history.<date>.json` — 7 snapshots (2026-05-06 → 2026-05-12)
- `output/backups/signal_archive.<date>.json` — 6 snapshots (each 42 B placeholder)
- `backups/2026-04-18-pre-phase2/` — folder
- `backups/signal_history.2026-04-17-*.json` — 4 historical snapshots from rejection-migration day
- `output/signal_history.backup.json` — per-mutation rolling backup (per journal.py)
- `quarantine/backup_20260411_053552/`, `quarantine/wave2_20260423_021333/`, `quarantine/wave5_20260423_024400/` — three preserved snapshots
- `.github/workflows/eod_update.yml.bak` — disabled workflow

### 6.8 .draft / .wip / .old files in working tree
- None found.

---

## Section 7 — Recent Commit Pattern Analysis

### 7.1 Last 30 commits on main (counts by category)

| Category | Count |
|---|---|
| Automated `LTP update HH:MM IST` (bot) | 14 |
| Automated `Stop check HH:MM IST` (bot) | 15 |
| Automated `Bridge postopen YYYY-MM-DD HH:MM IST` (bot) | 1 |
| Manual feature / fix / chore commits | **0** |

All 30 recent commits on main are author `TIE TIY Bot`, all bot-driven, all within 2026-05-13 04:02-05:12 UTC (09:32-10:42 IST). No human commits in this window.

### 7.2 Last meaningful (non-bot) commit on main
Need to scan deeper — none of last 30 are human-authored. The user's adversarial-review context mentioned the local was 1,397 commits behind origin/main before this morning's pull, suggesting the operator-side commits live elsewhere or were pulled in bulk.

### 7.3 Branch commit cadence
- Each feature branch (`shadow_ops_v1`, `backtest-lab`, `rule_031_audit`, `vp-leakage-fix`) last touched **2026-05-05**, 8 days ago. All four idle.
- `v2-integration` last touched **2026-05-04**, 9 days ago.

### 7.4 Authorship signal
- Bot author on main: `TIE TIY Bot`
- Manual branches authored by user (commits not enumerated here).

---

## Section 8 — Summary Table (Everything in one view)

| Item | Location | Status | Last touched | Notes |
|------|----------|--------|--------------|-------|
| **— BRANCHES —** | | | | |
| `main` | git | tracked, active, sync with origin | 2026-05-13 (bot commits ongoing) | 5,781 total commits |
| `shadow_ops_v1` | git | sync with origin/shadow_ops_v1; 220 unique commits | 2026-05-05 19:43 | 1,334 files unique vs main |
| `backtest-lab` | git | ahead 9 of origin; 206 unique | 2026-05-05 00:57 | 1,272 files unique vs main |
| `rule_031_audit` | git local-only | 214 unique | 2026-05-05 03:10 | 1,316 files unique vs main |
| `vp-leakage-fix` | git local-only | 208 unique | 2026-05-05 03:29 | 1,305 files unique vs main; has consultant_briefings PDFs |
| `v2-integration` | git local-only | 1 unique | 2026-05-04 02:01 | 126 files unique vs main; has dqf_validation workflow + V2 patch notes |
| **— STASHES —** | | | | |
| `stash@{0}` "CC diagnostic outputs" | git stash on shadow_ops_v1 | UNCOMMITTED | (created prior, persisted) | **29 markdown files = 3,646 lines** — the missing diagnostic docs |
| `stash@{1}` "phase2-prep dirty files" | git stash on backtest-lab | UNCOMMITTED | (created prior) | LLM cost log update (+20 lines) |
| **— UNTRACKED ON MAIN —** | | | | |
| `doc/tietiy_mindmap/` | working tree | UNTRACKED | 2026-05-13 11:19 | 11 files, 220 KB (this morning's mindmap session) |
| `doc/tietiy_2_0_design/` | working tree | UNTRACKED | (prior CC session) | 8 files, 108 KB |
| `doc/plan_review/ADVERSARIAL_REVIEW.md` | working tree | UNTRACKED | 2026-05-13 16:18 | 32 KB, 433 lines |
| `doc/project_inventory/MASTER_INVENTORY.md` | working tree | UNTRACKED | 2026-05-13 (this file) | (this file) |
| `lab/cache/*.parquet` | working tree | UNTRACKED | varies | 197 stock parquets (~30 MB) |
| `lab/logs/*.log` | working tree | UNTRACKED | varies | 11 investigation logs |
| `lab/cache/llm/cost_log.jsonl` | working tree | UNTRACKED (also in stash@{1}) | varies | LLM cost log |
| **— DOC TOP-LEVEL (TRACKED) —** | | | | |
| `doc/brain_design_v1.md` | tracked main | committed | 2026-04-29 02:54 | 43 KB |
| `doc/bridge_design_v1.md` | tracked main | committed | 2026-04-28 19:23 | 61 KB |
| `doc/master_audit_2026-04-27.md` | tracked main | committed | 2026-04-28 22:29 | 72 KB |
| `doc/project_anchor_v1.md` | tracked main | committed | 2026-04-28 22:09 | 71 KB |
| `doc/fix_table.md` | tracked main | committed | 2026-04-28 22:29 | 52 KB |
| `doc/session_context.md` | tracked main | committed | 2026-04-29 10:50 | 24 KB |
| `doc/tiy.md` | tracked main | committed | 2026-05-13 01:34 | 13 KB (NB: newer version on shadow_ops_v1) |
| `doc/pre_wave5_resume_build_table_v1.md` | tracked main | committed | 2026-04-28 22:48 | 24 KB |
| `doc/wave5_prerequisites_2026-04-27.md` | tracked main | committed | 2026-04-28 23:54 | 13 KB |
| `doc/wave2_migration_log_…md` | tracked main | committed | 2026-04-25 | 4 KB |
| `doc/wave5_m08_log_…md` | tracked main | committed | 2026-04-25 | 1 KB |
| `doc/wave_execution_log_2026-04-23` | tracked main | committed | 2026-04-25 | 7 KB |
| `doc/engineering_dock.md` | tracked main | committed | 2026-04-25 | 16 KB |
| `doc/reconciliation_ritual.md` | tracked main | committed | 2026-04-25 | 5 KB |
| `doc/roadmap.md` | tracked main | committed | 2026-04-25 | 3 KB |
| `doc/regression_log.md` | tracked main | committed | 2026-04-25 | 161 B (essentially empty) |
| `doc/daily_checkin_template.md` | tracked main | committed | 2026-04-25 | 210 B |
| **— BRANCH-ONLY DOCS —** | | | | |
| `doc/shadow_ops_v1_architecture.md` | shadow_ops_v1 only | branch-only | 2026-05-05 | 1,406 LOC architecture |
| `doc/consultant_briefings/README.md` | shadow_ops_v1, vp-leakage-fix | branch-only | 2026-05-05 | |
| `doc/consultant_briefings/round_09_phase3_vp_fix.pdf` | shadow_ops_v1, vp-leakage-fix | branch-only | — | Round 9 consultant brief |
| `doc/consultant_briefings/round_10_rule031_supplement.pdf` | shadow_ops_v1, vp-leakage-fix | branch-only | — | Round 10 consultant brief |
| `doc/DEPLOYMENT_CHECKLIST.md` | v2-integration only | branch-only | 2026-05-04 | V2 deployment checklist |
| `doc/PATCH_NOTES_V2.md` | v2-integration only | branch-only | 2026-05-04 | V2 patch notes |
| `doc/black_swan_protocol.md` | v2-integration only | branch-only | 2026-05-04 | Black-swan protocol |
| **— DIAGNOSTIC DOCS (STASH ONLY) —** | | | | |
| `doc/tietiy_2_0_feasibility/MASTER_FEASIBILITY.md` | stash@{0} | uncommitted | — | 249 lines |
| `doc/tietiy_2_0_feasibility/01-08_*.md` | stash@{0} | uncommitted | — | 8 supporting files (~1,400 lines) |
| `doc/tietiy_diagnostic/MASTER_FINDINGS.md` | stash@{0} | uncommitted | — | 225 lines |
| `doc/tietiy_diagnostic/00-07_*.md` | stash@{0} | uncommitted | — | 8 supporting files (~825 lines) |
| `doc/tietiy_diagnostic_round2/MASTER_FINDINGS_R2.md` | stash@{0} | uncommitted | — | 176 lines |
| `doc/tietiy_diagnostic_round2/08-17_*.md` | stash@{0} | uncommitted | — | 10 supporting files (~947 lines) |
| **— LAB TREE (BRANCH-ONLY) —** | | | | |
| `lab/AUTO_RUN_STATUS.md` | shadow_ops_v1 + others | branch-only | 2026-05-05 | Lab pipeline status |
| `lab/COMBINATION_ENGINE_FEATURE_SPEC.md` | shadow_ops_v1 + others | branch-only | | |
| `lab/COMBINATION_ENGINE_PLAN.md` | shadow_ops_v1 + others | branch-only | | |
| `lab/DECISIONS_LOG.md` | shadow_ops_v1 + others | branch-only | | |
| `lab/FINDINGS_LOG.md` | shadow_ops_v1 + others | branch-only | | |
| `lab/LAB_PIPELINE_COMPLETE.md` | shadow_ops_v1 + others | branch-only | | |
| `lab/PROMOTION_PROTOCOL.md` | shadow_ops_v1 + others | branch-only | | |
| `lab/ROADMAP.md` | shadow_ops_v1 + others | branch-only | | |
| `lab/analyses/INV-001 .. INV-013_findings.md` | shadow_ops_v1 + others | branch-only | | 8 finding files (numbers 1,2,3,6,7,10,12,13) |
| `lab/analyses/PHASE-01..05_*.md` | shadow_ops_v1 + others | branch-only | | 5 phase docs |
| `lab/analyses/inv_*_runner.py` | shadow_ops_v1 + others | branch-only | | 18 runner scripts |
| `lab/analyses/inv_phase*_*.py` | shadow_ops_v1 + others | branch-only | | Phase pipeline scripts (Phase 1b through Phase 5) |
| `lab/cache/llm/*.json` | shadow_ops_v1 + others | branch-only | | ~1,300 LLM response caches |
| `lab/factory/{bear,bull,choppy}_*` | shadow_ops_v1 + others | branch-only | | 14 cohort subdirs |
| `lab/factory/opus_iteration/`, `opus_synthesis/`, `oos_validation/`, `production_backtest/` | shadow_ops_v1 + others | branch-only | | LLM-driven cohorts + OOS |
| `lab/infrastructure/analyzer/` | shadow_ops_v1 + others | branch-only | | Feature extractor / signal replayer |
| `lab/deployment_validator/` | v2-integration only | branch-only | 2026-05-04 | DQF deployment validator |
| **— SHADOW_OPS CODE —** | | | | |
| `shadow_ops/` (on main) | working tree | tracked structure | dormant | Only `tests/__pycache__/` — no production modules on main |
| `shadow_ops/daily_scan.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Hard-coded to rule_019/rule_031/kill_001 |
| `shadow_ops/lifecycle.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | State machine |
| `shadow_ops/regime_classifier.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Cross-validates against lab/ |
| `shadow_ops/journal.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Append-only event journal |
| `shadow_ops/schemas.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | 5 event types |
| `shadow_ops/read_model.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Materialized read model |
| `shadow_ops/daily_report.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Operator-facing report |
| `shadow_ops/alerts.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Alert system |
| `shadow_ops/pre_scan_check.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | 7 preconditions |
| `shadow_ops/end_of_shadow.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Campaign review |
| `shadow_ops/data_ingest.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Data ingest |
| `shadow_ops/bootstrap.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | Bootstrap (never invoked in production) |
| `shadow_ops/tests/*.py` | shadow_ops_v1 only | branch-only | 2026-05-05 | 13 test files |
| **— SCANNER CODE (MAIN, ACTIVE) —** | | | | |
| `scanner/main.py` | main | committed | (last touched in commits) | Orchestrator (1,085 LOC per mindmap) |
| `scanner/telegram_bot.py` | main | committed | | 2,915 LOC (largest single file) |
| `scanner/outcome_evaluator.py` | main | committed | | 1,215 LOC |
| `scanner/journal.py` | main | committed | | 994 LOC |
| `scanner/stop_alert_writer.py` | main | committed | | 849 LOC |
| `scanner/scanner_core.py` | main | committed | | 794 LOC |
| `scanner/brain/brain_reason.py` | main | committed | | 1,085 LOC (Anthropic SDK) |
| `scanner/brain/brain_output.py` | main | committed | | 853 LOC |
| `scanner/brain/brain_verify.py` | main | committed | | 620+ LOC |
| `scanner/brain/brain_derive.py` | main | committed | | 597 LOC |
| `scanner/brain/brain_telegram.py` | main | committed | | **6 LOC stub** |
| `scanner/brain/brain_cli.py` | main | committed | | 27 LOC stub |
| `scanner/bridge/` (full tree) | main | committed | | ~3,500 LOC across 25 modules |
| `scripts/_run_smoke_brain_*.py` | main | committed | 2026-04-28 to 2026-04-29 | 5 smoke runners |
| `scripts/wave2_migration.py`, `wave5_m08_migration.py` | main | committed | 2026-04-25 | One-shot migration scripts |
| `scripts/test_anthropic_api.py` | main | committed | 2026-04-28 | Sanity check |
| `scripts/analyze_full.py` | main | committed | 2026-04-27 | Ad-hoc analysis |
| **— WORKFLOWS —** | | | | |
| `.github/workflows/*.yml` (28 active + 1 .bak) | main | committed | varies | Per Dimension 2 of mindmap |
| `.github/workflows/eod_update.yml.bak` | main | committed | (preserved) | Disabled escape hatch |
| `.github/workflows/dqf_validation.yml` | v2-integration only | branch-only | 2026-05-04 | V2 DQF validator |
| **— CONFIG —** | | | | |
| `data/fno_universe.csv` | main | committed | | 188 F&O stocks |
| `data/mini_scanner_rules.json` | main | committed | varies | 9 patterns + 7 rule gates |
| `config/dqf_config.yaml` | v2-integration only | branch-only | 2026-05-04 | V2 DQF config |
| `config/regime_config_v2.yaml` | v2-integration only | branch-only | 2026-05-04 | V2 regime config |
| `config/rule_registry.json` | v2-integration only | branch-only | 2026-05-04 | V2 rule registry |
| `.env` | main | committed | 2026-04-28 12:33 | 127 B (secrets file — review for accidental commit) |
| `.gitignore` | main | committed | 2026-05-13 01:34 | 377 B |
| `requirements.txt` | main | committed | 2026-05-13 01:34 | 719 B; anthropic==0.97.0 included |
| `CLAUDE.md` | main | committed | 2026-04-27 | 121 lines |
| **— OUTPUT JSON (CURRENT) —** | | | | |
| `output/signal_history.json` | main | committed (every mutation) | 2026-05-13 10:44 | 706 KB, schema v5 |
| `output/signal_history.backup.json` | main | committed | 2026-05-13 10:44 | 704 KB |
| `output/bridge_state.json` | main | committed | 2026-05-13 10:44 | 247 KB |
| `output/ltp_prices.json` | main | committed | 2026-05-13 10:44 | 10 KB (5-min cadence) |
| `output/stop_alerts.json` | main | committed | 2026-05-13 10:44 | 26 KB |
| `output/proposed_rules.json` | main | committed | 2026-05-13 01:35 | 59 KB — **70 pending proposals** |
| `output/patterns.json` | main | committed | 2026-05-13 01:35 | 141 KB |
| `output/eod_prices.json` | main | committed | 2026-05-13 01:35 | 49 KB |
| `output/open_prices.json` | main | committed | 2026-05-13 01:35 | 3.9 KB |
| `output/meta.json` | main | committed | 2026-05-13 10:44 | 701 B |
| `output/contra_shadow.json` | main | committed | 2026-05-13 10:44 | 31 KB |
| `output/scan_log.json` | main | committed | 2026-05-13 10:44 | 6.6 KB |
| `output/system_health.json` | main | committed | 2026-05-13 01:35 | 897 B |
| `output/weekly_intelligence_latest.json` | main | committed | 2026-05-13 01:35 | 4.1 KB |
| `output/colab_export.json` | main | committed | 2026-05-13 01:35 | 800 KB |
| `output/regime_debug.json` | main | committed | 2026-05-13 10:44 | 4.5 KB |
| `output/banned_stocks.json` | main | committed | 2026-05-13 10:44 | 133 B |
| `output/nse_holidays.json` | main | committed | 2026-04-25 | 323 B |
| `output/tg_offset.json` | main | committed | 2026-04-25 (rev'd ~every 10 min) | 21 B |
| `output/health_report.json` | main | committed | 2026-04-25 (legacy) | 711 B |
| `output/signal_archive.json` | main | committed | 2026-04-25 | **42 B (essentially empty)** |
| **— OUTPUT/BRAIN —** | | | | |
| `output/brain/cohort_health.json` | main | committed | 2026-05-12 22:00 | ~15 KB |
| `output/brain/regime_watch.json` | main | committed | 2026-05-12 22:00 | 851 B |
| `output/brain/portfolio_exposure.json` | main | committed | 2026-05-12 22:00 | 1.7 KB |
| `output/brain/ground_truth_gaps.json` | main | committed | 2026-05-12 22:00 | small |
| `output/brain/reasoning_log.json` | main | committed (append-only) | growing | ~58 KB |
| `output/brain/decisions_journal.json` | main | committed | initialized | **0 entries** |
| `output/brain/unified_proposals.json` | main | committed | 2026-05-12 22:00 | 12 KB — 3 pending |
| `output/brain/history/<date>_*.json` | main | committed | 2026-04-28 → ongoing | Daily snapshots |
| **— OUTPUT/BRIDGE_STATE_HISTORY —** | | | | |
| `output/bridge_state_history/<date>_PRE_MARKET.json` | main | committed | daily | 30-day retention |
| `output/bridge_state_history/<date>_POST_OPEN.json` | main | committed | daily | 30-day retention |
| `output/bridge_state_history/<date>_EOD.json` | main | committed | daily | 30-day retention; first appeared 2026-04-28 |
| **— OUTPUT/BACKUPS (CURRENT) —** | | | | |
| `output/backups/signal_history.2026-05-06..12.json` | main | committed | 2026-05-13 01:35 | 7 daily snapshots, ~620-706 KB each |
| `output/backups/signal_archive.2026-05-06..12.json` | main | committed | 2026-05-13 01:35 | 6 snapshots (42 B each) |
| **— BACKUPS (REPO ROOT) —** | | | | |
| `backups/2026-04-18-pre-phase2/` | main | committed | 2026-04-25 | Pre-phase2 snapshot folder |
| `backups/signal_history.2026-04-17-220725.pre-rej-migrate.json` | main | committed | 2026-04-25 | 356 KB |
| `backups/signal_history.2026-04-17-223809.pre-rej-resolve.json` | main | committed | 2026-04-25 | 356 KB |
| `backups/signal_history.2026-04-17-224049.pre-rej-resync.json` | main | committed | 2026-04-25 | 356 KB |
| `backups/signal_history.2026-04-17-224551.pre-layer-fix.json` | main | committed | 2026-04-25 | 357 KB |
| **— QUARANTINE —** | | | | |
| `quarantine/backup_20260411_053552/` | main | committed | 2026-04-25 | Pre-2026-04-11 snapshot |
| `quarantine/wave2_20260423_021333/scanner/` | main | committed | 2026-04-25 | Wave 2 pre-migration scanner |
| `quarantine/wave5_20260423_024400/scanner/` | main | committed | 2026-04-25 | Wave 5 pre-migration scanner |
| **— PWA / UI —** | | | | |
| `output/index.html` | main | committed | rebuilt on push | PWA root |
| `output/analysis.html` | main | committed | | Analysis dashboard |
| `output/health.html` | main | committed | | Health dashboard |
| `output/ui.js` | main | committed | | 61 KB main bundle |
| `output/app.js` | main | committed | | 62 KB |
| `output/journal.js` | main | committed | | 62 KB |
| `output/stats.js` | main | committed | | 49 KB |
| `output/analysis.js` | main | committed | | 36 KB engine |
| `output/sw.js` | main | committed | | 14 KB SW v8 |
| `output/manifest.json` | main | committed | | PWA manifest |
| `output/analysis/{overview,signals,segmentation,post_mortem,advanced}.js` | main | committed | 2026-04-25 | 5 plugin bundles |
| `output/icon-*.png`, `badge-*.png`, `health-icon-*.png` | main | committed | | PWA icons |
| `CNAME` | main | committed | 2026-04-25 | tietiy.in |
| **— L99 EXTERNAL ARTIFACTS —** | | | | |
| `~/Downloads/TIE_TIY_Swing_Scanner_Full_Blueprint.pdf` | filesystem only | NOT in repo | 2026-05-04 03:43 | 30 KB, 20 pages |
| `~/Downloads/TIETIY_Rule031_Audit_Supplement.pdf` | filesystem only | NOT in repo | 2026-05-05 03:14 | 15 KB, 6 pages |
| **— ~/.claude PROJECT MEMORY —** | | | | |
| `~/.claude/projects/-Users-abhisheklalwani-code-tietiy-scanner/91a4e01d-…jsonl` | filesystem | session log | 2026-05-05 20:54 | **69.2 MB** — previous mega-session |
| `~/.claude/projects/-Users-abhisheklalwani-code-tietiy-scanner/2461e34b-…jsonl` | filesystem | session log | 2026-05-13 17:03 | 1.57 MB — today's session |
| `~/.claude/plans/modular-tumbling-honey.md` | filesystem | saved plan | 2026-04-27 20:59 | 3.6 KB (may or may not be tietiy-related) |
| `~/.claude/tasks/2461e34b-…` | filesystem | today's task store | 2026-05-13 11:20 | (internal) |
| `~/.claude/tasks/8f2abc68-…` | filesystem | older task store | 2026-05-10 03:06 | (internal) |
| `~/.claude/tasks/91a4e01d-…` | filesystem | older task store | 2026-05-05 15:09 | (internal) |
| `~/.claude/paste-cache/` | filesystem | cache | active | 482 files, 3.4 MB |
| `~/.claude/file-history/2461e34b-…` | filesystem | versioned edits | active | Per-file `@v2` snapshots from today's session |
| **— ~/.claude OTHER —** | | | | |
| `~/.claude/sessions/15241.json`, `2908.json` | filesystem | session brackets | 2026-05-13 17:03 / 2026-05-05 19:46 | small |
| `~/.claude/history.jsonl` | filesystem | command history | 2026-05-13 17:00 | 216 KB |
| `~/.claude/backups/` | filesystem | CC internal backups | 2026-05-13 16:43 | small |
| **— /private/tmp —** | | | | |
| `/private/tmp/claude-501/-Users-abhisheklalwani-code-tietiy-scanner/2461e34b-…/` | tmpfs | today's session scratch | 2026-05-13 10:53 | small |
| **— SUB-PROJECT CACHES (Claude knows about) —** | | | | |
| `~/.claude/projects/-Users-abhisheklalwani-code-foundation-backtest/` | filesystem | other-project memory | — | 16 MB (sibling project) |
| `~/.claude/projects/-Users-abhisheklalwani-code-tradingview-mcp/` | filesystem | other-project memory | — | 40 KB |

---

## Section 8 — Summary Table (raw row count)

The table above has **150+ rows** spanning branches, stashes, untracked files, doc folders, branch-only docs, stashed docs, lab tree, shadow_ops modules, scanner code, workflows, config, output JSON files, brain outputs, bridge history, backups, quarantine, PWA assets, L99 external PDFs, Claude memory artifacts, and tmp scratch areas.

---

## Appendix A — Files referenced in CLAUDE.md (all verified to exist on main)

`bridge_state.json` · `bridge_telegram_eod.py` · `bridge.py` · `eod_master.yml` · `eod.py` · `fix_table.md` · `outcome_evaluator.py` · `postopen.py` · `postopen.yml` · `premarket.py` · `proposed_rules.json` · `roadmap.md` · `session_context.md` · `signal_history.json` · `telegram_bot.py`

## Appendix B — Things explicitly checked NOT to exist anywhere

- `~/.anthropic/` — not present
- `~/.claude-cache/` — not present
- `/tmp/*tietiy*` — none
- `~/Documents/*tietiy*` — none
- `~/Desktop/*tietiy*` — none
- `.draft` / `.wip` files in repo — none
- L99 raw research as markdown anywhere — none (PDF only)

## Appendix C — Total scanner code

`wc -l` across `scanner/**.py` (excluding `__pycache__`): **29,438 LOC** (NB: the earlier mindmap stated ~19,769 LOC; the larger figure here includes all `scanner/brain/`, `scanner/bridge/` subdirs and was the same query method).

---

*End of inventory. Read-only; no recommendations, no plans, no actions proposed.*
