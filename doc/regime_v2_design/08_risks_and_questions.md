# 08 — Risks & Open Questions

## Risks (5)

### Risk 1 — v2 kills UP_TRI×Bear cohort attribution
**Severity:** CRITICAL. UP_TRI×Bear is the system's only validated edge (n=96, WR=94.7%).
**How it could happen:** v2's stricter Bear gate (additional `above_ema200` + `vix > 18` conditions) reclassifies some historical Bear days as Choppy or Bear-Recovery. The UP_TRI signals that fired on those days move out of "Bear-family" attribution. The 92.7% WR pool shrinks, possibly to a degraded WR.
**Detection:** Validation 1 (Cohort Preservation Test) — explicit pass/fail gate.
**Mitigation:**
- Threshold loosening: if initial v2 fails C2 (WR drops below 85%), loosen Bear gate parameters (e.g., remove `vix > 18` requirement) and re-run validation.
- Cap retuning at 3 iterations before hard reject.
- Forward-only attribution: historical signals retain v1 regime tag in `signal_history.regime`. v2 tag is in separate field. The proven cohort cannot be silently corrupted.
**Decision point:** If R1 (Validation 1 fails) triggers → REJECT v2 promotion, return to v1.

### Risk 2 — Too many regime transitions per year (noisy)
**Severity:** MEDIUM. Operator psychological tolerance limit.
**How:** persistence rules too loose; v2 emits 20+ transitions per year; brain produces regime_alert proposals weekly; trader fatigue.
**Detection:** Validation 3 T1 (transitions in 12mo). Cap at 20.
**Mitigation:**
- Persistence rules (P1, P2, P3 in §02) — 3-day confirmation for steady states, 2-day for recoveries, whipsaw guard.
- If V3 T1 > 20, tighten persistence (e.g., 4-day confirmation), re-run validation.
**Decision point:** R7 (soft trigger) — tune persistence, don't reject.

### Risk 3 — Too few transitions (over-smoothed)
**Severity:** MEDIUM. The exact problem v1 has.
**How:** persistence too strict; v2 sticky in one state; misses real regime changes.
**Detection:** Validation 3 T1 < 6 in 12mo, OR T2 < 75% of inflections caught.
**Mitigation:**
- Loosen persistence (e.g., 2-day confirmation for all states).
- Loosen gate thresholds (e.g., wider VIX bands).
**Decision point:** R7 (soft trigger) — tune, don't reject.

### Risk 4 — Required inputs unavailable (VIX fetch fails repeatedly)
**Severity:** LOW. India VIX is a stable ticker on yfinance.
**How:** yfinance has occasional downtime; ^INDIAVIX could be unavailable for 1-2 days at a stretch.
**Detection:** `regime_features.json` warnings field flags missing inputs.
**Mitigation:**
- Graceful degradation: VIX missing → Gate 1 (Bull) requires tighter slope to compensate; Gate 3 (Bull-Recovery) cannot fire (falls through to Choppy).
- Cache last known VIX value for ~3 days.
- Alert via Telegram if VIX unavailable > 3 days.
**Decision point:** Acceptable. Document the degraded behavior in `04_decision_logic.md`.

### Risk 5 — Consultant guidance contradicts v2 design
**Severity:** HIGH. Consultant has explicit Bear-only deployment guidance.
**Source of risk:** `doc/consultant_briefings/round_09_phase3_vp_fix.pdf §6.2` and `round_10_rule031_supplement.pdf §4.4`:
> "Bear-only may be valid, yet still be the wrong production object to psychologically and economically anchor yourself to."
> "Specifically: should shadow deployment proceed with this narrower scope, or should we wait for Path B discovery replay to confirm/refute Chem/Auto/FMCG emergence before starting shadow ops?"
**How it manifests:**
- Consultant treats sub_regime (hot/warm/cold) as primary granularity on top of regime (Bear/Bull/Choppy). v2 design uses regime alone with 5 states; does not include sub_regime.
- Consultant's rule_019 fires only when regime=Bear AND sub_regime=hot. Translating to v2: rule_019 fires under v2's `Bear` + some hot-vol condition.

**Mitigation:**
- v2 design **does not change** mini_scanner_rules.json regime gates. `win_001..007` and `kill_001..002` all gate on `regime=Bear` only — they will continue to fire under v2 `Bear` label.
- The hot sub_regime concept is **out of scope for v2**. It is the shadow_ops_v1 harness's separate concern (per `doc/shadow_ops_v1_architecture.md`). The two systems can coexist.
- During validation Phase 4 (shadow), surface the v2 label alongside v1 to the operator. If the consultant reviews v2 design and objects, the operator stops v2 promotion before Phase 5.

**Decision point:** Before promoting v2 (Phase 5), share design + validation results with consultant for sanity check. **This is a recommended pre-Phase-5 step, not a hard requirement.**

## Open Questions (5) — for user to decide before build starts

### Q1 — State granularity: 5 vs 7?

The design recommends **5-state**. Alternative: 7-state (adds Distribution + Bear-Capitulation).

| Option | Pros | Cons |
|---|---|---|
| **5-state (recommended)** | Manageable cohort sample sizes; clean validation; preserves Bear edge | Conflates Distribution-top with Choppy; conflates Capitulation with Bear |
| **7-state** | Captures top-formation + capitulation patterns | n explodes; some cohorts < 10; harder validation; risks v3 territory |

**Decision needed:** stick with 5 or expand to 7?

### Q2 — Methodology: rule-based vs hybrid?

The design recommends **pure rule-based**. Alternative: rule-based + ML refinement.

| Option | Pros | Cons |
|---|---|---|
| **Rule-based (recommended)** | Auditable; deterministic; consultant-aligned; no training data needed | Threshold tuning is manual; cannot capture non-linear features |
| **Hybrid (rule + ML)** | Could improve transition detection; learns from operator feedback | Adds opaque dependency; needs training data not yet available; ML calibration drift; "1 of 6 operationalize" risk |

**Decision needed:** confirm rule-based for v2, defer hybrid to v3?

### Q3 — Validation acceptance threshold for cohort preservation

Validation 1 C2 threshold: WR drop ≤ 10pp from 94.7% baseline (i.e., final WR ≥ 85%).

| Threshold option | Implication |
|---|---|
| ≥ 85% (current recommendation) | Strict; ensures edge survives v2 |
| ≥ 80% | Looser; allows minor re-attribution if a clear regime-transition explanation exists |
| ≥ 90% | Strictest; near-zero re-attribution allowed |

**Decision needed:** what's the operator's tolerance for cohort-WR drift?

### Q4 — Side-by-side shadow run duration: 1, 2, 4 weeks?

The design recommends **2 weeks (10 trading days)**.

| Duration | Pros | Cons |
|---|---|---|
| 1 week | Fast | Unlikely to span a regime transition |
| **2 weeks (recommended)** | Covers ~1 expected transition probabilistically | Operator attention span risk |
| 4 weeks | Higher confidence | Longer wait; operator boredom |

**Decision needed:** confirm 2 weeks or extend?

### Q5 — sub_regime: include in v2 or defer to v3?

The consultant uses `sub_regime` (hot/warm/cold) on top of base regime. v2 design **defers** sub_regime to v3.

| Option | Implication |
|---|---|
| **Defer (recommended)** | Cleaner v2 scope; reuse shadow_ops_v1 sub_regime classifier later if needed |
| Include sub_regime in v2 | State space becomes 5 × 3 = 15 cells; n per cell drops; validation harder; total effort grows by ~30% |

**Decision needed:** confirm sub_regime is out of scope for v2.

## What's unknown / cannot be answered until validation runs

1. **Actual VIX threshold calibration.** The proposed thresholds (vix < 18 for Bull, etc.) are based on long-run India VIX medians. Real-world calibration may need ±2-3 point adjustment.
2. **Bull-Recovery cohort size.** Whether enough historical days qualify as Bull-Recovery to produce a meaningful cohort (n ≥ 10) is unknown until backfill completes.
3. **Bear-Recovery cohort behavior.** Specifically: do UP_TRI signals fired during Bear-Recovery have a usable WR (e.g., 60%+ would justify a new boost rule)? Unknown until validation.
4. **Transition lag.** Whether v2 catches transitions 0-3 days earlier than v1 on average is unknown. Validation 4 shadow window will reveal.
5. **Operator psychological response to "regime_pending" alerts.** Brain will emit regime_shift alerts during the pending window. Will operator feel whipsawed or informed? Unknown until operating.

## Consultant alignment checklist

Before Phase 5 promotion, verify:

- [ ] v2 state `Bear` corresponds to the trading-enabled regime per consultant Round 9 §6.2.
- [ ] No active rule fires outside `Bear` (i.e., we're not silently expanding the deployable rule set under v2 without consultant review).
- [ ] Shadow_ops_v1 sub_regime concept is documented as "deferred to v3," not conflicting with v2.
- [ ] Validation results documented and made available for consultant review if requested.
