# 02 — Plug-in Interface Contracts

The single most important file in TIE TIY 2.0. Bad contracts lock in refactor pain; good contracts let new Bull setups land in 1 day instead of 1 week.

Conventions: Python 3.12 `Protocol` (structural typing); all dataclasses `frozen=True`; all interfaces versioned (`v1`, `v2`); registry takes name + version.

## Shared domain types

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Optional, Literal

@dataclass(frozen=True)
class Zone:
    low: float
    high: float
    anchor: str            # "swing_low_2026-04-22", "fib_50pct", "ema20_band", "atr_buffer"
    confidence: float      # 0..1; how trustworthy the anchor is

@dataclass(frozen=True)
class CandidateSignal:
    # IDENTITY
    signal_id: str         # deterministic: hash(symbol + detector + date)
    detector_name: str     # "up_tri", "bull_proxy", "vcp", "ema20_pullback", "darvas", ...
    detector_version: str  # semver
    
    # WHAT
    symbol: str
    sector: str            # from universe
    direction: Literal["LONG", "SHORT"]
    age_bars: int          # bars since the structural trigger
    
    # ZONES (replace point-based stop/target everywhere)
    entry_zone: Zone
    stop_zone: Zone
    target_zone_1: Zone    # T1 (typically Fib 1.272 ext)
    target_zone_2: Zone    # T2 (typically Fib 1.618 ext)
    
    # CONTEXT
    detected_at: datetime
    bar_date: datetime     # the bar that triggered detection
    regime_at_detection: str
    
    # DETECTOR EXPLAINABILITY
    rationale: dict        # raw features → decision trace; required for audit
    
    # AUDIT
    schema_version: int = 1

@dataclass(frozen=True)
class RegimeLabel:
    state: str             # plug-in defined; orchestrator only requires it's a string
    confidence: float      # 0..1
    components: dict       # the inputs that drove the label (sma50_slope, vix_5d_chg, adx, etc.)
    classified_at: datetime
    classifier_name: str
    classifier_version: str

@dataclass(frozen=True)
class GateDecision:
    approved: bool
    veto_source: Optional[str]   # "DIRECTION_DISAGREE", "OVERLAP_LOW", "API_TIMEOUT", "CONFIDENCE_LOW", None
    rationale: str
    raw_payload: dict             # full gate output (V5 verdict, jaccard scores, etc.)
    cost_usd: float
    latency_ms: int

@dataclass(frozen=True)
class BrainProposal:
    proposal_id: str       # unique
    proposal_type: str     # "cohort_promote", "kill_pattern_add", "threshold_tune", "v5_threshold", "exposure_warn", "regime_alert"
    title: str             # one-line for UI
    claim: dict            # {what, expected_effect, confidence}
    counter: dict          # {evidence: [...], risks: [...]}
    reversibility: str
    evidence_refs: list[str]
    target: dict           # what file/rule/threshold this would touch
    current_value: Optional[any]
    proposed_value: Optional[any]
    score_priority: float  # 0-10; orchestrator uses for top-N cap
    created_at: datetime
    expires_at: datetime
    generator_name: str
    generator_version: str

@dataclass(frozen=True)
class ApplyResult:
    success: bool
    changes: list[dict]    # list of {file, before, after}
    rollback_handle: str   # for "/undo {id}"
    error: Optional[str]
```

## Contract 1 — SignalDetector (THE critical interface)

```python
class SignalDetector(Protocol):
    """A detector that emits zero or more CandidateSignals per bar per symbol.
    
    Pure function. Must NOT do I/O (no yfinance fetches, no journal writes).
    Receives all data it needs as arguments. Returns its candidates only.
    Side-effect free; can be parallelized across symbols safely.
    """
    
    # --- metadata (class attributes) ---
    name: str                       # "up_tri", "vcp", "ema20_pullback", ...
    version: str                    # semver "1.0.0"
    direction: Literal["LONG", "SHORT", "BOTH"]
    supported_regimes: list[str]    # ["Stable-Bull", "Inflecting-Bear→Bull"] — detector self-declares regime fit; orchestrator gates on this
    min_bars: int                   # min lookback (e.g. VCP needs 200 bars for SMA200)
    config_schema: dict             # JSON schema for tunable parameters
    
    # --- runtime ---
    def detect(
        self,
        ohlcv: pd.DataFrame,        # symbol-specific, indexed by date, columns OHLCV + standard indicators
        symbol: str,
        sector: str,
        regime: RegimeLabel,
        nifty_close: pd.Series,     # market reference for relative strength
        sector_momentum: dict,      # {sector_name: "Leading"|"Neutral"|"Lagging"}
        bar_date: datetime,
        config: dict,               # passed from registry; honors config_schema
    ) -> list[CandidateSignal]:
        """Returns zero-or-more candidate signals detected for the given bar.
        Implementation MUST NOT mutate inputs. MUST be deterministic given same inputs.
        """
        ...
    
    def validate_config(self, config: dict) -> Optional[str]:
        """Returns error string if config is invalid, else None. Called at registration."""
        ...
```

**Why this contract works:**
- `detect` is pure → trivially parallelizable, trivially testable.
- `supported_regimes` lets the orchestrator skip detectors that don't apply (no per-detector "if regime != my_regime: return []" boilerplate).
- `min_bars` lets the orchestrator pre-filter symbols that don't have enough history.
- `rationale: dict` in the output forces explainability without prescribing format.
- Zones (not points) baked into the type; can't accidentally write a point-based detector.

**1.0 mapping:**

| 1.0 code | Becomes (2.0) |
|---|---|
| `scanner_core.detect_signals` UP_TRI block | `UpTriDetector.detect()` |
| `scanner_core.detect_signals` BULL_PROXY block | `BullProxyDetector.detect()` |
| `scanner_core.detect_signals` DOWN_TRI block | NOT PORTED (deprecate) |
| `scanner_core.detect_second_attempt` | `UpTriSADetector` / `DownTriSADetector` — defer |

**New 2.0 detectors:** `VcpDetector`, `Ema20PullbackDetector`, `BullFlagDetector`, `DarvasBoxDetector`, `CupHandleDetector`, `Rule019Detector` (ported from shadow_ops_v1).

## Contract 2 — RegimeClassifier

```python
class RegimeClassifier(Protocol):
    name: str
    version: str
    states: list[str]               # the labels this classifier produces
    required_inputs: list[str]      # ["nifty_ohlcv", "india_vix", "ad_line", "banknifty"]
    
    def classify(
        self,
        nifty_ohlcv: pd.DataFrame,
        india_vix_history: Optional[pd.DataFrame],
        nifty_ad_line: Optional[pd.Series],
        banknifty_ohlcv: Optional[pd.DataFrame],
        as_of_date: datetime,
    ) -> RegimeLabel:
        ...
    
    def explain(self, label: RegimeLabel) -> str:
        """Plain-English rationale for the label, used by UI Caveat footer."""
        ...
```

**1.0 mapping:**

- `scanner/main.py:get_nifty_info` → `ThreeStateRegimeClassifier(name="3state_v1", states=["Bull","Bear","Choppy"])`. Optional inputs are all None.
- Future: `SevenStateRegimeClassifier(name="7state_v1", states=[...])` per L99.

**Why the optional-inputs pattern:** lets the 3-state plug-in still register without VIX / AD-line / BankNifty data; lets the 7-state plug-in declare them required and fail registration if data layer can't supply.

## Contract 3 — ConfluenceGate

```python
class ConfluenceGate(Protocol):
    name: str
    version: str
    mode: Literal["logged_only", "veto_only", "approve_and_veto"]
    
    def evaluate(
        self,
        signal: CandidateSignal,
        chart_image_path: Path,
        regime: RegimeLabel,
        config: dict,
    ) -> GateDecision:
        ...
    
    def calibration_data_dir(self) -> Path:
        """Where the gate writes its decisions log for later calibration."""
        ...
```

**Mode field is load-bearing:**
- `logged_only`: gate runs, decision is logged, but `approved` is always True (caller proceeds). Used for V5's first 60 days.
- `veto_only`: gate can REJECT (`approved=False`) but cannot upgrade; missing gate decision = approve.
- `approve_and_veto`: gate is full authority.

This lets V5 be deployed safely without changing the orchestrator's flow.

## Contract 4 — ProposalGenerator (brain sub-plug-in)

```python
class ProposalGenerator(Protocol):
    name: str
    version: str
    
    def generate(
        self,
        derived_views: dict,        # {cohort_health, regime_watch, portfolio_exposure, ground_truth_gaps}
        signal_history: list[dict],
        decisions_journal: list[dict],
        config: dict,
    ) -> list[BrainProposal]:
        ...
```

Existing 1.0 generators (already shipped) wrap cleanly:
- `cohort_promotion_judge` → `CohortPromoteGenerator`
- `regime_shift_detector` → `RegimeAlertGenerator`
- `exposure_correlation_analyzer` → `ExposureWarnGenerator`

New 2.0 generators:
- `ThresholdTuneGenerator` — proposes parameter adjustments
- `KillProposalGenerator` — proposes new kill_patterns (replaces the broken `rule_proposer.py` that's emitted 31 stale proposals)
- `V5ThresholdTuner` — proposes V5 thresholds per regime post-McNemar

## Contract 5 — UICard

```python
class UICard(Protocol):
    name: str
    version: str
    data_source: str                # "output/brain/unified_proposals.json", etc.
    refresh_strategy: Literal["poll_5min", "poll_1min", "on_demand", "static"]
    
    def render(self, data: dict) -> dict:
        """Returns: {html: str, js_handlers: list[str], css: str, deeplinks: dict}"""
        ...
    
    def render_empty_state(self) -> dict:
        """When data file missing or empty (no proposals etc.)"""
        ...
```

UICards are statically loaded at PWA boot. Each card is a self-contained mini-app.

## Contract 6 — ApprovalHandler

```python
class ApprovalHandler(Protocol):
    def submit(self, proposal: BrainProposal) -> None:
        """Add to pending queue; surface in UI + Telegram."""
        ...
    
    def decide(
        self,
        proposal_id: str,
        decision: Literal["approved", "rejected", "deferred"],
        decider: str,                # "tietiy" or user ID
        reason: Optional[str],
    ) -> ApplyResult:
        """Validate, apply if approved, log to decisions_journal."""
        ...
    
    def list_pending(self) -> list[BrainProposal]:
        ...
    
    def list_history(self, since: datetime) -> list[dict]:
        ...
```

**1.0 reuse:** `scanner/telegram_bot.py:/approve_rule` and `/reject_rule` already exist; wrap as `TelegramApprovalHandler` implementing this protocol. New: `UIApprovalHandler` for dashboard button clicks (deep-links into Telegram for transport).

## Contract 7 — OutcomeEvaluator

```python
class OutcomeEvaluator(Protocol):
    def evaluate(
        self,
        active_signal: ActiveSignal,    # CandidateSignal + entry_date + entry_price + actual_open
        bars_since_entry: pd.DataFrame,
    ) -> Optional[ResolvedSignal]:
        """Returns ResolvedSignal if exit triggered (stop / T1 / T2 / trail / time / opposite),
        else None."""
        ...
```

**1.0 mapping:** `scanner/outcome_evaluator.py` → split into protocol implementations:
- `Day6ForceExitEvaluator` (legacy, deprecate)
- `ZoneBasedEvaluator` (new — handles T1 scale-out + Chandelier trail + 10-day time exit per L99)

## Configuration & registry contract

```python
# Plug-ins register via decorator OR entry_points
@registry.register_detector
class VcpDetector(SignalDetector):
    name = "vcp"
    version = "1.0.0"
    ...

# OR config file: data/plugins.yaml
plugins:
  detectors:
    - name: up_tri
      version: 1.0.0
      enabled: true
      config:
        stop_mult: 1.0
        min_atr_pct: 0.5
    - name: vcp
      version: 1.0.0
      enabled: false   # disabled by default until validated
      config:
        max_contractions: 4
        ...
  regime_classifier: "3state_v1"  # singleton; only one active at a time
  confluence_gate:
    name: "v5_sonnet_45"
    mode: "logged_only"
  proposal_generators:
    - cohort_promote
    - regime_alert
    - exposure_warn
```

Enabling a new detector is a one-line YAML toggle. Same detector code can run in shadow (logged only) and live (full effect) by toggling `enabled`.

## Why these contracts specifically

| Design choice | Reason |
|---|---|
| Zones (not points) in `CandidateSignal` | Forces zone-based architecture from day 1. Can't accidentally point-base a target. |
| `rationale: dict` required on every signal | Explainability for audit + brain feedback loop. |
| `supported_regimes` self-declared by detector | Detectors carry their own scope; orchestrator doesn't hardcode signal×regime mapping. |
| `mode: logged_only/veto_only/approve_and_veto` on gate | V5 can be deployed without changing orchestrator. Calibration window is data, not code. |
| `BrainProposal.score_priority` | Orchestrator's top-N cap is metadata-driven, not hardcoded. |
| `UICard.data_source: str (file path)` | Pure-static dashboard. No backend. Each card is self-contained. |
| `OutcomeEvaluator` as protocol | Lets us replace Day-6 forced-exit with zone-based without ripping out journal. |
| YAML config separate from code | Enabling/disabling detectors doesn't require code change. |

## What these contracts deliberately don't do

- **No streaming.** All detectors work on snapshot DataFrames. Real-time tick data is out of scope.
- **No multi-leg trades.** One CandidateSignal = one entry = one exit. No spreads, no hedges.
- **No backtest semantics in the live path.** Detectors work the same in shadow + live; the runner differs.
- **No machine-learned signal generation in v1.** All detectors are hand-coded rules. Brain proposes parameter tweaks, not new patterns.
