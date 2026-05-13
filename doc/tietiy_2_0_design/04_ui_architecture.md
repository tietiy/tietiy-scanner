# 04 — UI Architecture (TIE TIY 2.0)

The 1.0 UI is the system's weakest link. The brain has been generating actionable proposals nightly since 2026-04-28 (9+ days as of 2026-05-12). The current PWA (`output/index.html`, `output/analysis.html`) doesn't surface them. **Closing this gap is the single highest-leverage 2.0 work.**

## Design principles

1. **Pure-static dashboard.** No backend server. All data comes from `output/*.json` files served by GitHub Pages.
2. **Polling, not push.** 5-minute polling against the JSON files. WebSocket complexity is not justified.
3. **Telegram is the action transport.** UI buttons construct deep-links into the existing Telegram bot. No new approval API.
4. **One card per data source.** Each UI component reads ONE JSON file (e.g. `unified_proposals.json` → ProposalCard). Decoupling = independent evolution.
5. **Mobile-first PWA.** User is iPad-first, MacBook-secondary; design for touch and small viewports.
6. **Read-only PWA.** UI cannot write to `output/`; only Telegram bot mutates state. UI is a viewer + a launcher.
7. **Graceful degradation.** If a JSON file is missing or malformed, the corresponding card shows a friendly "data unavailable" state, not a crash.

## Component inventory

| Component | Reads | Shows | User actions | Refresh |
|---|---|---|---|---|
| **ProposalCard** | `output/brain/unified_proposals.json` | 3 PENDING proposals from last night's brain run with full evidence | `/approve`, `/reject`, `/explain` Telegram deep-links | 5-min poll |
| **ExposureCard** | `output/brain/portfolio_exposure.json` | Current 100% Choppy + 23.75% UP_TRI×Choppy×Bank cell warnings | Click → expand to per-position breakdown | 5-min poll |
| **RegimeCard** | `output/brain/regime_watch.json` | Current regime + transition evidence + recent 7-day distribution + weekly_intelligence snapshot | None (informational) | 5-min poll |
| **CohortHealthCard** | `output/brain/cohort_health.json` | Tier W/M/Candidate cohorts; Wilson-lower bounds; baselines per signal type | Click cohort → drill into per-trade history | 5-min poll |
| **SignalsCard** | `output/bridge_state.json` (current phase) | Today's PENDING signals with bucket assignment (TAKE_FULL / TAKE_SMALL / WATCH / SKIP) | Click signal → see full SDR + evidence panel | 5-min poll |
| **OutcomesCard** | `output/signal_history.json` filtered to past 30 days | Resolved trades with R-multiple histogram | Click outcome → see full trade lifecycle | 5-min poll |
| **LedgerCard** | `output/brain/decisions_journal.json` | Approval history; for each approved proposal, +30d outcome metrics | None (audit view) | 5-min poll |
| **HealthCard** | `output/system_health.json` | 7 chain validator checks + alerts | None | 5-min poll |
| **CaveatsCard** | `data/mini_scanner_rules.json` (watch_patterns) | Active watch_warnings, fired today | None (info) | static |

## Layout

iPad-first three-column desktop / single-column mobile:

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER: TIE TIY 2.0    [regime label]    [date]    [refresh]│
├─────────────────────────────────────────────────────────────┤
│ TOP ROW (priority cards):                                   │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ ProposalCard    │ │ ExposureCard    │ │ RegimeCard      │ │
│ │ 🟡 3 pending   │ │ ⚠️ 100% Choppy │ │ Choppy 7 days   │ │
│ │ [approve][rej] │ │ Bank 23.75%    │ │ slope +0.0022   │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ MID ROW: Today's signals                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SignalsCard — N PENDING today                           │ │
│ │ stock | signal | bucket | score | entry/stop/target     │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ LOWER ROW: history + audit                                  │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│ │ CohortHealthCard│ │ OutcomesCard    │ │ LedgerCard      │ │
│ │ Tiers W/M/Cand. │ │ Past 30 days    │ │ approvals       │ │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ FOOTER: HealthCard + CaveatsCard                            │
└─────────────────────────────────────────────────────────────┘
```

Mobile: same cards, single column, ProposalCard pinned at top.

## ProposalCard — the critical component

The card that closes the approval loop. Renders each pending proposal as:

```
┌─────────────────────────────────────────────────────────────┐
│ 🧠 BRAIN PROPOSALS — 2026-05-12 22:00 IST run               │
├─────────────────────────────────────────────────────────────┤
│ prop_unified_2026-05-12_001                          [PEND] │
│ UP_TRI × Bear: n=96, 94.7% WR, Tier M → boost (TAKE_SMALL)  │
│                                                             │
│ CLAIM                                                       │
│   Promote boost_pattern signal=UP_TRI, regime=Bear (Tier B  │
│   / TAKE_SMALL). +17.9pp edge.                              │
│                                                             │
│ EVIDENCE                                                    │
│   • Wilson 95% lower 0.8815 — sample adequate              │
│   • R-multiple 0.61 caps to Tier M (TAKE_SMALL)            │
│   • win_001 active (UP_TRI×Auto×Bear, n=21)                │
│   • [show 5 more]                                          │
│                                                             │
│ RISKS                                                       │
│   • Cohort tier may drift; demotion auto-fires per §3      │
│   • R-multiple under D-8 (Day-6 forced exit) review        │
│   • Approval propagates overlap to mini_scanner_rules.json │
│                                                             │
│ REVERSIBILITY                                               │
│   1-line revert in mini_scanner_rules.json boost_patterns[]│
│                                                             │
│ EXPIRES 2026-05-19 (7 days)                                 │
│                                                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ APPROVE  │ │ REJECT   │ │ DEFER    │ │ EXPLAIN  │         │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘         │
└─────────────────────────────────────────────────────────────┘
```

Buttons construct Telegram deep-links:
- APPROVE → `tg://msg?text=/approve%20prop_unified_2026-05-12_001`
- REJECT → opens reason input modal → constructs `tg://msg?text=/reject%20prop_unified_2026-05-12_001%20reason_text`
- DEFER → no-op locally; proposal will re-fire tomorrow if still relevant
- EXPLAIN → `tg://msg?text=/explain%20prop_unified_2026-05-12_001`

User taps button → Telegram opens with prefilled command → user hits send → existing Telegram bot processes → `mini_scanner_rules.json` updated → `decisions_journal.json` appended → next page poll picks up new state.

**This pattern requires zero new backend.** The PWA is static; Telegram is the action transport. The Telegram bot already handles the approval commands.

## Real-time refresh design

Pure polling:

```javascript
// Each card schedules its own poll
class ProposalCard {
  data_source: "output/brain/unified_proposals.json"
  refresh_strategy: "poll_5min"
  
  async refresh() {
    const r = await fetch(this.data_source + "?v=" + Date.now());  // cache-bust
    const data = await r.json();
    this.render(data);
  }
}
```

5-min poll = 288 fetches/day per card × 9 cards = ~2600 fetches/day. GitHub Pages handles this trivially. No server cost.

Optionally: an ETag-based conditional fetch reduces bandwidth to "only when changed". Easy optimization; not required for v1.

## Approval-loop closure detail

```
T+0:    Brain run completes 22:00 IST
        - writes output/brain/unified_proposals.json (3 PENDING)
        - writes output/brain/history/2026-05-12_unified_proposals.json
        - git commit-and-push
T+5min: PWA's ProposalCard polls, sees new proposals
        - renders 3 cards
        - sends one-time push notification (existing push_sender.py)
T+next user open: user sees badge "3 PENDING"
        - opens dashboard
        - reviews proposal 001 (UP_TRI×Bear boost)
        - taps APPROVE button
        - Telegram opens with /approve prop_unified_2026-05-12_001 prefilled
        - user hits send
T+approval+5s:
        - Telegram bot processes /approve
        - applies via rule_proposer.approve_proposal
        - writes data/mini_scanner_rules.json (new boost_pattern added)
        - writes output/brain/decisions_journal.json (approval entry)
        - writes output/brain/unified_proposals.json (status → "approved")
        - git commit-and-push
T+approval+5min: PWA polls
        - sees decision; ProposalCard now shows 2 PENDING + 1 APPROVED
        - LedgerCard shows the approval
        - mini_scanner_rules.json takes effect on next morning_scan
```

**Loop closure verified end-to-end without a backend.** This is the whole point of pure-static.

## Failure modes

| Failure | UI behavior |
|---|---|
| `unified_proposals.json` missing | ProposalCard shows "No brain output today. Last brain run: {regime_watch.generated_at}" |
| `unified_proposals.json` malformed JSON | Card shows "Brain output unreadable; check repo state" + raw `error.message` |
| GitHub Pages serves stale file (>1 hour) | Footer warns "Last refresh failed at {timestamp}; data may be stale" |
| Telegram bot is down | APPROVE button shows but tap → Telegram → user sends → bot doesn't ack → user notices missing decision in dashboard 5 min later. **Telegram bot up-time IS the approval loop SLA.** |
| User on iPad clicks button but Telegram not installed | Deep-link fails open → fallback shows the command text as copy-paste |

## Components NOT in the dashboard

To prevent scope creep:

- **No trading execution.** User trades manually via broker.
- **No real-time chart rendering.** Out of scope. (Link to TradingView per stock if user wants.)
- **No backtest UI.** Validation harness is CLI-only; output written to markdown reports.
- **No model parameter editing.** Plug-in config edits via `data/plugins.yaml` and `mini_scanner_rules.json` only — through Telegram approvals.
- **No alerts management UI.** Stop alerts and target alerts ship via Telegram; not duplicated in dashboard.

## Effort

| Task | Hours |
|---|---:|
| PWA shell (layout, navigation, service worker, polling framework) | 12 |
| ProposalCard (the critical one) | 8 |
| ExposureCard | 4 |
| RegimeCard | 4 |
| CohortHealthCard | 6 |
| SignalsCard | 8 |
| OutcomesCard | 6 |
| LedgerCard | 4 |
| HealthCard | 2 |
| CaveatsCard | 2 |
| Deep-link plumbing (Telegram action transport) | 4 |
| Push notification hooks (existing push_sender) | 2 |
| End-to-end smoke + iPad/MacBook testing | 6 |
| **Total** | **~68 hours** |

This can be split:
- **Phase 1 (P0, 28h):** PWA shell + ProposalCard + ExposureCard + deep-links + push. **Ships closed approval loop in 1 week.**
- **Phase 2 (P1, 22h):** RegimeCard + CohortHealthCard + SignalsCard. Ships richer visibility.
- **Phase 3 (P2, 18h):** OutcomesCard + LedgerCard + HealthCard + CaveatsCard + polish.

**The Phase 1 alone is the highest-ROI work in the entire TIE TIY 2.0 program** — it would close the approval loop that's been open since 2026-04-29, on top of the existing infrastructure, without waiting for the rest of 2.0 to ship.
