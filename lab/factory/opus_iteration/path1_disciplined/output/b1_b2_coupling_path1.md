# B1/B2 Coupling — Path 1 (Disciplined)

**Date:** 2026-05-03
**Scope:** Specify how the 4-tier confidence display (B1) integrates
with rule evaluation now, and how the sigmoid scoring (B2) layers in
later.

---

## Decision: Ship B1 now; defer B2 to Phase 2

Per Sonnet 4.5 critique adjustment in Step 1.5+2 SY:

- **B1 (4-tier confidence display)** ships immediately. Aligns with
  existing percentile-bucket architecture; minimal schema impact.
- **B2 (sigmoid soft-threshold scoring)** deferred. Requires
  continuous-feature support not yet present in production rule
  matcher.

---

## B1 4-tier mapping

The 4-tier display is implemented as **sub-regime values**, not as a
separate field. This avoids schema explosion.

### Tier-to-sub_regime mapping

| Tier | Bear sub_regime | Bull sub_regime | WR calibration |
|---|---|---|---|
| boundary_hot | "hot" + tier flag (boundary) | n/a | 65-75% |
| confident_hot | "hot" + tier flag (confident) | n/a | 60-65% |
| warm | "warm" | (transition zone for Bull recovery_bull) | 70-90% Bear / 60-74% Bull |
| boundary_cold | "cold" + tier flag (boundary) | n/a | 55-60% |
| confident_cold | "cold" + tier flag (confident) | n/a | 50-55% |

For Bull regime, the 4-tier mapping reuses the existing sub-regime axes:

| Tier | Bull sub_regime | WR calibration |
|---|---|---|
| recovery (transitional) | recovery_bull | 60-74% (with filter) |
| healthy (broad) | healthy_bull | 55-66% |
| normal (baseline) | normal_bull | 50-55% |
| late (avoid) | late_bull | 43-45% |

### Runtime computation

The sub-regime detector outputs both the discrete label and a tier
suffix:

```python
def detect_bear_subregime_with_tier(vp, n60):
    if vp > 0.70 and n60 < -0.10:
        # vp distance from 0.70 boundary; n60 distance from -0.10 boundary
        vp_dist = vp - 0.70
        n60_dist = -0.10 - n60
        if vp_dist > 0.05 and n60_dist > 0.05:
            return "hot", "confident_hot"
        else:
            return "hot", "boundary_hot"
    elif vp > 0.70 and -0.10 <= n60 < 0:
        return "warm", "warm"
    else:
        # cold
        if vp < 0.65 and n60 > -0.05:
            return "cold", "confident_cold"
        else:
            return "cold", "boundary_cold"
```

### Verdict mapping

Layer 2 sub-regime gate uses the discrete label for matching
(`sub_regime_constraint='hot'` matches both confident_hot and
boundary_hot). The tier suffix is used downstream for:

1. **WR display** in Telegram/PWA (calibrated band per tier)
2. **Sizing modulation** (boundary_hot full size; confident_hot full
   size; warm full size with caveat; cold cascade only)
3. **Audit logging** (per-tier WR tracking for drift detection)

---

## B2 deferral plan

B2 sigmoid scoring is deferred to Phase 2 deployment. When implemented,
it will:

1. Replace hard threshold matching for Bear sub-regime detector with
   continuous `bear_hot_conf` score (sigmoid over vp, n60)
2. Require schema v5 with `continuous_score_function` rule type, OR
3. Pre-compute `bear_hot_conf` as scanner enrichment field; rules match
   bucketed values (Path 1 preferred — aligns with 2-tier schema)

Rationale for deferral: B1 captures the same finding (boundary > deep
in Bear UP_TRI) via discrete tiers; B2 sigmoid produces same WR ranking
via continuous score. Shipping both creates UX confusion. Path 1
defers B2 to Phase 2 when discrete-tier production data validates the
boundary>deep finding.

---

## Path 1 specifics

### Sub-regime field is the single source of truth

Path 1 rules use `sub_regime_constraint` as the gate. The 4-tier display
is downstream (rendering and sizing), not upstream (rule matching). This
keeps the schema simple and matches Path 1's "explicit constraints"
mandate.

### Rule example showing tier-aware sizing

rule_007 (Health × Bear UP_TRI × hot) gates on sub_regime='hot'. The
display layer breaks "hot" into boundary_hot vs confident_hot for the
trader, but the kill rule fires regardless of which sub-tier:

- boundary_hot Health UP_TRI Bear: SKIP (calibrated 32.4% — kill rule)
- confident_hot Health UP_TRI Bear: SKIP (same kill rule)

The 4-tier display tells the trader WHY the SKIP fires (Health is
hostile across all hot sub-tiers).

### Phase-5 override with B1 tiers

B3 Phase-5 override compares Wilson lower bound to sub-regime base
+5pp. With B1 tiers:

- boundary_hot base = 71.5% (lifetime)
- Override threshold = 76.5%

A VALIDATED combo with Wilson lower 76.6% would NOT trigger override
on confident_hot (base 64%, threshold 69%, 76.6% > 69% → OVERRIDE) but
WOULD trigger on... wait, recompute: confident_hot base = 64%, override
threshold = 69%, override Wilson lower 76.6% > 69% → OVERRIDE TRIGGERS.

For boundary_hot (base 71.5%, threshold 76.5%), 76.6% > 76.5% → barely
TRIGGERS override (1pp gap).

This means Phase-5 override is more likely to fire on confident_hot
than on boundary_hot — which is correct mechanically (boundary_hot is
already the strongest tier; less room for override to add).

---

## Production integration timeline

| Phase | B1 status | B2 status |
|---|---|---|
| Phase 1 (Path 1 initial) | Sub-regime detector returns label + tier suffix; display layer renders 4-tier | Deferred |
| Phase 2 (post 30-day live data) | Tier-stratified WR audited; calibrations refined | Implement bucketed bear_hot_conf enrichment |
| Phase 3 (full deployment) | 4-tier display matures | Sigmoid integration if Phase 2 bucketed approach validates |

---

## Summary

- B1 ships now via sub-regime tier suffix; rule schema unchanged
- B2 deferred to Phase 2; pre-compute enrichment approach preferred
- 4-tier maps to sub_regime values + tier suffix, not separate field
- Phase-5 override interacts cleanly with both tiered and continuous
  modes
