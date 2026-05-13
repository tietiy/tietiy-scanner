# BEAR — Semantic Decision Memo

**Generated:** 2026-05-13 (pre-retune3)
**Purpose:** Define what BEAR means before tuning to it. Retune3 must implement this memo, not chase the Feb-April 2026 case specifically.
**Status:** Spec. Implementation follows in retune3.

---

## Q1 — What is BEAR?

**BEAR is the regime where short-side bias dominates and long-side momentum strategies should be reduced or paused, except for capitulation-bounce setups.**

In operational terms: a regime where the **next-bar prior over Nifty is negative** (more probability of further decline than recovery), where holding new long exposure carries elevated drawdown risk, and where trader behaviour should shift to defensive — close marginal longs, tighten stops, size new positions smaller. The exception is capitulation-bounce setups (UP_TRI×Bear, the validated 94.7% WR edge): these EXPECT the regime to mean-revert, so they fire AGAINST the regime's directional bias and profit from the bounce.

BEAR is **not** "vague pessimism" or "bad days." It is a specific market state characterized by:
1. **Price below long-cycle reference** (below EMA50 — i.e., the short-cycle trend is broken).
2. **Active or recent decline** (slope of medium-cycle reference is negative OR price has fallen meaningfully from a recent peak).
3. **Sustained character** (not a single-day flush; the state holds for multiple bars).

The 5-state space distinguishes BEAR from BEAR_RECOVERY (active recovery off lows) and CHOPPY (no directional bias). These have different forward distributions and different operator implications.

## Q2 — What conditions must hold for BEAR to fire?

### Required AND conditions (all must be true)

1. **`above_ema50 = False`** — Nifty closes below its 50-day EMA. This is the structural marker that the short-cycle uptrend is broken. **Non-negotiable.** If price is above EMA50, by definition the recent momentum is up — that is not BEAR even if longer-cycle indicators are weak.

### Required OR conditions (any one qualifies as "active or recent decline")

The classifier must see EVIDENCE of decline. Any ONE of these qualifies:

2a. **`slope_10d_ema50 < -0.003`** — the EMA50 is rolling over decisively (10-day slope negative beyond -0.3%).
   - Retune2 used -0.005. Per Fix I, loosen to -0.003 to capture slower-declining bears.
   - Rationale: a Bear regime doesn't require dramatic slope — a steady multi-week grind down qualifies.

2b. **`ret20_pct < -3%`** — Nifty's 20-day return is decisively negative (loosened from -2% in retune2; -3% is a clear "down month" not a noisy flat month).

2c. **`nifty_close / nifty_50d_high - 1 < -0.08`** — price is at least 8% below its 50-day high (Fix J — drawdown context).
   - Catches the case where Nifty has decisively fallen from a peak but slope/ret20 are not extreme on the specific bar.
   - 8% threshold: less than a "correction" (10%) but more than "noise" (5%). Aligns with what the cohort_health Bear cohort actually experienced.

### Disqualifying conditions (cannot be true)

3. **`above_ema200 = True` AND none of (2a, 2b, 2c) at extreme thresholds`** — in a long-cycle Bull, short-term weakness alone is not enough.
   - Specifically: if above_ema200=True, BEAR fires only if at least 2 of {2a, 2b, 2c} are true OR (2c < -10%).
   - This prevents short-cycle pullbacks within long-cycle Bull from being mis-tagged as Bear.

4. **VIX < 15 (if VIX available)** — implausibly low fear in a real Bear regime; almost certainly a measurement issue or short-lived correction within Bull. Currently moot in VIX-degraded mode.

### Persistence (separate from this gate but worth noting)

After the gate fires, retune2's persistence layer requires 3-of-5 confirmation before commit. That layer is unchanged.

## Q3 — The Feb-April 2026 test case

**Window**: Nifty 2026-02-01 to 2026-04-30, peak 26329 (early Feb) → trough 22331 (late March), recovery to 24176 (mid-April). Total drawdown -14.0% over ~45 trading days.

**Expected classification under this memo**:
- **BEAR for ≥15 days** in the deepest decline phase (mid-Feb through mid-late March).
- **BEAR_RECOVERY for ≥5 days** in the early-April recovery bounce (post-March 30 lows).
- **CHOPPY <30 days** within the deepest 30-bar segment (acceptable on bounce days within the decline, but cannot dominate).

**Rationale (per Q1-Q2 above)**:
- The Feb-March decline has above_ema50=False (price clearly below EMA50 by mid-Feb).
- slope_10d_ema50 turns < -0.003 by late Feb.
- ret20_pct < -3% across most of the decline period.
- Drawdown-from-50d-high exceeds 8% by early March.

ALL THREE OR-conditions hold during the decline (overdetermined). The classifier should be firmly BEAR.

The April recovery (Nifty 22331 → 24176, +8%) is BEAR_RECOVERY territory: above_ema50 is still False most of April, but slope is turning up and ret20 is rebounding from extreme negative. Capitulation-bounce setups (UP_TRI×Bear) are exactly the trades to take here. The memo's BEAR_RECOVERY definition (Q4) covers this.

**If retune3 fires BEAR for fewer than 15 days in this window, the memo is not being honored and either (a) the implementation has a bug, (b) the disqualifying conditions are wrong, or (c) the memo itself needs revision.** Promotion criteria (Q6) makes this explicit.

## Q4 — The BEAR vs BEAR_RECOVERY distinction

These are different forward distributions and different operator implications, so the memo must distinguish them cleanly.

### BEAR — active decline OR sustained low-and-flat

Conditions:
- All BEAR gates per Q2 active.
- Either slope < -0.003 (active decline) OR ret20 < -3% (recent damage that hasn't bounced).
- Price is BOTH below EMA50 AND showing weakness.

Operator implication: pause new long entries except validated capitulation setups. Tighten stops on existing longs. Consider closing positions that don't have a near-term thesis.

### BEAR_RECOVERY — active recovery from drawdown

Conditions:
- `above_ema50 = False` (still below the short-cycle reference)
- `slope_10d_ema50 > -0.001` (slope is flat or turning up — no longer actively declining)
- EITHER `ret20_pct > 0` (positive 20-day return now)
- OR `nifty_close / nifty_50d_low - 1 > 0.05` (price is at least 5% above its 50-day LOW — i.e., bounced meaningfully)

Operator implication: regime has stopped actively damaging; consider re-entering longs but size conservatively. Capitulation-bounce setups (UP_TRI×Bear) are PRIMETIME here — the recovery is exactly the upside they capture.

### The Feb-April 2026 mapping

| Phase | Dates (approx) | Memo state | Why |
|---|---|---|---|
| Decline-onset | Feb 1 - Feb 14 | CHOPPY → BEAR (transition) | EMA50 break + slope turning down |
| Active decline | Feb 14 - Mar 25 | **BEAR** (sustained) | Slope -0.005+, ret20 -8% to -12%, DD from 50d-high -10%+ |
| Crash bottom | Mar 25 - Apr 1 | **BEAR** (peak fear) | Maximum DD; price still falling on some bars |
| Bounce | Apr 1 - Apr 15 | **BEAR_RECOVERY** | Slope turns up but still below EMA50; bounce from lows |
| Recovery confirmed | Apr 15 - Apr 30 | BEAR_RECOVERY → CHOPPY | Approaches EMA50; momentum unclear |

Approximate counts:
- BEAR: ~25 days (Feb 14 - Mar 25 + Mar 25 - Apr 1)
- BEAR_RECOVERY: ~10 days (Apr 1 - Apr 15)
- CHOPPY: ~10 days (transitions on either end)

Memo target ≥15 BEAR + ≥5 BEAR_RECOVERY is comfortably within this expectation.

## Q5 — Edge cases (what is NOT BEAR)

### Not BEAR — slow 30-day -5% decline within Bull
- above_ema50 might be False briefly but above_ema200 still True.
- slope mild (-0.001 to -0.003).
- ret20 around -5% (not extreme).
- 50d-high DD around -5% (below 8% threshold).
- **Classification**: CHOPPY. This is a Bull pullback, not a Bear regime.

### Not BEAR — single -3% day in Bull
- Single-day move; persistence (3-of-5 window) prevents single-bar BEAR commit.
- **Classification**: depends on context. Almost always CHOPPY or stays BULL.

### Not BEAR — choppy sideways at low levels
- Price has been below EMA50 for weeks but slope is flat (~0), ret20 oscillating near zero.
- After a Bear regime, this is the "stalemate" phase.
- **Classification**: BEAR_RECOVERY if slope just turning up, else CHOPPY.

### Not BEAR — pure volatility expansion without direction
- VIX spikes from 12 to 22 but Nifty moves ±1% per day, ret20 near zero.
- **Classification**: CHOPPY. High vol alone is not Bear.

### Not BEAR — Bear-tradeable bypass triggers (Group A)
- ret_30d_prior ≤ -9% with V2 currently CHOPPY.
- Note: bypass is a tradeability flag, NOT a regime label. Group A signals fire UP_TRI trades through the bypass even when the underlying regime label is CHOPPY. **The bypass does not change Q2 conditions.**
- This memo aims to make Bypass less necessary by making BEAR fire correctly when conditions warrant. But the bypass continues to exist as a safety net.

### Not BEAR — 2024 mild correction (if in data)
- Mid-2024 had a ~3-5% pullback that didn't qualify as Bear.
- Should remain CHOPPY or BULL_RECOVERY, never BEAR.

## Q6 — Promotion criteria after retune3

For V2 retune3 to be promotion-ready (alongside retune2's existing successes), the following must all hold:

### Memo-implementation criteria (Feb-April 2026 window)
- **C-Memo-1**: ≥15 days classified as BEAR in Feb 1 → Apr 30 2026 window (retune2: 4 days)
- **C-Memo-2**: ≥5 days classified as BEAR_RECOVERY in the same window (retune2: 4 days, OK)
- **C-Memo-3**: <30 days classified as CHOPPY within the deepest 30-bar segment (Mar 5 - Apr 15 approximately)

### No-degradation criteria (must hold ON TOP of C-Memo-1/2/3)
- **C-Quality-1**: UP_TRI Bear-family WR (V5 P2 with bypass) ≥ 85% (retune2 with bypass: 92.6% n=54)
- **C-Quality-2**: 12-month transitions in 8-22 range (retune2: 19) — small relaxation upward acceptable
- **C-Quality-3**: Aug 2025 - Feb 2026 BULL days ≥ 40 (retune2: 53) — some loss acceptable, full collapse not
- **C-Quality-4**: 2020 COVID March-April: ≥20 BEAR days (visual verification)
- **C-Quality-5**: 2024 (any quiet year): NOT spuriously firing BEAR

### Hard rejection criteria (any one fails → revert to retune2)
- **R-1**: V5 P2 drops below 85% (proven cohort damaged)
- **R-2**: 12-month transitions > 30 (whipsaw introduced)
- **R-3**: 2020 COVID detection degrades below 15 days BEAR
- **R-4**: BULL Aug-Feb collapses below 30 days

### Soft acceptance (memo passes + minor degradation)
- C-Memo-1, C-Memo-2 PASS
- C-Quality-1 PASS
- One of C-Quality-2/3/4 misses by <20% but no hard rejection trigger
→ Document for tomorrow's review; user decides.

### Hard acceptance (full pass)
- All C-Memo and C-Quality criteria pass
- Sonnet visual: PASS or NEEDS_TUNE (not FAIL)
→ retune3 is the production candidate.

---

**This memo is the source of truth for retune3.** Implementation follows. If the implementation cannot satisfy the memo's promotion criteria, then either the memo is wrong (needs revision) or the V2 architecture needs more features (VIX, breadth) before BEAR can be classified to this standard.
