# Step 4 Methodology — Sonnet 4.5 Final Critique

**Date:** 2026-05-03
**Model:** `claude-sonnet-4-5-20250929`

# Step 4 Dual-Opus Methodology Comparison — Critique

## 1. Headline verdict on methodology

**The "Disciplined wins" conclusion is premature.** The 8.6pp gap (66.7% vs 58.1% PASS+WARN) is real but modest, and the merged set's +0.9pp advantage over Path 1 suggests both paths contributed meaningfully. More importantly, Path 2 caught a critical bug (kill_001) and surfaced 4 net-new rules that Path 1 missed entirely. This is not a clean win for constraints—it's evidence that both approaches have complementary strengths.

**The choice should be context-dependent, not a blanket default.** Use Disciplined (Path 1) when you have well-understood requirements and want predictable schema adherence. Use Trust-Opus (Path 2) for discovery, bug-catching, and surfacing edge cases from ambiguous source material. The fact that Path 2 generated 22 rules vs Path 1's 18, and caught the regime=None literalism bug, indicates higher recall at the cost of precision.

**Concrete action:** Don't pick one. Establish a two-stage protocol: (1) Disciplined pass for core synthesis, (2) Trust-Opus QA pass with explicit instructions to "find bugs, edge cases, and gaps in the Disciplined output." Budget $10 per major synthesis iteration (~$5 each). The methodology lesson is that Opus benefits from role diversity, not prompt monoculture.

## 2. Structural ceiling at 77%

**Close Step 4 now without inline recalibration.** The win_* prediction issue is mechanical and well-understood—live small-sample WR (90-100%) diverged from lifetime (53-60%). Fixing it manually would be non-trivial busywork (touching 6 rules, re-validating, re-merging) that belongs in a dedicated prediction-calibration workstream, not shoehorned into a prompt methodology comparison. Step 4's mandate was to evaluate Opus approaches, and that's complete.

**Document the ceiling explicitly and defer the fix.** Add a "Known Limitations" section to the Step 4 deliverable: "6 win_* rules fail validation due to prediction calibration mismatch (live 90-100% vs lifetime 53-60%). Fixing this is a ~5-minute manual edit that would lift PASS+WARN from 67.6% to ~80%, but is out of scope for prompt methodology evaluation." This makes the issue visible without scope creep.

**Concrete action:** Mark Step 4 complete. If Step 5 requires higher validation pass rates for schema finalization, fix win_* predictions at the *start* of Step 5 as a pre-processing task, not retroactively in Step 4. The current 67.6% is good enough to assess whether the merged rule set's *structure* is sound, which is what Step 5 needs.

## 3. Path 2's bug-catching value

**This is a systematic pattern, not a one-time win.** The kill_001 bug (regime=None literal preservation) is a classic case of constrained systems over-indexing on explicit instructions and missing semantic intent. Path 2, with freedom to reinterpret, caught this because it wasn't anchored to the existing rule's literal phrasing. This is precisely the failure mode that QA processes are designed to catch—when the "correct" implementation of instructions produces wrong results.

**The value is high but intermittent.** You won't see bug-catching wins in every iteration, but when you do, they're high-impact (kill_001 affected 3,695 trades vs the intended 653). The $5 cost of a Trust-Opus QA pass is cheap insurance against subtle semantic bugs that slip through rigid constraint-following. Path 2 also surfaced rule_020 (Bull DOWN late_bull × wk3) that Path 1 entirely missed—this is breadth discovery, another systematic win.

**Concrete action:** Institutionalize Trust-Opus as a QA stage. After any Disciplined synthesis run, execute a second Opus call with the prompt: "Review the attached rule set for bugs, semantic mismatches, and gaps. You have freedom to reinterpret source material. Flag issues and propose fixes." Budget 1 hour of human review to triage Path 2's output. This doubles Opus cost per iteration but catches bugs that would otherwise require expensive downstream firefighting.

## 4. Merge complexity

**Deploy all 37 rules with overlap; do not deduplicate.** The overlap you describe (recovery_bull broad vs recovery_bull × vol=Med × fvg<2) is feature hierarchy, not duplication. Broad rules capture general patterns; narrow rules capture high-confidence refinements. Removing either loses information: the broad rule misses the vol/fvg lift, the narrow rule misses trades outside its specificity. Production systems should evaluate all applicable rules and let confidence scoring or ensemble logic handle overlap.

**Aggressive deduplication (37 → 25) is premature optimization.** You're at 67.6% validation pass rate with known issues (win_* calibration). Cutting 12 rules now—before Step 5 schema finalization and Step 6 backtesting—risks discarding valuable signal. Deduplication should happen *after* you have production performance data showing that specific rules are redundant or harmful, not based on pre-deployment intuition about "too many rules."

**Concrete action:** Proceed to Step 5 with all 37 rules. Add a `rule_specificity` field to the schema (values: `broad`, `refined`, `niche`) and tag the hierarchy explicitly. In Step 6 backtesting, measure whether refined rules actually outperform their broad counterparts on holdout data. If they don't, *then* consider pruning. Premature deduplication is premature optimization.

## 5. $10 spend justification

**The $5 marginal cost for Path 2 was absolutely worth it.** You gained: (1) a critical bug fix (kill_001), (2) 4 net-new rules including a high-lift discovery (rule_020 +21.8pp), (3) concrete evidence that Trust-Opus has systematic bug-catching value, and (4) a reusable two-path methodology for future iterations. The +0.9pp PASS+WARN improvement on the merged set is the *least* valuable outcome—the real wins are qualitative (bugs, breadth) not quantitative (validation metrics).

**Single-path Disciplined runs would be a false economy.** You'd save $5 per iteration but lose the QA safety net and discovery breadth. The kill_001 bug alone could have cost hours of debugging in production if it slipped through. The rule_020 miss would have left a high-value pattern undiscovered. Spending $5 to avoid these failure modes is a bargain.

**Concrete action:** Make dual-path runs the default for major synthesis iterations (Steps 4, 7, 10, etc.) where source material is ambiguous or rule sets are being substantially revised. For minor iterations (tweaks, single-rule additions), a single Disciplined path is fine. Update the methodology playbook to reflect this: "Budget $10 per major synthesis: $5 Disciplined (core), $5 Trust-Opus (QA + discovery)."

## 6. Step 5 readiness

**The merged set is ready for Step 5 with documented caveats.** Step 5's mandate is schema and barcode finalization—ensuring the rule structure is production-ready, not that every rule passes validation perfectly. The 12 FAIL rules break down into two categories: (1) 6 win_* rules with known prediction calibration issues (fixable mechanically), and (2) 6 rules with structural issues (bucket labels, prediction bands, calendar specificity). The first category is deferred work; the second provides valuable signal about schema robustness.

**The FAILs are features, not bugs, for Step 5.** Schema finalization *should* stress-test against rules that fail validation—these reveal where the schema is brittle (e.g., bucket label matching in rule_010) or where prediction bands are too strict (rule_007, rule_011). Fixing the schema to accommodate these edge cases makes it more robust for future rule synthesis. Deferring them to "after Step 5" would hide this signal.

**Concrete action:** Proceed to Step 5 immediately. Create a `KNOWN_ISSUES.md` document listing the 12 FAIL rules with one-line explanations (e.g., "win_001-006: prediction calibration mismatch, fix in Step 5 pre-processing"). Use these failures as test cases for schema refinement. If Step 5 schema changes fix 4-6 of the structural FAILs organically (e.g., by loosening prediction band logic), you'll hit the ~80% ceiling without manual intervention.

## 7. Cumulative spend trajectory

**$15.23 for Steps 1-4 is excellent value.** You've delivered: (1) a validated 37-rule set at 67.6% PASS+WARN with a clear path to ~80%, (2) a reusable dual-Opus methodology with documented tradeoffs, (3) specific findings on Disciplined vs Trust-Opus prompting, and (4) identification of structural issues (win_* calibration, bucket label matching) that would have caused production bugs. This is production-ready infrastructure, not exploratory research.

**The $20 total budget is appropriate; do not artificially cap spending.** If Steps 5-6 require additional Opus calls to finalize schema or debug edge cases, spend the money. The marginal value of a robust, well-tested rule synthesis pipeline far exceeds the $5-10 you'd "save" by cutting corners. The Step 3 projection of <$20 total appears achievable if Step 5 is light (schema formalization, no heavy synthesis) and Step 6 is validation-only (no Opus calls).

**Concrete action:** Authorize up to $25 total spend for Steps 1-6, with explicit approval required to exceed that. Current trajectory ($15.23 through Step 4, likely $3-5 for Steps 5-6) keeps you well under budget. If you hit $20 before Step 6 completion, pause and assess whether remaining work justifies additional spend—but based on value delivered so far, the answer will almost certainly be yes. Document spend and value at each step to justify any future budget requests.
