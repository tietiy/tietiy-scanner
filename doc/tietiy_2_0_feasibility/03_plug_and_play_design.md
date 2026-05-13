# 03 — Plug-and-Play Architecture Design

Interface contracts for TIE TIY 2.0. Each interface is a Python `Protocol` with strict input/output dataclasses.

## Core domain types

```python
@dataclass(frozen=True)
class Zone:
    low: float
    high: float
    anchor: str    # "swing_low_2026-04-22", "fib_50pct", "atr_buffer", etc.
    confidence: float  # 0..1

@dataclass(frozen=True)
class CandidateSignal:
    signal_id: str
    symbol: str
    sector: str
    signal_type: str    # "VCP", "EMA20_PULLBACK", "BULL_FLAG", "DARVAS", "CUP_HANDLE", "UP_TRI", "BULL_PROXY", "rule_019"
    direction: str      # "LONG" | "SHORT"
    entry_zone: Zone
    stop_zone: Zone
    target_zone_1: Zone   # T1 (Fib 1.272 ext typically)
    target_zone_2: Zone   # T2 (Fib 1.618 ext typically)
    age_bars: int
    detected_at: datetime
    regime_at_detection: str       # 7-state classifier output
    rule_version: str
    detector_rationale: dict       # raw features → decision trace

@dataclass(frozen=True)
class RegimeLabel:
    state: str      # one of 7 states
    confidence: float
    components: dict    # {sma50_vs_200, vix_level, adx, choppiness_idx, ad_line, nifty_banknifty_div}
    classified_at: datetime

@dataclass(frozen=True)
class V5Verdict:
    direction: str
    confidence: float
    entry_zone: Optional[Zone]
    stop_zone: Optional[Zone]
    target_zone: Optional[Zone]
    rationale: str
    latency_ms: int
    cost_usd: float
    chart_hash: str    # SHA256 of the chart image sent

@dataclass(frozen=True)
class ConfluenceDecision:
    approved: bool
    veto_source: Optional[str]   # "V5_DISAGREE", "ZONE_OVERLAP_LOW", "REGIME_GATE", None
    jaccard_overlap: dict        # {"entry": 0.74, "stop": 0.61, "target": 0.55}
    final_zones: dict            # merged TIE TIY × V5 zones
    decision_at: datetime

@dataclass(frozen=True)
class BrainProposal:
    proposal_id: str
    proposal_type: str    # "boost_promote", "kill_rule", "threshold_tune", "regime_threshold_adjust", "v5_threshold_adjust"
    target: dict          # which rule / cohort / threshold
    current_value: Any
    proposed_value: Any
    rationale: str
    evidence_refs: list[str]
    risk_assessment: str
    reversibility: str
    created_at: datetime
    expires_at: datetime    # auto-expire if not acted on

@dataclass(frozen=True)
class ApprovalDecision:
    proposal_id: str
    decision: str    # "approved" | "rejected" | "deferred"
    decider: str
    decided_at: datetime
    reason: Optional[str]
```

## Interface contracts

### SignalDetector (Protocol)

```python
class SignalDetector(Protocol):
    name: str                          # "vcp_breakout", "ema20_pullback", "bull_flag", "darvas", "cup_handle", "up_tri_bear", "bull_proxy_bear"
    version: str                       # "1.0.0"
    supported_regimes: list[str]       # ["Stable-Bull", "Inflecting-Bear→Bull"]
    
    def detect(
        self,
        ohlcv: pd.DataFrame,
        symbol: str,
        sector: str,
        regime: RegimeLabel,
        nifty_close: pd.Series,
    ) -> list[CandidateSignal]:
        """Returns zero or more candidate signals for the current bar."""
        ...
```

**Modules that already fit (almost):** `scanner_core` UP_TRI detection, BULL_PROXY detection (need adapter to return `Zone` instead of point `stop`).

**Need full build:** VCP, EMA20 pullback, bull flag, Darvas, cup-handle.

### RegimeClassifier (Protocol)

```python
class RegimeClassifier(Protocol):
    version: str
    states: list[str]   # the 7 states

    def classify(
        self,
        nifty_ohlcv: pd.DataFrame,
        india_vix_history: pd.DataFrame,
        nifty_ad_line: pd.Series,
        banknifty_ohlcv: pd.DataFrame,
    ) -> RegimeLabel:
        ...
```

**Modules that already fit:** `main.py:get_nifty_info` (3-state). `shadow_ops/regime_classifier.py` (3-state + sub_regime hot/warm/cold).

**Need build:** 7-state classifier per L99 spec. ~30 hours.

### ConfluenceGate (Protocol)

```python
class ConfluenceGate(Protocol):
    version: str
    
    def evaluate(
        self,
        signal: CandidateSignal,
        chart_image_path: Path,
        regime: RegimeLabel,
    ) -> ConfluenceDecision:
        """Send chart to V5, compute Jaccard overlap, apply asymmetric trust."""
        ...
```

**Modules that already fit:** `bridge/core/bucket_engine.py` (the 4-gate engine could be the seed — Gate 3 already does boost_match-based approval). Needs **major** extension to add V5 call + Jaccard computation.

**Need build:** V5 client + Jaccard zone-overlap + asymmetric trust + regime-specific thresholds + per-regime McNemar calibration. ~40 hours (see §04).

### BrainProposer (Protocol)

```python
class BrainProposer(Protocol):
    version: str
    
    def analyze(
        self,
        signal_history: list[ResolvedSignal],
        cohort_health: dict,
        regime_history: list[RegimeLabel],
    ) -> list[BrainProposal]:
        ...
```

**Modules that already fit:** `brain/brain_derive.py` + `brain/brain_verify.py` + `brain/brain_reason.py` (3 LLM gates). These together implement the proposal pipeline.

**Need adapter:** brain currently writes to `output/brain/unified_proposals.json`; new schema includes proposal `expires_at` + `evidence_refs`. ~16 hours.

### ApprovalHandler (Protocol)

```python
class ApprovalHandler(Protocol):
    version: str

    def submit(self, proposal: BrainProposal) -> None: ...           # add to queue, notify Telegram + dashboard
    def decide(self, decision: ApprovalDecision) -> AppliedChange: ... # validate + apply if approved
    def list_pending(self) -> list[BrainProposal]: ...
    def list_history(self, since: datetime) -> list[ApprovalDecision]: ...
```

**Modules that already fit:** `scanner/telegram_bot.py` `/approve_rule` / `/reject_rule` handlers. Need extension to handle the broader proposal types (V5 threshold, regime threshold, cohort promotion).

**Need build:** Dashboard-side approval UI + audit log. ~24 hours (see §05).

### OutcomeEvaluator (Protocol)

```python
class OutcomeEvaluator(Protocol):
    def evaluate(
        self,
        open_signal: ActiveSignal,
        current_bar: datetime,
        ohlcv_since_entry: pd.DataFrame,
    ) -> Optional[ResolvedSignal]:
        """Returns ResolvedSignal if exit hit (stop/T1/T2/trail/time), else None."""
        ...
```

**Modules:** `shadow_ops/lifecycle.py` is the closest existing fit. Need extension for zone-based exits + T1-scale-out + Chandelier trail + 10-day time-exit (vs current Day-6 forced exit). ~16 hours.

### Universe / Calendar / Storage

| Interface | Existing module | Fit |
|---|---|---|
| Universe | `scanner/universe.py` | ⭐ |
| Calendar | `scanner/calendar_utils.py` | ⭐ |
| EventJournal | `shadow_ops/journal.py` | ⭐ (append-only JSONL + checksum) |
| AtomicWrite | `bridge/core/state_writer.py` | ⭐ |
| ErrorHandler | `bridge/core/error_handler.py` | ⭐ |

## Architecture diagram (text)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TIE TIY 2.0 daily run (cron-job.org dispatch)                          │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ├──► UniverseLoader → 188 symbols + sectors
        │
        ├──► RegimeClassifier(7-state)  ─────► RegimeLabel
        │           inputs: Nifty/VIX/ADX/Choppiness/AD-line/BankNifty
        │
        ├──► For each symbol:
        │       ├──► PriceFeed → OHLCV
        │       ├──► [SignalDetector_VCP, SignalDetector_EMA20, ...]
        │       │       (each returns 0+ CandidateSignal with Zones)
        │       ├──► For each candidate:
        │       │       ├──► ChartGenerator → chart_at_bar_t.png
        │       │       ├──► ConfluenceGate(V5)
        │       │       │       │ Send chart to V5 (Sonnet 4.5)
        │       │       │       │ V5 returns direction + zones + confidence
        │       │       │       │ Compute Jaccard overlap
        │       │       │       │ Apply asymmetric trust
        │       │       │       └─► ConfluenceDecision
        │       │       │
        │       │       └──► If approved: emit ActiveSignal → EventJournal
        │       │
        │       └──► For each open ActiveSignal:
        │              └──► OutcomeEvaluator → maybe ResolvedSignal → EventJournal
        │
        ├──► BrainProposer (post-EOD)
        │       inputs: ResolvedSignals, CohortHealth, RegimeHistory
        │       output: list[BrainProposal]
        │       └──► ApprovalHandler.submit(proposal) → Telegram + Dashboard
        │
        ├──► DailyReport
        │       output: markdown digest, Telegram-formatted
        │
        └──► AlertEmitter
                CRITICAL/WARNING/INFO → ack sidecars
```

## Module fit summary

| Interface | Existing module that fits | New build effort |
|---|---|---:|
| `SignalDetector` (5 new Bull setups) | scanner_core UP_TRI/BULL_PROXY (partial) | 80h (5 × ~16h each) |
| `RegimeClassifier` (7-state) | shadow_ops/regime_classifier.py (3-state) | 30h |
| `ConfluenceGate` (V5 + Jaccard) | bridge/core/bucket_engine.py (seed) | 40h |
| `BrainProposer` | brain/brain_derive + verify + reason | 16h adapter |
| `ApprovalHandler` | telegram_bot.py /approve_rule + new dashboard UI | 24h |
| `OutcomeEvaluator` | shadow_ops/lifecycle.py (seed) | 16h |
| Daily orchestrator (chains everything) | shadow_ops/daily_scan.py (seed) | 30h |
| Dashboard backend (proposals + history) | none | 40h |
| Dashboard frontend (proposals + approval) | output/*.js (frontend exists for current scanner) | 40h |
| EventJournal | shadow_ops/journal.py | 4h adapter |
| Universe/Calendar/Storage | reuse | ~5h |
| **Total interface + new build** | | **~325 hours** |

Plus the **~211 hours of porting** from §01.

Grand total: **~536 hours = ~18 weeks at 30 productive hours/week.** Optimistic (no surprises): 12 weeks. Pessimistic (regressions, V5 calibration takes longer): 24+ weeks.
