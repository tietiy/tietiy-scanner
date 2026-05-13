# Adversarial Review — TIE TIY Fix-and-Improve Plan

**Generated:** 2026-05-13
**Reviewer:** CC (Claude Opus 4.7, 1M context)
**Mode:** Adversarial. Read-only.
**Operator track record (controlling constraint):** 1 of 6 prior projects operationalized.

---

## TL;DR — One sentence

**The user should NOT start the shadow_ops sprint tonight; they should spend this weekend on the three leverage points already identified in the mindmap (L1 brain digest + L2 daily regime + L3 PWA bridge banner), then take stock before committing 4-8 weeks to a sprint that the data shows is the build-not-operate pattern reasserting itself.**

---

## 0. Verification — what is true vs what was claimed

Before critiquing the plan, I verified the user's stated facts. Several do not hold.

| Claim | Reality | Source |
|---|---|---|
| `doc/tietiy_diagnostic/` exists | **DOES NOT EXIST on any branch.** Only stash reference on shadow_ops_v1. | `find doc -type d`; `git log --all -- doc/tietiy_diagnostic` |
| `doc/tietiy_diagnostic_round2/` exists | **DOES NOT EXIST.** | same |
| `doc/tietiy_2_0_feasibility/` exists | **DOES NOT EXIST.** | same |
| `doc/tietiy_2_0_design/` exists | ✅ exists, 8 files | confirmed |
| `doc/tietiy_mindmap/` exists | ✅ exists, 11 files (created this session) | confirmed |
| "46 paper positions open" | **80 pending positions.** Worse. | signal_history.json query |
| "36 DOWN_TRI bleeding paper positions" | **50 pending DOWN_TRI** (28 UP_TRI, 2 BULL_PROXY). Worse. | same |
| "31 dangerous proposals" | **70 pending proposals** (50 kill + 20 warn). | proposed_rules.json |
| "prop_005/006/011/012/013 would kill winning UP_TRI×Bear" | **MISLEADING.** prop_005/006 target BULL_PROXY age=0 (WR 42.1%, edge -17.9pp — a loser). prop_011/012/013 target UP_TRI×**Choppy** (WR 29-36%, edge -25 to -27pp — also losers). **None target UP_TRI×Bear.** | proposed_rules.json |
| "UP_TRI×Bear proven edge" | ✅ TRUE — **n=96 resolved, WR=92.7%.** Strong. | signal_history query |
| "Nifty Bull-recovery mislabeled as Choppy" | **Partially true; the situation is worse.** Sunday's weekly_intel snapshot (2026-05-08) showed above_ema50=True, slope=+0.0022, ret20=+1.37 (Bull-leaning). But Mon-Tue this week: Nifty fell from 24176 → 23379 (-3.3%), `above_ema50` flipped True→False on 2026-05-12, classifier still says Choppy. Brain has been reading the **stale Sunday Bull label all week** while the market is now decisively rolling over. | regime_debug.json |
| "brain proposals firing into the void" | ✅ TRUE — `decisions_journal.json` has 0 entries. `brain_telegram.py` is a 6-line stub. 3 brain proposals pending from 2026-05-12 22:00 run that nobody has seen. | brain files |
| "shadow_ops_v1 was built 220 commits never bootstrapped" | ✅ TRUE — last commit 2026-05-05 19:43 IST (**8 days idle**). Step 11 was "bootstrap + README + architecture doc consolidation" — but no campaign has actually been bootstrapped. | git log origin/shadow_ops_v1 |

**Net:** The user has internalized a narrative ("31 dangerous proposals that would kill my winning cohort") that, when checked against the data, is wrong. The actual situation is worse on raw bleed (50 DOWN_TRI not 36) and better on proposal safety (the named "dangerous" proposals target losing cohorts, not winning ones). The user is reasoning from memory of past LLM sessions, not from facts.

This is a meta-pattern worth flagging: **after 36 hours of planning, the user no longer knows what the data says about their own system.** That, by itself, is a strong argument for the L3 PWA-banner fix before another sprint.

---

## 1. Plan coherence assessment

The plan is **coherent in structure but inconsistent with the controlling constraint (the user's operationalize pattern).**

### Where it's coherent
- It sequences validation → integration → walk-forward → switch box in a defensible order.
- It identifies real opportunities (Bull setup capability gap, V5 gate, walk-forward as live validation).
- It correctly refuses TIE TIY 2.0 rebuild (the design study reached the same conclusion).
- It correctly identifies the inversion philosophy (debug before build) — though it then ignores that principle in execution.

### Where it's incoherent

**Incoherence #1 — The plan violates its own stated philosophy.** The user states "inversion philosophy: debug first, build second" then proposes 4-8 weeks of **building** (shadow_ops engineering, Bull encoders, V5 gate) before **debugging** the operational system (regime staleness, brain digest stub, DOWN_TRI bleed, PWA blindness). The stated philosophy and the plan's first move directly contradict.

**Incoherence #2 — Validation is presented as the bottleneck. Operations is the bottleneck.** The mind-map's leverage analysis (which the user just read) identified that brain output is **already** invisible to the trader, regime is **already** stale, PWA is **already** blind. Adding 5 new validated Bull detectors to a system whose 3 existing detectors are already operating without observability does not improve the operator's situation. It compounds it.

**Incoherence #3 — The "one weekend doubles usefulness" finding was acknowledged then ignored.** The mind-map's L1/L2/L3 leverage points are concrete, scoped, and stated as the highest-impact short-term work. The current plan defers all three indefinitely ("PWA gets proper redesign in Phase 5", "Telegram delivery polish deferred", "brain → analysis.html data layer integration is important, form TBD"). The plan acknowledges these matter and then puts each on a back burner.

**Incoherence #4 — "Sprint then integrate" treats UP_TRI×Bear as untouchable while ignoring its current operating risk.** The plan says we don't need to worry about money flow because "we know our edge (UP_TRI×Bear), it's paper, doesn't matter." But the actual risk to UP_TRI×Bear is **not** the brain proposals (which target Choppy/Bank/Other, not Bear). The actual risks are: (a) the stale regime keeps UP_TRI×Bear correctly identified, (b) DOWN_TRI signals consume operator attention and confidence, (c) the operator never builds the muscle of approving proposals correctly. The plan optimizes against a non-risk and ignores the real ones.

### Verdict on coherence
**The plan is sequenced as if the constraint is "we don't know which Bull setups work." The actual constraint is "the operator does not yet operate the system we have."** Sequencing more validation before fixing operations does not change the actual binding constraint.

---

## 2. Per-phase risk analysis

### Phase A — Shadow_ops Validation Sprint (4-8 weeks)

**Stated goal:** Validate 5 Bull setups + V5 gate via shadow_ops harness on historical data.

#### A.1 — Is shadow_ops_v1 operational?

**Verified state (origin/shadow_ops_v1, last commit 2026-05-05):**
- ✅ Code is complete and well-engineered (~3,000 LOC, 13 modules, 13 test files).
- ✅ Architecture document is comprehensive (1,406 LOC at `doc/shadow_ops_v1_architecture.md`).
- ✅ Append-only journal with SHA-256 tamper-evidence sidecars.
- ✅ Audit-faithful contract mirrors `lab/infrastructure/signal_replayer.py` bit-for-bit.
- ✅ Pre-scan checks gate operator with 7 preconditions.
- ✅ Cross-validation against canonical pipeline.
- ❌ **No campaign ever bootstrapped.** Zero committed `.json`/`.jsonl` runtime artifacts under `shadow_ops/`. `runs/<date>/` directories don't exist yet.
- ❌ **Idle 8 days.** Last touch 2026-05-05. The pattern that produced this harness has stopped.

**Verdict A.1:** shadow_ops_v1 is **engineered, untested in production, and currently dormant.** It is itself a perfect example of the user's documented build-not-operate pattern.

#### A.2 — Is the harness designed for batch validation of arbitrary detectors?

**No.** This is the most important finding for the entire plan.

From `shadow_ops/daily_scan.py`:

```python
ACTIVE_RULE_IDS = (
    "rule_019_bear_uptri_hot_refinement",
    "rule_031_bear_uptri_it_hot",
    "kill_001",
)
```

Followed by hardcoded dispatch:

```python
if r019:
    disposition = "TRADE_CARD_PROPOSED"
elif k001:
    disposition = "SUPPRESSED_BY_KILL_001"
else:
    disposition = "RULE_031_OVERLAY_ONLY"
```

**There is no plug-in framework.** Each new detector requires source code edits across:
1. `daily_scan.py` — add ID + if/elif branch
2. `schemas.py` — extend TradeCard if rule has custom fields
3. `lifecycle.py` — verify state machine handles new entry/exit semantics
4. `read_model.py` — extend derivation if needed
5. `end_of_shadow.py` — add campaign statistics
6. `pre_scan_check.py` — verify rule active
7. `tests/*.py` — write fixtures
8. `unified_rules_v4_1_FINAL.json` (in `lab/`) — rule must be **defined first**

**Effort estimate per the Explore agent's audit:**
- If 5 Bull rules already defined in unified_rules JSON: **5-6 days engineering** to integrate
- If 5 Bull rules need design + audit first: **3-4 weeks**
- Then **30+ trading days of shadow campaign** before any data
- **Total Phase A realistic floor: 5-6 weeks. Realistic ceiling: 10-12 weeks** if Bull rules need full design.

The user's "4-8 weeks" is too optimistic by 30-50% if the rules aren't already in unified_rules. **Have you confirmed they are?** The Explore agent did not find them.

#### A.3 — Risks during Phase A

- **shadow_ops itself becomes the second build-don't-operate artifact.** If the 5-week sprint completes but the resulting validated rules don't get deployed to TIE TIY 1.0 (Phase B), then we have a second harness sitting at "Step 11" idle forever.
- **The operator skill that matters (read brain digest, approve/reject proposals, trust the regime label) is not exercised during shadow_ops.** Shadow_ops is a developer's harness. It produces JSONL files. The skill being developed is engineering, not operation.
- **Historical overfit.** Shadow_ops validates against the same historical bars used to design the rules. McNemar on the same data the V5 gate was tuned on is not independent evidence. This is a real statistical concern.
- **"Walk-forward starts after Phase B" means walk-forward starts in week 10+.** Live walk-forward data for the new rules accumulates only after deploy. So in the 4-8 weeks of "validation sprint" we get zero forward data.

**Verdict Phase A:** Worth doing **eventually**. Wrong move to do first.

---

### Phase B — Deploy Findings to TIE TIY 1.0

**Stated goal:** Integrate shadow_ops-validated capabilities into main.

#### B.1 — Integration surface

New detectors plug into `scanner/main.py:run_morning_scan()`:
- `scanner_core.detect_signals()` would need 5 new entry points (VCP, EMA20PB, etc.)
- `scorer.py` would need scoring rules for each new signal type
- `mini_scanner_rules.json` would need new boost/kill/warn entries
- Bridge `bucket_engine.py` Gate 3 would need new boost_match logic for each type
- Telegram `bridge_telegram_premarket.py` would need new emoji/section per type
- The PWA `ui.js` rendering would need updates

**~12 modules touched for integration.** Plus regression tests. Probably **2 weeks** of careful work, not "deploy findings."

#### B.2 — Risk to UP_TRI×Bear

**The most precious thing the system has is UP_TRI×Bear at 92.7% WR n=96.** Integration of 5 new detectors carries risk because:

- The bridge bucket_engine has a 4-gate tree. Adding boost rules for Bull setups means **Gate 3 fires more often**. Today, Gate 4 (evidence consensus) is the dominant route for most signals; a system change can shift cohort assignments.
- The mini_scanner rules file currently has the comment `regime_alignment: PERMANENTLY DISABLED — backtest proves Bear regime UP_TRI is highest conviction trade (avg 4.85%). Activating this rule kills the best signals.` That's a stated invariant; integration must preserve it.
- Adding 5 new signal types **increases the daily commit volume** through ltp_writer (more tracked symbols) and changes the signal_history schema (new signal types).

**Mitigation needed:** every integration step should leave UP_TRI×Bear paths untouched and add new types as parallel branches. This is doable but requires care, and "deploy findings" undersells the effort.

#### B.3 — How does operator know capabilities are firing correctly?

**Without L1 (brain digest), the operator has no daily proposal visibility. Without L3 (PWA bridge_state banner), the operator has no daily bucket visibility.** So if Phase B deploys 5 new detectors and one fires incorrectly:

- It will appear in `signal_history.json` (visible only via SQL.js in analysis.html — slow)
- It will appear in `bridge_state.json` (not currently read by PWA at all)
- It will be Telegram-broadcasted by `bridge_telegram_premarket.py` IF it makes it into a TAKE_FULL/TAKE_SMALL bucket; otherwise silently SKIP'd

**The operator's most likely failure mode is missing a regression for days.** Same as today, except now with 5 more signal types to debug.

**Verdict Phase B:** The integration is risky enough that it **requires** visibility infrastructure (L1, L3) to be in place first. Otherwise Phase B has no safety net.

---

### Phase C — Walk-Forward Verification (parallel with B)

#### C.1 — Statistical sample size

For a new detector to have a statistically meaningful walk-forward signal:
- McNemar test on paired samples: **n ≥ 30 paired observations** at minimum, ideally 50+
- Cohen's w ≥ 0.3 for medium effect detection: requires n ~85 to reach 80% power
- With ~5-8 signals/day in TIE TIY's universe and only some matching a new detector, expect **6-12 weeks to accumulate enough paired samples per detector**

So Phase C produces **publishable evidence at week 18-24 from today** at the earliest. Not 4-8 weeks.

#### C.2 — During the sprint, what walk-forward data accumulates?

**Zero for the new detectors** — they aren't deployed until Phase B. The only walk-forward data accumulating during weeks 1-8 is on the existing 3 detectors. Which the operator isn't watching, because there's no brain digest.

#### C.3 — Historical overfit risk

The user's L99 5-Bull-setup research presumably tuned setup parameters on the same historical data shadow_ops will replay. McNemar on that data tests **calibration**, not **out-of-sample edge**. Without a clean train/validate/walk-forward split, all the sprint produces is "the encoder I wrote matches the spec I wrote." That is necessary but not sufficient evidence of edge.

**Verdict Phase C:** The walk-forward design works only if (a) detectors deploy in week 5-7, (b) operator watches results daily, (c) sample size patience holds for another 12+ weeks after deploy. Without L1/L3 visibility, requirement (b) is empirically already failing.

---

### Phase D — PWA Switch Box (eventually)

#### D.1 — Pulling Phase 5 work into Phase D is inconsistent

L99's 12-month plan put PWA redesign in Phase 5 (final hygiene + UI). The current plan pulls a chunk of that work forward to "switch box" but defers the rest. The result is a partial PWA dependency that has to be re-architected later.

If you're going to touch the PWA, do it once and properly. If not, defer entirely. Pulling switch-box forward without the rest creates rework.

#### D.2 — Minimal viable switch box

The user describes "per-detector, per-regime, per-V5-threshold toggles." That's three dimensions of switches. Minimal viable would be:
- Boolean per detector (5 toggles + 3 existing = 8)
- Boolean per regime gate (3 toggles)
- V5 threshold slider (1)

That's 12 controls. Per the plan, each should be backed by an entry in `mini_scanner_rules.json`. Today the file has 7 boost_patterns + 1 kill_pattern + 1 watch_pattern = 9 entries. So the switch box would roughly double the rule complexity at the same time it's first being operated.

**Verdict Phase D:** Reasonable goal but premature. Build the visibility first (so you know what to toggle), then build the toggles.

---

## 3. What's missing / what's being avoided

### 3.1 — The 70 pending proposals are not addressed

The plan does not say what to do with the existing `proposed_rules.json` queue. As verified:
- 70 pending (50 kill + 20 warn)
- Several are **structurally correct kill decisions** that the user has flagged as "dangerous" via misremembered framing
- `prop_011` (kill UP_TRI×Choppy, n=107, WR 34.6%, edge -26.5pp) is a textbook example of a kill rule that the system needs **today** — it would have prevented today's 8/8 SKIP from being attempted at all (because today's regime is Choppy and the UP_TRI cohort in Choppy regime is a -27pp edge)

**Not approving these correct decisions is itself a cost.** Every day the operator doesn't approve prop_011, the system continues to spend cohort_health resolution capacity on UP_TRI×Choppy signals that statistically lose money. Continuing to "be careful" is not free.

### 3.2 — The 50 DOWN_TRI pending positions are not addressed

This is worse than the user said. 96 DOWN_TRI ever, 46 resolved at 21.7% WR / -0.32R / -4.74% PnL. **50 still pending.** That's a structurally broken signal type continuing to bleed paper P&L.

The sprint plan ignores this. It is treated as "doesn't matter, it's paper." But three things are true:
1. **Operator attention is finite.** Every DOWN_TRI in the Telegram brief or `/today` response is a distraction from the real edge (UP_TRI×Bear).
2. **The bleed will continue for ~6 more weeks** as those 50 pendings resolve at -32R-equivalents. The signal_history dataset acquires more negative-edge data.
3. **A `kill DOWN_TRI` rule is the obvious operational fix.** Why hasn't it been approved? The system already detected the problem — `pattern_miner` and `rule_proposer` have produced proposals — and the operator has not acted.

This is the operationalize gap, visible and quantifiable.

### 3.3 — Brain → operator path stays broken for 4-8 more weeks

Today: 3 brain proposals pending (last refreshed 2026-05-12 22:00), 0 trader decisions logged, `decisions_journal.json` empty, Step 7 stub. The plan does not include shipping Step 7.

This means during the entire sprint:
- Brain runs nightly at 22:00 IST and produces top-3
- Anthropic API calls cost ~$0.05/night, ~$0.35/week, ~$2-3 over 8 weeks
- Trader never sees any of them
- `reasoning_log.json` grows append-only with LLM rationales the operator never reads
- `decisions_journal.json` stays empty so brain's history context for the next night is also empty (brain re-reasons the same proposals from scratch)

The brain that the user paid Anthropic to run has produced ~14 days of proposals to date with **zero trader feedback**. The plan extends that to ~70+ days.

### 3.4 — Regime daily refresh (L2) is not addressed

Today's data confirms the problem dramatically:
- 2026-05-08 (Sunday last weekly_intelligence): above_ema50=True, slope=+0.0022, ret20=+1.37%, regime="Choppy" (Bull-recovery lean)
- 2026-05-12: above_ema50=False (Nifty fell below EMA50), slope=+0.0023, ret20=-0.98%, regime="Choppy"
- 2026-05-13: above_ema50=False, slope=+0.0011, ret20=-1.94%, regime="Choppy"

Nifty fell -3.3% in 2 days and the regime label hasn't moved because brain reads the weekly snapshot. **By next Sunday (when weekly_intelligence refreshes), the regime might finally flip to Bear — but only after a week of mis-bucketing.** During the sprint, this same cadence holds.

If a UP_TRI signal fires this week with regime=Bear (the real state), it would be the system's highest-conviction trade (92.7% WR). Instead it will be tagged Choppy and bucketed SKIP. **The operator loses real opportunity right now and the plan doesn't address it.**

### 3.5 — Live capital deployment timeline

User initially wanted live capital in 2-4 weeks. The current plan pushes to 8+ weeks (Phase A) + 2-3 weeks (Phase B) + 4-8 weeks (Phase C accumulation) = **14-19 weeks before any live capital decision can be made on the new detectors**. UP_TRI×Bear capital deployment is technically possible today but the plan does not name when it happens.

If the answer is "live capital is paper-only during the sprint," the user should say so plainly. If the answer is "live capital on UP_TRI×Bear immediately, sprint on the side," the plan should be restructured around that.

### 3.6 — The diagnostic docs the user thinks they have

As verified in §0: `tietiy_diagnostic/`, `tietiy_diagnostic_round2/`, `tietiy_2_0_feasibility/` do not exist on any branch. The user is making planning decisions citing documents that aren't durable. **This is itself an operationalize-pattern symptom**: knowledge produced, not persisted.

---

## 4. L99 12-month plan vs the current plan

L99 recommended sequence (as stated by user):
- Phase 1 — Operational visibility (3 wks), incl. L1/L2/L3
- Phase 2 — Stop bleed (4 wks), incl. DOWN_TRI quarantine + dangerous proposal purge
- Phase 3 — Discipline window + live capital (6 wks)
- Phase 4 — Capability additions (Bull + V5 + zones) — 22 wks
- Phase 5 — Hygiene + PWA redesign — 17 wks

The user's current plan effectively **flips Phase 4 to first**:
- Sprint = Phase 4 work (Bull setups, V5, validation harness)
- Phase 1/2/3 deferred to "after sprint"
- Phase 5 pulled forward as "switch box"

### Is reordering defensible?

**Sometimes.** A defensible reordering would be: "the binding constraint is capability gap, the existing operational layer is good enough."

But the evidence does not support that:
- The existing operational layer is **demonstrably failing** to surface brain output (0 entries in decisions_journal)
- The existing operational layer is **demonstrably failing** on regime accuracy (week-stale label while Nifty sells off)
- The existing operational layer is **demonstrably failing** the operator (after 36 hours of planning, the operator no longer knows what the data shows)

The binding constraint is **not** capability. It's operation.

### Is this the build-not-operate pattern?

**Yes, and the user named the pattern themselves.** Per the user's own diagnostic summary:
> "Brain layer shipped April 29 with proposals never read"
> "shadow_ops_v1 built 220 commits never bootstrapped"
> "foundation-backtest and nuvama-vision built and validated never operated"

The sprint plan adds a **fourth** entry to that list: "Bull setups validated in shadow_ops, never operated." Without operational discipline being built first, the sprint cannot evade the pattern. It re-instantiates it.

### Verdict on L99 reordering

**Reordering is defensible only if Phase 1 work is folded into the sprint or executed in parallel.** The current plan defers Phase 1 entirely. That's the pattern reasserting.

---

## 5. Honest recommendation

### Probability of operationalization & risk profile per option

| Option | Description | P(operationalized) | Time to live capital | Risk to UP_TRI×Bear | Time to first user-facing improvement |
|---|---|---|---|---|---|
| **X — Pure sprint** | Current plan: 4-8 wk shadow_ops, then integrate, then walk-forward, then switch box | **~25%** based on track record | 14-19 weeks | High (no visibility during integration) | 5-8 weeks if at all |
| **Y — Weekend visibility first** | 1 weekend on L1+L2+L3 (~25 hrs), THEN sprint | **~50%** | 2-4 weeks for UP_TRI×Bear live, sprint output 14-18 weeks | Low (visibility before integration) | 1 weekend |
| **Z — L99 as drafted** | Strict phase 1→5, 12 months | **~35%** | 13 weeks per plan | Low | 3 weeks |
| **W — CC's recommendation** | 3 weeks operations-first; sprint deferred to Month 2 | **~55%** | 3-4 weeks UP_TRI×Bear live, sprint Month 2+ | Low | 1 weekend |

Probability estimates are conservative anchored on 1-of-6 base rate, adjusted by how much each plan front-loads operationalization muscle.

### Option W in detail — what I'd recommend

**Week 1 (this weekend through next Friday): Visibility + control.**
- Day 1 (Sat, ~6 hrs): Ship L1. Implement `brain_telegram.py` Step 7. Wire `/approve <unified_id>` and `/reject <unified_id>` in `telegram_bot.py`. Test on tomorrow's brain digest. Output: trader sees brain proposals from Sunday's run for the first time.
- Day 2 (Sun, ~6 hrs): Ship L2. Change `brain_derive._derive_regime_watch()` to read from a daily source. Today's data alone proves the staleness costs real opportunity. Output: regime label moves with daily Nifty state, not Sunday's snapshot.
- Day 3 (Mon evening, ~4 hrs): Ship L3 mini-version. Add `bridge_state.json` fetch to `ui.js`. Render banner state + color from `bridge_state.banner`. Add bucket badge per signal card. Output: PWA shows DEGRADED banner; trader sees TAKE_FULL/TAKE_SMALL/WATCH/SKIP at a glance.
- Day 4-5 (Tue-Wed, ~6 hrs total): Review the 70 pending proposals via the new digest. Approve the obvious wins (prop_011 kill UP_TRI×Choppy, prop_032/033/034/035 kill UP_TRI×Bank, prop_005/006 kill BULL_PROXY age=0 if user agrees with cohort analysis). Reject anything dubious. Add `kill DOWN_TRI` rule manually to mini_scanner_rules.json or via a brain proposal if one exists. Output: rule queue cleaned; system stops detecting losing cohorts.
- Day 6-7 (Thu-Fri, ~4 hrs total): Watch the system operate with new visibility. Don't ship anything. Observe what brain proposes nightly, how regime label moves, whether DOWN_TRI bleed stops. Output: operational muscle exercised.

**Total week 1: ~26 hrs across 7 days. Realistic with 4 hrs/day. Verifiable progress every day.**

**Week 2: UP_TRI×Bear live capital.**
- Define position sizing rules (1% capital risk on Tier S UP_TRI×Bear signal, 0% on others initially).
- Trade UP_TRI×Bear live for one week. n=2-3 signals expected (Bear regime, low frequency).
- Observe behavior of live vs paper.
- Output: first live capital deployment of the system.

**Week 3: Stabilize + sprint decision.**
- Review 2 weeks of operational data.
- Decide on shadow_ops sprint with eyes open: do we still want 5 Bull setups? Or has the regime stabilization (post L2 fix) made UP_TRI in Bull regimes already work?
- If sprint still wanted: start it from a system that's now actually operated.
- If not: redirect to V5 gate or Phase 2 (DOWN_TRI quarantine, dangerous proposal purge per L99).

**Output by week 3:** operational system, live capital on proven edge, decision on sprint based on actual data not theoretical hope.

### What CC would actually choose

**Option W. With Option Y as a fallback if W feels too ambitious.**

The sprint is not wrong. It is **wrongly first**. The user can do the sprint in Month 2 with full operational visibility and a track record of having approved/rejected ~70 proposals and traded live for 2 weeks — and at that point the sprint will be **more likely to succeed** because the operator is now exercising the muscle the sprint validates.

If the user starts the sprint tonight, the most likely outcome (~75%) is: 4-6 weeks of partial sprint work, gradual loss of momentum, side-tracked by an unrelated TIE TIY operational bug nobody noticed, sprint becomes a fifth example of build-don't-operate.

---

## 6. The 3 most uncomfortable truths CC found in this review

### Truth #1 — The user is making planning decisions citing documents that don't exist

`doc/tietiy_diagnostic/`, `tietiy_diagnostic_round2/`, `tietiy_2_0_feasibility/` were named as primary inputs to the plan. **None exist on any branch.** Only their successor docs (`tietiy_2_0_design/` and the mind-map I just produced) exist. The user is reasoning from session memory of LLM conversations, not from durable artifacts.

This matters because after 36 hours of "planning," the operator no longer can trace which finding came from where. When the sprint runs into a disagreement six weeks from now, "what did the diagnostic say" cannot be answered. The plan rests on knowledge that has not been persisted.

### Truth #2 — The "dangerous proposals" framing is wrong

The 5 proposals named as dangerous (prop_005, 006, 011, 012, 013) do **not** target UP_TRI×Bear. They target:
- BULL_PROXY age=0 (a -17.9pp edge underperformer)
- UP_TRI×Choppy (a -25 to -27pp edge underperformer — same regime that bucketed today's 8 signals SKIP)

**These are correct kill decisions sitting unapproved.** Every day they sit, the system continues to detect signals it then SKIPs anyway. The operator's caution is protecting losers, not winners.

The actual protection of UP_TRI×Bear comes from a different file (`data/mini_scanner_rules.json` has the comment `regime_alignment: PERMANENTLY DISABLED — backtest proves Bear regime UP_TRI is highest conviction trade`). That structural protection is **already in place** and not at risk from these proposals.

The operator has a false fear and a real opportunity sitting unaddressed.

### Truth #3 — shadow_ops_v1 IS the build-not-operate pattern

The user listed three examples of the pattern: brain (April 29, never operated), shadow_ops_v1 (220 commits, never bootstrapped), foundation-backtest + nuvama-vision (built, never operated).

**The current plan proposes spending 4-8 weeks extending shadow_ops_v1.** That is, the plan proposes that the way to escape the pattern is to spend more time on the largest existing instance of the pattern. The harness's last commit was 2026-05-05 with the message "bootstrap" — the literal next step that did not happen.

If the user could operationalize the brain digest (200 LOC weekend's worth of work), they would be on track to operationalize the shadow_ops sprint output. If they cannot, the sprint output will join the brain in not being operated.

**The cheapest test of "can I escape the pattern" is the one-weekend visibility fix.** If after one weekend, brain digest is live and the operator is approving proposals daily — then the sprint is worth starting. If the one weekend doesn't happen, the sprint won't either.

---

## 7. The 3 things the user is right about (no review is one-sided)

### Right #1 — Refusing the TIE TIY 2.0 rebuild

The `tietiy_2_0_design/MASTER_DESIGN.md` study concluded that 2.0 is structurally smaller than expected and reduces to "1.0 with plug-in refactor + dashboard." The plug-in refactor will be **easier after operational discipline** than before, because operating the system tells you which boundaries are real and which are accidental. **Deferring 2.0 is correct.**

### Right #2 — UP_TRI×Bear is the edge and worth preserving

n=96, WR=92.7%, no flat. This is a real, measurable, large edge. The user's instinct to **not screw this up** is correct. Any plan must include "leave UP_TRI×Bear paths untouched." This is a true invariant of the system and should anchor any sequencing decision.

### Right #3 — shadow_ops_v1 is real, valuable, and well-engineered

Despite being idle for 8 days, the harness is excellent work: append-only journal with SHA-256 tamper-evidence, audit-faithful state machine, pre-scan checks, comprehensive architecture doc. **The cost of doing nothing with it is real.** Once operational visibility is in place, this harness becomes a genuine asset — for the rule_019/rule_031 it was built for, and potentially (with engineering work) for new rules.

The right move is not to abandon shadow_ops. It's to defer the sprint until the operator has built the operational muscle to actually consume what the sprint will produce.

---

## Closing note

The mind-map produced one sentence the user has not yet acted on:

> "To make TIE TIY twice as useful with one weekend of work: ship Step 7 (L1), connect the PWA to bridge_state (L3), and rethink regime cadence (L2). Everything else is incremental."

That sentence is not a suggestion. It is the cheapest test of the plan itself. If the user can ship the weekend, the sprint follows naturally. If the user can't ship the weekend, the sprint will not save them.

**Don't start the sprint tonight. Do the weekend tonight + tomorrow. Then take stock.**

---

*End of adversarial review. Generated under the user's instruction to be brutally honest, with the operationalize track-record as the controlling constraint. No production code modified. No diagnostic claims accepted on faith — all key numbers re-verified from the repo.*
