# Path 2 Precedence Logic — Rule Evaluation Order

## Overview

Path 2 uses a 4-layer precedence model where rules are evaluated in
strict hierarchical order. Each layer can terminate evaluation (KILL/REJECT)
or modify a verdict (boost/sector/calendar). Phase-5 override applies
last and can only upgrade verdicts (never downgrade).

---

## Layer 1 — KILL/REJECT (terminating)

If any KILL or REJECT rule matches, output that verdict immediately.
No further layers evaluated.

**KILL/REJECT rule examples (Path 2):**
- `rule_009`: Choppy BULL_PROXY → REJECT (entire cell)
- `rule_006`: Health × Bear UP_TRI hot → SKIP (hostile cell)
- `rule_007`: December × Bear UP_TRI → SKIP (catastrophic month)
- `rule_005`: vol_climax × Bear BULL_PROXY → REJECT
- `rule_001`: late_bull × Bull UP_TRI → SKIP
- `rule_002`: late_bull × Bull BULL_PROXY → SKIP
- `kill_001`: Bank × Bear DOWN_TRI → REJECT
- `rule_013/014/015/016`: Sector/calendar Choppy kills
- `rule_018/019`: Energy/Sep Bull kills
- `rule_021`: Low-vol Bear UP_TRI

**Precedence within Layer 1:** All KILL rules are equally terminating.
Order does not matter; first match wins logically since all produce
the same SKIP/REJECT verdict.

---

## Layer 2 — Sub-regime gate

If no KILL fired, sub-regime classification establishes baseline verdict.

**Bear sub-regime gate** (computed: `vp > 0.70 AND n60 < -0.10 = hot`):
- `hot`: `rule_008` → TAKE_FULL (broad Bear UP_TRI baseline)
- `warm`: TAKE_FULL (live evidence; no specific rule, defaults to allowing layer 3)
- `cold`: requires Tier 1 cascade match (`rule_012` wk4 × swing_high=low)
  or SKIP

**Bull sub-regime gate** (computed: `200d × breadth → recovery/healthy/normal/late`):
- `recovery_bull`: `rule_003` → TAKE_FULL UP_TRI
- `healthy_bull`: `rule_004` → TAKE_FULL BULL_PROXY
- `late_bull`: KILLS already triggered in Layer 1 (`rule_001/002`)
- `late_bull` for DOWN_TRI: `rule_020` → TAKE_SMALL

**Choppy sub-regime gate** (computed: `vol × breadth × momentum`):
- Various (vol_regime + breadth) cells: `rule_010` (DOWN_TRI),
  `rule_011` (UP_TRI)

---

## Layer 3 — Sector / Calendar boost & modulation

Sector-specific and calendar-specific rules apply on top of sub-regime
verdict. **Pessimistic merge:** the most conservative verdict wins
when multiple rules match.

**Verdict ordering (most → least conservative):**
`REJECT > SKIP > TAKE_SMALL > TAKE_FULL`

**Sector/calendar BOOST examples (Path 2):**
- `win_001` to `win_006`: Bear UP_TRI sector preferences (Auto, FMCG,
  IT, Metal, Pharma, Infra) → TAKE_FULL
- `win_007`: Bear BULL_PROXY broad → TAKE_FULL
- `rule_017`: Bear DOWN_TRI wk2/wk3 → TAKE_SMALL

**Composition rule:** Boost rules CONFIRM but don't UPGRADE verdicts
beyond what the sub-regime baseline supports. If a sub-regime says
TAKE_SMALL and a sector boost says TAKE_FULL, take TAKE_SMALL
(pessimistic). If both agree, take that verdict.

---

## Layer 4 — Phase-5 override

Phase-5 override searches the combo database for VALIDATED matches
with Wilson lower bound > sub-regime base + 5pp. Override can ONLY
upgrade (never downgrade).

**Override decision:**
1. Query combo_db with `(regime, signal_type, signal_features)`
2. Filter to `live_tier == VALIDATED AND live_n >= 10 AND recency_90d`
3. Pick max(Wilson_lower)
4. If Wilson_lower > current_baseline + 5pp, upgrade verdict tier
5. Else, retain Layer 1-3 verdict

**Logging:** Record `wr_source` as either `sub_regime_base`,
`sector_boost_match`, or `phase5_override_<combo_id>`.

---

## Conflict resolution examples

### Example 1: Bear UP_TRI hot Auto wk4

```
Date: 2026-04-25, AUTOLINKS UP_TRI, Bear, Auto sector
Sub-regime: hot (vp=0.75, n60=-0.13)

Layer 1 (KILL): No matches
  - rule_006 (Health) doesn't match (sector=Auto)
  - rule_007 (December) doesn't match (Apr)
  - rule_021 (Low vol) doesn't match
Layer 2 (sub-regime): rule_008 hot → TAKE_FULL
Layer 3 (sector): win_001 Auto → TAKE_FULL (confirms)
Layer 4 (override): No VALIDATED combo > 73.3% Wilson lower

Final: TAKE_FULL
WR estimate: 74% (from win_001 evidence)
```

### Example 2: Bull UP_TRI late_bull (KILL)

```
Date: 2027-08-19, late_bull conditions
Stock: TCS UP_TRI, Bull, IT sector

Layer 1 (KILL): rule_001 late_bull × Bull UP_TRI → SKIP

Final: SKIP (Layer 1 terminates)
WR estimate: N/A
```

### Example 3: Bear UP_TRI hot Health (sub-regime conflict with sector kill)

```
Date: 2026-04-15, hot Bear regime
Stock: SUNPHARMA UP_TRI, Bear, Health sector

Layer 1 (KILL): rule_006 Health × Bear UP_TRI hot → SKIP

Final: SKIP (Health hostility overrides hot sub-regime baseline)
WR estimate: N/A (32.4% historical)
```

### Example 4: Choppy DOWN_TRI strong filter match

```
Date: 2026-09-23, Wednesday wk3
Stock: ASIANPAINT DOWN_TRI, Choppy, Other sector
Features: breadth=medium, vol=Medium

Layer 1 (KILL):
  - rule_013 (Pharma) doesn't match
  - rule_014 (Friday) doesn't match
Layer 2 (sub-regime): No specific Choppy DOWN_TRI baseline rule
Layer 3 (boost): rule_010 breadth=med × vol=Med × wk3 → TAKE_FULL
Layer 4 (override): No Bull/Bear override applies

Final: TAKE_FULL
WR estimate: 57.8% (rule_010 evidence)
```

### Example 5: Choppy BULL_PROXY (always REJECT)

```
Date: any, any stock
Signal: HDFCBANK BULL_PROXY, Choppy

Layer 1 (KILL): rule_009 Choppy BULL_PROXY → REJECT

Final: REJECT
WR estimate: N/A (cell-level kill)
```

---

## Schema enforcement notes

- `match_fields` must EXACTLY match (signal, sector, regime). `null`
  acts as wildcard.
- `conditions` array applies AND logic across feature-value pairs.
- `regime_constraint = "any"` allows wildcard regime matching (rare;
  most rules constrain).
- `sub_regime_constraint = null` means rule applies regardless of
  sub-regime; otherwise must match exactly.

## Determinism

Path 2 evaluation is deterministic given:
1. Signal features at fire time
2. Market state (NIFTY vol_percentile, 60d_return, 200d_return, breadth)
3. Combo database state (Phase-5 VALIDATED set, refreshed quarterly)

Each scan day produces the same verdict for the same signal.
