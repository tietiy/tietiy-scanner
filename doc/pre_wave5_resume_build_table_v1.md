# Pre-Wave-5-Resumption Build Table

**Authored:** 2026-04-28 late evening IST · Planning doc · No execution
**Repo head at audit time:** `7995254` (batch closeout)
**Scope:** Sequencing every gap / fix / drift / cleanup / decision item that should land before Wave 5 Step 3 implementation resumes. Three-tier classification: BLOCKER / SHOULD-CLEAR / CAN-DEFER.
**Source-of-truth inputs:** `doc/project_anchor_v1.md` (commit `50325c7` §5/§6/§7) + `doc/fix_table.md` (38 PENDING / 9 PARTIAL / 6 DEFERRED mentions) + `doc/wave5_prerequisites_2026-04-27.md` (B/S/N items) + `doc/brain_design_v1.md §4 Step 3` (4 deriver function signatures).

**Discipline:** does NOT add new scope. Catalogs and sequences existing items. TIER 1 BLOCKER classification requires citation to a specific Step 3 dependency from Part 1; if no Step 3 dependency cites, item drops to TIER 2 or TIER 3.

---

## Part 1 — Step 3 dependency inventory

Every upstream input Step 3 actually consumes, per `brain_design_v1.md §4 Step 3` function signatures:

```
derive_cohort_health(history) → output/brain/cohort_health.json
derive_regime_watch(history, weekly_intelligence) → output/brain/regime_watch.json
derive_portfolio_exposure(history) → output/brain/portfolio_exposure.json
derive_ground_truth_gaps(history, mini_rules, patterns) → output/brain/ground_truth_gaps.json
```

Per `project_anchor_v1.md §11 Q5 status update`: Step 3 reads `bridge_state_history/<date>_EOD.json` as primary for `derive_portfolio_exposure`; signal_history is fallback.

| # | Input | Source path | Step 3 deriver function | Schema status | Quality status | Pre-Step-3 cleanup needed? |
|---|---|---|---|---|---|---|
| 1 | signal_history | `output/signal_history.json` | `derive_cohort_health` (filter outcome != 'OPEN'); `derive_portfolio_exposure` (signal_history fallback if EOD archive missing); `derive_ground_truth_gaps` | schema_version = 5 (locked since Wave 2 Apr-23) | M-13 oddity: 8 records have `outcome='OPEN'` AND `outcome_date='2026-04-27'` set simultaneously. Step 3's `outcome != 'OPEN'` filter (per audit Part D-1) correctly excludes them. | **NO** — M-13 records correctly filtered out by Step 3's design |
| 2 | weekly_intelligence | `output/weekly_intelligence_latest.json` | `derive_regime_watch` | schema_version = 1 (locked) | mtime 2026-04-26 (2 days old as of today). Step 3 reports `weekly_intelligence_age_days` per audit Part B-2 schema. | **NO** — staleness reflected in output `_metadata.warnings` |
| 3 | bridge_state_history EOD archive | `output/bridge_state_history/<date>_EOD.json` | `derive_portfolio_exposure` (primary source; reads `open_positions[]`) | schema_version = 1 (locked) | Today's archive landed via manual dispatch (`a5edc32`); 80 open positions; tomorrow's first scheduled-tick fire pending user-side cron-job.org dashboard entry. | **NO** — Step 3 has signal_history fallback per `brain_design §11 Q5` |
| 4 | mini_scanner_rules | `data/mini_scanner_rules.json` | `derive_ground_truth_gaps` | schema_version = 3 (locked) | Clean: 1 kill_pattern, 1 watch_pattern, 7 boost_patterns, 0 warn_patterns | **NO** |
| 5 | patterns | `output/patterns.json` | `derive_ground_truth_gaps` (informational; tier breakdown) | schema_version = 1 (locked) | `total_resolved_signals = 161` vs signal_history non-OPEN = 181 (20-record gap). Step 3 derives its own count from signal_history per audit Part D-1 + project_anchor §6.8 docstring comment. | **NO** — drift documented inline; not corrupting Step 3 output |

**Conclusion: Step 3's specific inputs are all clean.** All known issues handled by Step 3's design (filters, fallbacks, defensive `.get()` reads, metadata staleness flags). No upstream cleanup gates Step 3 implementation.

**Inputs Step 3 does NOT consume** (so anomalies in these don't block Step 3):
- `system_health.json` — read by `brain_reason.py` Step 5 LLM gates only; M-12 false-DEGRADED issue is Step 5 territory per `project_anchor §7 D-3`
- `proposed_rules.json` — Step 3 doesn't generate proposals; that's Step 6
- `contra_shadow.json` — informational only, not Step 3 logic
- `decisions_journal.json` — doesn't exist yet; Step 6 creates it
- `colab_insights.json` — Step 3 deriver signatures don't reference this

---

## Part 2 — TIER 1 BLOCKERS

**Test for inclusion:** Step 3 implementation cannot ship cleanly without this resolved, OR Step 3 produces wrong output, OR Step 3 smoke checks cannot run meaningfully.

**Result: 0 items.**

**Cited reasoning:**
- Per Part 1 dependency inventory, Step 3's 5 input sources are all clean (M-13 filtered by design; weekly_intelligence staleness reflected in metadata; bridge_state_history fallback exists; mini_scanner_rules + patterns clean).
- All 11 D-items from `project_anchor_v1.md §7` block Steps 4–7, not Step 3:
  - D-1 (bot username) blocks Wave UI / IT-05
  - D-2 (rule conflict resolution) blocks Step 6
  - D-3 (M-12 fix vs ignore-flag) blocks Step 5
  - D-4 (brain weekend cadence) blocks Steps 6+7 (`decisions_journal.json` cadence depends on it; Step 3 just writes derived-view snapshots indexed by `as_of_date`, works regardless of weekend-run policy)
  - D-5 (S-4 failover playbook) blocks brain.yml ship (Step 6+7 territory)
  - D-6 (master_check discipline) blocks nothing immediate
  - D-7 (M-series priority) sequences cleanup, not Step 3
  - D-8 (exit_logic_redesign DRAFT vs REJECT) parallel track, blocks recalibration of brain Step 5 LLM gates if R-multiple distribution shifts; doesn't block Step 3 (Step 3 just measures R-multiple per cohort)
  - D-9 (HYDRAX) out of scope
  - D-10 (Wave UI kickoff) post Step 3+
  - D-11 (colab_sync + diagnostic migration) low-priority infra
- All HIGH gaps (GAP-01, 04, 14, 21, 22) either Wave UI scope OR partially-closed-by-Step-3-itself (GAP-21 + GAP-22)
- Wave 5 prereqs B-1/B-2/B-3/B-4 ALL ✓ shipped per `project_anchor §5.3`
- S-1/S-2/S-3 are advisory not blocking per `wave5_prerequisites` Sequence notes ("not blocking Step 3")

**Implication:** Step 3 is unblocked. User can proceed directly to schema lock-in + implementation whenever ready. No pre-work required.

---

## Part 3 — TIER 2 SHOULD-CLEAR

**Test for inclusion:** Doesn't block Step 3 ship but represents drift between code and docs that's worth fixing pre-Step-3 to prevent re-discovery during Steps 4-7 implementation.

| # | Item ID | One-line description | Why cleanup not blocking | Time est. | Sequencing | Recommended approach | Cost of NOT clearing |
|---|---|---|---|---|---|---|---|
| 1 | **`project_anchor §6.2`** — bridge query plugin doc drift | `bridge_design_v1.md §9.1` says 7 queries; reality is 15 plugins (13 active, 3 orphan per `project_anchor §3.2.1`) | Step 3 doesn't import bridge query plugins (audit Part G: "brain_derive uses its own helpers, no cross-package import"); doc drift only affects future audits | ~30 min | Independent of all other items | Update `bridge_design_v1.md §9.1` table to list 15 plugins with active/orphan status; cross-ref `project_anchor §3.2.1` | Future Wave 5+ session re-discovers the drift, wastes audit cycles |
| 2 | **`project_anchor §6.3`** — engineering_dock.md retirement decision | `doc/engineering_dock.md` (260 LOC) claims "5 critical incidents (C-01..C-05)" all VERIFIED Apr-21 per master_audit; doc effectively superseded | Doc is stale, not load-bearing; user reads fix_table + master_audit + session_context + project_anchor instead | ~15 min | Independent | Either delete OR convert to historical-only with retirement note at top + redirect pointer to current docs | Stale doc continues to mislead any future session that searches it |
| 3 | **`project_anchor §6.8`** — patterns.json vs signal_history count gap (20 records) | Step 3 uses signal_history directly per audit Part D-1; patterns count is informational. Drift documented but not codified inline. | Step 3 ships with correct counts regardless of doc; codifying as inline comment in `derive_cohort_health` docstring is preventative | ~5 min (inline comment during Step 3 implementation) | Folds into Step 3 implementation, not standalone | Add 1-2 line comment in `scanner/brain/brain_derive.py` Step 3 — "patterns.json reports 161; signal_history non-OPEN reports 181; brain uses signal_history directly because of M-13 filter behavior" | Future contributor reading brain_derive sees the count as confusing/wrong |
| 4 | **M-12** — chain_validator step ordering in eod_master.yml | False-positive DEGRADED warns daily (per `fix_table M-12` filed `ddd66b7`). D-3 says M-12 blocks Step 5 cleanly; Step 3 doesn't read system_health so doesn't block Step 3. | Pure workflow YAML edit, low risk; landing pre-Step-3 unblocks D-3 prep for Step 5 (saves a future round-trip). Worth doing now while context is fresh. | ~30-60 min (audit chain step ordering + edit `eod_master.yml` + verify against tomorrow's chain) | Independent of TIER 2 items 1-3; sequenced before Step 5 | Move chain_validator from step 6 to step 9 in `eod_master.yml` (post-pattern_miner + post-rule_proposer) per `fix_table M-12` Recommendation | D-3 inherits; Step 5 implementation either waits for M-12 fix OR adds brain_reason `degraded_input` ignore flag (workaround) |

**TIER 2 total: 4 items, ~80-110 min combined effort.**

---

## Part 4 — TIER 3 CAN-DEFER

**Test for inclusion:** Items legitimately belonging to a different wave / parallel track / dependent on Step 3 outputs / requiring fresh-headed dedicated session.

### 4.1 Wave UI scope (post Wave 5 Steps 3-7 ship + 1-2 weeks observation per D-10)

| Item ID | Description | Target wave | Cite |
|---|---|---|---|
| IT-01 | PWA plugin folder + bridge_state fetch | Wave UI | `fix_table TIER 4` |
| IT-02 | Phase-aware UI banner | Wave UI | `fix_table TIER 4` |
| IT-03 | Sorted signal card renderer | Wave UI | `fix_table TIER 4` |
| IT-04 | Expandable [why?] reasoning | Wave UI | `fix_table TIER 4` |
| IT-05 | Proposal approval card (LE-05 paired) | Wave UI | `fix_table TIER 4` |
| IT-06 | Self-query disclosure card | Wave UI | `fix_table TIER 4` |
| LE-05 | PWA → Telegram deep-link approval | Wave UI (paired with IT-05 per commit `0512cd2`) | `fix_table LE-05` |
| GAP-14 (HIGH) | PWA doesn't read bridge_state.json | Wave UI / IT-01 | `master_audit GAP-14` |
| GAP-15 (MED) | No proposals/approval surface in PWA | Wave UI / IT-05 | `master_audit GAP-15` |
| GAP-16, GAP-17, GAP-18, GAP-30 | Other PWA gaps | Wave UI | `master_audit` PART 10 |
| D-1 | Bot username for deep-link tightening | Wave UI session (recommendation: add `TELEGRAM_BOT_USERNAME` to config) | `project_anchor §7 D-1` |
| D-10 | Wave UI kickoff trigger | Post Wave 5 Steps 3-7 + 1-2 weeks observation | `project_anchor §7 D-10` |

### 4.2 Brain Wave 5 Step 4-7 scope (downstream of Step 3)

| Item ID | Description | Target step | Cite |
|---|---|---|---|
| Brain Step 4 | Pre-verification scaffolding | Wave 5 Step 4 | `brain_design §4 Step 4` |
| Brain Step 5 | LLM reasoning gates | Wave 5 Step 5; depends on D-3 (M-12 fix preferred) | `brain_design §4 Step 5 + §11 Q1/Q2` |
| Brain Step 6 | Unified proposal queue | Wave 5 Step 6; depends on D-2 + D-4 | `brain_design §4 Step 6 + §10 W5-S6` |
| Brain Step 7 | Approval handlers | Wave 5 Step 7; depends on D-2 | `brain_design §4 Step 7 + §10 W5-S7` |
| D-2 | Rule conflict resolution amendment to brain_design §5 | Pre-Step-6 design pass; recommendation: surface conflict in `claim.counter` | `project_anchor §7 D-2` |
| D-3 | M-12 fix vs brain_reason ignore-flag | Pre-Step-5 design pass; recommendation: M-12 fix first (TIER 2 item 4 lands this) | `project_anchor §7 D-3` |
| D-4 | Brain weekend cadence Mon-Sun vs Mon-Fri | Pre-Step-6 design pass; recommendation: Mon-Sun daily | `project_anchor §7 D-4` |
| D-5 | S-4 cron-job.org failover playbook | Concurrent Step 6/7 OR pre-brain.yml | `project_anchor §7 D-5` |
| GAP-21 (HIGH) | No cross-signal correlation awareness | Closes via Step 3 portfolio_exposure → Step 5 LLM gate → Step 6 proposal | `master_audit GAP-21` |
| GAP-22 (HIGH) | No learning-loop surface | Closes via Step 3 cohort_health → Step 5 → Step 6 chain | `master_audit GAP-22` |

### 4.3 Bridge cleanup scope (advisory; not Wave 5-blocking)

| Item ID | Description | Target | Cite |
|---|---|---|---|
| S-1 | q_outcome_today + q_contra_status dedup (composers inline equivalent) | Wave 6+ cleanup; advisory not Step 3-blocking | `wave5_prerequisites S-1` |
| S-2 | Renderer escape pattern grep across L1/L2 (M-31 territory) | Wave 4 cleanup or any later session | `wave5_prerequisites S-2` |
| S-3 | state_writer per-phase signals[] validation | Advisory; brain reads defensively per audit Part C | `wave5_prerequisites S-3` |
| `q_proposals_pending.py` orphan | No caller anywhere; dead code candidate | Either remove OR explicit Step 5+ consumer added | `project_anchor §3.2.1` |

### 4.4 Other open scope (Wave 6+, parallel tracks, low-priority)

| Item ID | Description | Target | Cite |
|---|---|---|---|
| GAP-01 (HIGH) | signal_history multi-writer race | Wave 6+ | `master_audit GAP-01` |
| GAP-04 (HIGH) | cron-job.org SPOF | Wave 7+ via S-4 playbook D-5 | `master_audit GAP-04` |
| M-13 | OPEN-with-outcome_date schema oddity | Standalone investigation when fresh-headed (D-7 priority); writer-side cleanup, current consumer is defensive | `fix_table M-13` |
| M-14 | eod.yml + colab_sync.yml schedule collision | Mooted on eod side post `2fc1f35` migration; collision resolves when colab_sync also migrates (D-11) | `fix_table M-14` |
| M-16 | Open-positions count discrepancy 94 vs 80 | Resolves naturally when UX-03 retires legacy `main.py eod` Telegram path (post Wave 5 Step 7) | `fix_table M-16` |
| D-6 | master_check discipline (relax CLAUDE.md to match observed) | End-of-week decision; recommendation (b) per `project_anchor §7 D-6` | `project_anchor §7 D-6` |
| D-7 | M-12 → M-16 → M-13 priority order | Sequencing decision for cleanup queue | `project_anchor §7 D-7` |
| D-8 | exit_logic_redesign DRAFT vs REJECT | Parallel track, dedicated session, recommendation: DRAFT | `project_anchor §7 D-8` |
| D-9 | HYDRAX Phase 0 timing | Out of scope; separate audit when phase begins | `project_anchor §7 D-9 + roadmap.md Phase 5` |
| D-11 | colab_sync.yml + diagnostic.yml migration to cron-job.org | Low priority post Wave 5 Step 7 | `project_anchor §7 D-11` |
| LE-04 | Telegram approval commands for queries | Wave 5 LE-series (Step 5 area for query proposals via LE-02) | `fix_table LE-04` |
| H-06 | Sector taxonomy (14 CSV vs 8 tracked) | Wave 6+ | `fix_table H-06` |
| H-07 | price_feed.py full adoption | Wave 6+ | `fix_table H-07` |
| INV-01 | DOWN_TRI live divergence | Monitor; gates on Apr 27-29 Choppy resolutions | `fix_table INV-01` |
| AN-04, DATA-02, MC-01..03, HL-01..05, OPS-01..04 | Various Week 2-3+ items | Wave 6+ | `fix_table` |
| prop_001 | DOWN_TRI restriction | DEFERRED; gates on Apr 27-29 Choppy resolutions data | `fix_table prop_001` |
| `roadmap.md` staleness | 10 days behind (per `project_anchor §6.5`) | User explicitly deferred to next session per batch closeout note | `project_anchor §6.5` |
| `fix_table` headline-vs-annotation pattern | Convention question (per `project_anchor §6.7`) | TIER 3; fits fix_table preamble note when convenient | `project_anchor §6.7` |
| Sunday-Apr-26 1KB premarket archive | Anomalous file (per `project_anchor §5.5` + Phase 1 audit) | Low-priority diagnosis; not load-bearing | `project_anchor §5.5` |

**TIER 3 total: ~30 items across Wave UI / Wave 5 Steps 4-7 / Bridge cleanup / Wave 6+ / parallel tracks.** None block Step 3.

---

## Part 5 — Sequencing graph

**Pre-Step-3 work (TIER 1 + TIER 2):**

```
TIER 1 (BLOCKERS):
  ∅ — none

TIER 2 (SHOULD-CLEAR, all parallel):
  ┌─ project_anchor §6.2 (bridge query plugin doc drift)
  ├─ project_anchor §6.3 (engineering_dock retirement)
  ├─ project_anchor §6.8 (count gap docstring — folds into Step 3)
  └─ M-12 (chain_validator step ordering — workflow YAML edit)

  Each is independent. Can ship in any order, even concurrently in one batch commit.
```

**Post-Step-3 chains (TIER 3 sequencing — for context, not pre-work):**

```
Step 3 (derived views) ──┬──→ Step 4 (verify scaffolding)
                          │     │
                          │     ↓
                          │   Step 5 (LLM gates) ←── REQUIRES: D-3 resolved (M-12 fix preferred)
                          │     │
                          │     ↓
                          │   Step 6 (unified queue) ←── REQUIRES: D-2 + D-4 resolved
                          │     │
                          │     ↓
                          │   Step 7 (approval handlers)
                          │     │
                          │     ↓
                          │   brain.yml workflow ship ←── REQUIRES: D-5 (S-4 playbook) resolved
                          │     │
                          │     ↓
                          │   1-2 weeks observation
                          │     │
                          │     ↓
                          └──→ Wave UI kickoff (D-10) ←── REQUIRES: D-1 (bot username)
                                │
                                ↓
                              IT-01..IT-06 + LE-05 ship together as one design pass
                                │
                                ↓
                              GAP-14, 15, 16, 17, 18, 30 close
```

**Parallel tracks (independent of Step 3 chain):**

```
exit_logic_redesign_v1.md DRAFT (D-8) ────→ may inform Step 5 R-multiple recalibration
                                            (parallel; not blocking)

UX-03 retirement ────→ resolves M-16 (open-positions count discrepancy)
                       (post Wave 5 Step 7)

S-4 cron-job.org failover playbook (D-5) ────→ ships pre-brain.yml
                                                (recommendation per highest-cost-of-wrong-call)

M-13 standalone investigation ────→ writer-side cleanup; no consumer crashes
                                    (low priority; D-7)
```

---

## Part 6 — Total time budget

| Tier | Item count | Time estimate | Notes |
|---|---|---|---|
| TIER 1 BLOCKERS | 0 | 0 min | Step 3 is unblocked |
| TIER 2 SHOULD-CLEAR | 4 | ~80–110 min combined | All parallel; can bundle in single commit |
| TIER 3 CAN-DEFER | ~30 | not budgeted pre-Step-3 | Post-Step-3 chains + parallel tracks; each scoped independently |

**Pre-Step-3 envelope: 0–110 min depending on whether TIER 2 lands first vs interleaved with Step 3.**

**Step 3 implementation itself (separate budget per audit Part C):** ~430-500 LOC across `brain_input.py` + `brain_state.py` + `brain_derive.py` + `_run_smoke_brain_derive.py`. Spec audit estimated ~50-60 min implementation post schema lock-in. With smoke + commit + spot-check sample review: ~90-120 min total Step 3 ship.

**Realistic next-session scoping:**
- Skip TIER 2 entirely → straight to Step 3 → ~120 min total session
- TIER 2 first → Step 3 → ~3-4 hour session

---

## Part 7 — Decision points within the build

D-items from `project_anchor_v1.md §7` that require user decision before they can be executed:

### Pre-Step-3 decisions (none required)

Step 3's specific inputs are clean per Part 1; no user decision unblocks Step 3.

The one open decision adjacent to Step 3 is the **schema lock-in for the 4 derived views** — this is in-conversation between user + CC right now (audit Parts A-E surfaced; user lock-in pending). That's not a D-item; it's an operational decision in the current conversation thread.

### Post-Step-3 decisions (deferred to their respective ship sessions)

| D-item | Required before | User input needed | Recommendation per `project_anchor §7` |
|---|---|---|---|
| D-2 | Brain Step 6 design pass | Pick: (a) auto-suppress conflicting / (b) surface in `claim.counter` / (c) propose both with conflict flag | (b) surface conflict — aligns with §6 honest pre-verification |
| D-3 | Brain Step 5 design pass | Pick: (a) M-12 fix first / (b) brain_reason ignore-flag workaround | (a) M-12 fix first (TIER 2 item 4 lands this option pre-Step-5) |
| D-4 | Brain Step 6+7 design pass | Pick: (a) Mon-Sun daily / (b) Mon-Fri only | (a) Mon-Sun daily — preserves brain's "runs nightly" invariant |
| D-5 | brain.yml ship | Pick: (a) ship pre-brain.yml / (b) post / (c) skip | (a) pre-brain.yml — highest cost-of-wrong-call (16-workflow SPOF) |
| D-6 | End-of-week (Sun Apr-27 boundary) | Pick: (a) restore strict / (b) relax CLAUDE.md / (c) keep + log violations | (b) relax CLAUDE.md — observed practice operationally adequate |
| D-7 | Cleanup scheduling | Lock M-12 → M-16 (UX-03) → M-13 priority order | M-12 first, M-16 absorbs into UX-03, M-13 standalone |
| D-8 | Whenever fresh-headed | DRAFT vs REJECT `exit_logic_redesign_v1.md` | DRAFT — Day-6 dominance findings worth capturing |
| D-1 | Wave UI / IT-05 design pass | Add `TELEGRAM_BOT_USERNAME` to `scanner/config.py` (yes/no) | Yes — 2-tap UX materially better |
| D-10 | Post Wave 5 Steps 3-7 + 1-2 weeks observation | Trigger Wave UI track (yes/no) | Wait for usage data per recommendation (b) |
| D-11 | Post Wave 5 Step 7 | Migrate colab_sync + diagnostic to cron-job.org | (a) bundled migration |

---

## Part 8 — Recommended kickoff sequence

### Option A — Straight to Step 3 (CC's recommendation given TIER 1 = 0)

**Session N+1 (next session):**
1. **In-conversation:** review Step 3 audit Parts A-E (already surfaced); lock schemas + answer K/N questions (already drafted in conversation).
2. **Implement Step 3:** `brain_input.py` + `brain_state.py` + `brain_derive.py` + `_run_smoke_brain_derive.py`. ~430-500 LOC total.
3. **Smoke + spot-check:** sandbox run + per-view assertions + idempotency check + real signal_history SHA256 invariant. Surface live-data samples (4 derived view JSONs) for spot-check before commit.
4. **Commit + push:** atomic single commit with `feat(brain): Wave 5 Step 3` message pattern.

**Session N+2 (later):** TIER 2 cleanup bundle (4 items, ~80-110 min) + Step 4 design pass.

**Session N+3:** Step 4 implementation + D-3 resolution + Step 5 design pass kickoff.

**Rationale for Option A:** TIER 2 items are cleanup, not corrections. They don't make Step 3 better; they prevent future re-discovery. Shipping Step 3 first unblocks the entire downstream chain (Steps 4-7, GAP-21+22 partial closure, brain learning loop). TIER 2 can interleave between Wave 5 step ships without slowing momentum.

### Option B — TIER 2 first

**Session N+1 morning (~90 min):** TIER 2 cleanup bundle (project_anchor §6.2 doc fix + §6.3 engineering_dock retirement decision + M-12 chain_validator fix).

**Session N+1 afternoon (~120 min):** Step 3 implementation + smoke + commit.

**Rationale for Option B:** Lands cleanup while context is fresh; M-12 fix unblocks D-3 prep for Step 5 (saves a future round-trip). Trade-off: Session N+1 longer; Step 3 ship slightly delayed.

### Recommendation: Option A

Step 3 ship is the higher-value next move. TIER 2 items are genuinely deferrable (zero impact on Step 3 correctness; modest impact on future audit cycles). Defer TIER 2 to Session N+2 bundle. Ship Step 3 fast; momentum compounds.

If user prefers Option B for completeness/discipline reasons (one cleanup-then-ship session), both paths land Step 3 within Session N+1; Option B just shifts ~90 min of cleanup forward.

---

## Cross-references

- Source-of-truth: `doc/project_anchor_v1.md` (commit `50325c7` §5/§6/§7)
- Operational tracker: `doc/fix_table.md`
- Wave 5 prereqs: `doc/wave5_prerequisites_2026-04-27.md` (B/S/N items)
- Step 3 design: `doc/brain_design_v1.md §4 Step 3` (verbatim 4 deriver function signatures)
- Step 3 audit (in-conversation, not yet doc): Parts A-E surfaced earlier this session covering: (A) 14 future-ready properties × 4 views, (B) locked schemas, (C) implementation contracts, (D) integration risks, (E) open questions K-1..K-5 + N-1..N-5
- Resume-point: `doc/session_context.md` (commit `7995254` batch closeout)

---

_End of build table. This doc sequences existing items only; no new scope. Step 3 is unblocked per Part 1 evidence; user can proceed when ready._
