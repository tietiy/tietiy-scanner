# W3 Walk-Forward Stability Analysis

**Date:** 2026-05-03
**Method:** 60-day rolling windows, 30-day step, 182 windows over
2011-2026

---

## A. Headline classification

| Category | Count |
|---|---|
| INSUFFICIENT_DATA (n_windows_with_match <5) | 11 |
| SURVIVOR (boost rule, mean_lift>5pp, pct>70%, n>=5) | 3 |
| SURVIVOR_KILL (kill rule, mean_lift<=-3pp) | 2 |
| WEAK_SURVIVOR | 4 |
| WEAK_SURVIVOR_KILL | 4 |
| WATCH_INFORMATIONAL | 4 |
| DEGRADER (positive mean BUT recent decay >10pp) | 3 |
| REJECT_NEGATIVE_LIFT (boost rule with negative lift) | 4 |
| UNSTABLE_POSITIVE | 1 |
| REJECT_KILL_NOT_KILLING | 1 |

## B. The 3 INTERSECTION rules (walk-forward SURVIVOR + backtest READY_TO_SHIP)

These are the highest-confidence Lab outputs:

| rule_id | walk-forward | backtest | mean_lift | pct_pos | n_match | recent_Δ |
|---|---|---|---|---|---|---|
| `kill_001` | SURVIVOR_KILL | READY_TO_SHIP | -7.1pp | 39% (kill) | 16 | -8.9pp |
| `win_001` | SURVIVOR | READY_TO_SHIP | +8.1pp | 71% | 28 | +39.3pp |
| `rule_019_bear_uptri_hot_refinement` | SURVIVOR | READY_TO_SHIP | +17.2pp | 78% | **191** | -7.7pp |

## C. Sonnet 4.5 critique adjustments (key)

### Tightened SURVIVOR thresholds recommended

Sonnet: "5pp lift threshold allows marginal noise — tighten to mean_lift
> 8pp AND pct_positive > 75% AND n >= 10."

Re-applied:

| rule_id | passes tighter bar? | reason |
|---|---|---|
| `kill_001` | YES | clear kill, large n, stable |
| `rule_019` | YES | +17.2pp, 78%, n=191 (massive sample) |
| `win_001` | NO (n=28) | "borderline sample, recent_Δ +39.3pp suggests regime-specific 2024-26 strength" |

Sonnet: "Don't count win_001 as independent confirmation. It's in
production already; backtest → production → walk-forward all use
overlapping data."

### Phase 1 recommended scope: 2 rules

**kill_001 + rule_019_bear_uptri_hot_refinement.**

### DEGRADERS — rejected by Sonnet

- **rule_029_bear_uptri_pharma_hot**: +18pp mean BUT -57.7pp recent.
  Sonnet: "Catastrophic regime break — REJECT outright."
- **win_003**: ALREADY in production with -14.1pp recent decay. Sonnet:
  "Demands immediate recall or capital reduction."
- **win_007**: +32.5pp mean is statistical artifact (n=8 windows = ~480
  days). Should not deploy.

### Bull rules verdict

All 4 Bull rules (rule_010/011/012/023) show negative lift in walk-
forward. Sonnet: "rule_011 has n=180 windows; lift -5.7pp suggests Bull
UP_TRI healthy is lagging indicator, not edge. Lab's Bull work may be
wrong."

Sonnet recommendation: "Either (a) extend windows to 120d, (b) regime-
filter to Bull-only windows, or (c) acknowledge Bull rules are
unvalidated and exclude from deployment." For now: exclude.

### Sector divergence red flag

rule_031 (IT hot, +16pp, recent +9.5pp = strengthening) vs rule_029
(Pharma hot, +18pp, recent -57.7pp = collapsing). Same cell logic
(Bear×UP_TRI×hot_sector), opposite recent trajectories.

Sonnet: "This divergence is evidence that **sector rotation dominates,
not stable UP_TRI edge**. Lab's 'hot sector' classification is either
backward-looking or the 'hot' label is overfit. NEITHER should deploy."

### Lab over-fit verdict

Sonnet: "Lab delivered 8 READY_TO_SHIP from backtest; walk-forward
validates 3, of which 1 is marginal. **62% false-positive rate** in
Lab's backtest process. Walk-forward didn't validate Lab; it
**debugged** it. Phase 1 should be 2 rules. Accept the 2-rule outcome.
Deploying all 8 would be repeating Lab's over-fit mistake with
walk-forward lipstick on."

## D. Adjusted decision case

Original session brief CASE 2: "2-4 SURVIVORS overlap with backtest
READY_TO_SHIP → DEPLOY high-confidence survivors only."

Post-Sonnet adjusted: **2 rules** (kill_001 + rule_019). Tightened
threshold drops win_001 from intersection.

**Final SHIP candidates: 2 rules** at 25% normal capital, kill-switches,
60-day evaluation window.

## E. What walk-forward confirmed about Opus's deep dive

Opus claimed: "Circular validation. 37 rules from cohort_health.json's
3 observations at sample sizes (n=2, 6, 11) that don't support 37
statistical tests."

Walk-forward result: of 37 rules, only 2 pass tightened SURVIVOR bar.
Lab's "8 READY_TO_SHIP" was 62% false positives.

**This empirically confirms Opus's circular-validation diagnosis.**

## F. What walk-forward refutes about Lab

The "delete 32 rules, deploy 5" recommendation was directionally right
but specifically wrong — the actual evidence supports **deploy 2** of
Lab's rules. The other 35 either:
- Don't accumulate samples (11 INSUFFICIENT_DATA)
- Show negative lift (4 REJECT)
- Show degradation (3 DEGRADER)
- Are kill rules with marginal performance (10 WEAK or below)

## G. SURVIVOR-quality findings

Despite Lab's over-fit, walk-forward confirmed real edge in:

1. **kill_001** (Bear × Bank × DOWN_TRI = REJECT) — already in
   production. -7.1pp consistent kill across 80 windows. Stable signal.

2. **rule_019_bear_uptri_hot_refinement** — Bear UP_TRI hot sub-regime
   refinement. +17.2pp mean lift, 78% positive, n=191 mean per window.
   The broad-sample winner.

These are the foundation Phase 1 should ship.

---

## Walk-forward validates the deeper finding

Walk-forward isn't a test "did Lab work?" — it's a test "which Lab
hypotheses survive 15 years of out-of-sample windows?" The answer is
2 of 37 (5.4%). That's not a Lab failure; that's how trading systems
work. Most edges are smaller than backtest suggests, most rules don't
generalize.

The 2 survivors are the real product of 5 weeks of Lab work plus
$25.12 in AI spend. Every other rule is a hypothesis library for
future investigation when more data accumulates.
