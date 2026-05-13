# Sonnet Visual Review (retune4)

Model: claude-sonnet-4-6

---

## Retune4 Sanity Review

---

### Test Results

| # | Test | Result | Evidence |
|---|------|--------|----------|
| 1 | Feb-Apr 2026 BEAR ≥15 days | ✅ **PASS** | 26 days — large contiguous pink block Mar-mid Apr visible in 60-day chart |
| 2 | Aug 2025-Feb 2026 BULL ≥40 days | ❌ **FAIL** | 19 days (53→19) — 365-day chart shows BULL green nearly absent post-Aug 2025; CHOPPY dominates where BULL should be |
| 3 | Historical bears 2020/2015-16/2022 | ✅ **PASS** | Full-history chart shows pink bands at all three periods; 2020 COVID preserved at 39 days |
| 4 | Fix L+M whipsaw creation | ❌ **FAIL** | 90-day V2 chart shows multiple rapid BEAR_RECOVERY↔BEAR↔CHOPPY flickers Feb-early Mar 2026; transitions 25→33 exceeds 22-day ceiling |
| 5 | UP_TRI Bear-family WR ≥85% | ❌ **FAIL** | 75.9% on n=133 — dilution from fragmented regime labeling inflating denominator with weak Bear-family days |

---

### Overall Verdict: **NEEDS_TUNE → Retune5**

Fix L correctly solved the Bear detection regression. Fix M is the primary offender — asymmetric 2-day exit gate is too short and accelerates exits from **all** trending regimes symmetrically in practice, fragmenting both BULL and BEAR into CHOPPY churn.

---

### Retune5 Recommendation

**Root cause:** Fix M's 2-day exit lockdown is insufficient — it barely slows BULL→CHOPPY erosion, creating fragmentation without providing genuine stability.

**Proposed fixes:**

- **Fix M revised:** Symmetric lockdown — restore exit gate to **4 days** (not 2) for both trend exits. The asymmetry experiment failed; the real need is a longer exit dwell, not a shorter one
- **Fix O (new):** BULL-specific persistence guard — add a **BULL→CHOPPY suppression** requiring Nifty to be below its 20-day SMA for ≥3 consecutive days before BULL can exit to CHOPPY. This mirrors the spirit of Fix L (drawdown exemption) but on the upside
- **Fix L — retain unchanged:** The drawdown <-8% Bear exemption is working; do not touch
- **Validate Fix N reconsideration:** With fragmentation now exposed, re-evaluate whether the 5-day minimum commitment (previously skipped as redundant with Fix G) actually provides distinct protection against the BULL→CHOPPY→BULL micro-oscillation pattern now visible in the 90-day chart

**Priority order:** Fix M-revised first (single lever), re-run metrics before adding Fix O — isolate causality cleanly.