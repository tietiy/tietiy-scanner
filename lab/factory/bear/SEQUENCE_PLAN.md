# Bear Regime Cell Investigation — Sequence Plan

**Status:** PLANNING
**Date:** 2026-05-02 night
**Scope:** Plan Bear regime cell sequence using the 5-step methodology
validated through Choppy regime work.
**Authoritative companion:** `lab/factory/choppy/lifetime/synthesis.md`
(records the methodology that this plan applies).

---

## A. Methodology (validated from Choppy work)

The Choppy regime investigation validated a 5-step pipeline. Each Bear cell
will follow the same sequence:

### Step 1 — Live cell investigation (per signal type)

Four atomic commits per cell:
1. `extract.py` — pull all live signals for {signal_type × regime}, slot
   into VALIDATED / PRELIMINARY / REJECTED / WATCH groups via Phase-5
   classification
2. `differentiators.py` — compute winners-vs-rejected feature differential
   (univariate, pairwise, threshold-conditioned)
3. `filter_test.py` — back-test top differentiator combinations against
   live data; report match rate, matched WR, lift-over-baseline
4. `playbook.md` — synthesize into production filter rules with confidence
   tier and evidence table

### Step 2 — Lifetime validation (per cell)

One commit per cell, separate session:
- Apply cell's articulated filter to lifetime data (15-yr backtest)
- Compute lifetime WR + lift; compare to live findings
- Document divergence (regime-shift adaptive vs structural)
- Output: `lifetime_validation.json` + `playbook.md` v1.1 update

### Step 3 — Comprehensive lifetime search (regime-wide)

One session, 5 commits:
- L1: data extraction + segmentation
- L2: cell-finding consolidation
- L3: combinatorial 2/3-feature mix-and-match search across full regime
  universe (per signal type, n≥100, lift≥+5pp, p<0.01)
- L4: sector × calendar × volatility stratification
- L5: synthesis + playbook updates across all cells

### Step 4 — Sub-regime detector (per regime)

One session, 1 commit:
- Adapt T1 detector pattern for the regime under investigation
- Identify regime-specific sub-regime axes (may differ from Choppy's
  vol-percentile primary)
- Validate against L4 stratification breakdown
- Document live current sub-regime classification

### Step 5 — Live-pattern × lifetime-pattern reconciliation

One session, 1 commit per cell:
- Test L3 lifetime-derived patterns against live data (à la Choppy T2)
- Document sub-regime mismatch when present
- Production posture: deploy / take_small / hold_pending_subregime / refute

**Total:** 4 commits per cell × 3 cells = 12 commits + 6 commits for
regime-wide work (lifetime search + detector + reconciliation per cell).
Roughly 18-20 commits across Bear regime work.

---

## B. Bear regime cell sequence (priority order)

### Cell 1 — Bear UP_TRI ★ FIRST (proof-of-methodology + reference)

**Why first:** Phase-5 produced 100% validation rate across 87 patterns —
strongest validated cell in entire Lab. Live data is rich (n=74 signals,
94.6% WR). This is the trader's bread-and-butter setup; formalize what
already works.

**Live data status (as of 2026-04-26):**
| Metric | Value |
|---|---|
| Live signals | 74 |
| W / L | 70 / 4 |
| Baseline WR | **94.6%** |
| Lifetime baseline | 55.7% |
| Live-vs-lifetime gap | **+38.9pp** (massive — Choppy F1 was +23pp, this is bigger) |

**Expected outcome:** HIGH-confidence cell, but with **major lifetime
divergence flagged**. The 94.6% live WR vs 55.7% lifetime is a 39pp gap —
larger than Choppy F1's collapse. Bear UP_TRI is likely **regime-shift
adaptive** (works in current sub-regime; collapses in average sub-regime).
Validation must include lifetime cross-check before any production
recommendation beyond TAKE_SMALL.

**Risks unique to this cell:**
- Trader bias: this is the existing trade workflow. Risk of confirmation
  bias — assume it works because it has been working. Lifetime validation
  is critical.
- Sample concentration: 74 live signals likely cluster in narrow date
  range; 6-12 months of additional live data needed for confidence.

**Estimated effort:** 4-6 hours CC time across 2-3 sessions.

---

### Cell 2 — Bear DOWN_TRI ☆ SECOND (high-uncertainty, high-value)

**Why second:** Live evidence shows 18.2% WR (n=11) — `kill_001` rule
already deployed for Bank sector. But lifetime aggregate is 46.1% across
3,640 signals. If a sub-cluster within DOWN_TRI×Bear has positive edge,
finding it produces immediate production value (currently 100% suppressed
via kill_001).

**Live data status:**
| Metric | Value |
|---|---|
| Live signals | 11 (very thin) |
| W / L | 2 / 9 |
| Baseline WR | 18.2% |
| Lifetime baseline | 46.1% |
| Live-vs-lifetime gap | **−27.9pp** (live is artificially hostile) |

**Expected outcome:** Either (a) cell DEFERRED similar to Choppy DOWN_TRI
due to live n=11 sparsity, OR (b) lifetime combinatorial search finds
narrow-band DOWN_TRI×Bear winners that justify a TAKE_FULL filter
overriding kill_001 for specific signatures. Outcome (a) is more likely
given current live evidence.

**Risks unique to this cell:**
- kill_001 currently suppresses all DOWN_TRI×Bear×Bank signals. If
  filter found, must specify exactly when to OVERRIDE kill_001.
- Adversarial regime: DOWN_TRI in Bear is contrarian (going short in
  bearish market expecting upside) — counter-intuitive trades require
  strong evidence.

**Estimated effort:** 3-5 hours; may bottom out at DEFERRED quickly.

---

### Cell 3 — Bear BULL_PROXY ☆ THIRD (best BULL_PROXY cohort)

**Why third:** Phase-5 shipped 82% validation rate across n=17 BULL_PROXY
patterns — strongest BULL_PROXY cohort in any regime. Live evidence is
positive (n=13, 84.6% WR). Lifetime baseline is 47.3%, so live-vs-lifetime
gap is +37.3pp (also large but less extreme than Bear UP_TRI).

**Live data status:**
| Metric | Value |
|---|---|
| Live signals | 13 (small n) |
| W / L | 11 / 2 |
| Baseline WR | 84.6% |
| Lifetime baseline | 47.3% |
| Live-vs-lifetime gap | +37.3pp |

**Expected outcome:** PRELIMINARY-confidence cell. n=13 is too thin for
robust filter articulation; produces filter candidates with caveats.
Lifetime validation may surface that Bear BULL_PROXY also has sub-regime
specificity (analogous to Choppy BULL_PROXY's narrow-exception story).

**Risks unique to this cell:**
- Choppy BULL_PROXY was killed; Bear BULL_PROXY presumed alive only on
  current live evidence. Lifetime data must confirm structural edge
  before any production deployment.
- 11/13 winners may have feature-indistinguishable losers in larger
  sample. Need to examine differentiator analysis carefully for
  separability.

**Estimated effort:** 3-4 hours.

---

### Bear regime synthesis — FOURTH

After all 3 cells complete + their lifetime validations:

- Apply L1-L5 comprehensive lifetime search to Bear regime
- Build Bear sub-regime detector (likely different primary axis — Bear
  is dominantly high-vol, so percentile may not segment well)
- Synthesis playbook + cross-cell decision flow
- Live-pattern × lifetime-pattern reconciliation per cell

**Estimated effort:** 4-6 hours; one or two dedicated sessions.

---

## C. Per-cell expected scope

| Component | Effort | Commits |
|---|---|---|
| extract.py | 1 hour | 1 |
| differentiators.py | 1.5 hours | 1 |
| filter_test.py | 1.5 hours | 1 |
| playbook.md | 1 hour | 1 |
| Lifetime validation (separate session) | 1-2 hours | 1 |
| **Total per cell** | **6-7 hours** | **5** |

**3 cells × 5 commits = 15 commits**, plus regime-wide work:

| Regime-wide work | Effort | Commits |
|---|---|---|
| L1 segmentation | 30 min | 1 |
| L2 cell consolidation | 30 min | 1 |
| L3 comprehensive search | 1 hour | 1 |
| L4 stratification | 1 hour | 1 |
| L5 synthesis + playbook updates | 1.5 hours | 1 |
| Sub-regime detector | 1.5 hours | 1 |
| Live-lifetime reconciliation × 3 cells | 1 hour each | 3 |
| **Subtotal regime-wide** | **8-10 hours** | **9** |

**Total Bear regime: ~50-65 hours, ~24 commits, 6-9 sessions over 1-2 weeks.**

---

## D. Lessons applied from Choppy

| Choppy lesson | Bear application |
|---|---|
| Don't trust live findings without lifetime validation | Build lifetime validation INTO the cell pipeline (Step 2 baked in, not afterthought) |
| Phase 4 high-tier patterns can be over-fit | Test Phase 4 Tier S/A patterns last, not first; expect regime-mismatch artifacts |
| Two features beat ten | Default filter spec to 2-feat with optional 3-feat extension; resist deeper combinations |
| Anti-features can invert at lifetime | Universal anti-feature claims require universal evidence — test in BOTH live and lifetime before adoption |
| KILL verdicts validate more reliably than TAKE filters | Be more confident about cell-killing than cell-promoting; expect to KILL one of three Bear cells |
| Sub-regime structure exists; expect it in Bear too | Build detector early (Step 4), not at the end. Sub-regime axes may differ from Choppy's vol-percentile dominance |
| F1's +23pp live → +1.7pp lifetime (Choppy) | Bear UP_TRI's +94.6% live vs 55.7% lifetime is a louder signal of the same risk; lifetime work is mandatory before any production posture |
| Combinatorial L3 search surfaces patterns cells miss | Run L3 BEFORE finalizing cell playbooks, not after; let L3 inform cell filter selection |

---

## E. Bear-specific considerations

### Bear has rich live data but extreme live-vs-lifetime gaps

| Cell | Live WR | Lifetime WR | Gap |
|---|---|---|---|
| UP_TRI | 94.6% | 55.7% | +38.9pp |
| DOWN_TRI | 18.2% | 46.1% | −27.9pp |
| BULL_PROXY | 84.6% | 47.3% | +37.3pp |

These are **enormous** regime-shift artifacts. Three possibilities:
1. Current live Bear period is in a Bear sub-regime that was rare in 2011-2025
2. Phase-5 selection biased toward signals with current-window-friendly features
3. Bear regime classification itself has changed (different stocks classified Bear now vs historically)

Investigation must surface which mechanism dominates. Until it does, all
Bear filter recommendations should carry **regime-shift caveat tags**.

### Bear is dominantly high-vol

Lifetime vol distribution in Bear:
- High: 60.2%
- Medium: 36.7%
- Low: 3.1%

Bear's "stress sub-regime" (vol > 0.70) covers majority of lifetime —
unlike Choppy where balance was the dominant bucket. The Choppy detector's
3-cell partition may degenerate to 2 cells in Bear (stress + balance,
quiet effectively empty).

Implication: Bear sub-regime detector design should consider **drawdown
depth** or **trend persistence** as the primary axis instead of vol
percentile, since vol is too concentrated to discriminate.

### Bear sub-regime hypothesis (to test)

Three plausible Bear sub-regimes:
- **Early Bear** — recent transition from Bull/Choppy; high uncertainty, sentiment shifting
- **Sustained Bear** — multi-month decline, broad participation in down moves
- **Capitulation Bear** — extreme low breadth, climax-style reversal candidates

These may segment cleanly on `nifty_20d_return_pct` or `52w_high_distance_pct`,
not on vol percentile.

### Bear UP_TRI is trading bread-and-butter

The user's existing strategy heavily relies on Bear UP_TRI bounces. Cell 1
work should NOT disrupt the existing trade workflow — articulating filters
should ADD precision, not remove it. If filter cuts match rate aggressively,
default to TAKE_SMALL on filter-mismatched signals rather than SKIP, until
production data confirms filter discrimination.

### Bear DOWN_TRI is contrarian

Going short on a downward triangle in a Bear market is contrarian
(market is already going down; signal expects further decline; gets
counter-trend bounce). The 18% live WR confirms this is a hostile
configuration. kill_001 (DOWN_TRI×Bear×Bank suppression) is the right
default. Cell investigation goal: find narrow-band winners that justify
overriding kill_001 specifically.

---

## F. Pre-Bear-cell preparation

Before Cell 1 (Bear UP_TRI) begins:

### Required confirmations

- [ ] Live Bear signal count + outcome distribution (DONE in this plan: 98 total, 94/4 W/L excluding flats across 3 cells)
- [ ] Lifetime Bear cohort coverage (DONE: 19,682 signals across 3 cells)
- [ ] Phase 4 + Phase 5 outputs filtered to Bear regime confirmed available in `lab/output/combinations_live_validated.parquet`
- [ ] Vol regime distribution within Bear (DONE: 60% High / 37% Med / 3% Low — informs detector design)

### Bear-specific feature checks

- [ ] Verify `feat_sector_relative_strength` columns are populated in
  `enriched_signals.parquet` (Bear cells likely need sector RS as a primary
  feature, since Bear regime amplifies sector divergence)
- [ ] Check `feat_drawdown_depth_pct` if it exists — relevant for Early /
  Sustained / Capitulation Bear hypothesis
- [ ] Check `feat_52w_high_distance_pct` — likely a primary Bear sub-regime
  axis

### Open feature gaps (may need feature library v2.2 work)

- Bear-specific drawdown features may not exist yet
- "Bear age" feature (days since Bear regime started) would help separate
  Early vs Sustained Bear — likely not in current 114-feature library

---

## G. Decision points before Bear work begins

These need answers before Cell 1 starts:

### G.1 — Cell 1 priority validation

**Question:** Do we want Bear UP_TRI as proof-of-concept first (validate
methodology, build reference implementation) or skip to Bear DOWN_TRI
(higher uncertainty, more learning per session)?

**Recommendation:** Bear UP_TRI first. Reasons:
- Strongest evidence base = highest signal-to-noise for methodology
  refinement
- Reference implementation other cells can copy
- Trader bread-and-butter; user benefits most from formalization
- DOWN_TRI's likely DEFERRED outcome (per live n=11) provides less
  methodology learning

**Reject if:** User specifically wants to investigate DOWN_TRI's failure
mechanism rather than UP_TRI's success mechanism.

### G.2 — Parallel vs sequential cell work

**Question:** Run cells 1, 2, 3 in parallel sessions or strictly sequential?

**Recommendation:** Sequential. Reasons:
- Cell 1 produces methodology refinements that improve Cells 2 and 3
- Each cell's lifetime validation needs Cell 1's regime-wide L1-L4 work
  for full context
- Choppy investigation showed sequential ordering surfaced cross-cell
  insights at synthesis time

### G.3 — Lifetime validation timing

**Question:** Lifetime validate after each cell, or once at the end?

**Recommendation:** After each cell (in same or next session). Reasons:
- Choppy's after-the-fact lifetime validation surfaced major
  reclassifications (F1 weakened, anti-features REFUTED) that should
  inform subsequent cells
- "Live findings without lifetime cross-check" was the #1 lesson from
  Choppy; bake it in early

### G.4 — Production deployment timing

**Question:** Deploy Bear filters as cells complete, or wait for full
regime synthesis?

**Recommendation:** Deploy Bear UP_TRI cell-level filter (with
regime-shift caveat) after Step 1+2 completes, before regime-wide work.
Defer Bear DOWN_TRI / BULL_PROXY production decisions until full regime
synthesis.

**Reject if:** Bear UP_TRI lifetime validation reveals it's a
regime-shift artifact like Choppy F1. In that case, NO production
deployment until L3 surfaces a lifetime-validated alternative.

### G.5 — Feature library extensions

**Question:** Should Bear-specific features (drawdown_depth, bear_age,
sector_RS_breakdown) be added to feature library v2.2 BEFORE Bear cell
work, or surface gaps and address them later?

**Recommendation:** Surface gaps as encountered, defer library work to
v2.2 release. Reasons:
- Adding features pre-investigation invites confirmation bias
- Choppy investigation succeeded with existing 114 features
- Library extensions take 2-4 hours of separate work; folding them in
  delays Bear cell work without proportional value

---

## H. Production deployment timing (overall roadmap)

### Phase 1 — Choppy (current)

| Item | Status |
|---|---|
| Choppy cells (3 cells + synthesis) | ✅ DONE |
| Choppy lifetime validation (V1-V4) | ✅ DONE |
| Choppy comprehensive search (L1-L5) | ✅ DONE |
| Choppy sub-regime detector (T1) | ✅ DONE (design + prototype) |
| Choppy lifetime-pattern reconciliation (T2) | ✅ DONE |
| **Choppy production deployment** | **NEXT — see master_audit / fix_table** |

### Phase 2 — Bear (next, this plan)

| Item | Estimated session |
|---|---|
| Bear UP_TRI cell (Steps 1+2) | Session +1, +2 |
| Bear DOWN_TRI cell (Steps 1+2) | Session +3, +4 |
| Bear BULL_PROXY cell (Steps 1+2) | Session +5, +6 |
| Bear regime-wide L1-L5 + detector | Session +7, +8 |
| Bear live-lifetime reconciliation | Session +9 |
| **Bear production deployment** | **Session +10 (post-synthesis)** |

### Phase 3 — Bull (future)

Defer until Bull regime returns to live data. Currently ~0 live Bull
signals (April 2026 is uniformly Choppy/Bear). When Bull returns:
- Repeat 5-step methodology
- Cross-validate Bull cells against existing Choppy / Bear cells'
  feature signatures (some patterns may be regime-universal, e.g.,
  compression-coil bullish setups)

### Phase 4 — Cross-regime synthesis

After Bull cells complete:
- Build unified decision flow per signal_type × regime
- Identify regime-universal vs regime-specific filter rules
- Document regime transition handling (signal fires during Bear→Choppy
  shift — which filter applies?)

**Estimated total system completion:** ~4-6 weeks from Bear UP_TRI start,
assuming 2-3 sessions per week.

---

## Update Log

- **v1 (2026-05-02 night):** Initial Bear regime cell sequence plan.
  Methodology validated through Choppy work. Bear UP_TRI prioritized as
  Cell 1. Major risk flagged: Bear UP_TRI live-vs-lifetime gap is +38.9pp
  (larger than Choppy F1's +23pp regime-shift artifact). All three Bear
  cells expected to require lifetime cross-check before production.
