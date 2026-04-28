"""Brain reason — LLM gate invocation + cost tracking + circuit breaker.

3 gates per V-1 lock:
  - cohort_promotion_judge (filter+enrich Step 4 boost_promote candidates)
  - regime_shift_detector (generate regime_alert if true shift)
  - exposure_correlation_analyzer (generate exposure_warn if concentration)

Cost: $5/Mtok input + $25/Mtok output (Opus 4.7 verified rates per CORRECTION 4).
Circuit breaker: $1 soft warning, $5 hard abort PER RUN (V-5/CORRECTION 3).
History context: last 20 reasoning_log entries (per gate) + last 10
decisions_journal entries (cohort-identity match, 90-day window per V-12 +
consistency lock).

reasoning_log: append-only forever per K-4 + V-3 schema with gate_input_summary
field per CORRECTION 2.

Production-default; mock client via dependency injection in smoke runner only
per V-10/V-14.

See doc/brain_design_v1.md §1 constraint 4 + §4 Step 5 + §6 + §11 Q1/Q2/Q4.
"""
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from scanner.brain import brain_state, brain_verify


_IST = timezone(timedelta(hours=5, minutes=30))
_UTC = timezone.utc

# ── Locked constants per V-1..V-14 + 6 corrections ─────────────────
_MODEL_ID = "claude-opus-4-7"
_OPUS_INPUT_COST_PER_MTOK = 5.00      # CORRECTION 4 verified
_OPUS_OUTPUT_COST_PER_MTOK = 25.00    # CORRECTION 4 verified
_MAX_TOKENS_PER_CALL = 1024
_SOFT_WARNING_USD = 1.00
_HARD_ABORT_USD = 5.00
_RETRY_BACKOFF_TIMEOUT_SEC = 5
_RETRY_BACKOFF_RATE_LIMIT_SEC = 30
_HISTORY_REASONING_LOG_LIMIT = 20      # last N entries per gate
_HISTORY_DECISIONS_JOURNAL_LIMIT = 10  # last N entries per cohort identity
_HISTORY_DAYS_WINDOW = 90              # CORRECTION 6 90-day window

_GATE_NAMES = (
    "cohort_promotion_judge",
    "regime_shift_detector",
    "exposure_correlation_analyzer",
)


# ── System prompts (V-2 / CORRECTION 1 / CORRECTION 5 disagreement, 90-day) ─
_SYSTEM_PROMPT_COHORT_PROMOTION_JUDGE = """\
You are TIE TIY's brain reasoning gate: cohort_promotion_judge.

ROLE
You review boost_promote candidates produced by deterministic Step 4 generators.
Step 4 has already classified each candidate cohort as Tier M or Tier S per
brain_design §3 statistical rules (n + WR + Wilson lower + edge_pp + R-multiple
gates). Your job is to decide whether each candidate should reach the trader's
review queue, be suppressed, or held pending more data — given cross-view
evidence (regime_watch, portfolio_exposure) and trader history (decisions_journal).

DECISION BOUNDARIES

APPROVE when ALL of these hold:
- Step 4 cohort statistics are strong (already verified by tier classifier)
- No catastrophic cross-view risk (e.g., promoting a cohort already
  representing >30% of open exposure compounds concentration excessively)
- Trader history (if any) does not show recent rejection of similar promotion
  for the same cohort

SUPPRESS when ANY of these hold:
- Cross-view evidence reveals a risk that Step 4 deterministic generators
  cannot see (e.g., regime currently absent + portfolio already skewed)
- Trader rejected a similar boost_promote for THIS cohort within the loaded
  history context (up to 90 days)
- Sample bias suspected: cohort's trades cluster on 1-2 days (Step 4 doesn't
  detect this; you have to)

HOLD when:
- Cohort meets tier thresholds but a specific data point would resolve
  ambiguity (e.g., "wait for Bear regime to return; revisit then")

DISAGREEMENT AWARENESS
If history context contains prior decisions for this cohort or closely
related cohorts (same signal_type, adjacent regime, or same sector),
evaluate whether your current decision conflicts with prior trader feedback.
If disagreement detected, surface explicitly in additional_counter_evidence
(e.g., "Note: trader rejected boost_promote for UP_TRI×Bear on
2026-04-15 with reason 'sample bias to Apr 6-8 cluster'; current candidate
addresses this by requiring n>=15 from non-cluster days").

OUTPUT
Strict JSON. NO prose outside JSON.
{
  "decision": "approve" | "suppress" | "hold",
  "rationale": "1-3 sentences",
  "additional_counter_evidence": ["string", ...],
  "additional_risks": ["string", ...],
  "confidence_override": "high" | "medium" | "low" | null,
  "disagreement_detected": false
}
"""

_SYSTEM_PROMPT_REGIME_SHIFT_DETECTOR = """\
You are TIE TIY's brain reasoning gate: regime_shift_detector.

ROLE
You read regime_watch.json (current regime, 7-day distributions, weekly
intelligence snapshot) and decide whether the data shows a TRUE regime
shift worth alerting the trader to, or a one-week wobble that would
generate noise. Output is a regime_alert candidate OR no_alert decision.

SIGNAL TAXONOMY

TRUE SHIFT (generate regime_alert) when ANY hold:
- Recent 7-day distribution majority differs from prior 7-day distribution
  majority (e.g., prior=Bear majority, recent=Choppy majority)
- Weekly intelligence slope crosses zero (sign change implies regime
  inflection)
- Days_in_current_regime is short (<5) AND prior distribution was stable
  (>=5 days same regime)

ONE-WEEK WOBBLE (no_alert) when:
- Days_in_current_regime >= 7 AND distribution within current regime is
  consistent (no day-to-day flips inside the window)
- Weekly intelligence slope same sign as prior week
- Distribution shift is single-day spike followed by reversion

EVIDENCE TO CITE
For TRUE SHIFT: cite specific numbers from regime_watch (recent vs prior
distribution counts; slope; days_in_current_regime).
For NO ALERT: cite stability evidence (consecutive days same regime).

NEW REGIMES SUSTAINED >7 DAYS
If days_in_current_regime > 14 (regime fully settled), the alert window
has passed; suppress regime_alert generation. The shift was real but is
no longer news.

OUTPUT
Strict JSON. NO prose outside JSON.
{
  "decision": "generate_alert" | "no_alert",
  "rationale": "1-3 sentences",
  "alert_payload": {
    "from_regime": "string|null",
    "to_regime": "string|null",
    "transition_evidence": ["string", ...],
    "what_evidence_would_resolve_ambiguity": "string|null",
    "confidence": "high" | "medium" | "low"
  } OR null when decision is "no_alert"
}
"""

_SYSTEM_PROMPT_EXPOSURE_CORRELATION_ANALYZER = """\
You are TIE TIY's brain reasoning gate: exposure_correlation_analyzer.

ROLE
You read portfolio_exposure.json (open positions broken down by signal_type,
sector, regime + concentration cells) and cohort_health.json (per-cohort
WR/edge). You decide whether the current portfolio exhibits concentration
risk worthy of trader attention. Output is an exposure_warn candidate OR
no_warn decision.

CONCENTRATION RISK CRITERIA

GENERATE exposure_warn when ANY hold:
- regime_concentration.triggered == true (single regime > 80% of open)
  AND that regime's per-cohort WR has not been validated at high tier
- A single (signal_type × sector × regime) cell has share >= 0.20
  (>=20% of all open positions in one bucket)
- Single signal_type concentration > 0.85 share (e.g., 85%+ of positions
  are UP_TRI) AND regime is unstable (regime_watch days_in_current < 5)

NO WARN when:
- All concentrations within tolerance (regime <80%, cells <20%, signal <85%)
- Concentrations exist but offsetting (e.g., 90% UP_TRI but Bear regime
  with Tier S cohort_health for UP_TRI×Bear — the concentration is
  validated edge, not blind exposure)

CROSS-VIEW SYNTHESIS
Look up each concentrated cell in cohort_health. If the cell has a
high-tier cohort entry (Tier M or S), the concentration is partially
justified by edge data — note this in rationale. If cell has Tier W or
Candidate or no entry, the concentration is unvalidated exposure.

WHAT THE WARNING SHOULD RECOMMEND
Either:
- "Pause new entries in <axis>=<value>" — block additions until concentration
  drops via natural exit (Day 6) OR
- "Hedge <pair>" — specific hedge instruction
The recommendation must be specific enough for trader to act on without
further questions.

OUTPUT
Strict JSON. NO prose outside JSON.
{
  "decision": "generate_warn" | "no_warn",
  "rationale": "1-3 sentences",
  "warn_payload": {
    "concentration_axis": "string (e.g., 'by_regime' or 'by_signal_type×sector')",
    "concentration_value": "string",
    "share": <float 0..1>,
    "evidence": ["string", ...],
    "recommended_action": "string (specific, actionable)",
    "tail_risk_scenario": "string (what breaks if regime shifts)"
  } OR null when decision is "no_warn"
}
"""

_SYSTEM_PROMPTS = {
    "cohort_promotion_judge": _SYSTEM_PROMPT_COHORT_PROMOTION_JUDGE,
    "regime_shift_detector": _SYSTEM_PROMPT_REGIME_SHIFT_DETECTOR,
    "exposure_correlation_analyzer": _SYSTEM_PROMPT_EXPOSURE_CORRELATION_ANALYZER,
}


# ── Cost tracking state (V-5 / CORRECTION 3 per-run) ────────────────

@dataclass
class RunCostState:
    """Per-run cost state. NOT persisted across runs.

    reasoning_log is the persistent record across runs;
    cost circuit breaker is per-run only.
    """
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    soft_warning_fired: bool = False
    circuit_breaker_aborted: bool = False
    gates_completed: list = field(default_factory=list)
    gates_skipped_due_to_abort: list = field(default_factory=list)
    gates_skipped_due_to_failure: list = field(default_factory=list)

    def record_call(self, input_tokens: int, output_tokens: int) -> float:
        self.total_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        cost = _compute_call_cost(input_tokens, output_tokens)
        self.total_cost_usd = round(self.total_cost_usd + cost, 4)
        if (not self.soft_warning_fired
                and self.total_cost_usd >= _SOFT_WARNING_USD):
            self.soft_warning_fired = True
            print(f"[brain_reason] SOFT WARNING: cumulative cost "
                  f"${self.total_cost_usd:.4f} crossed ${_SOFT_WARNING_USD}",
                  file=sys.stderr)
        return cost

    def should_abort(self) -> bool:
        return self.total_cost_usd >= _HARD_ABORT_USD


def _compute_call_cost(input_tokens: int, output_tokens: int) -> float:
    """Cost computed from API response usage block."""
    return round(
        (input_tokens / 1_000_000) * _OPUS_INPUT_COST_PER_MTOK
        + (output_tokens / 1_000_000) * _OPUS_OUTPUT_COST_PER_MTOK,
        4
    )


# ── reasoning_log read/write (V-3 + CORRECTION 2) ───────────────────

def _reasoning_log_path(output_dir: str) -> str:
    return os.path.join(output_dir, "brain", "reasoning_log.json")


def _load_reasoning_log(output_dir: str) -> dict:
    """Returns reasoning_log dict; constructs empty shell if missing.
    Append-only forever per K-4."""
    path = _reasoning_log_path(output_dir)
    if not os.path.exists(path):
        return {
            "schema_version": 1,
            "view_name": "reasoning_log",
            "generated_at": None,
            "entries": [],
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {
            "schema_version": 1,
            "view_name": "reasoning_log",
            "generated_at": None,
            "entries": [],
        }


def _append_reasoning_log_entry(output_dir: str, entry: dict) -> None:
    """Atomic append. K-4 lock: NO PRUNE."""
    log = _load_reasoning_log(output_dir)
    log["entries"].append(entry)
    log["generated_at"] = entry.get("timestamp")

    path = _reasoning_log_path(output_dir)
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    payload = json.dumps(log, indent=2, ensure_ascii=False)
    tmp_path = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(tmp_path, path)


# ── History context construction (V-12 + CORRECTION 6 cohort identity) ─

def _extract_cohort_identity(candidate: dict) -> str:
    """Per CORRECTION 6: cohort_axis + cohort_filter (or thin_id /
    transition / concentration_axis depending on type)."""
    ptype = candidate.get("type", "")
    md = candidate.get("decision_metadata", {}) or {}
    if ptype in ("boost_promote", "boost_demote", "kill_rule"):
        axis = md.get("cohort_axis", "")
        cf = md.get("cohort_filter", {}) or {}
        sig = "__".join(f"{k}={cf[k]}" for k in sorted(cf.keys()))
        return f"{axis}__{sig}"
    if ptype == "cohort_review":
        return md.get("rule_id") or md.get("pattern_id") or ""
    if ptype == "regime_alert":
        return f"{md.get('from_regime', '?')}→{md.get('to_regime', '?')}"
    if ptype == "exposure_warn":
        return f"{md.get('concentration_axis', '?')}__{md.get('concentration_value', '?')}"
    return ""


def _candidate_cohort_identity_from_id(candidate_id: str,
                                       proposal_type: str,
                                       md: dict) -> str:
    """Reconstruct cohort identity from a decisions_journal candidate_id +
    metadata (for prefix matching across types)."""
    return _extract_cohort_identity({"type": proposal_type,
                                      "decision_metadata": md})


def _build_gate_history_context(
        gate_name: str,
        candidate_or_none: Optional[dict],
        prior_reasoning_log: dict,
        prior_decisions_journal: dict | list | None) -> dict:
    """Per V-12 + CORRECTION 6: last N reasoning_log entries for this
    gate + last N decisions_journal entries with cohort-identity match.

    90-day window per consistency correction.
    """
    today = datetime.now(_IST).date()
    cutoff_date = today - timedelta(days=_HISTORY_DAYS_WINDOW)

    # Reasoning log: filter by gate_name + 90-day window
    reasoning_entries = []
    for e in (prior_reasoning_log.get("entries") or []):
        if e.get("gate_name") != gate_name:
            continue
        ts = e.get("timestamp", "")
        try:
            entry_date = datetime.fromisoformat(ts).date()
        except (ValueError, TypeError):
            continue
        if entry_date < cutoff_date:
            continue
        reasoning_entries.append(e)
    reasoning_entries = reasoning_entries[-_HISTORY_REASONING_LOG_LIMIT:]

    # Decisions journal: cohort-identity match if candidate provided
    decisions_entries = []
    if candidate_or_none and prior_decisions_journal:
        target_identity = _extract_cohort_identity(candidate_or_none)
        if target_identity:
            entries = (prior_decisions_journal.get("entries")
                       if isinstance(prior_decisions_journal, dict)
                       else prior_decisions_journal) or []
            for e in entries:
                ts = e.get("decision_at") or e.get("created_at") or ""
                try:
                    entry_date = datetime.fromisoformat(ts).date()
                except (ValueError, TypeError):
                    continue
                if entry_date < cutoff_date:
                    continue
                # Match cohort identity (any proposal type)
                e_id = _candidate_cohort_identity_from_id(
                    e.get("candidate_id", ""),
                    e.get("type", ""),
                    e.get("decision_metadata", {}) or {})
                if e_id == target_identity:
                    decisions_entries.append(e)
            decisions_entries = decisions_entries[-_HISTORY_DECISIONS_JOURNAL_LIMIT:]

    return {
        "reasoning_log_entries": reasoning_entries,
        "decisions_journal_entries": decisions_entries,
    }


# ── LLM API call wrapper (V-13 retry + skip) ─────────────────────────

def _call_anthropic_with_retry(
        client,
        gate_name: str,
        system_prompt: str,
        user_prompt: str,
        run_id: str) -> Optional[dict]:
    """Calls Anthropic Messages API; retries once on
    (timeout / rate limit / malformed JSON). Returns dict with parsed
    response or None on failure (caller skips gate).
    """
    last_error = None
    for attempt in (1, 2):
        try:
            msg = client.messages.create(
                model=_MODEL_ID,
                max_tokens=_MAX_TOKENS_PER_CALL,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content_blocks = msg.content if msg.content else []
            text = ""
            for block in content_blocks:
                if hasattr(block, "text"):
                    text += block.text
            text = text.strip()
            # Strip markdown JSON fences if model wraps
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as je:
                last_error = f"JSONDecodeError attempt {attempt}: {je}"
                if attempt == 1:
                    user_prompt = (user_prompt + "\n\n[SYSTEM CORRECTION]: "
                                   "Your previous response was not valid JSON. "
                                   "Output strict JSON only, no markdown fences, "
                                   "no prose.")
                    continue
                return None

            return {
                "parsed": parsed,
                "raw_text": text,
                "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens,
                "request_id": getattr(msg, "id", "unknown"),
                "model": msg.model,
            }
        except Exception as e:
            last_error = f"{type(e).__name__} attempt {attempt}: {e}"
            err_name = type(e).__name__
            if "RateLimit" in err_name or "429" in str(e):
                if attempt == 1:
                    time.sleep(_RETRY_BACKOFF_RATE_LIMIT_SEC)
                    continue
            elif "Timeout" in err_name or "timeout" in str(e).lower():
                if attempt == 1:
                    time.sleep(_RETRY_BACKOFF_TIMEOUT_SEC)
                    continue
            elif "Authentication" in err_name or "401" in str(e):
                # No retry; abort run signaled to caller
                print(f"[brain_reason] AUTH FAILURE in {gate_name}: {e}",
                      file=sys.stderr)
                return None
            # Other errors: retry once with no backoff
            if attempt == 1:
                continue
    print(f"[brain_reason] {gate_name} call failed after retries: {last_error}",
          file=sys.stderr)
    return None


# ── Gate dispatchers ─────────────────────────────────────────────────

def _get_relevant_cohort(cohort_health: dict, candidate: dict) -> Optional[dict]:
    """Locate the specific cohort dict in cohort_health.cohorts[] that
    matches a candidate's filter (for cohort_promotion_judge prompt input)."""
    target_filter = (candidate.get("decision_metadata") or {}).get("cohort_filter") or {}
    for c in cohort_health.get("cohorts", []):
        if c.get("cohort_filter") == target_filter:
            return c
    return None


def _gate_input_summary_for(gate_name: str,
                            candidates: list,
                            derived_views: dict,
                            history: dict) -> str:
    """Per CORRECTION 2: 1-2 line summary of what gate saw."""
    n_history_reasoning = len(history.get("reasoning_log_entries", []))
    n_history_decisions = len(history.get("decisions_journal_entries", []))

    if gate_name == "cohort_promotion_judge":
        if not candidates:
            return f"Reviewed 0 boost_promote candidates. {n_history_reasoning} prior reasoning entries; {n_history_decisions} matching decisions."
        descs = []
        for c in candidates:
            md = c.get("decision_metadata") or {}
            cf = md.get("cohort_filter") or {}
            sig = cf.get("signal_type", "?")
            other = cf.get("regime") or cf.get("sector") or "?"
            descs.append(f"{sig}×{other} (Tier {md.get('tier', '?')}, n={md.get('n', '?')})")
        return (f"Reviewed {len(candidates)} boost_promote candidates: "
                f"{', '.join(descs)}. {n_history_reasoning} prior reasoning entries; "
                f"{n_history_decisions} matching decisions.")
    if gate_name == "regime_shift_detector":
        rw = derived_views.get("regime_watch", {}) or {}
        return (f"regime_watch shows {rw.get('current_regime', '?')} "
                f"{rw.get('regime_stability', '?')} "
                f"{rw.get('days_in_current_regime', '?')} days; "
                f"{n_history_reasoning} prior regime alerts in history.")
    if gate_name == "exposure_correlation_analyzer":
        pe = derived_views.get("portfolio_exposure", {}) or {}
        rc = pe.get("regime_concentration", {}) or {}
        n_concs = len(pe.get("concentrations", []))
        sig_desc = ", ".join(f"{k} {v}" for k, v in (pe.get("by_signal_type") or {}).items())
        return (f"portfolio_exposure: regime_concentration triggered={rc.get('triggered')} "
                f"({rc.get('observed', 0)*100:.1f}% {rc.get('dominant_regime', '?')}), "
                f"{n_concs} sector concentrations, signal types ({sig_desc}). "
                f"{n_history_reasoning} prior exposure warnings.")
    return f"{gate_name}: {len(candidates)} candidates."


def _run_cohort_promotion_judge(
        candidates: list,
        derived_views: dict,
        prior_reasoning_log: dict,
        prior_decisions_journal,
        client,
        cost_state: RunCostState,
        run_id: str,
        output_dir: str) -> tuple[list, list]:
    """Filter+enrich gate. Returns (kept_candidates, skipped_failures)."""
    if cost_state.should_abort():
        cost_state.gates_skipped_due_to_abort.append("cohort_promotion_judge")
        return candidates, []  # passthrough on abort

    kept = []
    failures = []
    for cand in candidates:
        if cost_state.should_abort():
            cost_state.gates_skipped_due_to_abort.append(
                f"cohort_promotion_judge:{cand.get('candidate_id')}")
            kept.append(cand)  # passthrough rest
            continue

        history = _build_gate_history_context(
            "cohort_promotion_judge", cand,
            prior_reasoning_log, prior_decisions_journal)

        relevant_cohort = _get_relevant_cohort(
            derived_views.get("cohort_health", {}) or {}, cand)

        user_prompt = _build_user_prompt_cohort_promotion(
            cand, derived_views, relevant_cohort, history)

        result = _call_anthropic_with_retry(
            client, "cohort_promotion_judge",
            _SYSTEM_PROMPT_COHORT_PROMOTION_JUDGE, user_prompt, run_id)

        if result is None:
            failures.append(("cohort_promotion_judge", cand.get("candidate_id"),
                             "API call failed; passing candidate through unmodified"))
            kept.append(cand)
            continue

        cost_state.record_call(result["input_tokens"], result["output_tokens"])

        parsed = result["parsed"]
        decision = parsed.get("decision", "approve")
        rationale = parsed.get("rationale", "")
        addl_evidence = parsed.get("additional_counter_evidence") or []
        addl_risks = parsed.get("additional_risks") or []
        confidence_override = parsed.get("confidence_override")

        # Log
        _append_reasoning_log_entry(output_dir, {
            "timestamp": datetime.now(_IST).isoformat(),
            "run_id": run_id,
            "gate_name": "cohort_promotion_judge",
            "model": result["model"],
            "candidate_id": cand.get("candidate_id"),
            "gate_input_summary": _gate_input_summary_for(
                "cohort_promotion_judge", [cand], derived_views, history),
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "cost_usd": _compute_call_cost(result["input_tokens"],
                                           result["output_tokens"]),
            "request_id": result["request_id"],
            "decision": decision,
            "rationale": rationale,
            "aborted_by_circuit_breaker": False,
        })

        if decision == "suppress":
            continue  # drop candidate from output
        if decision == "hold":
            continue  # also drop; "hold" means not yet ready

        # APPROVE: enrich
        enriched = json.loads(json.dumps(cand))  # deep copy
        if addl_evidence:
            enriched["counter"]["evidence"] = list(enriched["counter"]["evidence"]) + list(addl_evidence)
        if addl_risks:
            enriched["counter"]["risks"] = list(enriched["counter"]["risks"]) + list(addl_risks)
        if confidence_override in ("high", "medium", "low"):
            enriched["claim"]["confidence"] = confidence_override
        enriched.setdefault("decision_metadata", {})["llm_enrichment_rationale"] = rationale
        kept.append(enriched)

    cost_state.gates_completed.append("cohort_promotion_judge")
    return kept, failures


def _run_regime_shift_detector(
        derived_views: dict,
        prior_reasoning_log: dict,
        prior_decisions_journal,
        client,
        cost_state: RunCostState,
        run_id: str,
        output_dir: str) -> tuple[Optional[dict], list]:
    """Generate gate. Returns (regime_alert_candidate_or_none, failures)."""
    if cost_state.should_abort():
        cost_state.gates_skipped_due_to_abort.append("regime_shift_detector")
        return None, []

    history = _build_gate_history_context(
        "regime_shift_detector", None,
        prior_reasoning_log, prior_decisions_journal)

    user_prompt = _build_user_prompt_regime_shift(derived_views, history)

    result = _call_anthropic_with_retry(
        client, "regime_shift_detector",
        _SYSTEM_PROMPT_REGIME_SHIFT_DETECTOR, user_prompt, run_id)

    if result is None:
        cost_state.gates_skipped_due_to_failure.append("regime_shift_detector")
        return None, [("regime_shift_detector", None,
                       "API call failed; no regime_alert generated")]

    cost_state.record_call(result["input_tokens"], result["output_tokens"])

    parsed = result["parsed"]
    decision = parsed.get("decision", "no_alert")
    rationale = parsed.get("rationale", "")

    _append_reasoning_log_entry(output_dir, {
        "timestamp": datetime.now(_IST).isoformat(),
        "run_id": run_id,
        "gate_name": "regime_shift_detector",
        "model": result["model"],
        "candidate_id": None,
        "gate_input_summary": _gate_input_summary_for(
            "regime_shift_detector", [], derived_views, history),
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost_usd": _compute_call_cost(result["input_tokens"],
                                       result["output_tokens"]),
        "request_id": result["request_id"],
        "decision": decision,
        "rationale": rationale,
        "aborted_by_circuit_breaker": False,
    })

    cost_state.gates_completed.append("regime_shift_detector")

    if decision != "generate_alert":
        return None, []

    payload = parsed.get("alert_payload") or {}
    today = datetime.now(_IST).date().isoformat()
    from_r = payload.get("from_regime") or "?"
    to_r = payload.get("to_regime") or "?"
    signature = f"{from_r}-to-{to_r}"

    candidate = brain_verify.build_proposal_candidate(
        proposal_type="regime_alert",
        source="brain_step5",
        source_view="regime_watch",
        title=f"Regime shift: {from_r} → {to_r}",
        claim_what=f"Regime transition detected: {from_r} → {to_r}",
        claim_expected_effect=(
            payload.get("what_evidence_would_resolve_ambiguity")
            or "Trader awareness; cohort_health classifier may need recalibration"),
        claim_confidence=payload.get("confidence") or "medium",
        counter_evidence=list(payload.get("transition_evidence") or [
            "Generated from regime_shift_detector LLM gate"]),
        counter_risks=[
            "Detection may be one-week wobble misclassified as transition",
            "Trader manual confirmation required; informational only",
        ],
        reversibility=("Informational alert; no system mutation. "
                       "Auto-suppresses on next run if regime stabilizes."),
        evidence_refs=[
            "regime_watch.json#current_regime",
            "weekly_intelligence_latest.json#regime",
        ],
        cohort_filter_signature=signature,
        decision_metadata={
            "from_regime": from_r,
            "to_regime": to_r,
            "transition_evidence": payload.get("transition_evidence") or [],
            "llm_rationale": rationale,
        },
    )
    return candidate, []


def _run_exposure_correlation_analyzer(
        derived_views: dict,
        prior_reasoning_log: dict,
        prior_decisions_journal,
        client,
        cost_state: RunCostState,
        run_id: str,
        output_dir: str) -> tuple[Optional[dict], list]:
    """Generate gate. Returns (exposure_warn_candidate_or_none, failures)."""
    if cost_state.should_abort():
        cost_state.gates_skipped_due_to_abort.append(
            "exposure_correlation_analyzer")
        return None, []

    history = _build_gate_history_context(
        "exposure_correlation_analyzer", None,
        prior_reasoning_log, prior_decisions_journal)

    user_prompt = _build_user_prompt_exposure_correlation(
        derived_views, history)

    result = _call_anthropic_with_retry(
        client, "exposure_correlation_analyzer",
        _SYSTEM_PROMPT_EXPOSURE_CORRELATION_ANALYZER, user_prompt, run_id)

    if result is None:
        cost_state.gates_skipped_due_to_failure.append(
            "exposure_correlation_analyzer")
        return None, [("exposure_correlation_analyzer", None,
                       "API call failed; no exposure_warn generated")]

    cost_state.record_call(result["input_tokens"], result["output_tokens"])

    parsed = result["parsed"]
    decision = parsed.get("decision", "no_warn")
    rationale = parsed.get("rationale", "")

    _append_reasoning_log_entry(output_dir, {
        "timestamp": datetime.now(_IST).isoformat(),
        "run_id": run_id,
        "gate_name": "exposure_correlation_analyzer",
        "model": result["model"],
        "candidate_id": None,
        "gate_input_summary": _gate_input_summary_for(
            "exposure_correlation_analyzer", [], derived_views, history),
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost_usd": _compute_call_cost(result["input_tokens"],
                                       result["output_tokens"]),
        "request_id": result["request_id"],
        "decision": decision,
        "rationale": rationale,
        "aborted_by_circuit_breaker": False,
    })

    cost_state.gates_completed.append("exposure_correlation_analyzer")

    if decision != "generate_warn":
        return None, []

    payload = parsed.get("warn_payload") or {}
    axis = payload.get("concentration_axis") or "?"
    value = payload.get("concentration_value") or "?"
    signature = f"{axis}__{value}"
    share = payload.get("share")
    share_pct_str = f"{share*100:.1f}%" if isinstance(share, (int, float)) else "?"

    candidate = brain_verify.build_proposal_candidate(
        proposal_type="exposure_warn",
        source="brain_step5",
        source_view="portfolio_exposure",
        title=f"Exposure concentration: {axis} = {value} ({share_pct_str})",
        claim_what=(f"Concentration risk: {axis} = {value}; "
                    f"recommended action: {payload.get('recommended_action', 'review')}"),
        claim_expected_effect=(
            f"Trader awareness of tail risk: "
            f"{payload.get('tail_risk_scenario', 'concentration breakdown')}"),
        claim_confidence="medium",
        counter_evidence=list(payload.get("evidence") or [
            "Generated from exposure_correlation_analyzer LLM gate"]),
        counter_risks=[
            "Recommendation may be over-cautious; concentration may be edge-validated",
            "Trader may already be aware; informational only",
        ],
        reversibility=("Informational warning; no system mutation. "
                       "Suppresses on next run if concentration drops below threshold."),
        evidence_refs=[
            "portfolio_exposure.json#concentrations",
            "cohort_health.json#cohorts",
        ],
        cohort_filter_signature=signature,
        decision_metadata={
            "concentration_axis": axis,
            "concentration_value": value,
            "share": share,
            "recommended_action": payload.get("recommended_action"),
            "tail_risk_scenario": payload.get("tail_risk_scenario"),
            "llm_rationale": rationale,
        },
    )
    return candidate, []


# ── User prompt builders ─────────────────────────────────────────────

def _build_user_prompt_cohort_promotion(
        candidate: dict,
        derived_views: dict,
        relevant_cohort: Optional[dict],
        history: dict) -> str:
    """User prompt for cohort_promotion_judge, scoped to a single candidate."""
    ch = derived_views.get("cohort_health", {}) or {}
    rw = derived_views.get("regime_watch", {}) or {}
    pe = derived_views.get("portfolio_exposure", {}) or {}

    lines = ["## Inputs", "", "### Step 4 candidate", ""]
    lines.append(json.dumps({
        "candidate_id": candidate.get("candidate_id"),
        "type": candidate.get("type"),
        "title": candidate.get("title"),
        "claim": candidate.get("claim"),
        "counter": candidate.get("counter"),
        "decision_metadata": {
            k: v for k, v in (candidate.get("decision_metadata") or {}).items()
            if k != "proposed_rule_entry"
        },
    }, indent=2))
    lines.append("")

    lines.append("### Derived views")
    lines.append("")
    lines.append("**cohort_health (relevant cohort + per-signal-type baseline):**")
    if relevant_cohort:
        lines.append(json.dumps(relevant_cohort, indent=2))
    sig_type = (candidate.get("decision_metadata") or {}).get(
        "cohort_filter", {}).get("signal_type")
    baselines = ch.get("baselines") or {}
    if sig_type in baselines:
        lines.append(f"\nbaseline for {sig_type}: {json.dumps(baselines[sig_type])}")
    lines.append("")

    lines.append("**regime_watch:**")
    lines.append(json.dumps({
        "current_regime": rw.get("current_regime"),
        "regime_stability": rw.get("regime_stability"),
        "days_in_current_regime": rw.get("days_in_current_regime"),
        "recent_distribution_7d": rw.get("recent_distribution_7d"),
        "prior_distribution_7d": rw.get("prior_distribution_7d"),
    }, indent=2))
    lines.append("")

    lines.append("**portfolio_exposure (summary):**")
    lines.append(json.dumps({
        "total_open": pe.get("total_open"),
        "by_signal_type": pe.get("by_signal_type"),
        "by_regime": pe.get("by_regime"),
        "regime_concentration": pe.get("regime_concentration"),
        "n_concentrations_flagged": len(pe.get("concentrations") or []),
    }, indent=2))
    lines.append("")

    lines.append("### History context (90-day window)")
    lines.append("")
    lines.append(f"**reasoning_log entries for cohort_promotion_judge "
                 f"(last {_HISTORY_REASONING_LOG_LIMIT}):** "
                 f"{len(history['reasoning_log_entries'])} entries")
    if history["reasoning_log_entries"]:
        for e in history["reasoning_log_entries"]:
            lines.append(f"- {e.get('timestamp')}: candidate {e.get('candidate_id')} → "
                         f"{e.get('decision')}: {e.get('rationale')}")
    lines.append("")
    lines.append(f"**decisions_journal entries with cohort identity match "
                 f"(last {_HISTORY_DECISIONS_JOURNAL_LIMIT}):** "
                 f"{len(history['decisions_journal_entries'])} entries")
    if history["decisions_journal_entries"]:
        for e in history["decisions_journal_entries"]:
            lines.append(f"- {e.get('decision_at') or e.get('created_at')}: "
                         f"{e.get('type')} {e.get('candidate_id')} → "
                         f"{e.get('decision') or e.get('status')}: "
                         f"{e.get('decision_reason') or '?'}")
    lines.append("")

    lines.append("### Question")
    lines.append("")
    lines.append("Evaluate the boost_promote candidate above. "
                 "Return strict JSON per the schema in the system prompt.")

    return "\n".join(lines)


def _build_user_prompt_regime_shift(derived_views: dict, history: dict) -> str:
    """User prompt for regime_shift_detector."""
    rw = derived_views.get("regime_watch", {}) or {}

    lines = ["## Inputs", "", "### regime_watch (full)", ""]
    lines.append(json.dumps(rw, indent=2))
    lines.append("")

    lines.append("### History context (90-day window)")
    lines.append(f"**Prior regime_alert reasoning entries:** "
                 f"{len(history['reasoning_log_entries'])} entries")
    for e in history["reasoning_log_entries"]:
        lines.append(f"- {e.get('timestamp')}: {e.get('decision')}: {e.get('rationale')}")
    lines.append("")

    lines.append("### Question")
    lines.append("")
    lines.append("Does regime_watch show a true regime shift worth alerting "
                 "the trader, or one-week wobble? Return strict JSON per the "
                 "schema in the system prompt.")
    return "\n".join(lines)


def _build_user_prompt_exposure_correlation(
        derived_views: dict, history: dict) -> str:
    """User prompt for exposure_correlation_analyzer."""
    pe = derived_views.get("portfolio_exposure", {}) or {}
    ch = derived_views.get("cohort_health", {}) or {}

    # Tier mapping for each concentration cell
    tier_lookups = []
    for conc in pe.get("concentrations", []) or []:
        cf = conc.get("concentration_filter", {}) or {}
        sig = cf.get("signal_type")
        sec = cf.get("sector")
        reg = cf.get("regime")
        # Look up signal+sector cohort tier
        for c in ch.get("cohorts", []):
            ccf = c.get("cohort_filter", {}) or {}
            if (ccf.get("signal_type") == sig and
                    (ccf.get("sector") == sec or ccf.get("regime") == reg)):
                tier_lookups.append({
                    "concentration": conc.get("concentration_label"),
                    "matched_cohort_id": c.get("cohort_id"),
                    "matched_cohort_tier": c.get("tier"),
                    "matched_cohort_n": c.get("n"),
                })
                break

    lines = ["## Inputs", "", "### portfolio_exposure (full)", ""]
    lines.append(json.dumps(pe, indent=2))
    lines.append("")

    lines.append("### cohort_health tier lookups for concentration cells")
    lines.append(json.dumps(tier_lookups, indent=2))
    lines.append("")

    lines.append("### History context (90-day window)")
    lines.append(f"**Prior exposure_warn reasoning entries:** "
                 f"{len(history['reasoning_log_entries'])} entries")
    for e in history["reasoning_log_entries"]:
        lines.append(f"- {e.get('timestamp')}: {e.get('decision')}: {e.get('rationale')}")
    lines.append("")

    lines.append("### Question")
    lines.append("")
    lines.append("Does portfolio_exposure show concentration risk worthy of "
                 "trader attention? Return strict JSON per the schema in the "
                 "system prompt.")
    return "\n".join(lines)


# ── Orchestrator (V-9 / V-11) ────────────────────────────────────────

def run_step5(
        derived_views: dict,
        step4_candidates: list,
        prior_reasoning_log: Optional[dict] = None,
        prior_decisions_journal: Optional[dict | list] = None,
        output_dir: str = "output",
        mode: str = "production",
        client=None,
        run_id: Optional[str] = None) -> dict:
    """Step 5 orchestrator. 3 gates fire in sequence; cost tracked
    cumulatively per run; circuit breaker aborts at $5; failures skip
    individual gates without aborting the run.

    mode: "production" (default; real Anthropic client) | "smoke"
          (mock client must be passed via client= param).
    client: Anthropic SDK client OR mock. None defaults to real Anthropic().
    run_id: optional; when provided (Step 6 orchestrator-supplied per
            Phase 1 LOCK C), threaded into all reasoning_log entries.
            Falls back to legacy brain_step5_run_<iso> format when None.
    """
    if mode == "production" and client is None:
        from anthropic import Anthropic
        from dotenv import load_dotenv
        load_dotenv()
        client = Anthropic()

    if prior_reasoning_log is None:
        prior_reasoning_log = _load_reasoning_log(output_dir)

    cost_state = RunCostState()
    if run_id is None:
        run_id = (f"brain_step5_run_"
                  f"{datetime.now(_IST).isoformat(timespec='seconds')}")

    # Filter candidates to boost_promote for gate 1 (only these are
    # cohort_promotion_judge's input). Other Step 4 candidate types
    # (boost_demote, cohort_review, kill_rule) pass through unmodified.
    boost_candidates = [c for c in step4_candidates
                        if c.get("type") == "boost_promote"]
    other_candidates = [c for c in step4_candidates
                        if c.get("type") != "boost_promote"]

    all_failures = []

    # Gate 1: cohort_promotion_judge
    enriched_boost, failures1 = _run_cohort_promotion_judge(
        boost_candidates, derived_views,
        prior_reasoning_log, prior_decisions_journal,
        client, cost_state, run_id, output_dir)
    all_failures.extend(failures1)

    # Gate 2: regime_shift_detector
    regime_alert, failures2 = _run_regime_shift_detector(
        derived_views, prior_reasoning_log, prior_decisions_journal,
        client, cost_state, run_id, output_dir)
    all_failures.extend(failures2)

    # Gate 3: exposure_correlation_analyzer
    exposure_warn, failures3 = _run_exposure_correlation_analyzer(
        derived_views, prior_reasoning_log, prior_decisions_journal,
        client, cost_state, run_id, output_dir)
    all_failures.extend(failures3)

    # Assemble final candidate list
    final = list(other_candidates) + list(enriched_boost)
    if regime_alert is not None:
        final.append(regime_alert)
    if exposure_warn is not None:
        final.append(exposure_warn)

    # Verify all candidates pass brain_verify shape contract
    verified = []
    for c in final:
        ok, viols = brain_verify.verify_proposal(c)
        if not ok:
            brain_verify.log_verification_failure(
                c, viols, "brain_reason.run_step5", output_dir)
            print(f"[brain_reason] REJECTED post-Step5 "
                  f"{c.get('candidate_id')}: {viols}", file=sys.stderr)
            continue
        verified.append(c)

    cost_summary = {
        "total_calls": cost_state.total_calls,
        "total_input_tokens": cost_state.total_input_tokens,
        "total_output_tokens": cost_state.total_output_tokens,
        "total_cost_usd": cost_state.total_cost_usd,
        "soft_warning_fired": cost_state.soft_warning_fired,
        "circuit_breaker_aborted": cost_state.should_abort(),
        "gates_completed": cost_state.gates_completed,
        "gates_skipped_due_to_abort": cost_state.gates_skipped_due_to_abort,
        "gates_skipped_due_to_failure": cost_state.gates_skipped_due_to_failure,
    }

    return {
        "candidates": verified,
        "cost_summary": cost_summary,
        "run_id": run_id,
        "failures": all_failures,
    }
