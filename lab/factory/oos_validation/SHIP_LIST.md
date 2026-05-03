# SHIP LIST — Phase 1 Production Deployment

**Date:** 2026-05-03
**Source:** Walk-forward W1-W3 + Sonnet critique tightening
**Scope:** 2 rules; Phase 1 at 25% capital; 60-day evaluation gate

---

## 1. Rules to add / modify in `data/mini_scanner_rules.json`

### A. Modify existing `kill_001` (regime fix)

Current production:
```json
{
  "id": "kill_001",
  "active": true,
  "signal": "DOWN_TRI",
  "sector": "Bank",
  "reason": "0/11 WR live (Phase B pattern miner). ..."
}
```

Modified to schema v4.1:
```json
{
  "id": "kill_001",
  "active": true,
  "type": "kill",
  "match_fields": {
    "signal": "DOWN_TRI",
    "sector": "Bank",
    "regime": "Bear"
  },
  "conditions": [],
  "verdict": "REJECT",
  "expected_wr": 0.45,
  "confidence_tier": "HIGH",
  "regime_constraint": "Bear",
  "sub_regime_constraint": null,
  "production_ready": true,
  "priority": "HIGH",
  "source_finding": "Bear×Bank×DOWN_TRI lifetime n=595 at 45.0% WR; live 0/11 confirms; walk-forward -7.1pp lift across 80 windows.",
  "evidence": {"n": 595, "wr": 0.45, "lift_pp": 0.0, "tier": "lifetime_calibrated"}
}
```

**Change from current production:** explicit `regime: "Bear"` constraint
(prior production had no regime field; matched all regimes including
Choppy/Bull DOWN_TRI Bank signals incorrectly).

### B. Add new `rule_019_bear_uptri_hot_refinement`

```json
{
  "id": "rule_019_bear_uptri_hot_refinement",
  "active": true,
  "type": "boost",
  "match_fields": {
    "signal": "UP_TRI",
    "sector": null,
    "regime": "Bear"
  },
  "conditions": [
    {"feature": "sub_regime", "value": "hot", "operator": "eq"}
  ],
  "verdict": "TAKE_FULL",
  "expected_wr": 0.71,
  "confidence_tier": "HIGH",
  "regime_constraint": "Bear",
  "sub_regime_constraint": "hot",
  "production_ready": true,
  "priority": "HIGH",
  "source_finding": "Bear UP_TRI hot sub-regime cross-sector refinement; +17.2pp walk-forward lift across 23 windows; mean n=191 per window; 78% positive windows.",
  "evidence": {"n": 240, "wr": 0.71, "lift_pp": 9.5, "tier": "walkforward_validated"}
}
```

---

## 2. Schema additions required

### A. `mini_scanner_rules.json` schema bump v3 → v4.1

Per Step 5 L2 schema design (already documented):
- `match_fields` (object) replaces flat `signal`/`sector`/`regime`
  fields
- `conditions` (array) for sub_regime + numeric thresholds
- `verdict`, `expected_wr`, `confidence_tier`, `priority`,
  `production_ready`, `source_finding`, `evidence` per-rule

### B. Sub-regime computation in production scanner

`rule_019` requires `sub_regime` to be computed on per-signal basis.
Port `lab/factory/bear/subregime/detector.py` to production:

```python
def detect_bear_subregime(vp, n60):
    """Bear sub-regime classifier (vol_pct × 60d_return).

    HOT: vp > 0.70 AND n60 < -0.10
    """
    if pd.isna(vp) or pd.isna(n60):
        return None
    if vp > 0.70 and n60 < -0.10:
        return "hot"
    if vp > 0.70 and n60 < 0:
        return "warm"
    return "cold"
```

Add to scanner enrichment pipeline. For Bull/Choppy regimes,
sub_regime stays null (their detectors are deferred per Phase 2+).

---

## 3. Telegram + PWA messaging changes

Per signal that matches `rule_019_bear_uptri_hot_refinement`:

```
[BEAR · UP_TRI · sub=hot] {SYMBOL}
TAKE_FULL — calibrated WR 71% (lifetime hot baseline)
Walk-forward: +17.2pp lift across 23 windows
PHASE 1 EXPERIMENTAL — 25% normal sizing
```

Per signal blocked by `kill_001`:

```
[KILL · BEAR × BANK × DOWN_TRI] {SYMBOL}
REJECTED — kill_001 (live 0/11 WR; lifetime 45%)
```

**Key:** add "PHASE 1 EXPERIMENTAL — 25% sizing" tag to all
rule_019 outputs to remind trader of reduced sizing during evaluation.

---

## 4. Pre-deployment checklist

### Code
- [ ] Update `data/mini_scanner_rules.json` with the 2 rules above
- [ ] Port Bear sub-regime detector to scanner enrichment (compute
      on each scan day)
- [ ] Verify `feat_nifty_vol_percentile_20d` and
      `feat_nifty_60d_return_pct` are available at scan time (they
      are; verified in scanner_core)
- [ ] Add Telegram messaging templates per rule
- [ ] Add Phase 1 experimental labeling
- [ ] Add daily WR tracking script (rolling 20-signal kill-switch
      monitor)

### Validation
- [ ] Re-run production backtest (PB1-PB4 harness) with these 2
      rules ONLY against signal_history.json — verify match counts
      + WRs match walk-forward predictions
- [ ] 7-day shadow mode (rules emit verdicts; trader does not act)
- [ ] Confirm sub_regime computation matches Lab's detector exactly

### Operational
- [ ] Define specific kill-switch thresholds the trader WILL act on
      (Sonnet PB4 warning: "65% WR over 20 signals" sounds rigorous
      but Wilson lower bound on 13/20 is 45%)
- [ ] Identify drawdown stop (e.g., Phase 1 max drawdown 10% of
      Phase-1-allocated capital)
- [ ] 60-day calendar evaluation date set (start_date + 60 trading days)
- [ ] Decision criteria for scale/hold/stop after 60 days

### Trader
- [ ] Read MORNING_READING_URLS.md (Opus deep dive output)
- [ ] Write 1-page Deployment Contract per FINAL_SYNTHESIS.md
      recommendation (Sonnet's "single concrete morning action")
- [ ] Sign + date contract before deploying

---

## 5. What is NOT in this ship list (deferred)

- 35 other Lab rules (mostly Bull regime + sub-regime narrow + calendar
  conditional) → defer to Phase 2+ when Bull regime returns or more
  Bear data accumulates
- Choppy 3-axis sub-regime detector (C1 finding) → defer; needs
  validation
- Bear 4-tier confidence display (B1) → defer; current sub_regime
  binary (hot/warm/cold) is sufficient for rule_019
- Phase-5 override mechanism (B3) → defer; Wilson-lower-bound override
  not needed at 2-rule scope
- Choppy BULL_PROXY entire-cell KILL → consider for Phase 2 (n=8 in
  April matching)
- Calendar SKIPs (Dec, Sep, Feb) → defer; insufficient walk-forward
  sample
- Sector boost rules (win_001-007) → defer; sector divergence flagged
  as "hot sector" framework instability

---

## 6. Honest position

This SHIP_LIST is **2 rules** out of Lab's 37. That's 5.4% of Lab's
output. The remaining 95% is either:
- Insufficient sample (couldn't validate either way)
- Negative lift in walk-forward (genuinely refuted)
- Recent degradation (regime shift)
- Overlapping logic with the 2 surviving rules

The 5 weeks + $25 was real engineering. The deliverable is **2
production-ready rules + 35 hypothesis-library entries + a
reusable validation methodology**. Not "37 rules of validated edge."

---

## 7. Post-Sonnet final modifications (W4 critique)

Sonnet's W4 critique mandates 6 modifications. Updated SHIP_LIST:

### Modified rule_019 spec

Add regime confirmation lag + vol decay check as conditions:

```json
{
  "id": "rule_019_bear_uptri_hot_refinement",
  "active": true,
  "type": "boost",
  "match_fields": {
    "signal": "UP_TRI",
    "sector": null,
    "regime": "Bear"
  },
  "conditions": [
    {"feature": "sub_regime", "value": "hot", "operator": "eq"},
    {"feature": "regime_consecutive_days", "value": 5, "operator": "gte"},
    {"feature": "vol_percentile_3d_decay", "value": 0, "operator": "lt"}
  ],
  "verdict": "TAKE_FULL",
  ...
}
```

**Two new computed features required in scanner:**
- `regime_consecutive_days`: consecutive days regime classification
  has been current (resets on regime change)
- `vol_percentile_3d_decay`: 3-day change in nifty_vol_percentile_20d
  (negative means vol declining = post-panic bounce phase)

### Revised kill-switches (Wilson-math-aware)

| Trigger | Action |
|---|---|
| Per-rule WR < 40% over rolling 30 signals | HALT that rule |
| Aggregate Phase 1 WR < 50% over rolling 50 signals | PAUSE Phase 1 entirely |
| Phase 1 drawdown > 10% from start | PAUSE Phase 1; review |
| Bear regime exits + Bull/Choppy persists 30+ days | PAUSE rule_019 |
| **REMOVED:** WR<50% over 20 (Wilson lower 25%; noise-prone) |
| **REMOVED:** 12.5% middle tier (mid-stream cuts useless) |
| **CHANGED:** at 30 signals if WR 40-55%, EXTEND eval another 30 at same 25% size |

### Revised evaluation gates

- **Day 60 = disaster check** (not validation)
  - Aggregate WR ≥ 50% AND drawdown < 10%: continue at 25% to Day 90
  - Aggregate WR < 50% over 50 signals: PAUSE; investigate
  - Drawdown > 10%: PAUSE regardless of WR
- **Day 90 / 50 signals = true validation gate**
  - WR ≥ 65% AND drawdown < 8%: scale to 50% capital
  - WR 55-65%: hold at 25% another 30 days
  - WR < 55%: STOP; revisit per CASE 3 (rebuild approach)

### win_003 immediate action

**RECALL NOW** (don't wait for confirmation):
- Reduce to 1% sizing immediately
- Flag "under review" for 30 days
- After 30 days / 10 signals at 1%, compare WR to rule_019 hot-gated
- If win_003 ≈ rule_019 hot: deprecate (sector boost was sub-regime
  artifact)
- If win_003 outperforms: investigate warm/cold edge missed by Lab

### Behavioral friction (replace label habituation)

Pick AT LEAST ONE of:

1. **Separate Telegram channel** for Phase 1 signals (`@tietiy_phase1`)
   — physical separation forces context-switch
2. **Manual confirmation per trade**: scanner posts "rule_019 fired
   on SYMBOL — reply `/confirm_019_SYMBOL` to execute"; friction =
   attention
3. **Daily aggregate summary at market open**: "Phase 1 active: N
   open positions, X% WR over Y signals, Z days until next review"
4. **PWA color-coding**: amber/orange Phase 1 vs green normal

Recommended: combine #2 (manual confirm) + #3 (daily summary).
Single Telegram channel keeps simplicity but high friction per trade.

### Pre-deployment scanner simulation (Sonnet's #3)

**MANDATORY before live capital**:
- Replay 2025 calendar year data day-by-day with production scanner
  code (not Lab harness)
- Compute `sub_regime` for every signal day
- Compare to walk-forward labels
- If divergence > 5%: scanner implementation bug; FIX before deploy
- If divergence < 5%: scanner reproduces walk-forward labels; safe
  to deploy

Expected runtime: ~10-30 minutes. Zero AI cost.

### Sonnet's probability framing

Phase 1 with all 6 mitigations applied:
- 40% meaningful positive return (>+3% / 60 days)
- 30% breakeven
- 20% modest loss
- 10% disaster

Without mitigations: probability drops to 25% success.

**Mitigations are not optional. They are the deployment.**

---

## 8. Final SHIP_LIST → 2 rules with 6 mitigations applied

Status: READY when all 6 mitigations implemented.

Estimated implementation time: 8-15 hours engineering work.
- Regime confirmation lag + vol decay computation: 2-3 hours
- Scanner simulation on 2025 data: 4-6 hours
- Kill-switch script: 1-2 hours
- Telegram manual-confirm + daily summary: 2-3 hours
- Pre-deployment checklist verification: 1 hour

After implementation + scanner simulation passes:
- 7-day shadow mode (rules emit verdicts; trader doesn't act)
- Sign Deployment Contract (per Opus FINAL_SYNTHESIS recommendation)
- Day 1 of live: 25% capital, both rules active, monitoring on
