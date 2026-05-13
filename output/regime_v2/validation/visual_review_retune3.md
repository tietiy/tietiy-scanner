# Sonnet Visual Review (retune3)

Model: claude-sonnet-4-6
Tokens: in=4848 out=1630

---

# Retune3 Sanity Review — Bear-Side Gate Calibration (Fix I+J+K)

---

## Test-by-Test Evaluation

### Test 1 — Feb–Apr 2026 Sustained BEAR Detection
**FAIL**

- Raw: 33/69 bars correctly flagged BEAR ✓ (gates working)
- Smoothed: only **6 BEAR days** — far below the ≥15 day threshold
- The 14% drawdown from ~26,000 → ~22,300 is unambiguously bearish; 6 smoothed days is a **critical miss**
- Visual confirmation (60-day chart): BEAR bands appear as thin scattered slivers, not a sustained block — exactly what "whipsaw guard blocking commits" looks like
- The whipsaw guard is now the **binding constraint**, making Fix I+J+K effectively inert on the smoothed output

---

### Test 2 — Aug 2025–Feb 2026 BULL Preserved
**PASS**

- 53 BULL days preserved (≥40 threshold met)
- 365-day chart shows clean, wide green BULL block from mid-2025 through Jan 2026
- No degradation from retune2; BULL-side Fixes (A–E) remain stable
- No false BEAR intrusions visible in the BULL block

---

### Test 3 — Historical Bear Detection (2020 COVID et al.)
**PASS**

- 2020 COVID: 39 BEAR days — unchanged from retune2, well above detection threshold
- Full history chart shows BEAR bands present at all major historical corrections (2011, 2015–16, 2018, 2020)
- Long-run BULL trend intact with appropriate regime transitions across 2011–2026
- No historical regression detected

---

### Test 4 — Whipsaw Guard: Oscillation in Charts
**FAIL**

- V2 (90-day chart, top panel): BEAR appears as **multiple narrow vertical slivers** — 4–5 isolated 1–2 day BEAR bands across Feb–Apr 2026 instead of one or two sustained blocks
- This is the textbook signature of whipsaw-guard lockdown: raw flips trigger the 3-in-10-day counter → CHOPPY lockdown → BEAR never accumulates enough consecutive days to "commit"
- 12-month transitions: **19 → 25** (32% increase) confirms raw churn has increased
- V1 comparison (bottom panel) ironically shows a cleaner single large BEAR block — V1's blunter instrument produces better UX despite worse calibration
- The guard, designed to prevent noise, is now **suppressing signal** in a genuine bear move

---

### Test 5 — Quiet Periods / 2024 H2 Spurious BEAR
**CONDITIONAL PASS**

- 23 BEAR days in 2024 H2 — noted as "some spurious but within tolerance"
- Full history chart shows 2024 H2 has scattered thin BEAR bands, but no large false-positive block
- Acceptable given the choppy actual price action in that period (~25,000–26,500 range with vol)
- Does not constitute a clean PASS but is not disqualifying — **within tolerance as stated**

---

### Test 6 — Overall Regime Quality / V2 vs V1 Comparison
**FAIL**

- V2 is **strictly worse than V1** on the primary use-case (Feb–Apr 2026 bear identification) from a user perspective
- V5 P2 bear-tradeable WR improved marginally (92.6% → 94.3%) but n=53 vs n=54 — net BEAR opportunities *slightly reduced*
- The gate loosening (Fix I: -0.005→-0.003, Fix J: drawdown <-8%) achieved the right raw signal but the smoothing layer is destroying the output

---

## Overall Verdict

```
NEEDS_TUNE — FAIL (2/5 core tests passed, binding constraint identified)
```

The architecture is correct; the gates are correctly calibrated. The failure is **entirely in the smoothing layer interaction**, not the signal generation.

---

## Retune4 Recommendation

### Root Cause (Precise)
Loosened gates → more raw BEAR entries → raw flip frequency crosses the 3-in-10-days whipsaw counter threshold → 5-day CHOPPY lockdown fires repeatedly → BEAR can never accumulate a sustained run in smoothed output.

### Fix L — Whipsaw Counter Bear Exemption (Primary Fix)
```
IF raw_state == BEAR 
AND drawdown_from_50d_high < -8%   ← Fix J condition already computed
THEN: do NOT increment whipsaw counter for this transition
```
Rationale: the whipsaw guard was designed for noisy choppy markets. A confirmed >8% drawdown is not noise — exempting it from the counter allows BEAR to commit without triggering lockdown.

### Fix M — Asymmetric Lockdown Duration
```
Whipsaw lockdown → CHOPPY: 5 days (unchanged for BULL↔CHOPPY transitions)
Whipsaw lockdown when last_committed == BEAR: reduce to 2 days
```
Rationale: In a bear move, a 5-day forced CHOPPY creates exactly the "recovery gap" that prevents BEAR from sticking across a volatile but still-declining sequence.

### Fix N — Minimum BEAR Commitment Window
```
Once BEAR commits (raw_state == BEAR for 2 consecutive days), 
hold BEAR for minimum 5 days unless price recovers above 50d_low + 5% 
(the existing Fix K exit condition)
```
This mirrors how BULL regime has natural persistence from trend confirmation and ensures parity.

### Validation Targets for Retune4
| Metric | Retune3 | Retune4 Target |
|---|---|---|
| Smoothed BEAR days Feb–Apr 2026 | 6 | ≥15 |
| 12-month transitions | 25 | ≤22 |
| 2020 COVID BEAR days | 39 | ≥35 |
| BULL Aug25–Feb26 | 53 | ≥45 |
| 2024 H2 spurious BEAR | 23 | ≤20 |

### Do NOT Change in Retune4
- Fix I slope threshold (-0.003) — correct, working at raw level
- Fix J drawdown <-8% entry — correct, reuse as exemption condition in Fix L
- Fix K BEAR_RECOVERY threshold (+5%) — correct exit, keep as minimum-window escape valve
- BULL-side Fixes A–E — no regression, leave untouched