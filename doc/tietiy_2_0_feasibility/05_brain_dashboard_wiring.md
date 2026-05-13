# 05 — Brain Layer ↔ Dashboard Wiring

## Current state (the gap)

| Component | Status |
|---|---|
| brain writes proposals to `output/brain/unified_proposals.json` | ✅ shipped, generates them daily-at-22:00 IST when fired |
| brain fires in production | 🟠 BLOCKED on user-side actions (ANTHROPIC_API_KEY GH secret + cron-job.org entries) |
| Telegram digest of proposals (brain_digest.yml at 22:05 IST) | ✅ shipped, blocked on same |
| dashboard reads proposals (analysis.html on tietiy.in) | ❌ no code path |
| user approval via dashboard | ❌ no UI |
| user approval via Telegram | ✅ `/approve_rule <id>`, `/reject_rule <id>` shipped |
| audit log of decisions | ✅ `output/brain/decisions_journal.json` (currently empty — no decisions ever recorded) |

**Net:** brain proposals → Telegram works in principle but no one approves them; dashboard doesn't surface them at all.

## Target architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ Daily 22:00 IST: brain.yml workflow                                  │
└──────────────────────────────────────────────────────────────────────┘
        │
        ├──► brain_derive → 4 truth views
        ├──► brain_verify → candidate proposals (deterministic)
        ├──► brain_reason → LLM gates (Opus 4.7, ~$0.10/run)
        ├──► brain_output → unified_proposals.json (append-only history file)
        │       │
        │       ├──► writes to output/brain/unified_proposals.json
        │       └──► writes to output/brain/history/{date}_unified_proposals.json
        │
        └──► brain_telegram → 22:05 IST digest message
                with ⤵️ inline buttons / commands per proposal:
                  /approve {prop_id}    /reject {prop_id} [reason]    /explain {prop_id}
                                                                      
┌──────────────────────────────────────────────────────────────────────┐
│ Continuously: dashboard read path (analysis.html)                    │
└──────────────────────────────────────────────────────────────────────┘
        │
        ├──► GitHub Pages serves output/ as static (already live)
        ├──► dashboard JS fetches output/brain/unified_proposals.json
        │       polls every 5 min or fires on bridge_state.json mtime change
        │
        ├──► renders "Brain Proposals" card per pending proposal:
        │       title • claim • evidence • risks • reversibility
        │       buttons: [APPROVE] [REJECT] [DEFER] [EXPLAIN]
        │
        └──► user clicks button → triggers Telegram deep-link with prefilled command
                (per LE-05 / IT-05 design; currently DEFERRED to Wave UI)

┌──────────────────────────────────────────────────────────────────────┐
│ User decision (via Telegram OR dashboard)                            │
└──────────────────────────────────────────────────────────────────────┘
        │
        ├──► telegram_bot.py handles /approve, /reject, /explain
        ├──► applies change via rule_proposer adapter (kill_rule or boost_promote)
        │       │ mini_scanner_rules.json updated atomically
        │       │ unified_proposals.json marked status=approved/rejected
        │       └─► decisions_journal.json appended
        │
        └──► next bridge L1 fire uses the new rule
```

## Architecture options (with effort estimates)

### Option A: Polling dashboard (simplest)

Dashboard JS polls `output/brain/unified_proposals.json` every 5 minutes. On change, refresh.

PRO: trivially simple. No backend. GitHub Pages caching handled by static asset versioning (`?v=Date.now()` per CACHE-01).
CON: Up to 5-min staleness. Approval still requires Telegram (deep-link).

**Effort: ~16h** (dashboard card component + polling + deep-link buttons).

### Option B: Brain writes to signal_history.json (rejected)

Add a `proposals` table inside `signal_history.json`. Dashboard already reads it for analysis.html.

PRO: Single read path.
CON: Violates the "signal_history is persistent truth, proposals are overlays" design principle (CLAUDE.md Principle 1). Mutates the most-sacred file.

**Rejected.**

### Option C: Webhook to dashboard backend (overkill for v1)

brain → POST /api/proposals/upsert → backend stores → dashboard fetches from backend.

PRO: Real-time. Audit trail in backend DB.
CON: Requires backend server. User has no backend infrastructure today (PWA is static).

**Defer to v2.** Effort if built: ~60h.

### Option D: Brain → Telegram + dashboard mirror (recommended)

Brain writes `unified_proposals.json` (already does). Brain triggers a `commit-and-push` workflow that includes the new proposals in the GitHub Pages deploy. Dashboard reads the static file. Telegram delivers digest 5 min later.

PRO: No new infrastructure. Audit trail = git history. Approval via Telegram is already shipped.
CON: Dashboard refresh requires explicit reload (no live update without polling).

**Effort: ~24h** for dashboard component + Telegram deep-link prefill.

## Recommended approach

**Option D** for v1 (24h). Migrate to Option C in v2 if real-time becomes important.

## Audit log

Every decision flows to `output/brain/decisions_journal.json`:

```json
{
  "schema_version": 1,
  "entries": [
    {
      "proposal_id": "prop_unified_2026-04-29_001",
      "decision": "approved",
      "decider": "tietiy",
      "decided_at": "2026-04-30T08:42:00+05:30",
      "reason": null,
      "applied_change": {
        "file": "data/mini_scanner_rules.json",
        "kind": "boost_promote",
        "diff": {...}
      },
      "outcome_tracking_window_days": 30,
      "post_decision_metrics": null   // populated at +30d
    }
  ]
}
```

After 30 days post-approval, `post_decision_metrics` is populated with the cohort's WR / avg PnL / R-multiple to track whether the approved change actually paid off. **This is the closing of the self-learning loop: approved changes are measured.**

## Effort to implement (Option D)

| Component | Hours |
|---|---:|
| Dashboard "Brain Proposals" card (HTML + JS) | 8 |
| Polling against output/brain/unified_proposals.json (5-min interval) | 2 |
| Deep-link buttons (tg://msg?text=/approve+prop_id) | 2 |
| Telegram bot extension for /explain command | 3 |
| decisions_journal.json schema + writer | 3 |
| post_decision_metrics computation (cohort-recompute at +30d) | 4 |
| End-to-end smoke test | 2 |
| **Total** | **~24 hours** |

## Pre-condition: brain must actually fire

None of this matters if brain.yml doesn't run. The user-side actions in `session_context.md` (the 3 cron-job.org dashboard entries + `ANTHROPIC_API_KEY` secret) are the gate. These are **0 code, ~30 minutes of dashboard clicks**. They've been outstanding since 2026-04-29.

**The dashboard wiring is the second-most-important fix. The brain production-fire is THE most important. Without the brain firing, there's nothing to wire.**

## Self-learning closure

The user's "self-learning" requirement closes via this loop:

```
Day D:    brain proposes (e.g., "boost UP_TRI×Auto×Bear → Tier A")
Day D+0:  user reviews proposal + evidence in Telegram/dashboard
Day D+0:  user /approve → mini_scanner_rules.json updated
Day D+0 to D+30: signals fire under new rule; outcomes accumulate
Day D+30: brain recomputes cohort metrics for the approved change
Day D+30: if metrics regressed below threshold → brain proposes demotion
Day D+30: user re-approves demotion or holds
```

This is "brain proposes, human disposes" per the user's spec. It is implementable today on top of the existing brain layer. Total effort: 24h dashboard + 30min user-side cron setup.
