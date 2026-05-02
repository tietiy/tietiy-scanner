# Bull Verification Critique Resolution — SUMMARY

**Date:** 2026-05-03
**Investigator:** Claude Opus 4.7 (Lab session, no production code changes)
**Step:** 1 of 7 in Bull production-prep plan

## Context

Sonnet 4.5's V4 critique of Bull pipeline verification flagged 5 untested
scenarios:

| # | Concern | Status before Step 1 |
|---|---|---|
| S1 | State persistence Bear→Bull transition | Untested |
| S2 | Volume filter absence case | Untested |
| S3 | Sector rotation edge cases | Untested |
| S4 | Regime classifier jitter at boundaries | Untested |
| S5 | BULL_PROXY trigger on first Bull day | Untested |

Step 1's mandate: investigate each scenario to honest verdict
(RESOLVED / GAP_DOCUMENTED / DEFERRED_TO_LIVE), surface real gaps,
recommend production-prep work. Documentation only — no scanner code
changes. 6 atomic commits (S1-S5 + this summary).

---

## Verdict matrix

| # | Scenario | Verdict | Pre-activation work? |
|---|---|---|---|
| S1 | State persistence Bear→Bull | ✅ RESOLVED | No |
| S2 | Volume filter absence | ✅ RESOLVED w/ gap | Optional (post-activation) |
| S3 | Sector rotation edge cases | ⚠️ GAP_DOCUMENTED | Yes (1 item) |
| S4 | Classifier jitter | ⚠️ GAP_DOCUMENTED | No (mitigated by 10-day gate) |
| S5 | BULL_PROXY first-Bull-day | ✅ RESOLVED | Yes (1 item, bundled) |

**3 RESOLVED, 2 GAP_DOCUMENTED. 0 DEFERRED_TO_LIVE.**

The two GAP_DOCUMENTED items represent real calibration weaknesses,
but neither blocks production activation. Both have documentation-only
or rules-file-only mitigations; no scanner code changes required.

---

## Synthesized findings

### Architectural strengths confirmed (resolved scenarios)

**S1 — Bear→Bull transitions are structurally safe.** Production
classifier mathematics prevent direct Bear↔Bull single-day transitions
(slope can't flip ±0.01 in 1 day). Empirically: 0 direct transitions
in 12 years of NIFTY data. All Bear→Bull transitions go through a
≥30-day Choppy buffer that flushes Bear-tagged signal context (max
detection age = 3 bars). Combined with stateless-per-scan signal
detection and fire-time regime tagging, Sonnet's failure mode is
architecturally impossible at the daily level.

**S2 — No hard volume filter exists, so legitimate Bull breakouts
are not dropped.** Scanner's `get_vol_rs()` computes vol_q and
vol_confirm as descriptive tags only; never gates signal emission.
All signal types (UP_TRI, DOWN_TRI, BULL_PROXY) emit independently
of volume. Sonnet's "filter dropping legitimate breakouts" concern
is empty.

**S5 — BULL_PROXY first-Bull-day flooding is structurally and
empirically refuted.** BULL_PROXY requires 5-condition conjunction
(above own EMA50, near support, bullish reversal candle, age≤1, valid
stop). Per-stock EMA50 gate creates structural lag between NIFTY
Bull activation and individual-stock BULL_PROXY eligibility. Day 1
fires LESS, not more, than steady-state. Lifetime data: 1.8/day
average across 188-stock universe. V3 replay: 0.67% per stock-day,
all WATCH bucket. First-day BULL_PROXY signals likely classify as
recovery_bull sub-regime — the cell's HIGHEST-WR cohort (57.4%).

### Calibration weaknesses surfaced (documented gaps)

**S3 — Sector handling has 3 calibration gaps in Bull-specific
behavior:**

1. **First-Bull-day stale ranking** (1-month sector_momentum window
   covers prior Bear/Choppy regime; Day 1-15 of Bull tags reflect
   old leadership)
2. **Leadership inflation in broad Bull rallies** (2023-06-15
   replay: 7 of 8 sectors all "Leading"; SecLead+1 bonus near-universal,
   loses discriminating power)
3. **Lab "SKIP Energy × Bull UP_TRI" rule (-2.9pp)** not in production
   `mini_scanner_rules.json`; Energy fired 12/112 (10.7%) of replay
   signals — most of any sector

**S4 — Classifier jitter is real but bounded:**

1. 17 single-day jitter events in 12 years (~1.4/year)
2. 13 two-day jitter events (~1.1/year)
3. 21.6% of all days are within ±1% of EMA50 (boundary-grazing)
4. Worst-case impact: ~0.5-1 UP_TRI signals/year wrongly demoted
   from DEPLOY to WATCH on jitter Choppy day
5. **Existing 10-day Bull activation gate already mitigates the
   first-Bull-day jitter risk** (worst case)

---

## Cross-scenario patterns

### Pattern 1: Stateless-per-scan architecture absorbs most regime-transition concerns

S1, S5 both confirm the same architectural truth: production scanner
has NO carry-forward state from previous scan days. Each scan day
re-fetches OHLCV, re-computes indicators, re-detects pivots, re-tags
with today's regime. Aging is "how many bars ago was the pivot",
computed within today's df only.

This means: any concern about "yesterday's regime contaminating
today's behavior" is structurally absorbed by the architecture. The
only persistent state is `signal_history.json` regime tag, which is
correctly fire-time-stamped (S1 Finding 3).

### Pattern 2: Lab cell findings ≠ production scoring rules

S3 and S5 both surfaced the same gap with different evidence:
**Lab discovered cell-specific kill/boost rules that are not in
production `mini_scanner_rules.json`.**

| Lab finding | Production state |
|---|---|
| Energy × Bull UP_TRI = SKIP (-2.9pp) | NOT in rules |
| vol_climax × BULL_PROXY = REJECT (-11pp Bear → universal) | NOT in rules |
| 7 Bear UP_TRI boost_patterns | IN rules (correct) |
| Bull-specific boost_patterns | NOT in rules (Gap 1) |

**Pre-activation work item:** populate `mini_scanner_rules.json`
with Bull cell findings before activation. This is one bundled task
covering boost + kill rules from Lab playbook recommendations. Maps
directly to `bull/PRODUCTION_POSTURE.md` Gap 1.

### Pattern 3: Sub-regime detector gap blocks the highest-impact filters

S2, S3, S5 all reference the same upstream gap: production has no
sub-regime classification layer, so Lab's best filters
(`recovery_bull × vol=Med × fvg_low` 74.1% WR; `healthy_bull × 20d=high`
62.5% WR) cannot be applied in production.

This is `bull/PRODUCTION_POSTURE.md` Gap 2. Already documented as
pre-activation work. Not new from S1-S5 but reinforced as the highest-
impact integration item.

---

## Production-prep deliverables (consolidated)

### MUST DO before Bull activation (3 items)

1. **Ship Bull rules to `mini_scanner_rules.json`** (S3 + S5):
   - kill_pattern: `Energy × Bull_UPTRI = SKIP` (Lab -2.9pp)
   - kill_pattern: `vol_climax × BULL_PROXY = REJECT` (Lab -11pp universal)
   - boost_patterns: from Bull cell playbooks (per-cell sub-regime
     × axis combinations)
   - **This is `PRODUCTION_POSTURE` Gap 1 expanded with S3/S5 specifics.**

2. **First-Bull-day briefing language** (S3 + S4 + S5):
   - Sector ranking lags ~15 days into new regime (S3)
   - Classifier may jitter on Day 1; trust 10-day gate (S4)
   - Bull BULL_PROXY is rarer + lower-WR than Bear UP_TRI;
     expect 1-2/day at WATCH level (S5)
   - **Bundles with `PRODUCTION_POSTURE` activation checklist
     trader-briefing item.**

3. **Sub-regime detector integration** (S2 + S5 referenced):
   - Production scanner gains `nifty_200d_return_pct` and
     `market_breadth_pct` features
   - Sub-regime classification layer added to enrichment pipeline
   - Boost rules can then reference `recovery_bull` /
     `healthy_bull` / etc.
   - **This is `PRODUCTION_POSTURE` Gap 2; the highest-impact
     unblocker for Bull cell strength.**

### NICE TO HAVE post-activation (4 items)

4. **Regime-aware vol_confirm scoring** (S2): consider reducing
   vol_confirm bonus from +1 to +0 or +0.5 in Bull (~2pp WR lift
   vs +6pp in Bear). Requires live Bull data for true calibration.

5. **Breadth-adjusted SecLead threshold** (S3): top-3 sectors by
   1m return rather than absolute >+2%. Restores discriminating
   power in broad Bull rallies.

6. **Classifier hysteresis** (S4): require 2 consecutive days at
   new regime before flipping tag. Reduces 17/12yr jitter to
   near-zero.

7. **regime_confidence field in Telegram digest** (S4):
   proximity-to-boundary score; helps trader interpret near-threshold
   days.

### NOT REQUIRED (deferred or non-issues)

- BULL_PROXY first-day flood mitigation (S5): non-issue, no work
  needed
- Bear-Bull transition state cleanup (S1): structurally impossible,
  no work needed
- Hard volume filter (S2): no filter exists, none needed

---

## Step 2 readiness assessment

**Step 2 is the next item in the 7-step Bull production-prep plan
(per session prompt context).** The 5 critique scenarios are
resolved at the documentation level. Production-prep deliverables
are now scoped + prioritized.

| Step 2 readiness check | Status |
|---|---|
| All 5 Sonnet scenarios investigated to verdict | ✅ DONE |
| Real gaps surfaced and quantified | ✅ DONE (3 must-do, 4 nice-to-have) |
| New gaps not in PRODUCTION_POSTURE | ✅ DONE (vol_climax × BULL_PROXY rule) |
| Cross-scenario architectural patterns documented | ✅ DONE (3 patterns) |
| Mitigations all documentation/rules-file (no code) | ✅ CONFIRMED |
| Pre-activation work items mapped to existing Gaps | ✅ DONE (Gap 1, Gap 2) |
| Step 2 scope unblocked | ✅ READY |

**Production code changes from Step 1: ZERO.**
**API spend from Step 1 (so far, before LLM critique): $0.**
**Atomic commits from Step 1: 5 (S1-S5).** + 1 (this SUMMARY) = 6 = matches plan.

---

## Honest accounting of limitations

1. **No first-Bull-day live data exists.** All conclusions about
   first-Bull-day behavior are based on (a) production scanner code
   inspection, (b) 12-year historical NIFTY classifier replay,
   (c) Lab cell lifetime data. Real first-Bull-day behavior in
   live production may surface effects not predicted here. The
   "monitor BULL_PROXY firing rate" item (S5 post-activation) is
   the live-data check.

2. **V3 replay used mid-Bull windows, not first-Bull-day windows.**
   The 2021-08-02 → 2021-08-13 and 2023-06-12 → 2023-06-23 windows
   are deep into Bull rallies. A future verification could replay
   actual first-Bull-day windows from the 18 historical Bear→Choppy→
   Bull transitions. Out of scope for Step 1.

3. **Sub-regime detector behavior on transition days is theoretical.**
   The recovery_bull / healthy_bull / etc. classification on Day 1 of
   Bull is INFERRED from sub-regime axis definitions (200d_return + breadth)
   but not empirically tested. Once sub-regime detector is
   integrated (Gap 2), real Day-1 classification will surface.

4. **Lab WR figures are lifetime, not live.** Bull cells have 0 live
   signals. Calibrated WR = lifetime baseline directly. No live
   inflation to remove. But also no live confirmation that lifetime
   data generalizes to current market structure. Bear UP_TRI showed
   +38.9pp live-vs-lifetime gap; whether Bull will show similar lift
   or compression is unknown.

---

## Recap

Step 1 of Bull production-prep complete. 5 of 5 critique scenarios
resolved or documented. 3 pre-activation must-do items consolidated
(all map to existing PRODUCTION_POSTURE Gaps 1 + 2). 4 nice-to-have
post-activation items captured. No scanner code changes. Step 2 is
unblocked.

LLM critique of this Step 1 summary appended next, before Step 1 closes.

---

## POST-CRITIQUE ADJUSTMENTS (Sonnet 4.5 review)

After running `_llm_critique.py` (output: `_llm_critique.md`),
Sonnet 4.5 surfaced 7 specific challenges. Honest accounting of
which adjustments to accept:

### Accepted as valid corrections

**1. S1 verdict slightly overconfident.** "Structurally impossible"
language assumed normal-market conditions. COVID-2020 had -13% single-
day moves. While 0 direct Bull↔Bear transitions in 12yr is empirical
fact, an unprecedented shock could in principle break the 30-day
Choppy buffer assumption. **Verdict revised in spirit**: structurally
impossible *under observed market regimes*; potential exposure window
in extreme tail (capped at ~3 trading days of in-flight signals due
to stateless-per-scan).

**2. S5 verdict assumes uncoordinated stock behavior.** A coordinated
news event (Budget, RBI rate cut, election surprise) could spike
BULL_PROXY to ~10-15 simultaneous fires by overriding per-stock
EMA50 lag. Still capped by 5-condition conjunction (candle pattern,
support proximity), so flood is bounded ~10x baseline, not 50x.
**Revised wording**: "low firing rate baseline; coordination events
3-5x normal; still bounded by conjunction filter."

**3. S2 "minor gap" framing understated.** If 38% of Bull signals
have vol_confirm=False AND ~25% of Bull DEPLOY-tier signals score
exactly 6, then ~10% of Bull DEPLOY pipeline is silently demoted to
WATCH by miscalibrated +1 bonus. Not minor. **Reframed**: scoring
asymmetry is the gap; manifests as tier demotion not signal drop.

**4. Missing S6 scenario: jitter wake-up surge.** Step 1 quantified
jitter (17 single-day events) but didn't model "what fires the day
AFTER a jitter Choppy day". On Choppy→Bull flip, all Bull cells
re-eligible — could see a 3-5x signal surge for the day. Compounds
S5 first-day concern. **Action**: add as documented gap (S6) for
post-activation monitoring; not blocking.

**5. MUST DO #3 (sub-regime detector) is overscoped as pre-activation.**
A 6-week feature (200d_return + breadth features, classifier, validator,
replay) cannot be MUST DO if next Bull activates in 30 days. **Revised
priority**: downgrade to NICE TO HAVE; Bull cells without sub-regime
detection underperform their potential but don't fire bad signals.

**6. Pre-activation rules audit should be Step 1.5.** Pattern 2 (Lab
findings ≠ production rules) confirmed across 3+ cells. Discovery
during Step 1 was reactive. Dedicated Step 1.5 = "rules audit per
cell × regime, with replay validation per ported rule" before any
Bull/Choppy activation.

**7. Fire drill is MUST DO, not optional.** 10-day Bull activation
gate could be re-purposed as shadow-mode fire drill: Bull cells emit
to test channel, daily standup reviews distribution against briefing,
exit criteria require 3 days of distribution within 2σ of expectations.
Cost zero (paper-trade); benefit substantial (de-risks first capital
deployment).

### Revised pre-activation must-do list

| # | Item | Revised priority |
|---|---|---|
| 1a | Ship Energy×Bull_UPTRI kill rule (1-line, low-risk) | **MUST DO — ship now** |
| 1b | Ship vol_climax×BULL_PROXY reject rule (1-line) | **MUST DO — ship now** |
| 1c | Ship boost_patterns from cell playbooks | **MUST DO — defer 2 weeks for WR validation** |
| 2 | First-Bull-day briefing | **MUST DO — ship 3 days before 10-day gate end** |
| 3 | Sub-regime detector integration (Gap 2) | **NICE TO HAVE — was MUST DO; downgraded** |
| 4 | Fire drill (10-day shadow mode) | **NEW MUST DO — re-use 10-day gate** |
| 5 | Step 1.5 — rules audit across all 10 Bull/Choppy cells | **NEW MUST DO — block Step 2 activation on this** |

### Step 2 readiness REVISED

| Step 2 phase | Blocked by |
|---|---|
| Code scaffolding (aging, bucketing, Telegram) | MUST DO #1a + #1b only |
| Replay testing | MUST DO #2 (briefing) |
| Activation decision | MUST DO #5 (rules audit) + MUST DO #4 (fire drill) |
| Capital deployment | All MUST DOs |

### Items rejected

**LLM suggestion #7 — squash summary commit into S5.** Rejected:
this SUMMARY contains net-new content (cross-scenario patterns,
prioritized deliverables, post-critique adjustments) that doesn't
fit any single S1-S5 file. Keeping as standalone S6 commit.

---

## Final state

| Step 1 closing metric | Value |
|---|---|
| Atomic commits | 6 (S1, S2, S3, S4, S5, SUMMARY+LLM) |
| Production code changes | 0 |
| API spend | $0.064 (LLM critique) |
| Original MUST DO items | 3 |
| Revised MUST DO items | 5 (split + 2 added) |
| Verdicts revised after LLM critique | 3 of 5 (S1, S2, S5 wording softened) |
| New scenarios surfaced | 1 (S6 jitter wake-up surge — documented gap) |
| Step 2 unblocked? | Code-scaffolding YES; Activation decision NO (Step 1.5 + fire drill required) |

Step 1 closes here. Step 1.5 (dedicated rules audit) and Step 2 (code
scaffolding) are next, with explicit gating from this revised checklist.
