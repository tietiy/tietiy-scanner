# Integration Notes — Step 7 Production Deployment Plan

**Schema:** `unified_rules_v4_1_FINAL.json`
**Validation:** 35 PASS / 2 WARN / 0 FAIL (100% PASS+WARN)
**Audience:** Production engineering + trader operating the live scanner.

This document specifies how to take the v4.1 ruleset out of the Lab
and into the live scanner pipeline. Phases are sequenced so that
detector dependencies are met before the rules that need them go live.

---

## 1. Pre-deployment checklist

Before any rule from v4.1 fires in production, all of the following
must be true:

1. ☐ `unified_rules_v4_1_FINAL.json` checked into the scanner repo at
   `tie_tiy/scanner/rules/unified_rules_v4_1_FINAL.json`.
2. ☐ Rule loader (`RuleEngine.load_v4_1`) understands the new fields:
   `production_ready`, `deferred_reason`, `known_issue`,
   `barcode_compatibility`. Rules with `production_ready=false` must
   be filtered out at load time.
3. ☐ Validation harness re-run against current `signal_history.json`
   confirms the same 35/2/0 result on a fresh checkout.
4. ☐ Sub-regime detector module (`tie_tiy/scanner/sub_regime.py`)
   ships with at least: `recovery_bull`, `healthy_bull`, `late_bull`,
   `hot`, `warm`, `cold`. Classification is deterministic.
5. ☐ Bull sub-regime detector (200d × breadth) unit-tested on at
   least 60 historical days, confusion matrix < 5% misclassification.
6. ☐ Bear 4-tier classifier (B1) shipped with hot/warm/cold + neutral
   bucket. Hysteresis: 3-day stickiness on tier change.
7. ☐ Phase-5 override database refreshed within last 90 days.
8. ☐ Barcode module (`tie_tiy/scanner/barcode.py`) implemented per L3
   spec; unit tests pass on validation_test_cases fixtures.
9. ☐ `KNOWN_ISSUES.md` reviewed and acknowledged by trader.
10. ☐ Rollback procedure dry-run completed: ability to revert to v3
    rules in < 5 minutes with a single config flag.

---

## 2. Phase 1 — HIGH priority rules (week 1-2)

**Rules shipping:** `kill_001`, `win_001`-`win_005`,
`rule_010_bull_uptri_recovery`, `rule_011_bull_uptri_healthy`,
`rule_013_bear_downtri_kill`, `rule_019_bear_uptri_hot_refinement`,
`rule_028_bear_uptri_metal_hot`, `rule_029_bear_uptri_pharma_hot`,
`rule_030_bull_downtri_healthy_kill`. (12 rules.)

**Cells covered:** Bear UP_TRI (all sectors + hot refinement), Bear
DOWN_TRI Bank kill, Bear DOWN_TRI cold kill, Bull UP_TRI
recovery/healthy, Bull DOWN_TRI healthy_kill.

**Detector dependencies:**
- Bull sub-regime (200d × breadth) — required ✓
- Bear 4-tier classifier (B1) — required ✓
- Phase-5 override (B3) — required for `rule_026` (Phase 2), but the
  override module itself must be available since some HIGH rules
  reference it indirectly via cap calculation.

**Cap rules:** No changes from v3. Existing name/date/sector caps apply.

**Telegram format:** Add `[v4.1]` tag to outgoing alerts. Verdict +
calibrated_wr surfaced from the barcode.

**Exit criteria for Phase 1:** ≥ 14 days of live signals, no
rule-loader exceptions, discrepancy rate vs v3 < 10%.

---

## 3. Phase 2 — MEDIUM priority rules (week 3-4)

**Rules shipping:** `watch_001`, `win_006`, `win_007`,
`rule_012_bull_uptri_late`, `rule_014`-`rule_018` (Choppy breadth
gated + wk3/wk4 seasonal), `rule_020`-`rule_027` (sub-regime gated
plus phase5 override), `rule_031_bear_uptri_it_hot`. (16 rules.)

**Detector dependencies added:**
- Choppy 3-axis classifier (C1) — required.
- Choppy N=2 hysteresis (C3) — required.
- `breadth_q` quintile labels: `low / medium / high` — required.
- `week_of_month` integer feature — required.
- Phase-5 override gate active for `rule_026`.

**Cap rules:** Sector cap may need a tweak: when both `rule_028` and
`rule_029` fire on the same day, the Pharma+Metal pair can saturate the
sector cap — verify with trader before going live.

**Exit criteria:** ≥ 14 days live, sub-regime classification stability
> 90% (no flip on intra-day re-runs), Choppy hysteresis fires at most
once per 5 trading days.

---

## 4. Phase 3 — LOW priority deferred (month 2+)

The 6 rules with `production_ready=false` — `rule_032` through
`rule_037` — are **not deployed**. They remain in the JSON for
auditability but are filtered out at load time.

**Revisit triggers:**
- Sub-regime detector v2 ships (refines warm classification).
- Step 1.5 raw-data re-derivation completes (`KNOWN_ISSUES.md`
  future iteration item).
- Cohort sample size for any LOW rule crosses n=120.

**Process:** Each LOW rule promoted via a separate change — recompute
WR band on fresh data, re-run validation harness, require trader
sign-off before flipping `production_ready=true`.

---

## 5. Detector integration order

| Order | Detector | Phase | Owner | Notes |
|---|---|---|---|---|
| 1 | Bull sub-regime (200d × breadth) | Phase 1 | Scanner team | recovery / healthy / late |
| 2 | Bear 4-tier classifier (B1) | Phase 1 | Scanner team | hot / warm / cold + neutral |
| 3 | Phase-5 override (B3) | Phase 1 | Scanner team | DB refresh quarterly |
| 4 | Choppy 3-axis classifier (C1) | Phase 2 | Scanner team | breadth × vol × trend |
| 5 | Choppy N=2 hysteresis (C3) | Phase 2 | Scanner team | composite signal |
| 6 | Sub-regime detector v2 | Month 2+ | TBD | unblocks LOW rules |

Rule activation must not exceed detector readiness. If a detector
slips, the rules depending on it stay dormant; other rules proceed.

---

## 6. Two-week parallel validation period

Both v3 (current) and v4.1 (new) ruleset run **concurrently** for 14
trading days starting at Phase 1 go-live.

**Mechanics:**
- Scanner emits signals through both rule engines.
- Both verdicts logged to `data/parallel_validation/<date>.jsonl`.
- Telegram alert shows both verdicts side by side:
  `v3: TAKE_FULL @ 0.72  |  v4.1: TAKE_FULL @ 0.595`
- Trader chooses which to follow per-signal. Choice is logged.

**Discrepancy categories:**
- **Verdict diverge** (v3 says TAKE, v4.1 says REJECT or vice versa).
- **WR diverge** (same verdict, calibrated_wr differs by > 5pp).
- **Match diverge** (one engine matches a rule, the other matches no
  rule).

**Daily review:** End-of-day report tabulates discrepancies, flags
any signal where v4.1 produced a worse outcome than v3.

---

## 7. Cutover criteria

After 14 trading days of parallel running, cutover to v4.1-only when
**all** of the following hold:

1. **Discrepancy rate < 5%** of signals where the two engines
   materially disagreed (verdict diverge or WR diverge > 5pp).
2. **WR delta < 3pp** between v3 and v4.1 on resolved signals over
   the parallel window. (v4.1 should not be substantially worse; some
   downside is expected because v4.1 is honestly calibrated.)
3. **Trader confidence affirmed** in writing: "I am ready to act on
   v4.1 verdicts alone."
4. **No unresolved P0 incidents** from the parallel period (e.g. rule
   loader crash, barcode write failure, sub-regime classifier flip).

**If criteria fail:** Stay parallel another 7 days; root-cause the
failing criterion. If a structural fix is needed, return to Lab and
re-issue v4.2.

**Rollback procedure:** Set `RULES_VERSION=v3` env var, restart the
scanner, alert acknowledged. Total time < 5 minutes. v4.1 JSON
remains on disk for forensic comparison.

---

## 8. Schema migration v3 → v4.1

**Files affected:**
- `mini_scanner_rules.json` → bumped to `unified_rules_v4_1_FINAL.json`.
- `RuleEngine.__init__` accepts both v3 and v4.1 via a version sniff
  on `schema_version`.
- v3-shaped rules treated as v4.1 with `production_ready=true` and
  no conditions.
- During parallel period, both files loaded; one selected by env var.

**Backward-compat shim:** v3 reads work unchanged; the shim only
intercepts v4.1 writes (signal_history rows gain a `barcode_ref`
field, ignored by v3 readers).

**Removal:** Once cutover criteria pass and trader signs off,
remove the v3 path on the next scanner release.

---

## 9. Barcode rollout (per L3 integration spec)

**Phase A — Shadow (week 1-2 of Phase 1):**
- Barcodes written to `data/barcodes/<YYYY-MM-DD>.jsonl`.
- Not consumed by Telegram or any downstream system.
- Goal: confirm `build_barcode` produces well-formed output on every
  signal; confirm storage layer is reliable.

**Phase B — Linked (week 3-4):**
- `signal_history.json` rows gain `barcode_ref` field pointing into
  the JSONL store.
- Telegram formatter reads from the barcode (verdict, calibrated_wr,
  caps_passed, dominant_rule_id) instead of reconstructing from
  scratch.

**Phase C — Consolidated (month 2+):**
- Hot barcode fields (`verdict`, `confidence_tier`,
  `calibrated_wr`, `caps_passed`, `dominant_rule_id`) promoted to
  first-class columns in `signal_history.json`.
- Full barcode remains in JSONL for audit/replay only.

**Performance budget:** `build_barcode` < 5 ms; `write_barcode`
< 2 ms. ≤ 200 signals/day → < 1.4 s total overhead per scan run.
Alarms fire if any signal exceeds 20 ms.
