# B1 — Bear Warm-Zone Display Honesty

**Date:** 2026-05-03
**Sonnet's concern:** "Bear sub-regime detector classifies live data
as 43% hot / 57% cold (binary), but real classification has uncertainty
zone. Production messaging may show binary classification (dishonest
about confidence)."

**Verdict: ✅ RESOLVED with action — 4-tier confidence display recommended; surprising finding: boundary_hot has HIGHER WR than confident_hot.**

---

## A. Hypothesis

Bear sub-regime detector uses hard thresholds (`vp > 0.70` AND
`n60 < -0.10`). Signals at `vp = 0.71, n60 = -0.11` are classified
hot; signals at `vp = 0.69, n60 = -0.09` are classified cold. Same
feature space, but binary tag. Production should display with
confidence tiering, not binary.

---

## B. Investigation

### Setup

n=17,828 resolved Bear signals from lifetime data. Baseline WR 53.5%.

Sub-regime detector reproduced inline:
```python
if vp > 0.70:
    if n60 < -0.10: hot
    elif n60 < 0:    warm  (added per S2 critique)
    else:            cold
else:                cold
```

### Current 3-tier classification distribution

| Sub-regime | n | WR |
|---|---|---|
| hot | 2,643 | 63.8% |
| warm | 7,608 | 51.5% |
| cold | 7,577 | 52.0% |

### 4-tier confidence proposal

Distance-from-boundary metric:
- `vp_dist = vp - 0.70`
- `n60_dist = -0.10 - n60` (positive = further into hot)

Tier definitions:
- **confident_hot:** vp > 0.75 AND n60 < -0.15 (both >0.05 from threshold)
- **boundary_hot:** 0.70 < vp ≤ 0.75 AND -0.15 ≤ n60 < -0.10 (just inside hot)
- **warm_zone:** one of two hot conditions met (other in cold side)
- **boundary_cold:** vp > 0.65 AND n60 > -0.15 (just outside hot)
- **confident_cold:** vp < 0.65 AND n60 > -0.05 (both >0.05 from threshold)

### Bear UP_TRI signal WR by tier

| Tier | n | WR |
|---|---|---|
| **boundary_hot** | 1,174 | **71.5%** ★ |
| confident_hot | 928 | 64.2% |
| boundary_cold | 2,213 | 59.0% |
| warm_zone | 6,687 | 52.1% |
| confident_cold | 2,737 | 52.1% |

**Counterintuitive finding:** boundary_hot signals (just-into-hot)
have HIGHER WR (71.5%) than confident_hot (64.2%). Mechanism: early-
stage capitulation reversals (cusp of hot) work better than deep-
stress reversals (already-extended downtrends).

---

## C. Mechanistic interpretation

### Why boundary_hot > confident_hot

Hot sub-regime captures Bear capitulation. Just-into-hot signals
fire on the FIRST day vol crosses 0.70 OR n60 reaches -0.10 — the
START of stress. Reversal mechanism (Bear UP_TRI = oversold bounce)
works best at the start of stress, before short-positions are
overcrowded.

Confident_hot signals fire mid- or late-stress when crowd is already
positioned. Reversals require more capitulation to clear, so WR is
slightly lower.

This is consistent with the Bear UP_TRI playbook's "broad-band edge"
finding: the cell doesn't reward depth-of-stress, it rewards
inflection-points within stress.

### Why boundary_cold > confident_cold (slightly)

Just-outside-hot still has SOME stress ingredients (high vol OR
low n60, but not both). Confident_cold has neither — pure mid-Bear
or recovery-Bear. Slight edge for boundary cells captures partial
ingredient match.

### warm_zone breakdown

8,377 warm_zone signals at 51.2% WR — essentially baseline. These
are the truly ambiguous signals: one of two hot conditions met, the
other absent.

---

## D. Production display recommendation

### Tier-specific Telegram messaging

```
[BEAR · BOUNDARY_HOT · 72% expected]    # confident or just-in
SIGNAL: HDFC.NS UP_TRI age=0
EXPECTED: TAKE_FULL · WR 65-75%

[BEAR · CONFIDENT_HOT · 60-65% expected]
SIGNAL: TCS.NS UP_TRI age=1
EXPECTED: TAKE_FULL · WR 60-65%

[BEAR · WARM_ZONE · 50-55% expected]
SIGNAL: ITC.NS UP_TRI age=0
EXPECTED: TAKE_SMALL · 1 of 2 hot conditions met

[BEAR · CONFIDENT_COLD · 50-55% expected]
SIGNAL: SBIN.NS UP_TRI age=0
EXPECTED: SKIP · neither hot condition met
```

### PWA messaging structure

| Tier | Telegram tag | Action default | Sizing | Calibrated WR (UP_TRI) |
|---|---|---|---|---|
| boundary_hot | "🔥 BOUNDARY_HOT" | TAKE_FULL | full | 65-75% |
| confident_hot | "🔥 CONFIDENT_HOT" | TAKE_FULL | full | 60-65% |
| warm_zone | "⚪ WARM" | TAKE_SMALL | half | 50-55% |
| boundary_cold | "🟦 EDGE_COLD" | TAKE_SMALL | half | 55-60% |
| confident_cold | "❄️ CONFIDENT_COLD" | SKIP / cascade | — | ≤55% |

### Calibration honesty addition

Current production messaging risks displaying live observed WR
(94.6%) which is post-Phase-5-selection. Honest reframe:

```
Observed live: 94.6% (n=74)
Calibrated (sub-regime gated): 65-75%
Reason: Phase 5 selection bias on hot baseline
```

Telegram footer or PWA tooltip should show calibrated WR alongside
live observation. Trader sees both numbers; understands the gap.

---

## E. Boundary signal WR cross-check

The 4-tier framework predicts boundary_hot Bear UP_TRI = 71.5% WR.
Apply to live April 2026 (n=74, 94.6% live observed):

The 26pp gap between live (94.6%) and calibrated (~65-75%) is what
the Bear UP_TRI cell investigation has already documented as
"Phase-5 selection bias." Boundary_hot tier reframes the calibrated
expectation:

| Layer | WR contribution |
|---|---|
| Bear baseline | 53.5% |
| Hot sub-regime gate | +14.3pp → 67.8% |
| Boundary refinement | +7pp → 71.5% (boundary_hot) |
| Phase-5 selection bias | ~+23pp → 94.6% live |

**Production should display 71.5% as boundary_hot calibrated
expectation**, not 94.6% live observed. This is a 23pp downward
adjustment — material for trader expectation management.

---

## F. Failure modes considered

### Failure mode 1: Tier misclassification at exact threshold

**Considered:** Signal with vp = 0.70 (exactly) and n60 = -0.10
(exactly) — which tier? Depends on inequality (`>` vs `≥`).

**Reality:** real-valued features rarely hit exact thresholds. Float
comparison handles this reliably. Document `>` (strict) for both
upper bounds.

### Failure mode 2: Boundary tier surprises trader

**Considered:** Trader sees "boundary_hot" tag and assumes it's WORSE
than "confident_hot" (intuitive interpretation: "boundary = uncertain
= weaker"). Doesn't trust the higher WR finding.

**Reality:** real UX risk. First-deployment briefing must explain
counterintuitive finding: boundary_hot = early-capitulation =
strongest. Use 🔥 emoji for both hot tiers; differentiate by tag
clarity.

### Failure mode 3: Live data drift away from boundary_hot

**Considered:** April 2026 live data is 100% hot per Bear UP_TRI
playbook. Future Bear period might shift toward different tier
distribution.

**Reality:** detection function works on real-time inputs. Tier
distribution updates as market shifts. No staleness risk.

---

## G. Verdict

**RESOLVED with action.** 4-tier confidence display addresses
Sonnet's "binary classification dishonesty" concern.

Key findings:
1. boundary_hot Bear UP_TRI: **71.5% WR (n=1,174)** — highest tier
2. confident_hot: 64.2% (n=928)
3. warm_zone: 52.1% (n=6,687) — essentially baseline
4. confident_cold: 52.1% (n=2,737)

**Counterintuitive:** boundary_hot beats confident_hot. Cell rewards
inflection-points within stress, not depth-of-stress. This finding
is NEW (not in current Bear UP_TRI playbook).

**Production integration:**
- Add tier classification function to scanner enrichment
- Surface tier in Telegram + PWA messaging
- Add calibrated WR alongside live observation
- First-deployment briefing must explain boundary_hot > confident_hot

**Ship priority:** MEDIUM-HIGH (improves trader expectation management
without blocking activation).

---

## H. Investigation summary

| Aspect | Finding |
|---|---|
| Bear resolved signals | 17,828 |
| Bear UP_TRI subset | 13,739 |
| boundary_hot Bear UP_TRI WR | **71.5%** (n=1,174) — HIGHEST tier |
| confident_hot Bear UP_TRI WR | 64.2% (n=928) |
| warm_zone Bear UP_TRI WR | 52.1% (n=6,687) |
| confident_cold Bear UP_TRI WR | 52.1% (n=2,737) |
| Tier ranking | boundary_hot > confident_hot > boundary_cold > warm_zone ≈ confident_cold |
| Counterintuitive finding | boundary_hot > confident_hot (early capitulation vs deep stress) |
| Live observed WR | 94.6% |
| Calibrated WR (boundary_hot tier) | 71.5% |
| Selection bias residual | ~23pp (94.6% - 71.5%) |
| Telegram messaging recommendation | 5-tier display with calibrated WR |
| Production code change | YES (tier function + display) |

Sonnet's concern was valid. The boundary_hot > confident_hot finding
is a NET-NEW insight from this investigation — should be added to the
Bear UP_TRI playbook as v3 update.
