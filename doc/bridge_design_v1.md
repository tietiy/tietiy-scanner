# TIE TIY Bridge — Design v1

**Status:** Locked design specification
**Owner:** Abhishek (decisions) + Claude (execution partner)
**Last design session:** 2026-04-26
**Implementation start:** Wave 2
**Canonical with:** `doc/fix_table.md`, `doc/session_context.md`

---

## Purpose of this document

This is the contract for what gets built. Every wave from Wave 2 onward implements against this spec. If reality diverges from this spec during build, this spec gets updated first, then code follows.

The bridge is the integration layer between TIE TIY's existing scanner pipeline and its consumers (PWA, Telegram). It composes Signal Decision Records (SDRs) from truth files, sorts them into action buckets, surfaces evidence chains, and tracks contra-rule research as it evolves toward promotion.

The bridge does NOT replace any existing module. It reads, composes, surfaces. It writes ONE state file. It owns its own folder.

---

## Table of contents

1. Architecture principles
2. The Decision Surface model
3. The day flow (08:35 → 16:08)
4. The Signal Decision Record (SDR)
5. The decision tree (bucket assignment)
6. The four bucket types — full examples
7. Contra-tracker integration and lifecycle
8. The bridge folder structure
9. Background queries (the analytical depth layer)
10. bridge_state.json schema
11. PWA integration
12. Telegram template structure
13. GitHub Actions wiring
14. Error handling and graceful degradation
15. Wave plan and file inventory
16. Out-of-scope and deferred decisions
17. Open questions for future decisions

---

## 1. Architecture principles

These are the load-bearing principles. Every implementation choice traces back to one of these.

### 1.1 Read-only by design

The bridge reads existing JSON truth files (signal_history, patterns, mini_scanner_rules, etc). It writes ONLY:
- `output/bridge_state.json`
- `output/bridge_state_history/<date>_<phase>.json`
- `output/query_proposals.json` (Wave 4-5 only)

It never modifies signal_history, patterns, or any other module's truth file. Truth flows one direction: scanner → journal → bridge → state → consumers. User intent flows back via Telegram approvals only.

### 1.2 Plugin architecture for things that grow

Three folders use plugin discovery patterns:
- `scanner/bridge/queries/` — query plugins (auto-loaded via _registry.py)
- `scanner/bridge/alerts/` — alert detector plugins (auto-loaded)
- `scanner/bridge/learner/` — gap detector plugins (auto-loaded, Wave 5+)

Adding capability = adding a file. Engine never changes when capabilities grow.

### 1.3 Pure functions for things that don't grow

- `scanner/bridge/rules/` — pure functions, stateless, no I/O
- `scanner/bridge/core/` — orchestration, single responsibility per file
- `scanner/bridge/composers/` — three phase entry points
- `scanner/bridge/templates/` — Telegram rendering, decoupled from compose

These don't grow over time. Their file count is fixed by the architecture.

### 1.4 Single write chokepoint

Only `core/state_writer.py` writes to disk. Atomic writes (tmp file → rename). Single file = single point of failure analysis.

### 1.5 Graceful degradation, never silent failure

If any plugin fails during compose, bridge writes a degraded state with explicit warning, sends Telegram error, exits non-zero (so GitHub Actions notification fires). User always knows when bridge is degraded.

### 1.6 Schema versioning from day one

Every JSON file the bridge produces has `schema_version: 1` from day one. Reader code checks version, gracefully handles unknown future versions.

### 1.7 Immutable phase records

Each compose produces SDRs frozen at that phase. L2 doesn't mutate L1's SDR — it produces a new POST_OPEN SDR for the same signal. This gives us free history + audit trail + no race conditions.

### 1.8 Bridge auto-evolves with data

Bridge runs 7 background queries on every compose, embedding analytical depth into every SDR. As signal_history grows, bridge's evidence depth grows automatically. No manual rule encoding required for bridge to learn — though encoded rules (boost_patterns, kill_patterns) take priority when they match.

### 1.9 Human approval mandatory for structural changes

No auto-promote, no auto-activate, no auto-modify rules. Bridge can DETECT promotion-readiness, can DETECT pattern emergence, can WRITE proposals. But changes to mini_scanner_rules.json or other truth files require explicit Telegram /approve commands. The Telegram poll is the single write-back channel from user to system.

### 1.10 Forward-compatible reserved fields

Wave 2 ships SDRs with empty `counter_evidence`, `learner_hooks`, etc. Wave 4-5 fills them. Same schema version, no migration needed. Reserved fields are a constitutional pattern.

---

## 2. The Decision Surface model

The bridge is not three separate things (backend, frontend, learner). It is ONE thing — the Decision Surface — viewed from three angles.
┌─────────────────────────────────────┐
             │      THE DECISION SURFACE           │
             │   one system, three faces           │
             └─────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
    ┌─────────┐    ┌─────────┐    ┌─────────────┐
    │ COMPOSE │    │ PRESENT │    │   LEARN     │
    │ (Python)│    │  (PWA + │    │ (Self-Query)│
    │         │    │ Telegram)│    │             │
    └─────────┘    └─────────┘    └─────────────┘
   reads truth      renders state    detects gaps
composes SDRs    captures intent  proposes queries
writes state     sends approvals  evolves system 
A signal exists in all three faces simultaneously:
- In Compose: it has SDR identity, evidence, bucket assignment
- In Present: it has card, tap targets, [why?] expansion
- In Learn: it has confidence band, gap flags, self-query candidates

Designing one face without the others fails. Designing them together as one Decision Surface succeeds.

This is why Bridge folder, Intelligence tab, and Learner share a single design document, not three. They are aspects of one thing.

---

## 3. The day flow (08:35 → 16:08 IST)

Anchored to Indian market hours. All timings IST.
08:35   morning_scan.yml fires (cron)
├─ scanner_core scans 188 stocks via yfinance (yesterday's close — settled)
├─ scorer assigns 1-10 scores
├─ mini_scanner applies kill_patterns
│   └─ on kill match: contra_tracker.record() writes shadow
├─ journal writes signal_history.json (NEW signals, result=PENDING)
├─ meta_writer updates meta.json
└─ chain_validator runs (M-05 expanded coverage)
└─ system_health.json updated
08:50   morning_scan completes
└─ workflow_run trigger fires next workflow
08:55   bridge_premarket.yml fires
├─ bridge.py --phase=PRE_MARKET runs
├─ Reads truth files (see §10)
├─ Composes SDRs (one per PENDING signal)
├─ Composes contra block
├─ Composes alerts
├─ Writes bridge_state.json
├─ Writes bridge_state_history/2026-04-29_premarket.json
└─ Sends Telegram pre-market brief
09:00   bridge_state.json complete on disk
└─ Available for PWA fetch
09:05   Telegram brief lands
└─ USER ACTION POINT 1: Read brief, plan orders for 09:15
09:15   Market opens
└─ User places orders based on bridge L1 recommendations
09:32   open_validator.yml fires (cron, +5 min from market open)
├─ Captures actual_open from yfinance (now reliable)
├─ Computes gap%, sets entry_valid=true/false
├─ Updates open_prices.json
└─ Triggers bridge_postopen via workflow_run
09:40   bridge_postopen.yml fires
├─ bridge.py --phase=POST_OPEN runs
├─ Reads same truth files PLUS open_prices.json (fresh)
├─ For each L1 SDR:
│   ├─ Re-evaluate gap_caveat with actual_open
│   ├─ Recompute R:R with actual entry
│   ├─ Re-run bucket assignment
│   ├─ If bucket flipped: set bucket_changed=true
│   └─ Write new POST_OPEN SDR
├─ Detect gap_breach alerts
├─ Write bridge_state.json (POST_OPEN phase)
└─ Send Telegram alert ONLY if gap_breach OR bucket_change
09:45   bridge_state.json updated
09:47   Telegram alert (conditional)
└─ USER ACTION POINT 2: Check positions if alert fires
09:50–15:30   Mid-day
├─ ltp_writer runs every 5 min (existing)
├─ stop_alert_writer runs every 5 min (existing)
├─ Stop hits trigger Telegram (existing)
└─ Bridge silent — no compose
15:30   Market closes
15:35   eod_master.yml fires
├─ eod_prices_writer captures EOD OHLC
├─ outcome_evaluator resolves Day-6 + stop hits
│   └─ contra_shadow resolutions also computed
├─ pattern_miner re-mines patterns
├─ rule_proposer drafts new proposals
├─ chain_validator runs
├─ meta_writer updates
└─ Triggers bridge_eod via workflow_run
16:00   bridge_eod.yml fires
├─ bridge.py --phase=EOD runs
├─ Reads everything fresh (all just updated)
├─ For today's signals: composes EOD SDR with outcome embedded
├─ For new patterns: includes in narrative
├─ For new proposals: includes in alerts
├─ Writes bridge_state.json (EOD phase)
├─ Writes bridge_state_history/2026-04-29_eod.json
└─ Sends Telegram EOD digest
16:08   Telegram EOD digest lands
└─ USER ACTION POINT 3: Review only
23:00   auto_analyst.py runs (existing, conditional on 5+ resolutions)
└─ colab_insights.json may update for tomorrow
Three composes. Three user action points. Three trigger workflows. Each fires AFTER its upstream completes (workflow_run cascade), never on independent crons. If upstream fails, bridge doesn't fire — chain_validator catches it next morning.

---

## 4. The Signal Decision Record (SDR)

The atomic unit of the bridge. Every signal becomes one SDR per phase. SDRs are immutable per phase — L2 produces new POST_OPEN SDRs, never mutates L1 PRE_MARKET SDRs.

### 4.1 SDR structure (full)

```json
{
  "sdr_id": "sdr_2026-04-29_PRE_MARKET_TATAMOTORS_UP_TRI",
  "signal_id": "2026-04-29-TATAMOTORS-UP_TRI",
  "phase": "PRE_MARKET",
  "phase_timestamp": "2026-04-29T03:00:00Z",
  "market_date": "2026-04-29",
  
  "symbol": "TATAMOTORS",
  "signal_type": "UP_TRI",
  "direction": "LONG",
  "sector": "Auto",
  "regime": "Bear",
  "age_days": 0,
  "is_sa_variant": false,
  "origin": null,
  
  "trade_plan": {
    "scan_price": 982.40,
    "actual_open": null,
    "entry": 982.40,
    "stop": 962.20,
    "target": 1024.80,
    "rr": 2.10,
    "risk_per_share": 20.20,
    "atr": 18.50,
    "score": 9,
    "score_components": {
      "base_score": 5,
      "regime_bonus": 3,
      "vol_confirm": 1,
      "rs_strong": 0,
      "sec_leading": 0,
      "grade_bonus": 0
    }
  },
  
  "bucket": "TAKE_FULL",
  "bucket_reason_short": "Tier A boost: UP_TRI × Auto × Bear (21/21 WR)",
  "bucket_reason_long": "Strongest validated cohort in system. Bear-regime UP_TRI in Auto sector has 21 historical resolutions, all wins (100% WR, avg P&L +4.85%). Pattern entered Validated tier April 22. R:R 2.1 acceptable. No counter-evidence flags.",
  "bucket_changed": false,
  "previous_bucket": null,
  "bucket_change_reason": null,
  
  "gap_caveat": {
    "applies": true,
    "threshold_pct": 2.0,
    "direction": "adverse",
    "absolute_threshold_price": 1002.05,
    "instruction": "Place at 09:15 open. If actual open gaps > 2% above scan_price (above ₹1002.05), reconsider entry — gap likely consumed expected upside.",
    "evaluated_at_l2": false,
    "gap_outcome": null,
    "gap_outcome_message": null
  },
  
  "evidence": {
    "patterns_supporting": [
      {
        "pattern_id": "P_UP_TRI_Auto_Bear",
        "tier": "VALIDATED",
        "n": 21,
        "wr": 1.00,
        "avg_pnl": 4.85,
        "edge_vs_baseline_pp": 19.0,
        "source_file": "patterns.json"
      }
    ],
    "patterns_opposing": [],
    "boost_match": {
      "boost_id": "win_001",
      "tier": "A",
      "matched_on": "signal+sector+regime",
      "source_file": "mini_scanner_rules.json"
    },
    "kill_match": null,
    "exact_cohort": {
      "n": 21,
      "wr": 1.00,
      "avg_pnl": 4.85,
      "avg_mfe": 6.2,
      "avg_mae": 1.4,
      "tier_status": "validated"
    },
    "sector_recent_30d": {
      "n": 24,
      "wr": 0.92,
      "avg_pnl": 3.8,
      "trend": "improving"
    },
    "regime_baseline": {
      "n": 78,
      "wr": 0.78,
      "avg_pnl": 2.9
    },
    "score_bucket": {
      "score": 9,
      "n": 18,
      "wr": 0.94
    },
    "stock_recency": {
      "last_signal_date": "2026-03-12",
      "last_outcome": "WON",
      "lookback_30d_count": 0,
      "lookback_30d_wr": null
    },
    "anti_pattern_check": null,
    "cluster_warnings": [],
    "active_proposals_relevant": [],
    "colab_insight_excerpt": "Auto sector defensive rotation continues; Bear-regime breakouts compounding since April 18.",
    "narrative_context": null
  },
  
  "counter_evidence": {
    "patterns_against": [],
    "data_quality_flags": [],
    "regime_concerns": [],
    "cluster_warnings": []
  },
  
  "display": {
    "card_title": "TATAMOTORS • UP_TRI",
    "card_subtitle": "Auto • Bear • Score 9 • Tier A",
    "card_color_hint": "green",
    "card_priority": 95,
    "show_in_main_signals_tab": true,
    "show_in_contra_tab": false,
    "tappable_for_why": true,
    "telegram_emoji": "✅",
    "telegram_priority": 95
  },
  
  "learner_hooks": {
    "self_query_candidates": [],
    "confidence_band": "high",
    "uncertainty_dimensions": [],
    "gap_flags": []
  },
  
  "audit": {
    "composed_by_version": "bridge_v1.0.0",
    "compose_duration_ms": 32,
    "upstream_health_at_compose": {
      "morning_scan": "ok",
      "pattern_miner": "ok",
      "rule_proposer": "ok",
      "contra_tracker": "ok"
    },
    "queries_executed": [
      "q_signal_today",
      "q_pattern_match",
      "q_boost_match",
      "q_kill_match",
      "q_exact_cohort",
      "q_sector_recent_30d",
      "q_regime_baseline",
      "q_score_bucket",
      "q_stock_recency",
      "q_anti_pattern",
      "q_cluster_check"
    ],
    "queries_failed": []
  }
}
```

### 4.2 Field group rationale

**Identity** (sdr_id, signal_id, phase, market_date, symbol, etc) — locates the SDR uniquely in time and space.

**trade_plan** — concrete trade parameters. `actual_open` is null at L1, populated at L2.

**bucket + bucket_reason_short/long** — the decision and its explanation. Short for cards, long for [why?] expansion.

**gap_caveat** — Path C contribution. L1 forward-looking, L2 evaluated.

**evidence** — everything the bridge knew when composing. Includes 7 background-query results plus boost/kill/pattern matches.

**counter_evidence** — reserved for Wave 4. Empty in Wave 2.

**display** — Compose's hints to Present. Decouples rendering from logic.

**learner_hooks** — reserved for Wave 5. Empty in Wave 2.

**audit** — bridge meta-info. Critical for debugging degraded composes.

---

## 5. The decision tree (bucket assignment)

The bucket_engine.py walks every signal through the same gates. First match wins. Order matters.
┌──────────────────────────┐
                │   SIGNAL ARRIVES         │
                │  (from signal_history)   │
                └────────────┬─────────────┘
                             │
                             ↓
                ┌──────────────────────────┐
                │  GATE 1 — KILL MATCH?    │
                └────────────┬─────────────┘
              YES ───────────┤
                │            │ NO
                ↓            ↓
        ┌────────────┐  ┌──────────────────────────┐
        │   SKIP     │  │  GATE 2 — VALIDITY?      │
        │  killed    │  │  entry_valid +           │
        └────────────┘  │  R:R ≥ 1.5 + age sane    │
                        └────────────┬─────────────┘
                          FAIL ──────┤
                            │        │ PASS
                            ↓        ↓
                    ┌────────────┐  ┌──────────────────────────┐
                    │   SKIP     │  │  GATE 3 — BOOST MATCH?   │
                    │  invalid   │  └────────────┬─────────────┘
                    └────────────┘               │
                          ┌──────────────────────┤
                          │ TIER A           TIER B  │ NO
                          ↓                      ↓   ↓
                  ┌────────────┐        ┌────────────┐  ┌──────────────────────────┐
                  │  TAKE_FULL │        │ TAKE_SMALL │  │  GATE 4 — EVIDENCE       │
                  │  Tier A    │        │  Tier B    │  │  CONSENSUS               │
                  │  boost     │        │  boost     │  │  (uses 7 bg queries)     │
                  └────────────┘        └────────────┘  └────────────┬─────────────┘
                                                      ┌──────────────┼──────────────┐
                                                      │              │              │
                                                   STRONG       PROMISING        WEAK
                                                   (n≥10        (n≥5            (other)
                                                   WR≥0.75      WR≥0.65
                                                   no warnings) supportive)
                                                      │              │              │
                                                      ↓              ↓              ↓
                                              ┌────────────┐  ┌──────────┐  ┌──────────┐
                                              │ TAKE_SMALL │  │  WATCH   │  │   SKIP   │
                                              │ promoted   │  │ thin     │  │ no edge  │
                                              │ from cohort│  │ evidence │  │          │
                                              └────────────┘  └──────────┘  └──────────┘
                                              ### 5.1 Gate definitions

**Gate 1 — KILL MATCH:** Signal matches an active kill_pattern in mini_scanner_rules.json. Hard SKIP regardless of other factors.

**Gate 2 — VALIDITY:** Signal must have entry_valid=true (or null), R:R ≥ 1.5, age within sane bounds (0-1 for most signals, 0 for DOWN_TRI per backtest). Failure → SKIP.

**Gate 3 — BOOST MATCH:** Signal matches an active boost_pattern.
- Tier A → TAKE_FULL
- Tier B → TAKE_SMALL

**Gate 4 — EVIDENCE CONSENSUS:** No boost match found. Bridge uses background queries to evaluate:
- exact_cohort strong (n≥10, WR≥0.75) AND no cluster_warning AND no anti_pattern → TAKE_SMALL
- exact_cohort moderate (n≥5, WR≥0.65) AND sector_recent supportive AND no concerning signals → WATCH
- exact_cohort weak (n<5) BUT sector_recent_30d strong AND regime_baseline supportive → WATCH (with thin-evidence note)
- Otherwise → SKIP (with explicit reasoning)

### 5.2 Key principles

- Kill rules over instinct (Gate 1)
- Math sanity before opinion (Gate 2)
- Hard-earned validated patterns get priority (Gate 3)
- Default at fall-through is SKIP, not WATCH (conservative bias)
- Bridge is honest about evidence depth — doesn't promote thin cohorts to TAKE_SMALL

---

## 6. The four bucket types — full examples

### 6.1 TAKE_FULL (Tier A boost)

Example: TATAMOTORS UP_TRI Bear regime Auto sector. Score 9.

Bridge sees:
- kill check: no
- validity: pass (R:R=2.1)
- boost check: HIT — UP_TRI×Auto×Bear is win_001 (Tier A)
- DECISION: TAKE_FULL

Key SDR fields:
- bucket: "TAKE_FULL"
- bucket_reason_short: "Tier A boost: UP_TRI × Auto × Bear (21/21 WR)"
- evidence.boost_match: win_001
- display.card_color_hint: "green"
- display.card_priority: 95
- display.telegram_emoji: "✅"
- learner_hooks.confidence_band: "high"

### 6.2 TAKE_SMALL (Tier B boost)

Example: HUDCO BULL_PROXY Bear regime Infra sector. Score 7.

Bridge sees:
- kill check: no
- validity: pass (R:R=1.65)
- boost check: HIT — BULL_PROXY × ANY × Bear is win_007 (Tier B)
- DECISION: TAKE_SMALL

Key SDR fields:
- bucket: "TAKE_SMALL"
- bucket_reason_short: "Tier B boost: BULL_PROXY × Bear (87.5% WR, n=16)"
- evidence.boost_match: win_007 (matched_on: "signal+regime")
- display.card_color_hint: "yellow"
- display.card_priority: 80
- display.telegram_emoji: "🟡"
- learner_hooks.confidence_band: "medium"

### 6.3 WATCH (no boost, decent cohort)

Example: ICICIBANK UP_TRI Bear regime Bank sector. Score 8.

Bridge sees:
- kill check: no
- validity: pass (R:R=1.65)
- boost check: no (Bank not in any active boost)
- evidence consensus check: cohort PROMISING (n=12, WR 75%)
- DECISION: WATCH

Key SDR fields:
- bucket: "WATCH"
- bucket_reason_short: "Score 8, no boost, cohort WR 75% n=12"
- bucket_reason_long: "...cohort UP_TRI×Bank×Bear historical n=12, WR 75%, avg P&L +1.8% — promising but below Tier B threshold (n≥15). Worth observing whether next 3 resolutions push it into Tier B territory."
- evidence.exact_cohort: {n: 12, wr: 0.75, ...}
- display.card_color_hint: "neutral"
- display.card_priority: 50
- display.telegram_emoji: "👁"
- learner_hooks.confidence_band: "medium"
- learner_hooks.uncertainty_dimensions: ["cohort_under_tier_b_threshold"]

### 6.4 SKIP (kill match)

Example: HDFCBANK DOWN_TRI Bear regime Bank sector. Score 7.

Bridge sees:
- kill check: HIT — DOWN_TRI×Bank matches kill_001
- DECISION: SKIP (Gate 1 fires)
- SIDE EFFECT: contra_tracker writes shadow (in mini_scanner, before bridge runs)

Key SDR fields:
- bucket: "SKIP"
- bucket_reason_short: "Killed by kill_001 (DOWN_TRI × Bank, 0/11 WR)"
- evidence.kill_match: kill_001
- counter_evidence.cluster_warnings: [{type: "apr_2026_squeeze", ...}]
- gap_caveat.applies: false
- display.card_color_hint: "red"
- display.card_priority: 10
- display.telegram_emoji: "❌"
- learner_hooks.confidence_band: "high"

### 6.5 Sorting + display

PWA + Telegram both sort by `display.card_priority` descending, then by score descending, then alphabetically by symbol.

A typical day:
✅ TATAMOTORS UP_TRI       priority 95   (TAKE_FULL)
✅ INFY UP_TRI             priority 95   (TAKE_FULL — IT sector boost)
🟡 HUDCO BULL_PROXY        priority 80   (TAKE_SMALL — Tier B)
👁 ICICIBANK UP_TRI        priority 50   (WATCH — Bank)
👁 SBIN UP_TRI             priority 50   (WATCH — Bank)
❌ HDFCBANK DOWN_TRI       priority 10   (SKIP — kill_001)
SKIPs are shown in the PWA, not hidden. Visibility builds trust and aids debugging. Empty SKIP-bucket day looks the same as no-data day; informative either way.

---

## 7. Contra-tracker integration and lifecycle

Contra is research that earns its way into action. Tracks itself. Displays itself. Alerts when ready for review. Never auto-trades. Promotion requires explicit Telegram approval.

### 7.1 Lifecycle states
TRACKING         → accumulating shadows, n<30 OR WR<80%
READY_FOR_REVIEW → n ≥ 30 AND WR ≥ 80%, awaiting approval
APPROVED         → rule promoted; signals appear in main Signals tab
INSUFFICIENT     → n ≥ 30 AND WR < 80%; kill rule confirmed correct, archived
State transitions:
- TRACKING → READY_FOR_REVIEW: automatic on data threshold cross
- READY_FOR_REVIEW → APPROVED: requires /approve_query Q-XXX in Telegram
- READY_FOR_REVIEW → INSUFFICIENT: 2 rejections, status archives
- APPROVED → TRACKING: automatic on WR collapse (10-window WR < 65%)

### 7.2 Thresholds (locked in `rules/thresholds.py`)

```python
CONTRA_REVIEW_N = 30                      # Sample size for review eligibility
CONTRA_REVIEW_WR = 0.80                   # WR threshold for promotion
CONTRA_PROMOTION_TAKE_SMALL_DAYS = 30     # First 30 days post-approval = TAKE_SMALL only
CONTRA_PROMOTION_TAKE_FULL_WR = 0.75      # Steady-state WR to graduate to TAKE_FULL
CONTRA_REVERT_WINDOW = 10                 # Rolling window size for revert check
CONTRA_REVERT_WR = 0.65                   # WR below this in window → auto-revert
CONTRA_PROPOSAL_AUTO_EXPIRE_DAYS = 7      # Re-propose after this if not acted on
CONTRA_REJECT_LIMIT = 2                   # 2 rejections → INSUFFICIENT
```

### 7.3 The contra block in bridge_state.json

```json
{
  "contra": {
    "schema_version": 1,
    "computed_at": "2026-04-29T03:00:00Z",
    "active_rules": [
      {
        "rule_id": "kill_001",
        "rule_descriptor": "DOWN_TRI × Bank",
        "rule_active_since": "2026-04-19",
        "status": "TRACKING",
        "n_total": 18,
        "n_resolved": 14,
        "n_pending": 4,
        "wr_resolved": 0.643,
        "avg_pnl_resolved": 2.4,
        "review_threshold_n": 30,
        "review_threshold_wr": 0.80,
        "progress_to_review_pct": 60,
        "ready_for_review": false,
        "promoted": false,
        "promoted_at": null,
        "promotion_proposal_id": null
      }
    ],
    "pending_shadows": [
      {
        "shadow_id": "contra_2026-04-29-ICICIBANK-DOWN_TRI",
        "rule_id": "kill_001",
        "symbol": "ICICIBANK",
        "signal_date": "2026-04-29",
        "day_count": 1,
        "inverted_entry": 843.20,
        "inverted_stop": 827.00,
        "inverted_target": 870.30,
        "rr": 1.5,
        "sector": "Bank",
        "regime": "Bear",
        "status_text": "tracking — Day 1 of 6"
      }
    ],
    "recent_resolutions": [
      {
        "shadow_id": "contra_2026-04-22-AXISBANK-DOWN_TRI",
        "rule_id": "kill_001",
        "symbol": "AXISBANK",
        "outcome": "WON",
        "outcome_date": "2026-04-28",
        "pnl_pct": 3.1,
        "mfe_pct": 4.2,
        "mae_pct": 0.8,
        "duration_days": 4
      }
    ],
    "alerts_this_cycle": []
  }
}
```

### 7.4 Promotion flow (Wave 4)

When TRACKING → READY_FOR_REVIEW:
1. Bridge writes new state to bridge_state.json
2. Bridge writes proposal to query_proposals.json
3. Bridge adds alert to bridge_state.contra.alerts_this_cycle
4. Telegram pre-market includes readiness alert with `/approve_query Q-007` instruction
5. PWA Contra tab shows [Review & Approve] button on rule card

When user runs `/approve_query Q-007`:
1. telegram_bot validates proposal
2. Updates mini_scanner_rules.json: adds `invert_to_long: true` + `promoted_at` to kill_pattern
3. Updates query_proposals.json: status=approved, approver+timestamp recorded
4. Sends confirmation: "✅ kill_001 promoted. Inverted LONGs surface as TAKE_SMALL starting tomorrow."

When user runs `/reject_query Q-007`:
1. Updates query_proposals.json: status=rejected, reason recorded
2. Reject counter incremented
3. After 2 rejections: status flips to INSUFFICIENT (no more re-propose)
4. Auto-expire: if no action within 7 days, proposal expires; bridge re-proposes if conditions still warrant

### 7.5 Post-promotion behavior

Next morning after approval, mini_scanner.py:
1. Sees DOWN_TRI Bank signal, matches kill_001
2. Because invert_to_long=true:
   - Still blocks original DOWN_TRI from signal_history.json
   - Writes inverted signal to signal_history.json: signal_type="UP_TRI_CONTRA", origin="contra_kill_001"
3. Continues writing to contra_shadow.json for ongoing track-record

Bridge L1 next morning:
1. Reads new UP_TRI_CONTRA signal in signal_history
2. Treats it like normal signal in bucket assignment
3. Special-case rule: any signal with origin="contra_kill_001" promoted within 30 days → forced TAKE_SMALL
4. After 30 days with WR ≥ 75% → eligible for normal bucket logic
5. PWA Signals tab shows it; [why?] card explains contra origin

### 7.6 Auto-revert on collapse

After promotion, if any 10-signal rolling window WR < 65%:
1. Bridge composer detects in EOD compose
2. Auto-removes invert_to_long flag from kill_pattern
3. Sets promoted: false in bridge_state
4. Status → TRACKING
5. Telegram alert: "⚠️ kill_001 contra reverted to shadow. WR collapsed to 58%. Kill rule still active. Re-tracking from current n=42."
6. Existing open positions NOT closed; run natural course

This is the only auto-action without approval. Principle: human approval required to escalate; not required to de-escalate. Safety bias.

### 7.7 PWA Contra tab structure

5th tab in bottom nav, labeled `🔄 Contra`. Three sections:

**Section A — Health card (top)**
- Title: "kill_001 — DOWN_TRI × Bank"
- Status badge: TRACKING (gray) / READY_FOR_REVIEW (yellow) / APPROVED (green) / INSUFFICIENT (red)
- Progress bar: n_resolved / 30 filled
- WR display: "64.3% WR (need ≥80% to promote)"
- For READY_FOR_REVIEW: [Review & Approve] button deep-links to Telegram

**Section B — Pending shadows**
- Header: "Open contra shadows (4)"
- Card per shadow: symbol, sector, day count, inverted entry/stop/target, status
- Empty state: "No pending shadows. Kill rule has not blocked any signals in the active 6-day window."

**Section C — Resolution log**
- Header: "Recent resolutions (last 10)"
- Card per resolution: symbol, outcome (W/S/F color-coded), P&L, MFE/MAE, date
- Pull to load more (up to 50). Beyond 50: stats-only view.

### 7.8 Telegram contra integration

**Pre-market footer (conditional on alerts_this_cycle):**
- At n=20: "📊 Contra-tracker: kill_001 at 18/30. WR 64%."
- At READY_FOR_REVIEW: "🚦 Contra-tracker READY: kill_001 n=30, WR 87%. /approve_query Q-007 to promote."
- At INSUFFICIENT: "📕 Contra-tracker INSUFFICIENT: kill_001 n=30, WR 52%. Kill rule confirmed correct."

**EOD digest paragraph (conditional on resolutions today):**
- "🔄 Contra resolutions: 2 today. 1 W (+2.4% AXISBANK), 1 STOPPED (-3.1% HDFCBANK). kill_001 running n=16, WR 62%."

### 7.9 Wave assignment

| Wave | Contra scope |
|------|--------------|
| Wave 2 | PWA tab, bridge writes contra block, conditional Telegram footer/paragraph. Read-and-render only. |
| Wave 3 | UP_TRI_CONTRA signal type recognition. Auto-revert detection. |
| Wave 4 | query_proposals.json full schema. /approve_query, /reject_query handlers. PWA approval card with deep-link. End-to-end promotion. |
| Wave 5 | Contra eligibility for broader self-query framework. |

---

## 8. The bridge folder structure
scanner/
├── bridge/
│   ├── init.py
│   ├── bridge.py                           # Orchestrator
│   │
│   ├── core/                               # Engine — fixed file count
│   │   ├── init.py
│   │   ├── sdr.py                          # SDR class + serialization
│   │   ├── bucket_engine.py                # Decision tree
│   │   ├── evidence_collector.py           # Evidence assembly into SDR
│   │   ├── display_hints.py                # Priority/color/emoji rules
│   │   ├── state_writer.py                 # Atomic writes
│   │   ├── upstream_health.py              # Reads system_health.json
│   │   └── error_handler.py                # Graceful degradation
│   │
│   ├── composers/                          # Three phase entry points
│   │   ├── init.py
│   │   ├── premarket.py                    # L1
│   │   ├── postopen.py                     # L2
│   │   └── eod.py                          # L4
│   │
│   ├── queries/                            # Plugin folder — grows
│   │   ├── init.py
│   │   ├── _registry.py                    # Auto-discovery
│   │   ├── q_signal_today.py
│   │   ├── q_pattern_match.py
│   │   ├── q_boost_match.py
│   │   ├── q_kill_match.py
│   │   ├── q_exact_cohort.py               # Background query 1
│   │   ├── q_sector_recent_30d.py          # Background query 2
│   │   ├── q_regime_baseline.py            # Background query 3
│   │   ├── q_score_bucket.py               # Background query 4
│   │   ├── q_stock_recency.py              # Background query 5
│   │   ├── q_anti_pattern.py               # Background query 6
│   │   ├── q_cluster_check.py              # Background query 7
│   │   ├── q_open_positions.py
│   │   ├── q_contra_status.py
│   │   ├── q_proposals_pending.py
│   │   ├── q_gap_evaluation.py             # Wave 3
│   │   └── q_outcome_today.py              # Wave 3
│   │
│   ├── rules/                              # Pure functions — fixed
│   │   ├── init.py
│   │   ├── thresholds.py                   # Magic numbers
│   │   ├── boost_matcher.py
│   │   ├── kill_matcher.py
│   │   └── validity_checker.py
│   │
│   ├── templates/                          # Telegram rendering
│   │   ├── init.py
│   │   ├── _base.py                        # Markdown helpers
│   │   ├── premarket.py
│   │   ├── postopen.py
│   │   └── eod.py
│   │
│   ├── alerts/                             # Plugin folder — grows
│   │   ├── init.py
│   │   ├── _registry.py
│   │   ├── _base.py
│   │   ├── chain_health.py                 # Wave 2
│   │   ├── contra_threshold.py             # Wave 2
│   │   └── gap_breach.py                   # Wave 3
│   │
│   └── learner/                            # Wave 5 fills
│       ├── init.py
│       └── _registry.py                    # Empty in Wave 2
│
└── ... (existing modules untouched)
### 8.1 Naming conventions

- Query files: `q_<topic>.py`
- Alert files: `<topic>.py`
- Learner files: `<gap_or_signal>_<topic>.py`
- Rule files: `<topic>_<verb>.py`
- Templates: phase name `premarket.py`/`postopen.py`/`eod.py`
- Internal-only: prefix with underscore `_registry.py`, `_base.py`

Lowercase, underscore-separated, descriptive. No camelCase.

### 8.2 Why this layout

**Plugin folders (queries/, alerts/, learner/) for things that grow.**
Adding capability = new file. No engine touch.

**Subfolders (core/, composers/, rules/, templates/) for things that don't grow.**
Fixed file count by architecture. Plain filenames.

**Strict input/output isolation.**
- queries/ reads files, returns data
- rules/ pure functions, no I/O
- core/ orchestrates
- composers/ are entry points
- templates/ read-only on state
- alerts/ + learner/ read state, return derived structures
- ONLY state_writer.py writes to disk (single chokepoint)

---

## 9. Background queries — the analytical depth layer

Bridge runs 7 background queries on every compose, embedding analytical depth in every SDR. This is what makes bridge evolve from day one rather than waiting for Wave 5.

### 9.1 The 7 queries

| Query | Returns | Purpose |
|-------|---------|---------|
| q_exact_cohort | n, WR, avg_pnl, MFE, MAE for (signal × sector × regime × age) | Specific cohort historical performance |
| q_sector_recent_30d | n, WR, avg_pnl, trend for sector last 30 days | Sector momentum |
| q_regime_baseline | n, WR, avg_pnl for regime all-time | Regime expectation |
| q_score_bucket | n, WR for this score level in this regime | Score-bucket performance |
| q_stock_recency | last_signal_date, last_outcome, lookback_30d_count, lookback_30d_wr | Stock-specific recency |
| q_anti_pattern | Patterns opposing this signal type/sector/regime | Counter-evidence |
| q_cluster_check | Date-cluster warnings (Apr 6-8 type events) | Event window flags |

### 9.2 Query implementation pattern

Each query plugin is a single file with the same shape:

```python
# Example: q_exact_cohort.py
QUERY_NAME = "q_exact_cohort"
QUERY_DESCRIPTION = "Returns historical cohort for exact signal+sector+regime+age match"
INPUT_FILES = ["signal_history.json"]

def run(signal, history_data):
    """
    Args:
        signal: dict, the signal to query for
        history_data: dict, signal_history.json content (loaded once by composer)
    Returns:
        dict with n, wr, avg_pnl, avg_mfe, avg_mae, tier_status
    """
    matches = []
    for record in history_data['history']:
        if record.get('result') in ('PENDING', 'REJECTED'):
            continue
        if (record['signal'] == signal['signal_type']
            and record['sector'] == signal['sector']
            and record['regime'] == signal['regime']
            and record['age_days'] == signal['age_days']):
            matches.append(record)
    
    if not matches:
        return {"n": 0, "wr": None, "avg_pnl": None, "tier_status": "no_data"}
    
    # ... compute statistics ...
    return result
```

### 9.3 Performance design

7 queries × 5-15 signals = 35-105 query runs per compose. Performance constraint: each query ≤ 100ms.

**Pattern:** evidence_collector.py loads truth files ONCE per compose, passes pre-loaded dicts to all queries. Queries use dict iteration only — no repeated file reads, no SQL, no external dependencies.

Estimated total compose time: 5-10 seconds. Well within the 25-minute window between morning_scan and market open.

### 9.4 Query results in SDR

All 7 query results land in `evidence` block:
- exact_cohort
- sector_recent_30d
- regime_baseline
- score_bucket
- stock_recency
- anti_pattern_check
- cluster_warnings

These feed both Gate 4 of bucket_engine (decision logic) and PWA [why?] card rendering (Wave 4).

---

## 10. bridge_state.json schema

Top-level structure:

```json
{
  "schema_version": 1,
  "phase": "PRE_MARKET" | "POST_OPEN" | "EOD",
  "phase_status": "OK" | "DEGRADED" | "ERROR",
  "phase_timestamp": "2026-04-29T03:00:00Z",
  "market_date": "2026-04-29",
  
  "banner": {
    "state": "PROVISIONAL" | "LIVE" | "DAY_COMPLETE" | "DEGRADED" | "ERROR",
    "color": "yellow" | "green" | "gray" | "orange" | "red",
    "message": "PROVISIONAL — validates at 09:30",
    "subtext": "Read brief. Place orders at 09:15 open."
  },
  
  "summary": {
    "total_signals_today": 6,
    "buckets": {
      "TAKE_FULL": 1,
      "TAKE_SMALL": 1,
      "WATCH": 2,
      "SKIP": 2
    },
    "open_positions_total": 11,
    "stop_alerts_open": 0,
    "exit_today_count": 1
  },
  
  "signals": [
    /* Array of SDRs, sorted by display.card_priority desc */
  ],
  
  "open_positions": [
    /* Active trades from prior days, abbreviated SDR-like records */
  ],
  
  "contra": {
    /* Contra block — see §7.3 */
  },
  
  "alerts": [
    /* Action items: stop hits, day-6 exits, contra readiness, chain health */
  ],
  
  "self_queries": [
    /* Empty in Wave 2; populated in Wave 5 */
  ],
  
  "upstream_health": {
    "morning_scan": "ok",
    "open_validate": "not_yet_run",
    "eod_update": "ok_yesterday",
    "outcome_eval": "ok",
    "pattern_miner": "ok",
    "rule_proposer": "ok",
    "contra_tracker": "ok"
  },
  
  "audit": {
    "bridge_version": "1.0.0",
    "compose_started_at": "2026-04-29T03:00:00Z",
    "compose_completed_at": "2026-04-29T03:00:47Z",
    "queries_total": 18,
    "queries_failed": 0,
    "files_read": ["signal_history.json", "patterns.json", ...],
    "warnings": []
  }
}
```

### 10.1 History retention

`bridge_state_history/<date>_<phase>.json` files retain 30 days. Older files archived to `backups/bridge_history/` weekly. Logic in state_writer.py.

### 10.2 Schema evolution

- Adding fields = no version bump (forward-compatible)
- Removing/renaming fields = schema_version bump (rare)
- Changing field meaning = schema_version bump (rare)

PWA reader checks schema_version; if newer than expected, shows "Bridge state newer than this app — refresh PWA". If older, errors politely.

---

## 11. PWA integration

### 11.1 Wave 2 PWA changes

| File | Change | Why |
|------|--------|-----|
| `output/app.js` | Modify Signals tab to read bridge_state.json (with fallback to signal_history.json) | Bridge becomes data source |
| `output/contra.js` (NEW) | Three sections: Health/Pending/Resolutions | Contra tab |
| `output/ui.js` | Add Contra to bottom nav, render phase banner | Tab routing + banner |
| `output/sw.js` | Bump cache version, add contra.js to precache | Force PWA refresh |
| `scanner/html_builder.py` | Add Contra tab nav, contra.js script tag, banner area | HTML shell rebuild |

### 11.2 Signal card rendering

PWA renders SDRs grouped by bucket, sorted by priority within bucket:
─────────────────────────
PROVISIONAL — validates at 09:30   [yellow banner]
─────────────────────────
✅ TAKE FULL (1)
TATAMOTORS • UP_TRI
Auto • Bear • Score 9 • Tier A
Entry: ₹982 • Stop: ₹962 • Target: ₹1024
R:R 2.10
Tier A boost: UP_TRI × Auto × Bear (21/21 WR)
⚠ Place at 09:15. If gap > 2% (₹1002), reconsider.
🟡 TAKE SMALL (1)
HUDCO • BULL_PROXY
...
👁 WATCH (2)
ICICIBANK • UP_TRI
Bank • Bear • Score 8 • watching
...
❌ SKIP (2)
HDFCBANK • DOWN_TRI
Bank • Bear • Score 7 • blocked
Killed by kill_001 (DOWN_TRI × Bank, 0/11 WR)
...
### 11.3 Wave 3 PWA evolution

Apply Session 4 visual design:
- Fraunces serif for headings
- Geist sans for body
- Geist Mono for numbers
- 3-column iPad landscape layout
- Time-aware modes (Brief/Market/Review) wired to `bridge_state.phase`

Same content, restyled. Functional layer (Wave 2) and visual layer (Wave 3) separate concerns.

### 11.4 Wave 4 PWA evolution

- Tap any signal card → expand [why?] showing full evidence chain
- Tap proposal in Contra tab → deep-link to Telegram with `/approve_query Q-XXX` pre-filled
- Render counter_evidence + colab_insight_excerpt fields

### 11.5 Wave 5 PWA evolution

- Self-query disclosure cards
- Show learner_hooks.gap_flags as small badges

---

## 12. Telegram template structure

### 12.1 Pre-market brief (Wave 2)
🎯 Pre-market — 2026-04-29
PROVISIONAL — validates at 09:30
✅ TAKE FULL (1)
TATAMOTORS · UP_TRI
Auto · Bear · Score 9 · Tier A
Entry: ₹982 · Stop: ₹962 · Target: ₹1024
R:R 2.10 · 21/21 WR
⚠ Gap > 2% (₹1002) reconsider
🟡 TAKE SMALL (1)
HUDCO · BULL_PROXY
Infra · Bear · Score 7 · Tier B
...
👁 WATCH (2)
...
❌ SKIP (2)
...
─────────────
📊 Contra-tracker: kill_001 at 18/30. WR 64%.
─────────────

### 12.2 Post-open alert (Wave 3, conditional)

Only fires when gap_breach OR bucket_change occurred:
⚠️ Post-open alert — 2026-04-29
ICICIBANK gapped 4.2% above scan_price.
L1 was WATCH. L2 reclassifies to SKIP.
If you entered: consider position management.

### 12.3 EOD digest (Wave 3)
📊 EOD — 2026-04-29
Today's signals resolved:
✅ TATAMOTORS WON +5.2% (entry-to-target)
✅ INFY WON +3.1%
🟡 HUDCO STOPPED -2.4%
Pattern updates:
🆕 UP_TRI × Auto × Bear: 22/22 (Tier A holding)
Proposals:
prop_011 drafted: BULL_PROXY × IT × Bear (n=11, edge +14pp)

Open positions: 11 (3 exit tomorrow)
🔄 Contra: 1 resolved. AXISBANK WON +3.1%. kill_001 n=15.
---

## 13. GitHub Actions wiring

### 13.1 Three new workflow files

**bridge_premarket.yml**
- Trigger: workflow_run on "Morning Scan" completed (success only)
- Concurrency: bridge-premarket, cancel-in-progress
- Action: `python scanner/bridge/bridge.py --phase=PRE_MARKET`
- Commits and pushes bridge_state.json

**bridge_postopen.yml**
- Trigger: workflow_run on "Open Validate" completed (success only)
- Same concurrency + action pattern, --phase=POST_OPEN

**bridge_eod.yml**
- Trigger: GitHub native schedule `45 10 * * 1-5` (UTC) = 16:15 IST Mon–Fri
         + workflow_dispatch as manual safety valve
- Concurrency: bridge-eod, cancel-in-progress: false
- Action: `python scanner/bridge/bridge.py --phase=EOD`
- Commits and pushes bridge_state.json
- See §13.4 for the rationale on the GitHub-schedule deviation

### 13.2 Existing workflow updates

**open_validate.yml:**
- Shift retry crons +5 min: 9:57/10:27 → 10:02/10:32
- Reason: yfinance settlement window for NSE data

**rebuild_html.yml:**
- Add `output/contra.js` to watched paths

**telegram_poll.yml:**
- Add concurrency group (TG-01 fix)

### 13.3 Workflow chain visualization
morning_scan.yml ──→ bridge_premarket.yml
│
└─→ writes bridge_state.json
sends Telegram
open_validate.yml ──→ bridge_postopen.yml
│
└─→ updates bridge_state.json
sends Telegram (conditional)
eod_master.yml ──→ bridge_eod.yml
│
└─→ updates bridge_state.json
sends Telegram digest
If upstream fails, downstream doesn't fire. chain_validator catches it next morning. No silent garbage.

### 13.4 EOD-workflow exception (added 2026-04-27, shipped commit `f9d4746`)

`bridge_eod.yml` deviates from the "workflow_dispatch only — no GitHub schedule" pattern that §13.1 documents and that `bridge_premarket.yml` + `bridge_postopen.yml` follow. EOD uses GitHub native `schedule:` (`45 10 * * 1-5` UTC = 16:15 IST Mon–Fri) plus `workflow_dispatch` as a manual safety valve.

**Why the deviation is acceptable for EOD specifically:**

1. **Drift-tolerant.** EOD is a digest, not entry-window-critical. Premarket and postopen are precision-critical (8:55 IST brief, 9:40 IST gap-evaluation alert) — they need cron-job.org's tight schedule fidelity. EOD's window is "after eod_master finishes ~15:40 IST + buffer." A 25–55 min effective buffer between eod_master start (15:35 IST) and the EOD digest fire window absorbs both eod_master runtime variability and GitHub Actions schedule drift. Under heavy GitHub load, drift can exceed nominal expectations; the buffer is sized for that reality.
2. **Reduces single-point-of-failure surface.** cron-job.org currently dispatches 14 precision-critical workflows (per `master_audit_2026-04-27.md` GAP-04). Adding eod.yml to that count would deepen the SPOF concentration. GitHub native schedule for the one bridge workflow that can tolerate drift moves it off the critical-cron list.
3. **No cron-job.org dashboard entry needed.** Reduces operational friction; one less manual entry to maintain.

**What this does NOT change:**

- Premarket and postopen stay on cron-job.org `workflow_dispatch`. Their precision requirements haven't changed.
- The architectural principle "workflow_dispatch only — no GitHub schedule" still applies to those two layers. EOD is the documented exception, not the new default.
- If a future precision-critical workflow ships, it should follow premarket/postopen's pattern, not eod's.

**Cross-references:**
- `bridge_eod.yml` docstring (the deviation note in the architecture v2 comment in the workflow file itself)
- `master_audit_2026-04-27.md` PART 4 (Workflow audit) GAP-04 (cron-job.org SPOF context)
- `wave5_prerequisites_2026-04-27.md` S-4 (cron-job.org failover playbook — separate, complementary item)

---

## 14. Error handling and graceful degradation

### 14.1 Failure modes and responses

| Failure | Response |
|---------|----------|
| One query plugin fails | Log to audit.queries_failed, continue with empty result, mark phase_status=DEGRADED |
| Multiple plugin failures | Same as above, additional warnings |
| Missing input file | error_handler reports specific file, sets phase_status=DEGRADED, populates upstream_health |
| Composer crashes | error_handler writes minimal bridge_state.json with phase_status=ERROR, sends Telegram error notification, exits 1 |
| state_writer fails | Logged to GitHub Actions output, exit 1 (no fallback — consider rollback to previous) |

### 14.2 Banner states reflect phase_status

- OK: normal phase banner
- DEGRADED: orange "⚠️ Bridge degraded — some evidence incomplete" banner
- ERROR: red "❌ Bridge failed — see Telegram for details" banner

### 14.3 Telegram error template
❌ Bridge failed at PRE_MARKET
Phase: 2026-04-29T03:00:00Z
Error: <type>: <message>
Last good state: <timestamp>
Check Actions logs: <link>
### 14.4 chain_validator integration

Bridge reads system_health.json (M-05 expanded coverage) and surfaces:
- Per-step health in upstream_health
- ERROR statuses in alerts
- Composer's queries_executed reflects what was actually run
- queries_failed tracks per-plugin failures

### 14.5 Non-trading day handling

bridge.py first checks calendar_utils.is_trading_day(). If non-trading:
- Exits cleanly without compose
- Logs to system_health.json: "non-trading day, bridge skipped"
- No state file update

---

## 15. Wave plan and file inventory

### 15.1 Wave 2 — Bridge Skeleton + Functional UI

**Goal:** Monday 09:00 you receive unified pre-market brief. Signals sorted by bucket. PWA Signals tab + new Contra tab. Existing visual style. Telegram delivery reliable.

**Effort:** 16 hours, 2 sessions on MacBook.

**Pre-Wave 2:**
- 0.1 — bridge_design_v1.md (this document) — committed before Wave 2 work begins

**Sidecar fixes (do FIRST, single-file edits):**
- 1.1 — TG-01 concurrency: `.github/workflows/telegram_poll.yml`
- 1.2 — TG-01 try/except: `scanner/telegram_bot.py`
- 1.3 — open_validator timing: `.github/workflows/open_validate.yml`

**Bridge folder + core:**
- 2.1 — Folder structure: `scanner/bridge/__init__.py` + 7 subfolder __init__.py
- 2.2 — `scanner/bridge/rules/thresholds.py`
- 2.3 — `scanner/bridge/core/sdr.py`
- 2.4 — `scanner/bridge/core/display_hints.py`
- 2.5 — `scanner/bridge/core/state_writer.py`
- 2.6 — `scanner/bridge/core/upstream_health.py`
- 2.7 — `scanner/bridge/core/error_handler.py`
- 2.8 — `scanner/bridge/rules/boost_matcher.py`
- 2.9 — `scanner/bridge/rules/kill_matcher.py`
- 2.10 — `scanner/bridge/rules/validity_checker.py`
- 2.11 — `scanner/bridge/core/bucket_engine.py`
- 2.12 — `scanner/bridge/core/evidence_collector.py`

**Query plugins:**
- 3.1 — `scanner/bridge/queries/_registry.py`
- 3.2-3.17 — All query plugins (16 files)

**Composers:**
- 4.1 — `scanner/bridge/composers/premarket.py` (full)
- 4.2 — `scanner/bridge/composers/postopen.py` (stub)
- 4.3 — `scanner/bridge/composers/eod.py` (stub)

**Templates:**
- 5.1 — `scanner/bridge/templates/_base.py`
- 5.2 — `scanner/bridge/templates/premarket.py` (full)
- 5.3 — `scanner/bridge/templates/postopen.py` (stub)
- 5.4 — `scanner/bridge/templates/eod.py` (stub)

**Alerts:**
- 6.1 — `scanner/bridge/alerts/_registry.py` + `_base.py`
- 6.2 — `scanner/bridge/alerts/chain_health.py`
- 6.3 — `scanner/bridge/alerts/contra_threshold.py`

**Learner placeholder:**
- 7.1 — `scanner/bridge/learner/__init__.py` + `_registry.py`

**Orchestrator:**
- 8.1 — `scanner/bridge/bridge.py`

**GitHub Actions:**
- 9.1 — `.github/workflows/bridge_premarket.yml`
- 9.2 — `.github/workflows/bridge_postopen.yml`
- 9.3 — `.github/workflows/bridge_eod.yml`
- 9.4 — `.github/workflows/rebuild_html.yml` (update watched paths)

**PWA changes (each file edited ONCE):**
- 10.1 — `scanner/html_builder.py`
- 10.2 — `output/app.js`
- 10.3 — `output/contra.js` (NEW)
- 10.4 — `output/ui.js`
- 10.5 — `output/sw.js`

**Closing:**
- 11.1 — `doc/session_context.md` update
- 11.2 — `doc/fix_table.md` update

### 15.2 Wave 3 — Full 3-layer rhythm + Session 4 visual design

**Goal:** All three bridge phases live. Session 4 visual design applied.

**Effort:** 12 hours.

- q_gap_evaluation.py (full), q_outcome_today.py (full)
- postopen.py composer (full), eod.py composer (full)
- postopen.py template (full), eod.py template (full)
- gap_breach.py alert
- regime_watch.py alert (DATA-02 Choppy watch)
- Session 4 fonts (index.html via html_builder)
- styles.css (NEW)
- 3-column iPad layout (ui.js + app.js + journal.js + stats.js + contra.js — single edit each)
- Time-aware modes (ui.js)
- Mark UX-02/03/05 SUPERSEDED in fix_table.md
- session_context.md + fix_table.md update

### 15.3 Wave 4 — Proposals + Approvals + Contra Promotion

**Goal:** Tap [why?] expansion. Proposal approval cards. Contra promotion end-to-end.

**Effort:** 7 hours.

- query_proposals.json schema doc
- UP_TRI_CONTRA signal type (scanner_core + scorer)
- Bridge surfaces UP_TRI_CONTRA (bucket_engine)
- Contra promotion handler (telegram_bot — /approve_query)
- mini_scanner.py invert_to_long flag
- q_proposals_active.py
- PWA expandable cards + approvals + deep-links (app.js + contra.js — single edit each)
- Auto-revert on collapse (eod.py composer)
- session_context.md + fix_table.md update

### 15.4 Wave 5 — Self-queries + Learner

**Goal:** Bridge auto-detects gaps, proposes investigations.

**Effort:** 7 hours.

- Query template registry (learner/_templates.py)
- Cohort thin detector
- Recurring failure detector
- Promotion eligibility detector
- query_proposals.json writer
- /reject_query, /promote_query handlers
- Self-query disclosure card (contra.js + app.js — single edit each)
- [why?] shows self-queries
- session_context.md + fix_table.md update

### 15.5 Wave 6 — Polish + Parallel

- CACHE-02 (analysis.html via html_builder)
- PIN-01 (PWA PIN injection)
- AN-04 (score × signal cross-tab)
- HL-01 (auto-healer framework)
- MC-01 (master check framework)

### 15.6 Wave 7+ — Conditional

- H-04/D3 (kill_001 scope) — gates on Apr 27-29 Choppy resolutions
- H-06 (sector taxonomy) — needs evidence review
- H-07 (price_feed full migration) — when 5paisa swap planned
- prop_005 (stop/target rebalance) — after Wave 4
- prop_007 (demotion framework) — after Wave 4
- OPS-01..04 (repo split) — separate decision

---

## 16. Out-of-scope and deferred decisions

### 16.1 Explicitly out of scope for bridge

- **Database integration.** No SQL, no Postgres, no SQLite (browser-only via sql.js stays).
- **Caching layer.** Compose reads disk every time. ~10 sec per compose acceptable.
- **Async/await.** Synchronous throughout. Easier to debug.
- **Class hierarchies for SDR variants.** Plain dicts. Data, not behavior.
- **Mid-day on-demand recompose.** Wave 5+ consideration.
- **Real-time data via 5paisa.** H-07 plug-in adapter, separate project.

### 16.2 Decisions deferred to later waves

- counter_evidence rendering: Wave 4
- Self-queries: Wave 5
- Auto-revert demotion ramps: Wave 4 (paired with prop_007/LE-06)
- Score recalibration: Wave 7+ (after AN-04 + Wave 5 self-queries)

### 16.3 Decisions explicitly NOT made

- Whether to add a 4th phase trigger (e.g., 11am intraday): defer based on Wave 2-3 usage data
- Whether to integrate news/sentiment data: future module, not bridge concern
- Whether to support multi-portfolio: out of scope, single portfolio assumption baked in

---

## 17. Open questions for future decisions

These don't block Wave 2 but should be answered before later waves:

- After Wave 2 ships, observe for 2 weeks: does the bucket distribution match expectation? If 80% of signals land in WATCH/SKIP, may need to rethink Gate 4 thresholds.
- After Wave 4 ships: does the promotion review process work in practice? If user repeatedly rejects with same reason, that's signal to refine the underlying matching logic.
- After Wave 5 ships: are self-queries useful? If proposed queries are routinely rejected as "I don't care," tighten gap detection thresholds.
- Long-term: when bridge_state.json grows large (~50+ SDRs/day, history of months), does PWA load time degrade? Monitor and consider pagination if so.
- Long-term: when contra-tracker accumulates many promoted rules, does the PWA Contra tab need restructuring? Plan for stack-of-rules display.

---

## 18. Document maintenance

This is a living document. After each wave ships:
1. Mark wave's items as SHIPPED in §15
2. Update §17 with newly answered questions
3. Add deferred items to §16 if needed
4. Bump version (next: bridge_design_v1.1.md if substantial revision)

Document author: Claude (with Abhishek's design decisions). Maintained jointly through chat sessions.

---

## 19. Appendix — Quick reference

### 19.1 File ownership map

| File | Owner | Bridge access |
|------|-------|---------------|
| signal_history.json | journal.py | READ |
| meta.json | meta_writer.py | READ |
| mini_scanner_rules.json | mini_scanner.py + telegram_bot.py | READ |
| patterns.json | pattern_miner.py | READ |
| proposed_rules.json | rule_proposer.py | READ |
| contra_shadow.json | contra_tracker.py + outcome_evaluator.py | READ |
| colab_insights.json | auto_analyst.py | READ |
| system_health.json | chain_validator.py | READ |
| open_prices.json | open_validator.py | READ |
| eod_prices.json | eod_prices_writer.py | READ |
| ltp_prices.json | ltp_writer.py | READ |
| stop_alerts.json | stop_alert_writer.py | READ |
| **bridge_state.json** | **bridge** | **WRITE** |
| **bridge_state_history/** | **bridge** | **WRITE** |
| **query_proposals.json** | **bridge** (Wave 4-5) | **WRITE** |

### 19.2 Glossary

- **SDR** — Signal Decision Record. The atomic unit of bridge output.
- **Bucket** — TAKE_FULL / TAKE_SMALL / WATCH / SKIP classification.
- **Gate** — A decision point in the bucket assignment tree.
- **Boost match** — Signal matches an active boost_pattern in mini_scanner_rules.
- **Kill match** — Signal matches an active kill_pattern.
- **Contra shadow** — Inverted research record for a kill_pattern match.
- **Background query** — One of 7 cohort/segmentation queries run on every compose.
- **Evidence chain** — Combined output of all queries embedded in SDR.evidence.
- **Decision Surface** — The unified Compose/Present/Learn system.
- **Proof-Gated Approval** — Pattern of: claim + evidence + counter-evidence + reversibility before accepting structural change.

### 19.3 Key timings

| Time (IST) | Event |
|------------|-------|
| 08:35 | morning_scan cron |
| 08:50 | morning_scan complete |
| 08:55 | bridge_premarket fires |
| 09:00 | bridge_state.json L1 written |
| 09:05 | Telegram L1 brief lands |
| 09:15 | Market opens |
| 09:32 | open_validator cron |
| 09:40 | bridge_postopen fires |
| 09:45 | bridge_state.json L2 written |
| 09:47 | Telegram L2 alert (conditional) |
| 15:30 | Market closes |
| 15:35 | eod_master cron |
| 15:55 | EOD chain complete |
| 16:00 | bridge_eod fires |
| 16:05 | bridge_state.json L4 written |
| 16:08 | Telegram L4 digest |
| 23:00 | auto_analyst (conditional) |

---

**End of bridge_design_v1.md**

**Next: Implementation begins with Wave 2, sidecar fixes first.**
