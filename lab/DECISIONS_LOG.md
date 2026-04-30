# Lab Decisions Log

**Last updated:** 2026-05-03

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

### INV-013 patterns.json status update
- **From:** PRE_REGISTERED
- **To:** COMPLETED (after user review)
- **Status:** PENDING user review
- **Recommended verdict (TBD):** PARTIAL_DOWN_TRI_SHORTER_HOLD_PNL_CANDIDATES_NO_WR_EDGE — 0 variants beat D6 on WR; 6 variants (D2/D3/D4/D5/TRAIL_1.5xATR/LADDER_B) beat on pnl ≥10% relative + p<0.05; D2 strongest at +66.5% rel. DOWN_TRI structurally negative (D6 avg_pnl -0.607%); shorter holds reduce loss but don't produce positive pnl.
- **Finalized verdict + rationale:** PENDING user judgment per Lab Discipline Principle 6
- **INV-006 inversion verified:** D6 sum INV-006 (0.5347) + INV-013 (0.4653) = 1.0000 EXACT — runner-bug-fix confirmed mathematically clean

### DOWN_TRI HOLDING_DAYS migration (if INV-013 surfaces candidate)
- **Status:** PENDING (awaits user review of INV-013 findings)
- **Lab evidence:** D2 plausibly net positive on pnl (+66.5% rel improvement; -0.203% vs D6 -0.607%); WR slightly higher (0.487 vs 0.4653); but DOWN_TRI cohort structurally negative
- **Decision context:** combine with UP_TRI D10 + BULL_PROXY D6 decisions for unified scanner.config update. Signal-specific exits required: LONG signals prefer LONGER holds (D10), SHORT signals prefer SHORTER holds (D2-D5). Migration to per-signal HOLDING_DAYS config required.
- **Implementation scope (if approved):** scanner/config.py per-signal HOLDING_DAYS map (UP_TRI=10, BULL_PROXY=6, DOWN_TRI=2 or 3) instead of single global value
- **Caveat:** DOWN_TRI structural negativity raises broader question whether to keep DOWN_TRI signal at all (not within INV-013 scope; flag for user)

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
