# INV-003 — Sector × regime × signal profitability matrix

**Generated:** 2026-04-30T11:24:28.495295+00:00

**Branch:** backtest-lab

**Cohorts evaluated:** 117 (13 sectors × 3 regimes × 3 signals)

**Sectors:** Auto, Bank, CapGoods, Chem, Consumer, Energy, FMCG, Health, IT, Infra, Metal, Other, Pharma

**Regimes:** Bear, Choppy, Bull

**Signals:** UP_TRI, DOWN_TRI, BULL_PROXY

---

## ⚠️ Caveats carried forward

**Caveat 1 (sector indices) RESOLVED:** all 8 indexed sectors now have real Leading/Neutral/Lagging classification. Chem sector remains 100% Neutral (no `^CNXCHEM` ticker on Yahoo Finance — outside scope).

**Caveat 2 (9.31% MS-2 miss-rate):** active. Sub-cohort findings at marginal n (n=30-50) particularly susceptible — Tier B/A results at marginal n should be re-validated post-Caveat 2 audit before promotion.

**Dimensionality deviation:** ROADMAP INV-003 spec said 11 sectors × 3 regimes × 3 signals = 99 cohorts. Actual backtest_signals.parquet has 13 sectors yielding 117 cohorts. Honoring actual data; extra sectors (CapGoods, Consumer, Health, Other beyond the original 11) are documented but their indices are NOT in cache → sector_momentum falls back to Neutral for those sectors only.

---

## Section A — Boost candidates (Tier S/A/B BOOST)

**Surfaced:** 3 cohorts (S=0 A=0 B=3)

| Sector | Regime | Signal | Train_n | Train_WR | Test_n | Test_WR | Drift_pp | Tier |
|--------|--------|--------|---------|----------|--------|---------|---------|------|
| Pharma | Bull | BULL_PROXY | 161 | 0.6087 | 40 | 0.525 | 8.37 | B |
| CapGoods | Bear | UP_TRI | 754 | 0.6048 | 171 | 0.5556 | 4.92 | B |
| Chem | Bear | UP_TRI | 938 | 0.6023 | 185 | 0.5297 | 7.26 | B |

---

## Section B — Kill candidates (Tier S/A/B KILL)

**Surfaced:** 4 cohorts (S=0 A=0 B=4)

| Sector | Regime | Signal | Train_n | Train_WR | Test_n | Test_WR | Drift_pp | Tier |
|--------|--------|--------|---------|----------|--------|---------|---------|------|
| Other | Bear | BULL_PROXY | 35 | 0.3714 | 18 | 0.3889 | 1.75 | B |
| Infra | Choppy | BULL_PROXY | 129 | 0.3798 | 40 | 0.45 | 7.02 | B |
| FMCG | Bull | DOWN_TRI | 625 | 0.3824 | 168 | 0.4345 | 5.21 | B |
| Energy | Bear | DOWN_TRI | 243 | 0.3992 | 62 | 0.4355 | 3.63 | B |

---

## Section C — REJECT cohorts (106 — n adequate, no tier)

Sorted by lifetime WR distance from coin-flip (most extreme first).

| Sector | Regime | Signal | Lifetime n | Lifetime WR | Wilson_lower | Boost drift_pp | Kill drift_pp |
|--------|--------|--------|-----------|-------------|--------------|----------------|---------------|
| Health | Choppy | BULL_PROXY | 35 | 0.6571 | 0.4915 | 12.04 | 12.04 |
| Health | Bull | BULL_PROXY | 46 | 0.6087 | 0.4646 | 25.98 | 25.98 |
| CapGoods | Bear | BULL_PROXY | 56 | 0.3929 | 0.2758 | 7.58 | 7.58 |
| Auto | Bull | DOWN_TRI | 675 | 0.3941 | 0.3579 | 12.3 | 12.3 |
| Auto | Bear | DOWN_TRI | 250 | 0.404 | 0.3451 | 17.26 | 17.26 |
| Auto | Bear | UP_TRI | 1009 | 0.5946 | 0.5641 | 3.87 | 3.87 |
| Other | Bear | UP_TRI | 852 | 0.5927 | 0.5594 | 3.86 | 3.86 |
| FMCG | Bear | BULL_PROXY | 85 | 0.4118 | 0.3132 | 1.33 | 1.33 |
| Metal | Bear | DOWN_TRI | 261 | 0.4138 | 0.3557 | 1.09 | 1.09 |
| Pharma | Choppy | DOWN_TRI | 478 | 0.4142 | 0.3709 | 8.95 | 8.95 |
| Energy | Choppy | BULL_PROXY | 117 | 0.5812 | 0.4906 | 12.81 | 12.81 |
| Other | Bull | DOWN_TRI | 546 | 0.4194 | 0.3787 | 4.91 | 4.91 |
| CapGoods | Bull | DOWN_TRI | 582 | 0.421 | 0.3815 | 13.0 | 13.0 |
| Pharma | Bear | UP_TRI | 1142 | 0.5771 | 0.5482 | 3.14 | 3.14 |
| Other | Choppy | BULL_PROXY | 85 | 0.4235 | 0.324 | 9.7 | 9.7 |
| FMCG | Bear | UP_TRI | 1274 | 0.5761 | 0.5488 | 4.07 | 4.07 |
| Infra | Bull | DOWN_TRI | 651 | 0.4255 | 0.3881 | 9.18 | 9.18 |
| Chem | Bull | DOWN_TRI | 779 | 0.4275 | 0.3932 | 1.08 | 1.08 |
| Metal | Bear | UP_TRI | 1147 | 0.5711 | 0.5422 | 4.62 | 4.62 |
| Health | Choppy | DOWN_TRI | 100 | 0.43 | 0.3373 | 0.38 | 0.38 |
| IT | Bear | BULL_PROXY | 58 | 0.569 | 0.4412 | 16.53 | 16.53 |
| Energy | Bull | DOWN_TRI | 841 | 0.4316 | 0.3985 | 8.26 | 8.26 |
| IT | Bull | UP_TRI | 2661 | 0.5678 | 0.5489 | 0.62 | 0.62 |
| IT | Bull | BULL_PROXY | 185 | 0.5676 | 0.4955 | 0.95 | 0.95 |
| IT | Choppy | BULL_PROXY | 141 | 0.4326 | 0.3537 | 3.12 | 3.12 |
| Pharma | Bull | DOWN_TRI | 749 | 0.4326 | 0.3975 | 8.95 | 8.95 |
| IT | Bull | DOWN_TRI | 670 | 0.4328 | 0.3958 | 3.58 | 3.58 |
| Infra | Bear | BULL_PROXY | 53 | 0.434 | 0.3095 | 40.85 | 40.85 |
| CapGoods | Bear | DOWN_TRI | 208 | 0.4423 | 0.3765 | 4.13 | 4.13 |
| Metal | Choppy | DOWN_TRI | 400 | 0.4425 | 0.3946 | 8.62 | 8.62 |
| Health | Bull | UP_TRI | 765 | 0.5542 | 0.5188 | 7.16 | 7.16 |
| CapGoods | Choppy | UP_TRI | 1550 | 0.5535 | 0.5287 | 9.09 | 9.09 |
| Bank | Choppy | DOWN_TRI | 1092 | 0.4478 | 0.4185 | 8.66 | 8.66 |
| Bank | Bear | DOWN_TRI | 595 | 0.4504 | 0.4109 | 0.14 | 0.14 |
| Infra | Choppy | DOWN_TRI | 426 | 0.4507 | 0.4041 | 8.97 | 8.97 |
| Consumer | Bull | UP_TRI | 263 | 0.5475 | 0.4871 | 8.31 | 8.31 |
| FMCG | Bull | BULL_PROXY | 238 | 0.5462 | 0.4827 | 7.4 | 7.4 |
| Auto | Choppy | BULL_PROXY | 132 | 0.5455 | 0.4604 | 11.9 | 11.9 |
| Health | Bear | BULL_PROXY | 33 | 0.4545 | 0.2984 | 40.91 | 40.91 |
| Bank | Bull | BULL_PROXY | 447 | 0.4564 | 0.4108 | 0.92 | 0.92 |
| FMCG | Choppy | UP_TRI | 2189 | 0.5427 | 0.5218 | 4.6 | 4.6 |
| FMCG | Choppy | BULL_PROXY | 203 | 0.5419 | 0.4732 | 14.28 | 14.28 |
| Auto | Choppy | UP_TRI | 1870 | 0.5412 | 0.5185 | 5.89 | 5.89 |
| Infra | Bear | UP_TRI | 1039 | 0.538 | 0.5076 | 11.06 | 11.06 |
| Bank | Bull | DOWN_TRI | 1609 | 0.4624 | 0.4382 | 4.09 | 4.09 |
| Health | Bull | DOWN_TRI | 214 | 0.4626 | 0.3971 | 0.51 | 0.51 |
| FMCG | Bull | UP_TRI | 2984 | 0.5352 | 0.5173 | 1.99 | 1.99 |
| IT | Choppy | DOWN_TRI | 428 | 0.465 | 0.4182 | 7.71 | 7.71 |
| Pharma | Choppy | BULL_PROXY | 172 | 0.4651 | 0.3922 | 5.94 | 5.94 |
| Consumer | Choppy | UP_TRI | 159 | 0.5346 | 0.4572 | 5.0 | 5.0 |
| IT | Bear | UP_TRI | 1046 | 0.5335 | 0.5032 | 5.0 | 5.0 |
| Chem | Choppy | DOWN_TRI | 439 | 0.467 | 0.4208 | 10.91 | 10.91 |
| Health | Choppy | UP_TRI | 473 | 0.5328 | 0.4877 | 14.45 | 14.45 |
| CapGoods | Choppy | BULL_PROXY | 124 | 0.4677 | 0.3822 | 8.65 | 8.65 |
| Metal | Bull | BULL_PROXY | 156 | 0.4679 | 0.3914 | 4.63 | 4.63 |
| Infra | Bear | DOWN_TRI | 226 | 0.469 | 0.405 | 15.99 | 15.99 |
| Auto | Choppy | DOWN_TRI | 431 | 0.471 | 0.4243 | 4.7 | 4.7 |
| Energy | Bull | BULL_PROXY | 193 | 0.5285 | 0.4582 | 6.81 | 6.81 |
| Bank | Bear | UP_TRI | 2459 | 0.5283 | 0.5085 | 3.03 | 3.03 |
| Energy | Bear | BULL_PROXY | 53 | 0.5283 | 0.3966 | 0.31 | 0.31 |
| Chem | Bull | UP_TRI | 2639 | 0.5279 | 0.5088 | 11.78 | 11.78 |
| Chem | Bull | BULL_PROXY | 235 | 0.4723 | 0.4095 | 18.94 | 18.94 |
| FMCG | Choppy | DOWN_TRI | 481 | 0.474 | 0.4298 | 8.68 | 8.68 |
| Pharma | Choppy | UP_TRI | 1971 | 0.5256 | 0.5035 | 0.52 | 0.52 |
| IT | Bear | DOWN_TRI | 259 | 0.4749 | 0.4149 | 14.87 | 14.87 |
| FMCG | Bear | DOWN_TRI | 320 | 0.475 | 0.4209 | 3.08 | 3.08 |
| Metal | Bull | DOWN_TRI | 732 | 0.4768 | 0.4408 | 14.59 | 14.59 |
| Infra | Bull | BULL_PROXY | 197 | 0.5228 | 0.4533 | 8.07 | 8.07 |
| Pharma | Bear | DOWN_TRI | 289 | 0.5225 | 0.465 | 7.14 | 7.14 |
| Energy | Choppy | DOWN_TRI | 523 | 0.478 | 0.4355 | 0.24 | 0.24 |
| Health | Bear | DOWN_TRI | 69 | 0.5217 | 0.4059 | 10.15 | 10.15 |
| Bank | Choppy | UP_TRI | 4622 | 0.5214 | 0.507 | 6.52 | 6.52 |
| Chem | Choppy | UP_TRI | 1961 | 0.5212 | 0.499 | 12.91 | 12.91 |
| CapGoods | Bull | BULL_PROXY | 119 | 0.521 | 0.432 | 10.61 | 10.61 |
| Auto | Bull | UP_TRI | 2566 | 0.5207 | 0.5013 | 1.0 | 1.0 |
| Auto | Bull | BULL_PROXY | 244 | 0.5205 | 0.458 | 20.38 | 20.38 |
| Other | Bear | DOWN_TRI | 197 | 0.5178 | 0.4483 | 11.02 | 11.02 |
| Consumer | Bear | UP_TRI | 91 | 0.5165 | 0.4152 | 15.9 | 15.9 |
| Energy | Choppy | UP_TRI | 2350 | 0.5162 | 0.496 | 7.12 | 7.12 |
| Metal | Bear | BULL_PROXY | 33 | 0.4848 | 0.325 | 22.18 | 22.18 |
| Bank | Bull | UP_TRI | 6302 | 0.5151 | 0.5027 | 2.49 | 2.49 |
| Pharma | Bear | BULL_PROXY | 101 | 0.4851 | 0.39 | 9.49 | 9.49 |
| CapGoods | Bull | UP_TRI | 2209 | 0.5143 | 0.4934 | 9.45 | 9.45 |
| Consumer | Choppy | DOWN_TRI | 35 | 0.4857 | 0.3299 | 10.71 | 10.71 |
| Health | Bear | UP_TRI | 280 | 0.4857 | 0.4278 | 10.02 | 10.02 |
| Metal | Choppy | BULL_PROXY | 105 | 0.5143 | 0.4199 | 12.41 | 12.41 |
| Metal | Bull | UP_TRI | 2713 | 0.5135 | 0.4946 | 4.85 | 4.85 |
| Infra | Bull | UP_TRI | 2465 | 0.5132 | 0.4934 | 6.07 | 6.07 |
| CapGoods | Choppy | DOWN_TRI | 392 | 0.4872 | 0.4381 | 9.46 | 9.46 |
| Chem | Bear | BULL_PROXY | 80 | 0.5125 | 0.4049 | 19.37 | 19.37 |
| Pharma | Bull | UP_TRI | 2970 | 0.5125 | 0.4945 | 1.81 | 1.81 |
| Bank | Bear | BULL_PROXY | 139 | 0.5108 | 0.4285 | 3.85 | 3.85 |
| Infra | Choppy | UP_TRI | 1918 | 0.5099 | 0.4875 | 2.15 | 2.15 |
| IT | Choppy | UP_TRI | 1652 | 0.5097 | 0.4856 | 1.93 | 1.93 |
| Other | Bull | UP_TRI | 2100 | 0.5095 | 0.4881 | 0.54 | 0.54 |
| Chem | Bear | DOWN_TRI | 281 | 0.4911 | 0.4332 | 5.95 | 5.95 |
| Energy | Bull | UP_TRI | 3314 | 0.4919 | 0.4749 | 2.14 | 2.14 |
| Consumer | Bull | DOWN_TRI | 67 | 0.4925 | 0.3765 | 15.24 | 15.24 |
| Other | Choppy | UP_TRI | 1533 | 0.5062 | 0.4812 | 13.65 | 13.65 |
| Bank | Choppy | BULL_PROXY | 329 | 0.5046 | 0.4508 | 3.94 | 3.94 |
| Energy | Bear | UP_TRI | 1352 | 0.503 | 0.4763 | 6.0 | 6.0 |
| Other | Choppy | DOWN_TRI | 381 | 0.5013 | 0.4513 | 1.37 | 1.37 |
| Metal | Choppy | UP_TRI | 1927 | 0.5003 | 0.478 | 9.35 | 9.35 |
| Auto | Bear | BULL_PROXY | 52 | 0.5 | 0.3689 | 6.72 | 6.72 |
| Chem | Choppy | BULL_PROXY | 140 | 0.5 | 0.4183 | 9.13 | 9.13 |
| Other | Bull | BULL_PROXY | 124 | 0.5 | 0.4133 | 31.53 | 31.53 |

---

## Section D — INSUFFICIENT_N cohorts (4 — n_excl_flat < 30)

| Sector | Regime | Signal | n_total | n_resolved | n_excl_flat |
|--------|--------|--------|---------|-----------|-------------|
| Consumer | Bear | DOWN_TRI | 27 | 27 | 26 |
| Consumer | Bear | BULL_PROXY | 8 | 8 | 7 |
| Consumer | Choppy | BULL_PROXY | 22 | 22 | 20 |
| Consumer | Bull | BULL_PROXY | 21 | 21 | 18 |

---

## Section E — Headline findings

- **Total cohorts evaluated:** 117
- **Boost candidates:** 3 (S=0 A=0 B=3)
- **Kill candidates:** 4 (S=0 A=0 B=4)
- **REJECT cohorts:** 106
- **INSUFFICIENT_N:** 4
- **Eval errors:** 0

**Most extreme cohorts by lifetime WR (informational only — does NOT mean tier qualified):**

Top 5 highest WR (boost-shaped):

| Sector | Regime | Signal | n | WR | Wilson_lower | Boost tier | Kill tier |
|--------|--------|--------|---|-----|-------------|----------|----------|
| Health | Choppy | BULL_PROXY | 35 | 0.6571 | 0.4915 | REJECT | REJECT |
| Health | Bull | BULL_PROXY | 46 | 0.6087 | 0.4646 | REJECT | REJECT |
| CapGoods | Bear | UP_TRI | 925 | 0.5957 | 0.5637 | B | REJECT |
| Auto | Bear | UP_TRI | 1009 | 0.5946 | 0.5641 | REJECT | REJECT |
| Other | Bear | UP_TRI | 852 | 0.5927 | 0.5594 | REJECT | REJECT |

Top 5 lowest WR (kill-shaped):

| Sector | Regime | Signal | n | WR | Wilson_lower | Boost tier | Kill tier |
|--------|--------|--------|---|-----|-------------|----------|----------|
| Other | Bear | BULL_PROXY | 53 | 0.3774 | 0.2594 | REJECT | B |
| CapGoods | Bear | BULL_PROXY | 56 | 0.3929 | 0.2758 | REJECT | REJECT |
| FMCG | Bull | DOWN_TRI | 793 | 0.3934 | 0.36 | REJECT | B |
| Auto | Bull | DOWN_TRI | 675 | 0.3941 | 0.3579 | REJECT | REJECT |
| Infra | Choppy | BULL_PROXY | 169 | 0.3964 | 0.3258 | REJECT | B |

**INV-001 cross-reference (UP_TRI × Bank × Choppy):**

- INV-003 cell verdict: `REJECT`
- INV-003 boost tier: `REJECT`
- INV-003 kill tier: `REJECT`
- Lifetime WR (excl flat): 0.5214; n=4622; Wilson lower 0.507
- INV-001 standalone investigation reached parent KILL tier `REJECT` (15-yr drift 6.52pp). INV-003 cell verdict here should match that result if cohort filters and tier evaluators are consistent.

**INV-002 cross-reference (UP_TRI × Bank × Bear):**

- INV-003 cell verdict: `REJECT`
- INV-003 boost tier: `REJECT`
- INV-003 kill tier: `REJECT`
- Lifetime WR: 0.5283; n=2459
- INV-002 standalone reached parent BOOST tier `REJECT` (HIGH_VARIANCE_SAMPLE_WINDOW_SUSPECT). INV-003 cell verdict here should match.

---

## Section F — Open questions for user review

The following questions are surfaced for user judgment in a separate session. CC does NOT make promotion calls.

1. **Boost candidates → potential mechanism INV follow-ups:** Each boost-tier cohort surfaced in Section A is a candidate for INV-006/007/008+ mechanism investigation. User decides which (if any) to pre-register based on cohort tradeable structure + business context.

2. **Kill candidates → potential `mini_scanner_rules.kill_patterns` promotion:** Kill-tier cohorts in Section B may warrant promotion to active suppression. User applies Gate 4 (ground-truth validation) + Gate 5 (mechanism) + Gate 7 (user review) before any patterns.json transition.

3. **kill_002 path with INV-003 context:** Does any other Bank × Choppy or broader cohort better explain the Apr 2026 cluster than the original kill_002 candidate? See Section E INV-001 cross-reference + cluster verification from prior Phase 4 (60d_ret subset analysis).

4. **Caveat 2 audit before promotion:** Each surfaced candidate at marginal n (say n_excl_flat < 100) should be re-validated after Caveat 2 (9.31% MS-2 miss-rate) audit. Caveat 2 audit deferred to separate session.

5. **patterns.json INV-003 status update:** PRE_REGISTERED → COMPLETED is a user-only transition; CC does not modify patterns.json beyond founding state.

---

## Promotion decisions deferred to user review (per Lab Discipline Principle 6)

This findings.md is **data + structured analysis only**. No promotion decisions are made by CC. User reviews end-to-end + applies Gate 7 (user review) before any patterns.json status change or main-branch promotion.
