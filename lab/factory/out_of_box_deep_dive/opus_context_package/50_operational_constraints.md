# Operational Constraints

**Date:** 2026-05-03
**Purpose:** Hard constraints Opus must factor into recommendations.

---

## Operator profile

- **Solo trader** with paused live trading. No team to delegate
  implementation to.
- Pre-deployment investment is significant (Lab pipeline took 5+
  weeks of full-time effort + $21.41 in AI calls). Sunk-cost bias
  is real.
- Trader has been seeing **95% live observed WR** during paused
  period (Bear UP_TRI cell hot sub-regime, n=74 in April 2026).
  Production calibrated WR is **~57-72%** (lifetime baseline).
  Emotional preparation document already created (`trader_expectations.md`).

## Capital constraints

- **5% per trade max** (no exceptions; not negotiable)
- **No moving stops** — fixed stop placement at signal time
- **Day-6 exit default** — bear UP_TRI specific behavior
- Trading paused; opportunity cost is real (don't quote specific
  amount; trader is sensitive)

## Time constraints

- Paused trading has income cost. Trader wants to resume.
- But trader has held back specifically to do Lab work properly.
- Restart pressure is psychological, not contractual.

## Infrastructure

- **Production scanner**: daily run, 188 F&O stocks (NSE).
- **GitHub Actions cron** triggers (premarket 8:55 IST, postopen
  9:40, EOD 15:35 + 16:00).
- **Telegram + PWA** notification stack — trader's primary signal
  delivery.
- **MacBook M5** local dev environment.
- **AICredits.in** for AI spend (~$0.25/run on Haiku, more on Opus).
  Budget exists but each call is conscious spend.

## Data constraints

- **April 2026 only** in operational window (3-4 weeks).
- **Hot Bear sub-regime** dominant — this is the trader's edge
  case, the entire reason rules look 90%+ in backtest.
- **Zero Bull regime data** — all Bull rules untested in production.
- **Lifetime data spans 15 years** but synthesized via Lab not
  observed live.

## Psychological constraints

- Trader is **sophisticated** (built complex Lab pipeline solo).
- Risk of **perfectionism** — keep iterating Lab work to delay
  deployment.
- Risk of **premature deployment** — pressure to restart trading
  before Lab fully validated.
- Risk of **AI-tool dependency** — has used Opus + Sonnet
  extensively; needs to keep judgment in human hands.
- Risk of **sunk-cost** — $21 + 5 weeks invested; difficulty
  abandoning over-engineered components.

## What "deployment" means concretely

- **Phase 1**: 8 READY_TO_SHIP rules from production backtest +
  existing 9 production rules = 17 rules total live.
- Telegram receives signal + verdict + calibrated WR.
- Trader manually executes trades in broker.
- Trader's discretion: take all signals, take subset, or skip.
- 4-6 week ramp to all 37 rules (per L4 integration_notes).

## What "abandonment" means concretely

- Revert to manual trading without Lab rules.
- Use existing kill_001 + win_007 only (already in production).
- Discard 35 new rules.
- Save AI spend for execution-time advisory only.
- Sunk cost on Lab is acknowledged; not recovered.
