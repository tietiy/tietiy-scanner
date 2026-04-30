# Auto-Run Status — Lab progress log

**Latest session:** INV-013 DOWN_TRI exit timing direction-aware (2026-05-03; user OUT auto-mode).
**Branch:** `backtest-lab` (main branch carries only the dispatcher YAML carve-out per TIY rule 11).

> **Canonical sources going forward:** `lab/FINDINGS_LOG.md` (cross-investigation findings ledger) and `lab/DECISIONS_LOG.md` (pending decisions ledger). This file remains the chronological session log; the two canonical files are the indexed cross-references.

---

## INV-013 session (2026-05-03; user OUT auto-mode)

| Phase | Status | Commit |
|---|---|---|
| 0 — Pre-flight | ✅ pytest 41/41; 19961 DOWN_TRI signals all direction='SHORT'; stop>entry on 99.98%; INV-013 PRE_REGISTERED | n/a |
| 1 — INV-013 build | ✅ 884-line script; SHORT-direction semantics throughout; reuses INV-006 schema with corrected logic | `49a63f45` |
| 2 — INV-013 execute | ✅ 22s runtime; 19948 evaluated, 13 skipped; findings.md 9.5 KB; T5 sanity check passed | `99a83a78` |
| 3 — Logs update | ✅ this commit | (next) |

**Tripwires fired:** NONE. T3 not exercised (n=19961 >> 1000 floor). T5 sanity passed (all DOWN_TRI direction=SHORT). T4/T6/T9/T10 all clean.

### INV-013 headline (data only; NO promotion calls)

**D6 baseline (SHORT-direction CORRECTED):**
- WR: 0.4653, n: 18097
- avg_pnl: **-0.6072% (NEGATIVE — DOWN_TRI structurally loses at D6)**
- R-mult: -0.1596

**Variant verdicts:**
- 0 variants BEAT D6 on WR (matches INV-006 LONG-cohort pattern)
- 5 variants WORSE on WR (all trailing stops + ladders)
- **6 variants BEAT D6 on pnl** (≥10% rel + p<0.05): D2 (+66.5%), D3 (+55.7%), D4 (+38.1%), D5 (+18.3%), TRAIL_1.5xATR (+25.2%), LADDER_B (+41.8%)

**Critical finding — direction-opposite of UP_TRI/BULL_PROXY:**
- LONG signals (UP_TRI/BULL_PROXY): LONGER holds (D10) beat D6 on pnl
- SHORT signals (DOWN_TRI): **SHORTER** holds (D2-D5) beat D6 on pnl

**INV-006 inversion verification:**
- D6 INV-006 reported: 0.5347 (INVALID — LONG-direction)
- D6 INV-013 corrected: 0.4653 (SHORT-direction)
- Sum: **1.0000 EXACT** — clean LONG/SHORT W/L inversion confirmed; runner-bug-fix is mathematically clean

### Cross-INV synthesis update

Four exit-timing investigations now complete spanning full LONG/SHORT space:
- INV-006 UP_TRI: D10 plausibly net positive (+16% capital efficiency, +83% pnl)
- INV-006 BULL_PROXY: D6 baseline holds (D10 net negative -6% capital efficiency)
- INV-006 DOWN_TRI: INVALID (runner LONG-only bug)
- **INV-013 DOWN_TRI corrected: D2-D5 beat D6 on pnl; structurally negative cohort**

Signal-specific exit migration required if pursued: LONG=D10, BULL_PROXY=D6, DOWN_TRI=D2 or D3. Single global HOLDING_DAYS no longer optimal.

### Pending user decisions

1. **INV-013 patterns.json status update:** PRE_REGISTERED → COMPLETED. Recommended verdict: PARTIAL_DOWN_TRI_SHORTER_HOLD_PNL_CANDIDATES_NO_WR_EDGE.
2. **DOWN_TRI HOLDING_DAYS migration to D2 or D3** — pending user review; combines with UP_TRI D10 + BULL_PROXY D6 for unified per-signal config decision.
3. **DOWN_TRI structural negativity** — raises broader question of keeping DOWN_TRI signal at all (avg_pnl -0.607% at D6; even D2 still -0.203%). Out of INV-013 scope; flag for user.
4. **Cross-INV synthesis update:** signal-specific exits required if migration approved; scanner/config.py needs per-signal HOLDING_DAYS map.

### Findings generated

- `lab/analyses/INV-013_findings.md` — 9.5 KB; 6 sections (caveats / methodology + direction-aware logic / per-variant table / drawdown + capital efficiency / INV-006 inversion check / headline / open questions)

### Lab readiness (updated)

- 6 investigations COMPLETED in patterns.json + 1 awaiting status update (INV-013)
- 3 investigations PRE_REGISTERED awaiting execution sessions (INV-005 / INV-010 / INV-012)
- Exit-timing space now fully covered with direction-aware semantics
- INV-013 closes the INV-006 runner-bug-fix loop

### Session end state

- Branch: `backtest-lab`
- HEAD commit: (set by next commit after this status update)
- Working tree: clean
- All commits pushed to origin

---

## INV-007 session (2026-05-02; user OUT auto-mode)

| Phase | Status | Commit |
|---|---|---|
| 0 — Pre-flight | ✅ pytest 41/41; Nifty parquet sane (3757 rows; 1 NaN dropped); 404G disk free | n/a |
| 1 — INV-007 build | ✅ 543-line script; 9-cell vol-bucket × signal matrix; uses hypothesis_tester.evaluate_hypothesis (no LONG-only bug) | `56e7049a` |
| 2 — INV-007 execute | ✅ 235ms runtime; 9 cells evaluated; 7.2 KB findings.md | `9dfa74a0` |
| 3 — Logs update | ✅ this commit | (next) |

**Tripwires fired:** NONE. T3 not exercised (all cells n_excl_flat ≥ 1279, well above 100 floor). T4/T5/T9/T10 all clean.

### INV-007 headline (data only; NO promotion calls)

| Metric | Value |
|---|---|
| Cells evaluated | 9 (3 signals × 3 vol buckets) |
| **CANDIDATE filter cells** | **0** (none cleared 5pp + p<0.05 + n≥100) |
| MARGINAL cells | 1 (BULL_PROXY × Medium −2.02pp) |
| Tier-earning cells (S/A/B) | **0** — all 9 REJECT on both BOOST and KILL |
| INSUFFICIENT_N | 0 |
| Eval errors | 0 |

**Verdict:** Vol regime filter does not yield clear edge in 15-year backtest. No filter promotion candidates surfaced. Cross-bucket avg deltas all <2pp; signal-specific not universal.

**Vol percentile thresholds (15-yr):** Low <p30 (vol < 0.1082), Medium p30-p70, High >p70 (vol > 0.1604).

### Pending user decisions

1. **INV-007 patterns.json status update:** PRE_REGISTERED → COMPLETED. Recommended verdict: NO_EDGE / REJECT_FILTER (matches headline). User finalizes per `DECISIONS_LOG.md`.
2. **UP_TRI HOLDING_DAYS migration to D10** — still deferred; awaiting INV-010 + INV-012 completion before batch decision. INV-007 result does not change this decision (vol regime not a filter; D10 question independent).
3. **Cross-INV synthesis update:** INV-003 (117-cohort) + INV-006 (exit timing) + INV-007 (vol filter) now all complete with consistent picture — current signal universe statistically near-coin-flip after OOS + drift + Wilson gates; no Tier S/A patterns from any direction.

### Findings generated

- `lab/analyses/INV-007_findings.md` — 7.2 KB; 6 sections (caveats / methodology / per-cell / surfaces / tier eval / cross-signal / headline / open questions)

### Lab readiness (updated)

- 5 investigations COMPLETED in patterns.json + 1 awaiting status update (INV-007)
- 4 investigations PRE_REGISTERED awaiting execution sessions (INV-005 / INV-010 / INV-012 / INV-013)
- INV-007 NO_EDGE verdict adds to converging picture: 3 discovery scans (INV-003 / INV-006 / INV-007) all surface near-coin-flip lifetime statistics

### Session end state

- Branch: `backtest-lab`
- HEAD commit: (set by next commit after this status update)
- Working tree: clean
- All commits pushed to origin

---

## Documentation lockdown session (2026-05-01)

**Summary:** Persistent FINDINGS_LOG + DECISIONS_LOG created; INV-001/002/003/006 statuses → COMPLETED with verdicts + rationales; INV-013 pre-registered as DOWN_TRI exit-timing direction-aware follow-up.

| Block | Action | Commit |
|---|---|---|
| pre-Block 1 | INV-006 findings runner-bug advisory banner committed (was uncommitted from prior turn) | `58ccf85e` |
| 1 | Created `lab/FINDINGS_LOG.md` (146 lines) + `lab/DECISIONS_LOG.md` (73 lines) | `8ad131c7` |
| 2 | patterns.json: INV-001/002/003/006 PRE_REGISTERED → COMPLETED (5 new fields each: completion_date, verdict, verdict_rationale, findings_path, user_review_timestamp) | `8f992dd1` |
| 3 | patterns.json: INV-013 pre-registered (DOWN_TRI direction-aware exit-timing follow-up; INVESTIGATION_DISCOVERY_SCAN type) | `a3537320` |
| 4 | this AUTO_RUN_STATUS update | (next) |

**Verdicts locked into patterns.json:**

| ID | Status | Verdict |
|---|---|---|
| INV-001 | COMPLETED | REJECT_PROMOTION |
| INV-002 | COMPLETED | REJECT_PROMOTION_LIFETIME_TIER_BUT_SECTION_2B_REAL_FILTER |
| INV-003 | COMPLETED | PARTIAL_PROMOTION_CANDIDATES_IDENTIFIED |
| INV-006 | COMPLETED | PARTIAL_UP_TRI_D10_CANDIDATE_BULL_PROXY_REJECT_DOWN_TRI_DEFERRED |

**Pre-registered awaiting execution:** INV-005, INV-007, INV-010, INV-012, INV-013.

### Outstanding pending decisions (per `lab/DECISIONS_LOG.md`)

1. **kill_002 ship path** — Lab evidence REJECT promotion; recommended NO SHIP per Lab Discipline Principle 6
2. **UP_TRI HOLDING_DAYS migration to D10** — defer until INV-007/010/012 complete; batch all changes together
3. **7 Tier B candidates from INV-003 individual review** — defer to dedicated review session
4. **Caveat 2 audit (9.31% MS-2 miss-rate)** — investigate 23 missing live Apr 2026 signals before any Tier B candidate promotion

### Lab readiness

- All MS-1..MS-4 infrastructure shipped + Caveat 1 backfill applied
- 4 investigations COMPLETED with structured verdicts in patterns.json
- 5 investigations PRE_REGISTERED awaiting execution sessions
- `lab/FINDINGS_LOG.md` + `lab/DECISIONS_LOG.md` are canonical going forward
- **Lab is ready for INV-007 / INV-010 / INV-012 execution sessions** (each its own session per scope)
- **Persistent logs are the canonical source** for all Lab findings + pending decisions; AUTO_RUN_STATUS continues as chronological session log only

### Session end state

- Branch: `backtest-lab`
- HEAD commit: (set by next commit after this status update)
- Working tree: clean
- All commits pushed to origin

---

## INV-006 session (2026-04-30)

| Phase | Status | Commit |
|-------|--------|--------|
| 0 — Pre-flight | ✅ pytest 41/41; 197 cache parquets; ATR-14 sample-checked on HDFCBANK (sane values) | n/a |
| 1 — INV-006 build | ✅ 671-line script; 12 exit variants × 3 signal types; cache pre-load + per-signal evaluator | `5f774265` |
| 2 — INV-006 execute | ✅ 87s matrix scan; 105415 signals evaluated; 568 skipped (cohort-end edge); findings.md 12 KB; Section 3 label fix included | `062c4780` |
| 3 — Status update | ✅ this commit | (next) |

**Tripwires fired:** NONE. T3 not exercised (all signal-type cohorts well above 100 floor: UP_TRI 72K, DOWN_TRI 18K, BULL_PROXY 5K). T4/T5/T6/T9/T10 all clean.

### INV-006 headline (data only; NO promotion calls)

| Signal | D6 baseline WR | Variants BEAT D6 | Variants WORSE | Marginal |
|---|---|---|---|---|
| UP_TRI | 0.52 (n=72059) | **0** | 5 | 7 |
| DOWN_TRI | 0.5347 (n=18097) | **0** | 5 | 7 |
| BULL_PROXY | 0.5268 (n=4964) | **0** | 5 | 7 |

**Zero variants beat D6** at the 3pp + p<0.05 candidate threshold across any of the 3 signal types. ATR trailing stops + profit ladders all underperform (early-exit dominance — winners cut short). Universal "best by avg WR" candidate is D10 (avg 0.5378 across 3 signals vs D6 0.5272) but +1.06 pp falls below the candidate floor.

This roughly maps to ROADMAP INV-006 outcome (c): "Current D6 confirmed best — no change."

### Findings generated (USER REVIEW REQUIRED)

- `lab/analyses/INV-006_findings.md` — 12 KB; 8 sections (caveats / methodology / 3× per-signal tables / headline / open questions / promotion deferral)

### User decisions deferred

1. **D6 retention vs migration** — findings strongly support keeping current scanner.config TARGET_R_MULTIPLE=2.0 + 6-day hold. User confirms before closing INV-006.
2. **Risk-adjusted (avg_pnl) cross-check** — WR comparison alone may not capture the full picture. User considers WR + avg_pnl jointly per Open Question 3 in findings.
3. **patterns.json INV-006 status** — PRE_REGISTERED → COMPLETED is user-only transition.
4. **Caveat 2 audit dependency** — irrelevant here since no candidate surfaced; INV-006 is a clean negative result.

### Outstanding for future sessions

- INV-007 (volatility regime filter) — pre-registered; awaiting execution session
- INV-010 (GAP_BREAKOUT new signal) — pre-registered; awaiting execution session
- INV-012 (BTST signal discovery) — pre-registered; awaiting execution session
- Caveat 2 audit (~30-45 min) — separate session, gates promotion of any borderline-n INV-003 candidates
- kill_002 + S-6 + M-17 ship to main — separate main-branch session; depends on user's INV-001 conviction-tag decision

### Recommended next step

User reviews `lab/analyses/INV-006_findings.md` + cross-references INV-003 matrix output. INV-006 outcome (D6 retention) is unambiguous; user judgment is mostly Gate 7 user-review confirmation rather than between-tier choice.

---

## INV-003 session (2026-04-30)

| Phase | Status | Commit |
|-------|--------|--------|
| 0 — Pre-flight | ✅ All tripwires clean (T1 data: 3 outputs + 7 sector indices; T2: 41/41 pytest; T5: not exercised) | n/a |
| 1 — INV-003 build | ✅ 425-line script; 117-cohort matrix (13 sectors × 3 regimes × 3 signals; ROADMAP spec was 99 but actual data has 13 sectors) | `a44b148e` |
| 2 — INV-003 execute | ✅ Runtime 970ms; findings.md 13.8 KB; 8 sections | `d7a107a8` |
| 3 — Status update | ✅ this commit | (next) |

**Tripwires fired:** NONE. T3 didn't halt (used as INSUFFICIENT_N flag per spec; 4 cohorts flagged). T4 didn't fire (0 eval errors).

### INV-003 headline (data only; NO promotion calls)

| Bucket | Count |
|---|---|
| Total cohorts evaluated | 117 |
| Boost candidates (Tier S/A/B BOOST) | **3** (all Tier B) |
| Kill candidates (Tier S/A/B KILL) | **4** (all Tier B) |
| REJECT cohorts | 106 |
| INSUFFICIENT_N | 4 |
| Eval errors | 0 |

**No Tier S or A surfaced anywhere in the matrix** — all 7 surfaced candidates are Tier B (watch-only per spec). This is consistent with the broader-market intuition that 15-year average WR is rarely far from coin-flip; most patterns shake out as REJECT once OOS-discipline + drift bounds + Wilson gates are applied.

**Boost candidates (Tier B):**
- `Pharma × Bull × BULL_PROXY` — train n=161, train WR 0.61, test WR 0.53, drift 8.4pp
- `CapGoods × Bear × UP_TRI` — train n=754, train WR 0.60, test WR 0.56, drift 4.9pp
- `Chem × Bear × UP_TRI` — train n=938, train WR 0.60, test WR 0.53, drift 7.3pp

**Kill candidates (Tier B):**
- `Other × Bear × BULL_PROXY` — train n=35 (**borderline**; Caveat 2 vulnerable)
- `Infra × Choppy × BULL_PROXY` — train n=129, train WR 0.38, test WR 0.45, drift 7pp
- `FMCG × Bull × DOWN_TRI` — train n=625, train WR 0.38, test WR 0.43, drift 5.2pp
- `Energy × Bear × DOWN_TRI` — train n=243, train WR 0.40, test WR 0.44, drift 3.6pp

### Cross-validation with prior INV results (internal consistency check)

| Standalone INV | Cell verdict | Prior verdict | Match? |
|---|---|---|---|
| INV-001 (UP_TRI × Bank × Choppy) | REJECT | REJECT | ✓ |
| INV-002 (UP_TRI × Bank × Bear) | REJECT | REJECT | ✓ |

Both INV-001 and INV-002 cells in INV-003 matrix REJECT — internally consistent with standalone investigations. Cohort filters and tier evaluators behave identically in matrix-scan vs single-investigation contexts.

### Findings generated (USER REVIEW REQUIRED)

- `lab/analyses/INV-003_findings.md` — 13865 bytes, 8 sections (A boost / B kill / C reject / D insufficient_n / E headline / F open questions / promotion deferral / caveats banner)

### User decisions deferred (per Lab Discipline Principle 6)

1. **Boost candidates → potential mechanism INV follow-ups:** decide which of the 3 Tier B boost cohorts (Pharma/CapGoods/Chem) warrant pre-registration as INV-006/007/008+
2. **Kill candidates → potential `mini_scanner_rules.kill_patterns` promotion:** apply Gate 4 (GTB validation) + Gate 5 (mechanism) + Gate 7 (user review) before any patterns.json transition. Note: `Other × Bear × BULL_PROXY` n=35 is borderline marginal — Caveat 2 audit highly relevant
3. **kill_002 path with INV-003 context:** matrix shows no Bank × Choppy cohort better explains Apr 2026 cluster than the original kill_002 candidate. INV-001 standalone (REJECT) + INV-003 matrix cell (REJECT) + Phase 4 60d_ret subset analysis (kill_002_v2 had no effect) all align — kill_002 conviction-tag path needs user judgment with full picture
4. **patterns.json status:** INV-001/002/003 stay PRE_REGISTERED; user-only transition to COMPLETED
5. **Caveat 2 audit:** required before promoting any borderline-n candidate (especially Other × Bear × BULL_PROXY at n=35, Pharma × Bull × BULL_PROXY at n=161)

### Outstanding for future sessions

- Caveat 2 audit (~30-45 min) — investigate the 23 missing live signals from MS-2 cross-validation; categorize root cause; re-validate borderline-n INV-003 candidates after audit
- INV-005 (macro-window) — low priority deferred per founding spec
- kill_002 + S-6 + M-17 ship to main — separate main-branch session; depends on user's INV-001 conviction-tag decision informed by INV-003 cross-reference
- Mechanism INVs (INV-006+) for any boost candidates user opts to follow up

### Recommended next step

User reviews `lab/analyses/INV-003_findings.md` end-to-end with fresh judgment. Then synthesizes across INV-001 / INV-002 / INV-003 + Phase 4 cluster verification before any promotion calls. NO single-finding-driven decisions; the 3-investigation picture should converge or surface tensions for further investigation.

### Session end state

- Branch: `backtest-lab`
- HEAD commit: (set by next commit after this status update)
- Working tree: clean
- All commits pushed to origin

---

## Earlier sessions (history below)

## INV auto-mode session (latest)

| Phase | Status | Commit |
|-------|--------|--------|
| 0 — Pre-flight | ✅ All tripwires clean (T1: data exists; T2: 41/41 pytest; T3: 5146 resolved >> 50; T4: 2689 resolved >> 30; T6: 404G disk free) | n/a |
| 1 — INV-001 build | ✅ 782-line script with 6-section pipeline (lifetime baseline + 6 mechanism candidates + 3 inverse patterns + tier eval + GTB-002 validation + headline) | `e85f44d5` |
| 2 — INV-001 execute | ✅ 14 KB findings.md generated; runtime 148ms (in-memory pandas operations) | `2fe67daf` |
| 3 — INV-002 build | ✅ 582-line script with 4-section pipeline (lifetime baseline + Bear sub-period + 3 mechanism candidates + tier eval) | `95a0160e` |
| 4 — INV-002 execute | ✅ 16 KB findings.md generated; runtime 237ms | `a283299b` |
| 5 — Status update | ✅ this commit | (next) |

**Tripwires fired this session:** NONE. T5/T7/T9/T10 all clean. T8 not exercised (all pushes succeeded first attempt).

### INV-001 headline (UP_TRI × Bank × Choppy)
- Lifetime cohort: 5186 signals; 5146 resolved
- All 6 mechanism candidates: INCONCLUSIVE / DATA_UNAVAILABLE
- All 3 inverse patterns: NO_INVERSE_SIGNAL
- **Parent KILL tier: REJECT** (15-yr WR ~52%, statistically near-50%; train→test drift 6.52pp)
- **GTB-002 validation: GATE_4_PASS** (kill_002 prevents 14L, suppresses 2W; ratio 7.0)
- Tension: 15-yr backtest does NOT support structural KILL at any Lab tier; but recent loss batch supports operational kill_002. Roughly ROADMAP outcome (c) — recent-regime artifact, not structural failure.

### INV-002 headline (UP_TRI × Bank × Bear)
- Lifetime cohort: 2689 resolved across 29 Bear sub-periods (15-yr history)
- Section 2a oversold rebound: INCONCLUSIVE
- **Section 2b rate-cycle proxy: CANDIDATE** (Bank Nifty 60-day return differentiates at p<0.10)
- **Section 2c sample-window bias: HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT** (sub-period WR range > 0.20pp)
- **Parent BOOST tier: REJECT** (lifetime WR ~53%, fails B floor 0.60; drift 3.03pp)
- The HIGH_VARIANCE finding directly answers INV-002 trigger: the live n=8 W=8 100% WR is sample-window artifact, NOT structural cohort edge. Matches ROADMAP outcome (b).

### Findings generated (USER REVIEW REQUIRED)
- `lab/analyses/INV-001_findings.md` — 14325 bytes, 563 lines
- `lab/analyses/INV-002_findings.md` — 15899 bytes, 562 lines

### Open caveats carried into findings (documented in each banner)
- **Caveat 1** (sector indices missing): impacts INV-001 Section 3b defensive rotation; impacts INV-002 Section 2b rate-cycle proxy. Backfill deferred to user/CC fresh session.
- **Caveat 2** (9.31% MS-2 miss-rate): warned at top of each findings.md. INV-001 cohort n=5146 is robust; INV-002 sub-period n at marginal levels is more vulnerable.
- **Caveat 3** (score column null): INV-001 Section 2e signal-score quartile DATA_UNAVAILABLE.
- **Caveat 4** (RBI rate calendar out of scope): INV-002 Section 2b uses 60-day return proxy; documented in section.

### User decisions deferred to morning review (per Lab Discipline Principle 6)
1. INV-001: kill_002 conviction-tag path — LIVE_EVIDENCE_ONLY persist (Section 4 REJECT) vs Tier B/A on operational evidence (Section 5 GATE_4_PASS). Tension between 15-yr null result and short-term loss batch.
2. INV-002: 100% live WR is sample-window artifact (per HIGH_VARIANCE finding); decide if cohort warrants Tier B watch tracking or full reject.
3. patterns.json status updates — INV-001 + INV-002 stay PRE_REGISTERED unless user manually transitions per Gate 7.
4. Section 2b CANDIDATE finding (rate-cycle proxy) — flag for INV-NN with proper RBI calendar (out of scope this session).

### Outstanding for future sessions
- Caveat 1 backfill (~10 min) — extend MS-1 `_INDEX_SYMBOLS` with 7 sector indices + re-run lab_ms1_fetch.yml workflow
- Caveat 2 audit (~30-45 min) — investigate 23 missing live signals; categorize root cause
- INV-003 (99-cohort matrix) — gated on Caveat 1 backfill
- INV-005 (macro-window) — low priority deferred
- kill_002 + S-6 + M-17 ship to main — separate main-branch session; depends on user's INV-001 conviction tag decision

### Recommended next step
- User reads INV-001_findings.md fresh tomorrow morning (full 563 lines)
- Then reads INV-002_findings.md (562 lines)
- THEN decides kill_002 path with full context of both findings
- DO NOT make promotion decisions before reading both end-to-end

### Session end state
- Branch: `backtest-lab`
- HEAD commit: (set by next commit)
- Working tree: clean
- All commits pushed to origin
- Next CC session: fresh, with user, for findings review

---

## Earlier sessions (history)

**Session timestamp:** 2026-04-30 (build phase + cloud-fetch + local-execution phase + MS-4 hardening)

---

## Milestones — all 4 BUILDS complete + MS-1/MS-2/MS-3 EXECUTED + tripwires cleared

| ID | Build status | Execution status | Commit |
|----|--------------|------------------|--------|
| MS-1 data_fetcher | ✅ COMPLETE + smoke 5/5 OK | ✅ EXECUTED via GitHub Actions (97.37% coverage; 185 OK / 5 PARTIAL / 0 FAILED) | build `16fd8f0`; cache populated `eb143de9` |
| MS-2 signal_replayer | ✅ COMPLETE + smoke OK | ✅ EXECUTED locally — **T2 PASSED at 90.69%** match (regen=812, live=247, matched=224 vs Apr 2026 live signal_history) | build `de4560d`; results `fb2a1e1a` |
| MS-3 regime_replayer | ✅ COMPLETE + smoke OK | ✅ EXECUTED locally — **T3 PASSED** (Apr 17 + Apr 29 2026 both classified Choppy); 3757 regime rows, distribution Bull 1832 / Choppy 1196 / Bear 729 | build `cdac6f2`; results `39bba517` |
| MS-4 hypothesis_tester | ✅ COMPLETE + HARDENED + 41/41 unit tests passing | N/A (invoked per-investigation; no standalone execution) | build `b981476`; hardening `8e1c2e94` + `d5dfc9ac` + `6e80644d` |
| MS-1 GitHub Actions workflow | ✅ COMPLETE + YAML validated | ✅ TRIGGERED + completed (run 25129950831) | `0b372c8` (backtest-lab); cherry-picked to main `8243ca9f` |

**Total commits across both sessions:** 9 (build session 5 + execution session 4 — MS-1 cache, MS-3 results, MS-2 results, this status update).

**Tripwires:** T1 PASSED (97.37% coverage ≫ 30% floor), T2 PASSED (90.69% match ≫ 80% floor), T3 PASSED (Apr 17 + Apr 29 both Choppy), T4 PASSED (25/25 unit tests).

**Hard stops honored:** NO MS-5 work; NO INV execution; NO main branch modifications; NO patterns.json/GTB modifications; NO scanner/ source modifications; NO real cohort hypothesis testing.

---

## Files produced

```
lab/
├── infrastructure/
│   ├── data_fetcher.py          (~340 LOC) MS-1
│   ├── signal_replayer.py       (~480 LOC) MS-2
│   ├── regime_replayer.py       (~280 LOC) MS-3
│   ├── hypothesis_tester.py     (~340 LOC) MS-4
│   └── test_hypothesis_tester.py (~410 LOC, 25 tests)
├── cache/                        (5 parquets from MS-1 smoke test; gitignored)
└── logs/
    └── fetch_report.json        (MS-1 smoke run report)

.github/workflows/
└── lab_ms1_fetch.yml             (~110 LOC; user-triggered cloud execution)
```

**Total LOC delivered:** ~1960 across 6 files (5 Python + 1 YAML).

---

## Smoke test results

| Module | Smoke command | Result |
|--------|---------------|--------|
| MS-1 data_fetcher | `--smoke` (5 symbols) | RELIANCE 3778 / HDFCBANK 3778 / TCS 3778 / ^NSEI 3757 / ^NSEBANK 3772 — all OK |
| MS-2 signal_replayer | `--smoke` (synthetic 80-bar) | detect_signals importable; compute_d6_outcome → TARGET_HIT pnl=3.64% |
| MS-3 regime_replayer | `--smoke` (synthetic 200-day Nifty) | Classifier returns valid regimes (Bull/Bear/Choppy); insufficient-lookback safe-default verified |
| MS-4 hypothesis_tester | `pytest -v` | **25/25 PASSED in 0.36s** |

---

## Critical context for user on return

### What CC did this turn

1. Built all 4 milestone code modules + GitHub Actions workflow + 25 unit tests
2. Smoke-tested every module before commit
3. Validated MS-4 unit tests (25/25 pass; T4 cleared)
4. Workflow YAML validated via `yaml.safe_load`
5. Each milestone atomic-committed with descriptive message + Co-Authored-By trailer

### What CC did NOT do (per hard-stop discipline)

1. **No MS-5** (ground-truth validator) work
2. **No INV-001/002/003/005 execution**
3. **No real cohort hypothesis testing**
4. **No main branch modifications** — main still at `588cf26` (TIY Wave UI deferral closeout)
5. **No patterns.json modifications** — registry stays as founded
6. **No GTB modifications** — ground-truth stays as founded
7. **No /scanner/ source modifications** — only READ for reference (detector imports + classifier ports)
8. **No /output/signal_history.json modifications**
9. **No multi-hour execution attempts** — surfaced structural per-turn limit and pivoted to GitHub Actions cloud-execution path

---

## User decision points on return

### 1. Trigger MS-1 fetch (REQUIRED before any further Lab work)

**Action:** GitHub repo → Actions tab → "🧪 Lab MS-1 fetch" → Run workflow → branch `backtest-lab` → submit.

**Wait time:** ~3-4 hours wall time. Check Actions tab for progress.

**On completion:**
- Download "lab-cache" artifact (zip of ~190 parquets + fetch_report.json)
- 90-day retention default; download soon
- Unzip into local `/lab/cache/` for MS-2/MS-3 local execution

**T1 tripwire (built into workflow):** workflow exits 2 with `::error::` if `coverage_status = CRITICAL` (< 30% coverage). User must investigate (yfinance throttling pattern continuing? NSE bhav copy fallback?).

### 2. After MS-1 cache downloaded — MS-3 next (regime + sector_momentum history)

**Action:** `python lab/infrastructure/regime_replayer.py`

**Validates T3 tripwire:** Apr 17 + Apr 29 2026 must classify as Choppy. Built-in validation; halts if mismatch.

**Output:** `lab/output/regime_history.parquet` + `lab/output/sector_momentum_history.parquet`.

### 3. After MS-3 — MS-2 signal regen (depends on MS-1 cache + MS-3 outputs)

**Action:** `python lab/infrastructure/signal_replayer.py`

**Validates T2 tripwire:** regenerated 2026-04 signals must match ≥80% of live signal_history.json. Built-in validation; halts if mismatch.

**Output:** `lab/output/backtest_signals.parquet` (~50K-200K signals across 15 years).

### 4. After MS-2 — MS-4 ready for INV-001/002/003/005 execution

**Action (per investigation):**
```python
import pandas as pd
from lab.infrastructure.hypothesis_tester import evaluate_hypothesis

df = pd.read_parquet('lab/output/backtest_signals.parquet')
result = evaluate_hypothesis(
    df,
    cohort_filter={'signal': 'UP_TRI', 'sector': 'Bank', 'regime': 'Choppy'},
    hypothesis_type='KILL'
)
print(result['tier'])  # 'S' / 'A' / 'B' / 'REJECT'
print(result['decision_log'])
```

This is INV-001 work (per `/lab/registry/patterns.json`); separate session, not auto-mode.

### 5. Pre-INV review checklist

Before kicking off INV-001 execution, user reviews:
- [ ] MS-4 hypothesis_tester.py threshold logic (verify Gate 3 quotes match `PROMOTION_PROTOCOL.md`)
- [ ] MS-4 unit tests (25 passing — verify coverage of edge cases user cares about)
- [ ] MS-2 cross-validation match_pct on Apr 2026 (must be ≥ 80% per T2)
- [ ] MS-3 regime validation (Apr 17 + Apr 29 = Choppy per T3)
- [ ] MS-1 coverage_pct ≥ 70% per T1 (or accept partial-coverage caveat)

---

## Halts (none this session)

No tripwires fired. No exceptions caught. Build proceeded clean.

---

## Architectural decisions worth flagging

### A. Cache storage: GitHub Actions artifacts (NOT branch commits)

**Reason:** `/lab/cache/*.parquet` is gitignored per founding commit; cannot commit. Artifacts retain 90 days default.

**Trade-off:** User must download artifact within 90 days OR re-run workflow if expired. Future option: extend to S3/GCS bucket with secret token (out of scope tonight).

### B. Regime + sector_momentum classifiers — PORTED, not imported

**Reason:** Live functions in `main.py` (`get_nifty_info`, `get_sector_momentum`) call `yf.download` internally; not directly callable as pure functions.

**Resolution:** Logic ported into `regime_replayer.py` as pure functions taking df argument. Algorithm identical (verified line-by-line); data plumbing decoupled.

**Source field on output:** `live_classifier_ported` (always; no fallback heuristic needed since logic is purely a port).

### C. evaluate_hypothesis renamed (was test_hypothesis)

**Reason:** pytest auto-discovery treats `test_*` functions as test fixtures. Production function `test_hypothesis` collided.

**Resolution:** Renamed in production module + test file. All 25 tests pass after rename.

### D. detect_signals + helper functions — PURE per audit

**Audit findings:**
- `detect_signals(df, symbol, sector, regime, regime_score, sector_momentum, nifty_close=None)` is pure given inputs
- Module-level constants from `scanner.config`; no global mutable state
- `_get_stock_regime`, `_get_nifty_pct` pure on respective inputs

**Resolution:** Direct import into `signal_replayer.py`. No `IMPURITY_NOTES.md` needed.

---

## MS-4 hardening (2026-04-30 late session)

Code-review audit of `hypothesis_tester.py` + `test_hypothesis_tester.py` surfaced 1 spec deviation, 1 routing ambiguity, 10 missing edge-case tests, and (as a bonus catch) 1 production FP-precision bug. All four issues fixed in three atomic commits:

| Block | Issue | Resolution | Commit |
|-------|-------|------------|--------|
| 1 | Wilson 95% lower + p-value gates not enforced for BOOST Tier S/A despite spec lines 65 + 72 | Added `_check_boost_tier` helper; Tier S requires Wilson ≥0.60 + p<0.05; Tier A requires Wilson ≥0.50 + p<0.05; Tier B unchanged (watch-only per spec) | `8e1c2e94` |
| 2 | FILTER `hypothesis_type` always routed to BOOST evaluator; no way to express FILTER-on-KILL parent | Added `filter_parent_type` keyword param to `evaluate_hypothesis`; default `None` preserves backward compat (FILTER → BOOST) | `d5dfc9ac` |
| 3a | 10 missing edge-case tests (drift boundaries, extreme WR, all-FLAT, p-value not significant, split boundary, missing outcome column) | 11 tests added | `6e80644d` |
| 3b | **FP-precision bug** discovered while writing boundary tests: `abs(0.7 - 0.5) = 0.19999999999999996` slipped under strict `< 0.20` threshold; pattern at exact drift=0.20 silently promoted to Tier B instead of REJECT (also Tier S at exact drift=0.10) | `drift = round(abs(twr - ewr), 4)` in both evaluators (matches existing WR rounding); test assertions wrapped in `round()` to mirror production semantics | `6e80644d` |

**41/41 tests passing.** MS-4 is now fully hardened for INV use. Bug-discovered-and-fixed-same-session = clean discipline win.

---

## Next suggested step

**Status:** All MS-1..MS-4 builds + executions complete; MS-4 hardened; all tripwires cleared. The Lab is now ready to run INV-001 / INV-002 / INV-003 / INV-005 hypothesis testing per `/lab/registry/patterns.json` pre-registrations.

**Recommended next-session scope (INV-001 first — the kill_002 mechanism investigation):**

```python
# Inside next CC session, on backtest-lab branch:
import pandas as pd
from lab.infrastructure.hypothesis_tester import evaluate_hypothesis, filter_cohort

df = pd.read_parquet('lab/output/backtest_signals.parquet')

# INV-001 cohort: UP_TRI × Bank × Choppy
cohort = filter_cohort(df, signal='UP_TRI', sector='Bank', regime='Choppy')
result = evaluate_hypothesis(
    cohort,
    hypothesis_type='KILL',
    train_end='2022-12-31',
    test_start='2023-01-01'
)
# result['tier']: 'S' / 'A' / 'B' / 'REJECT'
# result['decision_log']: gate-by-gate evidence
```

**Open caveat — sector_momentum:** MS-3 wrote sector_momentum_history.parquet but 7 of 8 sector indices were not in MS-1 cache (only ^NSEBANK was fetched; ^CNXIT/^CNXPHARMA/^CNXAUTO/^CNXMETAL/^CNXENERGY/^CNXFMCG/^CNXINFRA absent). Those 7 sectors fall back to "Neutral" momentum throughout history. INV-001 (Bank-only) is unaffected since ^NSEBANK is present. INV-003 (full 99-cohort matrix) will need a sector-index backfill before sector × signal × regime cells outside Bank are reliable. Recommended: extend MS-1 `_INDEX_SYMBOLS` to include the 7 sector indices and re-run lab_ms1_fetch.yml — incremental cost ~15 min; result lands as additional parquets in lab/cache/.

**Open caveat — MS-2 missing live signals (9.31% gap):** 23 of 247 live Apr 2026 signals did not regenerate. Spot-check shows several `DOWN_TRI_SA` rows and `BULL_PROXY` in cohorts; possible drift from live detector configuration window-end (live runs each morning 9:15 IST whereas backtest replay uses cached EOD bars). Acceptable per T2 80% floor, but worth a follow-up audit before INV-003 publishes per-cohort headline tier promotions.

---

## Branch state summary

```
backtest-lab branch:
  Founding commit:        b8dfc30  (Lab founded — README + PROMOTION_PROTOCOL + ROADMAP + patterns.json + GTB-001 + GTB-002)
  + MS-1 build:           16fd8f0
  + MS-2 build:           de4560d
  + MS-3 build:           cdac6f2
  + MS-4 build + tests:   b981476
  + MS-1 workflow:        0b372c8
  + AUTO_RUN_STATUS v1:   45cb2d99
  + TIY Section K rule:   cbcdc503
  + MS-1 cache populated: eb143de9
  + MS-3 results:         39bba517
  + MS-2 results:         fb2a1e1a
  + AUTO_RUN_STATUS v2:   a72260ae
  + MS-4 BLOCK 1 (Wilson/p gates):           8e1c2e94
  + MS-4 BLOCK 2 (FILTER routing):           d5dfc9ac
  + MS-4 BLOCK 3 (boundary tests + FP fix):  6e80644d
  + this status update:   (next commit)

main branch:
  Carries only:           8243ca9f  (lab_ms1_fetch.yml dispatcher — single-file carve-out per TIY rule 11)
  + bot LTP/stop_check commits as they land
```

**Working tree at session-end:** clean (after this status commit + push).

---

## Discipline retrospective

- Surfaced structural per-turn limit at session start; pivoted to hybrid build-only + cloud-execution model rather than pretending multi-hour autonomous run was possible
- Each milestone build + smoke test + commit + push as atomic unit
- All 25 unit tests passed before MS-4 commit (T4 tripwire cleared)
- Pytest naming collision caught + fixed (test_hypothesis → evaluate_hypothesis)
- No scope creep into MS-5 / INV / pattern search despite remaining context budget
- All commits include Co-Authored-By: Claude Opus 4.7 (1M context) trailer
- Execution session: all four tripwires (T1 coverage, T2 match, T3 regime, T4 unit tests) cleared without halt
- Surfaced two open caveats (sector-index backfill needed for 7 sectors; 9.31% MS-2 miss-rate worth audit) rather than silently ignoring
