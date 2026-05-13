# 17 — Zone-Based Architecture Readiness

User asked: *"If we add Fib-based zones for support/resistance (not single lines) as architecture: which modules need to change, and which already operate on zones rather than points?"*

This report walks each module and assesses whether it already works with zones vs. points.

## Already zone-aware

### `scanner/scanner_core.py:build_zones()` ✓

Already computes `szH/szL` (support zone high/low) and `rzH/rzL` (resistance zone high/low) on every detected pivot. Lines 197-242:

```python
if not np.isnan(sp):                       # sp = support pivot price
    szH[i] = sp + 0.5 * atr                #  support zone high = pivot + 0.5×ATR
    szL[i] = sp - 0.1 * atr                #  support zone low  = pivot - 0.1×ATR
if not np.isnan(rp):                       # rp = resistance pivot price
    rzH[i] = rp + 0.1 * atr                #  resistance zone high = pivot + 0.1×ATR
    rzL[i] = rp - 0.5 * atr                #  resistance zone low  = pivot - 0.5×ATR
```

**Zones already exist.** They're asymmetric (support zone extends 0.5 ATR above, 0.1 ATR below; resistance extends 0.1 ATR above, 0.5 ATR below — both biased "toward the inside of the structure"). They're used by `add_zone_proximity()` and the `nearSZ` flag in BULL_PROXY detection.

**Fib refactor here:** replace the 0.5/0.1 ATR widths with Fib retracements of the prior leg (38.2%, 50%, 61.8%). Zone structure stays, anchor changes from "pivot ± ATR" to "leg × Fib".

### `scanner/scanner_core.py:add_zone_proximity()` ✓

Already operates on zones — checks if `Low <= szH AND High >= szL` (overlap with zone interior). This is the BULL_PROXY trigger and would extend naturally to Fib zones.

### `scanner/scanner_core.py` BULL_PROXY stop calculation ✓

```python
stop_z = szL_v[i] - 0.5 * atr if not np.isnan(szL_v[i]) else lows[i] - atr
```

Uses `szL` (support zone low) minus 0.5 ATR. Already zone-anchored, not pivot-point-anchored. **Zero refactor needed if Fib zones populate `szL`.**

## Point-based (need to change)

### `scanner/scanner_core.py` UP_TRI stop calculation ✗

```python
stop = round(pivot_px - STOP_MULT * atr, 2)
```

Uses the raw pivot LOW price minus 1×ATR. **Point-based.** Fib refactor: replace `pivot_px` anchor with `pivot_px + fib_offset × (recent_high - pivot_px)` for a Fib-zone-aware stop. Or simpler: replace `STOP_MULT * atr` with `fib_pct * leg_size`.

Effort: 5 lines.

### `scanner/scanner_core.py` DOWN_TRI stop calculation ✗

```python
stop = round(pivot_px + STOP_MULT * atr, 2)
```

Mirror of UP_TRI. Same fix.

Effort: 5 lines.

### `scanner/scorer.py:calc_target()` ✗

Calls `entry + 2 × risk` for `Target2x` or `entry + 1.5 × risk` for `Target1_5x`. **R-multiple based, not zone based.** A Fib-target version would compute target at the next confirmed resistance zone (`rzL` for longs, `szH` for shorts) using Fib extension levels (1.272×, 1.618×).

Effort: new function `calc_zone_target(entry, swing_low, swing_high, fib_level)` ≈ 20 lines.

### `scanner/scorer.py:get_exit_rule()` ✗

Currently returns `Target2x` or `Day6`. A zone-aware version would return `ZoneTarget` (use next resistance zone) when zones are confidently identified.

Effort: small, but **only worth doing if calc_zone_target is in place**.

### `scanner/bridge/rules/validity_checker.py` (not read directly, but inferable from bucket_engine) ⚠

Checks `rr >= 1.5`. With zone-based targets, `rr` becomes "distance to zone-target / distance to zone-stop". The check logic stays the same; only the inputs change.

Effort: zero if the upstream produces the right `rr` value. Need to verify validity_checker doesn't hard-code anywhere.

### `scanner/journal.py` (not read in depth) — needs to store zone metadata ✗

If we want to audit zone-based outcomes, signal records need to carry zone boundaries (`stop_zone_high`, `stop_zone_low`, `target_zone_high`, `target_zone_low`) alongside the point values. This is **schema-v6** territory.

Effort: schema migration + journal write-time additions. **Non-trivial.** Likely 1-2 days work.

### `scanner/bridge/composers/*.py` — render zones in SDR display ✗

The bridge SDR currently has `stop_price` (single number) and `target_price` (single number) in `display`. Zone-aware: add `stop_zone_low`/`stop_zone_high` for the L1 brief to render "Stop zone: 1200-1218" rather than "Stop: 1209". Mostly cosmetic but enables better operator decisions ("am I close to the zone boundary?").

Effort: 1-2 days for L1+L2+L4 + the 3 renderers.

### `scanner/bridge/queries/q_pattern_match.py` (not read) ⚠

Looks for supporting/opposing patterns. Adding zone-awareness would let it surface "the prior resistance zone is overlapping with this entry's target zone, confirming a clean breakout setup". Probably scope-creep for a first zone migration.

## Already not affected

- `scanner/brain/*.py` — Brain consumes truth files; doesn't compute stops/targets. Unchanged by zone migration.
- `scanner/scanner_core.py` pivot detection — point detection is fine; zones are derived after.
- All filter rules in `mini_scanner_rules.json` — `kill_patterns`, `boost_patterns`, `watch_patterns` operate on signal-type × sector × regime; no stop/target awareness.
- `scanner/outcome_evaluator.py` — outcome attribution is "did high cross target, did low cross stop". Trivial to adapt to "did high enter target zone, did low enter stop zone".

## Zone migration readiness scorecard

| Module | Today | After Fib zones | Effort |
|---|---|---|---:|
| `scanner_core.build_zones` | Has zone math | Replace ATR with Fib | XS |
| `scanner_core.add_zone_proximity` | Operates on zones | No change | 0 |
| `scanner_core` UP_TRI stop | Point-based (`pivot−ATR`) | Zone-based (`pivot−fib_leg`) | XS |
| `scanner_core` DOWN_TRI stop | Point-based (`pivot+ATR`) | Mirror | XS |
| `scanner_core` BULL_PROXY stop | Already zone (`szL−0.5×ATR`) | Replace ATR with Fib | XS |
| `scorer.calc_target` | R-multiple | New `calc_zone_target` | S |
| `scorer.get_exit_rule` | Day6 / Target2x | Add ZoneTarget | XS (conditional on calc_zone_target) |
| `bridge/rules/validity_checker` | Reads `rr` | No change if rr correct | 0 |
| `journal.py` write schema | point-only | Add zone metadata | M (schema v6) |
| `bridge/composers/*` SDR display | point-only | Add zone fields | M |
| `outcome_evaluator` | "crossed price" | "entered zone" | S |
| `brain/*` | doesn't care | doesn't care | 0 |
| Filter rules JSON | unchanged | unchanged | 0 |

XS = ≤1 hour. S = ½ day. M = 1-2 days.

## Verdict

**Zone-based architecture is genuinely feasible.** `scanner_core.build_zones` already does zone math; BULL_PROXY stop is already zone-anchored. The point-based hold-outs (UP_TRI/DOWN_TRI stops, scorer target) are small edits. The non-trivial pieces are journal schema migration (because we want zone metadata on every signal record for outcome attribution) and bridge display refresh (rendering zones in L1/L2/L4).

**Total effort estimate:**
- Phase 1 (signal-time zone use, no schema change): 1 day.
- Phase 2 (schema v6 + bridge display): 2-3 days.
- Phase 3 (outcome_evaluator zone-entry semantics): 1 day.

Reasonable single-session work for an experienced operator, multi-session for paired audit-first work.

The user's framing about "Fib zones not single lines" suggests the migration should target the structural cause of the current pain (Day-6 forced exits with no target path on most cohorts) by **giving every signal a real target zone**, not just UP_TRI×Bear. Pairs well with the Round 1 surgical fix #4 (add `Target2x` to BULL_PROXY); the zone variant generalizes that.

## What I could not determine

- Whether the user wants Fib levels measured from "most recent confirmed leg" (high to low or low to high) or from a longer-context anchor (last major swing). Both are common; choice affects stop tightness.
- Whether zone "entry" should require a close inside the zone or a wick. Matters for stop-out logic.
- Whether the Fib zone for shorts (DOWN_TRI) should be measured from prior swing low → swing high (retracement) or extended above the high (extension to 1.272/1.618). Two different placement schemes.
