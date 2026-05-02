# SY Synthesis — Sonnet 4.5 Final Critique (Step 3 Readiness)

**Date:** 2026-05-03
**Model:** `claude-sonnet-4-5-20250929`
**Context:** Critique of Step 1.5 + Step 2 output package before Opus rule synthesis

# FINAL Critical Review — Step 3 Readiness

## 1. Step 3 Readiness Verification

**Missing production scenario: regime transition day handling.** The 5 worked examples all assume stable regime state. But your scanner runs daily, and regime flips happen mid-week. What does the scanner output on transition days? Does it use old-regime rules until EOD, or new-regime rules immediately? If a Bear→Bull flip happens Tuesday and Bull cell rules say "SKIP late_bull," but it's first-Bull-day (unknown sub-regime), what's the fallback behavior? This is a gap.

**Worked examples lack DOWN_TRI depth.** You have 1 Bear DOWN example (calendar filter), 0 Choppy DOWN examples with the new 3-axis detector, and 0 Bull DOWN examples despite Bull DOWN_TRI late_bull × wk3 being your strongest Bull cell. Opus will be guessing at how DOWN_TRI sub-regime interactions compose. Add 2-3 DOWN_TRI worked examples spanning all 3 regimes before Step 3.

**Input package is otherwise complete.** The 9 playbooks + synthesis docs + schema + precedence model + WR calibration table covers structural needs. But operational ambiguity around transition-day logic and DOWN_TRI underspecification will cause Opus to either (a) make assumptions you'll need to rework, or (b) ask clarifying questions that delay Step 3. Author the missing examples now.

## 2. B1 vs B2 Conflict Resolution

**Ship B1 (5-tier display), defer B2 (sigmoid).** B1's finding is operationally complete: you have 4 labeled tiers (baseline/cold/hot/boundary_hot) with calibrated WR for each, and production scanner can directly map stress percentile → tier → verdict. B2's sigmoid requires additional calibration: where are the inflection points, how steep is the curve, and how do you discretize continuous sigmoid output back into TAKE/SKIP/AVOID? That's future work.

**B2's value is in continuous features you don't yet have.** Sigmoid shines when input features are continuous (stress = 0.0–1.0) and you want smooth probability curves. Your current scanner uses percentile buckets (cold/baseline/hot). If you later add continuous stress metrics or want probabilistic confidence scores, revisit B2. For now, tiered thresholds match your existing architecture.

**Concrete action:** Implement B1's 4-tier Bear UP_TRI rules (baseline → cold → hot → boundary_hot) in Step 3. Document B2's sigmoid approach as a "Phase 2 enhancement" for when you add continuous feature support or probabilistic output mode. This keeps Step 3 shippable without blocking future flexibility.

## 3. C1 + C3 Sequencing

**Ship together, but apply hysteresis to composite sub-regime, not per-axis.** If you add momentum (C1) without hysteresis (C3), you'll 3x your whipsaw problem before solving it—operationally backwards. But hysteresis per-axis (vol needs 2 confirming days, breadth needs 2 confirming days, momentum needs 2 confirming days) creates lag hell: a true regime shift could take 6 days to fully recognize.

**Composite hysteresis logic:** Compute the 3-axis sub-regime label (e.g., "vol=High × breadth=Low × momentum=Positive" → sub-regime X). Require 2 consecutive days of *the same composite label* before officially entering that sub-regime. This keeps lag at 2 days max while stabilizing the 27-cell space. Your whipsaw data shows 38% of episodes are 1-day duration—N=2 composite hysteresis eliminates those entirely.

**State implications:** You're adding statefulness either way (C3 requires yesterday's sub-regime). Composite hysteresis needs 1 state variable: `previous_subregime_label`. Per-axis hysteresis needs 3 state variables plus composition logic. Composite is simpler. Initialize state as `NULL` on first scan or regime change; use `NULL → confirmed` logic to handle bootstrap (first 2 days in a regime are "provisional" verdicts, lower confidence).

**Concrete action:** Step 3 ships both C1 (3-axis Choppy) and C3 (N=2 composite hysteresis) together. Schema includes `requires_confirmation: true` flag on Choppy rules. Scanner maintains `last_subregime_label` state variable. On regime flip, reset state to `NULL` and apply conservative fallback rules (baseline Choppy verdicts) until 2-day confirmation.

## 4. Rule Precedence Model Sufficiency

**The 4-layer hierarchy is insufficient—you need interaction resolution.** KILL > sub-regime > sector/calendar > override defines *priority*, but not *composition*. Example: Bear UP_TRI hot says TAKE_HALF (60% WR), Health AVOID says SKIP (35% WR). Both match. Does KILL-class Health AVOID override everything? Or does sub-regime hot "upgrade" the verdict? Your current spec is ambiguous.

**Two missing pieces:** (1) Within-layer conflicts (two sub-regime rules match—which wins?), and (2) Cross-layer composition (sub-regime says TAKE_HALF, calendar filter says SKIP—output?). You need explicit logic: "KILL-class rules are absolute, they terminate evaluation" vs "Rules compose via pessimistic merge (TAKE + SKIP → SKIP, TAKE_HALF + AVOID → AVOID)" vs "Last-match-wins."

**Recommended model:** **Pessimistic composition with KILL termination.** Evaluation order: (1) Check KILL rules first—if any match, output that verdict and stop. (2) Evaluate sub-regime, sector, calendar, override rules in parallel; collect all matching verdicts. (3) Output the most conservative verdict from the set (AVOID > SKIP > TAKE_HALF > TAKE_FULL). This prevents a weak calendar boost from overriding a strong sub-regime AVOID, and keeps trader expectations conservative (no false confidence).

**Concrete action:** Step 3 docs must include explicit composition logic with 3 worked conflict examples (e.g., Bear UP_TRI boundary_hot TAKE_HALF + Health AVOID → AVOID; Bull recovery TAKE_FULL + late_bull SKIP → SKIP; Choppy breadth=Low SKIP + Feb SKIP → SKIP [idempotent]). Opus encodes composition logic in rule evaluator, not per-rule.

## 5. Trade Mechanism Annotation Scope

**Annotate per-cell, not per-rule.** Trade mechanism (mean-reversion / breakout-continuation / regime-transition) is a cell-level property: Bear UP_TRI is *always* mean-reversion (buying stress dips), Bull UP_TRI recovery is *always* breakout-continuation, Choppy UP_TRI is *always* regime-transition (anticipating breakout). Sector or calendar filters don't change the underlying mechanism—they modulate *confidence* within the same mechanism.

**Per-rule annotation creates redundancy and drift risk.** If you annotate "mean_reversion" on 15 different Bear UP_TRI rules (hot, boundary_hot, Dec, wk2, Utilities, etc.), you're maintaining 15 copies of the same conceptual tag. When you later refine mechanism taxonomy (e.g., split mean-reversion into "bear-rally-fade" vs "support-bounce"), you have to update 15 rules. Per-cell annotation means 9 cells × 3 mechanisms = ~20 tags total, centralized.

**Implementation:** `parametric_cells.json` includes `trade_mechanism` field per cell. Example: `{cell: "Bear_UP_TRI", mechanism: "mean_reversion", sub_mechanisms: ["stress_dip_fade", "multi_day_decline_bounce"]}`. Individual rules inherit mechanism from parent cell. If a rule *changes* mechanism (rare—maybe Choppy UP_TRI + breadth=High becomes "false_breakout" instead of "regime_anticipation"), override at rule level, but make it explicit and documented.

**Concrete action:** Opus outputs `trade_mechanism` metadata in `parametric_cells.json`, one per cell. `structural_rules.json` references cell mechanism but doesn't duplicate it. Step 3 docs include mechanism taxonomy (4-6 core types) with trader-facing descriptions ("mean reversion: fade stress spikes; expect 2-5 day hold, exit on relief").

## 6. Schema Versioning and Migration

**Breaking change is safer than forward-compat here.** Your v3 schema is 9 flat `boost_patterns`. New 2-tier schema is fundamentally different: `match_fields` + `conditions` arrays + parametric cells. Forward-compat would require the new evaluator to parse both formats, adding complexity and bug surface. You're also only at 9 rules—migration cost is low. Clean break is better.

**Migration path:** (1) Step 3 outputs new schema (v4) in separate files (`structural_rules_v4.json`, `parametric_cells_v4.json`). (2) Run parallel evaluation for 2 weeks: scanner loads both v3 and v4 rules, computes verdicts from both, logs discrepancies. (3) If v4 discrepancy rate < 5% and WR delta < 3pp, cut over to v4 and archive v3. (4) If discrepancies are high, debug before cutover. Parallel mode de-risks deployment without blocking Step 3.

**Version the evaluator, not the rules.** `mini_scanner_rules.json` gains a top-level `schema_version: 4` field. Evaluator checks version and dispatches to correct parser. This keeps rule files clean and makes future v4→v5 transitions explicit. Opus includes version check logic in Step 3 reference implementation.

**Concrete action:** Step 3 outputs v4 schema files with `schema_version: 4` header. Scanner implements parallel-evaluation mode (v3 + v4) with discrepancy logging. Cutover after 2-week validation window. No attempt at forward-compat—clean break, validated transition.

## 7. Production Capacity vs Lab Fidelity

**Prune to HIGH + MEDIUM rules only for initial Step 3 ship.** Going 9 → 70 rules is too big a jump; you'll spend months debugging interactions instead of validating core findings. Your own priority ranking shows 10 HIGH+MEDIUM rules. Ship those first (9 old + 10 new = 19 total rules, 2x growth). This captures 80% of edge (sub-regime drivers + universal hygiene) at 25% of complexity cost.

**LOW-priority rules ship in Step 4 after Step 3 validation.** Rules 11-14 (sector micro-rules, day-of-week patterns) have narrow applicability and lower WR lift. Validate that Step 3's HIGH+MEDIUM rules don't *conflict* with production reality first (e.g., does Bear UP_TRI boundary_hot actually hold 71.5% WR live, or was it backtest overfitting?). Once core rules prove robust for 4-6 weeks, add LOW-tier rules incrementally.

**Operational safety valve: confidence thresholds.** Even with 19 rules, you could get 5+ rules matching on a single scan (Bear UP_TRI + hot + boundary + Utilities + wk2). Implement a "max rules per verdict" cap (e.g., display top 3 matching rules ranked by WR) to keep trader UI digestible. This also surfaces if rule interactions are creating weird compositions (e.g., 8 rules all match but produce conflicting verdicts—flag for review).

**Concrete action:** Step 3 outputs all ~14 new rules, but tags 11-14 as `production_ready: false`. Initial deployment includes only HIGH+MEDIUM rules (10 new + 9 existing). LOW-tier rules undergo additional live validation in paper-trading mode before promotion. Expect Step 4 (incremental rule additions) 6-8 weeks after Step 3 ships.

## 8. Worked Examples Coverage Gap

**Author 4 additional worked examples before Step 3.** Your list is exactly right: (1) Bull DOWN_TRI late_bull × wk3 (strongest Bull DOWN combo), (2) Bear DOWN_TRI calendar filter (your only Bear DOWN spec), (3) Choppy DOWN_TRI 3-axis (tests new momentum axis + hysteresis), (4) Bull regime activation day (first-day bootstrap when sub-regime unknown). These cover the major gaps: DOWN_TRI composition, new Choppy logic, and transition-day handling.

**Format for new examples:** Match existing structure: scenario setup (regime, signal, feature values) → rule matching process (which rules evaluate, which match, precedence resolution) → final verdict + confidence → expected WR + trade mechanism + exit logic. Each example should demonstrate at least one potential conflict or edge case (e.g., Bull DOWN late_bull × wk3: does late_bull SKIP override wk3 boost, or vice versa?).

**Why 4 examples matter more than 10 rules:** Worked examples encode *system behavior* (how rules compose, how conflicts resolve, how edge cases fall back). Rules encode *individual decisions*. Opus will use examples to validate that its rule synthesis produces the intended system behavior. Insufficient examples → Opus makes reasonable-seeming choices that violate your implicit intentions → you spend Step 4 fixing emergent bugs. 4 examples now saves 2 weeks later.

**Concrete action:** Author 4 worked examples (Bull DOWN late_bull × wk3, Bear DOWN calendar, Choppy DOWN 3-axis + hysteresis, Bull first-day bootstrap) before Step 3. Each example ~1 page, follows existing template. Add to input package as `worked_examples_supplement.md`. Opus uses all 9 examples (5 existing + 4 new) to validate rule synthesis and composition logic.

---

## Summary Recommendation: Step 3 IS NOT YET READY

**Three blockers must resolve first:**

1. **Author 4 missing worked examples** (Bull DOWN, Bear DOWN, Choppy DOWN, transition-day). 2-3 hours of work, prevents weeks of rework.
2. **Define explicit rule composition logic** (pessimistic merge + KILL termination, with 3 conflict examples). Required for Opus to generate correct evaluator.
3. **Decide C1+C3 sequencing** (ship together with composite hysteresis, or defer C1 to Step 4). Changes schema and state requirements.

**Two important clarifications:**

4. **B1 vs B2:** Ship B1 (tiered display), document B2 as future enhancement.
5. **Pruning strategy:** Step 3 outputs all 14 rules but marks 11-14 as `production_ready: false`; initial ship is HIGH+MEDIUM only (10 new rules).

**Three process improvements:**

6. **Schema migration:** Breaking change (v3 → v4), 2-week parallel validation, clean cutover.
7. **Trade mechanism annotation:** Per-cell in `parametric_cells.json`, not per-rule.
8. **Precedence + composition:** 4-layer hierarchy + pessimistic composition + explicit conflict examples.

**Estimated time to Step 3 ready:** 4-6 hours (examples + composition spec + sequencing decision). Then Step 3 can run with full context and produce shippable output. Rushing Step 3 now will create technical debt that costs more to fix than the 4 hours of prep work.
