# Dimension 4 — Signal Lifecycle (birth → death)

**Generated:** 2026-05-13
**Scope:** Trace one signal end-to-end: detected at 08:45, resolved at 15:35–22:00, analyzed at 22:00, proposed into a rule, optionally approved.

---

## The state machine

```
                            ┌────────────────────────────────────────┐
                            │            BORN                        │
                            │  scanner_core.detect_signals()         │
                            │  Conditions: pivot + zone + EMA align  │
                            │  Types: UP_TRI, DOWN_TRI, BULL_PROXY   │
                            │       (+ Second-Attempt detect_sa)     │
                            └──────────────────┬─────────────────────┘
                                               │
                                               ▼
                            ┌────────────────────────────────────────┐
                            │           ENRICHED                     │
                            │  scorer.enrich_signal()                │
                            │  + score, action, target, RR, shares   │
                            │  + scan_price, entry, target_price     │
                            └──────────────────┬─────────────────────┘
                                               │
                                               ▼
                       ┌───────────────────────┴───────────────────────┐
                       │            FILTERED                            │
                       │  mini_scanner.filter_signals()                 │
                       │  Default SHADOW_MODE — all pass; rejections    │
                       │  logged to rejected_log.json only.             │
                       │  If rules active: min_score / min_rr / grade / │
                       │  regime_alignment / require_volume / kill_*    │
                       └─┬─────────────────────┬─────────────────────┬─┘
                         │PASSED              │REJECTED            │KILL_HIT
                         │                    │ (shadow off)       │+contra
                         ▼                    ▼                    ▼
                       LOG_SIGNAL         LOG_REJECTED         contra_shadow.record
                  → signal_history     → signal_history     → contra_shadow.json
                    result=PENDING        result=REJECTED      shadow=INVERTED
                                          (terminal)            outcome=PENDING
                         │
                         ▼
              ┌──────────────────────────┐
              │     SDR COMPOSED L1      │
              │ bridge premarket.py      │
              │ + 9 evidence queries     │
              │ + bucket_engine 4 gates  │
              │ → bridge_state.json      │
              │   (bucket: TAKE_FULL /   │
              │    TAKE_SMALL / WATCH /  │
              │    SKIP)                 │
              └──────────┬───────────────┘
                         │ 📨 premarket Telegram brief (always)
                         ▼
              ┌──────────────────────────┐
              │       09:32 GAP CHECK    │
              │ open_validator.py        │
              │ + actual_open, gap_pct   │
              │ + entry_valid flag       │
              │ → signal_history mutated │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │     SDR COMPOSED L2      │
              │ bridge postopen.py       │
              │ + gap_evaluation query   │
              │ + bucket re-assignment   │
              │ → bridge_state.json      │
              │   bucket_changed flag    │
              └──────────┬───────────────┘
                         │ 📨 postopen Telegram (conditional)
                         ▼
              ┌──────────────────────────┐
              │   INTRADAY TRACKING      │
              │ 09:30–15:30 every 5 min  │
              │ ltp_writer: ltp_prices   │
              │ stop_alert_writer:       │
              │   detect STOP/TARGET hit │
              │   sanity check ±30%/±20% │
              │ → stop_alerts.json       │
              └──────────┬───────────────┘
                         │ 📨 stop_check Telegram (on breach)
                         ▼
              ┌──────────────────────────┐
              │   15:35 OUTCOME EVAL     │
              │ outcome_evaluator.py     │
              │ (THE sole post-09:32     │
              │  mutator of signal_hist) │
              │                          │
              │ For 6-bar tracking window│
              │ from entry_date:         │
              │  - low <= stop  → STOP   │
              │  - high >= target →TARGET│
              │  - else Day 6:           │
              │     close>=entry → WIN   │
              │     close<entry  → LOSS  │
              │     within 0.5%  → FLAT  │
              │                          │
              │ Writes outcome, result,  │
              │ pnl_pct, r_multiple,     │
              │ MFE, MAE, failure_reason,│
              │ data_quality             │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │     SDR COMPOSED L4      │
              │ bridge eod.py            │
              │ plain-dict SDR (no       │
              │ bucket field, outcome    │
              │ block embedded)          │
              │ → bridge_state.json      │
              │   (phase=EOD)            │
              └──────────┬───────────────┘
                         │ 📨 EOD Telegram digest (always)
                         ▼
              ┌──────────────────────────┐
              │   15:35 PATTERN MINER    │
              │ pattern_miner.py         │
              │ Mines (regime,sector,    │
              │   grade) cohorts from    │
              │   RESOLVED signals       │
              │   (not yours alone — all)│
              │ → patterns.json          │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   15:35 RULE PROPOSER    │
              │ rule_proposer.py         │
              │ Promotes patterns →      │
              │ proposed kill/warn/boost │
              │ rules (if no active rule │
              │ already covers them)     │
              │ → proposed_rules.json    │
              │   status=pending         │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   22:00 BRAIN ANALYSIS   │
              │ brain.brain_cli run      │
              │ Step 3 derive:           │
              │   cohort_health,         │
              │   regime_watch,          │
              │   portfolio_exposure     │
              │ Step 4 verify: 16-code   │
              │ Step 5 LLM gates (Opus)  │
              │ Step 6 unified_proposals │
              │   top-3 cap, conflict    │
              │   detection §5.1         │
              │ → output/brain/*.json    │
              │ → proposed_rules.json    │
              │   (dual-write kill_rule  │
              │    + boost_demote)       │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │    USER DECIDES          │
              │ Telegram /approve_rule N │
              │ or /reject_rule N        │
              │ (legacy proposed_rules)  │
              │                          │
              │ /approve <unified_id> &  │
              │ /reject <unified_id>     │
              │ DESIGNED but Step 7      │
              │ DEFERRED — handlers      │
              │ NOT wired yet            │
              └──────────┬───────────────┘
                         │ approve
                         ▼
              ┌──────────────────────────┐
              │   RULE ACTIVATED         │
              │ data/mini_scanner_rules. │
              │ json gains a kill_pattern│
              │ or boost_pattern         │
              │                          │
              │ Future scans now route   │
              │ through this new rule.   │
              │ Loop closes.             │
              └──────────────────────────┘
```

---

## State transitions in `signal_history.json`

The single record evolves through several mutations:

| When | Field changes | Driven by |
|---|---|---|
| 08:45 detect | record created, `result="PENDING"`, `outcome=None` | `journal.log_signal()` |
| 08:45 (if rejected, shadow off) | record created, `result="REJECTED"`, `outcome=None` (terminal) | `journal.log_rejected()` |
| 09:32 | `actual_open`, `gap_pct`, `entry_valid` filled | `open_validator.py` |
| 09:32 (D6B) | if day-6 today: outcome resolved early | `outcome_evaluator` via `open_validator` |
| 15:35 outcome eval | `outcome`, `result`, `exit_date_actual`, `exit_price`, `pnl_pct`, `r_multiple`, `mfe_pct`, `mae_pct`, `failure_reason`, `data_quality` filled | `outcome_evaluator.py` |
| (never) | `result` cycles back to PENDING — once terminal, always terminal | — |
| 90 days later | record archived | `journal.archive_old_records()` → `signal_archive.json` |

**Invariant:** `signal_history.json` is mutated by exactly four scripts: `journal.py` (create), `open_validator.py` (09:32), `outcome_evaluator.py` (15:35 + D6B), `recover_stuck_signals.py` (manual). Bridge composers and brain are READ-ONLY against this file.

---

## Terminal outcomes (5)

```
result        outcome           triggered by                          pnl_pct sign
─────────     ─────────────     ───────────────────────────────       ───────────
PENDING       (none)            initial state                         null
REJECTED      (none)            mini_scanner.kill or filter, shadow=off  null (terminal)
TOOK          STOP_HIT          low(LONG)/high(SHORT) hits stop       negative (forced)
TOOK          TARGET_HIT        high(LONG)/low(SHORT) hits target     positive (~+target_R)
EXITED        DAY6_WIN          close >= entry at day 6               positive
EXITED        DAY6_LOSS         close < entry at day 6                negative
EXITED        DAY6_FLAT         |close-entry|/entry <= 0.5% at day 6  ~0
```

`r_multiple` is capped at `-1.0` for STOP_HIT, `+target_multiplier` (2.0 live / 3.0 shadow) for TARGET_HIT, uncapped for DAY6_*.

---

## Rejection points — where a signal dies before becoming a position

7 major gates (full detail in Dimension 7). Listing in order:

1. **Universe gate** (`universe.py`) — symbol not in `fno_universe.csv` → never scanned.
2. **Corporate-action gate** (`scanner_core.has_recent_corporate_action`) — 60-day skip after split/merge.
3. **Data sufficiency** — <60 bars of yfinance data → skip.
4. **Detection criteria** (scanner_core) — pivot/zone/EMA/wick conditions; if not met, no signal emitted.
5. **Second-attempt blockers** — pending first attempt exists, or SA already open, or no eligible STOPPED parent.
6. **Duplicate-pending filter** (main.py:664) — same symbol + signal_type already PENDING → skip the new one.
7. **Mini-scanner overlay** — min_score, min_rr, regime_alignment, require_volume, grade_gate, kill_patterns. Default `shadow_mode=true` so most rules are passive; only `kill_patterns` (when active) hard-reject and route to `contra_tracker`.
8. **Open validation (09:32)** — `gap_pct > 3%` → `entry_valid=False`. Signal is recorded but **never tracked** by outcome_evaluator.
9. **Sanity rejector (stop_check)** — price moves >30% from entry or >20% from EOD close → alert suppressed (data error guard, not signal rejection).

A signal that survives gates 1–8 becomes a position the system tracks until terminal outcome.

---

## Special tracks

### Second Attempt (SA)
- Only UP_TRI / DOWN_TRI parents that have `result="STOPPED"` can spawn an SA.
- Detection: `scanner_core.detect_second_attempt()` (line 509-630).
- `is_sa=True`, `sa_parent_id=<parent_id>`, `attempt_number=2`.
- Resolved through the same outcome_evaluator path as primary signals.

### Contra Shadow (research)
- If `mini_scanner.kill_patterns` rejects a signal, `contra_tracker.record_inverted_shadow()` records the LONG version of the killed SHORT (or vice versa) into `contra_shadow.json`.
- These shadows do NOT execute or alert — they are research-only.
- Resolved at Day 6 by `outcome_evaluator` (CS3).
- Purpose: validate that the kill_pattern is actually losing money on the original side AND that the inverse would have won.

### prop_005 Shadow (3.0× target)
- Parallel resolution track at `target_multiplier=3.0` (live uses 2.0).
- Computed alongside the live outcome in `outcome_evaluator`.
- Used to measure the edge improvement of larger-target exits in backtests.

---

## What a single signal record looks like over time

A signal `2026-05-13-TATASTEEL-UP_TRI` (LONG, Auto sector, Choppy regime):

```
08:45  CREATED   result=PENDING  outcome=null  score=6  entry=155  stop=148  target=169
                 gap_pct=null    actual_open=null
09:32  GAP_OK    gap_pct=0.4  actual_open=155.6  entry_valid=true
        (no other changes; record still PENDING)
09:40  L2 SDR    bucket re-eval: still WATCH (no bucket_changed)
        (no signal_history mutation)
10:15  LTP UPD   (no signal_history mutation; ltp_prices.json updated)
13:30  LTP UPD   (no signal_history mutation)
15:00  STOP HIT  low touched 147.5 — stop_alert fired
        (Telegram only; signal_history NOT mutated yet)
15:35  OUTCOME   result=TOOK  outcome=STOP_HIT  exit_price=147.5  pnl_pct=-4.83
                 r_multiple=-1.0  mfe_pct=+0.8  mae_pct=-4.83
                 failure_reason="Choppy regime fresh breakout failed"
                 data_quality="eod_primary"
16:15  EOD SDR   appears in bridge_state.json (phase=EOD) as plain-dict with outcome block
21:00+ now feeds pattern_miner the next day (or 22:00 cohort_health)
```

---

## Where to look for each phase

| Phase | Script | Output |
|---|---|---|
| Detect | `scanner/scanner_core.py:detect_signals()` | in-memory dict |
| Enrich | `scanner/scorer.py:enrich_signal()` | enriched dict |
| Filter | `scanner/mini_scanner.py:filter_signals()` | (passed, all, rejections) |
| Log | `scanner/journal.py:log_signal()` | `output/signal_history.json` |
| L1 SDR | `scanner/bridge/composers/premarket.py` | `output/bridge_state.json` |
| Gap check | `scanner/open_validator.py` | `output/open_prices.json` + mutates SH |
| L2 SDR | `scanner/bridge/composers/postopen.py` | `output/bridge_state.json` |
| LTP | `scanner/ltp_writer.py` | `output/ltp_prices.json` |
| Stop/Target | `scanner/stop_alert_writer.py` | `output/stop_alerts.json` |
| Outcome | `scanner/outcome_evaluator.py` | mutates SH |
| L4 SDR | `scanner/bridge/composers/eod.py` | `output/bridge_state.json` |
| Mine | `scanner/pattern_miner.py` | `output/patterns.json` |
| Propose | `scanner/rule_proposer.py` | `output/proposed_rules.json` |
| Brain derive | `scanner/brain/brain_derive.py` | `output/brain/*.json` |
| Brain propose | `scanner/brain/brain_output.py` | `output/brain/unified_proposals.json` |
| Approve | `scanner/telegram_bot.py:_respond_approve_rule()` | mutates `data/mini_scanner_rules.json` |
