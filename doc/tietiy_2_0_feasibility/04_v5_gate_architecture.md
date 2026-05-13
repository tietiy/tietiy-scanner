# 04 — V5 Confluence Gate Architecture

## Design

V5 is **not the generator**; the rule engine generates candidate signals. V5 is queried per candidate to either confirm or veto.

### Interface

```python
ConfluenceGate.evaluate(signal: CandidateSignal, chart_image_path: Path, regime: RegimeLabel) -> ConfluenceDecision
```

### Flow

```
CandidateSignal (with TIE TIY Zones)
        │
        ▼
ChartGenerator(symbol, end_at=detection_bar) → chart_at_t.png
        │
        ▼
V5 client (Anthropic Sonnet 4.5)
   prompt: "Analyze chart. Provide direction, confidence, entry/stop/target ZONES."
        │
        ▼
V5Verdict (direction, confidence, entry_zone, stop_zone, target_zone, rationale)
        │
        ▼
Direction match? ──── no ──► REJECT (veto_source="V5_DISAGREE")
        │ yes
        ▼
Jaccard overlap computation per zone (entry, stop, target)
        │
        ▼
Composite overlap = weighted_mean(entry, stop, target)  [entry weighted highest]
        │
        ▼
regime-specific threshold lookup (e.g. Stable-Bull=0.65, Stable-Choppy=0.80)
        │
        ▼
overlap >= threshold? ──── no ──► REJECT (veto_source="ZONE_OVERLAP_LOW")
        │ yes
        ▼
APPROVE (final_zones = merge(TIE TIY zones, V5 zones))
```

### Asymmetric trust (per L99 + literature)

Vision LLMs exhibit **yes-bias**: they tend to confirm prompted directions ("see what you ask for"). Asymmetric trust applies:

- **V5 says "DIRECTION DISAGREES with TIE TIY"** → veto. (Strong signal — V5 had to break with the prompted direction.)
- **V5 says "AGREE"** → require ALSO that Jaccard overlap ≥ threshold. (Direction agreement alone is weak evidence.)
- **V5 confidence < 0.4** → treat as no-evidence (neither veto nor approval). Fall back to TIE TIY decision alone.

### Calibration via McNemar test

Once ≥80 paired signals accumulate (TIE TIY decision × V5 decision × outcome):

```
                       V5 approve   V5 veto
TIE TIY win            a            b
TIE TIY loss           c            d
```

McNemar's χ² = `(b - c)² / (b + c)` — tests whether V5 vetoes correlate with TIE TIY losses (asymmetry of disagreement).

- If `b > c` significantly (p<0.05): V5 vetoes are useful (catches TIE TIY winners less often than it correctly skips TIE TIY losers). Lower V5 threshold.
- If `b ≈ c`: V5 is noise; raise threshold or remove gate.
- If `c > b`: V5 is anti-predictive; INVERT gate (use V5 disagreement as confirmation). Unlikely but logged.

Calibration runs weekly per regime (each regime has its own threshold). Threshold updates go through brain proposal → user approval (don't auto-apply per self-learning policy).

## Cost model

Anthropic Sonnet 4.5 pricing (as of 2026-05): ~$3/M input + $15/M output. Per chart call:
- Input: ~1500 tokens (system prompt) + ~1100 tokens (chart image) = ~2600 input tokens → $0.0078
- Output: ~400 tokens (JSON verdict) = ~$0.006
- **Per call: ~$0.014** (≈ ₹1.20)

Call rate projection:
- 188 stocks scanned daily.
- Average signal-firing rate per stock per day (current data): ~6 signals/day total across all signal types.
- TIE TIY 2.0 has 7 active signal detectors. Firing rate up to ~15-25 candidates/day.
- V5 only called on candidates that pass TIE TIY's own rule (post-detection), not all 188.
- **Daily V5 calls: ~20.** **Daily cost: ~$0.28. Monthly cost: ~$8.50.**

If we expand to per-bar chart inquiry for active positions: ~5 active positions × 1 call/day = 5 more calls/day → monthly $10.

**Aggressively pessimistic monthly cap: $50/month (~₹4200).** Well within feasibility.

## Failure modes

| Failure | Behavior | Logged |
|---|---|---|
| API timeout (>30s) | Default to REJECT with `veto_source="API_TIMEOUT"`. Don't take trade. | yes |
| API HTTP error | Default to REJECT with `veto_source="API_ERROR"`. Don't take trade. | yes |
| JSON parse failure | Default to REJECT with `veto_source="V5_PARSE_FAIL"`. Save raw response for debug. | yes |
| Contradictory output (zones outside chart range) | Default to REJECT with `veto_source="V5_INCOHERENT"`. Flag for manual review. | yes |
| V5 confidence between 0.4-0.6 + zones broadly disagree | REJECT with `veto_source="V5_UNCERTAIN"`. | yes |

**Fail-closed default.** When in doubt, don't take the trade. The opportunity cost of skipping a real signal is less than the cost of a bad trade.

## Calibration data storage

```
output/v5_calibration/
├── decisions_log.jsonl       # every V5 decision, append-only
│       fields: signal_id, chart_hash, prompt_hash, regime, v5_verdict_full,
│       tietiy_decision, final_decision, outcome (resolved later), cost_usd
├── per_regime_mcnemar.json   # rolling McNemar results, updated weekly
└── threshold_history.jsonl   # every threshold change with rationale + git SHA
```

The `chart_hash` + `prompt_hash` allows determinism check: if V5 disagrees with its prior verdict on the same chart, that's a model-drift signal.

## What V5 is NOT used for

- ❌ Generating signals (zero-shot "find me a trade"). Literature: vision LLMs hallucinate signals on random charts; not robust.
- ❌ Reading numerical levels off charts. Pixel-imprecise; use the TIE TIY-computed zones, not V5's pixel-derived ones.
- ❌ Multi-timeframe analysis from a single image. V5 sees what's drawn; chart generator must render the full context the user wants validated.

## Effort to build

| Component | Hours |
|---|---:|
| V5 client wrapper (already exists in foundation-backtest as reference) | 4 |
| Chart generator (mplfinance-based, like nuvama-vision phase1) | 8 |
| Jaccard overlap math + asymmetric trust logic | 6 |
| Per-regime threshold storage + lookup | 4 |
| McNemar calibration runner (weekly) | 8 |
| Failure-mode handling (5 modes) | 6 |
| Decisions log + chart_hash determinism | 4 |
| Integration with BrainProposer (threshold tuning proposals) | 4 |
| Tests + smoke + sample-N validation | 6 |
| **Total** | **~50 hours** |

## Honest caveat on V5 viability

**The literature is genuinely pessimistic on vision LLMs for chart reading at production stakes.** The user has personally validated V5 on 5-stock + 10-stock + TATASTEEL bar replay tests (`~/code/nuvama-vision/`). The findings from those tests:

- 10-stock retrospective: V5 captured edge that aligned with quant rules. Useful confluence.
- TATASTEEL bar replay (52 walk-forward V5 calls): **FAIL** classification, −0.52 avg R on 3 trades.

The bar-replay FAIL is the closest analogue to how V5 would be used in TIE TIY 2.0 (true walk-forward, no future data). It suggests V5 may not generalize as a real-time gate. Two interpretations:

1. **TATASTEEL is a low-edge stock** (per the 10-stock data) and V5 inherits that. On a higher-edge stock, V5 might do better.
2. **V5's gate value is real but small.** Even at chance-level direction agreement, V5's veto on extreme cases (zone disagreement) might still pay.

Recommended: build V5 gate as a **logged-only** overlay for the first 60 days. Don't gate trades on V5 yet. Accumulate the 80-paired-signal McNemar sample. Then decide.

If McNemar says V5 is noise, the gate is removed; TIE TIY 2.0 still has its full rule library. **The V5 component is removable without rebuilding the system.** That's the value of plug-and-play.
