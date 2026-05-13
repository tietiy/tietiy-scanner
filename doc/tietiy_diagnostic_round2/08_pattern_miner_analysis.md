# 08 — Pattern Miner

Source: `scanner/pattern_miner.py` (539 LOC); output: `output/patterns.json`.

## What it does

Nightly cron job (7 PM IST per docstring; actually run by `eod_master.yml`). Reads resolved live signals from `signal_history.json`, groups them by 1-to-3-feature combinations of `signal × regime × sector × age × grade`, computes WR and average PnL per group, compares to per-signal-type baseline (`UP_TRI / DOWN_TRI / BULL_PROXY`), and classifies each pattern into one of three tiers:

| Tier | Rule |
|---|---|
| **validated** | n ≥ 20 AND |edge| ≥ 15 pp |
| **preliminary** | n ≥ 10 AND |edge| ≥ 10 pp |
| **emerging** | n < 10 OR |edge| < 10 pp |

Patterns sorted by tier, then by `|edge|`, then by `n`. Output schema_v1 → `output/patterns.json`. Consumed by `rule_proposer.py` (which writes `proposed_rules.json`) and by `chain_validator` for liveness check.

## What's actually in `output/patterns.json` (last run 2026-04-28)

- **Total resolved signals input:** 165
- **Total patterns mined:** 186
- **Tier breakdown:** 27 validated, 55 preliminary, 104 emerging
- **Baselines:** UP_TRI WR 75.4% n=118, BULL_PROXY 66.7% n=24, DOWN_TRI 17.4% n=23

### Top validated POSITIVE patterns (n ≥ 20, edge ≥ +15pp)

| Pattern | WR | Edge | n | Avg PnL |
|---|---:|---:|---:|---:|
| `regime=Bear_sector=Bank` | 47.6% | **+30.2pp** | 21 | **−3.61%** ⚠ |
| `age=1` | 95.8% | +20.4pp | 24 | +7.99% |
| `regime=Bear_age=1` | 95.8% | +20.4pp | 24 | +7.99% |
| `signal=UP_TRI_regime=Bear_age=0` | 95.3% | +19.9pp | 43 | +5.26% |
| `signal=UP_TRI_regime=Bear` | 95.2% | +19.8pp | 83 | +6.18% |
| `signal=UP_TRI_regime=Bear_age=2` | 90.9% | +15.5pp | 22 | +7.34% |

### Top validated NEGATIVE patterns

| Pattern | WR | Edge | n | Avg PnL |
|---|---:|---:|---:|---:|
| `regime=Choppy` | 26.1% | −49.3pp | 46 | −1.54% |
| `regime=Choppy_age=0` | 26.1% | −49.3pp | 46 | −1.54% |
| `signal=UP_TRI_regime=Choppy` | 28.6% | −46.8pp | 35 | −1.66% |
| `sector=Bank_grade=B` | 43.8% | −31.6pp | 32 | −2.78% |
| `sector=Bank_age=0` | 45.5% | −29.9pp | 33 | −2.98% |
| `age=0` | 53.9% | −21.5pp | 115 | +0.23% |

### Surprising patterns (preliminary tier, n=10-19)

| Pattern | WR | n | Avg PnL | Note |
|---|---:|---:|---:|---|
| `regime=Bear_sector=Metal` | 100.0% | 16 | +8.68% | Perfect cohort, n approaching validated |
| `signal=UP_TRI_age=1` | 100.0% | 14 | +6.86% | Age-1 UP_TRI also perfect |
| `regime=Bear_sector=IT` | 100.0% | 12 | +6.13% | rule_031's IT focus matches this |
| `regime=Bear_sector=Auto` | 100.0% | 11 | +7.55% | |
| `signal=DOWN_TRI_sector=Bank` | **0.0%** | 11 | −11.12% | kill_001 evidence |
| `signal=BULL_PROXY_age=1` | 90.0% | 10 | +9.57% | Age-1 BP rare but strong |

## Bug / mislabeling in the summary

The summary line:
```
"top_positive": "regime=Bear_sector=Bank"
"top_negative": "regime=Choppy"
```

`Bear×Bank` is flagged "top positive" because **WR (47.6%) is +30.2pp above the DOWN_TRI baseline (17.4%)**. But the cohort's average pnl is **−3.61%** — the cohort is losing money. The pattern miner computes "edge" purely in WR-percentage-points against the *signal-type baseline*, with no awareness that:

1. Different signal types have wildly different baselines (DOWN_TRI 17%, UP_TRI 75%) so +30pp from DOWN_TRI is still terrible in absolute terms.
2. WR-edge ignores PnL-magnitude, so the "winner" cohort can still bleed because losses are heavier than wins.

**This is a meaningful Round 2 finding:** `top_positive` from pattern_miner is unsafe to ship as a boost_pattern as-is. The brain's `cohort_health.json` Wilson-bounded approach + manual review caught this; the deterministic pattern miner did not. **Anything that consumes `patterns.json` `top_positive` (including `rule_proposer.py`) is at risk of over-promoting losing cohorts.**

## Integration

- Run nightly via `eod_master.yml` step 7.
- Output read by `rule_proposer.py` (proposed_rules.json) and `chain_validator.py` (system_health check).
- `chain_validator` currently shows **pattern_miner = WARN** because last run was 2026-04-27 (stale).

## Verdict

**Pattern miner is sound on negative-pattern discovery (it correctly flags Choppy and DOWN_TRI+Bank).** Positive-pattern discovery is **structurally flawed by the WR-vs-baseline metric.** Anything downstream that treats `top_positive` as actionable (`rule_proposer.py`) should be reviewed before allowing auto-approve. The brain layer's Wilson-bounded approach + manual reasoning is the correct successor.
