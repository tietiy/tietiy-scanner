# Consultant Briefings

Version-controlled record of consultations with external consultant on TIE TIY architecture
and validation. Each round documents a discrete decision point and the framework agreed.

Every shadow ops, audit, or workstream commit should reference the relevant round number
in its commit message when the work flows from consultant guidance.

## Round 9 — Phase 3 audits + vp leakage fix briefing

File: round_09_phase3_vp_fix.pdf

Context: Five harness audits on rule_019 completed; vp leakage discovered, fixed, full 37-rule
re-validation done; zero net change in deployable rule count post-fix.

Open question: deployment path forward given Bear-only constraint.

Consultant decision: Path A + Path B in parallel. Deploy rule_019 alone in shadow now.
Add rule_031 only after compressed audit. Re-run discovery on corrected data as separate
research workstream. Four pre-shadow audits required (compressed rule_031 audit, rarity-
impact business audit, regime-transition trust audit, shadow ops framework).

Underweighted risk named: business-model mismatch. valid sleeve != income-capable
operating system.

## Round 10 — rule_031 compressed audit results

File: round_10_rule031_supplement.pdf

Context: Compressed Phase 3 audit on rule_031 (7 audits: 5 mirroring rule_019, 2 NEW
designs for sector concentration + drift vs rule_019).

Material finding: Audit 6 (sector substitutability) revealed IT specialization in rule_031
is NOT load-bearing. 9 of 12 non-IT sectors produce HIGHER lift when substituted into
rule_031's match logic. IT ranks 5 of 13 sectors. rule_031 deployment recommendation
reversed: do NOT deploy as separate trade rule.

Audit 7 (drift vs rule_019) confirmed strict-subset window coverage and surfaced a
+2.07pp coincident-indicator delta — rule_031's firing is informative about regime
strength even though it doesn't add a separate edge.

Open questions surfaced: rule_031 as confirmation overlay? Priority shift in pre-shadow
workstreams? Path B scope expansion to test Chem/Auto/FMCG emergence?

Consultant decisions:
- rule_031: shadow-only logging as confirmation overlay candidate. NOT live sizing yet.
  Compare distributions across rule_031_confirm=0 vs =1 in shadow.
- Workstream priority (revised): (1) shadow ops framework, (2) regime-transition trust
  audit, (3) rarity-impact business audit, (4) Path B replay (parallel).
- Path B scope expanded: explicitly include "would Chem/Auto/FMCG/Other sector-specialized
  Bear+UP_TRI+hot rules have emerged as credible survivors under clean data?" Folded
  into all four replay components.
- Shadow timing: start now, do not wait for Path B. But: shadow != automatic path to
  live capital. Business-model mismatch is sharper post-rule_031-retirement, not softer.

## Branch reference for audit work cited above

- vp leakage fix: vp-leakage-fix branch, commit e8395f95
- rule_019 Phase 3 audits: backtest-lab branch, commits 4d1d2bb..7ed2d98d
- rule_031 compressed audit: rule_031_audit branch, commits e0b35cf0..c87d70a8
