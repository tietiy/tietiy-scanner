# L2 Schema Validation — Sonnet 4.5 Critique

**Date:** 2026-05-03

# L2 Schema Validation + v4.1 Design Review

## 1. Real Progress vs. Overfitting to Validation Harness

**The recalibration is partially legitimate, partially suspicious.** Rules like rule_007 (158→42 count) represent genuine sub-regime discoveries where initial predictions assumed broader applicability. Hot Bear UP_TRI Health is legitimately rare. Similarly, rule_020/022/025 corrections reflect Path 2's interpretive overreach being corrected by reality. These are valid learning-loop adjustments.

**However, you've crossed into overfitting territory.** When you set `predicted_match_count_min/max` to bands that perfectly envelope actual lifetime observations (e.g., rule_007: 42 actual, band 30-100), you've essentially encoded the test answer key into the schema. The validation harness now tests "does reality match reality?" rather than "do predictions generalize?" A honest v4.1 would have set bands *before* seeing lifetime data, or held out 20% of signals for true validation.

**The 100% PASS+WARN rate is a red flag, not a victory condition.** Production systems should maintain 10-15% ongoing uncertainty because markets evolve. Your schema now has zero predictive tension. When rule_011 suddenly drops from 1700 matches to 900 in Q3 due to regime shift, v4.1 will call that a failure when it's actually normal market adaptation. You've optimized for historical fit at the expense of forward robustness.

## 2. Schema v4.1 Sufficiency for Production

**The production-readiness fields are a good start but incomplete.** `production_ready`, `deferred_reason`, and `known_issue` add operational metadata that v4.0 lacked. The explicit tolerance bands solve the implicit-assumptions problem. But you're missing critical production concerns: (1) **rule precedence/conflict resolution** when multiple rules match the same signal (e.g., does rule_003's Bear filter override rule_023's broader Choppy logic?), (2) **deprecation lifecycle** tracking when rules are sunset vs. temporarily disabled, (3) **performance degradation triggers** that auto-flag rules when WR drops below tolerance for N consecutive weeks.

**Second-order metadata gaps will hurt you.** Where's the `last_calibration_date` field so operators know when predictions went stale? Where's `minimum_sample_size_for_validity` to prevent rules like win_007 (n=86) from being treated as statistically significant? You need `interaction_effects: [rule_ids]` to document which rules create portfolio concentration risk when they fire simultaneously. Schema v4.1 reads like "validation passed" rather than "production operated."

**The `source_evidence` field is underspecified.** "Lifetime baseline observation" doesn't distinguish between "observed in 12-month backtest" vs. "3 weeks of live trading." Production teams need `observation_period_start`, `observation_period_end`, and `sample_regime_distribution` (% Bull/Bear/Choppy) to assess whether the calibration data represents all market conditions or just the recent chop-fest.

## 3. Kill-Rules-Matching-Winners: Delete or Accept?

**rule_027's 66% WR on a SKIP rule is a smoking gun that demands investigation, not acceptance.** The Lab found Pharma×Choppy DOWN_TRI = -4.7pp anti-edge. Production data shows +16pp lift (66% vs. 50% base). Either (A) the rule logic inverted a filter (e.g., `sector == 'Pharma'` when it should be `!= 'Pharma'`), (B) Pharma's behavior regime-shifted between Lab analysis and production, or (C) the Lab finding was a small-sample fluke. You must reproduce the Lab analysis on the production-matched cohort before accepting this discrepancy.

**Accepting WARNING status creates institutional rot.** If teams learn that "kill rules matching winners" generates a shrug and a KNOWN_ISSUES.md entry, you'll accumulate technical debt where 15% of your ruleset has inverted logic that nobody investigates. The correct process: (1) **halt rule_027 in production immediately**, (2) re-run Lab analysis on the n=386 matched signals to see if Pharma×Choppy DOWN_TRI shows anti-edge *in this specific cohort*, (3) if Lab confirms +edge, flip the rule to a TAKE rule with revised predictions, (4) if Lab confirms anti-edge, delete as a logic bug.

**win_007's WARNING is less urgent but still problematic.** n=86 is borderline statistical significance (you need ~385 for ±5pp precision at 95% confidence). The WR is out-of-band but the sample is tiny. Rather than WARNING, the schema should have a `insufficient_sample_size` validation state that auto-disables rules until they hit minimum n. Letting low-n rules persist trains the team to ignore warnings.

## 4. Second-Order Production Risks in 30-Day Live Trading

**Regime overfitting will surface immediately.** Your recalibrations used "lifetime observation" data that—based on the rule_023 count of 4,954 and watch_001 at 27,260—likely spans a 6-12 month period heavily weighted toward the recent Choppy regime (your rules have Choppy overweights). When the market shifts to sustained Bull in weeks 2-4, rules like rule_022 (Choppy TAKE) will underfire (you predicted 700, might see 200), while rule_013 (likely Bull-exposed given the 3,719 count) will overfire. Your tolerance bands won't save you because they're centered on Choppy-regime means.

**Portfolio concentration risk is invisible to single-rule validation.** rule_021 (n=2,275), rule_023 (n=4,954), and watch_001 (n=27,260) fire frequently. If they share overlapping filter logic (e.g., all favor Tech sector + Choppy regime), you could have 60% of live signals coming from correlated rule clusters. A single adverse event (Tech selloff) will cause simultaneous drawdown across most of your book. The schema has no `correlation_cluster` or `max_portfolio_weight` fields to catch this.

**The "production_ready" boolean will be abused as a political tool.** When rule_018's WR drops from 39% to 30% in week 3 (variance happens), someone will flip `production_ready: false` with `deferred_reason: "underperforming"` rather than doing root-cause analysis. Six months later you'll have 12 rules in limbo with nobody owning the decision to delete vs. rehabilitate. You need a `review_date` field and a forcing function that auto-escalates deferred rules to monthly review meetings. Otherwise v4.1 becomes a JIRA graveyard for rules teams don't want to formally kill.
