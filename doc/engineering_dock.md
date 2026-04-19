# TIE TIY Engineering Dock

**Purpose:** Single source of truth for what's being built, shipped, and considered.
**Owner:** Abhishek (decisions) + Claude (proposals)
**Update frequency:** Daily during active development.

---

## 🚢 CURRENT STATE

**Last ship:** 2026-04-19 — Session 3: Kill Switch + Contra Shadow + Rule Proposer + Regime Audit + Morning Brief + Weekly Review
**Production status:** STABLE
**Open incidents:** NONE

---

## 🟢 SHIPPED (last 30 days)

| Date | Release | Files | Status |
|---|---|---|---|
| 2026-04-19 | Session 3: Kill + Contra + Proposer + Brief | 15 files | ✅ Stable |
| 2026-04-19 | Phase A + Phase B (Pattern Miner, eod_master) | 14 files | ✅ Stable |
| 2026-04-17 | V2 53/53 (cache, UI, workflows) | 11 files | ✅ Stable |
| 2026-04-10 | Bugs B1-P1 | 8 files | ✅ Stable |

---

## 🟡 PENDING REVIEW

*Claude writes here. Abhishek approves/rejects.*

(none — all current session proposals approved)

---

## 🔴 BLOCKED / NEEDS DISCUSSION

- **Regime classifier rewrite** — waiting for 7 days of regime_debug.json data
- **Contra shadow activation** — waiting for n=20 samples in contra_shadow.json
- **DOWN_TRI validation** — if patterns.json still shows 0% WR after n=20, permanent kill

---

## 🎯 NEXT RELEASE CANDIDATES (not yet proposed)

- **Auto-apply pattern rules** — currently manual via /approve_rule, could be automatic once confidence is high
- **Intraday consolidation** — intraday_master.yml absorbing ltp_updater + stop_check
- **Morning consolidation** — morning_master.yml absorbing morning_scan + scan_watchdog + open_validate
- **New UI refresh** — Session 4 plan (12 UI files, 5 new)
- **Score recalibration** — Phase 3 when n≥100 live resolved
- **Portfolio correlation** — Phase 3/4 when multi-position tracking needed

---

## 📋 DAILY CHECK-IN TEMPLATE

Copy-paste this to our chat each day:

