# Wave 2 Migration Log (v3)

**Timestamp:** 20260423_021333

**Files modified:** 11

**Backup:** `quarantine/wave2_20260423_021333`

## Plan

```
════════════════════════════════════════════════════════════
WAVE 2 MIGRATION PLAN (v3 — AST imports + funcs)
════════════════════════════════════════════════════════════

📝 scanner/outcome_evaluator.py
   Import needed: True
   Call-site replacements:
     • 3× date.today() UTC → ist_today() IST
     • 5× _is_trading_day( → is_trading_day(
   Local functions to delete:
     • _is_trading_day() [lines 110-114]

📝 scanner/open_validator.py
   Import needed: True
   Call-site replacements:
     • 5× date.today() UTC → ist_today() IST
     • 2× _is_trading_day( → is_trading_day(
   Local functions to delete:
     • _is_trading_day() [lines 69-70]

📝 scanner/ltp_writer.py
   Import needed: True
   Call-site replacements:
     • 2× date.today() UTC → ist_today() IST
     • 4× _ist_today() → ist_today()
     • 6× _ist_now() → ist_now()
     • 2× _ist_now_str() → ist_now_str()
     • 2× _is_trading_day( → is_trading_day(
   Local functions to delete:
     • _ist_now() [lines 81-83]
     • _ist_now_str() [lines 86-88]
     • _ist_today() [lines 91-97]
     • _is_trading_day() [lines 114-140]

📝 scanner/heartbeat.py
   Import needed: True
   Call-site replacements:
     • 3× date.today() UTC → ist_today() IST
     • 2× _is_trading_day( → is_trading_day(
   Local functions to delete:
     • _is_trading_day() [lines 38-52]

📝 scanner/stop_alert_writer.py
   Import needed: True
   Call-site replacements:
     • 9× _now_ist_date() → ist_today()
     • 5× _now_ist_str() → ist_now_str()
     • 2× _is_trading_day( → is_trading_day(
   Local functions to delete:
     • _now_ist_str() [lines 97-107]
     • _now_ist_date() [lines 110-114]
     • _is_trading_day() [lines 118-133]

📝 scanner/journal.py
   Import needed: True
   Call-site replacements:
     • 5× date.today() UTC → ist_today() IST

📝 scanner/main.py
   Import needed: True
   Call-site replacements:
     • 9× date.today() UTC → ist_today() IST

📝 scanner/weekend_summary.py
   Import needed: True
   Call-site replacements:
     • 2× date.today() UTC → ist_today() IST

📝 scanner/recover_stuck_signals.py
   Import needed: True
   Call-site replacements:
     • 3× date.today() UTC → ist_today() IST

📝 scanner/eod_prices_writer.py
   Import needed: True
   Call-site replacements:
     • 5× _today_ist() → ist_today()
     • 3× _now_ist() → ist_now()
     • 2× _now_ist_str() → ist_now_str()
   Local functions to delete:
     • _now_ist() [lines 57-60]
     • _now_ist_str() [lines 63-64]
     • _today_ist() [lines 67-68]

📝 scanner/chain_validator.py
   Import needed: True
   Call-site replacements:
     • 2× date.today() UTC → ist_today() IST

────────────────────────────────────────────────────────────
TOTALS: 11 files to modify, 107 changes planned, 0 parse errors
════════════════════════════════════════════════════════════
```

## Execution

- ✅ `scanner/outcome_evaluator.py`
- ✅ `scanner/open_validator.py`
- ✅ `scanner/ltp_writer.py`
- ✅ `scanner/heartbeat.py`
- ✅ `scanner/stop_alert_writer.py`
- ✅ `scanner/journal.py`
- ✅ `scanner/main.py`
- ✅ `scanner/weekend_summary.py`
- ✅ `scanner/recover_stuck_signals.py`
- ✅ `scanner/eod_prices_writer.py`
- ✅ `scanner/chain_validator.py`
