# TIE TIY 2.0 — Master Design (Decision-Ready)

Generated 2026-05-13 on `main` branch (production). Sub-reports 01-07 carry the detailed designs.

---

## 1. Executive summary

TIE TIY 2.0 is a **plug-in architecture refactor** of an already-working production system. The scanner pipeline, brain layer, and bridge composers are operationally excellent (verified: brain has been firing nightly since 2026-04-28, 9 days of history files, last run 2026-05-12 generated 3 PENDING proposals). The two real gaps are (a) **UI doesn't surface brain proposals so the approval loop never closes** and (b) **adding new signal detectors today requires editing a 38 KB monolithic orchestrator**. 2.0 fixes both: pure-static PWA dashboard with one card per JSON data source, and a `SignalDetector` plug-in protocol that lets new detectors (5 L99 Bull setups + ported existing ones) land as one-file additions instead of orchestrator edits. Brain + bridge port wholesale via adapters. The architectural seam is the registry. The single highest-leverage work — the dashboard — can ship as a 1.0 patch in Week 1, gating the rest of the 2.0 build on demonstrated operational discipline.

---

## 2. Module map (one paragraph each)

**Core (always-loaded):** `core/orchestrator` runs the daily pipeline, loading plug-ins via `core/registry`. `core/journal` owns `signal_history.json` with atomic writes and dated backups. `core/brain` and `core/bridge` are thin adapters that wrap the existing `scanner/brain/` and `scanner/bridge/composers/` code unchanged. `core/data_layer` abstracts yfinance/5paisa; `core/calendar` handles IST + holidays; `core/universe` loads the 188-stock CSV; `core/outcome_evaluator` walks open signals to exits; `core/ipc` provides schema-validated JSON I/O. 

**Plug-ins (registered, optional):** `SignalDetector` is the critical plug-in — each detector (UP_TRI, BULL_PROXY, VCP, EMA20 pullback, Bull flag, Darvas, Cup-handle, rule_019) is a one-class file declaring its name, version, supported_regimes, min_bars, and `detect()` method. `RegimeClassifier` plug-ins (3-state today, 7-state next) declare states and required inputs. `ConfluenceGate` plug-ins (V5 next) carry a mode field (`logged_only` / `veto_only` / `approve_and_veto`) that lets V5 deploy in shadow without orchestrator changes. `ProposalGenerator` sub-plug-ins inside brain (cohort_promote, regime_alert, exposure_warn — all shipped; threshold_tune, kill_proposal, v5_threshold_tuner — new). `UICard` plug-ins each render one JSON file with one refresh strategy.

**Delivery (UI + Telegram):** Pure-static PWA reading `output/*.json` via 5-min polling. Each card is self-contained. APPROVE/REJECT/DEFER/EXPLAIN buttons construct Telegram deep-links — the existing Telegram bot is the action transport. No backend server.

---

## 3. The three most important interface contracts

### SignalDetector (the highest-pain interface)

```python
class SignalDetector(Protocol):
    name: str                       # "vcp", "up_tri", "ema20_pullback"
    version: str
    direction: Literal["LONG", "SHORT", "BOTH"]
    supported_regimes: list[str]    # detector self-declares regime fit
    min_bars: int                   # min OHLCV history required
    config_schema: dict             # JSON schema for tunable params
    
    def detect(
        self, ohlcv, symbol, sector, regime, nifty_close,
        sector_momentum, bar_date, config,
    ) -> list[CandidateSignal]:
        """Pure function. No I/O. Deterministic. Returns 0+ signals with Zones."""
        ...
    
    def validate_config(self, config: dict) -> Optional[str]:
        ...
```

`CandidateSignal` carries `entry_zone / stop_zone / target_zone_1 / target_zone_2` as Zone objects (low/high/anchor/confidence) — **zones, not points, from day 1.** Plus `rationale: dict` for explainability.

### RegimeClassifier

```python
class RegimeClassifier(Protocol):
    name: str
    version: str
    states: list[str]
    required_inputs: list[str]
    
    def classify(self, nifty_ohlcv, india_vix, ad_line, banknifty, as_of_date) -> RegimeLabel: ...
    def explain(self, label) -> str: ...
```

`required_inputs` lets the 3-state classifier register without needing VIX / AD-line data, and the 7-state classifier declare them required and fail registration if data layer can't supply.

### ConfluenceGate

```python
class ConfluenceGate(Protocol):
    name: str
    version: str
    mode: Literal["logged_only", "veto_only", "approve_and_veto"]
    
    def evaluate(self, signal, chart_image_path, regime, config) -> GateDecision: ...
    def calibration_data_dir(self) -> Path: ...
```

The `mode` field is load-bearing. V5 deploys in `logged_only` for the 60-day McNemar calibration window without touching the orchestrator. When calibration completes, a config flip changes mode to `veto_only` — no code change.

---

## 4. Migration approach (1.0 stays up the whole time)

Strategy: parallel `tietiy_2_0` branch, opt-in migration, hard switchover criterion.

| Phase | Weeks | Effort | What's deployable at end |
|---|---|---:|---|
| 1 Foundation | 1-2 | 50h | Registry skeleton; empty (no detectors yet) |
| 2 Detector port | 3-4 | 40h | 2.0 shadow output = 1.0 production output (14-day byte match) |
| 3 Brain/bridge adapter | 5 | 20h | 2.0 brain run = 1.0 brain run |
| 4 UI | 6-7 | 28h | **Dashboard surfaces brain proposals** ← highest-value early ship |
| 5 Validation harness | 8-9 | 48h | First Bull detector passing backtest |
| 6 New Bull detectors | 10-14 | 66h | 5 detectors paper-validated |
| 7 Live cutover | 15 | 20h | 2.0 = production; 1.0 retired |

Switchover criterion: 14 consecutive days where 2.0 shadow output matches 1.0 production output byte-for-byte on ported detectors. Plus ≥10 approval decisions made in `decisions_journal.json` proving the loop works.

Rollback: 1.0 code remains on `main` until cutover succeeds. If regressions detected post-cutover, cron flip reverts to 1.0.

**Critical accelerator: Phase 4 (dashboard) can be done as a 1.0 PATCH in parallel with Phases 1-3, delivering the user-visible win in Week 1.** Recommendation: do it as a 1.0 patch first regardless of the 2.0 decision.

---

## 5. UI architecture summary

Pure-static PWA. 9 UICards: ProposalCard, ExposureCard, RegimeCard, CohortHealthCard, SignalsCard, OutcomesCard, LedgerCard, HealthCard, CaveatsCard. Each polls one `output/*.json` file at 5-min cadence. Buttons construct Telegram deep-links (no new backend). iPad-first layout; mobile single-column; desktop three-column.

**ProposalCard is the critical component:** renders each PENDING proposal with full title + claim + evidence + risks + reversibility + expires_at. APPROVE button → `tg://msg?text=/approve%20{id}`. REJECT button → modal for reason → `tg://msg?text=/reject%20{id}%20{reason}`. EXPLAIN button → `/explain {id}`. User taps, Telegram opens with prefilled command, user sends, existing Telegram bot processes the approval, `mini_scanner_rules.json` updates atomically, `decisions_journal.json` appends, next PWA poll picks up the new state.

**Approval-loop closure verified end-to-end without a backend.** This is the whole point of pure-static.

Total UI effort: 68h. Phase-1 minimum (PWA shell + ProposalCard + ExposureCard + deep-links + push hooks): **28h.**

---

## 6. Self-learning workflow summary

State machine: `[ABSENT] → [PENDING] → [APPROVED|REJECTED|EXPIRED|DEFERRED]`. After APPROVED: `[TRACKING_OUTCOME] → [CONFIRMED|DEMOTION_PROPOSED]` at T+30d. Every state transition is journaled to `decisions_journal.json`; rule changes are committed via git so the history is the audit log.

**The brain learns from three signals:**

1. **Approval frequency by proposal type.** User rejects all `kill_pattern_add` → brain proposes them less aggressively / with stricter thresholds.
2. **Rejection reasons.** Free-form text in `/reject {id} {reason}` — already ingested by `brain_reason.py` via its 90-day decisions_journal lookback during LLM gating.
3. **Post-decision metrics.** At T+30d each approved change is measured; brain proposes demotion if WR regressed >5pp from baseline.

**Safe-to-auto-apply** (cohort metric recompute, log appends, calibration metric updates) needs no proposal. **Always-approval** (rule parameter changes, regime threshold changes, V5 threshold changes, kill/boost additions, tier reassignments) flows through proposal queue. **Never-auto** (new signal types, universe additions, risk-per-trade %, capital changes, plug-in registration) requires manual config/code edit.

Total self-learning closure effort: **~38 hours** (most work is wiring the closure; the brain itself is shipped).

---

## 7. Sequencing recommendation

**Recommended: Phase 1 dashboard patch on 1.0 (Week 1, 28h) → Path A surgical fixes (Week 2, 12h) → Discipline observation window (Weeks 3-6, 0h) → IF gate met, TIE TIY 2.0 incremental build (Weeks 7-20, 290h).**

| Phase | Weeks | Hours | Gate to next phase |
|---|---|---:|---|
| 1. Dashboard 1.0 patch | 1 | 28 | Dashboard rendering proposals |
| 2. Path A surgical fixes | 2 | 12 | Patches deployed; dangerous proposals rejected |
| 3. Discipline observation | 3-6 | 0 (operations only) | ≥10 approval decisions made; ≥80% of nightly digests reviewed; ≥1 approved proposal tracked to T+30d |
| 4. TIE TIY 2.0 incremental build | 7-20 | 290 | 2.0 ships incrementally; cutover at week 20 |

**Total clock: 20 weeks. Total effort: 330 hours.** Time-to-first-value: 1 week (dashboard). Time-to-2.0-deployable: 20 weeks.

If Phase 3 fails (user doesn't close the approval loop in 4 weeks of operating the new dashboard), **2.0 is paused indefinitely.** The architecture is not the problem; the operational gap is. Fixing the architecture more aggressively doesn't help.

---

## 8. Three biggest risks of the design

1. **The "build-but-not-operate" pattern.** Brain layer shipped 2026-04-29 → still has 3 PENDING proposals from that day re-firing nightly with zero approvals. Shadow_ops_v1 shipped 220 commits → never bootstrapped. Foundation-backtest + nuvama-vision validated → never put into operator hands. Hit rate of "built → operated": 1 of 6 prior projects. **TIE TIY 2.0 is on the same trajectory unless Phase 3 explicitly validates operational discipline before Phase 4 begins.** Mitigation: the Phase 3 gate is non-negotiable; if missed, halt build.

2. **Plug-in protocol churn.** Lock the §02 contracts at v1 too early → painful migrations later when an unanticipated detector doesn't fit. Lock them too late → no plug-ins built. Mitigation: lock contracts after Phase 2 ports the existing detectors (UP_TRI / BULL_PROXY / rule_019) successfully. Use the port to surface contract gaps before committing.

3. **Dashboard is the architectural single point of failure.** If the PWA doesn't load on iPad, the user can't approve proposals → loop stays open. Mitigation: keep Telegram bot as full-functionality backup (already in place via `/approve_rule`, `/reject_rule`, `/explain`). Dashboard is the convenience layer; Telegram is the SLA.

---

## 9. Three biggest unknowns that need user input

1. **Hold-time defaults per Bull detector.** L99 says 6-10 days for VCP, 10 for EMA20, 7 for Bull flag, 15 for Darvas, 15 for Cup-handle. Are these correct for NSE F&O on Indian holiday calendar? Or should they be tuned per stock liquidity? Affects every detector's lifecycle config.

2. **Position-sizing per detector.** Today's 1%/3%/5% risk tiers via score buckets are global. Do new detectors share that scale, or each carry their own? Affects `core/scorer` interface design.

3. **Universe filtering per detector.** Should VCP fire on all 188 stocks, or only liquid mega-caps? Darvas was validated on Nifty Midcap 50 per Patil 2024; the universe matters. Affects detector config + backtest result interpretation.

These are not architectural decisions — they are trading-rule decisions the user must own. Architecture supports any answer; the answers must be locked before backtests are meaningful.

---

## 10. Where this design draws from prior work

- **L99 research** (5 Bull setups, 7-state regime, Fib framework, V5 gate, McNemar calibration) → directly encoded in §02 contracts and §07 sequencing.
- **shadow_ops_v1 architecture** → reused as the backtest harness substrate (§06); 70% of its modules generalize, 30% (rule_019-specific bits) don't carry over.
- **Existing brain layer** → preserved wholesale via adapter; brain proposal types extend cleanly.
- **Existing bridge composers** → preserved wholesale via adapter; SDR schema bumps from v1 to v6 with backward-compatible reader.
- **Path A surgical fixes** from prior R1+R2 diagnostics → Phase 2 of the recommended sequence.
- **Round 2 audit of `proposed_rules.json`** → Phase 2 explicit rejection of dangerous broad-scope proposals before any 2.0 ApprovalHandler is live.

---

## Final note on the design itself

This design is **structurally smaller than the user might expect**. It does NOT replace the scanner pipeline. It does NOT replace the brain. It does NOT replace the bridge. It does NOT replace `signal_history.json`. It does NOT introduce a backend server. It does NOT add a new language or framework.

What it adds: a `core/registry`, a `SignalDetector` protocol, a `RegimeClassifier` protocol, a `ConfluenceGate` protocol, a `UICard` protocol, an `OutcomeEvaluator` protocol, and a pure-static dashboard.

What it changes structurally in 1.0: `scanner/main.py` becomes `core/orchestrator` with a registry instead of hardcoded steps; `scanner/scorer.py` becomes parameterized per-detector; `scanner/rule_proposer.py` is retired in favor of LLM-gated `KillProposalGenerator`; `scanner/pattern_miner._build_summary` gets a 5-LOC fix.

That's it. The design is intentionally conservative. The TIE TIY 1.0 system is good enough to keep running daily; what's missing is **closing the approval loop and adding new detectors cleanly.** 2.0 does exactly those two things and nothing more.
