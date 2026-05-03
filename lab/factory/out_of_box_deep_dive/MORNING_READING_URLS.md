# Morning Reading URLs — Deep Dive Output

**Date:** 2026-05-03 (last task before sleep)
**For:** Tomorrow morning's Fold 7 review before any deployment
decision
**Branch:** `backtest-lab` at `a19aecc1`
**All commits:** pushed to `origin/backtest-lab` ✓

---

## Suggested reading order (60-90 min total)

### 🔴 PRIMARY (read first, 15 min)

**1. FINAL_SYNTHESIS.md** — combined findings + decision tree + single
concrete next action (write Deployment Contract by 10 AM)

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/out_of_box_deep_dive/FINAL_SYNTHESIS.md

---

### 🟠 BRUTAL ASSESSMENT (read second, 15 min)

**2. brutal_assessment.md** — Opus 4.7's hardest output. "You over-
engineered a solution to a problem you don't yet have." Reading order
sensitive: read AFTER FINAL_SYNTHESIS so you have the framing.

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/out_of_box_deep_dive/output/brutal_assessment.md

**3. sonnet_critique.md** — Sonnet 4.5's critique of Opus's deep dive.
Identifies where Opus pulled punches and the strategic question Opus
never asked: *"Why are you trading quantitatively at all?"*

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/out_of_box_deep_dive/sonnet_critique.md

---

### 🟡 SUPPORTING DETAIL (read if FINAL_SYNTHESIS triggers questions, 30 min)

**4. independent_diagnosis.md** — Opus identified 4 deeper problems
(circular validation, win_*/Path B anomaly, methodology overfit,
complexity-without-evidence). Data-starvation is just symptom 1 of 4.

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/out_of_box_deep_dive/output/independent_diagnosis.md

**5. path_critique.md** — Opus rated my 10 paths. Path 9 (paper
trading 60 days) SIGNIFICANTLY OVERRATED. Path 6 (multi-detector)
OVERRATED. Path 4 (regime tolerance) is band-aid. The missing path:
"Delete 32 rules, deploy 5."

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/out_of_box_deep_dive/output/path_critique.md

**6. unconventional_alternatives.md** — Opus's 3 alternatives:
(a) Delete 32 rules deploy 5; (b) Trade 5-rule system 6 months FIRST
then revisit Lab; (c) Hire human quant for $300-500 4-hour review.

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/out_of_box_deep_dive/output/unconventional_alternatives.md

**7. recommended_combination.md** — Opus's recommended Phase 0/1/2/3
sequence. 2-week ramp not 10-week. Walk-forward OOS test as Day 1-3
action.

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/out_of_box_deep_dive/output/recommended_combination.md

---

### 🟢 BACKGROUND (only if needed, ~30 min)

**8. trader_expectations.md** — emotional + analytical preparation.
95% live observed → ~57-72% calibrated WR shift. Already wrote this
in Step 5 L4; re-read if anchoring drifts.

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/step5_finalization/L4_opus_output/trader_expectations.md

**9. BACKTEST_REPORT.md** — production backtest findings. 8
READY_TO_SHIP, 29 NEEDS_LIVE_DATA. Sonnet's PB4 critique downgraded
NEEDS_REVIEW → NEEDS_LIVE_DATA.

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/factory/production_backtest/BACKTEST_REPORT.md

**10. LAB_PIPELINE_COMPLETE.md** — full Lab pipeline summary
(Steps 1-5, $21.41 spend, 37 rules at 100% PASS+WARN, 3 operational
gaps Sonnet identified).

→ https://github.com/tietiy/tietiy-scanner/blob/backtest-lab/lab/LAB_PIPELINE_COMPLETE.md

---

## Top 3 to open first

1. **FINAL_SYNTHESIS.md** (the morning briefing — single page of
   combined recommendation)
2. **brutal_assessment.md** (the part you don't want to read; read it
   anyway)
3. **sonnet_critique.md** (catches Opus's pulled punch about premise)

## Reading time budget

- 🔴 Primary trio (1+2+3): **45 minutes** focused
- 🟡 Supporting detail (4-7): 30 min if questions arise
- 🟢 Background (8-10): only if needed

**Single concrete action by 10 AM IST tomorrow** (per FINAL_SYNTHESIS):
write the 1-page Deployment Contract. If it can't be written in 30
minutes, that itself is the answer — step away from quantitative
trading for 90 days.

---

## Access notes

- Repo `github.com/tietiy/tietiy-scanner` — confirm GitHub mobile
  signed in to the `tietiy` account (or repo is public — verify on
  first link click)
- Branch is `backtest-lab` — NOT main. URLs explicitly use
  `/blob/backtest-lab/` path
- All files render as rendered Markdown on GitHub mobile (no source
  view needed)
- Files are short (4-13 KB each); load fast on mobile
- Total payload: ~85 KB across 10 files

---

## Quick cumulative spend recap

| Phase | Spend |
|---|---|
| Lab Steps 1-5 | $21.41 |
| Production backtest | $0.03 |
| Deep dive (D1-D3) | $3.68 |
| **TOTAL** | **$25.12** |

Trivial in absolute dollars. Significant in opportunity cost (5+ weeks
paused trading). The next $0 spent on Lab work — for 6 months — is the
disciplined choice if Deployment Contract gets written + signed.
