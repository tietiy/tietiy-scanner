# Bear UP_TRI Cell — Investigation Notes (Session 1)

**Date:** 2026-05-02 night
**Branch:** `backtest-lab`
**Commits:** `bb9e38e6` (B1) → `4b5bc1fe` (B2) → `2c819e25` (B3) → this (B4)

This file captures hypotheses tested, surprises, decision points, and
open questions accumulated during Session 1 of the Bear UP_TRI cell
investigation.

---

## Hypotheses tested

### H1 — Bear UP_TRI has a clean 2-3 feature filter (analogous to Choppy F1)

**Status:** ❌ REFUTED.

The B3 filter back-test surfaced no candidate filter that improves on the
94.6% baseline. Skipped subsets often have HIGHER WR than matched subsets.
The cell is broad-band edge, not narrow-band — opposite of the Choppy
UP_TRI structure.

### H2 — `nifty_60d_return_pct=low` is the dominant filter anchor

**Status:** 🟡 PARTIAL.

Differentiator score is dominant (+52pp vs WATCH), and the feature is
mechanistically defensible (regime anchor for sustained Bear stress).
But filter back-test shows it captures only 43% of winners with 93.8%
precision — does not improve on baseline. Retained as defensive sub-regime
anchor, not as filter.

### H3 — `day_of_month_bucket=wk4` is a universal anti-feature

**Status:** ❌ REFUTED at live data.

B2 surfaced wk4 as a −68.6pp anti-signal in WATCH vs winners. But 0 of
the 4 live losses occurred in wk4. The signal is likely a Phase 4
selection artifact (analyzer's combinatorial search may have systematically
excluded wk4 entries from surviving combinations) rather than a real
production rule. Documented but NOT deployed as SKIP.

### H4 — Bear UP_TRI is regime-shift adaptive (similar to Choppy F1)

**Status:** ✅ STRONGLY SUSPECTED.

The +38.9pp live-vs-lifetime gap is the largest in the Lab. April 2026
data is uniformly `nifty_vol_regime=High` — same fingerprint as Choppy
F1's regime-shift dependency. Will be confirmed/refuted in Session 2
lifetime validation.

### H5 — S-tier Phase 4 dominance signals true edge (vs Choppy where S/A all REJECTED)

**Status:** ✅ CONFIRMED.

VALIDATED group has 45 S / 15 A / 4 B (S-tier dominates). PRELIMINARY
has 19 A / 4 S. Bear UP_TRI rewards highest-edge backtest patterns —
opposite of Choppy where the highest-tier patterns all over-fit. This is
strong evidence that Bear UP_TRI is the regime the scanner was originally
tuned to detect (the analyzer's S-tier discrimination matches reality
in Bear).

---

## Surprises

### S1 — All 4 losses have `ema_alignment=mixed`, but so do 50%+ of winners

The 4 live losses are unanimously `ema_alignment=mixed` (not `bull` and
not `bear`). This INITIALLY looked like a clean discriminator. But
inspection showed that majority of winners also have mixed EMA alignment
in the current Bear sub-regime. The signal is not exclusionary.

**Implication:** EMA alignment is NOT a useful filter at this n. Need
larger sample to look for mixed-EMA-winner-vs-mixed-EMA-loser
sub-discriminator.

### S2 — Date-correlation risk emerged (3 of 4 losses on 2 dates)

Losses occurred 2026-04-01 (1) and 2026-04-09 (2 different stocks). Plus
OIL.NS on 2026-04-06 (between the two clusters). This suggests:
- 2026-04-01 / 2026-04-09 were "bad days" for Bear UP_TRI broadly
- Multiple Bear UP_TRI losses on the same day = date-correlation risk

**Implication:** Production should consider day-correlation cap on Bear
UP_TRI position sizing — if 3+ Bear UP_TRI signals fire on the same day,
size each at 80% of normal.

### S3 — OIL.NS lost twice in 6 days (repeat-name failure mode)

OIL.NS fired Bear UP_TRI on 2026-04-01 (lost) and 2026-04-06 (lost again).
Both with mixed EMA alignment. Novel failure mode — not seen in Choppy
cells.

**Implication:** "Same name, second attempt within 6 trading days" should
trigger TAKE_SMALL (half size) until either side of the pattern resolves.

### S4 — Sectors don't concentrate losses

Live losses by sector:
- Energy: 2 (both OIL.NS)
- Chem: 1 (COROMANDEL.NS)
- Infra: 1 (JKCEMENT.NS)

But Energy also has 6 wins (75% WR), so sector mismatch rule isn't clean.
Chem and Infra have small live n (4 and 8). Cannot derive sector mismatch
rules from current data.

---

## Decision points (resolved)

### D1 — Filter selection: precision-first or recall-first?

**Decision:** No filter selected. Cell verdict is "TAKE_FULL on all
signals within current sub-regime."

**Rationale:** None of 6 candidate filters improves on 94.6% baseline.
Imposing a filter would reduce signal volume without precision gain.
Trader benefits more from sub-regime-aware sizing than from filter rules
at this stage.

### D2 — Should anti-features (wk4, ema_bear) be production SKIP rules?

**Decision:** No. Documented but not deployed.

**Rationale:** Live losses don't validate the anti-features. They appear
to be Phase 4 selection artifacts rather than real production rules. Risk
of false-positive SKIPs that exclude profitable trades.

### D3 — How to communicate the +38.9pp regime-shift risk?

**Decision:** Bake the caveat into both Status section ("HIGH for current
sub-regime / LOW for universal Bear") and Risk section. Do NOT downplay.

**Rationale:** Choppy F1 lesson — communicating sub-regime fragility
upfront prevented over-confidence in F1's +23pp lift. Bear UP_TRI's
+38.9pp gap is louder; deserves louder caveat.

---

## Open questions for Session 2 (lifetime validation)

1. **Does the cell's 94.6% live WR replicate at lifetime scale?**
   Predicted answer: NO. Expect lifetime WR around 60-70% (above
   55.7% baseline but well below 94.6%). The +38.9pp gap is too large
   to be structural.

2. **What sub-regime axis discriminates winners from losers at lifetime?**
   Candidate axes:
   - `nifty_60d_return_pct` (the differentiator anchor)
   - `nifty_vol_regime` (sampling artifact in current live but may be
     real at lifetime)
   - `bear_age_days` or similar drawdown-depth feature
   - `consecutive_down_days` of NIFTY before signal

3. **Is the +38.9pp gap mostly explained by current-window selection bias,
   or by a genuinely "hot Bear" sub-regime that's rare historically?**
   Test: how much of lifetime Bear data falls in `nifty_60d_return=low
   AND nifty_vol_regime=High` vs current 100%? If <30% of lifetime,
   strong sub-regime specialization confirmed.

4. **Do the WATCH-set patterns (n=405) actually fail, or are they just
   under-observed?**
   Test: pull the 405 WATCH patterns' lifetime test_wr. If their lifetime
   test_wr is similar to VALIDATED (~70%), they're under-observed in live
   rather than failing — which would suggest the cell's true edge is
   broader than the 87 winners suggest.

5. **Does the L3 comprehensive lifetime search (analogous to Choppy L3)
   surface a different filter family for Bear UP_TRI than the B2
   single-feature differentiators?**
   Per Choppy methodology, L3 should be done in Session 3 (regime-wide
   work). Expect: lifetime data will surface combinatorial patterns that
   the cell investigation missed (analogous to Choppy's
   `breadth=medium × vol=High × MACD bull`).

---

## Files produced this session

| File | Lines | Purpose |
|---|---|---|
| `extract.py` | 244 | B1: Phase 5 group extraction + descriptive stats |
| `comparison_stats.json` | ~150 | B1 output |
| `differentiators.py` | 333 | B2: feature differentiator scoring + LLM prompt |
| `differentiators.json` | ~530 | B2 output |
| `differentiators_llm_interpretation.md` | 51 | B2 LLM mechanism analysis |
| `filter_test.py` | 257 | B3: candidate filter back-test |
| `filter_test_results.json` | ~280 | B3 output |
| `playbook_synth.py` | 99 | B4 LLM helper for trader narrative |
| `_playbook_narrative.md` | 19 | B4 LLM-generated narrative (interim) |
| `playbook.md` | 287 | B4: Production playbook v1 |
| `investigation_notes.md` | (this) | B4: hypotheses tested, surprises, open questions |

---

## Session 1 verdict

**Cell complete; verdict captured; ready for Session 2.**

The Bear UP_TRI cell does not produce a production filter rule, contrary
to initial expectations. It produces:
1. A confidence-weighted TAKE_FULL recommendation for current sub-regime
2. Two trader-judgment heuristics (date-correlation cap, repeat-name cap)
3. A defensive sub-regime anchor (`nifty_60d=low`) for monitoring
4. A clearly-flagged regime-shift fragility risk requiring Session 2
   lifetime validation

This is honest documentation of what the data supports — not what we
hoped to find. The user's framing ("strong cohort, formalize what
already works") was correct on the WR side; the "filter discrimination"
expectation was not borne out by the small live n.

**Next session (S2):** Lifetime validation of cell findings against the
15,151 historical Bear UP_TRI signals.
