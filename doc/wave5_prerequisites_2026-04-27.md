# Wave 5 Prerequisites — 2026-04-27

**Companion to:** `doc/brain_design_v1.md` (Step 1, just shipped). This doc identifies what blocks the remaining 7 build steps.
**Source for gap IDs:** `doc/master_audit_2026-04-27.md` PART 10 (33 gaps catalogued, 7 HIGH).
**Audit discipline:** every item below cross-references a specific gap or file location. No new claims.

**Amended 2026-04-27 evening:** B-2 (GAP-13 PWA EOD-phase guard) moved from BLOCKING to NICE-TO-HAVE (now N-9) after grep verification confirmed PWA does not read `bridge_state.json`. B-1 (Session D) can now ship standalone — no PWA-side prerequisite. See `master_audit_2026-04-27.md` GAP-13 for the verification trail.

---

## How to read this doc

Three buckets, each ranked by sequence:

- **BLOCKING** — work that must complete before Wave 5 Step 2 (folder skeleton) can ship safely, OR before a specific later Step can ship. Small list: 4 items.
- **SHOULD-FIX** — work that doesn't strictly block Wave 5 but materially improves the foundation it lands on. Better before Step 4 (LLM integration), where ambiguity gets expensive. 5 items.
- **NICE-TO-HAVE** — work that can defer until after Wave 5 ships. Either low-severity or genuinely independent. 8 items.

Effort labels: **XS** (<30 min), **S** (30-90 min), **M** (half-session), **L** (full session+).

---

## Section 1 — BLOCKING

These must clear before the listed Wave 5 step ships. Work the list top-down.

### B-1. Wave 3 Session D — `.github/workflows/eod.yml`

- **Blocks:** Brain Step 3 (derived views) at full fidelity. Brain falls back to POST_OPEN snapshots without EOD data per `brain_design_v1.md §11 Q5`, so technically not a hard block — but the fallback path is degraded and self-defeating to ship into Wave 5. Treat as BLOCKING for clean Step 3.
- **Cross-ref:** Master audit GAP-NONE (Session D is in-flight, not a gap); `fix_table.md` BR-04 status PARTIAL; `session_context.md` Bridge Build Status table.
- **Files:** `.github/workflows/eod.yml` (new); cron-job.org dashboard schedule (external).
- **Effort:** S (workflow YAML mirrors `postopen.yml`); + cron-job.org config (external, manual).
- **Sequence:** ship before Brain Step 2.

### B-2. _(Removed 2026-04-27 evening — see N-9)_

GAP-13 reclassified to LOW after PWA grep verification. Moved to NICE-TO-HAVE bucket as **N-9**. Original claim that this blocks Session D was wrong — PWA doesn't read bridge_state, so EOD SDR shape divergence has no current consumer.

### B-3. Anthropic SDK in venv + `ANTHROPIC_API_KEY` secret

- **Blocks:** Brain Step 5 (LLM gates).
- **Cross-ref:** Master audit doesn't enumerate this (out of scope of code audit); explicit prerequisite per `brain_design_v1.md §1` constraint 4 + §4 Step 5.
- **Files:** `requirements.txt` (add `anthropic`); `.venv` (`pip install anthropic`); GitHub Actions secret `ANTHROPIC_API_KEY` for the eventual brain-nightly workflow; local `.env` or shell export for CLI testing.
- **Effort:** XS (pip install + secret set); + verify at least one successful test call before Step 5 starts.
- **Sequence:** any time before Step 5; ideally early so we have time to validate.

### B-4. Brain Step 1 doc lock

- **Blocks:** Steps 2-8 conceptually.
- **Status:** ✅ shipped tonight (`720c127`). Listed for completeness.
- **Cross-ref:** Master audit GAP-33 — closed.
- **Effort:** done.

**BLOCKING tally:** 1 in-flight (B-1), 1 setup (B-3), 1 done (B-4), 1 removed (B-2 → N-9). Effective remaining work: B-1 (Session D, can ship standalone) + B-3 (Anthropic SDK setup). Single focused session.

---

## Section 2 — SHOULD-FIX (before Step 4)

These don't block Wave 5 starting, but every one materially improves the foundation Step 4 (verification scaffolding) and Step 5 (LLM reasoning) land on. Work the list top-down where it intersects active sessions.

### S-1. GAP-07 + GAP-08 — `q_outcome_today` and `q_contra_status` duplicate logic

- **Cross-ref:** Master audit GAP-07 (MEDIUM), GAP-08 (MEDIUM).
- **Why before Step 4:** Brain's derived views may want to call these query plugins (cohort_health derives from outcome_today; regime_watch may use contra_status). If the queries exist as plugins but the bridge composers inline equivalent logic, brain inherits the inconsistency.
- **Files:** `scanner/bridge/queries/q_outcome_today.py` + `scanner/bridge/queries/q_contra_status.py` (already exist); `scanner/bridge/composers/eod.py` `_select_resolutions_today` (delete inline, call plugin); `scanner/bridge/composers/premarket.py` `_build_contra_block` (move into `q_contra_status`).
- **Effort:** S (~60 min, plus smoke retest).
- **Sequence:** Wave 3 Session C cleanup or early Wave 5 Step 3.

### S-2. GAP-31 — renderer escape pattern grep

- **Cross-ref:** Master audit GAP-31 (LOW). Caught + fixed in EOD renderer; pattern not yet audited in L1/L2.
- **Why before Step 4:** Brain's `brain_telegram.py` will be a new renderer. If the same anti-pattern exists in L1/L2 renderers, codifying the lesson NOW in CLAUDE.md (already done) is good but not enough — fix the actual bugs first if any are present.
- **Files:** `scanner/bridge_telegram_premarket.py`, `scanner/bridge_telegram_postopen.py` (grep for `f"...{_esc(x)} <literal-with-reserved-char> {_esc(y)}..."`).
- **Effort:** S (~45 min — grep + read + decide + fix).
- **Sequence:** any Wave 4 cleanup session.

### S-3. GAP-32 — state_writer per-phase signals[] validation

- **Cross-ref:** Master audit GAP-32 (MEDIUM).
- **Why before Step 4:** Brain reads `bridge_state_history/*` and assumes shapes per phase. If state_writer doesn't enforce shape, brain's read code has to defensively handle every variation. Better to enforce at write time + let brain trust the schema.
- **Files:** `scanner/bridge/core/state_writer.py` (`_validate_state` extension); `scanner/bridge/core/sdr.py` (perhaps adopt a separate `EODSDR` dataclass or accept the divergence).
- **Effort:** M (need to decide between unifying SDR shapes vs validating each phase's permissible shape).
- **Sequence:** Wave 4 cleanup or Wave 5 Step 3 pre-req.

### S-4. GAP-04 — cron-job.org failover playbook

- **Cross-ref:** Master audit GAP-04 (HIGH).
- **Why before Step 4:** Brain's nightly run at 22:00 IST will be cron-job.org-triggered (per `brain_design_v1.md §2`). Adding another cron-job.org dependency without a failover plan increases SPOF risk.
- **Files:** `doc/operations_runbook.md` (NEW); document how to manually trigger the 14 cron-job.org workflows when the service is down. No code change.
- **Effort:** S (documentation only).
- **Sequence:** any time before brain workflow ships.

### S-5. LE-06 — demotion framework (Wave 3 Session C)

- **Cross-ref:** `fix_table.md` LE-06 status APPROVE READY; `session_context.md` Bridge Build Status BR-04 Session C.
- **Why before Step 4:** Brain's tier classifier (§3 of `brain_design_v1.md`) auto-demotes on threshold breach. Wave 3's `LE-06` boost-pattern demotion warnings populate `state.summary.pattern_updates[]`. Brain will read those updates as one input. Cleaner if the field is populated by a real Wave 3 path before brain depends on it.
- **Files:** `scanner/bridge/composers/eod.py` (rolling-window WR helper + demotion warning emission).
- **Effort:** M (Wave 3 Session C scope, ~1.5 hrs per `master_audit_2026-04-27.md` PART 5 / Sessions C+D plan).
- **Sequence:** between B-1 and Brain Step 3.

**SHOULD-FIX tally:** 5 items. ~3-5 hours total work spread across Wave 3 Session C/D + a Wave 4 cleanup session.

---

## Section 3 — NICE-TO-HAVE (defer until after Wave 5 ships)

Genuinely deferrable. Listed for completeness so they're not forgotten.

### N-1. GAP-06 — UTC-labeled-as-IST commit messages
- **Effort:** XS. Cosmetic only. `TZ='Asia/Kolkata' date ...` in 3 bridge workflows.

### N-2. GAP-10 — `ltp_updater.yml` concurrency group
- **Effort:** XS. Add `concurrency: ltp-updater` group. Real but low-probability race.

### N-3. GAP-11 — failure-handling style split
- **Effort:** XS. Standardize on `if: failure()` across all workflows.

### N-4. GAP-12 — `morning_scan` push-exhaustion exit-1
- **Effort:** XS. Add `exit 1` after the for-loop.

### N-5. GAP-09 — `recover_stuck_signals` audit log + dry-run default
- **Effort:** S. Operational hardening.

### N-6. GAP-19 — schema-discipline pattern legacy cleanup
- **Effort:** S. Spring-clean of pre-Apr-26 patterns. Already covered in CLAUDE.md going forward.

### N-7. GAP-28 + GAP-30 — PWA legacy patch comments + analysis.js orphan
- **Effort:** S. Cleanup during Wave UI session.

### N-8. GAP-29 — P-01 broker P&L correlation ritual
- **Effort:** M (process design, not code). Trader-skipped on 2026-04-23. Acknowledged ongoing risk; not blocking any code.

### N-9. GAP-13 — PWA EOD-phase render handling
- **Cross-ref:** Master audit GAP-13 (LOW, reclassified 2026-04-27 evening). Originally B-2 in this doc.
- **Why deferred to Wave UI / IT-01:** PWA does not currently read `bridge_state.json` (verified 2026-04-27 evening via grep — zero references in `output/*.js` or `output/analysis/*.js`). EOD SDR shape divergence has no current consumer; no production risk. Becomes relevant only when Wave UI / IT-01 wires PWA-to-bridge-state integration, at which point the per-phase render strategy is part of IT-01's design — not a one-line guard.
- **Effort:** L (folded into Wave UI work).
- **Sequence:** Wave UI / IT-01 design pass.

**NICE-TO-HAVE tally:** 9 items (was 8; +1 from B-2 reclassification). ~4-6 hours combined; none time-sensitive.

---

## Recommended sequence

```
Next session:
   1. Ship B-1 standalone (Wave 3 Session D).
      → eod.yml workflow
      → cron-job.org dashboard update
      (B-2 removed — PWA doesn't read bridge_state, no guard needed.
       PWA EOD-phase render handling now N-9, deferred to Wave UI / IT-01.)
   2. Verify B-3 (anthropic SDK, API key).
      → pip install + secret set + one test call

Following session:
   3. S-5 — Wave 3 Session C (LE-06 demotion warnings).
   4. S-1 — q_outcome_today + q_contra_status dedup.
   5. Brain Step 2 — folder skeleton.

Wave 5 main thread:
   6. Brain Step 3 — derived views.
   7. Brain Step 4 — verify scaffolding (S-2, S-3 ideally cleared first).
   8. Brain Step 5 — LLM gates (B-3 must be cleared).
   9. Brain Steps 6-7 — unified queue + handlers.

Wave UI track (parallel, separate sessions):
   - Brain Step 8 (PWA Monster tab) + LE-05 + IT-series.

Backlog (cleanup, low priority):
   - All NICE-TO-HAVE items, distributed across cleanup sessions.
```

---

## Final tally

| Bucket | Count | Total effort |
|---|---|---|
| BLOCKING | 3 (1 done, 2 active) _was 4 before B-2 reclassification_ | ~one session for B-1 + B-3 |
| SHOULD-FIX | 5 | ~3-5 hours across multiple sessions |
| NICE-TO-HAVE | 9 _was 8; +1 from B-2 → N-9_ | ~4-6 hours combined; defer |

**Bottom line:** Wave 5 backend (Brain Steps 2-7) is unblocked after one focused session that ships eod.yml + Anthropic SDK setup. (Originally a third item — PWA EOD guard — was listed; it has been correctly removed after grep verification proved PWA doesn't read bridge_state.) The other prerequisite-flagged items are quality improvements, not gates.

---

_End. Cross-reference index for next session: GAP IDs map to `master_audit_2026-04-27.md` PART 10 table; LE / BR codes map to `fix_table.md` tier sections._
