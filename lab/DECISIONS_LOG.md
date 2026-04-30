# Lab Decisions Log

**Last updated:** 2026-05-04 (post-INV-010 auto-mode)

This is the canonical persistent ledger of Lab decisions — pending, resolved, and
blocked. Companion to `FINDINGS_LOG.md` (cross-investigation findings ledger).
Per Lab Discipline Principle 6, CC does NOT make promotion or operational
decisions; this file tracks what awaits user judgment.

---

## Pending decisions

### INV-001 patterns.json status update
- **From:** PRE_REGISTERED
- **To:** COMPLETED
- **Verdict:** REJECT_PROMOTION (Lab tier REJECT; outlier event identified; no mechanism surfaces; no inverse pattern; Section 2b filter does not catch Apr cluster)
- **Status:** TO BE EXECUTED IN BLOCK 2

### INV-002 patterns.json status update
- **From:** PRE_REGISTERED
- **To:** COMPLETED
- **Verdict:** REJECT_PROMOTION_LIFETIME_TIER_BUT_SECTION_2B_REAL_FILTER (Lab tier REJECT; HIGH_VARIANCE confirms live n=8 100% WR sample-window artifact; Section 2b filter is real but doesn't extend to INV-001 cohort)
- **Status:** TO BE EXECUTED IN BLOCK 2

### INV-003 patterns.json status update
- **From:** PRE_REGISTERED
- **To:** COMPLETED
- **Verdict:** PARTIAL_PROMOTION_CANDIDATES_IDENTIFIED (7 Tier B candidates surfaced; individual review pending)
- **Status:** TO BE EXECUTED IN BLOCK 2

### INV-006 patterns.json status update
- **From:** PRE_REGISTERED
- **To:** COMPLETED (with caveat: DOWN_TRI deferred to INV-013)
- **Verdict:** PARTIAL_UP_TRI_D10_CANDIDATE_BULL_PROXY_REJECT_DOWN_TRI_DEFERRED — UP_TRI D10 candidate identified for HOLDING_DAYS migration; BULL_PROXY stays D6; DOWN_TRI deferred to INV-013
- **Status:** TO BE EXECUTED IN BLOCK 2

### UP_TRI HOLDING_DAYS migration to D10
- **Status:** PENDING (defer until INV-007/010/012 complete; batch all changes together)
- **Lab evidence:** D10 plausibly net positive (+16% capital efficiency, +83% avg pnl, but 2pp deeper p5 tail)
- **Implementation scope:** `scanner/config.py` `HOLDING_DAYS` for UP_TRI signals

### 7 Tier B candidates from INV-003 — individual review
- **Status:** PENDING (defer to dedicated review session)
- **Boost candidates:** Pharma × Bull × BULL_PROXY (n=161), CapGoods × Bear × UP_TRI (n=754), Chem × Bear × UP_TRI (n=938)
- **Kill candidates:** Other × Bear × BULL_PROXY (n=35), Infra × Choppy × BULL_PROXY (n=129), FMCG × Bull × DOWN_TRI (n=625), Energy × Bear × DOWN_TRI (n=243)

### INV-007 patterns.json status update
- **From:** PRE_REGISTERED
- **To:** COMPLETED (after user review)
- **Status:** PENDING user review
- **Recommended verdict (TBD):** NO_EDGE — vol regime filter shows 0 CANDIDATE cells, 1 MARGINAL, 0 tier-earning cells across 9-cell matrix. No filter promotion candidates surfaced. Verdict suggestion: `REJECT_FILTER_NO_VOL_REGIME_EDGE` or similar.
- **Finalized verdict + rationale:** PENDING user judgment per Lab Discipline Principle 6

### DOWN_TRI signal viability (entire signal type)
- **Status:** PENDING
- **Lab evidence:** DOWN_TRI lifetime backtest negative across 15 years (n=18,097, WR 46.5%, avg_pnl -0.607%/trade, R-mult -0.16). Even best exit variant (D2) still produces -0.20% avg pnl per trade.
- **Question:** should DOWN_TRI be retired from scanner entirely, kept with structural caveat, or restricted to specific cohorts only (per INV-003 Tier B kill candidates: FMCG×Bull, Energy×Bear)?
- **Decision impact:** live scanner architecture; signal taxonomy
- **Source:** INV-013 Section 5 (headline) + Section 2 (per-variant table)
- **Cross-references:** INV-001 Section 3a (DOWN_TRI inverse pattern); INV-003 (FMCG×Bull DOWN_TRI Tier B kill, Energy×Bear DOWN_TRI Tier B kill)
- **Recommended timing:** defer until INV-010 + INV-012 complete; final decision in Phase 2 calibration session
- **Resolution_date:** TBD

### DOWN_TRI HOLDING_DAYS migration (if signal kept)
- **Status:** PENDING (depends on DOWN_TRI viability decision above)
- **Lab evidence:** D2 best variant +66.5% pnl improvement vs D6 baseline; D3-D5 also valid candidates (+18-56% pnl)
- **Decision context:** combine with UP_TRI D10 (INV-006) and BULL_PROXY D6 (INV-006) for unified scanner.config update; requires per-signal HOLDING_DAYS map architecture change (not single constant)
- **Resolution_date:** TBD

### Per-signal HOLDING_DAYS architecture migration
- **Status:** PENDING
- **Lab evidence:** INV-006 + INV-013 demonstrate LONG signals favor longer holds (D10 for UP_TRI), SHORT signals favor shorter holds (D2-D3 for DOWN_TRI). Single HOLDING_DAYS constant in scanner.config insufficient.
- **Decision impact:** scanner architecture change; affects entry/exit logic in scanner_core.py + outcome_evaluator.py
- **Cross-references:** INV-006 + INV-013
- **Resolution_date:** TBD

### INV-010 patterns.json status update
- **From:** PRE_REGISTERED
- **To:** COMPLETED (after user review)
- **Status:** PENDING user review
- **Recommended verdict (TBD):** PARTIAL_SUB_COHORT_TIER_B_BOOST_NO_LIFETIME_EDGE — lifetime BOOST/KILL both REJECT; 4 sub-cohorts earn Tier B (Bank×Choppy, FMCG×Choppy, FMCG×Bull, Other×Bull); GAP_BREAKOUT vs UP_TRI marginal at +0.90pp lifetime WR.
- **Finalized verdict + rationale:** PENDING user judgment per Lab Discipline Principle 6

### GAP_BREAKOUT scanner integration (if INV-010 surfaces tier candidate)
- **Status:** PENDING (awaits user review of INV-010 findings)
- **Lab evidence:** lifetime tier REJECT but 4 sub-cohorts Tier B BOOST; GAP_BREAKOUT vs UP_TRI marginal on lifetime WR (+0.90pp)
- **Decision context:** three options for user judgment
  1. **Full signal:** add GAP_BREAKOUT as new signal type to scanner.scanner_core (REJECT lifetime tier — not recommended unless user accepts watch-only Tier B status)
  2. **Conditional signal:** add GAP_BREAKOUT only for the 4 Tier B sub-cohorts (Bank×Choppy, FMCG×Choppy/Bull, Other×Bull) — adds complexity to scanner; n at margin (65-128) makes Caveat 2 audit critical
  3. **Archive:** acknowledge GAP_BREAKOUT does not materially beat UP_TRI; defer to other discovery investigations
- **Implementation scope (if approved):** scanner.scanner_core extension for new signal type + scanner.config new signal registration + bridge composer signal-routing update; production deployment is separate main-branch workstream
- **Caveat 2 priority:** any sub-cohort promotion needs Caveat 2 audit first (n=65-128 marginal)
- **Cross-reference:** Bank×Choppy GAP_BREAKOUT earns Tier B (WR 0.58, n=74) despite INV-001 closing same cohort REJECT for UP_TRI — reinforces signal-cohort interaction; not transitive across signal types

### Caveat 2 audit (9.31% MS-2 miss-rate)
- **Status:** PENDING
- **Scope:** investigate 23 missing live Apr 2026 signals; categorize root cause
- **Priority:** before any Tier B candidate promotion

### Persistent log creation
- **Status:** EXECUTING (this turn)

---

## Resolved decisions

### kill_002 ship path
- **Status:** RESOLVED
- **Resolution:** NO_SHIP_PER_LAB_EVIDENCE
- **Resolution_rationale:** Lab tier REJECT at lifetime n=5146 (INV-001); Apr cluster Section 2b filter does not catch losses (Phase 4); 4-year declining WR trend acknowledged but lifetime evidence does not support structural KILL rule. Lab Discipline Principle 6: do not ship rules unsupported by lifetime evidence. Apr 2026 outlier event documented; reopen if further loss clusters surface.
- **Resolution_date:** 2026-05-02
- **Original-pending context:** Lab evidence REJECT promotion at any tier (lifetime + Apr verification both inconclusive); risk-if-not-shipping was future Apr-like cluster vs risk-if-shipping was suppressing 5186 historical signals (mostly winners) to fix 26 outlier losses.

---

## Decisions blocked

(empty initially)
