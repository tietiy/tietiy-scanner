# Dimension 8 — Brain Layer Internals

**Generated:** 2026-05-13
**Scope:** What the nightly brain actually computes, step-by-step. Lives under `scanner/brain/`.

Designed in `doc/brain_design_v1.md` (534 LOC, fully locked spec §1–§12). Most recent production run: **2026-05-12 22:00 IST**.

---

## What is the brain?

A nightly analysis layer that:
1. **Derives** 4 read-only views from truth files (cohort_health, regime_watch, portfolio_exposure, ground_truth_gaps).
2. **Verifies** candidate proposals against a 16-violation taxonomy.
3. **Reasons** about them using Claude Opus 4.7 (3 LLM gates).
4. **Outputs** a unified queue of top-3 proposals with conflict detection.

It does NOT mutate `signal_history.json`. It only writes to `output/brain/` and dual-writes kill/demote candidates into `proposed_rules.json`.

---

## The seven steps (per `doc/brain_design_v1.md`)

| Step | Phase | File | Status |
|---|---|---|---|
| 1 | Schema lock | doc/brain_design_v1.md | ✅ locked |
| 2 | Skeleton | scanner/brain/__init__.py + 8 stub files | ✅ done |
| 3 | Derive | brain_derive.py | ✅ production |
| 4 | Verify + generate candidates | brain_verify.py | ✅ production |
| 5 | LLM reason | brain_reason.py | ✅ production |
| 6 | Unified queue output | brain_output.py | ✅ production |
| 7 | Telegram digest + `/approve` `/reject` | brain_telegram.py | ⚠️ STUB (6 lines) |
| 8 | PWA Monster tab | (not yet started) | ⏳ Wave UI |

---

## Step 3 — Derive (`brain_derive.py`, 597 LOC)

Orchestrator: `brain_derive.run_all()` (line 56). Four derivers, each isolated by try/except so one failure doesn't kill the others. All write atomically via `brain_state.write_brain_artifact()` (current + dated history archive).

### `_derive_cohort_health` (line 232)
**Axes**: signal+regime, signal+sector.

For each cohort:
- n, wins, losses, flat, wr
- wr_wilson_lower (95% CI lower bound)
- avg_pnl_pct, r_multiple
- edge_vs_baseline_pp (WR vs per-signal-type baseline)
- tier classification (per brain_design §3):
  - **Tier S**: n≥25, wr≥0.85, wilson≥0.75, edge≥20pp, r_mult≥1.0, |drift|≤10pp
  - **Tier M**: n≥15, wr≥0.75, wilson≥0.65, edge≥10pp, r_mult≥0.5
  - **Tier W**: n≥10, wr≥0.65, edge≥5pp
  - **Candidate**: n<10 OR fails Tier W
- Temporal-split drift (Tier S only): first-half vs second-half WR

→ `output/brain/cohort_health.json` + `output/brain/history/<date>_cohort_health.json`

### `_derive_regime_watch` (line 348)
**Authoritative regime source**: `weekly_intelligence_latest.json#regime#latest#regime`

The brain does NOT compute regime from price data. It reads the field set by `scanner/weekly_intelligence.py` on Sunday 20:00 IST.

Stability classifier:
- `stable`: same regime ≥5 of last 5 trading days
- `shifting`: any change in last 7 trading days
- `unclear`: otherwise

`regime_concentration` triggered if dominant regime > 80% of open positions (K-3 lock).

→ `output/brain/regime_watch.json`

### `_derive_portfolio_exposure` (line 436)
**Primary source**: `output/bridge_state_history/<as_of_date>_EOD.json#open_positions[]`.
**Fallback**: `signal_history.json` filtered by `outcome=='OPEN'`, with warning code `eod_archive_missing`.

Computes:
- `total_open` count
- `by_signal_type`, `by_sector`, `by_regime` breakdowns
- `concentrations` for 3-way cells (signal×regime×sector) ≥10%
- `regime_concentration` trigger if dominant regime >80%

→ `output/brain/portfolio_exposure.json`

### `_derive_ground_truth_gaps` (line 539)
Identifies:
- `thin_rules` (active rules with n<5)
- `thin_patterns` (mined patterns with n<10)

→ `output/brain/ground_truth_gaps.json`

---

## Step 4 — Verify + generate candidates (`brain_verify.py`, 620+ LOC)

### Verification (`verify_proposal`, line 88)
Validates against 16 violation codes (V-1 taxonomy):
- missing_id, invalid_type, missing_fields, invalid_field_type
- missing_claim, missing_counter, empty_counter
- missing_reversibility, missing_evidence_refs
- ... (12 more)
- And in Step 6: `conflict_evidence_missing`, `conflict_risk_missing`, `conflict_metadata_missing`

### Candidate construction (`build_proposal_candidate`, line 158)
`candidate_id = stable_cohort_identity + as_of_date` — NOT a content hash (V-2 CORRECTION 1). This means re-running the same cohort on the same day produces the same `candidate_id` (idempotency).

### Score-priority ranking (`score_priority`, line 250)
Pure deterministic heuristic, no LLM:

```
score = type_weight + confidence_weight + min(log10(n+1), 2.0) + tier_weight
```

Weights:
- type_weight: kill_rule=4.0, boost_promote=3.0, regime_alert=2.0, exposure_warn=2.0, cohort_review=1.0, boost_demote=0.0
- confidence: high=3.0, medium=2.0, low=1.0
- tier: S=3.0, M=2.0, W=1.0, Candidate=0.0
- n: min(log10(n+1), 2.0) — capped

Example (real, 2026-05-12 run): boost_promote, Tier M, high confidence, n=96 → `3.0 + 3.0 + 1.987 + 2.0 = 9.99`.

### Four deterministic generators
1. **`generate_boost_promote_candidates`** (line 326) — Tier M+S cohorts. Mirrors `mini_scanner_rules.boost_patterns[]` schema. Surfaces cross-view counter-evidence (Wilson lower, R-multiple vs threshold) and risks (tier drift, Day-6 dominance, regime absence).
2. **`generate_boost_demote_candidates`** (line 438) — Compares current vs prior dated archive. Auto-demotes on tier downgrade.
3. **`generate_kill_rule_candidates`** — Tier W cohorts with edge ≤-10pp.
4. **`generate_cohort_review_candidates`** — Thin rules/patterns from ground_truth_gaps.

### Failure log
Failed candidates appended to `output/brain/verification_failures.json` (1000-entry cap).

---

## Step 5 — LLM gates (`brain_reason.py`, 1,085 LOC)

**Model**: `claude-opus-4-7` (line 38)
**Cost**: $5/Mtok in, $25/Mtok out (CORRECTION 4 verified)
**Max tokens per call**: 1,024
**Soft warn**: $1 cumulative per-run
**Hard abort (circuit breaker)**: $5 cumulative per-run
**Typical run cost**: ~$0.05 (3 candidates × ~$0.02 each)

### Three gates

#### Gate 1: `_run_cohort_promotion_judge` (line 534)
- **Triggers**: each boost_promote candidate (iterates)
- **Role**: Filter + enrich. Evaluate against cross-view evidence + trader history (decisions_journal, 90-day window)
- **Decision**: `approve` / `suppress` / `hold`
  - approve → keep candidate, enrich counter[] with LLM evidence, possibly override confidence
  - suppress / hold → drop
- **Disagreement detection**: if recent decisions_journal entries oppose this approval, the LLM flags it

#### Gate 2: `_run_regime_shift_detector` (line 625)
- **Triggers**: always once per run (not candidate-specific)
- **Role**: Distinguish true regime shift from one-week wobble
- **Input**: regime_watch full payload + recent reasoning_log entries
- **Output**: either generate a `regime_alert` candidate, or `no_alert`

#### Gate 3: `_run_exposure_correlation_analyzer` (line 721)
- **Triggers**: always once per run
- **Role**: Evaluate portfolio concentration risk; cross-reference cohort_health for tier validation
- **Output**: either generate an `exposure_warn` candidate, or no warn
- **Trigger conditions**: single regime >80%, sector cell ≥20%, signal >85% + unstable regime

### Cost tracking
`RunCostState` dataclass (line 226):
- Accumulates per-run cost
- Logs `cost_state.gates_skipped_due_to_failure` for API failures
- Logs `cost_state.gates_skipped_due_to_abort` if circuit breaker hits

### Retry logic
`_call_anthropic_with_retry` (line 410):
- Retry once on timeout / rate-limit / malformed-JSON
- No retry on auth failure

### History context (V-12)
For each LLM call, the prompt includes:
- Last 20 reasoning_log entries for this gate (90-day window)
- Last 10 decisions_journal entries with cohort-identity match (90-day window)

This is how the brain becomes "smarter every day" — past reasoning is replayed as context.

### reasoning_log.json
Append-only forever (K-4 lock). Per LLM call records: gate_name, prompt_tokens, completion_tokens, cost_usd, timestamp, request_id, decision, rationale, aborted_by_circuit_breaker flag.

---

## Step 6 — Unified queue output (`brain_output.py`, 853 LOC)

Orchestrator: `run_step6()` (line 650). Nine-step finalizer:

### 1. Combine
Combine Step 5 kept (filtered boost_promote candidates) + Step 5 generated (regime_alert, exposure_warn).

### 2. Stamp score_priority
Call `_stamp_score_priority()` on deep copies.

### 3. §5.1 Conflict detection (`detect_conflicts`, line 161)
For each proposal, query `mini_scanner_rules.json` for active rules matching the tuple `(signal, sector, regime)`. Per §5.1 typology:

| Proposal type | Existing active rule type | Result |
|---|---|---|
| kill_rule | boost_pattern | **contradiction** |
| boost_promote | kill_pattern | **contradiction** |
| boost_promote | boost_pattern (exact match) | **redundant** |
| boost_promote | boost_pattern (superset/subset) | **overlap** |
| boost_promote | watch_pattern | **overlap** (per LOCK A 997d4af) |

### 4. Populate conflict surfacing
`populate_conflict_surfacing` (line 220):
- Enrich `counter.evidence` with citations: `<rule_id> active: <signal> × <sector> × <regime> (n=<n>)`
- Append risk strings: `approval would propagate <conflict_type> to mini_scanner_rules.json`
- Set `decision_metadata.conflicts_with` as list-of-objects

### 5. Verify shape + verify surfacing
Two verifies: §6 shape + §5.1 conflict surfacing. Three new violation codes for conflict surfacing failures. Candidates that fail any verify are dropped to `verification_failures.json`.

### 6. Top-3 selection (`apply_top_n_selection`, line 331)
Sort by `(-score_priority, candidate_id_alpha)`. Keep top 3, drop the rest.
- **Hardcoded**: `_TOP_N_DEFAULT = 3` (line 56)
- Dropped candidates tracked in `_metadata.dropped_due_to_top3_cap` with score + "below_top3_cap" reason

### 7. Build unified entries (`build_unified_proposal_entry`, line 355)
Per V-2 schema: id, type, source, claim/counter/reversibility, status=pending, created_at, expires_at=+7days, approver=null.

### 8. Dual-write to `proposed_rules.json` (V-3 scope)
**Only `kill_rule` + `boost_demote` candidates** are dual-written into the legacy `proposed_rules.json` queue. boost_promote / regime_alert / exposure_warn stay unified-only.

### 9. Atomic write
- `output/brain/unified_proposals.json` (current)
- `output/brain/history/<date>_unified_proposals.json` (archive)
- Initialize `output/brain/decisions_journal.json` if missing

---

## Step 7 — Telegram digest + approval (STUB)

`scanner/brain/brain_telegram.py` is **6 lines**: a module docstring and nothing else.

Workflow `brain_digest.yml` (22:05 IST cron-job.org) fires the stub and exits.

Designed flow:
1. Trader sees top-3 in `unified_proposals.json` (via Telegram digest OR PWA Monster tab)
2. Trader replies `/approve prop_unified_2026-05-12_001` or `/reject <id> [reason]`
3. Bot handler (Step 7) calls `brain_output.append_decision()` → `decisions_journal.json` entry
4. If type is kill_rule/boost_demote: also calls `rule_proposer.approve_proposal()` → mutates `mini_scanner_rules.json`
5. If type is regime_alert/exposure_warn: informational — approver just marks "read"
6. Next brain run reads decisions_journal to populate history context for LLM gates

Current reality: `/approve_rule` and `/reject_rule` (legacy, for `proposed_rules.json`) work today via `telegram_bot.py`. `/approve <unified_id>` and `/reject <unified_id>` are not yet wired.

---

## What's in `output/brain/` right now (2026-05-13 verified)

```
output/brain/
├── cohort_health.json              (~15 KB)   — as_of 2026-05-12
├── regime_watch.json               (~851 B)   — regime=Choppy, stable, 7 days
├── portfolio_exposure.json         (~1.7 KB)  — total_open=48
├── ground_truth_gaps.json
├── reasoning_log.json              (~58 KB)   — entries since first run
├── decisions_journal.json          (~231 B)   — initialized, empty
├── unified_proposals.json          (~12 KB)   — 3 proposals pending
├── verification_failures.json
└── history/
    ├── <date>_cohort_health.json
    ├── <date>_regime_watch.json
    ├── <date>_portfolio_exposure.json
    ├── <date>_ground_truth_gaps.json
    └── <date>_unified_proposals.json
```

Today's 3 proposals (from `unified_proposals.json` last run 2026-05-12 22:00 IST):
1. `prop_unified_2026-05-12_001` — boost_promote UP_TRI × Bear (Tier M, n=96, 94.7% WR, score 9.99)
2. `prop_unified_2026-05-12_002` — boost_promote UP_TRI × Metal (score 9.63)
3. `prop_unified_2026-05-12_003` — exposure_warn (score 6.0)

None approved yet. None will resolve today's Choppy SKIP issue — they need a Bear regime or apply to Metal sector specifically.

---

## Why today's 8/8 signals are bucketed SKIP (the brain's view)

1. The regime label comes from `weekly_intelligence_latest.json`, last updated **Sunday 2026-05-11 20:00 IST**. It says regime = **Choppy** with `stable` classifier for 7 days.
2. Mini-scanner rules that boost UP_TRI / DOWN_TRI are mostly Bear-gated or sector-gated.
3. Bucket_engine Gate 3 finds no boost match in Choppy regime for today's symbols.
4. Bucket_engine Gate 4 (evidence consensus) examines exact_cohort + sector_30d + regime_baseline for each signal — all are thin in Choppy regime.
5. Result: bucket = SKIP for all 8.

The "DEGRADED" banner is composed by the bridge (`bridge_state.banner`), not the brain. Brain's contribution is the regime label being Choppy (read from weekly_intel, not freshly computed).

**To resolve today's SKIPs without changing regime**: either approve a UP_TRI × Choppy boost (requires a Tier M cohort to exist for that combination — verify in cohort_health.json) OR wait for the regime to shift back. Brain Step 5 `regime_shift_detector` would surface a `regime_alert` if it sees evidence of a shift, but as of 2026-05-12 it did not.

---

## Brain's design locks (referenced by code)

These are stable design decisions documented in `doc/brain_design_v1.md`:

| Lock | Meaning |
|---|---|
| **K-3** | regime_concentration triggers at >80% dominant regime |
| **K-4** | reasoning_log + decisions_journal are FULL_NO_PRUNE — never deleted |
| **D-4** | cadence: brain runs Mon-Sun (not Mon-Fri) |
| **D-8** | R-multiple thresholds under review (35/36 of Apr-27 resolutions Day-6 forced; caps observable R-multiple) |
| **D-10** | weekend tone differs in digest format |
| **M-15** | precision-critical workflows fire from cron-job.org, not GH schedule |
| **V-1..V-14** | brain_reason / brain_output verification rules |
| **V-2** | candidate_id is stable cohort identity + as_of_date (NOT content hash) |
| **V-3** | dual-write scope: only kill_rule + boost_demote into proposed_rules.json |
| **V-12** | LLM context includes last 20 reasoning_log + 10 decisions_journal entries |
| **§5.1** | conflict typology: contradiction / redundant / overlap |
| **LOCK A** | watch_pattern overlap surfacing rule (997d4af) |
| **LOCK C** | ee4007d nine-step finalizer order in Step 6 |

---

## Anomalies / open questions

1. **Phantom auto_analyst**: brain_design lists `query_promote` proposal type for a future `query_proposer` (line 338) — not implemented. Wave 6+.
2. **brain_cli Tier 1 commands** (`status`, `rules`, `explain`, `trace`) are stubs that print "not yet implemented" (line 21).
3. **decisions_journal is empty**: Step 7 not wired. The brain has nowhere to learn from trader decisions yet.
4. **Weekend brain runs read stale data**: signal_history doesn't mutate on weekends. Brain reproduces Sunday's analysis on Saturday from Friday-EOD data. Designed per D-4 (cadence lock); intentional but worth noting.
5. **R-multiple Tier classification underclassifies cohorts** (C-3 warning): 35/36 of Apr-27 resolutions exited via Day-6 forced exit, capping observable R-multiple. cohort_health emits a warning when any cohort n≥15, but this is a known cap.

---

## How the brain helps (when Step 7 ships)

The brain is the only layer in the system that:
- **Compares yesterday to today** (via dated history archives).
- **Brings cross-view context** (a boost_promote candidate is judged with regime_watch, portfolio_exposure, decisions_journal).
- **Uses LLM reasoning** (the only Anthropic API integration in the codebase).
- **Detects regime shift** (via regime_shift_detector gate).
- **Detects portfolio concentration** (via exposure_correlation_analyzer gate).
- **Detects conflict with existing rules** (§5.1 conflict detection during Step 6 unified queue assembly).

The trader sees this as the daily 22:05 digest (when shipped) — a top-3 list of "should you change something tomorrow?" actionable proposals. Today, this digest does not arrive because brain_telegram is a stub.
