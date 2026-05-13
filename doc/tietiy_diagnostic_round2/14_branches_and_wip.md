# 14 — Branches and Work in Progress

## All branches (sorted by last-commit date)

| Branch | Last commit | Subject | Commits ahead of main |
|---|---|---|---:|
| **shadow_ops_v1** (current) | 2026-05-05 | shadow_ops Step 11: bootstrap + README + architecture doc consolidation | **220** |
| **rule_031_audit** | 2026-05-05 | rule_031 Audit 7: drift_vs_rule_019 — strict subset, +2pp coincident-indicator delta | 214 |
| **vp-leakage-fix** | 2026-05-05 | doc: version-control consultant briefings (Round 9 + Round 10) | 208 |
| **backtest-lab** | 2026-05-05 | Phase 3.6: embargo_sensitivity audit on rule_019 — AMBIGUOUS by spec, FAVORABLE empirically | 206 |
| **v2-integration** | 2026-05-04 | Phase 2: integrate V2 code pack on v2-integration branch | 1 |
| **main** | 2026-05-03 | chore: weekly intelligence report 2026-05-03 17:13 UTC [skip ci] | 0 |

Remote branches:
- `origin/main`, `origin/backtest-lab`, `origin/shadow_ops_v1` (3 of 6 pushed).
- Local-only: `rule_031_audit`, `vp-leakage-fix`, `v2-integration`.

## Branch-by-branch analysis

### `main` (production scanner)

Head commit: `chore: weekly intelligence report 2026-05-03 17:13 UTC [skip ci]`. This is the **production-running** branch. The diagnostic Round 1 was actually against this branch's state (the file mtime of `signal_history.json` is 2026-05-04 which matches a daily eod_master run on 2026-05-03).

### `shadow_ops_v1` (this session's working branch)

**This is a major redesign track.** 220 commits ahead of main. Contents:
- `shadow_ops/` directory with 13 modules (`bootstrap`, `daily_scan`, `lifecycle`, `read_model`, `daily_report`, `alerts`, `pre_scan_check`, `end_of_shadow`, `data_ingest`, `journal`, `regime_classifier`, `schemas`, `__init__`).
- `doc/shadow_ops_v1_architecture.md` (DRAFT pre-implementation review) — 16-section design doc.
- `doc/consultant_briefings/round_09_phase3_vp_fix.pdf` (25 KB)
- `doc/consultant_briefings/round_10_rule031_supplement.pdf` (15 KB)
- 11 build steps shipped per the recent commits (Steps 7-11 are visible in `git log -5`).

**What shadow_ops is:**
A forward-time process-validation harness for the audited rule library (rule_019, rule_031, kill_001). 30-day minimum forward operation. Process-validation, **not** edge-validation. Generates hypothetical trade cards from counterfactual fills; no capital deployed. Operator runs 4 daily commands. Reviews at campaign end. Per Round 10 consultant: "shadow ≠ automatic path to live capital."

**Primary trade rule:** `rule_019_bear_uptri_hot_refinement` — Bear regime + UP_TRI cohort refinement, 71% expected WR, 14.8pp walk-forward lift on 15-year backtest with 2,149 won-resolved matches. Fires ~22× per 182 historical 60-day windows (~1 trade/8 weeks during favorable regimes).

**Confirmation overlay:** rule_031 (Bear+UP_TRI+IT). Logged but not used for sizing.

**Sectoral diagnostic:** kill_001 (Bear+Bank+DOWN_TRI). Doesn't overlap rule_019; logged for context.

**Out of scope for v1:** Bull regime rules (zero survive audit), Choppy regime rules (six are dead schema), other Bear sub_regime variants, BULL_PROXY rules other than kill_001.

**Status:** Architecture doc + 11 implementation steps + bootstrap-ready. Ready to bootstrap a 30-day campaign on demand.

### `vp-leakage-fix` (foundation for shadow_ops)

208 commits ahead of main. Head: `doc: version-control consultant briefings (Round 9 + Round 10)`. Per the shadow_ops architecture doc:

> Audit dependencies: `vp-leakage-fix` branch at `ae519fb6` (corrected `feat_nifty_vol_percentile_20d` + W3 re-classification)

So this branch **fixed a data-leakage bug in a feature** (`feat_nifty_vol_percentile_20d` — Nifty volatility percentile, 20-day). The fix invalidated some prior backtests and forced W3 re-classification. shadow_ops_v1 is built on top of this fix.

### `rule_031_audit`

214 commits ahead of main. Head: `rule_031 Audit 7: drift_vs_rule_019 — strict subset, +2pp coincident-indicator delta`. This branch is auditing the relationship between rule_031 (Bear+UP_TRI+IT) and rule_019. **Strict subset** means rule_031 matches are a subset of rule_019 matches; the +2pp WR delta when both fire together is a coincident-indicator finding (rule_031 fires don't add edge beyond what rule_019 already provides).

This is the audit that justified rule_031's classification as **logged but not used for sizing** in shadow_ops_v1.

### `backtest-lab`

206 commits ahead of main. Head: `Phase 3.6: embargo_sensitivity audit on rule_019 — AMBIGUOUS by spec, FAVORABLE empirically`. This branch is the **research lab** — runs backtest experiments, audits, embargo-sensitivity tests on rule_019. Phase 3.6 finding: by strict spec the rule's edge is ambiguous when embargoed (held out from validation), but empirically still favorable.

### `v2-integration`

1 commit ahead of main, dated 2026-05-04. Head: `Phase 2: integrate V2 code pack on v2-integration branch`. This is a stub — almost no work. Likely an abandoned attempt or placeholder for a future integration.

## Which branch has the answer to the current problem?

The current problem (per Round 1 + Round 2 findings):
- DOWN_TRI structurally broken
- UP_TRI×Choppy bleeding
- Regime detector conflating sub-states
- Brain proposals expired without action
- Day-6 forced exits dominate, no target rule on most cohorts

**`shadow_ops_v1` is the answer.** It explicitly:
- **Retires the open-ended DOWN_TRI / BULL_PROXY / UP_TRI×Choppy approach** in favor of rule_019 only.
- **Replaces the Bear/Choppy/Bull regime classifier** with `shadow_ops/regime_classifier.py` (computes `regime` + `sub_regime` via canonical `add_derived_features`).
- **Adds `sub_regime`** as a first-class concept — exactly what Round 1 recommended (Choppy needs to be split).
- **Audit-faithful T+1 entry, no gap-fill, 6-day inclusive D1-D6 hold** — same Day-6 limitation, but consultants accepted this as the audited rule's expected behavior.

So shadow_ops_v1 is a much more disciplined supersession of the current scanner. Whether the user wants to deploy it depends on whether they're OK with the **sleeve rarity** (~1 trade per 8 weeks). The consultant Round 10 explicitly flagged: "shadow != automatic path to live capital. Business-model mismatch is sharper post-rule_031-retirement, not softer."

## Verdict

- `main` is production but stale (last update May 3).
- `shadow_ops_v1` is the most-advanced redesign track, ready to bootstrap a 30-day campaign.
- `vp-leakage-fix` is its foundation (data-leakage fix).
- `rule_031_audit` and `backtest-lab` are supporting research branches.
- `v2-integration` is essentially abandoned.

The Round 1 surgical fix plan (complete brain production-fire, broaden kill_001, add Bull label, add BULL_PROXY target) **was scoped to the live scanner on `main`**. shadow_ops_v1 is an alternative that bypasses those fixes by retiring the underlying signal types entirely. The user faces a fork: incremental fix on the current scanner versus campaign-start on shadow_ops_v1.
