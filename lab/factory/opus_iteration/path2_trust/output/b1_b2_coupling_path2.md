# B1 / B2 Coupling — Path 2 Spec

## Decision

**Ship B1 (4-tier display) NOW. Defer B2 (sigmoid scoring) to Phase-2.**

B1 and B2 are alternative mechanisms for the same finding (boundary_hot
beats confident_hot in Bear UP_TRI). Production should ship one, not
both. B1 is operationally simpler and fits the existing
percentile-bucket architecture; B2's sigmoid requires continuous-feature
support not yet present.

---

## B1 — 4-tier confidence display (SHIP NOW)

### Tier definitions

Computed from `nifty_vol_percentile_20d (vp)` and
`nifty_60d_return_pct (n60)`:

```python
def classify_bear_tier(vp, n60):
    if vp > 0.75 and n60 < -0.15:
        return "confident_hot"
    if vp > 0.70 and -0.15 <= n60 < -0.10:
        return "boundary_hot"
    if vp > 0.70 and n60 < -0.10:
        return "boundary_hot"  # default for hot region not confident
    if vp > 0.65 and n60 > -0.15:
        return "boundary_cold"
    if vp > 0.70 or n60 < -0.10:
        return "warm_zone"  # one-of-two hot conditions
    if vp < 0.65 and n60 > -0.05:
        return "confident_cold"
    return "warm_zone"  # default fallback
```

### Per-tier WR mapping (calibrated from B1 lifetime data)

| Tier | n | WR | Production action |
|------|---|----|---------|
| boundary_hot | 1,174 | **71.5%** ★ | TAKE_FULL (highest WR) |
| confident_hot | 928 | 64.2% | TAKE_FULL |
| boundary_cold | 2,213 | 59.0% | TAKE_SMALL |
| warm_zone | 6,687 | 52.1% | TAKE_SMALL or SKIP per cascade |
| confident_cold | 2,737 | 52.1% | SKIP unless Tier 1 cascade match |

### Telegram messaging

```
[BEAR · BOUNDARY_HOT · 71% expected]
SIGNAL: HDFC.NS UP_TRI age=0
EXPECTED: TAKE_FULL · WR 65-75%

[BEAR · CONFIDENT_HOT · 64% expected]
SIGNAL: TCS.NS UP_TRI age=1
EXPECTED: TAKE_FULL · WR 60-65%
```

### Counter-intuitive finding briefing

Trader must understand: **boundary_hot > confident_hot**. Mechanism:
early-capitulation reversals (cusp of stress) work better than
deep-stress reversals (already-extended). First-day briefing must
explain this OR risk trader dismissing boundary_hot signals as "weaker."

### Coupling to rules

- `rule_008` (Bear UP_TRI hot baseline): tier classification adds
  precision but base rule remains operative
- Sizing modifier:
  - boundary_hot: full
  - confident_hot: full
  - warm_zone: half
  - boundary_cold: half
  - confident_cold: skip (unless cascade match)

---

## B2 — Sigmoid scoring (DEFER)

### Why deferred

1. **Continuous-feature scoring not yet supported in schema.** Adding
   `continuous_score_function` rule type is non-trivial.
2. **B1 captures same finding via tiered display.** Shipping both
   creates UX confusion.
3. **Sigmoid parameters fitted to lifetime data.** Need quarterly
   re-fit cadence not yet established.
4. **Verdict re-mapping required.** Soft TAKE_SMALL has higher WR
   than soft TAKE_FULL — production must re-label, which complicates
   migration.

### Phase-2 plan (post-deployment)

When sub-regime detector + Phase-5 override are stable in production,
revisit B2:
- Pre-compute `bear_hot_conf` as scanner enrichment field
- Add tier-based mapping (effectively same as B1's 5 tiers)
- Re-label verdict bands to align WR with TAKE_FULL/TAKE_SMALL labels

### Why not ship both

B1's 4-tier display + B2's sigmoid would produce:
- Trader sees boundary_hot (B1 label)
- Same signal scores hot_conf=0.45 (B2 score)
- Two parallel displays, same finding, redundant

Ship one. B1 wins for v1 simplicity.

---

## Cross-reference to B3 (Phase-5 override)

B3's Phase-5 override LAYERS on top of B1's tier classification:

```
Layer order:
  1. KILL filters (B1 doesn't matter if killed)
  2. Sub-regime gate → tier classification (B1)
  3. Sector/calendar boost
  4. Phase-5 override (B3)

Override decision uses tier baseline:
  - boundary_hot baseline: 71.5%
  - confident_hot baseline: 64.2%
  - Phase-5 override fires only if Wilson_lower > tier_baseline + 5pp
```

In practice, override rarely fires for boundary_hot signals because
71.5% baseline is already very high; only the strongest combos beat it.

---

## Production rollout

### Phase 1 (now): B1 4-tier display
- Add `bear_tier` enrichment field to scanner pipeline
- Update Telegram messaging with tier tag
- Add tier classification to v3 Bear UP_TRI playbook
- First-deployment briefing: explain boundary_hot > confident_hot

### Phase 2 (later): Optional B2 sigmoid
- After 6+ months of B1 production data
- If trader requests finer granularity
- If continuous scoring unlocks WR calibration improvements

### Out of scope for this iteration
- Quarterly sigmoid re-fitting cadence
- Cross-regime tier extension (only Bear UP_TRI gets tiers in v1)

---

## Coupling to Path 2 rules

The Path 2 rule schema includes `sub_regime_constraint` which captures
the broad hot/warm/cold gate. Tier classification is INTERNAL to the
hot bucket — not exposed as a separate match field. Tier-based sizing
modifications happen at the integration layer, not the rule layer.

If future iterations need tier-based rule matching, add
`tier_constraint` field to schema; for now, the WR expectation tier
serves as documentation, not match logic.
