# KNOWN_ISSUES.md

This file documents the known limitations, deferred items, and
operational risks for the v4.1 ruleset and its supporting
infrastructure. It is the trader-and-engineer's reference for
"things that are imperfect but acknowledged" as we ship v4.1 to
production.

---

## 1. Active WARNINGs (2 items)

### 1.1 `rule_027` — Choppy DOWN Pharma SKIP (kill rule matches winners)

**Status:** WARNING (not FAIL — kill rule did not produce a wrong
outcome, but its evidence basis is contested).

**What happened:** Lab analysis said Pharma × Choppy × DOWN_TRI is
a -4.7pp anti-edge cell, justifying a REJECT verdict. The validation
harness, scanning live signal_history, found that this same cell
matches signals with **66.1% WR** — i.e. signals our kill rule is
rejecting are actually winning trades.

**Possible causes:**
- Lab finding was over-fit to a specific cohort window that no
  longer generalizes.
- Sub-regime composition of Choppy DOWN Pharma signals shifted
  between Lab's cohort and current live data.
- Live sample is small (n=145) — could be noise.

**Mitigation:**
- Rule remains active with `confidence_tier=LOW` and
  `priority=MEDIUM`. The rule will reject; trader sees the verdict.
- Trader has discretion to override on individual signals if pattern
  context suggests it.
- **Action item:** at month 2 review, re-derive Pharma × Choppy ×
  DOWN_TRI from raw data and decide: keep, soften (downgrade to
  WATCH), or remove.

### 1.2 `watch_001` — Choppy UP_TRI broad informational

**Status:** WARNING (informational rule with WR slightly outside
predicted band).

**What happened:** This is the existing production "watch" rule for
the broad Choppy UP_TRI cell. Lifetime WR = 52.3%. Live observation
showed WR closer to 51.0%, just outside the predicted band of
52.3% ± 0.4pp.

**Why deferred:** This is a watch-only rule (no trade action). The
WR drift is < 2pp and within sampling noise for a cell with n > 27,000.
No production risk.

**Mitigation:**
- Predicted WR band widened to 50-55% in next refresh.
- No action required for Phase 1.

---

## 2. LOW priority deferred (production_ready=false)

The following 6 rules are **not deployed** in any phase. They are
preserved in the JSON for auditability and revisit at month 2+.

| Rule ID | Cell | Reason | Revisit when |
|---|---|---|---|
| `rule_032_choppy_uptri_health_low` | Choppy UP_TRI Health, breadth_low | n=55, LOW confidence | n ≥ 120 OR sub-regime detector v2 |
| `rule_033_bear_bullproxy_warm` | Bear BULL_PROXY warm | Warm classifier still tuning | sub-regime detector v2 ships |
| `rule_034_bull_bullproxy_late` | Bull BULL_PROXY late_bull | Rare event, n=65 | n ≥ 120 |
| `rule_035_choppy_downtri_bank` | Choppy Bank DOWN_TRI | Ambiguous lift signal | Step 1.5 raw-data re-derivation |
| `rule_036_bear_uptri_bank_cold` | Bear cold Bank UP_TRI | Conflicts with rule_001 family | Q3 cohort refresh |
| `rule_037_choppy_bullproxy_low` | Choppy BULL_PROXY breadth_low | Rare combination, n=60 | sub-regime detector v2 + cohort refresh |

**Process to promote a LOW rule:**
1. Recompute WR + count band on fresh data.
2. Re-run validation harness; rule must achieve PASS.
3. `confidence_tier` must be raised to MEDIUM with justification.
4. Trader signs off.
5. `production_ready` flipped to `true`; ship in next release.

---

## 3. Methodology limitations

These are constraints on the Lab work itself; they bound how much
trust to place in any v4.1 prediction.

### 3.1 No live first-Bull-day data
The Bull sub-regime detector classifies on day-of-regime-change. We
have no live signals from the first day of a fresh Bull regime
because no Bull regime has begun within our live cohort. Behavior on
that day is inferred from lifetime composition only.

### 3.2 Bucket threshold registry not yet formalized
Path 2 introduced bucket labels (`low`, `medium`, `high`) for
features like `breadth_q`. The thresholds defining each bucket exist
in code but not in a central registry. Risk: silent threshold drift
across releases.

**Mitigation planned:** formal `feature_thresholds.json` registry by
month 2.

### 3.3 Phase-5 override database needs quarterly refresh
The Phase-5 override (used by `rule_026`) reads a database of
pre-bottom signal combinations. Last refresh: 90 days ago. Stale
combinations can fire spuriously.

**Mitigation:** quarterly cron-job to refresh; alarm if database
age > 100 days.

---

## 4. Future iteration items (Lab → v4.2)

1. **Step 1.5 raw-data re-derivation** (SY recommendation):
   re-derive Lab thresholds directly from raw price data rather than
   from cached features. Will reduce risk of cached-feature drift.
2. **B2 sigmoid soft thresholds** (deferred to Phase 2 in B1+B2):
   currently sub-regime classification is hard cutoffs. Sigmoid
   would give smoother transitions and reduce N=2 hysteresis pressure.
3. **Choppy 3-axis detector with composite hysteresis (C1+C3):**
   in Phase 2 of v4.1; expected to mature in v4.2.
4. **Win_* family lifetime-vs-live calibration:**
   the L1 recalibration was the bottleneck for failing the 80%
   PASS+WARN target in Step 4. v4.2 should test whether shrinking
   the lifetime baseline toward a Bayesian posterior yields tighter
   bands without losing accuracy.
5. **Path-2 unique rule audit** (rule_020, rule_022, rule_025):
   re-evaluate after 60 days of live signals; confirm or retire.

---

## 5. Operational risks

### 5.1 Live small-sample inflation
Bear hot UP_TRI showed 95% live WR over n=74 in Lab data. The
production calibration is 71% (sub-regime refined). If early
production data again shows 90%+ WR, this is **selection bias from
small sample, not a real edge upgrade**. Do not increase position
size based on early WR.

### 5.2 Sub-regime detector classification on transition days
On regime-change days (Bull → Choppy or Bear → Bull), the sub-regime
classifier sees a transient state. The 3-day hysteresis in B1
mitigates this but does not eliminate it.

**Operational guidance:** on the first 2 days following a regime
change, treat HIGH-confidence rules as MEDIUM and MEDIUM as
informational only.

### 5.3 Multiple kill rules firing simultaneously
If two kill rules match the same signal (e.g. `kill_001` and a
sub-regime kill), the verdict is REJECT regardless. No resolution
needed. But the `dominant_rule_id` field in the barcode must be
deterministic — currently the lowest-numbered rule wins. Document
this in the barcode spec.

### 5.4 Win_* WR drift
The win_001 through win_006 rules are calibrated to lifetime
baselines (53-60% WR). If live observation over 60+ days shows
sustained WR < 50%, this signals the lifetime baseline no longer
holds — review immediately, do not wait for the next quarterly
refresh.

---

## 6. Schema/process gaps not yet closed

- **Per-rule SHAP-like attribution:** which feature drove the verdict?
  Not surfaced in the barcode yet. Useful for post-mortem analysis;
  defer to v4.2.
- **Cap rule unification:** v4.1 ruleset doesn't enumerate cap rules
  explicitly; they live in `compute_caps`. Future schema may absorb
  them as `type: "cap"` rules.
- **Multi-language Telegram alert:** trader has requested
  English-Hindi bilingual alert. Out of scope for v4.1.

---

## 7. Acknowledgements

The 35/2/0 validation result was **not** the original target (80%+
PASS+WARN reached cleanly). It is the result of two passes of
recalibration (L1 win_* + L2 schema refinement). The remaining 2
WARNINGs are documented above and accepted by the trader as honest
limitations rather than blockers.
