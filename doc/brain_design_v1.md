# TIE TIY Brain Layer — Design v1

**Status:** Design-only. No code in repo yet. Wave 5 build target.
**Authored:** 2026-04-27 late-night (addresses GAP-33 from `master_audit_2026-04-27.md`).
**Companion docs:** `bridge_design_v1.md` (architectural conventions), `master_audit_2026-04-27.md` PART 8 + PART 9 (integration map + approval consolidation), `fix_table.md` LE-series (open work).
**Inheritance:** Brain inherits the bridge's load-bearing principles — read-only, single chokepoint, schema versioned from day one, plugin auto-discovery, immutable phase records, human approval mandatory.

**Amended 2026-04-28:** Wave 4 closure drift audit pass — design substance verified intact. Status update annotations added for: §11 Q5 Session D ship (`f9d4746`), §12 LE-06 ship (`7b96a97`), §3 R-multiple-as-tier-threshold caveat under Day-6 forced-exit dominance (deferred to `exit_logic_redesign_v1.md` track). No design substance changes; status refresh only.

This document locks the brain-layer design into the repo. Where chat-history detail isn't load-bearing, this doc states a default; where the answer is genuinely open, it's flagged in §11.

---

## §1. Mission and constraints

**Mission.** The brain layer extends what the system can *propose* without changing what the system can *do*. Bridge ships decisions; brain ships proposals about how decisions should be made next. The contract is unchanged: **system proposes, human disposes.**

**Hard constraints (constitutional — never relax):**

1. **Decision support only — NEVER auto-trading.** No code path in `scanner/brain/` may modify trade entry, stop, target, or exit. Not even with a flag. Not even guarded by approval. Auto-trading is out of scope at the architecture level — brain has zero broker integration.
2. **Read-only over truth files.** Brain reads `signal_history.json`, `patterns.json`, `proposed_rules.json`, `contra_shadow.json`, `mini_scanner_rules.json`, `weekly_intelligence_latest.json`, `bridge_state_history/*`, and never writes them. Brain writes only to `output/brain/*`.
3. **No cost for routine operation.** Pure-Python deterministic logic for daily derived views, statistical aggregations, threshold checks. Zero LLM calls for routine compute.
4. **LLM calls only at gates.** Opus 4.7 (or successor) is invoked at a small number of approval gates (target 3-5 calls/day, hard cap 10), never as a continuous-reasoning loop. Budget target <$1/day, hard cap $5/day with circuit-breaker abort.
5. **Single approval channel.** All proposals (rule, query, brain-derived) flow through one `unified_proposals.json` queue. One Telegram command, one PWA tab, one schema.
6. **Brain proposes, human approves.** No auto-mutation of `mini_scanner_rules.json` or any rules file by brain code, ever. The single exception inherited from `bridge_design_v1.md` §7.6 is the auto-revert path for collapsed contra-promoted patterns ("de-escalate, never escalate"). This exception lives in bridge composers, not brain.
7. **Honest pre-verification.** Every brain proposal includes claim, counter-evidence, expected effect, and reversibility path. Format is structurally enforced by `brain_verify.py`. No "trust me" proposals.
8. **Cap the proposal queue.** Maximum 3 new proposals per nightly run. Forces brain to rank rather than fire-hose. Proposals that don't fit get tracked in `decisions_journal.json` as "considered, deferred, rationale: …".

**Soft constraints (defaults — adjustable with rationale):**

- Nightly run anchored at 22:00 IST every day Mon-Sun (after market close + buffer for any delayed eod_master). Saturday and Sunday runs read Friday-EOD-stable truth files (signal_history immutable on weekends — verified 2026-04-29 against `.github/workflows/*.yml` cron expressions + cron-job.org dispatch surface). LLM gates always fire (no short-circuit); weekly cost ~$0.70 vs ~$0.50 weekday-only, delta well below $1/day soft cap. Sunday run additionally consumes fresh `weekly_intelligence_latest.json` (Sunday 20:00 IST publication via `weekly_intelligence.yml`). Locked 2026-04-29 per D-4 (`project_anchor_v1.md` §7).
- Proposal default expiry: 7 days. Auto-expire if no decision by then; brain may re-propose if conditions still warrant.
- Forward validation window: 30 days. Backtest-derived rules carry `days_validated_forward` counter; rules failing forward auto-demote (no approval needed for demotion).
- LLM gate count: 3-5 (specifics in §11 open questions).

---

## §2. Architecture overview

**Eight modules.** Mirror bridge's separation of orchestration / pure functions / plugins.

```
scanner/brain/
├── __init__.py
├── brain_input.py        — read truth files, normalize, surface as derived-view inputs
├── brain_derive.py       — materialize derived views (cohort_health, regime_watch, etc.)
├── brain_verify.py       — pre-verification framework (claim/counter/effect/reversibility)
├── brain_reason.py       — LLM gate invocation + cost tracking + circuit breaker
├── brain_output.py       — write to unified_proposals.json + decisions_journal.json
├── brain_telegram.py     — nightly batch digest renderer
├── brain_cli.py          — CLI command surface (Tier 1: status/rules/explain/trace)
└── brain_state.py        — read/write helpers for output/brain/*.json
```

**Inherited conventions from bridge.**

- Read-only over truth files (principle 1.1).
- Plugin discovery for things that grow (`brain/derivers/` may emerge as derived-view plugins if cohort/regime/exposure logic doesn't share enough scaffolding to live as functions in `brain_derive.py`). Decision deferred to Step 3.
- Pure functions for things that don't grow (verify, reason, output mechanics).
- Schema versioning from day one (`schema_version: 1` on every JSON file brain writes).
- Single write chokepoint (`brain_state.py` is the only writer; `brain_output.py` calls into it).
- Graceful degradation (a derived view crash logs WARNING, doesn't kill the nightly run; reasoning gate exhaustion logs ERROR + skips that gate but completes the run).
- Forward-compatible reserved fields (`unified_proposals.json` proposal entries carry `decision_metadata: {}` open dict for future enrichment).

**Output directory.** `output/brain/` (new). Eight new JSON files (§5 schema, §11 verify). Mirrors `output/bridge_state_history/` in retention semantics: append-only journals + dated snapshots, 30-day prune for derived views, indefinite retention for `decisions_journal.json` and `reasoning_log.json` (audit-trail value).

**Daily cycle.**

```
22:00 IST — brain_input.py loads truth files
22:01     — brain_derive.py runs deterministic derivers
22:02     — brain_verify.py scaffolds proposal candidates
22:03-04  — brain_reason.py fires 3-5 LLM gates (each <$0.20 budget)
22:05     — brain_output.py finalizes proposals, writes unified_proposals.json
22:06     — brain_telegram.py sends nightly batch (top-3, single message)
            → trader reviews PWA Monster tab or replies /approve <id>
            → brain logs decision to decisions_journal.json next cycle
```

Brain does NOT run during market hours. Brain does NOT participate in the bridge phase rhythm (L1/L2/L4). Brain reads `bridge_state_history/*` snapshots from earlier in the day; it does not write to bridge state.

**Weekend behavior (D-4 lock 2026-04-29).** On Sat 22:00 IST: derived views regenerate against Friday-EOD-stable truth files (signal_history.json, patterns.json, proposed_rules.json, mini_scanner_rules.json all immutable Sat/Sun — only `backup_manager.yml` Sat 8:30 IST + `weekend_summary.yml` Sat 9:00 IST run, neither mutates brain inputs). Cohort_health, regime_watch, portfolio_exposure, ground_truth_gaps archives byte-identical to Friday's. Step 4 candidates: cohort_axis + filter_signature stable, only `_<as_of_date>` suffix differs from Friday. Step 5 LLM gates always fire (no short-circuit; per V-12 + CORRECTION 6 the 90-day reasoning_log + decisions_journal context is fed INTO each prompt — short-circuit would break "smarter every day" + disagreement-awareness). decisions_journal appends with `_metadata.warnings: ["no_fresh_trading_inputs_since_<friday_date>"]`. On Sun 22:00 IST: regime_watch picks up fresh weekly_intelligence (~2hr publication lag; `weekly_intelligence.yml` Sun 20:00 IST is the only weekend brain-input mutator); other views identical to Friday. Step 7 Telegram renderer SHOULD format empty-queue Sat/Sun nights as quiet "all clear" rather than alarm — design pass for Step 7 (deferred).

---

## §3. The three-tier rule classification

Rules earn tier promotion through statistical thresholds. Once promoted, rules carry tier-specific influence on bucket assignment. Demotion is automatic on threshold breach; promotion always requires approval.

| Tier | Sample (n) | WR | Wilson 95% lower bound | Edge vs baseline | R-multiple | Temporal split | Influence on bridge bucket |
|---|---|---|---|---|---|---|---|
| **Tier S** (top) | ≥25 | ≥85% | ≥75% | ≥20pp | ≥1.0 | First-half WR within 10pp of second-half | TAKE_FULL boost; surfaces as Tier-A in `mini_scanner_rules.json` `boost_patterns[]` |
| **Tier M** (middle) | ≥15 | ≥75% | ≥65% | ≥10pp | ≥0.5 | (not required at this tier) | TAKE_SMALL boost; surfaces as Tier-B |
| **Tier W** (watch) | ≥10 | ≥65% | (not required) | ≥5pp | (not required) | (not required) | WATCH/informational only — no bucket boost; surfaces in [why?] expansion |
| **Candidate** | <10 OR fails Tier W gates | — | — | — | — | — | Not surfaced as a rule; tracked in `cohort_health.json` for future promotion |

**Wilson 95% lower bound.** `(p̂ + z²/(2n) − z·sqrt((p̂(1−p̂) + z²/(4n))/n)) / (1 + z²/n)` with `z=1.96`. Conservative WR estimate that accounts for sample-size uncertainty. Adopted instead of raw WR to avoid promoting small-n flukes.

**Temporal split (Tier S only).** Split the cohort's resolved trades into two halves chronologically. WR-difference between halves must be ≤10pp. This catches edges that worked once and decayed (regime artifacts, calendar effects).

**Demotion path.** If a Tier S rule's rolling-30 WR drops below Tier M floor, brain auto-demotes (no approval). If a Tier M rule drops below Tier W floor, brain auto-demotes. Demotion below Tier W deactivates the rule entirely with notification. Promotion in either direction always requires approval.

**Backtest seed handling.** Rules pre-loaded from running statistical analysis on the existing 141 resolved signals (~136 after schema-discipline filter, per `analysis_report_2026-04-27.md`). These carry `source: "backtest_derived"` and `days_validated_forward: 0`. After 30 calendar days of forward observation, brain auto-promotes (still no approval needed for *seed validation*, only for *initial activation*) those that meet thresholds with both backtest + forward agreement; auto-demotes those that fail forward.

**Rationale for three tiers vs binary.** Binary (active/inactive) creates a cliff — a rule passing 84% WR has zero influence; passing 86% has full TAKE_FULL influence. Three-tier scaling smooths the discontinuity and gives Wave-3 boost-pattern data (currently 7 patterns, all hand-flagged Tier A or B in `mini_scanner_rules.json`) a gradient of system trust.

**Status note 2026-04-28 (R-multiple under Day-6 dominance):** The R-multiple threshold column above is computed from realized P&L / risk on resolved trades. Per the F-2 audit (2026-04-28) and the prop_005 reframe rationale, today's live R-multiple distribution is dominated by Day-6 forced-exit outcomes (35/36 of 2026-04-27 resolutions were Day-6 outcomes, not target/stop hits). If the deferred exit-logic redesign track (`exit_logic_redesign_v1.md`, design only — not yet drafted) reshapes the exit-mechanism distribution, the R-multiple thresholds in this table may need recalibration before Step 5 LLM gates depend on Tier S/M assignments. Flagged for design rev when exit_logic_redesign_v1.md drafts; not addressed in tonight's status-refresh pass.

---

## §4. Eight build steps mapped to specific files

Each step is a session boundary. After each step, the work is shippable independently (smoke-tested + committed) without forcing the next step to ship.

### Step 1 — Schema lock

**Goal:** This document + `unified_proposals.json` schema doc.

**Files created:** `doc/brain_design_v1.md` (this file). Schema for `unified_proposals.json` is in §5 below; no separate doc.

**Files modified:** None.

**Smoke test:** N/A — pure documentation.

**Dependency:** Master audit must land first (✓ as of `58f4983`).

**Rollback:** revert the doc commit.

### Step 2 — Brain folder skeleton

**Goal:** Empty `scanner/brain/` package + module stubs that import without errors.

**Files created:**
- `scanner/brain/__init__.py`
- `scanner/brain/brain_input.py` — stub with module docstring + `def load_truth_files()` returning `{}`
- `scanner/brain/brain_derive.py` — stub
- `scanner/brain/brain_verify.py` — stub
- `scanner/brain/brain_reason.py` — stub
- `scanner/brain/brain_output.py` — stub
- `scanner/brain/brain_telegram.py` — stub
- `scanner/brain/brain_cli.py` — stub with argparse skeleton (`brain status` returns "not yet implemented")
- `scanner/brain/brain_state.py` — stub

**Files modified:** None.

**Smoke test:** `import scanner.brain.brain_input as _; print('OK')` for each module. CLI: `.venv/bin/python -m scanner.brain.brain_cli status` returns the not-yet-implemented stub.

**Dependency:** Step 1.

**Rollback:** delete the package.

### Step 3 — Derived views layer

**Goal:** First real logic. `brain_derive.py` produces four JSON outputs from existing truth files. No LLM, no proposals yet.

**Files created/modified:**
- Implement `brain_derive.py` with four deriver functions:
  - `derive_cohort_health(history) → output/brain/cohort_health.json`
  - `derive_regime_watch(history, weekly_intelligence) → output/brain/regime_watch.json`
  - `derive_portfolio_exposure(history) → output/brain/portfolio_exposure.json`
  - `derive_ground_truth_gaps(history, mini_rules, patterns) → output/brain/ground_truth_gaps.json`
- Implement `brain_input.py` with `load_truth_files(paths)` mirroring `evidence_collector.load_truth_files` style.
- Implement `brain_state.py` with `write_brain_artifact(path, data)` (atomic write + schema_version stamp + 30-day rolling history retention).

**Smoke test:** Sandbox copy of real `signal_history.json`. Run `brain_derive.run_all()` against it, verify all four JSONs land with `schema_version=1`, sensible non-empty content, real history SHA256 unchanged. Mirror the `_run_smoke_postopen.py` pattern.

**Dependency:** Step 2.

**Rollback:** revert deriver code; brain folder remains as stubs.

**Risks:** `[needs-verification]` — exact list of fields per derived view. §5 specifies `unified_proposals.json` precisely; the four derived views' schemas are deferred to Step 3 design pass (next session can lock at draft time).

### Step 4 — Pre-verification scaffolding

**Goal:** `brain_verify.py` enforces the claim/counter/effect/reversibility format. No LLM yet — verification is pure-Python schema validation.

**Files created/modified:**
- Implement `brain_verify.py`:
  - `verify_proposal(p: dict) → (bool, list_of_violations)` — checks shape per §6 format.
  - `build_proposal_candidate(type, source, claim, counter, effect, reversibility, evidence_refs) → dict` — convenience constructor.
  - `score_priority(p, derived_views) → float` — heuristic ranking for top-3 selection (no LLM).

**Smoke test:** Hand-craft 3-5 candidate proposals (well-formed + intentionally malformed), run through `verify_proposal`, assert correct accept/reject + violation messages.

**Dependency:** Step 3 (uses derived views as input to `score_priority`).

**Rollback:** revert `brain_verify.py` to stub.

### Step 5 — Reasoning gates (LLM)

**Goal:** First LLM integration. `brain_reason.py` invokes Opus at a bounded number of gates with cost tracking and circuit-breaker abort.

**Gates (initial proposed set, finalized at Step 5 design lock):**

`[needs-verification]` — exact gate count (3 vs 5) is in §11 open questions. Initial proposed set:

1. **Cohort-promotion gate** — when a cohort crosses Tier W → Tier M threshold, LLM is asked: "Given this cohort's data + counter-evidence + regime context, recommend approve / reject / hold-for-more-data." LLM output structures the *claim* + *counter*; promotion still requires human approval.
2. **Regime-shift detection gate** — when `regime_watch.json` signals a transition, LLM is asked: "Is this a true regime shift or a one-week wobble? What evidence would resolve the ambiguity?" Output feeds a regime_alert proposal.
3. **Exposure-correlation gate** — when `portfolio_exposure.json` shows high concentration in one (signal_type × sector × regime) cell, LLM is asked: "What's the correlated tail risk if this regime breaks? What hedge or pause-on-new-entries makes sense?" Output feeds an exposure_warn proposal.
4. **(optional) Disagreement gate** — when brain-proposed action conflicts with trader's recent manual decisions (read from `decisions_journal.json` history), LLM articulates the disagreement.
5. **(optional) Ground-truth-gap synthesis gate** — when multiple cohorts hit `n<5`, LLM proposes which to investigate first.

**Cost tracking.** Each LLM call logs to `output/brain/reasoning_log.json` with: `gate_name, prompt_tokens, completion_tokens, cost_usd, timestamp, request_id`. Daily total computed at start of next run; if cumulative >$1, soft warning. If >$5, circuit-breaker — skip remaining gates that day, log to `reasoning_log.json` with `aborted_by_circuit_breaker: true`.

**Files created/modified:**
- Implement `brain_reason.py` with gate dispatchers, prompt templates (one per gate), Anthropic SDK client, cost accumulator, circuit breaker.

**Smoke test:** Replace SDK client with a stub returning canned responses. Verify each gate's prompt assembly and output parsing. Live run with real Anthropic SDK happens out-of-band, manually first time.

**Dependency:** Step 4 (pre-verification format must be locked before LLM is asked to fill it).

**Rollback:** revert `brain_reason.py` + comment out gate dispatch in `brain_output.py`. Brain falls back to deterministic-only mode (no proposals from gates that needed LLM, but derived views + heuristic-ranked rule proposals still flow).

### Step 6 — Unified proposal queue

**Goal:** Single source of truth for all proposals (rule, query, brain-derived). Schema in §5 below.

**Files created/modified:**
- Implement `brain_output.py`:
  - `add_proposal(p) → unified_id` writes to `output/brain/unified_proposals.json`
  - `record_decision(unified_id, decision, reason, approver) → None` updates status + appends to `decisions_journal.json`
  - `expire_stale() → list[unified_id]` runs at start of nightly cycle to mark 7-day-old pending as `expired`
- Modify `scanner/rule_proposer.py`:
  - `approve_proposal` and `reject_proposal` keep existing `proposed_rules.json` writes (back-compat).
  - **New:** dual-write to `unified_proposals.json` via `brain_output.add_proposal` adapter.
  - New ID convention: `prop_unified_<date>_<seq>` for unified entries; legacy `prop_NNN` ids preserved as `legacy_id` field on the unified record.

**Smoke test:** Sandbox copy of `proposed_rules.json` + new empty `unified_proposals.json`. Approve a legacy proposal — verify both files update consistently. Reject a legacy proposal — verify both files reflect the rejection.

**Dependency:** Steps 4 + 5 (schema + verify must exist; reasoning may have populated some proposals).

**Rollback:** disable dual-write flag in rule_proposer; new file becomes a read-only mirror until consciously turned on again.

### Step 7 — Approval handlers

**Goal:** Single `/approve` and `/reject` command operating on the unified queue. Legacy `/approve_rule` and `/reject_rule` become deprecated aliases.

**Files created/modified:**
- Modify `scanner/telegram_bot.py`:
  - Add router branches for `/approve <unified_id>` and `/reject <unified_id> [reason]`.
  - New handlers `_respond_approve(chat_id, full_text)` and `_respond_reject(chat_id, full_text)` that route to `brain_output.record_decision`.
  - `/approve_rule` and `/reject_rule` now print "deprecated; use /approve <unified_id>" + still execute legacy path for one wave (backward compat).
  - Update `_respond_help` to list the new commands and mark the old ones deprecated.
- Modify `scanner/brain/brain_output.py` to dispatch: if proposal type is `kill_rule`, call `rule_proposer.approve_proposal/reject_proposal` under the hood (preserving the existing kill-pattern write path); if proposal type is `query_promote` etc., handle the relevant write directly.

**Smoke test:** Sandbox a unified_proposals.json with one of each type (kill_rule, regime_alert, exposure_warn). Run `/approve` on each via `_respond_approve` directly. Verify the right downstream write happens. Run `/reject` similarly. Run `/approve_rule prop_001` and verify deprecation message + legacy path still works.

**Dependency:** Step 6.

**Rollback:** revert telegram_bot router + handlers; delete `/approve` / `/reject` branches.

### Step 8 — PWA Monster tab

**Goal:** PWA surface for the unified queue.

**Files created/modified:** New tab in `output/app.js` or new file (e.g., `output/monster.js`); new entry in `output/index.html` bottom nav; CSS additions; deep-link to Telegram approve via `tg://msg?text=/approve%20<id>` (LE-05 mechanism).

**Smoke test:** Manual browser-side test on real PWA. Verify cards render, deep-link opens Telegram with pre-filled command.

**Dependency:** Step 7 + LE-05 work + Wave UI design pass.

**Status:** **Deferred to Wave UI track** — not part of the brain backend build sequence. Listed here for completeness; Wave UI session will pick it up.

**Rollback:** revert PWA changes; Telegram-only approval flow continues.

### Build sequence summary

| Step | Files | LOC est | LLM? | Smoke | Wave |
|---|---|---|---|---|---|
| 1 | doc/brain_design_v1.md (+ this) | 600 | — | n/a | 5 (this session pre-emptive) |
| 2 | 9 stub files | 80 | — | import test | 5 |
| 3 | derive + input + state | 800 | — | sandbox + real history | 5 |
| 4 | verify | 250 | — | shape assertions | 5 |
| 5 | reason + reasoning_log | 600 | yes | stub SDK + manual first call | 5 |
| 6 | output + unified queue + rule_proposer adapt | 350 | — | sandbox dual-write | 5 |
| 7 | telegram_bot router + handlers | 200 | — | per-type routing | 5 |
| 8 | PWA Monster tab | (Wave UI) | — | manual | UI |

Total Wave-5 brain backend (Steps 1-7): ~2280 LOC, 5-7 sessions.

---

## §5. Single approval queue schema

`output/brain/unified_proposals.json`:

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-27T22:05:00+05:30",
  "stats": {
    "total":     12,
    "pending":   3,
    "approved":  6,
    "rejected":  2,
    "expired":   1
  },
  "proposals": [
    {
      "id":          "prop_unified_2026-04-27_001",
      "legacy_id":   "prop_007",
      "type":        "kill_rule",
      "source":      "rule_proposer",
      "title":       "DOWN_TRI × Bank: 0/11 WR (kill candidate)",
      "claim": {
        "what":              "Add kill_pattern: signal=DOWN_TRI, sector=Bank",
        "expected_effect":   "Block ~6 signals/month at -19pp edge",
        "confidence":        "high"
      },
      "counter": {
        "evidence":          ["sample n=11 below n>=20 floor"],
        "risks":             ["regime mean reversion if Bear → Bull"]
      },
      "reversibility":       "1-line revert in mini_scanner_rules.json kill_patterns",
      "evidence_refs":       ["proposed_rules.json#prop_007", "patterns.json#sig=DOWN_TRI_sec=Bank"],
      "status":              "pending",
      "created_at":          "2026-04-27T22:05:00+05:30",
      "expires_at":          "2026-05-04T22:05:00+05:30",
      "approver":            null,
      "decision_at":         null,
      "decision_reason":     null,
      "decision_metadata":   {}
    }
  ]
}
```

**Type values (initial set, extensible).**

| Type | Source | Routing on approve |
|---|---|---|
| `kill_rule` | rule_proposer or brain | `rule_proposer.approve_proposal(legacy_id)` |
| `boost_promote` | brain | append to `mini_scanner_rules.json` `boost_patterns[]` |
| `boost_demote` | brain (auto path; appears as informational, not for approval) | (auto-applied; entry is read-only audit) |
| `query_promote` | future query_proposer | TBD when LE-03 ships |
| `regime_alert` | brain reasoning gate | informational; approve = "I've read it"; reject = "irrelevant" |
| `exposure_warn` | brain reasoning gate | same as above |
| `cohort_review` | brain ground-truth-gap detector | links to `cohort_health.json` cohort id; approve = trigger investigation; reject = ignore |

**Status values:** `pending`, `approved`, `rejected`, `expired`. Only `pending` is mutable through `/approve` or `/reject`. Approved kill_rules also flow through to `proposed_rules.json` for back-compat audit trail.

**Retention.** `unified_proposals.json` holds the rolling current queue (pending + recently-decided). On nightly run, items older than 90 days OR with status in `{approved, rejected, expired}` for >30 days move to `output/brain/proposals_archive.json`. This prevents the live file from growing unbounded.

### §5.1 Conflict surfacing (D-2 lock 2026-04-29)

When a brain-generated proposal's claim conflicts with an active rule in `data/mini_scanner_rules.json` (kill_pattern, boost_pattern, or watch_pattern), the proposal MUST surface the conflict in `counter` rather than be auto-suppressed. Locked per `project_anchor_v1.md` §7 D-2 + this session's design pass.

**Conflict definition + typology.** A proposal "conflicts with" an active rule iff it targets the same (signal_type, sector, regime) tuple matched by any active rule (wildcard nulls match), AND the proposal's action would produce a rule-level relationship of one of three distinct `conflict_type` values:

| proposal action | conflicts with active | conflict_type |
|---|---|---|
| `kill_rule` | matching `boost_pattern` (active=true) | `contradiction` |
| `boost_promote` | matching `kill_pattern` (active=true) | `contradiction` |
| `boost_promote` | matching `boost_pattern` same exact (signal, sector, regime) | `redundant` |
| `boost_promote` | matching `boost_pattern` broader-OR-narrower scope (e.g., new proposal regime-axis covers existing sector-axis rules) | `overlap` |
| `boost_promote` | matching `watch_pattern` (active=true) | `overlap` |
| `boost_demote` | (none — proposal targets the boost_pattern by `pattern_id`; not a conflict, a referenced action) | n/a |
| `cohort_review` / `regime_alert` / `exposure_warn` | (informational; never conflicts) | n/a |

**Concrete case (today's data, 2026-04-29).** Brain's Step 4 generator produced a `boost_promote` candidate for cohort `regime=Bear × signal_type=UP_TRI` (n=96, Tier M). Active boost_patterns `win_001`..`win_007` cover narrower (signal, sector, regime) tuples within that scope (UP_TRI×{Auto,FMCG,IT,Metal,Pharma,Infra}×Bear + BULL_PROXY×any×Bear). The new regime-axis proposal is **overlap**, not redundant — proposal is a SUPERSET of existing rules. Surfacing logic must distinguish: under (signal=UP_TRI, sector=null, regime=Bear) wildcard match, every active win_NNN matches → `decision_metadata.conflicts_with: [{rule_id: "win_001", conflict_type: "overlap"}, {rule_id: "win_002", conflict_type: "overlap"}, ...]`.

**watch_pattern overlap rationale (added per Phase 1 V-8 audit).** A `boost_promote` proposal whose tuple matches an active `watch_pattern` creates a dual-fire scenario in `mini_scanner.py` matching: in the regime where the watch_pattern fires, the same signal would carry BOTH the watch warning ("⚠️ caution") AND the TAKE_FULL conviction tag. Real trader-confusion + risk surface. Concrete case: today's C2 candidate `boost_promote UP_TRI × Metal × any-regime` matches `watch_001 (UP_TRI × any × Choppy)` — if approved, in Choppy regime UP_TRI×Metal would trigger watch warning AND boost-conviction simultaneously. Surfaced as `overlap` so trader sees the dual-fire risk before approval; not suppressed.

Pure dedup against pending `proposed_rules.json` entries is NOT a conflict — handled by Step 6 dual-write deduplication (legacy_id mapping), not §5.1.

**Required surfacing format.** When `decision_metadata.conflicts_with` is non-empty:
- `counter.evidence[]` MUST include one citation per conflicting rule, in format `"<rule_id> active: <signal> × <sector> × <regime> (n=<n>)"`. Programmatic format, not free-text. Example: `"win_002 active: UP_TRI × FMCG × Bear (n=19)"`.
- `counter.risks[]` MUST include the exact-match string `"approval would propagate <conflict_type> to mini_scanner_rules.json"` substituting actual conflict_type. If multiple conflict_types co-exist (rare; e.g., one redundant + one overlap), one risk string per distinct type. Example: `"approval would propagate overlap to mini_scanner_rules.json"`.
- `decision_metadata.conflicts_with` MUST be a list of objects (NOT a flat string list): `[{rule_id: "<id>", conflict_type: "<type>"}, ...]`. Programmatic structured format enables Step 7 Telegram badge rendering ("REDUNDANT" vs "OVERLAP" vs "CONTRADICTION") + future analytics queries.

The proposal verification gate extends with three new violation codes enforcing surfacing format. These codes live in `brain_output.verify_conflict_surfacing()` (Step 6 finalizer's semantic validator), separate from `brain_verify.verify_proposal()` which owns §6 shape rules. The §5.1 codes are STATE-DEPENDENT (need mini_scanner_rules context), while §6 codes are pure shape:

- `conflict_evidence_missing` — `decision_metadata.conflicts_with` non-empty but `counter.evidence[]` lacks programmatic-format citation for ≥1 listed rule_id.
- `conflict_risk_missing` — `decision_metadata.conflicts_with` non-empty but `counter.risks[]` lacks exact-match risk string for ≥1 listed conflict_type.
- `conflict_metadata_missing` — heuristic detector found a conflict (active rule matches proposal tuple) but `decision_metadata.conflicts_with` is empty/missing.

A proposal failing either gate is rejected into `verification_failures.json` (same path as other shape failures). Step 6 finalizer ordering:
1. `detect_conflicts` populates `decision_metadata.conflicts_with` + counter additions
2. `verify_proposal` validates §6 shape (state-independent)
3. `verify_conflict_surfacing` validates §5.1 semantics (state-dependent)
4. Both gates must pass for inclusion in `unified_proposals.json`

**Why surface, not suppress.** Auto-suppression hides cohort classification readiness from the trader, defeating the "smarter every day" reasoning_log mechanism. Surfacing in `counter` aligns with §6 "honest pre-verification" — the trader sees the conflict at approval time, makes the informed call. Differentiated `conflict_type` lets the trader read intent at-a-glance: REDUNDANT = no-op approval; OVERLAP = scope-expansion decision; CONTRADICTION = real safety call. Cost: single-trader skim-and-approve risk on contradiction-type; mitigated by structured counter format + verify_proposal enforcement + Step 7 Telegram badge (deferred to Step 7 design).

---

## §6. Pre-verification format

Every brain-generated proposal MUST contain the following fields, validated by `brain_verify.py`:

- **`claim.what`** — one sentence, action-oriented. *"Add kill_pattern: …"* or *"Promote boost_pattern: …"* or *"Investigate cohort: …"*. Imperative voice.
- **`claim.expected_effect`** — one sentence, quantified where possible. *"Block ~N signals/month at edge X"* or *"Surface as Tier-A boost on M cohort matches/week"*.
- **`claim.confidence`** — `high` / `medium` / `low`. Reflects brain's own self-assessment given sample size + counter-evidence weight.
- **`counter.evidence`** — array of strings. Each entry is one piece of evidence against the claim. Empty array is allowed only if claim.confidence == "high" AND human-readable rationale is in `decision_metadata.no_counter_rationale`.
- **`counter.risks`** — array of strings. Failure modes if the claim is acted on. Always non-empty (every action has SOME risk).
- **`reversibility`** — one sentence. *"1-line revert in X file"* or *"Demotion auto-fires if rolling-30 WR drops"*. If the action is irreversible, `reversibility` field reads "IRREVERSIBLE — see counter.risks", and the proposal type must be in an explicit allowlist (currently empty — no irreversible action types defined).
- **`evidence_refs`** — array of strings, each pointing to a source file + identifier. Allows trader to verify brain's data on demand.

**Verification gate:** any proposal failing this shape is rejected by `brain_verify.verify_proposal` and never reaches the queue. Brain logs the malformed candidate to `output/brain/verification_failures.json` for debugging.

---

## §7. CLI command surface

**Tier 1 — essential, ships in Step 5 (alongside reasoning gates):**

| Command | Output |
|---|---|
| `brain status` | One-line summary: pending count, last derived-view age, today's LLM cost, circuit-breaker state |
| `brain rules` | Active rules grouped by tier (S/M/W) with WR + n + days_validated_forward |
| `brain explain <unified_id>` | Full claim/counter/effect/reversibility for a proposal |
| `brain trace <signal_id>` | For one signal, show every brain output that referenced it (cohort, regime view, exposure, proposals) |

**Tier 2 — observability, ships after 14 days of brain in production:**

| Command | Output |
|---|---|
| `brain performance` | Brain proposal accuracy: approved-and-shipped vs subsequent outcome |
| `brain disagreements` | Cases where brain's recommendation conflicted with trader's manual decision; outcome of each |
| `brain proposals --pending`, `--rejected`, `--approved` | Filtered queue views |

**Tier 3 — possibly never:**

| Command | Output |
|---|---|
| `brain whatif <pattern>` | Replay history with alternative rule activation; show counterfactual P&L |

**Rationale for tiers.** Tier 1 is the minimum surface for trader to interrogate brain's reasoning during nightly review. Tier 2 needs ~14 days of decision history before its output is meaningful. Tier 3 is exploratory and may never justify the build cost; flagged here so we don't accidentally start it without a trigger.

---

## §8. Three interfaces

Brain surfaces in exactly three places. No additional channels.

| Interface | Cadence | Purpose |
|---|---|---|
| **PWA Monster tab** | Tactical, weekly review | Visual queue, expand cards, deep-link to Telegram for approve/reject |
| **Telegram approval gate** | Nightly, single batch message | Quick-tap approval with /approve or /reject; mobile-friendly |
| **Claude CLI terminal (`brain` command)** | On-demand, deep investigation | Trace a signal, replay reasoning, audit cost |

**No web dashboard, no email digest, no Slack integration.** The trader is one person; three channels with clear separation of cadence + purpose is sufficient.

---

## §9. Backtest seed + forward validation

**Seed at Wave 5 ship.** Brain runs once over the existing 141 (≈136 canonical) resolved signals, applies the §3 tier classifier, and emits a "seed candidates" output: every cohort that meets Tier W or above as of the historical data alone.

These do NOT auto-activate. They ship as `pending` proposals in `unified_proposals.json` with:
- `source: "backtest_seed"`
- `claim.confidence: "medium"` (downgraded — backtest-only)
- `decision_metadata.days_validated_forward: 0`

Trader reviews the seed batch on the first nightly run after Wave 5 ships. May approve, reject, or hold-for-forward-validation per individual proposal.

**Forward validation, days 1-30.** Approved seed rules carry their tier influence, but brain monitors. If forward WR diverges from backtest WR by >15pp on first 10 forward signals, brain auto-demotes (no approval) and emits an informational `boost_demote` entry to the queue. Trader sees the demotion + can re-promote with override after investigation.

**Day 30 and beyond.** Rule's `days_validated_forward` increments daily. After 30 days with forward WR within Tier-S thresholds, brain auto-promotes (still requires approval) any Tier M cohort that has earned Tier S status. The 30-day window prevents single-week regime quirks from propagating.

**Demotion always automatic; promotion always requires approval.** Inherited from bridge §7.6 safety bias.

---

## §10. Migration from current fragmented state

Reproduces master audit PART 9 migration table for in-doc reference. Phases align with build steps in §4.

| Phase | When | Action | Backward compat |
|---|---|---|---|
| W4-A | After LE-07 (✓ shipped) | Document brain design (this doc) | n/a |
| W5-S6 (Step 6) | Brain Step 6 | rule_proposer dual-writes: legacy `proposed_rules.json` + new `unified_proposals.json` | `/approve_rule` continues to work |
| W5-S7 (Step 7) | Brain Step 7 | New `/approve` and `/reject` handle `prop_unified_*`; legacy `prop_*` still routed via deprecated alias | both work; help text marks legacy as deprecated |
| W5+30 | 30 days after Step 7 ships | Telegram bot logs deprecation warning every time legacy command fires | both work; visible deprecation pressure |
| W6 | After Wave 6 stabilization | Remove legacy `/approve_rule` and `/reject_rule` aliases | one-wave grace period elapsed; clean state |

**Audit trail during migration.** During W5-S6 dual-write, `unified_proposals.json` is canonical for *display* and *new approvals*; `proposed_rules.json` is the canonical execution path for kill_rule type (rule_proposer.approve_proposal still does the actual mini_scanner_rules.json write). At W6, rule_proposer becomes a thin adapter that writes only to unified_proposals.json + executes the rule mutation; `proposed_rules.json` becomes a read-only legacy artifact.

---

## §11. Open questions / deferred decisions

**Q1. LLM gate count: 3 or 5?**

Three gates (cohort-promotion, regime-shift, exposure-correlation) cover the highest-leverage reasoning needs. Five (adding disagreement-detection + ground-truth-gap synthesis) capture more value but add cost + complexity. Default to **three at Step 5 ship**, add the optional two at Step 5.5 if observed cost is well under $1/day after 14 days. `[needs-verification]` — final lock at Step 5 design pass.

**Q2. Cost circuit-breaker threshold: $1 / $5 / $10 daily?**

$1 soft warning, $5 hard abort. Both subject to revision after first 14 days of real LLM usage. If a real-world proposal genuinely needs $3 of analysis on one rare night, we want the system to complete it; if cost balloons due to a bug or prompt regression, $5 cap stops the bleed.

**Q3. Brain self-evaluation cadence?**

Brain should track its own proposal accuracy: of the proposals it generated, what fraction were approved? Of approved proposals, what fraction proved correct in 30-day forward? Quarterly (every 90 days) generate a "brain performance review" markdown for trader; tier-2 CLI command surface is the primary read path. Cadence locked at quarterly to avoid over-tweaking on small sample.

**Q4. Disagreement-with-trader detection logic?**

Brain reads `decisions_journal.json` history. When brain's proposal disagrees with trader's recent (last 14 days) manual rule edit or take/skip decision pattern, brain flags the proposal with `decision_metadata.disagreement_with_trader: true` and articulates the disagreement in `claim.counter`. The disagreement detection logic itself is `[needs-verification]`: does it pattern-match exact (signal_type, sector, regime) tuples? Does it generalize? Defer to Step 5 design.

**Q5. Brain reading bridge_state vs reading bridge_state_history?**

Bridge writes 3 phase snapshots per trading day to `bridge_state_history/`. Brain runs nightly at 22:00 IST — long after the day's L4 phase landed (16:00). Brain reads from `bridge_state_history/<date>_EOD.json` (when it exists) for that day's full record. If L4 didn't run (Session D not yet shipped), brain falls back to `bridge_state_history/<date>_POST_OPEN.json` and degrades gracefully with `degraded_input: ["no_L4_state_for_<date>"]` in `reasoning_log.json`. **This is part of why Wave 3 Session D is a Wave-5 prerequisite (see `wave5_prerequisites_2026-04-27.md`).**

**Status update 2026-04-28:** Wave 3 Session D shipped this morning as `eod.yml` (commit `f9d4746`); the wave5_prerequisites B-1 dependency is satisfied (production verification still pending the 16:15 IST first fire). The fallback logic remains useful but its trigger condition narrows: now applies only to days when eod.yml fails per-run, not to "Session D not shipped" as a broader rollout state.

**Q6. Brain folder structure: flat 8 modules or nested by responsibility?**

Default to flat. Bridge proved flat-with-prefix works (composers/, core/, queries/, rules/). Brain's 8 modules are small enough to live at one level. If `brain_derive.py` grows past 600 LOC, split into `brain/derivers/` plugin folder per the bridge precedent.

---

## §12. Cross-references

| Topic | Source |
|---|---|
| Architecture conventions inherited | `bridge_design_v1.md` §1 (load-bearing principles) |
| Decision Surface model | `bridge_design_v1.md` §2 |
| Day flow rhythm (where brain slots in at 22:00 IST) | `bridge_design_v1.md` §3 + this doc §2 |
| SDR shape (brain reads SDRs, never writes) | `bridge_design_v1.md` §4 |
| Bucket assignment (brain proposals can adjust bucket-influencing rules) | `bridge_design_v1.md` §5 |
| Contra-tracker integration | `bridge_design_v1.md` §7 (auto-revert exception inherited) |
| Schema v1 conventions | `bridge_design_v1.md` §10 |
| Data flow map (brain's reads/writes in context) | `master_audit_2026-04-27.md` PART 1 |
| Workflow rhythm | `master_audit_2026-04-27.md` PART 2 |
| Approval gate consolidation rationale | `master_audit_2026-04-27.md` PART 9 |
| Specific gaps brain addresses | `master_audit_2026-04-27.md` GAP-21 (correlation), GAP-22 (learning loop), GAP-25 (note capture), GAP-26 (portfolio view), GAP-33 (brain doc gap — this doc closes it) |
| LE-series open work | `fix_table.md` LE-01..LE-07 |
| LE-05 (PWA → Telegram deep-link) | Wave UI dependency for Step 8 |
| LE-06 (demotion framework) | Wave 4 work that brain inherits + extends — shipped 2026-04-28 commit `7b96a97` |
| Wave 5 ship plan | `fix_table.md` SHIP PLAN section |

---

_Design end. Next session opens with `wave5_prerequisites_2026-04-27.md` (companion doc) — what blocks Step 1 vs Step 4 vs full Wave 5._
