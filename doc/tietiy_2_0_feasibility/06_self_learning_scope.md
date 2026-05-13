# 06 — Self-Learning Scope

## User's stated definition (verbatim)

> The system learns through human approval, not autonomous evolution.
> - Brain analyzes signal outcomes daily/weekly
> - Brain proposes rule changes
> - Proposals appear in dashboard for user review
> - User approves or rejects via Telegram or dashboard
> - Approved proposals are applied to live rules
> - System tracks proposal → approval → outcome chain
> - Self-evolves through accumulated human-approved adjustments
> - **NEVER auto-applies changes without human approval**

This is **closed-loop reinforcement through curated human approval**. Different from autonomous learning. Different from full RL. The system learns the human's preferences over time and proposes more of what the human approved, less of what the human rejected.

## Scope: what the brain CAN learn in 4-8 weeks

| Capability | Feasibility | Risk | Build hours |
|---|---|---|---:|
| **Rule parameter tuning** — propose threshold adjustments based on outcome data (e.g. "tighten UP_TRI Bear+Bank to require vol_confirm=True") | ✅ feasible | LOW | 12 (already mostly in `brain_reason.cohort_promotion_judge`) |
| **Cohort identification** — find UP_TRI×Sector subsets that under/over-perform vs cohort baseline | ✅ feasible | LOW | already shipped (cohort_health.json + brain_reason) |
| **Regime classifier calibration** — adjust regime thresholds based on per-state outcome distributions | ✅ feasible | MEDIUM (regime is load-bearing) | 16 |
| **V5 threshold calibration per regime** — McNemar-driven (per §04) | ✅ feasible | MEDIUM | 8 (logic exists in §04 design) |
| **Position sizing tier adjustment** — propose changes to risk_pct based on rolling Sharpe | ✅ feasible | MEDIUM | 12 |
| **Kill-rule promotion** — broaden kill_001 from Bank to Bank+Energy based on evidence | ✅ feasible | MEDIUM | already shipped (rule_proposer + brain dual-write) |
| **New signal type proposal** — brain suggests novel rule (e.g. "DOWN_TRI variant with X tweak") | ⚠️ RISKY | HIGH | 40+ (and probably wrong) |
| **Auto-adjustment of universe** — brain proposes adding/removing symbols based on per-symbol performance | ⚠️ RISKY | HIGH | 16 |
| **Backtest-self-validation** — brain runs a backtest on proposed rule before surfacing | ✅ feasible | LOW | 30+ (would consume API + compute) |
| **Outcome-tracking-loop closure** — brain measures the +30d post-approval performance of every approved change | ✅ feasible | LOW | 8 (per §05 `post_decision_metrics`) |

## Safe-to-auto-apply vs requires-approval vs never-auto-apply

| Class | Examples | Auto policy |
|---|---|---|
| **Auto-apply OK** | logging config changes, dashboard rendering tweaks, calibration metric recompute, daily cohort_health regeneration | yes |
| **Requires user approval** | rule parameter changes (e.g. threshold from 0.65 → 0.70); regime threshold changes; V5 threshold per regime; kill_pattern additions; boost_pattern promotions/demotions; cohort tier reassignments | yes — all flow through proposal queue |
| **Never auto-apply** | new signal type definitions; universe additions/removals; risk-per-trade percent changes; total-capital changes; minimum-position-size changes; data-source switches | no — manual rule-config edit only |

## What the brain SHOULD NOT learn in 4-8 weeks

1. **New signal types from scratch.** "Brain proposes a new entry pattern" is novelty generation. Vision LLMs do this poorly; deterministic miners overfit. **Defer to year 2+.** Until then, rely on human-defined signal types (the 5 L99-derived Bull setups + existing UP_TRI/BULL_PROXY) and let the brain tune their parameters.

2. **Cross-symbol arbitrage proposals.** "Sell Reliance when ONGC breaks support." Requires multi-leg execution + correlation modeling. Out of scope.

3. **Position-management proposals.** "Add to position on retest." Multi-leg sizing decisions are out of scope for a discretionary-trader system.

4. **Stop placement creativity.** Stops live in the signal definition; brain proposes parameter tweaks within the same family, not novel stop logic.

5. **Schedule changes.** When the scanner fires, what time of day. Operator control plane.

## How "self-learning" actually works in TIE TIY 2.0

**Day 1 of campaign:**
- 7 signal detectors live (5 new Bull + UP_TRI×Bear + BULL_PROXY×Bear, all gated by 7-state regime).
- Each detector has parameter defaults (the L99 spec values).
- V5 gate inactive (LOGGED ONLY) for first 60 days.
- Brain runs nightly, accumulates evidence.

**Days 7-30:**
- Each signal accumulates outcomes. Brain's `cohort_health.json` populates Wilson-bounded tiers.
- First brain proposals fire: "VCP × Sector_X has 90% WR n=8 — promote to Tier W when n≥10."
- User reviews, approves selectively (e.g., approves Auto sector; defers Bank).

**Days 30-60:**
- V5 gate accumulates 80+ paired decisions. McNemar test runs weekly.
- First V5 threshold proposal: "Stable-Bear V5 threshold should drop from 0.65 to 0.55 — V5 vetoes correlate with TIE TIY losses at p=0.03."
- User approves V5 threshold change for Bear only; defers Bull.

**Days 60-90:**
- Each approved proposal has its `post_decision_metrics` populated. Brain proposes demotion of approved changes that regressed.
- Trader sees "approved 23, rejected 11, demoted 2" — a real feedback loop.

**Day 90 onward:**
- The rule library is meaningfully different from Day 1. Each change has an audit trail. Each is reversible.
- The user has personally approved every adjustment; nothing changed without consent.

## Build effort for self-learning core

Most of the components exist (brain layer is shipped). The work is **integration + closure**:

| Component | Status | Hours to integrate |
|---|---|---:|
| Brain proposal generation | ✅ shipped | 0 (just needs production-fire) |
| Telegram approval | ✅ shipped | 0 |
| Dashboard approval surface | ❌ not built | 24 (per §05) |
| post_decision_metrics closure (+30d cohort recompute) | ❌ not built | 8 |
| Approval audit log expansion (decisions_journal richer schema) | partial | 4 |
| Brain proposal types beyond cohort_promotion/regime_alert/exposure_warn (e.g. threshold_tune) | partial | 16 |
| Calibration data storage (V5, regime, sizing) | partial | 8 |
| **Total** | | **~60 hours** |

## The trap to avoid

The user's pattern (per Round 2 §14 + spec): builds infrastructure (brain layer, shadow_ops_v1) faster than operates it. If TIE TIY 2.0 is built with elaborate self-learning machinery but the brain never fires in production, **the self-learning loop never closes**. The proposals expire silently. The user is no better off than today.

**Pre-condition for self-learning value: brain.yml must fire daily.** That requires the 3 cron-job.org entries and the GH secret. Without those, every hour spent on self-learning UI is wasted.

The recommended order:
1. (Day 0, 30 min) Complete brain production-fire user actions.
2. (Day 1-2, 24h) Dashboard wiring per §05.
3. (Day 3-7, 60h) Self-learning closure (post_decision_metrics, expanded proposal types).
4. (Week 2+) Build TIE TIY 2.0 rule library and signal detectors.

If step 1 doesn't happen, don't do steps 2-4.
