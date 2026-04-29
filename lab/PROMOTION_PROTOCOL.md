# Lab Pattern Promotion Protocol

**Purpose:** A pattern discovered in Lab graduates to main TIE TIY (`data/mini_scanner_rules.json` kill_pattern OR boost_pattern, OR brain layer enrichment) **ONLY after passing this protocol**. Promotion is empirical, not pressure-driven. Every gate has a documented pass/fail criterion.

**Companion docs:** `README.md` (vision + lab-vs-live distinction); `ROADMAP.md` (investigation queue).

**Founding date:** 2026-04-30. Protocol may evolve as Lab matures; revisions tracked via commit history on this file.

---

## Promotion Gates (all 7 must pass)

A pattern proceeds gate-by-gate in order. Failure at any gate halts promotion; pattern returns to investigation or is rejected per Rejection Mechanics below. Skipping gates is forbidden.

---

### Gate 1: Hypothesis registered

**Criterion:** Pattern hypothesis filed in `/lab/registry/patterns.json` BEFORE backtest run begins.

**Required fields per registration:**
- `pattern_id` (e.g., INV-001)
- `cohort` definition (signal × sector × regime tuple, with explicit nulls for wildcards)
- `hypothesis_primary` (causal claim about why pattern works/fails)
- `hypothesis_inverse` (if applicable; what profits when primary fails)
- `methodology` (what backtest will measure)
- `live_evidence_at_registration` (cohort stats at the moment of registration)
- `expected_outcome` (what success / failure / inconclusive looks like)

**Why this gate:** Pre-registration prevents post-hoc fitting. If you can articulate the hypothesis only AFTER seeing the backtest, you've fit the data to the story.

**Pass condition:** Registration timestamp predates first backtest run timestamp. All required fields populated.

**Fail condition:** Hypothesis articulated only after results visible OR required fields missing.

---

### Gate 2: Backtest infrastructure used

**Criterion:** Pattern tested via `/lab/infrastructure/` tools (data_fetcher / signal_replayer / regime_replayer / hypothesis_tester / ground_truth_validator), not via ad-hoc Colab notebooks or one-off scripts.

**Why this gate:** Reproducibility requirement. Another investigator (future-you, six months from now) must be able to re-run the same backtest and arrive at the same conclusion. Ad-hoc analysis evaporates.

**Pass condition:** Investigation script committed to `/lab/analyses/INV-NNN/` referencing infrastructure modules. Inputs (universe, period, parameters) explicitly logged.

**Fail condition:** Analysis run outside `/lab/infrastructure/` OR inputs not reproducible.

---

### Gate 3: Train/test OOS protocol

**Criterion:** Hypothesis tested with mandatory train/test split:

- **Train period:** 2011-01-01 → 2022-12-31 (or available history if shorter; min 5 years)
- **Test period:** 2023-01-01 → present (must include recent loss batches per Gate 4)
- **OOS rule:** Hypothesis derived/tuned on TRAIN only; TEST evaluation happens once. No iterating on test set.

**Statistical thresholds (three-tier structure):**

The three-tier model matches existing system conventions (`mini_scanner_rules` tier A/B; `brain_design` Tier S/A/B; bridge TAKE_FULL/SMALL/WATCH/SKIP). Patterns earn the highest tier whose criteria they satisfy; lower-tier patterns can graduate to higher tiers via re-investigation as evidence accumulates.

#### BOOST patterns (positive-edge cohorts)

**Tier S — High Conviction Boost**
- Train WR ≥ 75% · Train n ≥ 100 · Wilson 95% lower > 60% · p < 0.05
- Test WR ≥ 65% · Test n ≥ 30
- Drift train→test < 10pp
- Promotion target: `mini_scanner_rules.boost_patterns[]` with `conviction_tag: "HIGH"`
- Position-size guidance (future): full size

**Tier A — Solid Boost**
- Train WR ≥ 65% · Train n ≥ 50 · Wilson 95% lower > 50% · p < 0.05
- Test WR ≥ 55% · Test n ≥ 20
- Drift train→test < 15pp
- Promotion target: `mini_scanner_rules.boost_patterns[]` with `conviction_tag: "STANDARD"`
- Position-size guidance (future): reduced size (trader judgment)

**Tier B — Watch Only**
- Train WR ≥ 60% · Train n ≥ 30
- Test WR ≥ 50% · Test n ≥ 15
- Drift train→test < 20pp
- Promotion target: `mini_scanner_rules.watch_patterns[]` (informational only; does NOT auto-suppress or boost)
- Position-size guidance (future): no trade; watch tracking only

#### KILL patterns (negative-edge cohorts; actively suppressed)

**Tier S — High Conviction Kill**
- Train WR ≤ 25% · Train n ≥ 100
- Test WR ≤ 30% · Test n ≥ 30
- Drift train→test < 10pp
- Promotion target: `mini_scanner_rules.kill_patterns[]` with `conviction_tag: "HARD_KILL"`

**Tier A — Standard Kill**
- Train WR ≤ 35% · Train n ≥ 50
- Test WR ≤ 40% · Test n ≥ 20
- Drift train→test < 15pp
- Promotion target: `mini_scanner_rules.kill_patterns[]` with `conviction_tag: "STANDARD_KILL"`

**Tier B — Watch Only Kill (informational warning)**
- Train WR ≤ 40% · Train n ≥ 30
- Test WR ≤ 45% · Test n ≥ 15
- Drift train→test < 20pp
- Promotion target: `mini_scanner_rules.watch_patterns[]` (warning only; does NOT auto-suppress)

#### FILTER patterns (sub-cohort splits)

Filter patterns inherit parent boost/kill tier criteria. Sub-cohort must independently pass tier requirements to graduate at that tier. A filter that passes Tier B requirements but fails Tier A graduates only to Tier B.

**Statistical significance:** Wilson 95% lower bound (`(p̂ + z²/(2n) − z·sqrt((p̂(1−p̂) + z²/(4n))/n)) / (1 + z²/n)` with `z=1.96`) used for confidence; p-value < 0.05 supplementary.

**Why this gate:** OOS is the defense against overfit. Patterns that pass train but fail test are statistical noise dressed as signal. Tier-specific drift bounds (10/15/20pp for S/A/B) prevent declaring success when WR falls materially between train and test — that's a regime shift, not a robust pattern. Tier S requires the tightest drift because position size at promotion is largest; tolerance widens at lower tiers because operational impact is smaller.

**Pass condition:** Pattern satisfies ALL criteria for at least Tier B (the floor); pattern earns the highest tier whose criteria are fully met.

**Fail condition:** Pattern fails Tier B floor (any threshold miss OR drift exceeds 20pp).

#### kill_002 ship context (live operational ship; NOT Lab promotion)

The `kill_002` candidate currently shipping on main branch (separate from Lab; per Lab Discipline Principle 6) at lifetime **n=26 resolved + 3 OPEN, WR 27%** is a live-evidence operational ship. It does NOT pass Lab's promotion gates today: n=26 resolved falls below Tier A's 50-minimum, below Tier B's 30-minimum, and far below Tier S's 100-minimum.

Lab investigation INV-001 will validate kill_002 against 15-year backtest. If validated, kill_002 may be re-promoted to a Lab tier (S or A depending on backtest n + WR) with the appropriate `conviction_tag` added.

**Until Lab validation:** kill_002 ships with `conviction_tag: "LIVE_EVIDENCE_ONLY"` (operational ship; not Lab-validated). This tag is the explicit marker that the rule pre-dates Lab discipline and exists by trader judgment + live signal_history evidence alone.

#### Empirical tier preview (where current live cohorts COULD land IF Lab investigation reproduces live evidence on multi-year backtest)

The table below is **illustrative only**. Live evidence is the starting point for Lab investigation, not a tier landing. Actual tier assignment requires the full 7-gate pipeline (Gate 1 hypothesis registration through Gate 7 user review). No live cohort below is currently Lab-validated.

| Cohort | Live evidence | Tier-eligibility (pending Lab) |
|--------|---------------|--------------------------------|
| UP_TRI × Bear | n=90, WR 94% | Pending **INV-002**. IF Lab validates similar WR on 15-year backtest with n ≥ 100 and drift < 10pp → qualifies **Tier S boost**. IF backtest WR drops below 75% OR drift exceeds 10pp → qualifies lower tier (A/B) or rejects. |
| UP_TRI × Pharma × Choppy | n=9, WR 67% | Pending future INV (not yet pre-registered). IF Lab backtest yields n ≥ 50 + WR ≥ 65% + drift < 15pp → qualifies **Tier A boost**. IF n insufficient or WR drift exceeds bounds → qualifies Tier B or rejects. |
| UP_TRI × Energy × Choppy | n=7, WR 71% | Same status as Pharma × Choppy. Live n is too small for any tier today; Lab investigation must establish historical n + WR before tier assignment. |
| UP_TRI × Bank × Choppy | n=26 resolved (3 additional OPEN), WR 27% | Pending **INV-001**. **Live evidence (n=26) is below Tier A's n≥50 minimum AND below Tier B's n≥30 minimum — cannot promote to ANY Lab tier on live evidence alone today.** kill_002 ships on main as `LIVE_EVIDENCE_ONLY` (per Principle 6) precisely because live data is too thin for Lab gates; trader judgment + live signal_history justify operational ship while Lab pursues n expansion. IF Lab backtest validates WR ≤ 35% with n ≥ 50 + drift < 15pp → qualifies **Tier A kill**. IF Lab backtest contradicts (e.g., 15-year WR closer to 50%) → rejects; kill_002 demoted; recent-regime-drift hypothesis investigated separately. |
| UP_TRI × Bank × Bear | n=8, WR 100% | Pending **INV-002**. Live n insufficient for any tier; Lab investigation must establish whether 100% WR is genuine cohort edge or small-sample artifact. |

This preview demonstrates tier-framework reasoning applied to current cohorts. Actual tier assignment requires Lab investigation completion. The preview is illustrative for design review only — no live pattern is yet Lab-validated.

---

### Gate 4: Ground-truth validation

**Criterion:** Pattern tested against ALL registered loss batches in `/lab/registry/ground_truth_batches/`. Counterfactual P&L computed.

**For kill patterns:**
- Question: "Of the loss-batch losses, how many would this rule have prevented?"
- Question: "Of the same period's winners, how many would this rule have suppressed (false positives)?"
- Acceptance: prevented losses > suppressed winners by ≥ 2:1 margin
- Documented as: `kill_002 applied to GTB-001 + GTB-002: prevented 16 losses (-43.2% aggregate P&L); suppressed 4 winners (+8.1% aggregate P&L); net +35.1% counterfactual P&L delta`

**For boost patterns:**
- Question: "On loss-batch dates, would inverse pattern have profited?"
- Question: "Pattern's lifetime forward-validation: does post-registration WR hold?"
- Acceptance: inverse pattern WR ≥ 50% on loss-batch dates with n ≥ 5; lifetime forward WR drift from train < 15pp

**Why this gate:** Past loss batches are real money. A pattern that doesn't explain real losses is hypothesis-only — not actionable. A pattern that explains losses but suppresses too many winners over-corrects.

**Pass condition:** Counterfactual delta meets acceptance criteria for pattern type.

**Fail condition:** Pattern doesn't materially affect loss-batch outcomes OR over-suppresses winners.

---

### Gate 5: Mechanism explanation

**Criterion:** Causal hypothesis stated for WHY pattern works. Pattern without mechanism = lower confidence; require larger sample (n ≥ 100 train) to compensate.

**Examples of valid mechanisms:**
- "Bank stocks in Choppy regime fail UP_TRI breakouts because sector-internal churn (rate-sensitive flows + index rebalancing) absorbs price moves before follow-through can establish."
- "Pharma sector defensive characteristic (regulated revenue + lower beta) supports breakout follow-through during macro uncertainty (Choppy regime)."
- "Volume-confirmed UP_TRI breakouts have higher follow-through because volume signals institutional participation; weak-volume breakouts are retail-driven and revert."

**Examples of invalid mechanisms (insufficient):**
- "It works because the data shows it works." (tautology)
- "Some institutional pattern." (unspecified)
- "Statistical edge." (restating the result)

**Why this gate:** Mechanism is the line between discovered pattern and curve-fit noise. Patterns with explicit causal hypotheses can be falsified (e.g., "if PSU bank consolidation explains 2018-2020 cohort failure, post-2021 cohort should differ" — testable). Patterns without mechanism are vulnerable to silent regime shifts the trader can't predict.

**Pass condition:** Causal claim stated; falsifiable conditions identified.

**Fail condition:** No mechanism OR mechanism is tautological / unspecified.

**Compensation rule (with 90-day sunset clause; Tier A and Tier B only):** If mechanism explanation is weak/absent but evidence passes Tier A or Tier B thresholds (per Gate 3), pattern may proceed to promotion with `mechanism_status: "empirical_only"` flag and the following sunset clause:

- Lab investigator must articulate mechanism hypothesis within 90 days of promotion (logged in `patterns.json` `mechanism_articulated_date` field).
- If 90 days elapse without mechanism articulation: pattern auto-demotes via reverse PR (`main → backtest-lab → main` with rule `active = false`) per Demotion Mechanics.
- Lifetime forward-monitoring required regardless: WR drift beyond tier-specific bound (10pp Tier S / 15pp Tier A / 20pp Tier B per Gate 3) triggers re-investigation.

**Tier S exclusion:** `empirical_only` is NOT permitted at Tier S. Tier S patterns carry the largest position-size guidance and broadest market impact; mechanism is required at top tier. A pattern that passes Tier S statistical thresholds but lacks mechanism graduates to Tier A under empirical-only status with sunset clause; Tier S re-promotion happens only after mechanism is articulated and forward-validated.

This sunset prevents `empirical_only` becoming a permanent backdoor for mechanism-less promotion. Empirical patterns at Tier A or B earn their place by either developing mechanism OR auto-demoting.

---

### Gate 6: Sector-specificity preserved

**Criterion:** Pattern doesn't blanket-suppress profitable sub-cohorts.

**Test:** For every parent cohort the pattern affects, surface the within-cohort sector breakdown. If any sub-cohort within scope has WR > 55% (lifetime), the pattern must NOT include that sub-cohort.

**Worked example (founding case):**
- Pattern: "kill UP_TRI × Choppy"
- Parent cohort: UP_TRI × Choppy (any sector)
- Sub-cohort breakdown:
  - UP_TRI × Bank × Choppy: WR 27% — kill candidate ✓
  - UP_TRI × Pharma × Choppy: WR 67% — profitable; MUST NOT be killed
  - UP_TRI × Energy × Choppy: WR 71% — profitable; MUST NOT be killed
  - UP_TRI × CapGoods × Choppy: WR 67% — profitable; MUST NOT be killed
- Verdict: blanket kill REJECTED. Sector-specific kill_002 = UP_TRI × Bank × Choppy ACCEPTED.

**Why this gate:** Blanket rules destroy edge by suppressing winning sub-cohorts. Sector-specificity preserves heterogeneity. This gate is what makes Lab patterns surgical rather than blunt.

**Pass condition:** Pattern scope matches actual failure cohort; profitable sub-cohorts excluded.

**Fail condition:** Pattern suppresses any sub-cohort with lifetime WR > 55%.

---

### Gate 7: User review + lock-in

**Criterion:** Final pattern presented to user with all 6 prior gates' evidence. User approves promotion via explicit YES.

**Required evidence package per pattern:**
1. Hypothesis registration (Gate 1) — link to `patterns.json` entry
2. Investigation script + reproducibility notes (Gate 2)
3. Train/test OOS results table (Gate 3) — train WR / n, test WR / n, drift, Wilson bounds
4. **Tier assignment** (Gate 3 derived) — explicit tier (S / A / B) the pattern earns; conviction_tag specified per tier (HIGH / STANDARD / WATCH for boost; HARD_KILL / STANDARD_KILL / WATCH for kill)
5. Ground-truth counterfactual P&L per loss batch (Gate 4)
6. Mechanism explanation (Gate 5) — causal claim + falsifiable conditions; OR `mechanism_status: "empirical_only"` declaration with sunset clause acknowledged (Tier A/B only; Tier S forbids empirical-only)
7. Sub-cohort sector breakdown (Gate 6) — table proving no profitable sub-cohort suppressed
8. Proposed final pattern entry for target file — specifies which `mini_scanner_rules.json` array (`boost_patterns[]` / `kill_patterns[]` / `watch_patterns[]`) per tier landing

**Why this gate:** Empirical evidence is necessary but not sufficient. The trader holds context Lab can't see (recent broker conversations, macro views, capital constraints, risk appetite). User review is the human-in-the-loop check that closes the promotion decision.

**Pass condition:** User explicit YES on full evidence package.

**Fail condition:** User rejects OR requests revision.

---

## Promotion Mechanics

After all 7 gates pass:

1. **Lab investigation report committed** to `/lab/analyses/INV-NNN/` on `backtest-lab` branch with full evidence package + raw counterfactual data.
2. **Pattern entry crafted** for main branch target file per tier landing (from Gate 3):
   - Tier S boost → `data/mini_scanner_rules.json` `boost_patterns[]` append; `conviction_tag: "HIGH"`
   - Tier A boost → `boost_patterns[]` append; `conviction_tag: "STANDARD"`
   - Tier B boost → `watch_patterns[]` append (informational; does not boost)
   - Tier S kill → `kill_patterns[]` append; `conviction_tag: "HARD_KILL"`
   - Tier A kill → `kill_patterns[]` append; `conviction_tag: "STANDARD_KILL"`
   - Tier B kill → `watch_patterns[]` append (informational warning; does not suppress)
   - New signal types (rare; outside the boost/kill paradigm) → brain layer schema extension (cross-reference with `doc/brain_design_v1.md`)
3. **PR opened** `backtest-lab → main` with PR description containing:
   - Pattern entry diff
   - Link to `/lab/analyses/INV-NNN/` evidence package
   - 7-gate pass certification (gate-by-gate verdict per `patterns.json` `promotion_gate_status`)
4. **User reviews PR**; approves merge.
5. **Pattern entry added to main**; `backtest-lab` branch tagged with promotion event (`tag: promo-INV-NNN-2026-MM-DD`).
6. **`patterns.json` updated** on `backtest-lab`: pattern's `status` changes from `INVESTIGATING` to `PROMOTED` with promotion commit hash on main + tag reference.

---

## Rejection Mechanics

If pattern fails any gate (1 through 6):

1. **Documented in `patterns.json`**: pattern's `status` set to `REJECTED`. `failure_reason` populated with which gate failed and why (specific WR shortfall, mechanism inadequacy, sub-cohort suppression, etc.).
2. **Investigation artifact retained** in `/lab/analyses/INV-NNN/` for audit trail. Future investigators must be able to see WHY a hypothesis was rejected.
3. **Not retried without new evidence.** Re-investigation requires:
   - 6+ months additional live data, OR
   - New mechanism hypothesis (different causal claim than original), OR
   - Methodology change (e.g., different feature set, different cohort definition)
4. **Cross-reference**: `patterns.json` `rejection_history[]` array tracks all prior rejection iterations of the same cohort, so future investigators see the full history.

If pattern fails Gate 7 (user review):
- Pattern stays in `READY_FOR_REVIEW` status pending user feedback.
- User specifies revision or final rejection.
- Revisions cycle back to relevant gate; final rejection follows standard Rejection Mechanics above.

---

## Demotion Mechanics

If a previously-promoted pattern starts failing in live use:

1. **Trigger detection** (any one); drift threshold tier-specific:
   - Cohort sweep weekly drift report (per `ROADMAP.md`) flags WR drift from promotion baseline:
     - **Tier S patterns:** drift > 10pp triggers re-investigation
     - **Tier A patterns:** drift > 15pp triggers re-investigation
     - **Tier B patterns:** drift > 20pp triggers investigation
   - Trader observes loss batches that the pattern should have prevented (kill not firing) or losses on signals the pattern boosts (boost over-firing).
   - Brain layer (`bridge_state.json` history) shows pattern's downstream candidates degrading.
   - Empirical-only sunset (90 days elapsed without mechanism articulation per Gate 5 compensation rule) — auto-triggers demotion, not re-investigation.
2. **Lab re-investigation opens** as new INV-NNN with `parent_promoted_pattern: <pattern_id>`.
3. **Re-runs Gates 3-6** with updated data:
   - If pattern still passes thresholds + ground-truth + sector-specificity: no demotion; flag was false alarm; document and continue monitoring.
   - If pattern fails: prepare demotion PR.
4. **Demotion PR** `backtest-lab → main`:
   - Sets `kill_pattern.active = false` (or `boost_pattern.active = false`) in `mini_scanner_rules.json`
   - Does NOT delete the rule entry — keeps for audit trail
   - PR description documents what changed (regime drift / market structure shift / sample bias revealed by larger n)
5. **User reviews demotion PR**; approves merge.
6. **`patterns.json` updated**: pattern's `status` changes from `PROMOTED` to `DEMOTED` with demotion commit hash + reason. Original promotion artifact preserved for audit.

**Demotion is NOT failure-of-Lab.** Markets evolve. A pattern that worked for 18 months may stop working when market structure shifts. Honest demotion is healthier than denial.

---

## Protocol Versioning

This protocol is `v1.0` as of founding date 2026-04-30. Revisions tracked via commit history on this file. Material protocol changes (gate threshold adjustments, new gate addition, gate retirement) require documentation in commit message + `/lab/analyses/protocol_revision_NNN.md` rationale entry.

Patterns promoted under one protocol version remain valid under that version unless re-investigation under a newer version explicitly triggers demotion.
