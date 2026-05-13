# TIE TIY Deep Diagnostic — Master Findings, Round 2

Generated 2026-05-13. Sub-reports 08-17 carry detailed evidence. Round 1 master at `doc/tietiy_diagnostic/MASTER_FINDINGS.md`.

## TL;DR (incorporating R1 + R2)

1. **There is a parallel architecture track (`shadow_ops_v1`) that supersedes the current scanner.** 220 commits ahead of main, consultant-validated rule_019 (Bear+UP_TRI, 71% expected WR), 13-module forward-time validation harness, ready to bootstrap a 30-day campaign. This branch is where this entire diagnostic was performed.

2. **The current scanner's intelligence layer is producing actionable findings that nobody is reading.** Three parallel proposal/insight queues sit ignored: `output/brain/unified_proposals.json` (3 LLM-judged proposals expired 2026-05-06), `output/proposed_rules.json` (31 entries, mostly stale/duplicate, including DANGEROUS broad-scope kills), `output/brain/portfolio_exposure.json` (100% Choppy + 23.75% UP_TRI×Choppy×Bank exposure warning).

3. **`auto_analyst.py` is documented in design docs but was never built on any branch.** Its role has been absorbed by the brain layer; doc references are phantoms.

4. **`pattern_miner.py`'s "top_positive" recommendation logic is flawed** — it measures edge as WR-pp vs *signal-type baseline*, with no awareness of absolute PnL magnitude. Current top_positive (`regime=Bear_sector=Bank`) has avg PnL **−3.61%** — i.e. it's losing money but labeled "positive" because its 47.6% WR is above DOWN_TRI's 17.4% baseline. Anything that consumes top_positive unfiltered (notably `rule_proposer.py`) is at risk of over-promoting losing cohorts.

5. **`mini_scanner.py` filter rules have been in shadow_mode for 30+ days.** All 7 filter rules (`min_score`, `min_rr`, `require_volume`, etc.) are still `active: false`. Only kill_001 (DOWN_TRI×Bank) hard-blocks. No filter rule has activated despite empirically-clear cohort distinctions.

6. **`watch_matcher.py` (Phase 1) works as designed.** 107 LOC, one active watch (UP_TRI×Choppy), fired against COALINDIA on 2026-04-28 per session_context. Phase 2 (override-with-reason capture) gated on 2-3 clean production days; cannot confirm timing because this branch's `bridge_state_history` ends 2026-04-29.

7. **`bucket_engine.py` is architecturally sound.** 4-gate decision tree, evidence-driven, well-thresholded. Misclassifications happen at the *input* level (e.g., BULL_PROXY×Bear boost rule is sector-wildcard so includes Bank where the cohort weakens), not at the gate logic.

8. **Zone-based architecture is feasible with modest effort.** `scanner_core.build_zones` already does zone math; BULL_PROXY stop is already zone-anchored; the remaining point-based stops (UP_TRI, DOWN_TRI) are XS-effort edits. Total estimate: 1-3 days depending on whether schema-v6 + bridge display refresh are in scope.

---

## Updated surgical fix plan

The R1 plan was scoped to the live scanner on `main`. Round 2 surfaced `shadow_ops_v1` as an alternative that bypasses several R1 fixes by retiring the underlying mechanic. The user now faces a fork:

### Path A — Incremental fix on current scanner (`main`)

(R1 plan with R2 refinements.)

| # | Fix | Effort | New in R2? |
|--:|---|---|---|
| 1 | Complete brain production-fire (GH secret + 3 cron-job.org entries) | 0 code, dashboard only | R1 — still highest leverage |
| 2 | Add `kill_002` for DOWN_TRI sector=null (broad block) | 1 JSON entry | R1 |
| 3 | Add `Bull` label to regime classifier | ~10 LOC | R1 |
| 4 | Add `Target2x` exit rule for BULL_PROXY | 1 LOC | R1 |
| 5 | **NEW: Audit and clean `proposed_rules.json`** — reject prop_011/012/013 (kill UP_TRI) and prop_005/006 (kill BULL_PROXY) explicitly via `/reject_rule` to prevent accidental approval | Telegram commands or JSON edit | **R2** |
| 6 | **NEW: Pattern miner's "top_positive" needs absolute-PnL filter** — only label a cohort "top_positive" if avg_pnl > 0 AND WR-edge > +15pp | ~5 LOC in `_build_summary` | **R2** |
| 7 | **NEW: Activate `watch_002` for any cohort meeting n≥20 + WR-gap≥15% on the *loss* side** — currently only `watch_001` exists; the system has evidence to add more | JSON additions per cohort | **R2** |
| 8 | **NEW: After Fix 1, re-run brain.yml** so PENDING proposals regenerate against May data on `main` | manual workflow_dispatch | **R2** |

### Path B — Adopt `shadow_ops_v1` (campaign-start)

Bootstrap a 30-day shadow ops campaign on `shadow_ops_v1`:
```
python -m shadow_ops.bootstrap \
    --run-dir /path/to/campaign \
    --campaign-id "shadow_2026Q2" \
    --start-date 2026-05-14 \
    --operator <name> \
    --notes "first 30-day shadow"
```

Then daily: pre_scan_check → daily_scan → lifecycle → daily_report. After 30 days run end_of_shadow.

This implicitly addresses R1 fixes 2, 3, 4 because:
- DOWN_TRI is not deployed at all (Fix 2 = trivially satisfied).
- Regime classifier is replaced by `shadow_ops/regime_classifier.py` with first-class `sub_regime` (Fix 3 generalizes).
- Targets are computed per audited rule_019 spec (Fix 4 generalizes; not Target2x specifically, but a real target).

Path B does NOT address R1 Fix 1 (brain production-fire) since shadow_ops runs independently of the brain. The brain's insights stop accumulating once production scanner is paused.

### Recommended order (revised)

The R1 plan placed Fix 1 (brain production-fire) as highest leverage on the assumption that the user keeps running the existing scanner. That assumption is no longer obvious given shadow_ops_v1 is consultant-validated and ready.

**Decision point first, fix second.** Which path the user takes determines which fixes matter:

- If keeping the existing scanner → R1 plan + R2 additions 5-8.
- If switching to shadow_ops → bootstrap the campaign, retire the existing scanner's auto-fire, decide post-30-days on edge persistence.
- If running both in parallel → keep brain production-fire (R1 Fix 1) so insights accumulate while shadow validates; defer R1 fixes 2-4 as moot under shadow.

---

## Modules ready for production use vs needing work

| Module | Production status | Round 2 notes |
|---|---|---|
| `scanner_core.py` (signal detection) | ✅ Production | Asymmetric UP_TRI vs DOWN_TRI is intentional per backtest; mechanic limitations documented in R1 §02. |
| `scorer.py` | ✅ Production | Only UP_TRI×Bear has a target rule; everything else exits Day-6. Identified as fix candidate. |
| `mini_scanner.py` | ✅ Production | Shadow mode only; no filter rules active. kill_001 + boost_patterns load. |
| `pattern_miner.py` | ⚠ Production with caveat | Sound on negatives, structurally flawed on positives (WR-edge metric ignores PnL magnitude). |
| `rule_proposer.py` | ⚠ Production with caveat | Generating duplicate proposals (31 entries, many duplicates/dangerous). Brain layer's LLM gate path was designed to replace this but is gated on production-fire. |
| `chain_validator.py` | ✅ Production | Pure observability; doesn't gate. M-12 step-ordering false-positive known. |
| `weekly_intelligence.py` | ✅ Production | Sundays only; outputs only `_latest.json` (no dated archive). |
| `contra_tracker.py` | ✅ Production | 2 RBLBANK shadows pending; need 28 more resolved before unlock decision. |
| `bridge/composers/*` | ✅ Production (Wave 2/3) | All 3 phases (L1/L2/L4) shipped 2026-04-26 → 2026-04-28. |
| `bridge/rules/watch_matcher.py` | ✅ Production (Phase 1) | Pure function; one watch_001 active; one confirmed fire. |
| `bridge/rules/kill_matcher.py` | ✅ Production | kill_001 enforced. |
| `bridge/rules/boost_matcher.py` | ✅ Production | 7 boost_patterns enforced. |
| `bridge/rules/thresholds.py` | ✅ Production | Single source of truth; clean architecture. |
| `bridge/core/bucket_engine.py` | ✅ Production | 4-gate decision tree, evidence-driven. |
| `brain/brain_derive.py` | 🟠 Shipped, production-fire gated | Needs GH secret + cron entry. |
| `brain/brain_verify.py` | 🟠 Shipped, production-fire gated | Same. |
| `brain/brain_reason.py` | 🟠 Shipped, production-fire gated | Same. |
| `brain/brain_output.py` | 🟠 Shipped, production-fire gated | Same. |
| `brain/brain_telegram.py` | 🟠 Shipped, production-fire gated | Same. |
| `auto_analyst.py` | ❌ **Never built** | Phantom dependency in docs; absorbed by brain. |
| `shadow_ops/*.py` (13 modules) | ⏸ Ready to bootstrap | 30-day campaign ready on `shadow_ops_v1` branch. |

---

## Zone-based architecture readiness — per-module

| Module | Status | Effort if migrating |
|---|---|---:|
| `scanner_core.build_zones` | Already zone-aware (asymmetric ATR-based) | XS — replace ATR with Fib |
| `scanner_core.add_zone_proximity` | Already zone-aware | 0 |
| `scanner_core` UP_TRI stop | Point-based | XS |
| `scanner_core` DOWN_TRI stop | Point-based | XS |
| `scanner_core` BULL_PROXY stop | Already zone-anchored | XS — Fib offset |
| `scorer.calc_target` | R-multiple based | S — new `calc_zone_target` |
| `journal.py` schema | Point-only | M — schema v6 |
| `bridge/composers/*` display | Point-only | M — render zones |
| `outcome_evaluator` | "crossed price" | S — "entered zone" |
| `brain/*` | Indifferent | 0 |
| `bridge/rules/*` filter matchers | Indifferent | 0 |

**Yes/no per module: zone-readiness binary check:**
- `scanner_core`: PARTIAL (foundation exists, point-based stops to refactor).
- `scorer`: NO (R-multiple, no zone awareness).
- `journal`: NO (no zone fields in schema).
- `bridge`: NO (point-only display).
- `brain`: YES (indifferent to representation).
- `mini_scanner` rules: YES (indifferent).
- `outcome_evaluator`: NO (point-based; small refactor).

---

## Top 5 surprises from Round 2

1. **The `shadow_ops_v1` branch is a complete redesign that supersedes the current architecture.** 220 commits, consultant-validated rule_019, 13 modules shipped, ready to bootstrap. This wasn't visible from Round 1's `main`-branch-state-view focus. The user is sitting on a much more disciplined alternative to the current open-ended UP_TRI/DOWN_TRI/BULL_PROXY system.

2. **`pattern_miner.py`'s top-positive recommendation can be a losing cohort.** `regime=Bear_sector=Bank` was flagged as the system's top positive with +30.2pp edge, but its avg PnL is **−3.61%**. The pattern miner's WR-vs-baseline math doesn't weight PnL magnitude. Anything downstream that consumes this unfiltered is structurally at risk.

3. **`proposed_rules.json` has accumulated 31 stale/duplicate proposals**, several of which would kill the canonical winning cohorts (UP_TRI entirely, BULL_PROXY entirely). The deterministic rule_proposer has no schema-discipline check — it just keeps appending without dedup or sanity gates. The brain's LLM gate path was the intended fix but never went live.

4. **`auto_analyst.py` was never written**, despite being referenced as a load-bearing component in both `session_context.md` and `bridge_design_v1.md`. The role has been absorbed by the brain layer's `brain_reason.py`, but the docs still claim auto_analyst runs nightly. This is a phantom dependency that will mislead any future operator reading the canonical docs.

5. **Only ONE of the 7 filter rules in `mini_scanner.py` has ever activated** — and that was `kill_001` via the kill_patterns side-channel, not the filter-rule side. The 7 documented filter rules (`min_score`, `min_rr`, etc.) have been `active: false` for 30+ days despite the system collecting enough data to activate at least three of them (min_score threshold-7 is justified by the AN-04 score 5-6 non-monotonicity; require_volume by the pattern_miner v6 evidence; grade_gate by the Grade B underperformance). **The shadow-mode-collects-data principle has been adhered to so strictly that no rule has ever graduated to active.**

---

## Does the Round 1 surgical fix plan need updating?

**Yes — modestly:**

1. **Demote R1 Fix 1 (brain production-fire) from highest leverage to highest leverage *conditional on staying with the current scanner*.** If the user adopts shadow_ops_v1, the brain insights become less load-bearing.

2. **Add R2 Fix 5: explicitly reject the dangerous proposals in `proposed_rules.json`.** prop_005/006 (kill BULL_PROXY) and prop_011-013 (kill UP_TRI) are sitting there waiting for an accidental `/approve_rule`. A trader rushed through Telegram could destroy a winning cohort with one command.

3. **Add R2 Fix 6: patch pattern_miner's top_positive logic** to require `avg_pnl > 0` in addition to WR-edge. ~5 LOC.

4. **Add R2 Fix 7: activate watch patterns for documented loss cohorts.** UP_TRI×Choppy×Bank (n=12, 41.7% WR, −0.69 pnl) qualifies for watch_002 by the existing watch_001 evidence threshold.

5. **Add the path-decision step at top of plan:** "Are you keeping the existing scanner running, switching to shadow_ops_v1, or running both in parallel?" Different fixes apply to each.

The bulk of the R1 plan (Fix 2 broad DOWN_TRI kill, Fix 3 Bull label, Fix 4 BULL_PROXY target) stand and remain applicable to Path A.

---

## What I could not determine in R2

1. **The state of `main` branch's truth files.** Round 2 was performed on `shadow_ops_v1` which ends bridge_state_history at 2026-04-29 and signal_history.json at 2026-04-29. The May 4-12 DOWN_TRI cluster the user referenced in the task brief cannot be verified from this branch. **Recommended:** re-checkout `main` and re-run the data-driven portions of the diagnostic.

2. **Whether the bridge composers stopped firing after Apr 29 on `main`** or whether those fires landed on `main` but not on `shadow_ops_v1`. Same root question as #1.

3. **The exact 30-day-clean trigger for Phase 2 watch_pattern.** Memory says 2-3 days; cannot count production days without `main` truth files.

4. **Whether the lab/factory differentiator analyses contain unread insights.** 30+ subdirectories (`bear_uptri`, `bull_uptri`, etc.) with extract/synthesize/critique scripts. Each contains potentially-valuable per-cohort findings. Not read in Round 1 or Round 2.

5. **The `colab_insights.json` reference in `bridge_design_v1.md`.** Not present anywhere in `output/`; likely an artifact from the user's external Colab workflow (`lucifer` trigger context).

6. **Whether the V2 code pack on `v2-integration` is abandoned or paused.** Single commit dated 2026-05-04, no follow-up commits. Could be either.
