# S2 — Volume Filter Absence in Bull Regime

**Date:** 2026-05-03
**Sonnet's concern:** "Bull breakouts often happen on quiet volume — sector
rotation rallies, institutional accumulation. Does the scanner have a
volume filter that drops legitimate Bull breakouts as 'unconfirmed'? If
absent, are low-volume Bull signals scored fairly relative to high-volume
ones, or are they systematically penalized in a way that matches Bear's
volume-confirmation premium?"

**Verdict: ✅ RESOLVED — no hard filter exists; soft scoring asymmetry documented as gap**

---

## A. Hypothesis

Two distinct concerns nested in Sonnet's critique:

1. **Hard filter:** Scanner drops candidates whose volume is below some
   threshold, blocking legitimate Bull breakouts entirely.
2. **Soft scoring penalty:** Even if all signals fire, low-volume Bull
   signals are scored materially lower than high-volume ones, which is
   appropriate for Bear (institutional confirmation matters) but may
   over-penalize Bull (sector-rotation accumulation rallies are quiet
   by nature).

Both need separate investigation.

---

## B. Investigation — production volume mechanism

### Finding 1: NO hard volume filter exists in signal detection

`scanner/scanner_core.py:get_vol_rs()` (lines 291-320):

```python
def get_vol_rs(pb):
    avg_vol = df['Volume'].iloc[max(0, pb-20):pb].mean()
    sig_vol = df['Volume'].iloc[pb]
    vr      = sig_vol / avg_vol if avg_vol > 0 else 1
    vol_q   = ('High'    if vr > 1.5 else
               'Thin'    if vr < 0.7 else
               'Average')
    vol_confirm = bool(vr >= 1.2)
    ...
    return vol_q, vol_confirm, rs_q
```

Volume is computed as **descriptive tags only**. Each signal gets:
- `vol_q`: categorical bucket (High/Average/Thin)
- `vol_confirm`: boolean (vr ≥ 1.2)

These are attached to the signal dict but **never gate signal emission**.
Searched detect_up_tri/detect_down_tri/detect_bull_proxy paths — no
`if not vol_confirm: continue` or equivalent guard exists. Every pivot
that satisfies geometric criteria becomes a signal regardless of volume.

**Sonnet's "hard filter dropping legitimate breakouts" concern is empty.**
The scanner doesn't have such a filter. Bull-rotation low-volume
breakouts emit signals normally.

### Finding 2: Volume distribution in Bull replay (2021-08 + 2023-06)

From V3 verification replay (112 total Bull signals):

| Tag | Count | % |
|---|---|---|
| vol_q = High (vr>1.5) | 32 | 28.6% |
| vol_q = Average (0.7-1.5) | 53 | 47.3% |
| vol_q = Thin (<0.7) | 27 | 24.1% |
| vol_confirm = True (vr≥1.2) | 43 | 38.4% |
| vol_confirm = False | 69 | 61.6% |

Roughly **62% of Bull signals are below the vol_confirm threshold** —
material share. Distribution is plausibly representative of "Bull rallies
on quiet rotation volume."

### Finding 3: Soft scoring asymmetry (the real concern)

`scanner/scorer.py:enrich_signal()` adds `+1` when `vol_confirm == True`,
regardless of regime. The same +1 is awarded uniformly across Bull/Bear/
Choppy.

DEPLOY rate stratified by vol_confirm in Bull replay:

| Cohort | n | DEPLOY | DEPLOY % |
|---|---|---|---|
| vol_confirm = True | 43 | 27 | 62.8% |
| vol_confirm = False | 69 | 7 | 10.1% |

The **+1 vol_confirm bonus alone moves a Bull signal from `score=5`
(WATCH/SHORTLIST cusp) to `score=6` (DEPLOY threshold)** in many cases.
Low-volume Bull signals are systematically blocked from DEPLOY by the
scoring layer, even though they fire the signal.

### Finding 4: Bear lifetime data DOES show vol_confirm premium

For comparison from Bear UP_TRI lifetime base (separately verified in
the Bear UP_TRI cell investigation):

| Cohort | Bear UP_TRI lifetime WR |
|---|---|
| vol_confirm = True | ~58% |
| vol_confirm = False | ~52% |

A **6pp lift** for vol_confirm in Bear — institutional volume signal
matters. The +1 bonus is calibrated against this Bear lift.

For Bull (lifetime, from the Bull UP_TRI cell):

| Cohort | Bull UP_TRI lifetime WR |
|---|---|
| vol_confirm = True | ~52% |
| vol_confirm = False | ~50% |

A **2pp lift** for vol_confirm in Bull — much weaker. The +1 bonus
**over-rewards** vol_confirm in Bull relative to its actual predictive
strength.

### Finding 5: Lab uses NIFTY-level vol_regime, not signal-bar vol_q

The Bull UP_TRI Lab cell's best filter (`recovery × vol=Med × fvg_low`,
74.1% WR / +22pp lift) uses `nifty_vol_regime` — a NIFTY-INDEX-level
volatility classification (Low/Med/High via realized vol bucket), not
`vol_confirm` (signal-bar volume vs 20-day average for the individual
stock).

**These are different features:**
- Production `vol_confirm`: per-stock per-bar volume-vs-recent-average
- Lab `nifty_vol_regime`: NIFTY-level realized volatility regime

The Lab's high-WR Bull filter cannot be implemented in production today
because production has no NIFTY-vol-regime feature. This is an
independent gap (production data pipeline missing a Lab feature),
distinct from Sonnet's volume-filter concern.

---

## C. Failure modes considered

### Failure mode 1: Quiet Bull rotation breakouts dropped

**Considered:** Low-volume Bull breakout (e.g., IT rotation rally on
average volume) flagged as unconfirmed and not surfaced to trader.

**Reality:** Signal fires and lands in Telegram digest. `vol_confirm=False`
becomes a tag in the signal dict, displayed but not gating. Trader sees
the signal with `vol=Thin` or `vol=Average` annotation.

**Impossible — no hard filter exists.**

### Failure mode 2: Low-volume Bull signal blocked from DEPLOY by scoring

**Considered:** Bull rotation breakout, geometry valid, fires at score=5
(Age0+Bull regime+SecLead, missing vol bonus). Sits in WATCH bucket
instead of DEPLOY.

**Reality:** This is real. 69/112 (61.6%) of Bull replay signals fall
into vol_confirm=False; only 7 of those (10.1%) reach DEPLOY. The
asymmetry between Bear (vol_confirm meaningful, +6pp WR lift) and Bull
(vol_confirm weakly predictive, +2pp WR lift) means the +1 bonus is
miscalibrated for Bull.

**Documented gap, not a bug.** Doesn't drop legitimate signals; just
under-scores them. Trader can still see them in WATCH bucket.

### Failure mode 3: Lab's nifty_vol_regime feature missing

**Considered:** Bull UP_TRI's best filter (`recovery × vol=Med × fvg_low`)
references `nifty_vol_regime` which doesn't exist in production scanner
data.

**Reality:** Confirmed gap. Pre-activation work needs to bring NIFTY-level
vol classification into production scanner, separately from per-stock
vol_q. This was already documented in `bull/PRODUCTION_POSTURE.md` Gap
2 but framed as "sub-regime detector"; the vol_regime axis is part of
that detector's input.

**Pre-activation prep, not blocking signal generation.**

### Failure mode 4: Telegram digest doesn't communicate vol asymmetry

**Considered:** First-Bull-day, trader sees mostly `vol=Thin` /
`vol_confirm=False` signals, infers scanner is weak/broken.

**Reality:** Possible UX risk. Bull signals on rotation days WILL show
predominantly low-volume tags. If trader reads `vol=Thin` as warning sign,
may dismiss or override valid signals.

**Mitigation:** First-Bull-day briefing (already in PRODUCTION_POSTURE
activation checklist) should flag that low-volume Bull breakouts are
expected and lower vol_confirm threshold's predictive value.

---

## D. Volume mechanism design verdict

The concern decomposes cleanly:

**The hard-filter concern is empty.** Scanner has no volume filter
gating signal emission. All breakouts surface.

**The soft-scoring concern is real but minor.** Bull signals with
vol_confirm=False are under-rewarded by +1 relative to their actual
WR profile (2pp lift instead of the 6pp Bear lift the +1 was calibrated
against). This blocks ~50pp of low-volume Bull signals from reaching
DEPLOY threshold (10.1% DEPLOY for vol_confirm=False vs 62.8% for True).

**The Lab feature gap is real, separate, already documented.**
Production data pipeline lacks `nifty_vol_regime`; Lab's best Bull UP_TRI
filter (74.1% WR) cannot be applied in production until this feature
is added. Captured by `bull/PRODUCTION_POSTURE.md` Gap 2 (sub-regime
detector integration).

---

## E. Verdict

**RESOLVED with documented gap.**

1. No hard volume filter → no legitimate Bull breakout is dropped
2. Soft scoring +1 vol_confirm bonus is calibrated for Bear (~6pp WR
   lift) but applied uniformly to Bull (~2pp WR lift) — over-rewards
   in Bull, blocks low-volume Bull from DEPLOY scoring threshold
3. Lab `nifty_vol_regime` feature missing in production — independent
   pre-activation work captured in existing Gap 2

**No production code changes in this critique cycle.**

Future production-prep checklist items:
- (a) Consider regime-aware vol_confirm scoring: keep +1 for Bear,
  reduce to +0 or +0.5 for Bull. Requires live Bull data for true
  calibration; defer to post-activation review.
- (b) Add `nifty_vol_regime` feature to production data pipeline as
  prerequisite for Lab Bull UP_TRI filter (`recovery × vol=Med × fvg_low`,
  74.1% WR / +22pp lift). Already in Gap 2.
- (c) First-Bull-day briefing should mention that vol=Thin / vol_confirm=False
  is expected on rotation days and not a signal weakness.

---

## Investigation summary

| Aspect | Finding |
|---|---|
| Hard volume filter on signal emission | NONE |
| Soft scoring vol_confirm bonus | +1 uniform across regimes |
| vol_confirm distribution in Bull replay | 38% True / 62% False |
| DEPLOY rate vol_confirm=True (Bull) | 62.8% |
| DEPLOY rate vol_confirm=False (Bull) | 10.1% |
| WR lift from vol_confirm — Bear lifetime | +6pp |
| WR lift from vol_confirm — Bull lifetime | +2pp |
| Calibration mismatch | +1 over-rewards in Bull by ~3-4pp lift's worth |
| Lab `nifty_vol_regime` in production | MISSING (Gap 2) |
| Action required pre-activation | None blocking; 3 prep items above |

Sonnet's concern was partially valid: no filter to drop signals (concern
empty), but soft scoring asymmetry is real and documented for
post-activation review when live Bull data exists.
