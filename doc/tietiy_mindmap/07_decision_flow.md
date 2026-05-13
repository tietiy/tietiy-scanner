# Dimension 7 — Decision Flow (how a signal becomes a trade)

**Generated:** 2026-05-13
**Scope:** The gating chain from raw detection to a user-actionable alert. Every place a signal can die.

---

## The gating chain — top to bottom

```
                     yfinance daily bars (188 stocks)
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 1: UNIVERSE                   ║   data/fno_universe.csv
            ║ Stock must be in F&O universe      ║
            ╚════════════════════════════════════╝
                                │ skip if not in list
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 2: CORPORATE ACTION           ║   scanner_core.py:612
            ║ Skip 60 days after split/merge     ║
            ╚════════════════════════════════════╝
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 3: BAN LIST                   ║   banned_stocks.json
            ║ Skip if in F&O ban period          ║
            ╚════════════════════════════════════╝
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 4: DATA SUFFICIENCY           ║   scanner_core.py:620
            ║ Need ≥60 bars of daily data        ║
            ╚════════════════════════════════════╝
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 5: DETECTION CRITERIA         ║   scanner_core.py:261
            ║ - Pivot detected                   ║
            ║ - Near SMC zone (nearSZ)           ║
            ║ - EMA alignment                    ║
            ║ - Age 0-3 (BULL_PROXY: 0-1)        ║
            ║ - ATR non-zero, non-NaN            ║
            ║ - Stop validity (stop < close)     ║
            ║ - For BULL_PROXY: close ≥60% of    ║
            ║   range, lower wick ≥40%           ║
            ╚════════════════════════════════════╝
                                │ signal emitted
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 6: SECOND-ATTEMPT FILTERS     ║   scanner_core.py:509
            ║ Only UP_TRI/DOWN_TRI parents with  ║
            ║ result=STOPPED can spawn SA.       ║
            ║ Skip if: pending first attempt,    ║
            ║ pending SA, no eligible parent.    ║
            ╚════════════════════════════════════╝
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║       ENRICHED                     ║   scorer.py:173
            ║ score, action, target, RR, shares  ║
            ╚════════════════════════════════════╝
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 7: DUPLICATE PENDING          ║   main.py:664
            ║ Same symbol+signal already PENDING ║
            ║ → skip the new one                 ║
            ╚════════════════════════════════════╝
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 8: MINI-SCANNER OVERLAY       ║   mini_scanner.py:150
            ║                                    ║
            ║ Per rule (active only):            ║
            ║   min_score        →  if low: REJ  ║
            ║   min_rr           →  if low: REJ  ║
            ║   regime_alignment →  mismatch:REJ ║
            ║   require_volume   →  not conf:REJ ║
            ║   grade_gate       →  not in: REJ  ║
            ║   kill_patterns    →  HARD KILL +  ║
            ║                       contra shadow║
            ║                                    ║
            ║ DEFAULT shadow_mode=true:          ║
            ║   rejections only logged, signal   ║
            ║   still LOG_SIGNAL'd.              ║
            ║                                    ║
            ║ kill_patterns BYPASS shadow_mode   ║
            ║ → always reject + record contra.   ║
            ╚════════════════════════════════════╝
                       │ passed              │ rejected (shadow off)
                       │                     │
                       ▼                     ▼
                journal.log_signal()   journal.log_rejected()
                → signal_history       → signal_history
                  result=PENDING         result=REJECTED (TERMINAL)
                       │
                       ▼
            ╔════════════════════════════════════╗
            ║       SDR L1 PRE_MARKET            ║   bridge/composers/premarket.py
            ║                                    ║
            ║ 4-gate bucket_engine tree:         ║
            ║                                    ║
            ║ ▶ Gate 1: KILL MATCH               ║
            ║   if kill_match: bucket=SKIP       ║
            ║                                    ║
            ║ ▶ Gate 2: VALIDITY                 ║
            ║   if rr<min OR age>max OR          ║
            ║     entry_valid=False:             ║
            ║                  bucket=SKIP       ║
            ║                                    ║
            ║ ▶ Gate 3: BOOST MATCH              ║
            ║   if Tier A: bucket=TAKE_FULL      ║
            ║   if Tier B: bucket=TAKE_SMALL     ║
            ║                                    ║
            ║ ▶ Gate 4: EVIDENCE CONSENSUS       ║
            ║   from exact_cohort + sector_30d   ║
            ║   + regime_baseline:               ║
            ║     strong consensus → TAKE_FULL   ║
            ║     moderate → TAKE_SMALL          ║
            ║     thin/mixed → WATCH             ║
            ║     opposing → SKIP                ║
            ╚════════════════════════════════════╝
                                │
                                ▼
                  📨 Telegram premarket brief (ALWAYS)
                                │
                                ▼
                  USER reads bucket assignment
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 9: 09:32 OPEN VALIDATION      ║   open_validator.py
            ║ |gap_pct| > 3%: entry_valid=False  ║
            ║   → outcome_evaluator will skip    ║
            ║   → SDR L2 will mark as SKIP       ║
            ║ |gap_pct| > 1.5%: warning only     ║
            ╚════════════════════════════════════╝
                                │
                                ▼
            ╔════════════════════════════════════╗
            ║       SDR L2 POST_OPEN             ║   bridge/composers/postopen.py
            ║                                    ║
            ║ If gap_evaluation.entry_still_     ║
            ║ valid=False:                       ║
            ║   _force_skip_invalid_entry()      ║
            ║   bucket=SKIP, gate=L2_GAP_INVALID║
            ║                                    ║
            ║ Else re-run bucket_engine with     ║
            ║ updated rr_at_actual_open.         ║
            ║ Compare to L1 bucket → may set     ║
            ║ bucket_changed=True.               ║
            ║                                    ║
            ║ should_send_telegram =             ║
            ║   (bucket_changes>0 OR             ║
            ║    gap_breaches>0)                 ║
            ╚════════════════════════════════════╝
                                │ conditional 📨
                                ▼
            ╔════════════════════════════════════╗
            ║ Gate 10: SANITY GUARD              ║   stop_alert_writer.py:G2/G6
            ║ (suppression, not rejection)       ║
            ║                                    ║
            ║ |current_price - entry| > 30%      ║
            ║   OR                               ║
            ║ |current_price - last_EOD| > 20%   ║
            ║   → alert SUPPRESSED, marked       ║
            ║     UNKNOWN, warning logged        ║
            ║                                    ║
            ║ This is anti-MARUTI-ghost-stop —   ║
            ║ prevents bad data triggering exits ║
            ╚════════════════════════════════════╝
                                │
                                ▼
                  USER decides (paper or live)
                                │
                                ▼
                  Position runs to terminal outcome
```

---

## Bucket assignment (the four buckets)

| Bucket | Action | Color hint | Telegram emoji |
|---|---|---|---|
| **TAKE_FULL** | Trade with full position size (5% capital risk) | green | ✅ |
| **TAKE_SMALL** | Trade with reduced size (3% capital risk) | yellow | ⚠️ |
| **WATCH** | Don't trade yet; track for confirmation | grey | 👀 |
| **SKIP** | Do not trade (kill/invalid/no edge) | red | ❌ |

Bucket lives only in PRE_MARKET and POST_OPEN SDRs. EOD SDRs are plain dicts with an `outcome` block — no bucket, because the signal is closed.

---

## bucket_engine 4-gate tree (`scanner/bridge/core/bucket_engine.py`)

The L1 / L2 bucket assignment walks four gates in order, returning the first match:

```python
def assign_bucket(signal, evidence):
    # Gate 1: KILL MATCH
    if evidence['kill_match']:
        return SKIP (reason: "kill pattern matched")

    # Gate 2: VALIDITY
    if signal.rr < VALIDITY_MIN_RR:           return SKIP (low R:R)
    if signal.age > VALIDITY_MAX_AGE:         return SKIP (too old)
    if signal.entry_valid is False:           return SKIP (gap-invalidated)

    # Gate 3: BOOST MATCH
    if evidence['boost_match']:
        if tier == 'A': return TAKE_FULL
        if tier == 'B': return TAKE_SMALL

    # Gate 4: EVIDENCE CONSENSUS
    return _gate4_evidence(evidence)
        # examines exact_cohort.wr / sector_recent_30d / regime_baseline
        # → TAKE_FULL / TAKE_SMALL / WATCH / SKIP
```

---

## Score → action mapping (scanner-side, separate from bucket)

`scorer.get_action()` produces the legacy action label (used in `signal_history`):

| Score | Action |
|---|---|
| ≥6 | DEPLOY |
| 3–5 | WATCH |
| 2 | CAUTION |
| <2 | NO_TRADE |

This is **independent** of the bucket assignment from the bridge. Bucket is the trader-facing decision; action is the scorer's legacy classification, kept for backward compat.

---

## Scoring breakdown (`scorer.score_signal()`)

| Layer | Adds | When |
|---|---|---|
| age=0 | +3 | freshest |
| age=1 | +2 | yesterday |
| UP_TRI × Bear | +3 | highest conviction (per backtest) |
| UP_TRI × Bull | +2 | |
| UP_TRI × Choppy | +1 | |
| DOWN_TRI | +2 | no regime filter |
| BULL_PROXY (Bull/Choppy only) | +1 | |
| vol_confirm | +1 | quality |
| sector_leading | +1 | quality |
| rs_strong | +1 | quality |
| grade_A | +1 | quality |
| Cap | 10 | maximum |

---

## All "no-trade" rejection points (master list)

Ordered by stage:

| # | Stage | Killed by | What it means |
|---|---|---|---|
| 1 | universe | not in fno_universe.csv | symbol never scanned |
| 2 | scanner_core:612 | `has_recent_corporate_action()` | 60-day cooldown |
| 3 | main.py | `banned_stocks` list | F&O ban period |
| 4 | scanner_core:620 | <60 bars data | insufficient history |
| 5 | scanner_core:622 | yfinance download failed | fetch_failed list |
| 6 | scanner_core:436 | ATR NaN or ≤0 | data integrity |
| 7 | scanner_core:442 | not nearSZ | no SMC zone proximity |
| 8 | scanner_core:445 | bar range too small | sub-pip; can't size |
| 9 | scanner_core:456 | age > 1 (BULL_PROXY only) | aged-out |
| 10 | scanner_core:462 | stop_z ≥ close | invalid stop |
| 11 | scanner_core:450-452 | BULL_PROXY: close <60% or wick <40% | weak setup |
| 12 | scanner_core:544 | SA: pending first attempt | conflict |
| 13 | scanner_core:546 | SA: SA already open | duplicate |
| 14 | scanner_core:567-572 | SA: no STOPPED parent | nothing to retry |
| 15 | main.py:664 | duplicate-pending | already in book |
| 16 | mini_scanner | active rule: min_score below threshold | REJECTED (shadow off) |
| 17 | mini_scanner | active rule: min_rr below | REJECTED |
| 18 | mini_scanner | active rule: regime_alignment | REJECTED |
| 19 | mini_scanner | active rule: require_volume | REJECTED |
| 20 | mini_scanner | active rule: grade_gate | REJECTED |
| 21 | mini_scanner | kill_pattern hit | KILLED + contra shadow |
| 22 | bucket_engine Gate 1 | kill_match | bucket=SKIP |
| 23 | bucket_engine Gate 2 | rr < min_rr | bucket=SKIP |
| 24 | bucket_engine Gate 2 | age > max | bucket=SKIP |
| 25 | bucket_engine Gate 2 | entry_valid=False | bucket=SKIP |
| 26 | bucket_engine Gate 4 | no evidence consensus | bucket=SKIP or WATCH |
| 27 | open_validator | gap > 3% | entry_valid=False (never tracked) |
| 28 | postopen | L2_GAP_INVALID | bucket force-SKIP regardless of evidence |

(Stops 28 are not necessarily "kills" — some are bucket downgrades. But each is a place where the signal is removed from "trade today" candidacy.)

---

## Current state (2026-05-13)

Per session-context input:
- 8 signals today, all bucketed SKIP
- Regime = "Choppy" (stable for 7 days)
- Banner = "LIVE — partial data" (DEGRADED)

The dominant reason 8/8 SKIP today is **Gate 8 + bucket_engine Gate 4**:
- Most boost rules in `mini_scanner_rules.json` are regime-gated to Bear or Bull (or sector-gated to Metal/Auto/etc.).
- Choppy regime + Auto/Bank/Energy/etc. has no active boost match → bucket_engine falls through to Gate 4 (Evidence Consensus).
- Evidence Consensus for current cohorts in Choppy regime is thin (low n, mediocre WR) → defaults to SKIP.

This is correct behavior. The "DEGRADED" banner is bridge-side, not brain-side. The brain has proposed 2 boost_promote candidates pending user approval, but those are Bear/Metal-gated and won't help in Choppy regime.

---

## Who makes which decision

| Decision | Made by | Override? |
|---|---|---|
| Should we scan this stock? | universe.csv + ban list + corp-action filter | manually edit fno_universe.csv |
| Is this a signal? | scanner_core conditions (deterministic) | tune `config.py` constants |
| What's its score? | scorer.py rules | tune `config.py` thresholds |
| Apply rules? | mini_scanner_rules.json shadow_mode | edit `data/mini_scanner_rules.json` |
| Bucket TAKE_FULL/TAKE_SMALL/WATCH/SKIP? | bucket_engine 4 gates | activate/approve a kill or boost rule |
| Reclassify after open? | postopen gap_evaluation | only on gap_pct > 3% |
| Stop hit / target hit? | stop_alert_writer (sanity-guarded) | n/a — driven by price |
| Outcome (win/loss/flat)? | outcome_evaluator 6-bar window | n/a |
| Pattern? | pattern_miner (Tier validated/preliminary) | n/a |
| Proposed rule? | rule_proposer (and brain dual-write) | edit thresholds |
| Approve rule? | **USER via Telegram** `/approve_rule N` | only path to mutate mini_scanner_rules.json |
| Trade it? | **USER (manually, paper or live)** | the system never executes a trade |

---

## What the system explicitly does NOT do

- **It never places an order.** No broker integration. All trading is manual based on Telegram alerts.
- **It never auto-applies a brain proposal.** `unified_proposals.json` requires explicit `/approve` (designed; Step 7 deferred).
- **It never modifies bridge_state in retro.** Phase SDRs are immutable. L2 doesn't rewrite L1; it composes a new POST_OPEN snapshot.
- **It never re-runs morning_scan during the day.** Once the day's signals are detected at 08:45, no new signals appear until 08:45 next morning. (LTP/stop updates don't generate new entries.)
- **It never resolves an outcome until at least 15:35.** The earliest possible resolution is 09:32 (D6B: if today is Day-6 for a signal), and even that re-uses the outcome_evaluator at 15:35 path internally.
