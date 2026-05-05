# Shadow Ops v1 — Architecture Document

**Status**: DRAFT (pre-implementation review)
**Branch**: shadow_ops_v1
**Author**: TIE TIY core team
**Consultant inputs**: Round 9 (`doc/consultant_briefings/round_09_phase3_vp_fix.pdf`),
Round 10 (`doc/consultant_briefings/round_10_rule031_supplement.pdf`)
**Audit dependencies**: `vp-leakage-fix` branch at `ae519fb6` (corrected `feat_nifty_vol_percentile_20d` + W3 re-classification); `rule_031_audit` branch (compressed audit cycle, FAIL on sector substitutability)

This document anchors implementation. It is the audit-first deliverable for the shadow ops
workstream — design before code. Every implementation decision below is reviewable in
isolation; flagged open questions in Section 14 must be resolved before code begins.

---

## 1. Purpose & Non-Purpose

### 1.1 What shadow ops IS

Shadow ops v1 is a forward-time **process validation** harness. Its purpose is to test
whether the audited rule library can be operated as a disciplined trading process by a
human operator (or by an automated system under human supervision), separate from any
question of statistical edge.

The four failure modes shadow is designed to detect, derived directly from consultant
Round 9 framework:

1. **Operational integrity failure** — triggers fire ambiguously, lifecycle states diverge
   from spec, modules surface unexpected interactions, daily scan fails or partially
   succeeds without surfacing as an error.
2. **Behavioral discipline failure** — the operator overrides the rules, takes boredom
   trades during idle stretches, drifts toward discretionary additions to the trade plan,
   modifies past records.
3. **Process-fit failure** — the rule's signal rarity (rule_019 fires in only ~22 of 182
   historical 60-day windows = roughly 1 trade every 8 weeks during favorable regimes,
   far less often in non-Bear regimes) creates extended idle stretches that human
   psychology cannot tolerate; the operator stops running the process.
4. **Negative surprise** — something structurally inconsistent with audited rule behavior
   surfaces in live operation that the historical audits did not detect (e.g., a feature
   computation bug, a regime classifier inconsistency, a corner case in lifecycle
   transitions).

### 1.2 What shadow ops is NOT

Shadow ops v1 is **explicitly NOT**:

1. **A statistical edge proof.** The audited edge of rule_019 (~14.8pp post-vp-fix walk-
   forward lift, ~68% per-trade WR) is established from 15 years of backtest data
   covering 2,149 won-resolved matches. A 30-day shadow period at rule_019's natural
   firing rate generates an expected 0–4 trades. This is statistically meaningless for
   edge confirmation. Per Round 9 consultant framing: shadow validates **process**, not
   **edge**.
2. **A capital allocation tool.** No actual capital is deployed. No actual broker orders
   are placed. The shadow run produces logged hypothetical trade cards and counterfactual
   fill simulations only.
3. **A live trading system.** No order routing infrastructure. No real-time market data
   subscription beyond what the existing daily-EOD scanner already provides.
4. **An automatic path to live capital.** Per Round 10 consultant decision: "shadow !=
   automatic path to live capital. Business-model mismatch is sharper post-rule_031-
   retirement, not softer." Shadow completion is necessary but not sufficient for live
   deployment. After shadow, the explicit Bull/Choppy regime gap and overall sleeve
   rarity must be addressed before any live capital decision.

### 1.3 Decision criteria reframed

Shadow ops produces a binary outcome at the end of its 30-day minimum window:

- **PROCESS-VALIDATED**: All four failure modes inspected and clean. Trade cards
  flowed through lifecycle correctly. Operator did not override or drift. Idle
  stretches did not produce discipline collapse. No structural inconsistencies
  surfaced. → Eligible for the next architecture conversation about whether/how to
  proceed to a paper-trading or limited-capital-pilot phase.
- **PROCESS-FAILED**: One or more of the four failure modes fired. → Specific failure
  documented; either a code fix, a process change, or a recognition that the operator-
  rule fit is insufficient. Shadow restarts or workstream pauses for redesign.

A "no signals fired" outcome is itself informative — it surfaces sleeve rarity as a
process-fit constraint. The 30-day window may be extended (consultant Round 9: "extend
if signals sparse") to ensure at least 2-3 trade cards flow through full lifecycle.

---

## 2. Deployment Scope

### 2.1 Active rules

| Role | Rule ID | Behavior in shadow |
|---|---|---|
| **Primary trade rule** | `rule_019_bear_uptri_hot_refinement` | Fires per its match logic. Each fire generates a PROPOSED trade card. |
| **Sectoral distress diagnostic** | `kill_001` | LOGGED. Fires on Bear+Bank+DOWN_TRI conditions, which DON'T overlap with rule_019's Bear+UP_TRI match conditions. kill_001 cannot directly suppress rule_019 trade cards; same symbol cannot carry both signals simultaneously. Its co-firing on a scan day is a sectoral-distress diagnostic that may inform a manual operator decision to SKIP rule_019 PROPOSED cards (with `reason=sector_distress_pause`). See §4.3 for the manual decision criteria. |
| **Confirmation overlay** | `rule_031_bear_uptri_it_hot` | LOGGED, NOT used for sizing. When rule_031 ALSO fires on the same scan event, the trade card carries `rule_031_confirm = 1`. Otherwise `rule_031_confirm = 0`. See Section 11. |

**kill_001 framing note**: kill_001 doesn't directly affect rule_019 trade cards because their
match conditions don't overlap (rule_019 fires on UP_TRI signals; kill_001 on DOWN_TRI). It's
logged in shadow as a sectoral distress diagnostic that may inform manual operator pause
decisions when Bank-DOWN_TRI conditions cluster heavily on the same scan day. The pause
mechanism is the standard SKIPPED state with operator-supplied reason.

### 2.2 Inactive (logged only, not actionable in v1)

| Category | Status | Reason |
|---|---|---|
| Other 4 rule_019-class SURVIVORs (win_001, win_004, win_005, win_006) | Out of scope | Phase 3 audited only rule_019 in depth. Other survivors not yet audit-confirmed for live deployment. Round 9 consultant: deploy rule_019 alone first. |
| Bull regime rules | Out of scope | Zero deployable Bull-regime rules survive W3 + Phase 3. Round 9 consultant: business-model mismatch — Bear-only sleeve cannot generate income across Bull/Choppy stretches. |
| Choppy regime rules | Out of scope | Zero deployable Choppy-regime rules; 6 are dead schema (sub_regime constraint mismatch). |
| Other Bear sub_regime rules (warm/cold variants) | Out of scope for v1 | Not yet audit-confirmed; Phase 3 was rule_019 specific; rule_031 audit is informational not deployment. |

### 2.3 Period

- **Minimum 30 calendar days** of forward operation.
- Consultant guidance: extend if signals sparse. Hard ceiling not specified; recommend
  60 calendar days as upper bound, after which a "process-validated but undertraded"
  conclusion is drawn and the workstream pauses for sleeve-expansion design.

### 2.4 Capital and infrastructure

- **No capital deployed.** Trade cards are hypothetical. Realized P&L is computed
  counterfactually from public market price data (Section 6).
- **No broker integration.** No order management system, no risk management overlay.
- **Single-operator model.** v1 assumes one human operator running the daily process
  (or supervising an automated daily process). Multi-operator coordination is out of
  scope.

---

## 3. Data Model

### 3.1 Storage decision (proposed)

**Storage format: JSONL (JSON Lines), append-only, one file per event class.**

Rationale:
- **Append-only by file format**: each event is a complete JSON object on its own line.
  Reading is line-by-line; writing is `open(path, "a")` and `f.write(json.dumps(event) + "\n")`.
  Modification of a past line requires explicit rewriting of the entire file, which
  is detectable via git diff and never done by the daily process.
- **Human-readable**: every record is plain text, inspectable with `cat`, `tail`,
  or `jq` without specialized tooling.
- **Diff-friendly**: git diff on JSONL surfaces exactly which lines were added on
  which day; tampering with past records produces large diffs that are impossible
  to hide.
- **Schema evolution**: new fields can be added to future records without rewriting
  past records. Readers tolerate missing fields.

Alternatives considered and rejected:
- **SQLite**: queryable, but schema migration discipline is harder to enforce
  visually; binary format hides modification of past records; over-engineered for
  v1 volume (likely <100 records over 30 days).
- **CSV**: human-readable but column rigidity makes schema evolution painful;
  adding a new field requires all-rows rewrite; multi-line text fields (e.g., reasons
  for skip) require quoting discipline.
- **Markdown reports only**: not machine-parseable; cannot be analyzed at end-of-
  shadow without manual re-entry.

### 3.2 Storage location (proposed — see open questions §14)

Each shadow run gets a dedicated directory:

```
shadow_ops/
  runs/
    YYYY-MM-DD_runlabel/                    # e.g., 2026-05-06_v1_initial
      scan_events.jsonl
      candidate_signals.jsonl
      trade_cards.jsonl
      lifecycle_events.jsonl
      fill_simulations.jsonl
      operator_journal.md
      summary.md                            # written at run end
      run_config.json                       # config used for this run
```

Multiple runs are supported. The run directory is git-tracked so that the full
shadow record is part of the audit trail.

### 3.3 Event schemas

#### 3.3.1 `scan_event`

One record per daily scan run. Logged before any candidate processing. Captures the
context of the scan even if no signals fire.

```json
{
  "event_id": "scan_2026-05-06_001",
  "event_type": "scan_event",
  "timestamp_utc": "2026-05-06T10:35:42Z",
  "scan_date": "2026-05-06",
  "regime": "Bear",
  "sub_regime": "hot",
  "sub_regime_inputs": {
    "feat_nifty_vol_percentile_20d": 0.78,
    "feat_nifty_60d_return_pct": -0.12,
    "feat_market_breadth_pct": 0.32
  },
  "n_signals_universe": 188,
  "n_signals_post_filter": 23,
  "scan_status": "OK",
  "scan_duration_ms": 4521,
  "git_commit_sha": "ae519fb6...",
  "data_versions": {
    "enriched_signals_sha256": "...",
    "rules_path_sha256": "..."
  }
}
```

`scan_status` ∈ `{OK, PARTIAL, ERROR}`. PARTIAL means scan completed but with warnings;
ERROR means scan halted before generating signals (alerts fire — Section 9).

`git_commit_sha` and `data_versions` provide tamper-evidence: any later analysis can
verify that the scan ran against an exact code+data snapshot.

#### 3.3.2 `candidate_signal`

One record per (signal-row) that matches rule_019 OR is suppressed by kill_001 OR is
relevant to the rule_031 overlay state. Logged regardless of subsequent action.

```json
{
  "event_id": "cand_2026-05-06_LUPIN.NS_001",
  "event_type": "candidate_signal",
  "timestamp_utc": "2026-05-06T10:35:42Z",
  "scan_event_id": "scan_2026-05-06_001",
  "scan_date": "2026-05-06",
  "symbol": "LUPIN.NS",
  "sector": "Pharma",
  "signal": "UP_TRI",
  "regime": "Bear",
  "sub_regime": "hot",
  "rule_019_match": true,
  "rule_031_match": false,
  "kill_001_match": false,
  "trigger_disposition": "TRADE_CARD_PROPOSED",
  "rule_features_snapshot": {
    "feat_nifty_vol_percentile_20d": 0.78,
    "feat_nifty_60d_return_pct": -0.12,
    "atr": 23.45,
    "stop": 1820.50,
    "pivot_price": 1885.00,
    "entry_est": 1890.20
  }
}
```

`trigger_disposition` ∈ `{TRADE_CARD_PROPOSED, SUPPRESSED_BY_KILL_001, RULE_031_OVERLAY_ONLY, NO_ACTION}`.

#### 3.3.3 `trade_card`

One record per PROPOSED trade card. Created from a `candidate_signal` with disposition
`TRADE_CARD_PROPOSED`. Mutated only via `lifecycle_event` records (NOT in-place edits).

The `trade_card` JSONL stores the LATEST state per card, derived from the lifecycle
event log. The lifecycle log is the source of truth; the trade_card file is a
materialized read-model regenerated at end-of-day or end-of-run.

```json
{
  "card_id": "card_2026-05-06_LUPIN.NS",
  "event_type": "trade_card",
  "scan_event_id": "scan_2026-05-06_001",
  "candidate_signal_id": "cand_2026-05-06_LUPIN.NS_001",
  "symbol": "LUPIN.NS",
  "sector": "Pharma",
  "rule_id": "rule_019_bear_uptri_hot_refinement",
  "rule_031_confirm": 0,
  "kill_001_match": false,
  "scan_date": "2026-05-06",
  "proposed_entry_price": 1890.20,
  "proposed_stop": 1820.50,
  "proposed_target": 1990.30,
  "atr": 23.45,
  "current_state": "PROPOSED",
  "state_history": [
    {"state": "PROPOSED", "timestamp_utc": "2026-05-06T10:35:42Z", "reason": "rule_019_match"}
  ],
  "actual_entry_date": null,
  "actual_entry_price": null,
  "actual_exit_date": null,
  "actual_exit_price": null,
  "exit_reason": null,
  "realized_pnl_pct": null,
  "realized_R": null
}
```

#### 3.3.4 `lifecycle_event`

One record per state transition of any trade card. THIS IS THE SOURCE OF TRUTH for
trade card state. The `trade_card` file is materialized from this log.

```json
{
  "event_id": "lc_2026-05-07_card_2026-05-06_LUPIN.NS_001",
  "event_type": "lifecycle_event",
  "timestamp_utc": "2026-05-07T03:50:01Z",
  "card_id": "card_2026-05-06_LUPIN.NS",
  "from_state": "PROPOSED",
  "to_state": "ACTIVE",
  "reason": "hypothetical_fill_at_next_open",
  "trigger_data": {
    "fill_date": "2026-05-07",
    "fill_price": 1892.50,
    "open_price": 1890.00,
    "high_price": 1898.10,
    "low_price": 1881.00,
    "close_price": 1894.00
  }
}
```

Valid transitions (state machine, Section 5):
- `PROPOSED → ACTIVE` (hypothetical fill confirmed at next-day open or intraday)
- `PROPOSED → EXPIRED` (no fill condition met within entry window)
- `PROPOSED → SKIPPED` (manual override, kill_001 retroactive trigger, data error)
- `ACTIVE → HYPOTHETICAL_FILLED` (target hit)
- `ACTIVE → HYPOTHETICAL_STOPPED` (stop hit)
- `ACTIVE → EXPIRED` (held to day-6, no target/stop hit)

#### 3.3.5 `fill_simulation`

One record per attempted fill simulation. Captures the price-data inputs used for the
counterfactual fill computation, so any later auditor can reconstruct the simulation
deterministically.

```json
{
  "event_id": "fill_2026-05-07_card_2026-05-06_LUPIN.NS",
  "event_type": "fill_simulation",
  "timestamp_utc": "2026-05-07T03:50:01Z",
  "card_id": "card_2026-05-06_LUPIN.NS",
  "fill_attempt_type": "ENTRY",
  "fill_date": "2026-05-07",
  "fill_decision": "FILLED",
  "fill_price": 1892.50,
  "ohlcv": {
    "open": 1890.00,
    "high": 1898.10,
    "low": 1881.00,
    "close": 1894.00,
    "volume": 2350000
  },
  "fill_logic_applied": "next_day_open_above_pivot",
  "slippage_bps": 0,
  "data_source": "lab/cache/LUPIN_NS.parquet",
  "data_source_sha256": "..."
}
```

`fill_attempt_type` ∈ `{ENTRY, STOP, TARGET, EXPIRY}`.
`fill_decision` ∈ `{FILLED, NOT_FILLED, ERROR}`.

### 3.4 Operator journal

A free-text markdown file (`operator_journal.md`) where the operator records:
- Daily observations (what the scan produced, any concerns).
- Reasons for any SKIP transitions (must duplicate the structured reason in the
  lifecycle_event but adds operator commentary).
- End-of-day discipline self-checks (Section 8).

This is the human side of the audit trail. Free-form, but timestamped per entry.

### 3.5 Run config

`run_config.json` captures the configuration of a specific shadow run (e.g., entry
logic version, slippage assumption, expiry day count). Frozen at run start; never
mutated mid-run.

```json
{
  "run_label": "v1_initial",
  "started_utc": "2026-05-06T00:00:00Z",
  "min_period_days": 30,
  "max_period_days": 60,
  "rules_enabled": ["rule_019_bear_uptri_hot_refinement", "kill_001"],
  "overlay_rules": ["rule_031_bear_uptri_it_hot"],
  "entry_logic": "breakout_within_3_days_v1",
  "expiry_day_count": 6,
  "slippage_bps": 0,
  "git_commit_sha": "ae519fb6...",
  "data_versions": {...}
}
```

---

## 4. Trigger Logic

### 4.1 When does the daily scan fire?

**Proposed (open question, see §14)**: Daily, after IST market close (16:00 IST = 10:30
UTC), once EOD data for the day is available and validated. Scan generates a snapshot
of regime/sub_regime classification and matches the rule library against the day's
signals. Trade cards generated by today's scan are HYPOTHETICALLY FILLED at tomorrow's
open.

This requires:
- Daily EOD data feed in by ~16:30 IST (10:30 UTC).
- Scan completes before midnight IST.
- Next-day-open fills happen at 09:15 IST the following trading day.

If the scan must run during market hours instead (e.g., for pre-open positioning on
day T), surface this as an alternative — the trade card lifecycle changes accordingly.

### 4.2 rule_019 match logic

Per the rule definition in `lab/factory/step5_finalization/L4_opus_output/unified_rules_v4_1_FINAL.json`:

```
match_fields: signal=UP_TRI, sector=null, regime=Bear
sub_regime_constraint: hot
conditions: [{feature: sub_regime, value: hot, operator: eq}]
```

A scan-day signal triggers rule_019 iff:
1. `signal == "UP_TRI"`
2. `regime == "Bear"`
3. `sub_regime == "hot"` (i.e., `feat_nifty_vol_percentile_20d > 0.70 AND feat_nifty_60d_return_pct < -0.10` per `_validate_paths.py:bear_subregime`, using the corrected `feat_nifty_vol_percentile_20d` from the vp-leakage-fix branch)

There is no sector restriction. All 188 universe symbols are eligible.

### 4.3 kill_001 sectoral distress diagnostic

Per the rule definition (kill_001 is one of the 5 SURVIVOR rules from W3):

```
match_fields: regime=Bear, sector=Bank, signal=DOWN_TRI
verdict: REJECT (per rule schema)
```

**Why kill_001 cannot directly filter rule_019 candidates**: kill_001's match conditions
(Bear + Bank + DOWN_TRI) do not overlap with rule_019's match conditions (Bear + UP_TRI).
The same symbol on the same scan day cannot carry both UP_TRI and DOWN_TRI signal types
simultaneously. So kill_001 is NOT a direct row-level filter on rule_019 candidates.

**What kill_001 IS in shadow**: a sectoral distress diagnostic. When kill_001 fires
heavily on a scan day (multiple Bank-DOWN_TRI matches across the universe), that
indicates broad bank-sector selling. Operationally, the operator may decide that
PROPOSED rule_019 cards on the same scan day should be paused — not because
rule_019's audited edge is invalidated by sectoral distress, but as a portfolio-
level risk-management choice.

**Mechanism**: Manual SKIPPED state, NOT auto-suppression.

- Operator inspects `candidate_signals.jsonl` at end of scan.
- Counts kill_001 matches on the day.
- If count exceeds the operator's threshold (operator-defined; not encoded in v1),
  operator skips PROPOSED rule_019 cards by writing `lifecycle_event` records with
  `from_state=PROPOSED`, `to_state=SKIPPED`, `reason="sector_distress_pause"`.
- Operator journal entry parallels the structured reason.

**v1 deliberately does not auto-suppress** — the operator retains agency over portfolio-
level decisions. If discipline shows operators consistently apply the same threshold,
v2 may codify it. See §14.4 for the answered open question.

### 4.4 rule_031 overlay logic

Per Round 10 consultant decision: rule_031 fires alongside rule_019 (every rule_031
match is also a rule_019 match by construction; rule_031 = rule_019 + sector=IT
restriction). The overlay state is binary and per-trade-card:

```
rule_031_confirm = 1  iff  rule_031_match == True for the same scan event
rule_031_confirm = 0  otherwise
```

Logged on the `trade_card` record. NOT used for sizing, NOT used for filtering. Pure
informational logging for end-of-shadow analysis (Section 11).

### 4.5 Scan completeness

A scan is **COMPLETE** if all of:
1. Universe is fully loaded (188 symbols, no missing data feeds).
2. Regime + sub_regime classification computed without errors.
3. Rule matching ran against the full universe.
4. All matching rows generated `candidate_signal` records.
5. Trade cards (PROPOSED) generated for every TRADE_CARD_PROPOSED candidate.

A scan is **PARTIAL** if any of (1)-(5) failed for some symbols but completed for
others. PARTIAL surfaces an alert (Section 9) and the operator decides whether to
discard the scan (run_config marks it as discarded) or accept the partial scan and
flag affected candidates with `scan_status=PARTIAL`.

A scan is **ERROR** if regime/sub_regime classification fails OR fewer than 50% of
universe is loaded. Scan halts; no candidates generated. Alert fires.

---

## 5. Trade Card Lifecycle State Machine

### 5.1 States

| State | Description |
|---|---|
| `PROPOSED` | Candidate signal triggered rule_019 (and not suppressed by manual operator override). Trade card created. Awaiting entry-window evaluation on T+1 through T+3. |
| `ACTIVE` | Hypothetical fill confirmed. Position is "open" in the simulation. Daily price tracking active. |
| `HYPOTHETICAL_FILLED` | Target reached. Trade closed counterfactually with realized R > 0. Terminal state. |
| `HYPOTHETICAL_STOPPED` | Stop reached. Trade closed counterfactually with realized R < 0. Terminal state. |
| `NO_FILL` | PROPOSED never reached ACTIVE within the T+1..T+3 entry window (no breakout above pivot during the 3-day window). Trade card terminates without entry. Terminal state. Distinct from EXPIRED — no position was ever opened. |
| `EXPIRED` | Hold-period elapsed (6 trading days from entry, per existing scanner convention) without target or stop hit. Trade closed at day-6 close. Terminal state. Position was open through full hold window without meaningful exit. |
| `SKIPPED` | Manual operator override (e.g., sectoral distress pause, data quality concern, deliberate skip with documented reason). Trade card never enters ACTIVE. Terminal state. Reason logged. |

NO_FILL and EXPIRED are operationally distinct: NO_FILL means the entry condition never
materialized; EXPIRED means the trade was open and held to time-decay. End-of-shadow
analysis must count them separately because they imply different things about rule
behavior (NO_FILL = pivot/stop placement may be too aggressive; EXPIRED = hold window
may be too short or trades are slow movers).

### 5.2 Valid transitions

```
                       PROPOSED
                    /     |    |     \
                   /      |    |      \
                  /       |    |       \
                 v        v    v        v
              ACTIVE   NO_FILL SKIPPED  (no other PROPOSED-side terminals)
              / | \    (term)  (term)
             /  |  \
            /   |   \
           v    v    v
  HYP_FILLED EXPIRED HYP_STOPPED
   (term)    (term)    (term)
```

| From | To | Trigger |
|---|---|---|
| PROPOSED | ACTIVE | Breakout above pivot occurs on T+1, T+2, or T+3 (open or intraday). Entry simulation §6.2. |
| PROPOSED | NO_FILL | T+3 close reached without breakout above pivot. Terminal — no position ever opened. |
| PROPOSED | SKIPPED | Manual operator override (sector distress, data error, etc.). Reason logged. |
| ACTIVE | HYPOTHETICAL_FILLED | Target reached (gap-up past target OR intraday high ≥ target). Exit simulation §6.3. |
| ACTIVE | HYPOTHETICAL_STOPPED | Stop reached (gap-down past stop OR intraday low ≤ stop). Exit simulation §6.3. |
| ACTIVE | EXPIRED | Day-5 close reached after fill (6-day hold window from fill day inclusive) without target/stop hit. |

### 5.3 Transition timing

- **PROPOSED → {ACTIVE, NO_FILL, SKIPPED}**:
  - ACTIVE / NO_FILL: evaluated daily during the T+1..T+3 entry window. As soon as a
    breakout fires intraday or at open, transition to ACTIVE. If T+3 close passes with
    no breakout, transition to NO_FILL.
  - SKIPPED: any time before terminal, on operator action. Most common timing: same-day
    or T+1 morning, before any fill evaluation.
- **ACTIVE → {HYPOTHETICAL_FILLED, HYPOTHETICAL_STOPPED}**: evaluated daily for each
  ACTIVE card via OHLC check. Gap-fill mechanics in §6.3. Same-day-both-hit defaults to
  stop-priority worst-case (§14.5 answered).
- **ACTIVE → EXPIRED**: forced on fill_date+5 close (day 6 of the hold window) where
  fill_date is the actual day the card transitioned to ACTIVE.

### 5.4 No out-of-band edits

The state machine is the only path. Specifically:

- No editing of past `lifecycle_event` records.
- No deletion of past `trade_card` snapshots.
- No retroactive change of state.
- Corrections (if a logging error is discovered) are made via a NEW `lifecycle_event`
  record with `from_state=<incorrect>`, `to_state=<corrected>`, `reason="correction:
  <description>"`. The full audit trail shows both the original and the correction.
- The git history is the second-layer audit: any non-append-only change to JSONL files
  shows up in git diff and must be explicitly committed with explanation.

### 5.5 Terminal state finality

Once a card reaches a terminal state (`HYPOTHETICAL_FILLED`, `HYPOTHETICAL_STOPPED`,
`NO_FILL`, `EXPIRED`, `SKIPPED`), no further lifecycle events are valid for that card.
Attempting to transition out of a terminal state is an ERROR and triggers an alert.

### 5.6 Day-1 bootstrap

Day 1 of a shadow run is asymmetric. The scan runs and produces PROPOSED trade cards,
but no ACTIVE transitions can occur because:

- Day 1 PROPOSED cards have entry windows starting on T+1, which is Day 2.
- No prior ACTIVE cards exist (this is run start).

Operator should expect, on Day 1:
- `scan_event` recorded (regardless of signal-firing state).
- Possibly some `candidate_signal` records (if rule_019 matches).
- Possibly some `trade_card` records in PROPOSED state.
- Zero `lifecycle_event` records beyond the initial PROPOSED creation.
- Zero `fill_simulation` records.

The first `ACTIVE` transitions, if any, happen on Day 2's scan when Day 1's PROPOSED
cards are evaluated against Day 2's OHLC. The first realized P&L (HYPOTHETICAL_FILLED,
HYPOTHETICAL_STOPPED) earliest possible: Day 3 (intraday on Day 2's fill, evaluated
against Day 3's OHLC at next scan). EXPIRED earliest possible: Day 7 (Day 2 fill + 5
hold days).

Operator journal entry on Day 1 should explicitly note this bootstrap pattern so the
absence of state transitions doesn't trigger false-alarm investigation.

---

## 6. Would-Have-Filled Audit (Counterfactual Simulation)

### 6.1 Purpose

For each PROPOSED trade card, we need to determine whether it would have been filled
in real trading and, if so, what the realized P&L would have been. This is a
**deterministic** simulation given the price data.

### 6.2 Entry simulation (PROPOSED → ACTIVE)

**Entry logic v1: `audit_faithful_t1_open_unconditional`**

Entry is **unconditional at T+1's OPEN price**, mirroring the canonical lab
simulator at `lab/infrastructure/signal_replayer.py:160-162` (`compute_d6_outcome`).
There is no breakout-confirmation check, no T+2/T+3 fallback window.

```
post = symbol_df[symbol_df.index > scan_date]
entry_row = post.iloc[0]                # first post-scan trading day
actual_entry_price = float(entry_row["Open"])
```

The PROPOSED → ACTIVE transition happens whenever the symbol has a post-scan
bar in the cache. If the symbol has no post-scan data, the card stays PROPOSED
and the operator backfills (data_ingest re-run) to advance it.

**The `NO_FILL` state is reserved but not auto-emitted in v1.** Audit-faithful
entry never fails to fill on T+1; NO_FILL is left in the schema for future
operator-override use cases.

**Why audit-faithful (over an arch-doc-original T+1..T+3 breakout window)**:
the audit's calibrated WRs (rule_019 71%, rule_031 68%, kill_001 45%) were
computed by `compute_d6_outcome` using unconditional T+1 OPEN entry. Any
divergence in entry semantics means shadow measures a different policy from
the audit; the WR comparison breaks. Forward operations may want a more
realistic entry simulation (breakout, slippage), but that's a separate
project — not v1's mission.

### 6.3 Exit simulation (ACTIVE → terminal)

**Audit-faithful** — mirrors `signal_replayer.py:182-245` (`compute_d6_outcome`).
Holding window is **6 trading days inclusive (D1 through D6)**: D1 is the
entry day with intraday checks; D2–D5 are intraday checks; D6 is exit at OPEN
if no prior intraday hit.

For each post-scan trading-day bar `d` in `[D1, D6]`:

1. Compute `target_price`:
   - **target = entry_price + 2.0 × (entry_price − stop_price)** for LONG
     (2R reward-to-risk). For SHORT, `entry_price − 2.0 × …`.
   - `entry_price` is the PROPOSED entry (from rule firing), NOT the actual D1
     OPEN. Anchored to the audit's calibration baseline.

2. **Stop-hit check** (no gap-fill in v1):
   - LONG: if `Low[d] ≤ stop_price` → ACTIVE → HYPOTHETICAL_STOPPED with
     exit_price = **`stop_price`** (the literal stop level, even when the bar
     gapped far past it).
   - SHORT: if `High[d] ≥ stop_price` → same.

3. **Target-hit check** (no gap-fill in v1):
   - LONG: if `High[d] ≥ target_price` → ACTIVE → HYPOTHETICAL_FILLED with
     exit_price = **`target_price`** (the literal target level).
   - SHORT: if `Low[d] ≤ target_price` → same.

4. **Same-day both hit**: STOP wins (mirrors canonical loop order at
   `signal_replayer.py:186-222`). Stop is checked before target on each bar.

5. **No hit by D6 intraday**: ACTIVE → **EXPIRED** with exit_price = `Open[D6]`.

**No gap-fill in v1**: stop and target exits ALWAYS occur at the literal limit
price, regardless of how far the bar gapped past it. This is OPTIMISTIC in
gap-against-you scenarios but matches the canonical simulator the audit was
calibrated against. A future v2 may add gap-fill semantics, but it would change
the policy being measured and break audit-WR comparability — out of v1 scope.

### 6.4 Realized P&L computation

Once a card reaches terminal:
```
realized_pnl_pct = (exit_price − entry_price) / entry_price × 100
risk_per_share   = entry_price − stop_price
realized_R       = (exit_price − entry_price) / risk_per_share
```

Logged on the `trade_card` record. Cross-reference: the existing scanner's `pnl_pct`
column for historical signals computes the same formula; v1 must be byte-equivalent
for backtested signals to ensure forward consistency.

### 6.5 Price data source

Per §14.17 Option B resolution, shadow_ops owns its data flow end-to-end. A
`shadow_ops/data_ingest.py` module is the FIRST step of each daily scan and
refreshes the price data shadow consumes:

- **Symbol prices**: `shadow_ops/data_ingest.py` downloads daily yfinance OHLC for
  the 188-symbol universe and writes `lab/cache/<SYMBOL>_NS.parquet`. Refresh runs
  as the first step of each daily scan, before regime classification or rule
  evaluation.
- **Index prices**: same module updates `lab/cache/_index_NSEI.parquet` daily
  (Nifty), used by `lab/infrastructure/feature_extractor.py:_nifty_vol_percentile_at`
  for the regime/sub_regime classification.
- **Data freshness check**: at scan start, after data_ingest completes, verify
  every parquet has today's date as its latest timestamp. For any symbol where
  yfinance fetch failed: log WARNING per §9 and skip that symbol's evaluation for
  the day. Other symbols proceed.
- **lab/cache/*.parquet is gitignored**: `lab/cache/` is not committed to the
  repo. First-time campaign setup requires running
  `python -m shadow_ops.data_ingest` to populate the cache before
  `pre_scan_check.cache_freshness` (Step 9) will pass. Subsequent daily scans
  refresh incrementally.

**Cross-workstream note**: shadow's data_ingest also benefits any future re-
extraction work (Path B replay, periodic audit refresh, etc.) by keeping
`lab/cache/` continuously current. This is a side effect, not a shadow-ops
purpose; downstream consumers should not depend on shadow's schedule.

### 6.6 Slippage vs gap-fill: distinction

**Gap-fill mechanics**: NOT applied in v1 (per §6.3). Stop and target exits
happen at the literal limit price regardless of where the bar opened. This
matches the canonical simulator the audit was calibrated against.

**Slippage** (separate concept, also NOT applied in v1):
- **v1**: zero slippage AND zero gap-fill. Exit price is always the literal
  stop/target level for intraday hits, or the D6 OPEN for expirations. No
  bps adjustment, no bid-ask widening, no adverse-tick assumption.
- **v2 candidate**: configurable slippage in basis points + gap-fill semantics,
  applied as a post-processing pass on top of the audit-faithful exits.
  Surfaced for end-of-shadow review only; not actionable in v1.

Rationale: v1 is a process validation against the audit's calibration. Adding
slippage or gap-fill changes the policy being measured and breaks audit-WR
comparability. Real-trading slippage will be empirically measured during a
future paper-trading phase, separate workstream.

### 6.7 Determinism

The simulation is deterministic given:
- The symbol price parquets at scan time (referenced by `data_source_sha256`).
- The entry/exit logic version (referenced by `run_config.entry_logic`).
- The slippage assumption (`run_config.slippage_bps`).

Any later auditor can re-run the simulation against the logged inputs and verify
identical outputs.

---

## 7. No-Modification Discipline

### 7.1 Append-only by file format

- All event-class files (`*.jsonl`) are written via `open(path, "a")`. No process
  writes ever overwrite a file.
- The `trade_card.jsonl` file is the exception: it is the materialized read-model
  derived from `lifecycle_event.jsonl`. It is regenerated end-of-day from the
  authoritative log. The lifecycle log is append-only; the materialized read-model
  is rebuildable.

### 7.2 Code-level enforcement (proposed)

- Writer functions accept events via a typed `Event` dataclass and refuse to write
  if the event's `event_id` already exists in the corresponding file. (`event_id` is
  required, unique per event.)
- A startup check at each scan verifies file integrity: each line is valid JSON;
  `event_id`s are unique within file; no line has been edited (compare line count
  + last 10 lines hash to a sidecar `.checksum` file updated only by the writer).

### 7.3 Git as second-layer audit

- The `shadow_ops/runs/<run_id>/` directory is git-tracked.
- Daily scans trigger a commit with message `shadow_ops: <run_id> daily scan
  YYYY-MM-DD`. The commit captures all new event records as a delta.
- Any modification to a past record shows up in git diff. Such modifications are
  forbidden by the daily-scan code; if they appear, they came from outside the
  scan code (operator manual edit), which is a discipline violation logged in the
  end-of-shadow review.
- `git log --oneline` on the shadow_ops_v1 branch produces a per-day audit trail.

### 7.4 Operator overrides

The only legitimate human intervention in trade card state is via SKIPPED state:

- Operator decides to skip a PROPOSED card (e.g., portfolio-level kill_001 pause,
  data quality concern, deliberate override for a documented reason).
- Operator records a `lifecycle_event` with `from_state=PROPOSED`, `to_state=SKIPPED`,
  `reason="<specific reason>"`.
- Operator ALSO writes a parallel entry in `operator_journal.md` with timestamp and
  fuller commentary.
- The daily scan respects the SKIPPED state and never moves a SKIPPED card forward.

NO discretionary override is allowed for ACTIVE cards. Once a card is ACTIVE,
the lifecycle proceeds deterministically per the simulation. The operator cannot
"close early" or "let it run past day 6." Doing so is a discipline violation and
voids that card's data point.

### 7.5 Filesystem permissions (proposed §14)

- The `shadow_ops/runs/<run_id>/` directory could be made read-only between scan
  runs at the OS level (chmod 444). Daily scan would temporarily chmod 644 to
  append, then chmod back. Operator manual edits would require explicit chmod.
- Alternative: rely on git + code-level checks. Lighter-weight; less robust
  against operator carelessness.

Default v1: code-level + git audit, no chmod automation. Operator discipline
expected. If discipline violations surface in the first shadow run, escalate to
chmod-based locking in v2.

---

## 8. Behavioral Discipline Checks

### 8.1 What "discretionary drift" means (per Round 9)

Discretionary drift is any operator behavior that deviates from the rule book in
ways not explicitly documented and structurally allowed. Specific examples:

- **Boredom trades**: operator takes a position not generated by rule_019 because
  no signals have fired in 2 weeks and the operator "feels" something. Even if
  hypothetical (no capital), this contaminates shadow as a process validator.
- **Override creep**: operator skips PROPOSED cards based on private analysis,
  not the structured rule criteria. The skip rate becomes a measure of drift.
- **Sizing drift**: operator imagines or notes "I would have gone double size on
  this one" — even speculatively, this is sizing logic outside the rule and must
  be banned in shadow (where sizing is uniform per the rule).
- **Hold drift**: operator imagines exiting earlier than the rule's stop/target
  because of news flow, intraday volatility, etc.
- **Universe drift**: operator scans symbols outside the 188-stock universe.

### 8.2 Logged-reason discipline

Every SKIP transition has a `reason` field in the lifecycle event AND a parallel
operator journal entry. Reasons fall into categorized buckets:
- `data_error`: bad price data, missing fundamentals, symbol delisted.
- `kill_001_filter`: scan-day Bank-DOWN_TRI sectoral distress (operator decision).
- `discretionary`: operator override outside the structured filters. THIS IS THE
  COUNT THAT MATTERS for discipline assessment.
- `correction`: undoing an erroneously-logged event (logged separately, very rare).

### 8.3 Daily review checklist

Each trading day, the operator runs through:
1. Did the scan run? Status OK?
2. Are all expected `candidate_signal` records present in JSONL?
3. Are any SKIP transitions today? If `discretionary`, what's the reason in the
   journal?
4. Are any ACTIVE cards transitioning to terminal today? Verify by hand against
   OHLC data that the simulation is correct.
5. Update the journal with end-of-day observations.

This checklist becomes a structured form (proposed: `daily_checklist_<date>.md`
in the run directory) that the operator fills in. Not auto-generated; the act of
filling it in is part of the discipline.

### 8.4 End-of-shadow discipline review

At day 30 (or end of extended period), a structured retrospective:

- **Discretionary skip rate**: count(SKIPPED with reason=discretionary) /
  count(PROPOSED). Target: zero. Tolerance: TBD.
- **Override patterns**: were there clusters of skips (e.g., always skip pharma)?
  Identify whether the rule book has an implicit gap.
- **Boredom signal**: how many days of zero signal activity? Did the operator log
  comments suggesting the idleness was hard?
- **Journal completeness**: every day has a journal entry? Or did the discipline
  lapse during quiet periods?
- **Lifecycle anomalies**: any cards with state-machine violations that required
  correction events?

The output of this review is a markdown report (`end_of_shadow_review.md`) that
becomes part of the next architecture conversation.

---

## 9. Alerts & Operational Integrity

### 9.1 Alert classes

- **CRITICAL**: scan failed, regime classification errored, missing core data.
  Action: human review same-day. Possibly halt subsequent scans until resolved.
- **WARNING**: PARTIAL scan, stale data, lifecycle anomaly. Action: log, review
  next day.
- **INFO**: end-of-day summary, ACTIVE cards count, etc. Standard operational
  visibility.

### 9.2 Alert delivery (proposed §14)

v1: alerts written to `shadow_ops/runs/<run_id>/alerts.jsonl` with severity tags
AND printed to stdout. Operator reviews `alerts.jsonl` at start of each daily
session.

Alternatives (v2 or later): email, Slack, push notification. Not in v1.

### 9.3 Daily smoke test

Each scan, after writing all expected events, runs a smoke test:
1. Did `scan_event` get written?
2. Number of `candidate_signal` records ≥ 0 (plus expected ≥ 0 if regime active).
3. All ACTIVE cards from previous day have a fresh `lifecycle_event` evaluating
   their state today (transition or no-transition checked).
4. JSONL files all parse as valid line-delimited JSON.
5. `event_id`s are unique within and across the day.
6. Materialized `trade_card.jsonl` matches the lifecycle log derivation.

Smoke test failure → CRITICAL alert.

### 9.4 Data feed dependency

If the EOD signal scanner (existing `scanner/` infrastructure) hasn't produced
today's signals by scan time, shadow waits up to 30 minutes then fires CRITICAL
alert and skips the day. Operator must investigate.

If a single symbol's OHLC parquet is stale (most recent date < scan_date), alert
WARNING and skip that symbol's evaluation for the day. Other symbols proceed.

---

## 10. Shadow-to-Live Transition Criteria (per Round 9)

### 10.1 Operational integrity

- **Triggers unambiguous**: every scan day, rule matches are deterministic given
  the input data. Re-running the scan against the same inputs produces byte-identical
  outputs.
- **Lifecycle clean**: no state-machine violations across the run. Zero correction
  events. Zero stuck cards.
- **No module surprises**: no unexpected interactions between rule_019, kill_001,
  rule_031 overlay, regime classifier, and price data feeds.

Concrete day-31 inspection:
- Open `lifecycle_event.jsonl`. Count: every state transition is valid per §5.2.
- Check `correction` events: count == 0.
- Re-derive `trade_card.jsonl` from `lifecycle_event.jsonl`. Compare to materialized
  file. Diff is zero.

### 10.2 Behavioral discipline

- **No discretionary overrides**: count(SKIPPED with reason=discretionary) == 0.
- **No boredom trades**: zero entries in `operator_journal.md` describing speculative
  positions outside rule_019.
- **No drift**: end-of-shadow journal review shows the operator's mental model
  remained anchored to the rule book throughout.

Concrete day-31 inspection:
- Read full `operator_journal.md` end-to-end. Look for warning signs: language
  about "I almost", "would have", "considered", outside the structured framework.
- Tally SKIPPED reasons. Discretionary == 0.

### 10.3 Process-fit

- **Idle tolerable**: extended periods of zero signal did not break operator
  discipline. Operator continued running daily scans, filling journal, even on
  zero-signal days.
- **Signal rarity acceptable**: 0–4 trades over 30 days didn't surface as a
  fundamental fit problem. (If it did, this is exactly the business-model-mismatch
  surfacing that consultant Round 9 named.)

Concrete day-31 inspection:
- Count days of journal activity. Should equal trading days in the period.
- Read journal for evidence of distress about signal absence.
- Quantify: total days, trading days, scan-completed days, signal-firing days,
  trade-card-active days.

### 10.4 No negative surprise

- **No structurally inconsistent rule behavior**: rule_019 fires according to its
  audited match logic. Per-trade behavior (entry, hold, exit) matches the
  expectation set by Phase 3 audits.
- **No data quality surprises**: corp-action events affecting active cards are
  documented and handled (or surfaced as gaps in the v1 design).
- **Realized R distribution**: trade outcomes (where any exist) cluster within the
  range expected from Phase 3 audits — not necessarily statistically equal (sample
  too small) but qualitatively consistent.

Concrete day-31 inspection:
- For every terminal trade card, manually re-check the entry/stop/target prices
  against the price data. Verify the simulation logic.
- Cross-check rule_019 firing days against the audit's window-firing pattern (rule
  fired in 22 of 182 windows historically; in shadow, did it fire at a similar
  rate adjusted for the period?).

### 10.5 NOT a statistical edge threshold

Per consultant Round 9: 30 days will likely produce 0–4 trades. Any "edge"
inference from this sample is statistically meaningless. Shadow-to-live is gated
on the four criteria above, NOT on shadow P&L being positive.

If shadow shows process-validated AND every trade card was a stop-out, the
process is still validated; the operator faced bad luck or genuine regime shift.
Move forward to next-stage architecture conversation regardless of P&L sign.

If shadow shows process-failed (any of the four criteria fails), do NOT proceed
to live capital regardless of P&L sign. Even +20R shadow performance with
discipline failures is not deployable.

---

## 11. rule_031 Confirmation Overlay Design (per Round 10)

### 11.1 Mechanism

Per Round 10 consultant decision: rule_031's firing is logged on each trade card
but does NOT influence sizing, filtering, or any decision in v1. The overlay state
is informational.

```
trade_card.rule_031_confirm = 1  if  rule_031_match == True for the same scan event
trade_card.rule_031_confirm = 0  otherwise
```

By construction, rule_031's match conditions are a strict subset of rule_019's
(rule_031 = rule_019 + sector=IT). So rule_031_confirm == 1 implies sector=IT;
rule_031_confirm == 0 implies sector ≠ IT.

In shadow, rule_031_confirm == 1 will only fire on Bear+UP_TRI+hot+IT scan rows.
Audit 6 ranked IT 5th of 13 sectors by lift, so we expect rule_031_confirm == 1
to be uncommon.

### 11.2 Metrics tracked per trade card (logged for end-of-shadow comparison)

Every terminal trade card has all the following logged:

- **rule_031_confirm**: 0 or 1 (binary)
- **realized_R**: the trade's risk-adjusted return
- **realized_pnl_pct**: raw return percent
- **time_to_terminal_days**: days from fill to terminal state
- **adverse_excursion_pct**: max drawdown during ACTIVE phase
- **stop_distance_at_entry_pct**: (entry_price - stop_price) / entry_price
- **target_distance_at_entry_pct**: (target_price - entry_price) / entry_price
- **terminal_state**: HYPOTHETICAL_FILLED | HYPOTHETICAL_STOPPED | NO_FILL | EXPIRED | SKIPPED

### 11.3 End-of-shadow comparison (logged for analysis, NOT acted upon)

At end-of-shadow, segment all terminal trade cards into two groups:
- Group A: rule_031_confirm == 1 (rule_031 also fired; trade is on an IT-sector symbol)
- Group B: rule_031_confirm == 0 (only rule_019 fired; trade is on non-IT symbol)

Compute distributions for each metric in §11.2 within each group. Shadow's small
sample size means neither group will produce statistically-significant differences;
the comparison is qualitative trend identification only.

The output is a section in `end_of_shadow_review.md` titled "rule_031 Overlay
Observations" that reports both group's distributions side by side. No decision is
made from this. The data informs the consultant Round 11+ conversation about
whether rule_031 should be promoted to a live confirmation overlay (which would
require its own audit cycle separate from shadow ops).

### 11.4 What is explicitly NOT done with rule_031 in v1

- **No sizing differentiation**: every trade card is the same hypothetical "size"
  (sizing isn't real in shadow anyway).
- **No filtering**: rule_031_confirm == 0 cards are not skipped or de-prioritized.
- **No alert generation**: rule_031 firing or not firing produces no operational
  alert.
- **No live signal**: rule_031 candidates that don't accompany rule_019 fires are
  logged in `candidate_signal` records (with disposition=RULE_031_OVERLAY_ONLY)
  but never produce trade cards.

---

## 12. Out of Scope for v1

Explicitly NOT in shadow ops v1:

- **Live capital deployment** of any kind.
- **Real broker orders** (zerodha, IBKR, anything).
- **Order management system** integration.
- **Position management** beyond the simulated state machine.
- **Real-time data feeds** beyond daily EOD.
- **Intraday alerting** for active cards.
- **rule_031 used as live sizing input** (per Round 10).
- **Bull regime rules** — zero deployable.
- **Choppy regime rules** — zero deployable plus 6 dead schema.
- **Other Bear sub_regime rules** beyond rule_019 and kill_001 + the rule_031 overlay.
- **Sector specialization rules beyond IT** — Audit 6 surfaced Chem/Auto/FMCG/Other
  candidates. Not in v1; deferred to Path B replay workstream.
- **Multi-portfolio coordination** (multiple shadow runs in parallel for different
  rule sets).
- **Tax-aware accounting** of hypothetical P&L.
- **Risk overlay** (max-drawdown circuit breakers, position correlation limits).
- **User interface** beyond CLI + markdown reports + JSONL files.
- **External notifications** beyond CLI stdout.
- **Performance attribution** beyond per-card R logging.

---

## 13. Validation Criteria — How We Know Shadow Is Working

### 13.1 Daily

- Scan ran without errors (status OK or PARTIAL with explanation).
- Expected event records exist in JSONL files.
- Smoke test passes.
- Operator journal entry exists for the day.

### 13.2 Weekly (every 7 trading days)

- Trade card lifecycle review: walk through every active and terminal card from
  the past 7 days. Verify state transitions match the state machine. Verify
  exit price matches OHLC simulation logic.
- Any anomalies surfaced? Any cards in states they shouldn't be?
- Operator journal completeness: every trading day has an entry?
- Discipline check: any discretionary skips? Any drift language?

### 13.3 End-of-shadow (day 30+)

Comprehensive audit per consultant Round 10 framework:

- All four shadow-to-live criteria evaluated (Section 10).
- rule_031 overlay observations report (Section 11.3).
- End-of-shadow review document drafted, including:
  - Total scans run, OK rate.
  - Total trade cards: PROPOSED count, terminal state distribution.
  - Per-card R distribution.
  - Discretionary skip count.
  - Operator self-assessment.
  - Any open questions for consultant Round 11+.

### 13.4 Non-validation outcomes

- **Process-failed**: write a structured failure report (`process_failure_report.md`)
  identifying which of the four criteria failed and which root cause. Workstream
  pauses for redesign.
- **Process-undertraded** (zero or 1 trade card in 30 days): extend window to 60 days.
  If still undertraded, shift to shadow-paused state and surface the rarity-impact
  business audit (consultant Round 10 priority #3) as the active workstream.

### 13.5 Shadow run termination procedure

End of shadow is a **deliberate operator act**, not implicit at day 30. Termination
runs through a structured close-out script (`shadow_ops_end_run.py` or equivalent
implementation) that captures the run's final state in immutable form.

**Triggers for termination**:
1. Day 30+ reached, all four shadow-to-live criteria evaluated (operator-driven).
2. Process-failed outcome at any point (failure report drafted, run terminates early).
3. Process-undertraded after day 60 (rarity outcome, run terminates undertraded).
4. Operator explicitly aborts run (rare; logged as terminated_early with reason).

**Termination script actions**:
1. Append a final entry to `run_config.json` with:
   - `ended_utc`: timestamp of termination.
   - `termination_reason`: one of {completed_day_30, process_failed, undertraded_day_60,
     operator_abort}.
   - `termination_outcome`: PROCESS-VALIDATED | PROCESS-FAILED | PROCESS-UNDERTRADED.
2. Generate `summary.md` containing all stats per §13.3:
   - Total scans run; OK rate; PARTIAL/ERROR counts.
   - Total trade cards by terminal state (HYPOTHETICAL_FILLED, HYPOTHETICAL_STOPPED,
     NO_FILL, EXPIRED, SKIPPED).
   - Per-card R distribution (if any terminal cards exist).
   - Discretionary skip count (and breakdown by reason category).
   - Operator self-assessment summary lifted from journal end-section.
3. Generate `end_of_shadow_review.md` template with the four shadow-to-live-criteria
   sections from §10 pre-populated as headers + concrete day-31 inspection checklists.
   Operator fills these in by hand as the human-deliberation portion of the close-out.
4. Generate `rule_031_overlay_observations.md` per §11.3 — Group A/B distributions
   side-by-side.
5. Run a final integrity check: re-derive `trade_cards.jsonl` from `lifecycle_events.jsonl`
   and confirm zero diff.
6. Trigger a final commit on the shadow_ops_v1 branch with message
   `shadow_ops: <run_id> terminated — <outcome>`. The commit includes summary.md,
   end_of_shadow_review.md template, run_config.json final state.
7. Optionally `chmod 444` the run directory (operator decision; v1 default skip).

After termination, the run directory is **immutable in policy**. Any further
modification requires explicit operator decision documented in a separate followup
markdown file in the run directory; the modification itself is logged as a new
correction entry, not as an in-place edit.

---

## 14. Open Design Questions — Status

15 of 17 answered (post-review). 2 deferred pending verification.

### 14.1 Daily scan timing — **APPROVED**

**Resolution**: post-market T scan (after 16:00 IST). Hypothetical T+1 fill simulated
when next day's data arrives. 2-step daily flow: post-market scan day T, fill
evaluation day T+1 morning.

### 14.2 Storage location of shadow run data — **APPROVED**

**Resolution**: `shadow_ops/runs/` at repo root, git-tracked. Daily commits.

If shadow runs become routine, a cumulative-size policy may emerge in v2.

### 14.3 Trade card rendering format for operator — **APPROVED**

**Resolution**: option (b). Daily `trade_cards_<date>.md` markdown summary table,
regenerated each scan.

### 14.4 kill_001 auto-suppression semantics — **APPROVED (no auto-suppression)**

**Resolution**: log only; no auto-suppression. Reframed in §4.3: kill_001 cannot
directly suppress rule_019 candidates because their match conditions don't overlap.
Manual operator decision via SKIPPED state with `reason=sector_distress_pause` if
Bank-DOWN_TRI cluster fires. Document operator threshold in journal; do not encode
in v1.

### 14.5 Stop/target same-day priority — **APPROVED (with gap-fill mechanics, see §6.3)**

**Resolution**: stop-priority worst-case. Updated §6.3 with gap-fill mechanics: stop
fills at gap-down open if Open ≤ stop, else at exact stop level. Target fills at gap-
up open if Open ≥ target, else at exact target level. Same-day-both-hit applies
gap-fill to the stop side (worst-case).

### 14.6 Entry window — **REJECTED default → T+1..T+3 window**

**Resolution**: original T+1-only default rejected as too restrictive. Updated §6.2:
entry window is T+1, T+2, or T+3. If breakout occurs intraday (High[d] ≥ pivot) on
any of these days, fill at pivot. If gap-up at open, fill at open. After T+3 close
without breakout: PROPOSED → NO_FILL (terminal).

Mirrors how real traders evaluate breakout entries and matches the existing
scanner's `entry_date` flexibility.

### 14.7 R-target multiple — **ANSWERED — 2R (NOT 1.5R)**

**Resolution**: target = entry + 2.0 × (entry − stop). Verified against the codebase:

- `scanner/main.py:427`: `target = round(entry + 2 * risk, 2)` (LONG) — main scanner
  pipeline.
- `scanner/main.py:429`: `target = round(entry - 2 * risk, 2)` (SHORT) — main scanner
  pipeline.
- `lab/analyses/inv_010_runner.py:20`: explicit 2:1 RR comment for long signals.
- `lab/analyses/inv_013_runner.py:255`: `target_a = entry_price - 2 * R` for SHORT.

The 1.5R found in `scanner/contra_tracker.py:135` (`rr_ratio: 1.5`) is for a separate
"contra" feature path that does NOT produce the audit dataset's signals. The
historical signal-extraction pipeline behind `enriched_signals.parquet` used 2R;
forward shadow MUST use 2R for consistency with the audited rule library.

§6.3 updated to use 2R. Architecture doc's original 1.5R default was wrong; corrected.

### 14.8 Filesystem permissions for tamper-evidence — **APPROVED**

**Resolution**: no automated chmod. Rely on code-level checks + git audit trail.
If discipline violations surface in run 1, escalate to chmod-based locking in v2.

### 14.9 Operator journal cadence — **APPROVED**

**Resolution**: daily mandatory (every trading day, including zero-signal days).
The discipline of journaling on quiet days is itself a process check.

### 14.10 Alert delivery mechanism — **APPROVED + pre_scan_check addition**

**Resolution**: `alerts.jsonl` + stdout for v1. Email/Slack out of scope.

**Addition (per review)**: a `pre_scan_check.py` script (v1 inclusion, not deferred to
v1.1) that flags unreviewed alerts before the next scan can run. Lightweight; runs
at start of each daily session. If unreviewed alerts exist, scan blocks until
operator marks them reviewed (manual flag in `alerts.jsonl` or a sidecar
`alerts_reviewed.jsonl`).

### 14.11 Code location — **APPROVED**

**Resolution**: `shadow_ops/` at repo root. Parallel to `scanner/`, `lab/`. Reasoning:
shadow ops is a parallel runtime concern, not research lab (`lab/`) and not part of
production signal scanner (`scanner/`).

### 14.12 Shadow run identifier convention — **APPROVED**

**Resolution**: `YYYY-MM-DD_label` format. E.g., `2026-05-06_v1_initial`. Human-
readable, sortable by date.

### 14.13 What if rule_019 doesn't fire at all in 30 days — **APPROVED**

**Resolution**: extend to 60 days. If still no fire, terminate as "process-
undertraded" — neither validated nor failed. Surfaces the business-model-mismatch
concern named by Round 9 as the active workstream.

### 14.14 Multiple shadow runs simultaneously — **APPROVED (NO in v1)**

**Resolution**: v1 supports a single active run at a time. Parallel runs would split
operator attention and contaminate the discipline check. Future: v2 may support with
separate operator per run.

### 14.15 What gets logged in scan_event when no rule fires — **APPROVED**

**Resolution**: always log `scan_event` per scan, with `n_signals_post_filter = 0`
if no rules fired. Presence of zero-signal scan_events is part of the audit trail
(proves the scan ran).

### 14.16 Calendar vs trading days for hold window — **APPROVED**

**Resolution**: trading days. Hold window is exactly 5 trading days from fill.
Weekends and holidays don't count toward the 6-day window. Matches existing
`exit_day` convention.

### 14.17 Day-2+ regime classification — **RESOLVED — Option B (self-contained)**

**Recon finding (refined post-Step-2 implementation)**: `scanner/` and
`lab/factory/` **share scanner's slope/EMA50 regime classifier**; lab/'s
`add_derived_features` treats `regime` as a passthrough INPUT and adds
`sub_regime` (hot/warm/cold) on top. The two pipelines were not "structurally
different classifiers" — they were a single classifier with a sub_regime
extension layered on by lab/.

- `scanner/main.py:267-317` + `scanner/scanner_core.py:133-149`: produces
  `regime` (Bull/Bear/Choppy) via EMA50 slope + above/below. No sub_regime.
  Uses yfinance directly.
- `lab/factory/opus_iteration/_validate_paths.py:add_derived_features`:
  consumes `regime` from upstream input, computes `sub_regime` (hot/warm/cold)
  using `feat_nifty_vol_percentile_20d` + `feat_nifty_60d_return_pct` +
  breadth. Does not recompute regime.
- rule_019 fires on `Bear AND UP_TRI AND sub_regime=hot`.

For shadow ops's forward operation, the implication is: shadow needs to
produce both `regime` (mirror scanner's slope/EMA50 logic) and `sub_regime`
(invoke `add_derived_features`). The pre-recon framing of "restart scanner
OR duplicate features" doesn't fit the actual layering — see resolution
below.

**RESOLUTION: Option B (self-contained shadow with own feature extraction)**

- `shadow_ops/` imports `lab/infrastructure/feature_extractor.py:FeatureExtractor`
  (the post-vp-fix code at `vp-leakage-fix` branch HEAD `ae519fb6`) and
  `lab/factory/opus_iteration/_validate_paths.py:add_derived_features`.
  These are the canonical sources; shadow MUST NOT duplicate or fork the code.
- `shadow_ops/data_ingest.py` downloads yfinance daily for the 188-symbol universe,
  writes `lab/cache/<SYMBOL>_NS.parquet` (also updates `_index_NSEI.parquet`).
- `shadow_ops/regime_classifier.py` runs FeatureExtractor on today's data and
  computes sub_regime via `add_derived_features`.
- Shadow's regime classification is bit-for-bit identical to the audit pipeline.
- scanner/ restart is decoupled from shadow ops — separate workstream.

**Tradeoffs accepted**:
- +50–100 lines for `data_ingest.py`.
- +50 lines wrapping FeatureExtractor for daily-incremental computation.
- Shadow owns its own data flow; full traceability.
- Refreshing `lab/cache/` as side effect benefits any future re-extraction work
  (Path B replay, periodic audit refresh).

**Cross-workstream implication (out of shadow ops scope, surfaced for Round 11+)**:
The discovery that scanner/ uses a structurally different regime classifier than
the audit pipeline is itself a finding. scanner/'s outputs currently feed bridge
composers, Telegram alerts, and the PWA UI — meaning those downstream consumers
operate on a regime classification semantically different from the audited rule
library's. Whether scanner/ and the audit pipeline should be reconciled (and if
so, in which direction) is a separate question for consultant Round 11+. This is
flagged here for traceability; not in shadow ops scope.

---

## 15. Approval Checklist (pre-implementation)

This document is APPROVED for implementation when:

1. Sections 1-13 read by operator + reviewer with no fundamental objections.
2. All open questions in Section 14 are either answered or explicitly deferred to v2.
3. The four shadow-to-live criteria (Section 10) are accepted as the gating decision
   framework.
4. The data model schemas (Section 3.3) are accepted as the field set.
5. The state machine (Section 5) is accepted as the only path for trade card
   transitions.
6. The would-have-filled simulation logic (Section 6) is accepted with R-multiple
   and entry-window questions resolved.

After approval, implementation proceeds in this order (revised per §14.17 Option B
resolution — first 2 steps now data-flow before any logging code):

1. **`shadow_ops/` skeleton + `data_ingest.py`** — yfinance daily refresh writing
   `lab/cache/<SYMBOL>_NS.parquet` for the 188-symbol universe + `_index_NSEI.parquet`.
   Idempotent; safe to re-run on the same date.
2. **`shadow_ops/regime_classifier.py`** — wraps `lab/infrastructure/feature_extractor.py:FeatureExtractor`
   + `lab/factory/opus_iteration/_validate_paths.py:add_derived_features` for daily-incremental
   feature + sub_regime computation. IMPORTS canonical code; never duplicates or forks.
3. **Schema validation + JSONL writer**: dataclass / JSON schema for each event type
   per §3.3, basic append-only writer with event_id-uniqueness check.
4. **Daily scan harness**: orchestrates data_ingest → regime_classifier → rule logic
   → JSONL event writes (`scan_event` + `candidate_signal` records).
5. **Trade card lifecycle**: create PROPOSED, evaluate state transitions per §5,
   write `lifecycle_event` records. Includes T+1..T+3 entry window evaluation.
6. **Counterfactual fill simulation**: read OHLC from refreshed `lab/cache/`,
   compute fills per §6.3 with gap-fill mechanics, write `fill_simulation` events.
7. **Materialized read-model**: regenerate `trade_cards.jsonl` from lifecycle log
   (rebuildable view, NOT source of truth).
8. **Operator-facing daily report**: generate `trade_cards_<date>.md` summary
   (markdown table, per §14.3).
9. **Smoke tests + alerts**: per §9, including `pre_scan_check.py` script that
   blocks scan if unreviewed alerts exist (per §14.10 v1 inclusion).
10. **End-of-shadow review template + termination script** per §13.5.
11. **First shadow run**: 30 days minimum, extends to 60 if undertraded.

**Strict no-fork policy**: shadow_ops imports `FeatureExtractor` and
`add_derived_features` directly from their canonical locations. Forking these into
`shadow_ops/` would defeat the whole point — shadow must validate the audited
pipeline, not a copy of it. If the canonical code changes, shadow inherits the
change immediately on next scan.

---

## 16. References

- **Consultant Round 9**: `doc/consultant_briefings/round_09_phase3_vp_fix.pdf` (in
  this branch since commit ae519fb6).
- **Consultant Round 10**: `doc/consultant_briefings/round_10_rule031_supplement.pdf`.
- **Phase 3 audit chain (rule_019)**: `backtest-lab` branch, commits `de01457d`
  through `7ed2d98d`.
- **vp leakage fix**: `vp-leakage-fix` branch, commit `e8395f95`.
- **rule_031 audit chain**: `rule_031_audit` branch, commits `e0b35cf0` through
  `c87d70a8`. Audit 6 (sector concentration) is the FAIL determining rule_031's
  shadow-only confirmation-overlay role.
- **Rule definitions**: `lab/factory/step5_finalization/L4_opus_output/unified_rules_v4_1_FINAL.json`.
- **Walk-forward harness**: `lab/factory/oos_validation/walkforward.py`.
- **Sub_regime computation**: `lab/factory/opus_iteration/_validate_paths.py:add_derived_features`.

---

**End of architecture doc.**

Status: DRAFT, awaiting review. No implementation begun. Branch shadow_ops_v1
remains at the working-tree state with this document as the only addition.
