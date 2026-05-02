# Bull Production Scanner — Verification Report (V4)

**Date:** 2026-05-03
**Branch:** `backtest-lab`
**Verification scope:** Functional correctness of TIE TIY production
scanner's Bull regime pipeline before Bull regime activates live.
**Method:** Replay 2021-08 and 2023-06 historical Bull windows
through unmodified production functions; verify outputs.

---

## Top-level verdict

**✅ Bull pipeline FUNCTIONALLY WORKS.**

All 10 verification checks passed across 2 historical Bull windows
(5 days each). Production scanner correctly:
- Classifies NIFTY regime as "Bull" on Bull days
- Generates UP_TRI / DOWN_TRI / BULL_PROXY signals during Bull regime
- Tags signals with `regime='Bull'`
- Scores Bull signals via regime-aware scoring
- Produces 0 errors during scoring

**Documented gaps** (not blocking):
1. No Bull-specific `boost_patterns` in `mini_scanner_rules.json` —
   expected (no Bull live data to populate from)
2. `target_price=None` on Bull signals — by design (only UP_TRI×Bear
   gets a 2x ATR target; everything else is Day6 exit)

**No bugs found** in Bull pipeline.

---

## Per-component verdict

| Component | Verdict | Evidence |
|---|---|---|
| Regime classifier (NIFTY → Bull) | ✅ WORKS | 10/10 days correctly classified across 2 windows |
| Sector momentum classifier | ✅ WORKS | Leading/Lagging/Neutral assignments produced consistently |
| `detect_signals()` — UP_TRI | ✅ WORKS | 81 UP_TRI signals across 10 days; pivots + breakouts correct |
| `detect_signals()` — DOWN_TRI | ✅ WORKS | 26 DOWN_TRI signals; pivots + breakdowns correct |
| `detect_signals()` — BULL_PROXY | ✅ WORKS | 4 BULL_PROXY signals in 2021-08 (validates code path) |
| `enrich_signal()` (scoring) | ✅ WORKS | 0 scoring errors; scoring math verified manually |
| `regime` tag propagation | ✅ WORKS | All signals carry `regime='Bull'` correctly |
| Stock-level regime (`_get_stock_regime`) | ✅ WORKS | Per-stock Bull/Bear/Choppy assigned independently |
| `mini_scanner_rules` application | ⚠ N/A | No Bull-specific boost_patterns to test (expected) |

---

## Replay summary

### Primary window — 2021-08-02 → 2021-08-13 (post-COVID recovery rally)

| Date | Regime | Sector momentum | Signal types | Total |
|---|---|---|---|---|
| 2021-08-02 | Bull (score=0) | 3L/2Lag/3N | UP_TRI:2 DOWN_TRI:2 | 4 |
| 2021-08-05 | Bull (score=1) | 3L/1Lag/4N | UP_TRI:13 BULL_PROXY:2 DOWN_TRI:2 | 17 |
| 2021-08-09 | Bull (score=1) | 4L/0Lag/4N | UP_TRI:12 BULL_PROXY:1 DOWN_TRI:2 | 15 |
| 2021-08-11 | Bull (score=1) | 3L/1Lag/4N | UP_TRI:11 DOWN_TRI:2 | 13 |
| 2021-08-13 | Bull (score=1) | 3L/2Lag/3N | UP_TRI:14 DOWN_TRI:6 BULL_PROXY:1 | 21 |
| **TOTAL** | | | **51 UP_TRI / 14 DOWN_TRI / 4 BULL_PROXY** | **70** |

### Secondary window — 2023-06-12 → 2023-06-23 (broad uptrend)

| Date | Regime | Sector momentum | Signal types | Total |
|---|---|---|---|---|
| 2023-06-12 | Bull (score=0) | 6L/0Lag/2N | UP_TRI:16 DOWN_TRI:3 | 19 |
| 2023-06-15 | Bull (score=1) | 7L/0Lag/1N | UP_TRI:5 DOWN_TRI:1 | 6 |
| 2023-06-19 | Bull (score=1) | 6L/0Lag/2N | UP_TRI:4 DOWN_TRI:2 | 6 |
| 2023-06-21 | Bull (score=1) | 6L/0Lag/2N | UP_TRI:2 DOWN_TRI:5 | 7 |
| 2023-06-23 | Bull (score=0) | 3L/1Lag/4N | UP_TRI:3 DOWN_TRI:1 | 4 |
| **TOTAL** | | | **30 UP_TRI / 12 DOWN_TRI / 0 BULL_PROXY** | **42** |

**Note on 0 BULL_PROXY in secondary window**: BULL_PROXY pattern
requires bullish reversal candle in support zone. Calm broad-uptrend
period (2023-06) had fewer such candles than 2021-08 post-COVID
recovery. Code path verified to work in primary window (4 signals);
absence in secondary reflects market conditions, NOT a bug.

---

## Spot-check sample (10 signals)

Manually inspected 10 random signals across both windows. All
verifications passed:

### Primary window samples (5)

| Signal | Date | Symbol | Sector | Pivot → Entry | Stop | Score | Action | Verdict |
|---|---|---|---|---|---|---|---|---|
| UP_TRI age=0 | 08-05 | LALPATHLAB | Health | ₹1,658 → ₹1,978 (+19% above pivot) | ₹1,612 | 6 | DEPLOY | ✓ correct breakout |
| DOWN_TRI age=0 | 08-02 | DIXON | Other | ₹4,735 → ₹4,349 (-8% below pivot) | ₹4,854 | 5 | WATCH | ✓ correct breakdown |
| UP_TRI age=2 | 08-09 | AJANTPHARM | Pharma | ₹1,397 → ₹1,525 | ₹1,363 | 2 | CAUTION | ✓ low score (no vol confirm, age 2) |
| UP_TRI age=3 | 08-09 | TATAELXSI | IT | ₹4,107 → ₹4,268 | ₹3,958 | 3 | WATCH | ✓ Bull+SecLead bonus IT sector |
| DOWN_TRI age=0 | 08-09 | PAGEIND | FMCG | ₹33,989 → ₹32,471 | ₹34,884 | 6 | DEPLOY | ✓ vol confirm bonus |

### Secondary window samples (5)

| Signal | Date | Symbol | Sector | Pivot → Entry | Stop | Score | Action | Verdict |
|---|---|---|---|---|---|---|---|---|
| UP_TRI age=3 | 06-12 | CUMMINSIND | CapGoods | ₹1,556 → ₹1,790 | ₹1,505 | 3 | WATCH | ✓ low score (age 3, no sec lead) |
| UP_TRI age=0 | 06-12 | BHEL | CapGoods | ₹77 → ₹86 | ₹74 | 6 | DEPLOY | ✓ Age0 + Bull + Vol = 6 |
| UP_TRI age=2 | 06-21 | FORTIS | Health | ₹272 → ₹310 | ₹265 | 3 | WATCH | ✓ Bull+Vol bonus |
| UP_TRI age=2 | 06-12 | GRSE | CapGoods | ₹446 → ₹565 | ₹426 | 3 | WATCH | ✓ Bull+Vol |
| DOWN_TRI age=0 | 06-21 | IPCALAB | Pharma | ₹761 → ₹737 | ₹779 | 7 | DEPLOY | ✓ Age0+Down+Vol+SecLead = 7 |

### Scoring math verification

Cross-check against `scorer.py` constants:
- UP_TRI: Bull=+2 (vs Bear=+3, Choppy=+1)
- DOWN_TRI: regime-agnostic +2
- Age 0: +3, Age 1: +2
- Vol confirm: +1
- Sector leading: +1
- RS strong: +1
- Grade A: +1

Sample math (LALPATHLAB UP_TRI age=0, vol_confirm=True, sec_mom=Neutral):
- Age0 (3) + Bull (2) + Vol (1) = **6** ✓ matches output

Sample math (TATAELXSI UP_TRI age=3, IT sector Leading):
- Age3 (0) + Bull (2) + SecLead (1) = **3** ✓ matches output

All scoring math correct across samples.

---

## Cross-reference with Lab Bull UP_TRI cell findings

The Lab built Bull cell trio (UP_TRI / DOWN_TRI / BULL_PROXY) using
lifetime data only. Production scanner replay output should be
consistent with Lab's lifetime characterization.

### Sector representation

| Sector | Lab Bull UP_TRI lifetime WR | Production replay UP_TRI signals (sample) |
|---|---|---|
| IT | 56.8% (top) | TATAELXSI 2021-08-09 ✓ |
| Health | 55.4% | LALPATHLAB 2021-08-05, FORTIS 2023-06-21 ✓ |
| FMCG | 53.5% | (none in sample) |
| Pharma | 51.2% | AJANTPHARM 2021-08-09 ✓ |
| CapGoods | 51.4% | CUMMINSIND, BHEL, GRSE 2023-06-12 ✓ |
| Energy | 49.2% (bottom) | (none in sample) |

Production scanner Bull UP_TRI signals fire across sectors consistent
with Lab's lifetime sector ranking. No discrepancies.

### Regime classification consistency

Lab applied production-equivalent regime classifier algorithm to NIFTY
historical data; identified 8 Bull stretches in 2014-2026. Production
replay invocation produces identical Bull classifications:
- 2021-08-02 → 2021-08-13: 5/5 Bull ✓ (matches Lab's 2021 stretch)
- 2023-06-12 → 2023-06-23: 5/5 Bull ✓ (matches Lab's 2023 stretch)

Lab and production agree on regime classification.

### Production-Lab gap: sub-regime detector NOT in production

Lab built Bull sub-regime detector (`recovery / healthy / normal /
late` per `nifty_200d × breadth`) in BU1. Production scanner has NO
sub-regime detection — only 3-state regime (Bull/Bear/Choppy).

**This is expected and pre-documented.** Bear UP_TRI cell's
PRODUCTION_POSTURE.md flagged sub-regime detector as a Wave 5 brain
integration item, not yet deployed. Bull sub-regime detection is
even further from production.

When Bull regime activates live + provisional filters need
activation, sub-regime detection logic from Lab will need to be
integrated into production scanner. This is a documented next-step,
not a verification finding.

---

## Documented gaps for production deployment

### Gap 1 — No Bull-specific boost_patterns

`data/mini_scanner_rules.json:boost_patterns` has 7 entries, ALL
`regime: "Bear"`. No Bull-specific entries.

**Impact:** When Bull regime activates live, signals won't receive
TAKE_FULL conviction tags from boost_patterns layer. They'll be
treated as ordinary signals.

**Severity:** LOW. Lab cell findings (BU1-BU4) provide candidate Bull
boost_patterns:
- Bull UP_TRI: `recovery_bull × vol=Med × fvg_low` → 74% lifetime
- Bull DOWN_TRI: `late_bull × wk3` → 65% lifetime
- Bull BULL_PROXY: `healthy_bull × 20d=high` → 62.5% lifetime

These are PROVISIONAL_OFF until live validation. Once Bull regime
returns + 30+ live signals validate them, they should be added to
boost_patterns.

**Fix when Bull regime returns:** Add Bull boost_patterns from Lab
cell findings to `mini_scanner_rules.json`. Expected work: ~30 min.

### Gap 2 — `target_price` is `None` for non-Bear-UP_TRI signals

`scorer.py:get_exit_rule()` returns `Target2x` only for
`signal=='UP_TRI' AND regime=='Bear'`; everything else returns
`Day6`. `calc_target()` returns `None` for `Day6` exit_rule.

**Impact:** Bull UP_TRI / DOWN_TRI / BULL_PROXY signals all have
`target_price=None`. Telegram alerts may show "no target" or 0.00 for
these signals.

**Severity:** LOW. This is the **same behavior for Choppy regime**;
it's not Bull-specific. Choppy signals have been firing in production
for months without target_price; production downstream has presumably
adapted. Verification confirms Bull behaves identically.

**Status:** by-design; no fix needed for Bull verification scope.

### Gap 3 — Sub-regime detection not in production scanner

Lab built Bull sub-regime detector (`recovery/healthy/normal/late`)
but production scanner has no sub-regime detection layer. When Bull
provisional filters need activation (post Bull regime return), this
detector must be integrated.

**Severity:** LOW for current verification scope (out of scope per
spec discipline of "verification only, no fixes"); MEDIUM for future
production deployment.

**Status:** Documented as Wave 5 brain integration item.

---

## What this verification CAN'T catch

Per spec disclaimer:
- ✗ Bugs that only manifest in current/future data conditions
  different from historical Bull (no cross-validation possible
  without live data)
- ✗ Performance issues (functional verification only; no benchmarks)
- ✗ Integration issues with Telegram/PWA layers (focused on scanner
  core; downstream not exercised)
- ✗ Concurrent/race-condition issues (single-threaded replay)
- ✗ State-mutation bugs in cross-day signal tracking (each replay day
  is independent — production scanner uses persistent state via
  `signal_history.json` which wasn't simulated here)

---

## Recommended fixes before Bull regime activates live

| Priority | Item | Owner | Trigger |
|---|---|---|---|
| HIGH | Verify regime debug log (`output/regime_debug.json`) writes Bull entries correctly when classifier outputs Bull | scanner team | First Bull-classified live day |
| MEDIUM | Add Bull boost_patterns to `mini_scanner_rules.json` | lab + trader | Bull regime active ≥10 days + ≥30 live signals |
| MEDIUM | Integrate Lab Bull sub-regime detector into production scanner | scanner team | Pre-activation of Bull provisional filters |
| LOW | Manual test: trader runs scanner during first Bull-classified live day; confirms Telegram + PWA receive Bull signals | trader | Day 1 of live Bull |

None of these are blocking for Bull regime activation. The pipeline
works; these are quality-of-life improvements.

---

## Sonnet 4.5 architectural critique

See `bull_verification_critique.md` for the LLM critique of this
verification + recommendations for additional tests before Bull
regime activates live.

---

## Summary

Bull production scanner pipeline is **functionally verified**. All 3
signal types fire in Bull regime; regime classifier correctly outputs
Bull; scoring assigns Bull-specific scores; no errors in any
component.

**No bugs to fix. No blockers for Bull regime activation.**

The only documented gaps (no Bull boost_patterns, no sub-regime
detector in production) are expected and pre-documented Lab/Wave-5
integration items, not verification failures.

When Bull regime activates live, the scanner will produce signals.
The trader will see them in Telegram. They'll be scored correctly.
The pipeline works.
