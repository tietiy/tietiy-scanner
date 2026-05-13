# 12 — Watch Matcher (Phase 1 Brain)

Source: `scanner/bridge/rules/watch_matcher.py` (107 LOC, exactly matches memory). Mini-config: `data/mini_scanner_rules.json` → `watch_patterns[]`.

## What it does

Pure function. Takes a signal dict + a `watch_patterns` list. Returns a list of all matching active watch patterns, normalized for downstream rendering.

```python
check_matches(signal, watch_patterns) -> list[dict]
```

Match logic (lines 61-76):
- `pattern.signal` must equal `signal.signal_type` (exact match required; no wildcard on signal).
- `pattern.sector` matches if None/"ANY" (wildcard) OR equals `signal.sector`.
- `pattern.regime` matches if None/"ANY" (wildcard) OR equals `signal.regime`.
- Inactive patterns (`active: false`) skipped.
- Multiple matches return as a list (unlike kill_matcher which returns first match).

## Gating behavior

**Watch matcher is NOT a gate.** Module docstring (line 4):
> "UNLIKE kill_matcher (Gate 1 → SKIP) and boost_matcher (Gate 3 → boost), watch_matcher is NOT a gate. It does not influence bucket assignment, filtering, or scoring. Matches surface as informational warnings via SDR.evidence['watch_warnings'] (plural, list) and render in the L1 Telegram brief Caveats footer."

So matched watches:
- DO NOT change `bucket` (the signal still walks the bucket_engine 4 gates).
- DO NOT change `score`.
- DO NOT filter the signal out.
- DO surface as `evidence['watch_warnings']` for telegram rendering.

## Active watch patterns

From `data/mini_scanner_rules.json`:

```json
{
  "id": "watch_001",
  "active": true,
  "signal": "UP_TRI",
  "regime": "Choppy",
  "sector": null,
  "warning_text": "⚠️ WATCH: UP_TRI breakouts haven't followed through in Choppy regime in our data. Apr 17 cluster: 11 wins / 24 losses / 1 flat (n=36, WR 31%). Take with caution. If taken, note your reason.",
  "evidence": {
    "n": 36,
    "wr": 0.314,
    "source_clusters": ["2026-04-17"],
    "report_ref": "output/eod_anomaly_2026-04-27.md"
  },
  "added_date": "2026-04-27",
  "source": "user_per_anomaly_2026-04-27"
}
```

Only **one** active watch pattern. Added 2026-04-27 based on the 2026-04-17 Choppy cluster that resolved at 31.4% WR (the `eod_anomaly_2026-04-27.md` documented loss event).

## Production fire status

To verify Phase 1 production observations I would need to grep `output/bridge_state_history/*_PRE_MARKET.json` for `watch_warnings` content. From the file listing I have:

```
output/bridge_state_history/2026-04-26_PRE_MARKET.json
output/bridge_state_history/2026-04-27_PRE_MARKET.json
output/bridge_state_history/2026-04-28_PRE_MARKET.json
output/bridge_state_history/2026-04-29_PRE_MARKET.json
```

Per session_context.md: "Premarket Phase 1 watch_pattern verified clean + F-2 diagnosis benign + B-3 shipped. 08:55 IST premarket fire produced clean L1 brief; **watch_001 (UP_TRI×Choppy) fired against COALINDIA** with full evidence + warning text rendered into Telegram."

So Phase 1 has had at least one confirmed production fire (COALINDIA on a 2026-04-28 premarket). The infrastructure works.

## Phase 2 status

Per session_context: "Phase 2 (override-with-reason capture) deferred. Per memory, Phase 2 watch_pattern needs 2-3 days of clean Phase 1 production data first."

Counting trading days since Phase 1 fire (2026-04-28):
- Apr 28 (Mon) — Phase 1 first fire
- Apr 29 (Tue) — bridge_state_history present
- Apr 30, May 1, May 2 — weekend / holiday gap
- May 5, May 6, May 7 — no bridge_state_history files on this branch
- May 8 onward — no bridge_state files on this branch

**The branch `shadow_ops_v1` has bridge_state_history only through Apr 29.** Either:
1. Bridge composers stopped firing after Apr 29 (production paused?), or
2. Subsequent fires landed on `main` and weren't merged here, or
3. The whole branch diverged from production around Apr 29 in favor of building shadow_ops.

If the production scanner is still running on `main` and writing bridge_state daily, the Phase 2 trigger condition (2-3 clean days post-Phase-1) has likely been met. But since I'm on `shadow_ops_v1` and don't see those files, I cannot definitively confirm.

## Verdict

- **watch_matcher.py is production-quality.** 107 LOC, well-documented, pure function, correctly defensive.
- **One active watch pattern (`watch_001` UP_TRI×Choppy).** Has fired at least once in production (COALINDIA Apr 28).
- **Phase 2 (override-with-reason capture)** is deferred and the trigger condition (2-3 days clean Phase 1 data) may have been met, but cannot be confirmed from this branch's bridge_state_history files. **Need to check `main` branch to confirm Phase 1 production state.**
