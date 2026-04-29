# Backtest Lab — Discovery Factory for TIE TIY

**Branch:** `backtest-lab` (off `main` at founding commit)
**Founded:** 2026-04-30
**Operational independence:** Lab and main branch evolve separately; main branch live-trading work continues without Lab work blocking it. Promotion is the only path that touches main.

---

## Mission

The Lab is a separate-branch experimental workspace whose sole purpose is **discovering empirically-validated tradeable patterns**. The Lab is fundamentally different from operational TIE TIY (main branch):

| Dimension   | TIE TIY (main)                                          | Backtest Lab (this branch)                  |
|-------------|---------------------------------------------------------|---------------------------------------------|
| Purpose     | Live signal generation + risk management                | Pattern discovery + validation              |
| Cadence     | Daily Mon-Fri (live trading)                            | Investigation-driven (weeks per study)      |
| Data        | Live `signal_history.json` (29 days as of founding 2026-04-30) | Historical OHLC (multi-year backtest) |
| Output      | Trade decisions + Telegram digests                      | Validated pattern database                  |
| Risk        | Real money                                              | Zero (research only)                        |
| Stability   | Production-grade                                        | Experimental                                |
| Promotion   | N/A                                                     | Pattern → main via PROMOTION_PROTOCOL.md    |
| Concurrency | Brain runs nightly; bridge fires 3x/day                 | Investigation runs at trader's discretion   |

The Lab does not generate trade decisions. The Lab generates **rules** (kill / boost / new signal types) that, after passing empirical gates, graduate to main where the live scanner consumes them.

---

## Philosophical Insight: Inverse-Condition Symmetry

Markets exhibit regime-conditional symmetry. If signal X fails in regime Y on cohort Z (e.g., UP_TRI × Bank × Choppy at 27% WR over n=26 resolved), an inverse pattern X' often profits on the same cohort/dates.

The Lab's discovery methodology systematically searches for these inverses. When TIE TIY suffers a loss batch (e.g., the Apr 17 + Apr 29 UP_TRI × Bank × Choppy clusters totaling n=53 cluster losses), the Lab investigates:

- WHO won that day? Which sectors / signals / regimes profited on the same dates?
- WHAT mechanism explains the failure? Volume profile? Sector internal churn? Regime persistence?
- IS there a filter sub-cohort that profits inside the failing parent cohort?
- IS there an inverse pattern (different signal type, opposite direction, or sector rotation) that profits when the parent cohort fails?

The validated answers enrich the pattern database. Over time, the Lab builds a regime-symmetric library: for each failing cohort, a corresponding profitable counterpart is documented (or, the cohort is documented as "no symmetric profit found; structurally avoid").

---

## Discovery → Validation → Promotion Pipeline

```
Live loss batch observed in TIE TIY
        ↓
Lab investigation registered (hypothesis, cohort, scope)
        ↓
Backtest data fetched (historical OHLC for relevant universe + period)
        ↓
Signal regeneration (replay signal detection on historical data)
        ↓
Cohort baseline statistics (n, W, L, F, WR, avg pnl across full history)
        ↓
Mechanism analysis (WHY does cohort fail/succeed)
        ↓
Inverse-pattern search (what profits on same dates)
        ↓
Hypothesis testing (with mandatory train/test OOS split)
        ↓
Ground-truth validation (would discovered pattern have changed Apr 17 + Apr 29 outcomes)
        ↓
PROMOTION GATE (per PROMOTION_PROTOCOL.md — 7 gates)
        ↓
Pattern graduates to main: kill_pattern OR boost_pattern OR new signal type
```

Each arrow is a checkpoint where investigation may stop, fail, or pivot. The pipeline is **never** a fast-path; even high-conviction live evidence requires backtest validation before promotion.

---

## Lab Discipline Principles

These are non-negotiable. They protect the Lab from becoming a pattern-fishing exercise.

1. **Out-of-sample protocol mandatory.** Every hypothesis tests on TRAIN data; if it passes, validates on TEST data BEFORE acceptance. Train/test split locked in PROMOTION_PROTOCOL.md. No exceptions. No "we'll OOS later." Hypothesis tested only on test data = REJECTED (data leakage).

2. **Survivorship bias acknowledged.** Backtest universe (current 188 F&O stocks) overstates pre-2020 performance because delisted stocks aren't included. Always flag this in reports. Where survivorship bias materially affects conclusions (e.g., bank-cohort backtest pre-2018 when several PSU banks faced asset-quality crises and some were merged), reduce confidence in old-regime results.

3. **Regime classifier drift acknowledged.** Live regime classifier is calibrated on 2025-2026 data. Replaying it on 2008-2015 data may produce labels inconsistent with how those regimes felt to a contemporaneous observer. Treat older labels as approximate; flag any conclusion that depends heavily on regime labels older than 2018.

4. **Past loss batches as ground-truth.** Apr 17 + Apr 29 + future loss days are the ultimate validation set, registered in `/lab/registry/ground_truth_batches/`. Patterns that don't explain past losses don't graduate. Patterns that "would have caught" loss batches via test-period peeking (i.e., the pattern was derived from those exact dates) are flagged as overfit.

5. **No silent decisions.** Every hypothesis tested gets documented — including failures. Reject patterns are kept in `patterns.json` with `status="REJECTED"` plus failure reason. Future-you reading the registry must be able to see WHY a pattern was rejected, so it isn't naively retried.

6. **Lab does not block TIE TIY.** TIE TIY ships safety rules (kill / boost) based on live `signal_history` evidence even before Lab validates. Lab enriches, doesn't gate. Example: kill_002 (UP_TRI × Bank × Choppy) may ship to main based on live n=43 evidence + S-6 prerequisite, while Lab continues running INV-001 to enrich the rule with multi-year backtest context. Lab findings may later strengthen, weaken, or extend kill_002 — but they do not delay it.

7. **Sector-specificity > blanket rules.** UP_TRI × Bank × Choppy may fail at 27% but UP_TRI × Pharma × Choppy succeeds at 67%. Lab patterns are sub-cohort precise. Blanket "UP_TRI × Choppy = kill" suppresses profitable sub-cohorts; rejected by gate 6 of PROMOTION_PROTOCOL.md.

---

## Lab vs Live TIE TIY: Update Rhythm

- **Main branch:** continuous (live trading per Wave 5 brain operational rhythm + bridge L1/L2/L4 daily).
- **Lab branch:** investigation-paced (weeks per investigation; promote findings monthly or as discovered).
- **Lab → main flow:** PR review with empirical evidence package (cohort baseline + mechanism + OOS results + ground-truth validation + counterfactual P&L). Main branch never modified directly from Lab without explicit promotion ceremony.
- **Lab branch updates:** Lab pulls main's `output/signal_history.json` periodically as ground-truth source updates; Lab does not push to main except via promotion PR.

---

## Connection to HYDRAX

HYDRAX is a separate longer-horizon platform initiative deferred per `doc/project_anchor_v1.md` §7 D-9 (gates on Waves 1-5 stable + 2 weeks observation). Lab and HYDRAX are independent tracks today; future relationships (e.g., Lab insights informing HYDRAX classifier or architecture) will be defined when HYDRAX scope clarifies.

Refer to anchor §7 D-9 for HYDRAX status. Lab founding does not constrain HYDRAX scope.

---

## Founding State (2026-04-30)

- **Branch created:** `backtest-lab` off `main` commit `588cf26` (TIY Wave UI deferral closeout).
- **TIE TIY operational state at founding:**
  - Wave 5 backend complete (7/7 backend steps shipped 2026-04-29).
  - Brain layer operational; first production fire scheduled tonight 22:00 IST per `brain.yml`.
  - Bridge layer firing daily L1/L2/L4 (`bridge_state.json` mtime confirms continuous operation).
  - 42 open positions; 290 total signals in `signal_history.json` (29-day live span).
- **Recent loss batches motivating Lab founding:**
  - **Apr 17, 2026** broader cohort: UP_TRI × Choppy (all sectors), W=11 L=24 F=1, n=36, WR 31% per `watch_001` evidence in `data/mini_scanner_rules.json`. Surfaced as informational `watch_001` warning at the time.
  - **Apr 29, 2026** Bank-specific batch: UP_TRI × Bank × Choppy resolutions today, W=2 L=14 F=1, n=17, WR 12% — drove Lab founding decision today.
  - **kill_002 candidate cohort** (Bank-specific lifetime): UP_TRI × Bank × Choppy total **n=26 resolved + 3 OPEN** (today's 17 resolutions are SUBSET of the 26 lifetime resolved, NOT additional). Resolved breakdown: W=7 L=18 F=1 → **WR 27%** (7/26). Today's 17 contribute the bulk of recent losses (2W / 14L / 1F) within the broader 26. Sharp regime opposite to UP_TRI × Bank × Bear at WR 100% (n=8). The Bank-specific subset is the kill_002 candidate; the broader UP_TRI × Choppy cohort (Pharma 67% / Energy 71% / Bank 12%) is heterogeneous and should NOT be blanket-killed.
- **Live `kill_002` ship (separate work on main branch, not Lab):** Lifetime n=26 resolved is BELOW Lab's Tier A 50-minimum AND below Tier B 30-minimum (per `PROMOTION_PROTOCOL.md` Gate 3). Lab cannot promote on live evidence alone today; this is precisely why Principle 6 (Lab does not block TIE TIY) matters — kill_002 ships on main as `LIVE_EVIDENCE_ONLY` per trader judgment + live signal_history evidence, awaiting S-6 prerequisite (`mini_scanner.py` regime-axis defensive read). Lab investigation INV-001 will validate the same cohort against 15-year historical backtest expansion of n; Lab findings may strengthen, weaken, or extend kill_002 — but do not delay it.
- **Lab first investigations pre-registered:**
  - **INV-001:** UP_TRI × Bank × Choppy structural failure deep-dive (15-year backtest + mechanism + inverse-pattern search).
  - **INV-002:** UP_TRI × Bank × Bear validation (verify suspicious 100% WR n=8 against 15-year history).
- **Lab infrastructure status:** scaffolding only; data fetcher / signal replayer / regime replayer / hypothesis tester / ground-truth validator (MS-1..MS-5) ship in subsequent sessions.

---

## Reading Order for New Lab Visitors

1. This file (vision + philosophy + lab-vs-live distinction)
2. `PROMOTION_PROTOCOL.md` (7-gate empirical promotion path)
3. `ROADMAP.md` (investigation queue + infrastructure milestones)
4. `registry/patterns.json` (live pattern database)
5. `registry/ground_truth_batches/*.json` (past loss batches as validation set)
6. Any `analyses/*.md` reports (per-investigation findings; populate as investigations complete)
