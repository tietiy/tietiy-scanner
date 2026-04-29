# TIY — Tietiy Inventory Yardstick

**Last updated:** 2026-04-30 mid-day IST
**Last update commit:** (this commit)
**Maintenance discipline:** updated whenever an item ships, a new gap surfaces, or a phase boundary crosses (per Section K).

**Reading guide:**
- ✅ = SHIPPED with commit hash cited
- ⏸ = PENDING (in flight or scheduled)
- 🔒 = LOCKED but not yet executed (decision made, work pending)
- ❓ = OPEN decision (awaiting design pass or user input)
- 📋 = DEFERRED (intentional; gated on observation/dependency)
- ⚠️ = BLOCKER (blocks other work)

---

## SECTION A — WAVE 5 BACKEND (brain layer)

Status: COMPLETE 2026-04-29

| ID | Item | Status | Commit | Notes |
|----|------|--------|--------|-------|
| A-1 | Wave 5 Step 1 — schema lock (brain_design_v1.md blueprint) | ✅ | 720c127 | Pre-this-session |
| A-2 | Wave 5 Step 2 — folder skeleton | ✅ | 060d7c9 | Pre-this-session |
| A-3 | Wave 5 Step 3 — derived views (4 derivers) | ✅ | 76a85f4 | This session |
| A-4 | Wave 5 Step 4 — verification framework + 4 generators | ✅ | 8e5be29 | This session |
| A-5 | Wave 5 Step 5 — LLM reasoning gates | ✅ | c047fd2 | This session |
| A-6 | Wave 5 Step 6 — unified queue + decisions_journal + dual-write | ✅ | 05570fb | This session |
| A-7 | Wave 5 Step 7 — Telegram approval handlers | ✅ | 1e1c786 | This session |
| A-8 | brain.yml workflow + main.py brain mode | ✅ | d874180 | Tier 1 Item 1 |
| A-9 | brain.yml CWD fix + api_check mode | ✅ | e10454e | Mid-day Apr 30 fix |

---

## SECTION B — PRODUCTION FIRE INFRA (workflows + secrets + cron)

| ID | Item | Status | Owner | Notes |
|----|------|--------|-------|-------|
| B-1 | ANTHROPIC_API_KEY GitHub secret | ✅ | user | Verified 2026-04-30 mid-day api_check fire |
| B-2 | cron-job.org entry — brain.yml @ 22:00 IST | ✅ | user | Confirmed live |
| B-3 | cron-job.org entry — brain_digest.yml @ 22:05 IST | ✅ | user | Confirmed live |
| B-4 | cron-job.org entry — eod.yml @ 16:15 IST | ✅ | user | Confirmed live |
| B-5 | First scheduled brain.yml fire | ⏸ | passive | Apr 30 22:00 IST tonight |
| B-6 | First scheduled brain_digest.yml fire | ⏸ | passive | Apr 30 22:05 IST tonight |
| B-7 | First Sat/Sun brain run validation | ⏸ | passive | May 2-3 weekend |

---

## SECTION C — TIER 1 BATCH CLEANUP (next session entry)

| ID | Item | Status | Time est | Notes |
|----|------|--------|----------|-------|
| C-1 | fix_table.md M-12 flip + new monitoring entries | ⏸ | 5-10 min | Tier 1 Item 3 |
| C-2 | project_anchor §3.3 brain module update (Wave 5 1-2 → 1-7 SHIPPED) | ⏸ | 10 min | Tier 1 Item 4 |
| C-3 | session_context.md namespace disambiguation (S7-D-X vs anchor-D-X) | ⏸ | 10 min | P-1 from Section 4 stocktake |
| C-4 | fix_table.md BR-series + BR-02/BR-03 doc-drift flip (PARTIAL/PENDING → ✅) | ⏸ | 10 min | Bridge audit findings 2026-04-30 |

---

## SECTION D — DECISIONS pending (project_anchor §7 D-NN)

**Note:** project_anchor §7 D-NN namespace is DIFFERENT from Step 7 internal D-7/D-9/D-11 lock numbering. C-3 will disambiguate session_context.md accordingly.

| ID | Topic | Status | Recommendation |
|----|-------|--------|----------------|
| D-1 | Bot username for deep-link tightening | ❓ | Wave UI scope |
| D-2 | Rule conflict resolution amendment to brain_design §5 | ✅ RESOLVED | 27b60cb + 997d4af + ee4007d |
| D-3 | M-12 false-DEGRADED propagating to brain reasoning | ✅ RESOLVED | fe0a669 |
| D-4 | Brain weekend cadence | ✅ RESOLVED | 27b60cb (Mon-Sun) |
| D-5 | S-4 cron-job.org failover playbook | ❓ | Ship pre-Step-8 |
| D-6 | master_check.yml discipline | ❓ | Relax CLAUDE.md to match practice |
| D-7 | M-12 / M-13 / M-16 sequencing | ⏸ PARTIAL | M-12 done; M-13 + M-16 remain |
| D-8 | exit_logic_redesign DRAFT vs REJECT | ❓ | DRAFT (parallel; fresh session) |
| D-9 | HYDRAX Phase 0 timing | 📋 | Gates Waves 1-5 stable + 2 weeks observation |
| D-10 | Wave UI kickoff trigger | ❓ | Post Wave 5 + 1-2 weeks observation |
| D-11 | colab_sync + diagnostic migration timing | ❓ | Bundle migration; low priority |

---

## SECTION E — fix_table.md M-NN (PENDING only)

| ID | Topic | Priority | Notes |
|----|-------|----------|-------|
| M-13 | 8 signal_history records carry outcome='OPEN' AND outcome_date set | L | Standalone investigation per anchor-D-7 |
| M-14 | eod.yml + colab_sync.yml schedule collision (16:15 IST) | M | Defer per fix_table |
| M-16 | open-positions count discrepancy (94 vs 80 in parallel digests) | M | Resolves at UX-03 retirement |
| M-NEW-1 | digest size scaling threshold (Step 7 V-8 known monitoring point ~3800 chars) | L | File during C-1 |

---

## SECTION F — BEFORE WAVE UI (must-clear before Step 8 design pass)

| ID | Item | Status | Gate |
|----|------|--------|------|
| F-1 | ≥1 week trader feedback on Telegram-only flow | ⏸ | Time-based; ~May 6 earliest |
| F-2 | First 5+ days production brain runs validated | ⏸ | Apr 30 → May 5 |
| F-3 | First Sat/Sun brain run behavior validated | ⏸ | May 2-3 |
| F-4 | Choppy DOWN_TRI cluster resolution observed | ⏸ | LUPIN/OIL/ONGC outcomes Apr 27-29 |
| F-5 | M-13 standalone investigation closed | 🔒 | Per anchor-D-7 partial |
| F-6 | Tier 1 batch cleanup complete (C-1 .. C-4) | ⏸ | Next session ~30-45 min |

---

## SECTION G — WAVE UI (Step 8 + LE-05 + Wave UI design)

| ID | Item | Status | Estimated scope |
|----|------|--------|-----------------|
| G-1 | Wave 5 Step 8 — PWA Monster tab design pass | 🔒 | Design pass session ~3-4 hr |
| G-2 | Wave 5 Step 8 — implementation | 🔒 | ~600-1000 LOC; multi-session |
| G-3 | LE-05 mechanism (PWA → Telegram deep-link approval) | 🔒 | Bundled with Step 8 |
| G-4 | Wave UI design pass — overall (IT-01..IT-06 + Session 4) | ❓ | After Step 8 ships |

---

## SECTION H — AFTER WAVE UI (HYDRAX + parallel tracks)

| ID | Item | Status | Notes |
|----|------|--------|-------|
| H-1 | HYDRAX Phase 0 — environment setup | 📋 | MacBook + Cursor IDE; per anchor-D-9 |
| H-2 | HYDRAX 16-week build plan | 📋 | Gates on Phase 0 |
| H-3 | HYDRAX 12-week validation plan | 📋 | Gates on build |

---

## SECTION I — HYGIENE (low priority cleanup)

| ID | Item | Status | Time est |
|----|------|--------|----------|
| I-1 | doc/roadmap.md refresh (10+ days stale; mtime 25 Apr) | ⏸ | ~30 min |
| I-2 | doc/engineering_dock.md retire | ⏸ | ~15 min |
| I-3 | doc/exit_logic_redesign_v1.md DRAFT (per anchor-D-8) | 🔒 | ~500-800 LOC; fresh session |
| I-4 | brain_derive return-data cleanup (P-6; eliminate run_brain roundtrip) | ⏸ | ~30 min |
| I-5 | doc/pre_wave5_resume_build_table_v1.md retire (obsolete post-Wave-5) | ⏸ | ~5 min |
| I-6 | doc/wave5_prerequisites_2026-04-27.md retire (superseded) | ⏸ | ~5 min |
| I-7 | fix_table.md BR-01..BR-07 PARTIAL/PENDING → ✅ flip (Bridge audit drift; folds into C-4) | ⏸ | ~10 min |

---

## SECTION J — OBSERVATIONAL TRIGGERS (revisit when X happens)

| ID | Trigger | Action when triggered |
|----|---------|----------------------|
| J-1 | First brain.yml production fire | Verify chain succeeded; spot-check output/brain/* |
| J-2 | First Telegram digest arrives | Verify rendering, conflict badges, /approve copy on mobile |
| J-3 | First /approve action in production | Verify decisions_journal append + mini_scanner_rules mutation + status flip |
| J-4 | First Sat brain run | Verify weekend tone; reasoning_log entries skipped/short-circuit |
| J-5 | First contradiction-type proposal surfaces | Verify red badge rendering + counter.evidence + /explain expand |
| J-6 | Card budget exceeds 3800 chars | Re-tune per-card budget per Step 7 V-8 monitoring point |
| J-7 | LLM cost exceeds $1/run soft warning | Investigate; possibly suppress 1+ gate per §11 Q1 default |

---

## SECTION K — MAINTENANCE DISCIPLINE

How TIY stays current:

1. **Inline updates** — when CC ships a commit that changes a TIY row, CC updates the row in the same commit (or follow-up commit if scope creep concern).
2. **Trigger-word recall** — when user asks "what's left" / "show TIY" / "TIY status" / "give me TIY", CC reads doc/tiy.md and surfaces relevant sections (not all — too long).
3. **Section ordering** — A → L is reading order; sections most-relevant-now first.
4. **No stale rows** — items >60 days unchanged should be reviewed: ✅ → archived OR ❓ → re-decision OR removed.
5. **Cross-reference fix_table.md** — TIY rows mirroring M-NN cite the M-NN id; never duplicate full description.
6. **Cross-reference anchor §7** — TIY rows mirroring D-NN cite the D-NN id.
7. **Status flip protocol**: ⏸ → ✅ with commit hash on ship; ❓ → 🔒 on lock without execution; 🔒 → ✅ on execution; archive ✅ rows older than 90 days to doc/tiy_archive.md.
8. **Section additions**: new tracking categories surface as new sections (M, N, ...) — don't bloat existing sections.
9. **Cross-section row migration**: when an item starts in one section but life-cycles to another (e.g., F-6 Tier 1 cleanup ⏸ → ✅ ships → archives to L or removes), update the appropriate sections in same commit. Don't leave duplicate or contradictory rows across sections.
10. **Bridge-layer rule**: items in Section L (Bridge reference) NEVER move to other sections. If new Bridge work surfaces (future Wave 6, maintenance fix, etc.), file as new L-N row with own status. Section L is reference layer; other sections are action layers.

---

## SECTION L — BRIDGE LAYER (reference; all complete)

| ID | Wave | Scope | Status | Evidence |
|----|------|-------|--------|----------|
| L-1 | Bridge Wave 1 | Pre-bridge prep (CACHE-01, UX-08, fix_table rewrite, mini_scanner_rules seed, AN-02) | ✅ COMPLETE | fix_table.md:51 "ALL SHIPPED" |
| L-2 | Bridge Wave 2 | Backend foundation (16 files + scanner/bridge/ + TG-01 + 3 schema bug fixes) | ✅ COMPLETE | Module structure verified; commits ebab610 + 9545af5 + 7876518 |
| L-3 | Bridge Wave 3 | Composers (BR-02/03/04 Sessions A/B/C/D) + workflows (BR-05) + Telegram renderers (BR-07) | ✅ COMPLETE | 32e8b13 premarket, c469722 + 78c1eae postopen, c94e523 + 19d4146 + 7b96a97 + f9d4746 EOD |
| L-4 | Bridge Wave 4 | LE-07 + prop_005 + LE-06 + prop_007 (4/5 SHIPPED + LE-05 DEFERRED to Wave UI) | ✅ COMPLETE (4/5) | c43189a + 550b5f0 + 7b96a97 + c647e94; LE-05 paired with G-3 |
| L-5 | Bridge Wave 5 | Brain layer Steps 1-7 (Step 8 DEFERRED to Wave UI) | ✅ COMPLETE (7/7 backend) | This session: 76a85f4..e10454e |

**Production-fire status**: bridge_state.json daily firing continuous (3 phases per day Mon-Fri); last write Apr 30 10:50 IST today's POST_OPEN.

**Section discipline**: this section is REFERENCE, not action items. Items here are ✅ COMPLETE; row updates only happen if Bridge work resurfaces (hypothetical Wave 6 or maintenance fixes). Per Section K rule 10, Bridge items NEVER migrate to other sections.
