# Sonnet Visual Review (retune1)

Model: claude-sonnet-4-6
Tokens: in=4959 out=941

---

## Regime Classifier V2 Retune1 — Sanity Review

---

### Test 1 — Bear Capture (Feb–Apr 2026): **PARTIAL PASS**
V2 retune1 correctly fires BEAR (red bands) multiple times during the Feb–Apr 2026 drawdown, a clear improvement over retune0, but the bear identification is **fragmented into 4–5 narrow bands** rather than a sustained committed BEAR regime across the full 14% drawdown — the dominant background state remains CHOPPY throughout.

---

### Test 2 — Bull Capture (Aug 2025–Jan 2026): **FAIL**
Chart 2 shows the Aug 2025–Feb 2026 ATH rally (24500→26300) is classified almost entirely as **CHOPPY (gray)** with only a brief BULL_RECOVERY period in late 2025 and a BEAR_RECOVERY dip in Oct 2025 — V2 retune1 still fails to commit to BULL during a clear sustained uptrend making new highs.

---

### Test 3 — Historical Bears (2020, 2015–16, 2022): **PASS**
Chart 3 shows BEAR (red) is correctly triggered during the **2020 COVID crash**, the **2015–16 correction**, and the **2022 drawdown**, with appropriate clustering of red bands at all three known bear periods, confirming the classifier has reasonable historical bear detection capability.

---

### Test 4 — Whipsaw: **FAIL**
Chart 3 (full history) shows **excessive state fragmentation** throughout — particularly 2013–2019 where rapid alternation between BULL/CHOPPY/BEAR produces dozens of narrow single-day or two-day bands, and Chart 2 shows the same fragmentation pattern in the recent 365-day window, indicating the 3-of-5 rolling window is insufficient to suppress noise.

---

### Overall: **NEEDS_TUNE**

Retune1 represents genuine progress — BEAR now fires during real crashes (Test 1 improvement) and historical bears are preserved (Test 3) — but two fundamental problems remain unresolved. First, the **BULL state is structurally suppressed**: the classifier appears to demand conditions that are almost never met in real trending markets, causing it to default to CHOPPY even during confirmed ATH rallies. Second, the **BEAR commitment is still too shallow** — it fires in brief pulses rather than holding through a sustained drawdown, meaning the CHOPPY→BEAR fix (Fix A) is triggering but the persistence mechanism is not holding the state. The whipsaw problem suggests the rolling window threshold or the exit conditions are still too loose.

---

### Retune2 Recommended Changes

| Parameter | Current (Retune1) | Suggested (Retune2) | Rationale |
|---|---|---|---|
| BULL entry threshold | (unknown, apparently too strict) | **Loosen momentum/MA condition by ~15–20%** | BULL never fires in clear uptrends |
| BEAR exit / re-entry suppression | None apparent | **Add minimum BEAR hold = 5 trading days** before allowed to exit | Prevents fragmented bear pulses |
| CHOPPY→BULL path | Likely blocked or requires BULL_RECOVERY first | **Allow CHOPPY→BULL direct** (mirror Fix A for upside) | Symmetric with Fix A |
| Rolling confirm window | 3-of-5 | **Raise to 4-of-7** for BEAR→CHOPPY exit only | Prevents premature BEAR exit on single bounce |
| BULL→CHOPPY confirm | Likely 2 days (Fix B) | **Keep 2-day entry, but require 3-day exit confirm** | Asymmetric persistence favors holding trending states |

**Priority order for retune2:** Fix BULL suppression first (it's the most egregious failure), then address BEAR persistence, then recheck whipsaw on full history.