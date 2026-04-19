# TIE TIY Roadmap

**Purpose:** High-level vision, not detailed task list.
**Review frequency:** Quarterly.
**Last updated:** 2026-04-19

---

## 🎯 CURRENT PHASE: Prove Edge (Personal Use)

**Goal:** Validate that TIE TIY's signal edge is real by trading it consistently for 90 days.

**Success metric:** Positive P&L tracked in personal Google Sheet, correlated with scanner's claimed outcomes.

**Duration:** April 2026 - July 2026

---

## 🛣️ PHASED ROADMAP

### Phase 1 (Apr 2026) ✅ COMPLETE
- Scanner live with 188 stocks
- 3 signals: UP_TRI, DOWN_TRI, BULL_PROXY
- Telegram + PWA delivery
- Pattern Miner operational
- eod_master consolidation

### Phase 2 (current) — Intelligence Layer
- Kill switch for broken patterns ✅ (Apr 19)
- Contra shadow tracking ✅ (Apr 19)
- Rule proposer + Telegram approval ✅ (Apr 19)
- Regime debug logging ✅ (Apr 19)
- One-Message Morning Brief ✅ (Apr 19)
- Weekly Claude Review ✅ (Apr 19)

### Phase 3 (May-June 2026) — Self-Healing
- yfinance retry with fallback chains
- Self-diagnostic /status command
- Regime classifier rewrite (after 7 days debug data)
- Auto-apply validated patterns (graduate from /approve_rule)

### Phase 4 (July 2026) — Activate Contra (if proven)
- If contra_shadow.json shows consistent edge after n=20
- Activate inverted DOWN_TRI+Bank as real CONTRA_LONG_BANK signal
- New signal type: CONTRA (pattern-driven direction flip)

### Phase 5 (Aug-Sep 2026) — Evaluate Commercial Viability
- 90-day trading P&L review
- If edge proven: consider architecture shift for multi-user
- If edge not proven: refine signals or pivot

### Phase 6 (if commercial) — Product Build
- Migrate to proper SaaS stack (FastAPI, PostgreSQL, Next.js)
- User auth, payments, multi-tenant
- Mobile apps
- Brokerage integration

---

## 🧭 GUIDING PRINCIPLES

1. **Prove edge before scaling** — no premature optimization
2. **Automation over features** — reduce touch time, not add complexity
3. **Data over intuition** — every change backed by pattern_miner findings
4. **Shadow before live** — new patterns validated in shadow mode first
5. **Additive over replacive** — new features don't remove working ones
6. **Rollback always possible** — every ship has a defined undo

---

## 🚫 NOT IN SCOPE

- Auto-execution of trades (manual placement only — liability reasons)
- F&O / options trading (cash equity only for now)
- Multi-user support (personal tool until edge proven)
- Mobile native apps (PWA sufficient)
- Real-time streaming data (daily signals only)
