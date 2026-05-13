# 05 — Self-Learning Workflow

The user's definition (verbatim from prior session): **"Brain proposes, user approves, system applies, brain learns from outcomes."** Never auto-applies. Never autonomous evolution.

This is closed-loop reinforcement through curated human approval. Not RL. Not autonomous learning. The system learns the human's preferences over time and proposes more of what the human approved, less of what the human rejected.

## State machine

A proposal lives in one of these states:

```
                  ┌─────────────────────────────────┐
                  ▼                                 │
   [ABSENT]──── brain run ────►[PENDING]          (re-fires
                                  │  │              tomorrow
                                  │  └──► /defer ───if conditions
                                  │                  unchanged)
                                  │
                                  ├──► /approve ────►[APPROVED]
                                  │                       │
                                  │                       ▼
                                  │              (rule_change applied
                                  │               + outcome tracking
                                  │                  begins +30d)
                                  │                       │
                                  │                       ▼
                                  │           [TRACKING_OUTCOME]
                                  │              (T+30d)
                                  │                       │
                                  │              ┌────────┴────────┐
                                  │              ▼                 ▼
                                  │       [CONFIRMED]        [DEMOTION_PROPOSED]
                                  │       (metrics held)     (metrics regressed;
                                  │                          brain auto-proposes
                                  │                          revert)
                                  │
                                  ├──► /reject + reason ────►[REJECTED_RECORDED]
                                  │                              (logged; brain
                                  │                               sees this on
                                  │                               next 90-day
                                  │                               lookback)
                                  │
                                  └──── 7 days elapse ────►[EXPIRED]
                                                              (logged; re-fires
                                                              if same evidence
                                                              tomorrow)
```

## Data model

### Proposal record (`output/brain/unified_proposals.json`)

```json
{
  "proposal_id": "prop_unified_2026-05-12_001",
  "proposal_type": "boost_promote",
  "title": "UP_TRI × Bear: n=96, 94.7% WR ...",
  "claim": {
    "what": "Promote boost_pattern signal=UP_TRI, regime=Bear (Tier B / TAKE_SMALL)",
    "expected_effect": "+17.9pp edge",
    "confidence": "high"
  },
  "counter": { "evidence": [...], "risks": [...] },
  "target": {
    "file": "data/mini_scanner_rules.json",
    "path": "boost_patterns[]",
    "current_value": null,
    "proposed_value": {
      "id": "boost_brain_4d532dbb",
      "signal": "UP_TRI", "regime": "Bear",
      "tier": "B", "conviction_tag": "TAKE_SMALL",
      ...
    }
  },
  "reversibility": "1-line revert in mini_scanner_rules.json",
  "score_priority": 9.99,
  "status": "pending",            // pending|approved|rejected|expired|confirmed|demotion_proposed
  "created_at": "2026-05-12T22:00:00+05:30",
  "expires_at": "2026-05-19T22:00:00+05:30",
  "decided_at": null,
  "decider": null,
  "decision_reason": null,
  "applied_changes": null,        // populated on approval: list[{file, before, after}]
  "rollback_handle": null,
  "post_decision_metrics": null   // populated +30d
}
```

### Decisions journal (`output/brain/decisions_journal.json`)

```json
{
  "schema_version": 2,
  "entries": [
    {
      "proposal_id": "prop_unified_2026-05-12_001",
      "decision": "approved",
      "decider": "tietiy",
      "decided_at": "2026-05-13T08:42:00+05:30",
      "reason": null,
      "applied_changes": [
        {
          "file": "data/mini_scanner_rules.json",
          "diff": "+boost_patterns += [{...}]",
          "before_sha": "...",
          "after_sha": "..."
        }
      ],
      "rollback_handle": "rollback_2026-05-13_0842",
      "outcome_tracking": {
        "window_start": "2026-05-13",
        "window_end": "2026-06-12",
        "baseline_cohort_wr": 0.9468,
        "baseline_cohort_avg_pnl": 5.87,
        "baseline_cohort_n": 96,
        "checkpoints": [
          // populated at T+14d, T+30d
        ]
      },
      "final_metrics": null   // populated at T+30d
    }
  ]
}
```

## What the brain learns

The brain reads three signals to improve its proposals:

1. **Approval frequency by proposal type.** If user rejects all `kill_pattern_add` proposals → brain stops generating them (or proposes them less aggressively / with stricter thresholds). If user approves all `cohort_promote` → brain proposes more of them.

2. **Rejection reasons.** Free-form text in `/reject {id} {reason}`. Brain's `cohort_promotion_judge` (Opus 4.7) reads the last 90 days of rejection reasons during its LLM gate. The reasons feed the gate's reasoning. E.g., "rejected because n<30 for my comfort" → gate proposes future cohort_promotes only when n≥30.

3. **Post-decision metrics.** At T+30d, each approved change has its outcome measured. If the change improved metrics, brain proposes similar changes more confidently. If regressed, brain proposes a revert.

## Self-learning concrete flow

**Day 1:** Brain proposes "UP_TRI × Bear → Tier M boost." User approves.

**Day 1-30:** UP_TRI × Bear signals fire under the new boost rule. They get TAKE_SMALL bucket assignment in the bridge. Their outcomes accumulate.

**Day 14:** Mid-window checkpoint. Brain checks the cohort's WR in the post-approval window. If WR > 80% → on-track. If WR < 50% → brain raises a yellow flag in next nightly digest.

**Day 30:** Final metrics computed. Compare to baseline. Two outcomes:

- **CONFIRMED:** post-decision WR ≥ pre-decision WR − 5pp tolerance. Promotion was validated. Brain may propose tier upgrade.
- **DEMOTION_PROPOSED:** post-decision WR dropped >5pp. Brain auto-proposes `demote_boost prop_unified_2026-05-12_001`. User decides whether to revert.

**Day 31+:** The decision and its outcome are visible in the LedgerCard. The user can see: "I approved this 30 days ago; it worked / regressed by X percentage points." This is the **learning loop closure**.

## Safe-to-auto-apply vs always-approval

| Class | Examples | Auto policy |
|---|---|---|
| **Always-auto** | Cohort metric recompute; calibration metric updates; daily JSON regeneration; log appends | Yes; no human required |
| **Always-approval** | Rule parameter changes; regime threshold changes; V5 thresholds; kill_pattern additions; boost_pattern promotions; cohort tier reassignments | Yes; every change through proposal queue |
| **Never-auto** | New signal type definitions; universe additions/removals; risk-per-trade %; total capital; data-source switches; plug-in registration changes | Manual code/config edit only |

The brain proposes ONLY items in the middle class. Items in "always-auto" don't need a proposal (they're not changes to behavior). Items in "never-auto" are out of the brain's authority entirely (they're operator-control-plane).

## What the brain SHOULD NOT learn (constrained by L99 + prior consensus)

- **New signal types.** Brain doesn't propose novel patterns; vision LLMs overfit and the deterministic miner overfits too. Use human-defined detectors (the 5 L99 setups + UP_TRI/BULL_PROXY).
- **Cross-symbol arbitrage.** Out of scope.
- **Position-management proposals.** Add-to-position, scale-out timing — discretionary territory.
- **Stop placement novelty.** Stops belong to the signal definition; brain tunes parameters in the same family, not novel logic.
- **Schedule changes.** When the scanner fires. Operator control.

## Audit trail requirements

Every state transition is journaled:

1. Proposal creation → `unified_proposals.json` append; `history/{date}_unified_proposals.json` snapshot.
2. Approval/rejection → `decisions_journal.json` append.
3. Rule change application → `mini_scanner_rules.json` git commit (the git history IS the audit log).
4. Outcome tracking → `decisions_journal.json` checkpoint update at T+14d and T+30d.
5. Demotion proposal → new `unified_proposals.json` entry referencing original proposal_id.

**Every decision is reversible.** `rollback_handle` in each approval gives the exact diff to revert. Telegram `/undo {handle}` re-applies the inverse.

## Brain's 90-day lookback (already shipped in `brain_reason.py`)

The LLM gate already reads the prior 90 days of `decisions_journal.json` during its reasoning step. This is how the brain "remembers" rejections without re-proposing the same thing. **Already shipped.** Just needs proposals to actually be reviewed for this to bite.

## Effort to implement

| Component | Status today | Hours to ship |
|---|---|---:|
| Proposal generation (brain pipeline) | ✅ shipped | 0 |
| State machine (proposal lifecycle) | partial | 8 |
| Decisions journal expanded schema | partial | 4 |
| ApprovalHandler (Telegram side) | ✅ shipped | 0 |
| ApprovalHandler (UI side, deep-link to Telegram) | not built | 6 (per §04) |
| Outcome tracking +14d / +30d checkpoint | not built | 12 |
| Demotion auto-proposal | not built | 8 |
| 90-day rejection-reason ingestion into LLM gate | ✅ shipped (1.0 has it) | 0 |
| Audit trail / git-as-log validation | implicit (commits already happen) | 0 |
| **Total self-learning closure effort** | | **~38 hours** |

Most of this is "wire up the closure," not "build the brain." The brain is already smarter than the loop allows it to be — because the loop has never closed end-to-end.

## The critical bottleneck

**The bottleneck is not engineering effort. It is user discipline.** The brain has produced ~9 days of identical proposals (the same 3 PENDING items have regenerated every night since 2026-04-29 because nothing has been approved or rejected).

If the user can develop a discipline of reviewing nightly digest + clicking approve/reject within 24 hours of brain run, **the self-learning loop closes automatically.** The infrastructure works. The dashboard surfaces the proposals (per §04). The Telegram bot processes the decision. The brain reads decisions on its next 90-day lookback.

If the user cannot develop that discipline, no amount of UI polish helps. The proposals will continue to expire silently no matter how pretty the cards are.

**The acceptance test for "self-learning works":** in the first 14 days after the dashboard ships, the user makes ≥10 approval decisions (approved or rejected, not deferred or expired) across the 3 PENDING proposal types.

If that's met → continue building. If not met → halt building. The architecture isn't the problem.
