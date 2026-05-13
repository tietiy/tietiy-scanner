# 02 — shadow_ops_v1 vs TIE TIY 2.0 — What's the Actual Relationship?

## Direct answer

**shadow_ops_v1 is NOT TIE TIY 2.0.** They are different scopes that complement each other.

My Round 2 framing ("shadow_ops_v1 ≈ TIE TIY 2.0 in everything but name") was wrong. After reading the architecture doc TOC (16 sections, 1406 lines) and grep-checking for V5 / Fib / zones / self-learning / 7-state regime / brain proposals, **none of those concepts appear in `doc/shadow_ops_v1_architecture.md`.** Shadow_ops is much narrower.

## What shadow_ops_v1 actually is

A **forward-time process-validation harness for a single audited rule** (`rule_019_bear_uptri_hot_refinement`).

From the architecture doc:

- **Purpose** (§1.1): "test whether the audited rule library can be operated as a disciplined trading process by a human operator." Validates **process**, not **edge** (§1.2).
- **Active rule** (§2.1): rule_019 only. kill_001 logged as sectoral distress. rule_031 logged as confirmation overlay (not used for sizing).
- **Inactive** (§2.2): All Bull-regime rules ("zero deployable Bull-regime rules survive W3 + Phase 3"), all Choppy-regime rules ("six are dead schema"), other Bear sub_regime variants, BULL_PROXY rules generally.
- **Period** (§2.3): Minimum 30 calendar days. Hard ceiling ~60. Then PROCESS-VALIDATED / PROCESS-FAILED verdict.
- **Capital** (§2.4): Zero. Hypothetical trade cards from counterfactual fills. No broker integration.
- **Data model** (§3): 5 event schemas (`scan_event`, `candidate_signal`, `trade_card`, `lifecycle_event`, `fill_simulation`). Append-only JSONL.
- **Trigger logic** (§4): `rule_019` fires when `Bear AND UP_TRI AND sub_regime=="hot"`. sub_regime comes from `feat_nifty_vol_percentile_20d > 0.70 AND feat_nifty_60d_return_pct < -0.10`.
- **Lifecycle** (§5): T+1 OPEN entry, audit-faithful 6-day D1-D6 hold, no gap-fill, no mid-trade adjustments.
- **Out of scope for v1** (§12): Bull/Choppy rules, sub_regime variants, BULL_PROXY, V5 confluence, Fib framework, brain integration, self-learning.

That last point is decisive: **everything in the user's TIE TIY 2.0 vision is explicitly out of scope for shadow_ops_v1.**

## Why the relationship matters

TIE TIY 2.0 (per user's spec) needs:
1. V5 confluence gate
2. Unified Fibonacci framework (zones)
3. 7-state regime classifier
4. 5 new Bull-regime setups (VCP, EMA20 pullback, bull flag, Darvas, cup-handle)
5. Brain → dashboard → Telegram approval loop ("brain proposes, human disposes")
6. Self-learning via human-approved rule changes

shadow_ops_v1 provides: NONE of these.

What shadow_ops_v1 DOES provide that TIE TIY 2.0 would inherit:
- **Audit-faithful event-sourcing pattern** (5 event schemas, append-only JSONL with checksum sidecars).
- **Daily operator workflow** (pre_scan_check → daily_scan → lifecycle → daily_report).
- **`run_dir` pattern** with `run_config.json` freezing rules SHA + git SHA + audit-faithful constants.
- **Counterfactual fill simulation** (zero-gap T+1 OPEN entry).
- **End-of-shadow review** producing PROCESS-VALIDATED vs PROCESS-FAILED.

These are good patterns. They could become TIE TIY 2.0's audit substrate.

## How the relationship works in practice

If TIE TIY 2.0 is built:

- shadow_ops_v1 becomes **one of several validation campaigns** for TIE TIY 2.0 rules. Each new rule (VCP, EMA20 pullback, etc.) gets its own 30-day campaign. Shadow_ops semantics are reused.
- rule_019 (the shadow_ops primary rule) becomes **one Bear-regime entry in TIE TIY 2.0's rule library** — not the only thing. TIE TIY 2.0 has multi-regime, multi-setup ambition.
- The Phase 3 audits done on rule_019 become **the template for the validation pipeline** that TIE TIY 2.0's new Bull setups must pass before going live.

If TIE TIY 2.0 is NOT built:

- shadow_ops_v1 still has standalone value as a process-validation tool.
- The user can bootstrap a 30-day campaign on rule_019 and learn whether they can execute a sparse-fire (1 trade per 8 weeks) discipline.
- After 30 days: either PROCESS-VALIDATED (proceed to paper trading on rule_019) or PROCESS-FAILED (specific failure mode documented; either fix or abandon).

## Does shadow_ops_v1 become the seed of TIE TIY 2.0?

**Yes, partially.** The seed parts:

| shadow_ops_v1 component | TIE TIY 2.0 role |
|---|---|
| `data_ingest.py` | Foundation for new data layer (zone-aware) |
| `schemas.py` (5 event types) | Foundation for new event schemas (extended with V5 fields, zone fields, brain-proposal fields) |
| `journal.py` (append-only JSONL + checksum) | Foundation for new audit substrate |
| `regime_classifier.py` (computes `regime` + `sub_regime`) | Becomes input to 7-state classifier (the 3-state output is one of 7 states) |
| `daily_scan.py` (daily orchestrator) | Foundation for new daily orchestrator (extended to run multi-rule + brain + V5) |
| `lifecycle.py` (state machine T+1 → D6) | Foundation; extended to support zone-based exits + day-10 time-exit (per L99 framework) |
| `read_model.py` (derives view from event log) | Foundation for new dashboard read-model |
| `daily_report.py` (operator-facing markdown) | Foundation for new daily digest (with V5 + brain content) |
| `alerts.py` (CRITICAL/WARNING/INFO) | Reusable as-is |
| `pre_scan_check.py` (8 preconditions) | Reusable; extend with V5-API-up check |
| `end_of_shadow.py` (campaign-level review) | Foundation for per-rule validation pipeline (each new Bull setup goes through this) |
| `bootstrap.py` (run-config freeze) | Reusable verbatim |

Roughly **70% of shadow_ops_v1 is reusable as TIE TIY 2.0 audit substrate.** The 30% that's specific to rule_019 (the actual `trade_card` content, the rule_019 match logic, the rule_031 overlay) does NOT carry over wholesale.

## Effort implication

If TIE TIY 2.0 starts from shadow_ops_v1 substrate + adds new layers (V5 gate, Fib framework, 7-state regime, 5 Bull setups, brain-approval loop, dashboard wiring):

- shadow_ops_v1 substrate adaptation: ~30 hours (extend schemas, add new event types, generalize daily_scan).
- New components (V5 gate, Fib zone framework, 7-state classifier, 5 Bull setups, brain-approval wiring): ~300-450 hours (see §08 effort breakdown).

**Conclusion: shadow_ops_v1 is a strong foundation but TIE TIY 2.0 is a meaningfully larger project on top.**

## What about replacing TIE TIY (current scanner) with shadow_ops_v1 NOW, before TIE TIY 2.0?

This is the operationally fastest path. Tradeoffs:

PRO:
- shadow_ops_v1 is ready to bootstrap today (~0 hours of code, 1 hour of run_dir setup).
- Discipline test: can the user execute a rare-fire rule for 30 days?
- Generates real-data validation of rule_019 in the current (Choppy) regime — the missing piece in the audit chain.
- If process-validates, that's a green light for narrow rule_019 paper trading.

CON:
- rule_019 fires ~1 trade per 8 weeks during favorable regimes (per architecture doc §1.1). In the current Choppy regime, **likely zero fires in 30 days.**
- That's a useful but boring 30 days — operator gets "no signals" alerts daily.
- During that 30 days, the current scanner on `main` is still firing UP_TRI×Bank and BULL_PROXY signals — the operator must DECIDE what to do with those (continue trading them, paper-trade them, ignore them).
- Doesn't address the user's stated time-to-income concern.

Recommended sequencing if not building 2.0:

1. **Day 1:** `/reject_rule prop_005 prop_006 prop_011 prop_012 prop_013` to remove dangerous broad-scope kill proposals (R2 Fix 5).
2. **Day 1:** Bootstrap shadow_ops_v1 campaign in parallel (rule_019 process-validation).
3. **Day 1:** Complete brain production-fire (R1 Fix 1 — GH secret + 2 cron entries).
4. **Days 2-30:** Operator continues current scanner OR shifts to shadow-ops-only depending on risk appetite.
5. **Day 30:** Decide on TIE TIY 2.0 build based on shadow_ops outcome + 30 more days of current scanner data.
