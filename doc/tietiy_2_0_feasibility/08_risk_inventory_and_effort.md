# 08 — Risk Inventory + Total Effort

## Effort rollup

| Bucket | Hours | Source |
|---|---:|---|
| Port from current scanner (52 modules clean/adapter/refactor) | 211 | §01 |
| Plug-and-play architecture + interface adapters | ~70 | §03 (intersection with port, ~50% double-counted) |
| 7-state regime classifier | 30 | §03 |
| V5 confluence gate (incl. calibration) | 50 | §04 |
| Brain → dashboard wiring (Option D) | 24 | §05 |
| Self-learning closure (post_decision_metrics + expanded proposal types) | 60 | §06 |
| Validation framework (backtest + CPCV + paper + small-live infra) | 74 | §07 |
| 5 new Bull setup detectors | 66 | §07 |
| Integration + smoke tests + docs | ~50 | new |
| Brain production-fire (the prerequisite) | 0.5 (30 min) | §06 |
| **De-duplicated rollup** | **~480 hours** | |

At 30 productive hours/week: **~16 weeks = ~4 months.**

### Three-point estimate

| Estimate | Hours | Weeks @30h/wk | Caveats |
|---|---:|---:|---|
| **Optimistic** | 350 | 12 | No surprises, no audit failures, V5 works first time, all 5 Bull setups pass validation on first try, no scope creep |
| **Realistic** | 480 | 16 | One audit rejection, one V5 calibration redo, two scope-creep additions |
| **Pessimistic** | 720 | 24 | V5 fails calibration → must build alternative gate; 2 Bull setups fail validation → must replace; brain production-fire takes a week of operational debugging |

**Realistic point estimate: 4 months to deployable TIE TIY 2.0 with 3 of 5 Bull setups live.**

To get ALL 5 Bull setups + V5 calibrated + self-learning loop closed: **6 months realistic, 9 months pessimistic.**

## Critical path

```
Day 0 — User action 30 min:
       GH secret + 3 cron-job.org entries → brain.yml fires daily
       
Week 1 — Core foundation (port + interface design):
       bridge/core/* port (40h) + interface contracts (20h)
       
Weeks 2-3 — Detector + regime + V5 build:
       7-state regime (30h)
       2 fastest Bull detectors: EMA20 pullback + VCP (24h)
       V5 gate logic (40h, calibration deferred)
       
Weeks 4-6 — Validation infrastructure + first backtest:
       Backtest harness + purged-CPCV (50h)
       Run all backtest on EMA20 + VCP + UP_TRI×Bear + BULL_PROXY×Bear
       
Weeks 7-10 — Paper trading phase:
       Brain wiring (24h) + self-learning closure (40h)
       Paper trade 2 Bull setups + 2 retained current rules
       V5 calibration data accumulation (60+ days needed for 80 paired signals)
       
Weeks 11-14 — Small-live for the first 2 setups:
       Build remaining 3 Bull detectors (42h)
       Paper-trade remaining 3 in parallel
       Small-live for EMA20 + VCP if paper-pass
       
Weeks 15-16 — Full-live decision + cleanup:
       Promote passed setups to full-live
       Document everything; retire current scanner cleanly
```

**Critical-path single dependency:** the **60-day V5 calibration window** (need 80 paired decisions to McNemar-test V5's regime-specific value). This cannot be compressed. Even if all code is built in week 4, V5 confidence to ship requires waiting for the data.

If V5 calibration finds V5 is noise (real possibility per the TATASTEEL bar-replay FAIL), the gate is removed; TIE TIY 2.0 still ships without V5. The waiting is **insurance**, not blocker.

## Risk inventory

### Risk 1: "Starts but doesn't finish" — the user's actual pattern

**Severity: HIGH.**

The user's delivery record per `session_context.md` + `fix_table.md` + R2:
- Brain layer: backend 7/7 shipped 2026-04-29, NEVER FIRED IN PRODUCTION. Cron + GH secret outstanding for 14 days.
- shadow_ops_v1: 11 build steps + 1406-line architecture doc shipped, NEVER BOOTSTRAPPED. Ready ~Week of 2026-05-05; today is 2026-05-13.
- foundation-backtest project (~/code/foundation-backtest): built, validated, never deployed.
- nuvama-vision project (~/code/nuvama-vision): built, V5 ran 60+ snapshots, never put into operator hands.
- proposed_rules.json: 31 pending proposals from rule_proposer, NEVER REVIEWED. Some dangerous.
- 7 filter rules in mini_scanner.py: NEVER ACTIVATED in 30+ days of shadow_mode data.

**Each of these built systems was technically correct but operationally unused.** The pattern is clear: the user is faster at building infrastructure than at operating it.

TIE TIY 2.0 is a **larger** infrastructure project. Without addressing the operational gap, TIE TIY 2.0 is likely to follow the same path: built well, never operationalized.

**Mitigation:**
- Refuse to start TIE TIY 2.0 code until brain.yml + brain_digest.yml + eod.yml are firing in production for 30 consecutive days. This proves the operational chain works.
- Refuse to ship more code until the existing 31 stale proposals are dispositioned (approved/rejected). This proves the approval loop closes.
- Commit to a **30-day no-build operational discipline period** before TIE TIY 2.0 starts. If the user cannot maintain operational discipline on the current scanner, TIE TIY 2.0 won't help.

### Risk 2: Opportunity cost vs Path A surgical fixes

**Severity: HIGH.**

Path A (R1 + R2 surgical fixes):
- Complete brain production-fire (30 min user action)
- `/reject_rule` dangerous proposals (5 min)
- Add kill_002 broad DOWN_TRI block (1 JSON edit, 5 min)
- Add Bull label to regime classifier (~10 LOC, 1 hour)
- Add Target2x for BULL_PROXY (1 LOC, 5 min)
- Activate watch_002/003 for documented loss cohorts (10 min)
- Patch pattern_miner top_positive metric (5 LOC, 30 min)
- Dashboard wiring per §05 (24 hours)

**Total Path A: ~28 hours, deployable in 1 week.** Captures most of the safety + visibility wins of TIE TIY 2.0.

If Path A captures 60% of the value at 6% of the effort, the case for TIE TIY 2.0 needs to clear a high bar.

**Mitigation:** Do Path A first regardless. TIE TIY 2.0 becomes a longer-arc investment AFTER Path A demonstrates operational discipline.

### Risk 3: Time-to-income pressure

**Severity: USER-DEPENDENT.**

If user has 4-8 weeks of runway: TIE TIY 2.0 build is high-risk (no income during build; if pessimistic estimate hits, runway exhausted).

If user has 6+ months runway: TIE TIY 2.0 build is feasible. Realistic 4-month build leaves margin.

**Mitigation:** Honest runway disclosure. The user must know whether they can survive a 4-month build that may not generate income for another 2-3 months post-deploy (paper + small-live).

### Risk 4: Regime risk during build

**Severity: MEDIUM.**

The proven Bear-regime cohorts (UP_TRI×Bear 94.7% WR, BULL_PROXY×Bear +1.13R) only pay during Bear regimes. If Bear regime returns during the 4-month build, the user misses prime trading.

Current regime (per regime_watch.json): 7 days stable Choppy with positive slope. **The market is in transition.** If it flips back to Bear during build, the operating scanner generates winners while the rebuild is unfinished.

**Mitigation:** Keep current scanner running in parallel during build. Treat TIE TIY 2.0 as additive, not replacement. Specifically, do NOT retire the production scanner until TIE TIY 2.0 has 2+ live full-live setups.

### Risk 5: New repo accumulates its own debt

**Severity: MEDIUM.**

Rebuild often replaces known technical debt with unknown technical debt. The current scanner has 30 days of operational tuning (kill_001, watch_001, 7 boost_patterns). TIE TIY 2.0 starts blank.

**Mitigation:** Port `mini_scanner_rules.json` rules as-is to TIE TIY 2.0 on day 1 (kill_001, watch_001, boost_patterns). Don't reset operational state.

### Risk 6: Validation latency for 5 new Bull setups

**Severity: HIGH.**

Per §07: 14 weeks for all 5 setups live. **3 months minimum of paper/small-live before any new setup is full-live.** During those 3 months, the trader can only deploy: UP_TRI×Bear, BULL_PROXY×Bear (both ported with re-audit), and maybe rule_019 (from shadow_ops_v1 if process-validated).

If the user expects TIE TIY 2.0 to have 5 live Bull setups in 4 weeks, expectation is wrong.

**Mitigation:** Set explicit expectation. TIE TIY 2.0 v1.0 = port + V5 gate + 2 Bull setups in paper. v2.0 = +3 more Bull setups + full-live for the first 2. Realistic timeline.

### Risk 7: V5 risk — may simply not work as gate

**Severity: MEDIUM.**

Per §04 and the user's nuvama-vision TATASTEEL bar replay (FAIL classification, n=3, −0.52 avg R), V5 as a real-time gate may not generalize. The 10-stock retrospective showed promise but the walk-forward test failed.

**Mitigation:** Build V5 gate as a logged-only overlay for first 60 days. McNemar test decides whether it gates. If V5 = noise, remove cleanly; TIE TIY 2.0 still ships without V5. **The V5 component is removable without rebuilding the system.**

### Risk 8: Module ownership over time

**Severity: LOW (solo developer).**

Plug-and-play modules require maintenance discipline (interface stability, deprecation policy, version bumps). User is solo developer with iPad+MacBook workflow. Discipline can slip.

**Mitigation:** Minimal interface count (6 protocols per §03). Version each protocol. Don't change protocol after v1 lock.

## Total risk score

3 HIGH risks (operational starts-not-finishes, opportunity cost, validation latency), 4 MEDIUM, 1 LOW. **The HIGH risks are not engineering risks — they are execution-discipline risks.** Engineering effort is bounded (480 ± 160 hours). Discipline is unbounded.

If the user has demonstrated operational discipline in the 30 days preceding TIE TIY 2.0 build, risk profile drops. If not, TIE TIY 2.0 is at structural risk of joining the brain/shadow_ops/foundation-backtest pile of "well-built, never deployed."
