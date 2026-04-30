# Lab Decisions Log

**Last updated:** 2026-05-01

This is the canonical persistent ledger of Lab decisions — pending, resolved, and
blocked. Companion to `FINDINGS_LOG.md` (cross-investigation findings ledger).
Per Lab Discipline Principle 6, CC does NOT make promotion or operational
decisions; this file tracks what awaits user judgment.

---

## Pending decisions

### kill_002 ship path
- **Status:** PENDING (post-INV-007 batch decision recommended)
- **Lab evidence:** REJECT promotion at any tier (lifetime + Apr verification both inconclusive)
- **Recommended path:** NO SHIP per Lab Discipline Principle 6 (don't ship rules unsupported by lifetime evidence)
- **Risk if not shipping:** future Apr-like cluster causes new losses without operational protection
- **Risk if shipping anyway:** suppresses 5186 historical signals (most winners) to fix 26 outlier losses

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

### Caveat 2 audit (9.31% MS-2 miss-rate)
- **Status:** PENDING
- **Scope:** investigate 23 missing live Apr 2026 signals; categorize root cause
- **Priority:** before any Tier B candidate promotion

### Persistent log creation
- **Status:** EXECUTING (this turn)

---

## Resolved decisions

(empty initially; populated as decisions are made)

---

## Decisions blocked

(empty initially)
