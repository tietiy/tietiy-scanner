# Trader Expectations — v4.1 Live Deployment

This is your operating manual for the v4.1 scanner. Read it before
Phase 1 goes live. The hardest thing about this rollout is not the
rules — it's the **expectation reset**. Lab data showed numbers that
will not repeat in production. That's not a bug; that's honesty.

---

## 1. The honest WR shift

Here is what you have been seeing in live observation, and what to
expect in production:

| Cell | Live observed (small n) | Production calibrated |
|---|---|---|
| Bear hot UP_TRI (all sectors) | **95%** (n=74) | **71%** (sub-regime refined) |
| Bear UP_TRI Auto | 92% (n=18-21) | **59.5%** |
| Bear UP_TRI FMCG | 100% (n=18-21) | **57.6%** |
| Bear UP_TRI IT | 90% (n=18-21) | **53.3%** |
| Bear UP_TRI Pharma | 95% (n=18-21) | **57.7%** |

**Why the 30pp drop is honest, not the system "getting worse":**

The 95% number came from 74 signals over a few weeks of one specific
Bear regime. With samples that small, a few extra winners pull the
average way up. The lifetime baseline — 1,000+ signals across many
years and several Bear regimes — is **57-71% WR depending on cell**.
That is the real number. The 95% was always an inflated reading.

If you trade as if the system wins 95%, you will size too aggressively,
take a 5-trade losing streak as a system failure, and lose
discipline. If you trade as if it wins 60-70%, the same 5-trade
streak is a normal cluster of bad luck and you keep going.

**One sentence to internalize:** *the system's edge is real but
narrower than it looked in any small live window.*

---

## 2. First 30 days expectations

### Days 1-7: Shadow mode
- v4.1 emits verdicts but **no real capital is committed** based on
  v4.1 alone.
- Continue trading per current v3 process.
- Compare v3 vs v4.1 verdicts daily.
- Goal: confirm the new system isn't doing anything insane.

### Days 8-15: Phase 1 HIGH rules live
- Take signals where **both v3 and v4.1 say TAKE**, with **small
  position size** (50% of normal).
- If v4.1 says REJECT and v3 says TAKE: log it, skip the trade,
  watch the outcome.
- Realistic expectation: **8-12 signals total**, of which **5-8 win**
  (60-70% WR). Do not extrapolate from any 5-day window.

### Days 16-30: Phase 2 ramp
- Choppy + sub-regime gated rules go live.
- Position size returns to normal on cohorts where validation passed.
- HIGH rules: full size. MEDIUM rules: 75% size.
- Realistic outcome: 15-25 signals; 10-16 wins. Some weeks will be
  4/5; some weeks will be 1/4. Don't read either as signal.

---

## 3. Failure modes and recovery

### "First-day BULL_PROXY flood" (S5 finding)
**The fear:** on the first day of a new Bull regime, BULL_PROXY
signals will fire on dozens of names at once and saturate the system.

**The reality:** This is rare. In Lab data we observed it at most
3 times in 5 years. If it happens, sector cap saves you — at most
3-4 signals will pass cap.

**Action:** if cap denies a signal you wanted, that's the cap doing
its job. Do not override.

### "Sub-regime jitter on classification day"
**The fear:** the sub-regime detector flips between hot/warm/cold
within a single day, causing the same setup to be valid in the
morning and rejected by lunch.

**The reality:** the 10-day gate (3-day hysteresis on tier change)
prevents same-day flipping. You should never see this in normal
operation.

**Action:** if you do see this, flag the scanner team — it's a
classifier bug, not a market reality.

### "Phase-5 override fires on stale combo"
**The fear:** a pre-bottom signal database entry is from 2 years
ago and no longer represents current market structure.

**The reality:** the database is refreshed quarterly. If it's > 100
days stale, an alarm fires.

**Action:** if a Phase-5 override fires and the setup looks wrong
to you, **trust your read**. Phase-5 is a precision boost, not a
mandate.

---

## 4. When to escalate concerns

Escalate to the scanner team (do not silently push through) if any
of the following happens:

1. **WR < 50% over 30+ resolved signals.** This means a sub-regime
   classification or a cell calibration is off. Don't keep trading
   into it.
2. **Sector mismatch from Lab playbook.** If a Pharma signal is
   firing Bank rules or vice versa, kill_pattern is broken.
3. **Multiple kill rules firing simultaneously on a winning name.**
   Two kills on the same trade = the system is rejecting too
   aggressively; review precedence.
4. **Sub-regime label changes mid-day.** As above, classifier bug.
5. **Calibrated WR shows < 50% on a HIGH priority rule that recently
   showed 70%+.** Either small-sample inflation just unwound, or a
   real degradation; investigate.

---

## 5. Calibrated WR table (per active rule, per tier)

Active rules in production (29 rules; 6 LOW deferred):

### HIGH priority (12 rules — full size at calibrated WR)

| Rule | Cell | Verdict | Calibrated WR | Tier |
|---|---|---|---|---|
| kill_001 | Bear Bank DOWN_TRI | REJECT | 45% | HIGH |
| win_001 | Bear Auto UP_TRI | TAKE_FULL | 59.5% | HIGH |
| win_002 | Bear FMCG UP_TRI | TAKE_FULL | 57.6% | HIGH |
| win_003 | Bear IT UP_TRI | TAKE_FULL | 53.3% | MEDIUM |
| win_004 | Bear Metal UP_TRI | TAKE_FULL | 57.1% | MEDIUM |
| win_005 | Bear Pharma UP_TRI | TAKE_FULL | 57.7% | HIGH |
| rule_010 | Bull recovery_bull UP_TRI | TAKE_FULL | 62% | HIGH |
| rule_011 | Bull healthy_bull UP_TRI | TAKE_FULL | 58% | HIGH |
| rule_013 | Bear cold DOWN_TRI | REJECT | 42% | HIGH |
| rule_019 | Bear hot UP_TRI (refined) | TAKE_FULL | **71%** | HIGH |
| rule_028 | Bear hot Metal UP_TRI | TAKE_FULL | **74%** | HIGH |
| rule_029 | Bear hot Pharma UP_TRI | TAKE_FULL | **70%** | HIGH |
| rule_030 | Bull healthy DOWN_TRI | REJECT | 43% | HIGH |

### MEDIUM priority (16 rules — 75% size at calibrated WR)

| Rule | Cell | Verdict | Calibrated WR |
|---|---|---|---|
| watch_001 | Choppy UP_TRI broad | WATCH | 52.3% |
| win_006 | Bear Infra UP_TRI | TAKE_FULL | 53.8% |
| win_007 | Bear hot BULL_PROXY | TAKE_FULL | 65% |
| rule_012 | Bull late_bull UP_TRI | TAKE_SMALL | 51% |
| rule_014 | Choppy UP_TRI breadth_high | TAKE_FULL | 60% |
| rule_015 | Choppy UP_TRI breadth_medium | WATCH | 52% |
| rule_016 | Choppy UP_TRI breadth_low | REJECT | 44% |
| rule_017 | Choppy DOWN_TRI wk3 | TAKE_FULL | 61% |
| rule_018 | Choppy DOWN_TRI wk4 | REJECT | 45% |
| rule_020 | Bull late DOWN_TRI wk3 | TAKE_SMALL | 65.2% |
| rule_021 | Bear cold BULL_PROXY | REJECT | 41% |
| rule_022 | Bear warm UP_TRI | WATCH | 55% |
| rule_023 | Bull recovery BULL_PROXY | TAKE_FULL | 66% |
| rule_024 | Choppy BULL_PROXY breadth_high | TAKE_FULL | 59% |
| rule_025 | Bull late UP_TRI wk4 | REJECT | 46% |
| rule_026 | Bear hot DOWN_TRI + phase5 | TAKE_SMALL | 62% |
| rule_027 | Choppy Pharma DOWN_TRI ⚠ | REJECT | 48% |
| rule_031 | Bear hot IT UP_TRI | TAKE_FULL | 68% |

⚠ = WARNING per `KNOWN_ISSUES.md`. Trader may override.

### Range to expect across all active rules
- **Lowest WR (kill rules):** 41-46% (the rejected cells; verdict
  is correctly REJECT, low WR is the point).
- **Lowest WR (winning rules):** 51-55% (marginal-edge MEDIUM cells).
- **Typical WR (most winning rules):** 57-66%.
- **Highest WR (refined HIGH rules):** 68-74% (rule_019, rule_028,
  rule_029, rule_031).

You will **not** see 90%+ in production over any 100+ signal window.
If you do, it's small-sample inflation; do not update your priors.

---

## 6. Trader's mental model

Three principles to hold:

### 6.1 This is not a "system that wins 95%"
This is a system with **edge cells** producing 55-75% WR. The 95%
was a small-sample mirage. The honest number is below.

### 6.2 Edge is real but narrow
A 60-65% WR system, sized correctly with positive expectancy on
each trade, compounds beautifully over a year. A 60-65% WR system,
sized as if it were 95%, ruins you on the first 4-trade losing
cluster. **Size discipline matters more than rule quality.**

### 6.3 Phase-5 override is precision, not magic
The Phase-5 override (rule_026) is one extra check on whether a
signal has historically marked a pre-bottom. It improves precision
on a narrow cell. It is **not** a green light — caps still apply,
sizing still matters, and the calibrated WR is 62% not 95%.

---

## 7. One-page summary

- **Old expectation:** 90-95% WR.
- **New expectation:** 55-75% WR depending on cell.
- **First 30 days:** shadow → small size → normal size, in
  three weeks of two each.
- **If WR goes < 50% over 30 signals:** escalate.
- **If WR goes > 90% over 30 signals:** that's small-sample
  inflation, do not update priors, do not increase size.
- **Trust the caps.** Trust the sub-regime classifier (after the
  3-day hysteresis settles). Trust your read when something looks
  off — system is precision-tuned, not infallible.
- **Phase-5 is a boost, not magic.** Caps still apply.
- **Two known issues** (rule_027, watch_001) — see KNOWN_ISSUES.md.

The Lab work is done. From here, it's discipline.
