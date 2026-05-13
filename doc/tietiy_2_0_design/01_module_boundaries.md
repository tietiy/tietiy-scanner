# 01 — Module Boundaries (TIE TIY 2.0)

## What changed from my prior feasibility analysis

I was wrong about the brain layer. **Brain has been firing nightly in production from 2026-04-28 through 2026-05-12.** 9 days of history files prove it. Last night (2026-05-12 22:00 IST) generated 3 PENDING proposals — identical to those from 2026-04-29, because **the user has approved zero, rejected zero, allowed all to silently regenerate.**

This is a different problem than I diagnosed. The infrastructure operates. The **approval-loop closure** (UI + user-decision discipline) is the gap, not the brain itself.

The architecture below preserves what works and concentrates 2.0 design on the two real pain points: **plug-in detectors** and **UI closure**.

## Module map

Three concentric rings:

```
              ┌─────────────────────────────────────────────┐
              │   UI / DELIVERY (PWA, Telegram bot)         │
              │   - dashboard cards (proposals, exposure)   │
              │   - approval handlers                       │
              └─────────────────────────────────────────────┘
                              ▲ reads ▼ commands
              ┌─────────────────────────────────────────────┐
              │   CORE (always-loaded; never optional)       │
              │   - scanner pipeline (universe → fetch →    │
              │     detect → score → journal)               │
              │   - brain (derive → verify → reason → out)  │
              │   - bridge (premarket/postopen/eod)         │
              │   - data layer (signal_history, regime,     │
              │     ohlcv, calendar)                        │
              │   - IPC (atomic JSON writes, schemas)       │
              └─────────────────────────────────────────────┘
                              ▲ registers ▼ invokes
              ┌─────────────────────────────────────────────┐
              │   PLUG-INS (registered; hot-pluggable)      │
              │   - SignalDetector × N (UP_TRI, BULL_PROXY, │
              │     VCP, EMA20 pullback, Darvas, …)         │
              │   - RegimeClassifier × M (3-state today,    │
              │     7-state next)                           │
              │   - ConfluenceGate × K (none today, V5      │
              │     next)                                   │
              │   - ProposalGenerator × P (cohort_promote,  │
              │     regime_alert, exposure_warn, …)         │
              │   - UICard × Q (proposal card, exposure     │
              │     card, regime card, …)                   │
              └─────────────────────────────────────────────┘
```

## Core modules (always-loaded)

| Module | Role | 1.0 source | Hours to refactor to 2.0 |
|---|---|---|---:|
| `core/universe` | Loads `data/fno_universe.csv` (188 stocks + sector tags) | `scanner/universe.py` | 1 |
| `core/calendar` | IST helpers, trading day, holidays | `scanner/calendar_utils.py` | 1 |
| `core/data_layer` | OHLCV fetch + cache (yfinance / 5paisa abstraction) | `scanner/price_feed.py` + `scanner/ltp_writer.py` | 6 |
| `core/journal` | Owns `signal_history.json`, atomic writes, dated backups | `scanner/journal.py` (35 KB) | 12 — schema cleanup |
| `core/orchestrator` | Daily pipeline orchestration. Loads plug-ins via registry. | `scanner/main.py` (38 KB) | 30 — re-derive from registry pattern |
| `core/brain` | 4-step pipeline: derive → verify → reason → output. Calls registered ProposalGenerators. | `scanner/brain/*.py` (8 modules) | 8 — adapter only |
| `core/bridge` | 3-phase composer: premarket / postopen / eod | `scanner/bridge/composers/*.py` | 12 — adapter only |
| `core/scorer` | Aggregates per-signal score (age, regime, quality bonuses). Plug-in detectors emit raw signal; scorer enriches. | `scanner/scorer.py` | 6 — generalize for non-Bear targets |
| `core/outcome_evaluator` | Walks open signals to terminal outcomes. | `scanner/outcome_evaluator.py` | 16 — generalize for zone exits + 10-day time exit |
| `core/registry` | Plug-in registration + discovery (decorator + entry-point pattern) | (new) | 8 |
| `core/ipc` | Schema-validated JSON readers/writers + state_writer atomic pattern | `scanner/bridge/core/state_writer.py` | 4 |

**Core total: ~104 hours of refactor (mostly carving the registry seam through `main.py`).**

## Plug-in modules (registered)

### SignalDetector (the heart of 2.0)

Existing detectors in 1.0:
- UP_TRI (port to plug-in: 3h)
- BULL_PROXY (port to plug-in: 1h)
- DOWN_TRI (deprecate; don't port)
- UP_TRI_SA / DOWN_TRI_SA (defer; complexity not justified by current data)

Future detectors (L99 Bull setups):
- VCP breakout (~16h)
- EMA20 pullback (~8h, lowest effort, highest fire rate)
- Bull flag (~12h)
- Darvas box (~14h)
- Cup-and-handle (~16h)

Plus from `shadow_ops_v1`:
- rule_019 Bear+UP_TRI+sub_regime=hot (port from `shadow_ops/`: 6h)

**Total SignalDetector porting + new builds: ~76 hours.**

### RegimeClassifier

Existing: 3-state slope/EMA50 in `scanner/main.py:get_nifty_info`.
Add: 7-state classifier per L99 (Stable-Bull / Inflecting-Bull→Bear / Stable-Bear / Inflecting-Bear→Bull / Stable-Choppy / Trending-Choppy / Volatile-Range).
Plug-in interface lets both coexist; the orchestrator picks one via config.

**Effort: 30 hours (build 7-state) + 4h (adapter for 3-state).**

### ConfluenceGate

None today. V5 confluence gate from L99 plugs in here.

**Effort: 50 hours (per prior feasibility §04).** Build as logged-only first 60 days.

### ProposalGenerator (sub-plugins inside brain)

Existing in `brain_reason.py`: cohort_promotion_judge, regime_shift_detector, exposure_correlation_analyzer (Wave 5 Step 5).

Add 2.0:
- `kill_proposal_generator` — proposes broader kill_patterns based on cohort_health (currently the deterministic `rule_proposer.py` does this but produces 31 stale proposals; LLM-gated would be cleaner)
- `threshold_tune_generator` — proposes parameter adjustments (e.g. min_score 7 → 6)
- `v5_threshold_tuner` — proposes V5 thresholds per regime via McNemar (post 60-day calibration window)

**Effort: 24 hours (3 new generators, each ~8h).**

### UICard

Each card type is a plug-in module that knows how to render itself from a specific JSON source.

- `ProposalCard` — renders `output/brain/unified_proposals.json` entries with Approve/Reject/Defer buttons. (8h)
- `ExposureCard` — renders `output/brain/portfolio_exposure.json` warnings. (4h)
- `RegimeCard` — renders `output/brain/regime_watch.json` + transition evidence. (4h)
- `CohortCard` — renders per-cohort tier breakdown from `cohort_health.json`. (6h)
- `SignalCard` — renders today's PENDING signals from `signal_history.json` + bridge_state. (8h)
- `OutcomeCard` — renders resolved trades + R-multiple history. (6h)
- `LedgerCard` — renders approved/rejected proposal history from `decisions_journal.json`. (4h)

**Effort: 40 hours (7 cards × ~6h average).**

## Adapter modules

Thin glue between core and plug-ins:

| Adapter | Purpose | Hours |
|---|---|---:|
| `SignalDetectorRegistry` | Discovers all SignalDetector plug-ins, calls them per bar, validates outputs | 4 |
| `RegimeAdapter` | Wraps any RegimeClassifier plug-in; provides single label downstream | 2 |
| `GateAdapter` | Wraps any ConfluenceGate plug-in; provides veto decision downstream | 2 |
| `ProposalAdapter` | Collects proposals from all generators, applies dedup, top-3 cap | 4 |
| `UIRegistry` | Loads UICard plug-ins, renders dashboard layout | 4 |

**Adapter total: ~16 hours.**

## UI components (delivery layer)

| Component | Role | Hours |
|---|---|---:|
| PWA shell | Layout, navigation, real-time refresh (5-min polling), service worker | 20 |
| API layer | Optional FastAPI sidecar OR pure-static read of `output/*.json` (recommended: pure static) | 0 (pure static) or 30 (FastAPI) |
| Telegram bot | Approval commands (`/approve {id}`, `/reject {id} [reason]`, `/explain {id}`) | 8 (extend existing) |
| Dashboard backend | (only if not pure-static): proposal queue, audit log | 30 |

**UI total: 28h (pure-static) or 88h (FastAPI sidecar).** Recommendation: pure-static for v1; FastAPI later if needed.

## Aggregate effort

| Layer | Hours |
|---|---:|
| Core refactor | 104 |
| Plug-in detectors (port + 5 new) | 76 |
| Plug-in regime / gate / proposals | 108 |
| Plug-in UI cards | 40 |
| Adapters | 16 |
| UI delivery (pure-static) | 28 |
| Validation harness integration | 20 (see §06) |
| Integration + smoke + docs | 40 |
| **Total** | **~432 hours** |

At 30 productive hours/week: **~14 weeks realistic** (optimistic 11, pessimistic 20).

## What this is NOT

This module map deliberately does **not**:
- Replace `signal_history.json` with a new database. It's the persistent truth; preserve.
- Replace the existing Telegram bot. Extend.
- Add a backend server. Pure-static dashboard for v1.
- Reimplement the brain layer. Adapter only; preserve verbatim.
- Reimplement the bridge composers. Adapter only.

The point of 2.0 is the **registry seam** that lets new SignalDetectors / RegimeClassifiers / UICards plug in cleanly. Everything else is preserved with adapters.
