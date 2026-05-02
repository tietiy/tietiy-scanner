# Choppy Sub-Regime Detector — Design + Validation

**Date:** 2026-05-02 night
**Module:** `lab/factory/choppy/subregime/detector_design.py`
**Validation output:** `lab/factory/choppy/subregime/detector_validation.json`
**Scope:** classify any Choppy market state into stress / balance / quiet
sub-regime, with optional breadth-qualified subtype.

---

## Why this detector

The L1-L5 comprehensive lifetime exploration
([`../lifetime/synthesis.md`](../lifetime/synthesis.md)) established that
Choppy regime is **tri-modal**, not uniform:

| Sub-regime | Vol percentile | Lifetime share | UP_TRI baseline |
|---|---|---|---|
| quiet | < 0.30 | 22.5% | 55.1% |
| balance | 0.30 – 0.70 | 49.8% | **49.2% (hostile)** |
| stress | > 0.70 | 27.7% | 55.7% |

Filter behavior depends on which sub-regime is active (e.g.,
`market_breadth=medium` UP_TRI lifts +7.9pp in stress but inverts to −5.5pp
in balance). Production scanner cannot apply lifetime-derived filters
correctly without knowing the current sub-regime.

This detector is the missing classification layer.

---

## Feature selection

### Primary axis — `nifty_vol_percentile_20d`

20-day rolling percentile rank of NIFTY's daily volatility. Already computed
in feature pipeline. Deterministic boundaries observed in lifetime data:

| Categorical level | Percentile range |
|---|---|
| Low | min=0.006, max=0.299 |
| Medium | min=0.300, max=0.700 |
| High | min=0.700, max=0.993 |

Boundaries are baked into the feature definition (the categorical
`feat_nifty_vol_regime` is a discretization of `feat_nifty_vol_percentile_20d`
at exactly these breakpoints). Detector uses the underlying continuous
percentile so future refinements (sliding thresholds, transition-state
detection) remain feasible.

### Secondary axis — `market_breadth_pct`

Cross-section breadth: pct of universe stocks above 50-day SMA. Used as a
qualifier inside each sub-regime to produce subtype labels:

| Breadth qualifier | Range |
|---|---|
| low_breadth | < 0.30 |
| med_breadth | 0.30 – 0.60 |
| high_breadth | > 0.60 |

Breadth was the dominant feature in L3's combinatorial search
(`market_breadth_pct=medium` anchors top combos for both UP_TRI and
DOWN_TRI). Adding it as a subtype dimension gives 9 cells (3×3) instead of
3, allowing finer-grained filter targeting.

### Why not these features

| Feature | Reason excluded |
|---|---|
| `vix_level` | High correlation with `nifty_vol_percentile_20d`; redundant |
| `nifty_20d_return_pct` | Trend feature, not regime-state; orthogonal but not a sub-regime axis |
| `advance_decline_ratio_20d` | Highly correlated with `market_breadth_pct` |
| Breadth-change rate (Δ breadth) | Useful for *transition* detection, not steady-state classification — proposed for v2 detector |
| Volatility-of-volatility | Computable but not in current feature set; v2 candidate |

---

## Decision rules (pseudo-code)

```python
def detect_subregime(nifty_vol_percentile_20d, market_breadth_pct):
    vp = nifty_vol_percentile_20d
    br = market_breadth_pct

    # Primary classification
    if vp < 0.30:
        sub = "quiet"
    elif vp > 0.70:
        sub = "stress"
    else:
        sub = "balance"

    # Confidence: distance from boundary, normalized 0-100
    if sub == "quiet":
        conf = (0.30 - vp) / 0.30 * 100
    elif sub == "stress":
        conf = (vp - 0.70) / 0.30 * 100
    else:
        # balance: how centered in [0.30, 0.70]
        conf = (1.0 - abs(vp - 0.50) / 0.20) * 100

    # Secondary: breadth qualifier
    if br < 0.30:
        breadth_qual = "low_breadth"
    elif br > 0.60:
        breadth_qual = "high_breadth"
    else:
        breadth_qual = "med_breadth"

    return {
        "subregime": sub,
        "subtype": f"{sub}__{breadth_qual}",
        "confidence": conf,
        "vol_percentile": vp,
        "breadth": br,
    }
```

Full implementation: `detector_design.py` lines 50-115.

---

## Historical validation

### A. Distribution agreement

Detector lifetime classification (n=35,290 Choppy signals):

| Sub-regime | n | % |
|---|---|---|
| quiet | 7,954 | 22.5% |
| balance | 17,564 | 49.8% |
| stress | 9,772 | 27.7% |

Cross-tab against the existing categorical `feat_nifty_vol_regime`:
**100% agreement** (perfect diagonal) — expected since both derive from
the same percentile thresholds. The detector adds value through (a) the
continuous-confidence output and (b) the subtype dimension.

### B. WR pattern reproduction

Detector sub-regime × signal_type WRs reproduce L1's `by_signal_x_vol`
pattern exactly:

| Signal | quiet | balance | stress |
|---|---|---|---|
| UP_TRI | 55.1% | **49.2% (hostile)** | 55.7% |
| DOWN_TRI | 40.1% | **51.4% (best)** | 43.0% |
| BULL_PROXY | 52.1% | 48.6% | 49.3% |

Confirms the tri-modal hypothesis: UP_TRI prefers stress/quiet, DOWN_TRI
prefers balance, BULL_PROXY is structurally indifferent.

### C. Subtype refinement (n≥100, surprising findings)

| Signal | Subtype | n | WR | Note |
|---|---|---|---|---|
| UP_TRI | stress__med_breadth | 4,954 | **60.1%** | L3 winner — confirmed |
| UP_TRI | stress__low_breadth | 372 | **20.2%** | catastrophic; AVOID |
| UP_TRI | quiet__low_breadth | 359 | **65.1%** | new finding — strong |
| UP_TRI | balance__high_breadth | 4,760 | 54.0% | balance hostility is breadth-specific |
| UP_TRI | balance__med_breadth | 7,762 | 46.8% | the actual hostile cell |
| UP_TRI | balance__low_breadth | 1,262 | 45.8% | also weak |
| DOWN_TRI | balance__med_breadth | 1,903 | **55.2%** | L3 DOWN_TRI winner — confirmed |
| DOWN_TRI | quiet__high_breadth | 488 | 39.5% | weak |
| DOWN_TRI | stress__low_breadth | 151 | 35.3% | weak (small n) |
| BULL_PROXY | quiet__high_breadth | 178 | 57.1% | best BULL_PROXY cell |
| BULL_PROXY | balance__high_breadth | 294 | 55.8% | second-best |

**New findings beyond L1-L5:**
- UP_TRI `stress__low_breadth` is catastrophic (20.2%) — much weaker than
  stress aggregate (55.7%). Low breadth in stress = panic capitulation,
  triangles fail because there's no buying support.
- UP_TRI `quiet__low_breadth` is surprisingly strong (65.1%, n=359). Hard
  to explain — may be selection effect (only well-positioned stocks
  triangulate during quiet/low-breadth periods).
- The "balance is hostile" finding from L1 is **breadth-specific**:
  balance__med_breadth is hostile (46.8%) but balance__high_breadth is
  positive (54.0% UP_TRI, 55.8% BULL_PROXY).

---

## Current live classification (April 2026+)

| Field | Value |
|---|---|
| n recent Choppy signals (≥ 2026-04-01) | 366 |
| Dominant sub-regime | **stress** (100% of recent) |
| Top subtype | `stress__high_breadth` (319 / 87%) |
| Second subtype | `stress__med_breadth` (47 / 13%) |

**Implication for current production:**
- F1 (live-derived: ema_bull + coiled=medium) was tuned on `stress` data,
  predominantly `stress__high_breadth` — that's the regime where it works
- L3 lifetime-validated UP_TRI combo (`breadth=medium × vol=High × MACD bull`)
  maps to `stress__med_breadth` subtype — only 13% of live signals
- L3 DOWN_TRI combo (`breadth=medium × vol=Medium`) maps to
  `balance__med_breadth` subtype — **0% of recent live data**

The current live window is essentially one slice of the full sub-regime
space. Lifetime-derived filters mapped to other sub-regimes have not been
exercised in 2026.

---

## Production integration plan

### Where the detector runs

**Once per trading day, post-market open (~9:20 IST)**, as part of the
PRE_MARKET composer or scanner initialization phase. Inputs are
universe-level (NIFTY vol + market breadth), not per-signal — so detector
runs once and the label is shared across all Choppy signals that day.

```
9:15 IST: market opens
9:20 IST: scanner initialization
  → fetch NIFTY OHLCV (already happening)
  → compute nifty_vol_percentile_20d (already in feature pipeline)
  → compute market_breadth_pct (already in feature pipeline)
  → call detect_subregime()
  → write current_subregime.json to output/
9:25 IST: signal scan + per-signal feature join
  → Choppy signals get tagged with current sub-regime
  → barcode_match logic uses sub-regime to select filter set
```

### Output format

`output/current_subregime.json`:
```json
{
  "scan_date": "2026-05-02",
  "regime": "Choppy",
  "subregime": "stress",
  "subtype": "stress__high_breadth",
  "confidence": 75.0,
  "vol_percentile": 0.825,
  "breadth": 0.723,
  "filter_recommendation": {
    "UP_TRI": "F1_active (regime-shift adaptive)",
    "DOWN_TRI": "no lifetime filter active",
    "BULL_PROXY": "REJECT (KILL verdict)"
  }
}
```

### Barcode_match consumption

`scanner/barcode_match.py` reads `current_subregime.json` and picks the
appropriate filter set per signal type:

```python
def choppy_filter_for_signal(signal, current_subregime):
    if signal.signal_type == "BULL_PROXY":
        return "REJECT"

    sub = current_subregime["subregime"]
    subtype = current_subregime["subtype"]

    if signal.signal_type == "UP_TRI":
        if sub == "stress":
            # F1 was tuned on stress data — apply F1
            return apply_F1(signal)
        elif sub == "balance":
            # Apply L3 combo IF subtype matches — but balance__med_breadth
            # is hostile. Wait for breadth=high subtype to deploy.
            if subtype == "balance__high_breadth":
                return "TAKE_SMALL"
            else:
                return "SKIP"
        elif sub == "quiet":
            # L4 didn't surface a filter for quiet; default conservative
            return "SKIP_OR_TAKE_SMALL"

    if signal.signal_type == "DOWN_TRI":
        if sub == "balance":
            # Apply L3 winning DOWN_TRI combo
            return apply_balance_med_breadth_filter(signal)
        else:
            return "SKIP"

    return "SKIP"
```

### Performance overhead

- Detector itself: O(1) per call (two threshold comparisons)
- Daily compute: < 1 ms (single call per scan day)
- Storage: ~200 bytes JSON per day

Negligible. No need for caching beyond standard JSON write.

### Failure modes

| Failure | Handling |
|---|---|
| `nifty_vol_percentile_20d` missing | subregime = "unknown"; scanner reverts to F1-only logic (current behavior) |
| `market_breadth_pct` missing | subtype = "{sub}__unknown"; subregime unaffected |
| Edge case: vol_percentile exactly = 0.30 or 0.70 | Uses `<` and `>` strict comparisons; 0.30 → balance, 0.70 → balance (boundary cases get balance) |
| Detector disagrees with `feat_nifty_vol_regime` | Currently impossible (same thresholds); if v2 introduces drift, surface alert |

---

## Limitations and v2 candidates

### Known limitations

1. **No transition-state detection.** A market exiting "stress" → "balance"
   is currently labeled balance immediately, even if breadth/vol signals
   are still mid-transition. Quarterly Phase-5 data may show transition
   periods are their own micro-regime.

2. **Breadth thresholds inherited from feature spec, not optimized.**
   The 0.30/0.60 cutoffs come from `market_breadth_pct` feature definition.
   Whether 0.40/0.55 or other cutoffs would produce cleaner sub-regimes is
   untested.

3. **Confidence score is geometric, not statistically calibrated.**
   "75% confidence" means 75% of the way from boundary to extreme; it does
   NOT mean P(true subregime is X | features) = 0.75.

4. **Single-day classification.** No persistence smoothing (e.g., 5-day
   moving label). One outlier day can flip the label even if underlying
   regime hasn't shifted.

### v2 enhancement candidates

1. **Add Δ breadth (5-day breadth change rate)** as a transition signal.
   Distinguishes stable stress from collapsing-stress (entering quiet).

2. **Add volatility-of-volatility** (std of vol_percentile_20d over last
   20 days). Distinguishes "settled stress" from "spiky stress".

3. **EMA smoothing on subregime label** — e.g., require 3 consecutive
   days of same label before flipping to suppress noise.

4. **Statistically-calibrated confidence** — fit a logistic model
   predicting WR from features; output P(WR > baseline | features).

5. **Per-subtype filter mapping table** — populated from quarterly Phase-5
   data once each subtype accumulates ≥30 live signals.

---

## Open questions for tomorrow's review

1. Should detector also handle Bear / Bull regimes, or is this Choppy-only
   (different detector per regime)?
2. Does the production scanner currently load `nifty_vol_percentile_20d`
   in its market-data fetch, or only at signal-feature-join time?
3. Should `current_subregime.json` be a single point-in-time snapshot, or
   maintain a rolling history (e.g., last 30 days of subregime labels)?
4. When a balance__med_breadth UP_TRI signal fires (the lifetime hostile
   cell), should scanner SKIP or output a CAUTION label?
5. Is the `quiet__low_breadth` UP_TRI 65.1% finding (n=359) worth
   investigating as a separate cell, or is it likely a survivor-bias
   artifact?
