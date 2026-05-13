# 03 — Migration Path 1.0 → 2.0

Critical constraint: **1.0 stays running daily during the entire 2.0 build.** No "stop trading for 4 months while we rebuild."

## Strategy: parallel branch, opt-in migration, hard switchover

Build 2.0 modules in `tietiy_2_0` branch (or `~/code/tietiy-scanner-v2` separate repo — see §03.5 below). Keep `main` as the production branch. 2.0 modules can be tested in shadow mode against the **same** `signal_history.json` truth file before they're allowed to write to production.

```
main (production, never touched)         tietiy_2_0 (new architecture)
   │                                      │
   ├─ scanner/main.py fires daily        ├─ core/orchestrator works against
   ├─ writes output/signal_history.json  │   the same signal_history.json
   ├─ brain.yml fires nightly            ├─ but writes to output/v2_shadow_signals.json
   │                                      ├─ until switchover criterion met
   │                                      │
   └─ Telegram + dashboard live          └─ shadow runs ONLY; no Telegram, no PWA visible
```

## Phase 1 — Foundation (Weeks 1-2, ~50 hours)

| Task | 1.0 source | Outcome |
|---|---|---|
| Set up `tietiy_2_0` branch with `core/` skeleton | — | new dir tree |
| Define + lock protocols from §02 | — | `core/contracts.py` |
| Build registry pattern | — | `core/registry.py` |
| Port `core/calendar` from `scanner/calendar_utils.py` | clean lift | ⭐ |
| Port `core/universe` from `scanner/universe.py` | clean lift | ⭐ |
| Port `core/ipc` (atomic writes) from `scanner/bridge/core/state_writer.py` | clean lift | ⭐ |
| Port `core/data_layer` from `scanner/price_feed.py` + `ltp_writer.py` | adapter | 🔧 |

**Switchover criterion at end of Phase 1:** `core/orchestrator` can load registered plug-ins and call them. Empty registry. No detectors yet.

## Phase 2 — Detector porting (Weeks 3-4, ~40 hours)

Port the two proven detectors to the plug-in contract:

| Detector | Source | Effort |
|---|---|---:|
| `UpTriDetector` (Bear regime only — supported_regimes=["Stable-Bear"]) | `scanner_core.detect_signals` UP_TRI block | 3h |
| `BullProxyDetector` (Bear regime — supported_regimes=["Stable-Bear"]) | `scanner_core.detect_signals` BULL_PROXY block | 1h |
| `Rule019Detector` (Bear+UP_TRI+sub_regime=hot — supported_regimes=["Stable-Bear"]) | port from `shadow_ops_v1` | 6h |

After this, run **2.0 in shadow against May 2026 historical data**. Verify it produces the same detections that 1.0 produced on those dates. **Switchover criterion: 14 consecutive days where 2.0 shadow output matches 1.0 production output byte-for-byte (after normalizing for cosmetic field differences).**

If they diverge, fix 2.0 before proceeding. If they match: detectors port is validated.

## Phase 3 — Brain / bridge adapter (Week 5, ~20 hours)

Brain layer stays unchanged structurally; wrap with an adapter that reads from new orchestrator's output:

```python
# core/brain_adapter.py
def run_brain_v2():
    # 2.0's signal_history is byte-compatible with 1.0's schema v5
    # Brain code from scanner/brain/*.py works UNMODIFIED
    from scanner.brain import brain_cli
    brain_cli.run()
```

Same for bridge composers. **The brain and bridge are the existing crown jewels; they go through verbatim.**

**Switchover criterion at end of Phase 3:** Brain run against 2.0's shadow signal_history produces the same proposals (within UUID differences) that brain run against 1.0's signal_history produces.

## Phase 4 — UI parallel build (Weeks 6-7, ~28 hours)

Build the dashboard (per §04) **as a separate static deploy** at e.g. `tietiy.in/v2/` while keeping `tietiy.in/analysis.html` (the 1.0 PWA) live.

- 2.0 PWA reads the SAME `output/brain/*.json` files.
- 2.0 PWA surfaces the proposals 1.0 was hiding.
- User can use 2.0 PWA for proposal approval RIGHT AWAY — even before 2.0 orchestrator is doing anything live.

**This is the highest-leverage step. The brain has 3 PENDING proposals that have regenerated daily since 2026-04-29 with zero approvals.** Wiring just the dashboard to those proposals (without touching the scanner) would close the loop today.

**Switchover criterion at end of Phase 4:** User has approved or rejected the 3 PENDING brain proposals. The approval-loop closure is demonstrated to work.

## Phase 5 — Validation harness (Weeks 8-9, ~30 hours)

See §06 for detail. Take the shadow_ops_v1 harness and generalize it to accept arbitrary SignalDetector plug-ins. Each new Bull setup (from §07 of feasibility) runs through:
1. Backtest on 5-year data
2. Purged-CPCV with embargo
3. Per-regime stratified analysis
4. Paper trading (logged via 2.0 shadow path)

**Switchover criterion at end of Phase 5:** First new Bull detector (EMA20 pullback — lowest effort, highest fire rate) is passing backtest + CPCV + paper for 4 weeks.

## Phase 6 — New detectors (Weeks 10-14, ~100 hours)

Build the 4 remaining new detectors per L99 (VCP, Bull flag, Darvas, Cup-handle). Each goes through the validation harness. Each is added to the plug-in registry **disabled by default**. Only enabled after validation.

## Phase 7 — Live cutover (Week 15)

At this point 2.0 has:
- Same proven detectors as 1.0 (ported)
- Same brain + bridge (adapter only)
- New dashboard with closed approval loop
- 1-2 new Bull detectors paper-validated and ready
- Validation harness for the remaining detectors

**Live cutover criteria (ALL must hold):**

1. 2.0 has run in shadow for ≥14 consecutive days producing the same signals as 1.0 (ported detectors).
2. 2.0 dashboard has captured ≥10 approval decisions in `decisions_journal.json` (proves the loop works).
3. No regressions: 2.0's signal_history outputs are byte-compatible with 1.0's schema v5 for ported detectors.
4. User has explicitly approved cutover.

**Cutover procedure:**
1. Stop 1.0 cron entries for `morning_scan.yml`, `eod_master.yml`, `brain.yml`, `bridge.yml`.
2. Start 2.0 equivalents.
3. Keep 1.0 code available on `main` for emergency rollback.
4. Run 2.0 for 7 days while monitoring `system_health.json`.
5. If green: 1.0 retired; `main` branch fast-forwards to `tietiy_2_0`. If not: rollback to 1.0 via cron flip.

## What MUST port unchanged

- `output/signal_history.json` schema (v5 → v6 only if zone fields added; backward-compatible adapter required)
- `output/brain/*.json` files (brain code unchanged)
- `output/bridge_state*.json` files (bridge code unchanged)
- `data/mini_scanner_rules.json` (port wholesale; carries kill_001 + watch_001 + 7 boost_patterns)
- `data/fno_universe.csv`
- The 7 `boost_patterns` (proven Bear cohorts)
- The 1 `kill_pattern` (kill_001 DOWN_TRI+Bank)
- The 1 `watch_pattern` (watch_001 UP_TRI+Choppy)

## What MUST be re-derived (not ported)

- `scanner/main.py` (38 KB hand-coded 21-step orchestrator) → `core/orchestrator` via registry
- `scanner/scorer.py:get_exit_rule` (only handles UP_TRI×Bear) → zone-based exit per detector config
- `scanner/scorer.py:calc_target` (returns None for non-Bear UP_TRI) → `OutcomeEvaluator.evaluate` per detector config
- `scanner/rule_proposer.py` (produced 31 stale dangerous proposals) → `KillProposalGenerator` (LLM-gated via brain pipeline)
- `scanner/pattern_miner.py` `_build_summary` top_positive logic (labels −3.61% PnL cohort positive) → fix the WR-only metric

## What MUST be dispositioned before any switchover

- The 31 stale proposals in `proposed_rules.json`. Specifically dangerous: prop_005, prop_006 (kill BULL_PROXY entirely); prop_011, prop_012, prop_013 (kill UP_TRI entirely). Must be explicitly `/reject_rule`-ed BEFORE any 2.0 ApprovalHandler goes live, to prevent accidental approval propagation.

## 03.5 — Same repo vs new repo?

Two options:

**Option A: Branch in same repo (recommended)**

PRO:
- All git history preserved
- Easy to cherry-pick fixes between branches
- One PWA host (`tietiy.in` serves both via path namespace)
- Reuse existing GitHub Actions workflows with branch filters

CON:
- Mental gymnastics during dev (which branch am I on?)
- Risk of accidentally pushing 2.0 changes to main

**Option B: New repo (`tietiy-scanner-v2`)**

PRO:
- Clean break; impossible to accidentally affect 1.0
- New repo can have stricter discipline (pre-commit hooks, CI tests, branch protections)
- README/docs not littered with 1.0 history

CON:
- Lose git history
- Two GitHub Pages deploys
- Telegram bot has to route between repos
- More moving parts in cron-job.org dashboard

**Recommendation: Option A.** Lower risk; the git-discipline cost is real but manageable. The branch model has worked for the past 220 commits on `shadow_ops_v1` without disasters. Use the same discipline for `tietiy_2_0`.

## Summary timeline

| Phase | Weeks | Hours | What's deployable at end? |
|---|---|---:|---|
| 1 — Foundation | 1-2 | 50 | Registry skeleton; nothing user-visible |
| 2 — Detector port | 3-4 | 40 | 2.0 shadow matches 1.0 production on detectors |
| 3 — Brain/bridge adapter | 5 | 20 | 2.0 brain run = 1.0 brain run |
| 4 — UI | 6-7 | 28 | **New dashboard surfaces brain proposals (USER VALUE TODAY)** |
| 5 — Validation harness | 8-9 | 30 | First Bull detector passing backtest |
| 6 — New Bull detectors | 10-14 | 100 | 5 new detectors paper-validated |
| 7 — Live cutover | 15 | 20 | 2.0 = production |

**Total: ~14 weeks, ~290 hours.** Compared to the §08 of my feasibility report (480h total), this migration path is **leaner because it preserves brain/bridge wholesale** and ships the dashboard as Phase 4 (highest-leverage early win).

## What can go wrong

| Risk | Mitigation |
|---|---|
| 2.0 detectors diverge from 1.0 outputs | Phase 2 switchover requires 14-day byte-match; halt and fix if divergence detected |
| User approves a proposal that breaks 1.0 (dual-write hazard) | 2.0 ApprovalHandler writes to 2.0's mini_scanner_rules; 1.0 reads from 1.0's; isolated state during build |
| Phase 4 dashboard works but user still doesn't approve proposals | Dashboard build is the test; if user doesn't approve after dashboard is shipped, 2.0 doesn't help — pause the build |
| Phase 6 detectors fail validation | Don't deploy them. 2.0 launches with 3 ported detectors + whatever passed validation. The architecture supports it. |
| Phase 7 cutover regressions | Rollback via cron flip. 1.0 code remains on `main`. No data destruction. |

## Critical Phase 4 insight

**Phase 4 (dashboard wiring) can be done IN PARALLEL with Phase 1-3 work — and probably should be.** It's the only phase that delivers immediate user value (brain proposals become visible and actionable). If everything else slips, Phase 4 alone is worth the migration.

In fact, **Phase 4 could be done as a 1.0 PATCH** without any 2.0 architecture work. Just wire `output/brain/unified_proposals.json` into a new `proposals.html` page on the existing PWA host. ~24 hours of work. Closes the approval loop today without waiting for the full migration. **Strong recommendation: do Phase 4 as a 1.0 patch FIRST, regardless of the 2.0 decision.**
