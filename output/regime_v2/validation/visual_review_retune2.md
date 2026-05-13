# Sonnet Visual Review (retune2)

Model: claude-sonnet-4-6
Tokens: in=5031 out=755

---

## Retune2 Sanity Review

**1. Test 1 (Bear capture): FAIL**
The Feb–Apr 2026 bear remains fragmented into isolated ~2-day red pulses (confirmed by numerical data: still only 4 BEAR days, identical to retune1), with the dominant classification remaining CHOPPY throughout the crash — Fix G's 5-day minimum hold has not materially extended bear persistence.

**2. Test 2 (Bull capture): PASS**
The Aug 2025–Feb 2026 rally is now correctly classified as BULL (green) in Chart 2 for a sustained block, confirmed by the jump from ~0 to 53 BULL days — Fix E's loosened entry threshold is working as intended.

**3. Test 3 (Historical bears): PASS**
Chart 3 shows the 2020 COVID crash, 2015–16 correction, and 2022 bear all retain clear red BEAR blocks without visible degradation from the retune2 fixes.

**4. Test 4 (Whipsaw): PASS**
Transitions dropped from 21 to 19 (within target), and Chart 4 comparison shows V2 has notably fewer isolated single-day BEAR pulses relative to V1, though fragmentation in the Feb–Apr 2026 window persists.

**5. Overall: NEEDS_TUNE**
Retune2 successfully resolves the bull suppression problem (Test 2 passes cleanly) and marginally reduces whipsaw, representing genuine progress. However, the core bear fragmentation problem is **entirely unresolved** — 4 BEAR days across a ~2,500-point, 8-week crash is a critical classifier failure. Fix G (5-day minimum hold) should have addressed this but the numerical evidence confirms it did not fire, suggesting the BEAR *entry* condition is still too restrictive to ever accumulate 5 consecutive qualifying days. The CHOPPY state is absorbing the crash because initial BEAR entry conditions are not being met persistently enough for Fix F's 3-of-5 window to trigger, making Fix G irrelevant.

**6. Retune3 specific changes:**

- **Fix I (Primary — Bear entry relaxation):** Lower the BEAR entry slope threshold in VIX-elevated mode; current threshold requires conditions that resolve within 1–2 days during volatile crashes — target `slope < -0.003 OR ret20 < -4%` (analogous to Fix E's bull loosening, applied symmetrically to bear).
- **Fix J (Bear floor duration):** Implement a regime-level "crash lock" — if Nifty is >8% below its 50-day high, CHOPPY exit to non-BEAR states requires a 10-day confirmation window (prevents crash periods from defaulting to CHOPPY).
- **Fix K (CHOPPY suppression during drawdown):** Block CHOPPY classification when 20-day return < -6%, forcing classifier to choose between BEAR and BEAR_RECOVERY only — this directly attacks the CHOPPY-absorbing-crash failure mode.
- **Preserve:** All retune2 fixes (E, F, G, H) should be retained; Fix E is confirmed working and must not be rolled back.