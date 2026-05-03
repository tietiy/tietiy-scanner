# Independent Diagnosis

## TL;DR

You've correctly named one symptom (data-starvation) but missed the deeper diagnosis. The system has at least four distinct problems, only one of which is data-starvation. The others are: **circular validation, methodology overfit, complexity-without-evidence, and a documented winner→loser inversion that you've rationalized as "honest calibration."**

I don't agree with the data-starvation framing as the *primary* problem. I'll explain.

---

## The four diagnoses, ranked by severity

### 1. Circular validation (CRITICAL, under-acknowledged)

The honest caveat in file 06 says: *"Rules were derived in Lab steps 1-5 partly from this same April 2026 data."* Then you backtest those rules on April 2026 data and report 93.3% TAKE WR with +31.7pp lift. **This is not a backtest. It is a memorization check.**

Your defense is Path B (broader academic universe, same window). But Path B is the same window. Same regime. Same volatility cluster. The 2.1pp Δ between Path A and Path B does not establish generalization — it establishes that within a single hot-Bear window, the rule mechanism doesn't depend much on the production filter. That is a much weaker claim than "rules generalize."

The lifetime data is the only actual out-of-sample evidence, and the Lab synthesized rules *from* that lifetime data. There is no held-out set. There is no walk-forward. There is no real out-of-sample anywhere in this pipeline.

**This is the single biggest risk and you are not treating it as such.**

### 2. The win_003/win_005 anomaly is being papered over

Read your own data carefully:
- `win_003` (IT × Bear UP_TRI): Path A 100% (n=13) vs Path B 72% (n=25). **Path B is 12 additional signals at 58.3% WR.**
- `win_005` (Pharma × Bear UP_TRI): Path A 100% (n=2) vs Path B 67% (n=6). **Path B's 4 extra signals were 50% WR.**
- `rule_031` (IT hot): Path A 100% (n=13) vs Path B 82% (n=17). 4 extra signals at 25% WR.

The signals the production scanner *filtered out* lost. The signals it *let through* won. This is either:
- (a) The production scanner is doing the actual edge selection and the rules are ornamental, OR
- (b) Selection bias in the production filter is creating a phantom edge that won't survive out-of-sample.

Either interpretation should terrify you. Sonnet's PB4 critique downgraded these to NEEDS_LIVE_DATA, which is correct, but the framing "needs more data to resolve" understates it. **The data you already have suggests the rules don't add edge beyond what the scanner already does.**

### 3. Complexity-without-evidence (the cohort_health.json contradiction)

Your live cohort_health.json (file 27) shows:
- Choppy UP_TRI: WR 28.6%, n=35, edge **−48.2pp** vs baseline
- Bear UP_TRI: WR 94.7%, n=96, edge **+17.9pp**

This is a 66pp gap. **A two-rule system — "trade UP_TRI in Bear, skip UP_TRI in Choppy" — captures the entire observable edge.** You don't need 37 rules. You don't need sub-regime detectors. You don't need Phase-5 overrides. You don't need barcode v1.

The 35 additional rules are sub-segmentation of cells where you have n=2, n=6, n=13. The Lab's rule_028 (Bear hot Metal UP_TRI, predicted 74%) is built from a cohort the production data tested at n=6. Rule_029 (Bear hot Pharma UP_TRI, predicted 70%) was tested at n=1. These are not rules. They are hypotheses dressed as rules.

### 4. Data-starvation (REAL but secondary)

Yes, you don't have Bull regime data. Yes, you don't have cold Bear data. But this is the *consequence* of points 1-3, not the cause. If your two-rule system worked, data-starvation wouldn't matter much because you wouldn't be claiming 37 calibrated edges. The data-starvation framing exists because the Lab produced 37 rules and you're trying to validate them. Reduce the rule set, reduce the data need.

---

## Other diagnoses you missed

- **Methodology overfit on the methodology itself.** The Step 4 finding "Disciplined Opus prompting beats Trust-Opus by 8.6pp PASS+WARN" is overfit to one synthesis task. You spent $10 to discover this. It's not a generalizable lesson; it's a local minimum.
- **Validation harness problem.** The 35/2/0 PASS result was achieved after L1+L2 *recalibration* of predictions to make them pass. You changed the test until rules passed it. This is goodhart, not validation.
- **"Honest calibration" is doing work it shouldn't do.** The trader_expectations.md explanation of "95% live → 71% production" is correct mathematically (small-sample mean reversion) but emotionally it's preparing you to accept underperformance without questioning whether the system has edge at all. **A 71% expected WR system that delivers 60% looks identical to a 60% expected system delivering 60% — except in the first case you keep trading because "small-sample noise," and in the second you'd stop.**
- **Bridge / Brain / Lab / scanner are four overlapping systems.** File 31 shows Opus reasoning gates running at $0.02-0.03 per call making cohort promotion decisions. File 30 has 0 entries. You're building a meta-system to govern a system you haven't deployed.

---

## The single biggest risk in first 6 months

**You will deploy, the first 30 signals will return ~60-65% WR (small-sample, hot-Bear-dominant), you will interpret this as "system working as calibrated, just below the 71% sweet spot," and you will not detect that the actual edge is the production scanner doing pre-filtering plus survivor bias from regime-confined backtesting. You will scale up. Then the regime shifts (already shifting per file 28: 7 days Choppy after 5 days Bear), the Bear-hot rules become inert, the untested Bull/Choppy rules activate, and you discover whether they have edge while live with capital.**

The data-starvation framing makes you think the 6-month risk is "rules untested in cold Bear" — manageable, just need patience. The actual 6-month risk is "the hot-Bear edge itself was Lab-induced, not real, and I don't have a way to tell from inside the system." That is irreducible without out-of-sample testing.
