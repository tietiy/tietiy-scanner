# 07 — Sequencing Recommendation

The honest answer: **don't do Option A or D**.

## Why Option A (big-bang design then big-bang build) fails

12-16 weeks of build with nothing user-visible until the end. The user's documented pattern is "builds infrastructure faster than operates it." A 12-week build without user-touchable deliverables until week 12 maximizes the risk of joining the brain / shadow_ops / foundation-backtest / nuvama-vision pile of "well-built, never operated."

## Why Option D (different sequencing) is the recommendation

**Recommended sequencing: Option C-Modified — ship the dashboard as a 1.0 patch in Week 1, then incrementally migrate to 2.0.**

The single highest-ROI work in the entire TIE TIY 2.0 program is **wiring the dashboard to surface brain proposals**. This:
- Closes the approval loop that's been open since 2026-04-29
- Captures ~60% of the visible value of TIE TIY 2.0
- Takes ~28 hours of work (1 week)
- Doesn't require any 2.0 architecture
- Is a strict refinement to 1.0; 2.0 inherits it later

## The four-phase sequence

### Phase 1 — Approval-loop closure (Week 1, ~28 hours) 🔥 HIGHEST PRIORITY

**What:** Ship the ProposalCard + ExposureCard on the 1.0 PWA (per §04 Phase 1). NOT as TIE TIY 2.0 — as a patch to the current scanner.

**Why:** The brain has been generating 3 PENDING proposals every night for 14 days. Surfacing them in a clickable dashboard with Approve/Reject deep-links to Telegram closes the loop. The infrastructure already exists; only the UI render is missing.

**Acceptance test:** Within 14 days of the dashboard shipping, the user makes ≥10 approval decisions (approved or rejected, NOT deferred or expired) across the proposal types.

**Branch:** Patch on `main`. No 2.0 work required.

**This phase is non-negotiable.** If the user cannot close the approval loop with the dashboard available, then 2.0 won't help either. The discipline is the gate, not the architecture.

### Phase 2 — Path A surgical fixes (Week 2, ~12 hours)

**What:**
- `/reject_rule prop_005 prop_006 prop_011 prop_012 prop_013` (kill dangerous broad-scope proposals; 5 minutes via Telegram)
- Patch `pattern_miner._build_summary` so `top_positive` requires `avg_pnl > 0` (5 LOC)
- Add `kill_002` for broad DOWN_TRI sector=null in `mini_scanner_rules.json` (1 JSON entry)
- Add `Bull` regime label to `main.py:get_nifty_info()` (~10 LOC)
- Add `Target2x` exit rule for BULL_PROXY in `scorer.py:get_exit_rule()` (1 LOC)
- Activate `watch_002` for documented loss cohorts (1 JSON entry)

**Why:** These are the smallest possible fixes that move WR / max-DD / proposal-safety. Each is reversible in 1 commit. Total ~12 hours.

**Branch:** Patches on `main`.

### Phase 3 — Discipline observation window (Weeks 3-6, ~0 hours of dev)

**What:** No build. The user OPERATES the existing scanner + the new dashboard. Reviews brain proposals nightly. Approves or rejects within 24 hours of brain run. The shadow_ops_v1 campaign can be bootstrapped here as a discipline test (per §02 of prior feasibility) — though even without that, the operational test happens on the live scanner.

**Why:** This is the gate to 2.0. If the user CAN maintain operational discipline on 1.0 for 4 weeks, then 2.0 has a chance of being operationalized when it ships. If the user CANNOT, the next 12 weeks of 2.0 work are wasted.

**Acceptance criterion to enter Phase 4:** Across the 4 weeks of Phase 3, the user has:
- Reviewed ≥80% of brain digests
- Made approval decisions on ≥80% of pending proposals (not letting them expire)
- Tracked ≥1 approved proposal's +30d outcome

If yes: proceed to Phase 4. If no: TIE TIY 2.0 is paused indefinitely. Focus shifts to operational habit-building or external constraints.

### Phase 4 — TIE TIY 2.0 incremental build (Weeks 7-20, ~290 hours)

If Phase 3 passes, begin 2.0 build per the §03 migration path:

| Sub-phase | Weeks | Hours | Deliverable |
|---|---|---:|---|
| 4.1 Foundation (core/, registry, contracts) | 7-8 | 50 | Empty registry boots; tests pass |
| 4.2 Detector port (UP_TRI, BULL_PROXY, rule_019) | 9-10 | 40 | 2.0 shadow output = 1.0 production output (14-day byte match) |
| 4.3 Brain + bridge adapters | 11 | 20 | Brain/bridge work unchanged via wrapper |
| 4.4 Dashboard migration from 1.0 patch to 2.0 PWA | 12-13 | 40 | Dashboard runs on `tietiy.in/v2/` with full card set |
| 4.5 Backtest harness generalization | 14-15 | 48 | Harness accepts any SignalDetector plug-in |
| 4.6 First new Bull detector (EMA20 pullback) | 16 | 8 build + 4w paper concurrent | Detector passing backtest |
| 4.7 Additional Bull detectors (VCP, Bull flag, Darvas, Cup-handle) parallel build | 17-20 | 58 | All 5 detectors paper-validated or in flight |
| 4.8 Live cutover (1.0 retired, 2.0 = main) | 20 | 20 | TIE TIY 2.0 in production |

**End-state at Week 20:** 2.0 is production. UP_TRI×Bear + BULL_PROXY×Bear + rule_019 are full-live. EMA20 pullback is small-live. VCP + Bull flag + Darvas + Cup-handle are paper or shadow.

## Total clock time

| Path | Time-to-first-value | Time-to-deployable-2.0 |
|---|---:|---:|
| Recommended (C-Modified) | 1 week | 20 weeks |
| Option A (big-bang) | 12 weeks | 12-16 weeks |
| Option B (incremental fixes only, no 2.0) | 1 week | n/a — never builds 2.0 |
| Option D (other) | various | various |

The recommended path takes longer in total (20 weeks vs 12-16) but delivers value at week 1 and provides a discipline gate at week 6 that protects the 14-week 2.0 investment.

## What this sequencing optimizes for

1. **Minimizing wasted infrastructure work.** Phase 3's discipline check prevents 290 hours of 2.0 build if the user cannot operate the simpler 1.0 + dashboard. Phase 3 is the cheapest possible insurance.

2. **Front-loading user value.** Week 1 = approval loop closes. The user sees brain proposals daily, approves/rejects, sees outcomes at +30d. The scanner becomes meaningfully more useful immediately.

3. **Preserving 1.0 throughout.** 1.0 keeps running and trading. 2.0 is built in parallel. No "stop trading for 4 months" cost.

4. **Honest gating.** The phase transitions have measurable acceptance criteria. Not "the team feels ready" — quantitative checks. Phase 2 → 3 = patches deployed. Phase 3 → 4 = user approval discipline demonstrated.

## What if Phase 3 fails (user doesn't close the approval loop)?

Honest possibilities:

1. **Dashboard isn't actually surfacing things well.** Iterate the dashboard. ~16h. Re-test.
2. **Proposals aren't actionable enough for the user.** Brain needs richer evidence. ~24h to expand evidence_refs in proposals.
3. **User has other priorities (income pressure, life events).** Pause 2.0 build entirely. Don't sunk-cost.
4. **The approval discipline is structurally hard for this user.** Consider: do they actually want a self-learning system, or just better signals? If the latter, the approach is different — make the brain auto-apply low-risk proposals and bring high-risk ones to a weekly review. **This is a fundamental design pivot;** the user's prior "never auto-apply" stance would need to relax.

**Phase 3 is a discovery phase, not a passive observation.** Learning that the user can't or won't run the loop is valuable; it changes the architecture decisively.

## What I'd say to the user verbatim

The biggest thing you can do this week is wire your dashboard to your brain. Your brain has been producing the right proposals for 14 days; you just haven't seen them. The proposals are: approve `boost UP_TRI×Bear`, approve `boost UP_TRI×Metal`, decide on the 100% Choppy exposure warning. Once you can see them in your PWA with Approve/Reject buttons, you make decisions. The infrastructure to support those decisions already exists.

Don't build TIE TIY 2.0 yet. Build the dashboard patch (1 week), do the 6 surgical fixes (1 week), then operate for 4 weeks. If at the end of that month you're reviewing 80% of nightly digests and making decisions, then TIE TIY 2.0 is worth the 14-week investment. If not, the architecture isn't the problem — pivoting away from the "approve-every-change" model is. Either way you learn something concrete.

The current scanner trades. The brain reasons. The bridge composes. The dashboard is missing. Build that. Then operate. Then decide on 2.0.
