# A1 Rules Audit — Sonnet 4.5 LLM Critique

**Date:** 2026-05-03
**Model:** `claude-sonnet-4-5-20250929`

# Critical Review: A1 Rules Audit

## 1. Methodology Consistency Claim — The "0 Contradictions" Test

**The claim is mostly honest, but hides structural ambiguity.** The audit correctly identifies that there are no direct contradictions where identical feature × signal × regime contexts produce opposite verdicts. However, it sweeps real tension under the "regime-specific" rug. Example: `vol=High` is the *winning* tier in Bear UP_TRI (hot sub-regime, 65.8% WR) but an *anti-pattern* in Bull UP_TRI (-4.4pp edge destruction). These aren't contradictions because regime differs, but the audit doesn't acknowledge that this makes "vol=High" nearly meaningless as a standalone feature — it's regime-conditioned at the deepest level.

**The real missed conflict is directional.** Bear DOWN_TRI shows weak provisional evidence (Verdict A: kill_001 based on hostile sector counts), while Choppy DOWN_TRI shows strong CANDIDATE evidence (wk3 × breadth=med × vol=Med = +11.7pp, n=1295). Same signal type, different regimes, but the *mechanism* (mean-reversion in Choppy vs trend-continuation in Bear) is fundamentally opposed. The audit doesn't flag this because it doesn't test for **mechanistic contradictions** — cases where the same signal type requires opposite trading logic across regimes.

**Concrete action:** Step 3 (Opus) should explicitly document the *trading mechanism* for each rule (mean-reversion, breakout-continuation, regime-transition). If DOWN_TRI is mean-reversion in Choppy but trend-fade in Bear, those should be *different rule families* even if they share a signal name. The current audit passes consistency checks by not asking whether the underlying trade logic is coherent.

## 2. Universal Pattern Claim — Vol_Climax × BULL_PROXY Strength Variance

**This is NOT a universal pattern — it's two different patterns with a shared name.** The Bear case (-11pp, presumably high sample) shows strong anti-edge across the entire cell. The Bull case (-4.4pp) is weaker and context-dependent: the cell investigation showed vol_climax matters *only in late_bull sub-regime* where it destroys edge, but is neutral or slightly positive in recovery_bull and healthy_bull. The audit aggregates these into a single number, hiding critical sub-regime variation.

**The mechanistic stories are different.** In Bear, vol_climax × BULL_PROXY is anti because BULL_PROXY signals are contrarian mean-reversion plays in a downtrend — vol_climax means the knife is still falling. In Bull, vol_climax is anti *only in late_bull* because it signals distribution/exhaustion; in recovery_bull it may actually confirm momentum resumption. These are not the same phenomenon.

**Concrete action:** Reclassify this as "vol_climax × BULL_PROXY = REJECT *in Bear and late_bull*" rather than universal. The rule should explicitly check `sub_regime != recovery_bull AND sub_regime != healthy_bull` in Bull regime. If the schema can't support sub-regime conditionals (per question 3), this should be flagged as a **schema blocker** for Step 3, not handwaved as "universal with variance."

## 3. Schema Extension Scope — Field Explosion vs Runtime Compute

**Adding 6 new matchable fields is a design mistake.** The proposed schema (month, day_of_month_bucket, day_of_week, sub_regime, nifty_vol_regime, nifty_60d_return_bucket) conflates three different architectural layers: (1) static calendar features (month, day_of_week) that could be computed at rule-evaluation time, (2) market-state features (nifty_vol_regime, nifty_60d_return_bucket) that are runtime inputs from the scanner, and (3) *derived* features (sub_regime) that are **compositions** of other features (e.g., `recovery_bull = regime=Bull AND nifty_200d_return_bucket=low AND breadth_regime=improving`).

**The right architecture:** Calendar fields (month, day_of_week, day_of_month_bucket) should be runtime-computed helper functions, not schema fields — they're deterministic transforms of `signal_date`. Market-state fields (vol_regime, 60d_return_bucket) should be scanner outputs, passed as context. Sub-regime should be a **computed discriminator** at rule-evaluation time: the rule schema should support `conditions: [{nifty_200d_return_bucket: "low"}, {breadth_regime: "improving"}]` and the engine composes these into sub-regime detection. This keeps the schema stable while allowing arbitrary feature combinations.

**Concrete action:** Opus Step 3 should propose a **two-tier schema**: (1) `match_fields` = {signal, sector, regime, conviction_tag} (no expansion), and (2) `conditions` = array of feature-value pairs that must ALL be true (AND logic). This supports Bear UP_TRI cold cascade (`conditions: [{day_of_month_bucket: "wk4"}, {swing_high_bucket: "low"}]`) without adding `swing_high_bucket` as a top-level schema field. Calendar helpers become utility functions in the rule engine, not schema burden.

## 4. Priority Ranking — Sub-Regime Gating Misclassified as MEDIUM

**Priority ranking is upside-down.** The HIGH list focuses on *avoidance* rules (catastrophic cells, hostile sectors, bad calendar slots) — these prevent disasters but don't create edge. The MEDIUM list buries sub-regime gating (item 10: "late_bull = SKIP") even though the cell investigations show sub-regime is the *primary edge driver* in Bull regime: recovery_bull × vol=Med × fvg_low = 74% WR, while late_bull × same features = barely profitable. The delta between best and worst sub-regime (20-30pp WR swing) dwarfs the impact of sector filters (2-5pp).

**The miscalibration comes from focusing on catastrophe avoidance rather than edge capture.** HIGH priority should distinguish between *table-stakes hygiene* (don't trade Choppy BULL_PROXY ever, n=0 after filters) vs *active edge drivers* (sub-regime gating unlocks the 74% WR cells). Choppy BULL_PROXY KILL is important but has near-zero production impact if the cell never fired anyway. Sub-regime gating in Bull has massive production impact because Bull UP_TRI and BULL_PROXY are high-frequency cells.

**Concrete action:** Reframe priority as **Impact = Edge_Delta × Expected_Frequency**. Move sub-regime gating for Bull UP_TRI and BULL_PROXY to HIGH (recovery/healthy = TAKE, late = SKIP). Demote Choppy BULL_PROXY KILL to MEDIUM (it's a cleanup rule for a dead cell). Specifically: `recovery_bull` gating should be rule #1 or #2 — it's the difference between a 74% WR system and a 50% WR system in the most liquid regime.

## 5. Missing Gap Detection — Rule Conflict Resolution Absent

**The audit caught feature gaps but missed rule *interaction* gaps entirely.** Example from the audit's own findings: Bear UP_TRI has both (1) a cell-level boost for hot sub-regime (high confidence, 65.8% WR) and (2) a sector-level AVOID for Health sector (32.4% WR, hostile). What happens when a signal is `Bear × UP_TRI × hot sub-regime × Health sector`? The current production rules.json has no conflict resolution mechanism — does sector veto override sub-regime boost? Does sub-regime gate come first?

**The temporal interaction gap is worse.** Bear UP_TRI × Dec = catastrophic (-25pp). Bear UP_TRI × wk4 × swing_high=low = cold cascade boost (+13pp). December has a wk4. Does the monthly catastrophe override the weekly boost, or vice versa? The audit lists these as separate rules (HIGH priority #4 and MEDIUM priority #9) but doesn't specify evaluation order or boolean logic (AND? OR? hierarchical gating?).

**Concrete action:** Step 3 must define a **rule precedence model**. Recommended hierarchy: (1) REJECT/KILL rules fire first (entire-cell kills, vol_climax anti-patterns, catastrophic calendar), (2) sub-regime gating fires second (recovery/healthy/late, hot/warm/cold), (3) sector and calendar micro-adjustments fire last (Health AVOID, wk2/wk3 calendar filters). Each layer is AND-gated: a signal must pass all REJECT filters, match at least one sub-regime gate, and avoid sector/calendar vetos. The audit should include a **conflict matrix** showing all known overlaps and their resolution logic.

## 6. Step 3 Readiness — The Missing Piece is Rule Composition Examples

**The single most important missing element: worked examples of composite rule evaluation.** The audit provides 12 new rule recommendations and identifies schema gaps, but it doesn't show Opus *how a real signal would flow through the unified ruleset*. Step 3 will produce a rules.json with 20+ patterns (7 current + 12 new + schema expansion). Without end-to-end evaluation examples, Opus can't validate that the rules compose correctly or that the precedence model handles edge cases.

**Specifically missing:** A test case like "2024-03-15 (Friday, wk3, March), TCS (Tech sector), UP_TRI signal, regime=Bull, nifty_200d_return=low (recovery_bull), vol=Medium, breadth=Medium, fvg_percentile=25 (low)". Walk through: (1) does it pass REJECT filters (no vol_climax BULL_PROXY, not Choppy regime)? (2) does it match a sub-regime gate (recovery_bull × vol=Med × fvg_low = 74% WR hot cell)? (3) any sector/calendar vetos (Tech is neutral, March is neutral, wk3 is neutral, Friday is... wait, does the Choppy DOWN_TRI × Friday SKIP apply cross-regime? Audit doesn't say). Without this, Opus will write rules that pass schema validation but fail runtime coherence.

**Concrete action:** Audit should include **5 worked examples** representing the cross-product of (regime × signal × sub-regime). Each example should show: (1) raw signal features, (2) rule evaluation trace (which rules fired, in what order), (3) final verdict (TAKE_FULL / TAKE_HALF / SKIP / REJECT), (4) justification. These become Step 3's test vectors — Opus writes rules, then validates against the worked examples. This is the difference between "schema complete" and "system runnable."

## 7. Universal Patterns vs Cell-Specific — When Does Abstraction Fail?

**The universal-pattern framework starts failing when sub-regime axes are incommensurate.** The audit correctly identifies that all 9 cells have tri-modal sub-regime structure, but the axes differ: Choppy = vol × breadth, Bear = vol × 60d_return, Bull = 200d_return × breadth. This means "hot" sub-regime has no cross-regime meaning — Choppy hot = high vol + medium breadth, Bear hot = high vol + 60d_low, Bull hot = doesn't exist (Bull uses recovery/healthy/late on a different axis). Any rule that references "hot" is implicitly cell-specific despite using universal terminology.

**The calendar inversion pattern is similar.** The audit says "calendar inversion across direction" is universal (wk2/wk3 favor DOWN_TRI, wk1/wk4 favor UP_TRI in multiple regimes). But the *mechanism* isn't universal: in Bear, wk2/wk3 favor DOWN_TRI because they're institutional rebalancing windows (continuation). In Choppy, wk3 favors DOWN_TRI because it's a liquidity trough (mean-reversion). Treating these as the same pattern obscures that they require different invalidation conditions — if the Bear pattern breaks, it doesn't tell us anything about the Choppy pattern.

**When to abandon universal abstraction:** When the rule requires **regime-specific invalidation logic** or **mechanistic explanation** to be tradeable. Example: "vol=High is good in Bear UP_TRI hot but bad in Bull UP_TRI" can't be abstracted to "vol=High is good in hot sub-regimes" because Bull doesn't have a hot sub-regime, and even if it did, the mechanism (breakout continuation vs exhaustion) is opposite. The audit should flag rules that use universal vocabulary but require cell-specific runtime context.

**Concrete action:** Step 3 should create **two rule sets**: (1) *structural rules* that are truly universal (vol_climax × BULL_PROXY = anti, sub-regime tri-modal gating exists) and apply via shared logic, (2) *parametric rules* that follow universal *templates* but have cell-specific parameters (e.g., template = "sub_regime_gate(signal, regime, anchor_feature, tier_boundaries)" with Bear UP_TRI parameters = {anchor: 60d_return, tiers: [hot/warm/cold]}). The current audit conflates these, leading to false universality claims. If a rule needs a cell-specific lookup table, it's parametric, not structural — name it accordingly.
