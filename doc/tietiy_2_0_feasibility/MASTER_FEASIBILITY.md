# TIE TIY 2.0 — Master Feasibility Report

Generated 2026-05-13. Sub-reports 01-08 carry the detailed evidence.

---

## 1. Executive summary

**Recommendation: BUILD-LATER.**

TIE TIY 2.0 is technically feasible at ~480 hours (16 weeks realistic, 12 optimistic, 24 pessimistic). The architecture is sound, most modules port cleanly from the current scanner, the L99 research framework is encodable, and V5 / Fib zones / self-learning are all implementable. **But the user's actual track record is the controlling risk.** Brain layer shipped 14 days ago, still not firing in production. Shadow_ops_v1 ready to bootstrap, never bootstrapped. Foundation-backtest and nuvama-vision projects validated, never put into operator hands. 31 stale proposals sitting unread in `proposed_rules.json`, some dangerous. The pattern is consistent: infrastructure is built faster than it is operated. TIE TIY 2.0 is a 4-month build that would land another large unoperationalized system on top of three existing ones. **The correct next step is to operationalize what already exists.** Specifically: complete the brain production-fire (30 minutes of dashboard clicks), do the Path A surgical fixes (~28 hours, 1 week), bootstrap shadow_ops_v1 in parallel, then **earn the right to start TIE TIY 2.0 by sustaining 30 days of operational discipline first.**

---

## 2. Effort estimate

| Estimate | Hours | Weeks (30h/wk) | Caveats |
|---|---:|---:|---|
| **Optimistic** | 350 | 12 | No surprises; V5 works; all 5 Bull setups pass validation first try |
| **Realistic** | 480 | 16 | One audit rejection; one V5 recal; some scope creep |
| **Pessimistic** | 720 | 24 | V5 fails calibration; 2 Bull setups fail; brain operational debugging takes a week |

Critical-path single dependency that **cannot** be compressed: 60-day V5 McNemar calibration window. Add 4 weeks paper + 4 weeks small-live per setup. **Realistic time-to-full-live for 2 setups: 16 weeks. For all 5: 14+ months.**

---

## 3. Critical path

```
T+0:    User actions, 30 min
         - GH secret: ANTHROPIC_API_KEY
         - cron-job.org: brain.yml @ 22:00 IST
         - cron-job.org: brain_digest.yml @ 22:05 IST
         (everything else gated on these)

T+1w:   Path A surgical fixes complete + 30-day operational discipline period begins
         - 28 hours of work
         - Brain proposals start arriving in Telegram nightly
         - User starts approving/rejecting proposals
         - This is the test of whether the user can operate the system

T+5w:   Decision: did the 30-day operational discipline period validate the user's capacity?
         If YES: begin TIE TIY 2.0 build
         If NO: investigate why; defer TIE TIY 2.0

If TIE TIY 2.0 begins at T+5w:
T+5w:   Foundation port (bridge/core, calendar, schemas)
T+7w:   7-state regime classifier + 2 fastest Bull detectors (EMA20 pullback, VCP)
T+9w:   Validation infrastructure + first backtest
T+12w:  Brain wiring + self-learning closure
T+13w:  V5 gate (logged-only) goes live; 60-day calibration window starts
T+13w-21w: Paper trade 2 detectors + 2 retained current rules
T+21w:  V5 calibration McNemar test runs; threshold decisions made
T+25w:  First 2 Bull setups go live (full-live); remaining 3 in paper
T+30w:  All 5 setups status review; full-live where validated
```

**Earliest realistic TIE TIY 2.0 v1.0 deployment: T+25 weeks (~6 months from today).**

---

## 4. Risk inventory

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | "Starts but doesn't finish" — user's actual pattern with brain + shadow_ops + foundation-backtest + nuvama-vision | **HIGH** | Refuse to start TIE TIY 2.0 until 30 days of operational discipline on current scanner is demonstrated. |
| 2 | Opportunity cost vs Path A surgical fixes (~28h) | **HIGH** | Do Path A first regardless; TIE TIY 2.0 only after Path A shows operational lift. |
| 3 | Time-to-income pressure | USER-DEP. | Honest runway disclosure required before commit. 16-week build with no income; 6 months to paper-resolved Bull setups. |
| 4 | Regime risk during 4-month build (Bear may return) | MEDIUM | Keep current scanner running in parallel. Do NOT retire production scanner until TIE TIY 2.0 has 2+ live full-live setups. |
| 5 | New repo accumulates its own debt | MEDIUM | Port existing operational state (kill_001, watch_001, boost_patterns) day 1. Don't reset hard-won tuning. |
| 6 | 5 new Bull setups need 60+ trades each = 6-14 months validation | **HIGH** | Set explicit expectation. TIE TIY 2.0 v1.0 = 2 detectors live + 3 in paper. Full 5-setup deployment is v2.0+. |
| 7 | V5 may simply not work as gate (TATASTEEL bar replay FAILed) | MEDIUM | Build V5 as logged-only overlay first 60 days. McNemar decides. V5 component is removable without rebuilding. |
| 8 | Solo-developer module-ownership decay over time | LOW | Minimal protocol count (6). Version locked. No protocol changes post-v1. |

The HIGH risks (#1, #2, #6) are not engineering risks — they are **execution-discipline risks**. Engineering effort is bounded. Discipline is unbounded.

---

## 5. Validation timeline for 5 Bull setups

| Setup | Build | Backtest | Paper | Small-live | Total to full-live |
|---|---:|---:|---:|---:|---:|
| EMA20 pullback (highest signal frequency) | 8h | 1w | 4w | 4w | ~9 weeks |
| VCP breakout | 16h | 1w | 4w | 4w | ~10 weeks |
| Bull flag / high-tight | 12h | 1w | 4w | 4w | ~10 weeks |
| Darvas box (validated Patil 2024) | 14h | 2w | 6w (sparse) | 4w | ~13 weeks |
| Cup-and-handle | 16h | 2w | 6w (sparse) | 4w | ~14 weeks |

Parallel build, sequential graduate-to-live. **Earliest 1st setup full-live: ~9 weeks after TIE TIY 2.0 build starts.** **All 5 full-live: ~14 weeks after build starts.**

Total compute for purged-CPCV pass on all 5 setups: ~40 hours of MacBook CPU (~2 days continuous or 5 days nights-and-weekends).

---

## 6. V5 gate calibration plan

```
Day 1-60:    V5 gate operates in LOGGED-ONLY mode (does not gate trades)
             - Send chart to V5 per candidate
             - Record direction, zones, confidence, latency, cost
             - Store paired with TIE TIY decision + outcome (when resolved)
             - Daily cost: ~$0.28 USD (~₹24); 60-day cost: ~$17

Day 60:      ≥80 paired (TIE TIY × V5 × outcome) signals collected (across all regimes)
             - Run McNemar test per regime per signal type
             - Test asymmetry: V5_veto vs TIE TIY loss correlation
             
Day 60-90:   Per-regime threshold proposals fire from brain
             - "Stable-Bull V5 threshold should be 0.65" (or 0.70, or remove gate)
             - User approves or rejects per regime
             - Approved threshold goes live; brain monitors post-decision metrics
             
Day 90+:     V5 gate is active (or removed if McNemar = noise)
             - Weekly McNemar recompute
             - Threshold-update proposals if drift detected
             - Approval loop closes the learning cycle
```

**Cost: $17 for the 60-day calibration window.** Negligible.

**Decision threshold:** if McNemar χ² > 3.84 (p<0.05) in at least 3 of 7 regimes, V5 has gate value. If in fewer than 3 regimes, V5 is broadly noise; remove. If 0 of 7, V5 is anti-predictive; consider inverting (use disagreement as confirmation — unlikely but documented).

---

## 7. Self-learning workflow (text diagram)

```
┌─────────────────────────────────────────────────────────────────┐
│ Daily cycle                                                     │
└─────────────────────────────────────────────────────────────────┘
        │
        ├──► 08:30 IST: morning scan
        ├──► Throughout day: live trading from current rules
        ├──► 15:35 IST: EOD outcome evaluation
        ├──► 22:00 IST: brain.yml — analyze + propose changes
        │       └──► writes output/brain/unified_proposals.json
        ├──► 22:05 IST: brain_digest.yml — Telegram + dashboard
        └──► User reviews proposals (Telegram or dashboard)
                │
                ├──► /approve {prop_id}  → mini_scanner_rules.json updated
                ├──► /reject {prop_id} [reason]  → logged in decisions_journal
                └──► (deferred / expired)  → auto-expires after 7 days

┌─────────────────────────────────────────────────────────────────┐
│ Per-approved-change tracking (+30 days post-approval)           │
└─────────────────────────────────────────────────────────────────┘
        │
        ├──► Day +0:    Change applied; baseline metrics captured
        ├──► Day +14:   Mid-window metrics recompute; if drift, brain flags WATCH
        ├──► Day +30:   Final metrics computed
        │       - If improvement vs baseline: confirmed; promote tier if applicable
        │       - If regression: brain proposes demotion or reversal
        └──► closes the loop. User sees outcomes of past decisions.

┌─────────────────────────────────────────────────────────────────┐
│ NEVER auto-applied (always require approval)                    │
└─────────────────────────────────────────────────────────────────┘
- New rule activation
- Rule parameter changes
- Regime threshold changes
- V5 threshold changes
- Position sizing changes
- Universe additions/removals

┌─────────────────────────────────────────────────────────────────┐
│ Safe to auto-apply (no human approval needed)                   │
└─────────────────────────────────────────────────────────────────┘
- Cohort_health recompute
- Calibration metric updates (no threshold change)
- Logging / dashboard rendering tweaks
- Audit-log appends
```

---

## 8. Alternative paths comparison

| Path | Effort | Time-to-deploy | Outcome |
|---|---:|---:|---|
| **Path A — Surgical fixes on current scanner** (R1 + R2 fixes) | ~28h | 1 week | Brain firing nightly; dangerous proposals rejected; Bull label added; BULL_PROXY target rule active; watch_002/003 active. Captures **~60% of TIE TIY 2.0 visible value**. |
| **Path B — Bootstrap shadow_ops_v1** | ~1h setup | Day 1 | 30-day process-validation of rule_019. Sparse-fire (~1 trade in 30 days during Choppy). Discipline test only. No V5, no Fib, no 5 Bull setups. |
| **Path C — Parallel (A + B)** | ~29h | 1 week | Brain firing + shadow_ops campaign + Path A operational tuning. Best of both. Validates discipline AND captures most of TIE TIY 2.0 value. |
| **Path D — TIE TIY 2.0 ground-up rebuild** | ~480h | 16-24 weeks | New architecture; V5 gate; 7-state regime; 5 Bull setups (2 full-live by week 9, all 5 by week 14). High execution-discipline risk. |
| **Path E — Wait** (run current scanner, defer all decisions) | 0h | now | Current operational state continues. Brain proposals expire. Choppy regime UP_TRI losses accumulate (or stabilize as regime shifts). |

**Recommended: Path C** (parallel surgical fixes + shadow_ops bootstrap). 1 week of effort. Validates user's operational discipline. After 30 days, decide on Path D.

---

## 9. Honest assessment of "starts but doesn't finish" risk

The user's track record from `session_context.md`, `fix_table.md`, and direct file inspection:

| Project | Built | Validated | Deployed | Live data flowing | Time since "ready" |
|---|---|---|---|---|---:|
| Brain layer (Wave 5) | ✅ 7/7 steps shipped | ✅ smoke + live-data sample | ❌ no production fire | ❌ | **14 days** |
| shadow_ops_v1 | ✅ 11 steps + 1406-line arch doc | ✅ tests passing | ❌ no campaign bootstrapped | ❌ | **8 days** |
| foundation-backtest | ✅ multi-stock validated | ✅ Layer 1/2 forward tests | ❌ never went live | ❌ | weeks |
| nuvama-vision (V5 phase 1) | ✅ 60+ snapshots | ✅ TATASTEEL bar replay | ❌ never gated production trades | ❌ | weeks |
| Bridge L1/L2/L4 composers | ✅ Wave 2/3 shipped | ✅ smoke + bridge_state archive | ✅ fires daily | ✅ (until 2026-04-29) | live |
| `proposed_rules.json` (31 entries) | ✅ rule_proposer generated | n/a | ❌ no approvals | ❌ | weeks |

**One project deployed (Bridge L1/L2/L4 composers). Five projects built-but-not-deployed.** The hit rate is 1/6 (~17%).

The 6th project (TIE TIY 2.0) on this trajectory is more likely to join the 5 not-deployed than the 1 deployed.

**What changes the calculus?** Only sustained operational discipline on existing systems. Specifically:
- 30 days of brain.yml firing daily AND brain proposals being /approve'd or /reject'd (not deferred or expired).
- 30 days of the shadow_ops campaign running daily.
- Demonstrated weekly review of `decisions_journal.json` showing approved/rejected/expired counts.

Without those, **TIE TIY 2.0 is more likely than not to be the 6th unoperationalized project.**

The honest framing: *the user is good at engineering and underrate-ing the engineering of the operations layer. TIE TIY 2.0 doubles down on engineering; what's needed is doubling down on operations.*

---

## 10. Decision factors that would change the recommendation

The current recommendation is **BUILD-LATER**. The recommendation changes if:

| Factor | Changes to | Why |
|---|---|---|
| User completes brain production-fire (30 min) + sustains 30 days of daily approval discipline | **BUILD** | Operational risk #1 falls dramatically. TIE TIY 2.0 has a chance of being operationalized. |
| User explicitly states 6+ months runway with no income pressure | **BUILD** if discipline also clears | Time-to-income risk #3 disappears. |
| Path A's 28-hour surgical fixes produce measurable trading improvement (positive P&L or DD reduction) in 30 days | **BUILD-LATER** (validate now confirmed) | Demonstrates that the current scanner's ROI on small fixes is high; TIE TIY 2.0's ROI on bigger fixes is plausible. |
| User states they prefer to ship narrower (e.g., just V5 gate as a Telegram-side advisor, not a full rebuild) | **DON'T BUILD** | Narrower scope is achievable as a 2-week add-on to current scanner. No 2.0 needed. |
| Shadow_ops_v1 campaign fires zero rule_019 signals in 30 days (sparse-fire reality bites) | **DON'T BUILD** | The "rare-fire" paradigm of TIE TIY 2.0's most-disciplined rules may be operationally intolerable. Different architecture required. |
| User has third-party data showing V5 is reliable as gate at production stakes | **BUILD** | V5 risk #7 falls; the most novel component becomes lower-risk. |
| Regime returns to Bear and the existing scanner generates +50% in a month | **DON'T BUILD** | The existing scanner is doing its job; rebuilding is destructive. |
| Existing brain proposals (3 LLM-judged from 2026-04-29) are reviewed and produce >0 approvals | **BUILD-LATER** (operational signal good) | Demonstrates approval-loop closure. |

The most likely accelerator: **30 days of operational discipline on existing systems.** That's the gate.

---

## Three most important findings driving the recommendation

1. **shadow_ops_v1 is NOT TIE TIY 2.0.** My Round 2 framing was wrong. Shadow_ops_v1 is process-validation for one rule (rule_019 Bear+UP_TRI+sub_regime=hot). TIE TIY 2.0 is a comprehensive rebuild with V5 + Fib + 7-state regime + 5 new Bull setups + brain-approval loop. They are different scopes. (Source: §02 + grep of `doc/shadow_ops_v1_architecture.md`.)

2. **Brain layer + dashboard wiring captures ~60% of TIE TIY 2.0's user-visible value at ~5% of the effort.** The brain is shipped and writing proposals; only the production-fire (30 min) and dashboard surface (24 hours) are missing. Path A surgical fixes get most of the win in 1 week. (Source: §01 + §05 + §06.)

3. **The user's track record (1 of 6 projects deployed) is the controlling risk.** Engineering effort estimates are bounded (480 ± 160 hours); operational discipline is the unbounded factor. TIE TIY 2.0 doubles infrastructure; what's needed is operational discipline first. (Source: §08 Risk #1 + cross-reference of session_context + fix_table + R2 audit.)

---

## Honest one-paragraph answer: "If you were the user, would you do this?"

**Not yet.** I would do Path C this week: complete the brain production-fire (30 minutes of cron-job.org clicks + a GitHub secret), reject the dangerous proposals in `proposed_rules.json` (`/reject_rule prop_005 prop_006 prop_011 prop_012 prop_013`), do the small surgical fixes (kill_002 broad DOWN_TRI block; Bull regime label; BULL_PROXY target rule), wire the brain to the dashboard so proposals don't expire silently again, and bootstrap shadow_ops_v1 in parallel as a discipline test. That's ~29 hours of work — one focused week. Then I would spend the next 30 days **operating** what I built, not building more. Reviewing brain proposals nightly. Approving or rejecting decisively. Watching whether shadow_ops_v1 fires anything in Choppy regime. Tracking whether the surgical fixes actually move the WR + max-DD numbers. If after 30 days I am genuinely operating the existing system and earning trader-feedback from it, *then* I'd start TIE TIY 2.0 — informed by 30 days of operational reality, with a clear gating discipline already proven. Without that proof, TIE TIY 2.0 is a 4-month rebuild that joins the brain + shadow_ops + foundation-backtest + nuvama-vision pile of "well-built, never operated." The same hands that built the existing scanner would build TIE TIY 2.0 with the same operational gap. The fix is not more building. It is doing.
