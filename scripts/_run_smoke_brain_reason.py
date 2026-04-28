"""Wave 5 Step 5 smoke — brain_reason.py LLM gates.

Per CLAUDE.md §4 sandbox pattern + V-10/V-14 mock-via-injection.

Mock client lives ONLY here; brain_reason.py production code never imports
or contains mock infrastructure. Smoke uses canned responses with realistic
token counts so cost tracking exercises real arithmetic.

Smoke groups:
  A — gate output parsing (each gate's response → parsed correctly)
  B — cost tracking ($1 soft, $5 abort, gates skipped on abort)
  C — reasoning_log append (4 mocked calls → 4 entries)
  D — failure handling (mock raises → retry → skip-gate fallback)
  E — verify integration (all output candidates pass verify)
  F — SHA256 invariants on real files
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)

REAL_HISTORY = os.path.join(ROOT, "output", "signal_history.json")
REAL_PROPOSED = os.path.join(ROOT, "output", "proposed_rules.json")
REAL_MINI = os.path.join(ROOT, "data", "mini_scanner_rules.json")
REAL_COHORT_HEALTH = os.path.join(ROOT, "output", "brain", "cohort_health.json")
REAL_REGIME = os.path.join(ROOT, "output", "brain", "regime_watch.json")
REAL_EXPOSURE = os.path.join(ROOT, "output", "brain", "portfolio_exposure.json")
REAL_GTG = os.path.join(ROOT, "output", "brain", "ground_truth_gaps.json")


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ── Mock Anthropic SDK objects ──────────────────────────────────────

class _MockUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _MockTextBlock:
    def __init__(self, text):
        self.text = text


class _MockMessage:
    def __init__(self, text, input_tokens, output_tokens, msg_id="msg_mock"):
        self.content = [_MockTextBlock(text)]
        self.usage = _MockUsage(input_tokens, output_tokens)
        self.id = msg_id
        self.model = "claude-opus-4-7"
        self.stop_reason = "end_turn"


class _MockClient:
    """Returns canned responses indexed by gate_name (system prompt prefix)
    + sequential call counter per gate. Each canned response carries a
    realistic input_tokens + output_tokens count so cost tracking
    exercises real arithmetic."""

    def __init__(self, canned_responses):
        self._canned = canned_responses
        self._counter = {}
        self.messages = self  # so client.messages.create works
        self.fail_modes = {}  # {gate_name: fail_count_remaining}

    def create(self, **kwargs):
        system = kwargs.get("system", "")
        # Identify gate from system prompt
        gate = None
        for name in ("cohort_promotion_judge",
                     "regime_shift_detector",
                     "exposure_correlation_analyzer"):
            if name in system:
                gate = name
                break
        if gate is None:
            raise RuntimeError("Mock could not identify gate from system prompt")

        # Failure simulation
        if self.fail_modes.get(gate, 0) > 0:
            self.fail_modes[gate] -= 1
            raise TimeoutError(f"Simulated timeout for gate={gate}")

        responses = self._canned.get(gate, [])
        idx = self._counter.get(gate, 0)
        if idx >= len(responses):
            raise RuntimeError(f"Mock ran out of canned responses for {gate}")
        resp = responses[idx]
        self._counter[gate] = idx + 1
        return _MockMessage(
            text=resp["text"],
            input_tokens=resp["input_tokens"],
            output_tokens=resp["output_tokens"],
        )


# ── Canned responses ────────────────────────────────────────────────

def _canned_set_basic():
    """Approve both boost_promote, no regime alert, generate exposure warn."""
    return {
        "cohort_promotion_judge": [
            {
                "text": json.dumps({
                    "decision": "approve",
                    "rationale": "Tier M cohort UP_TRI×Bear; strong evidence; portfolio risk noted.",
                    "additional_counter_evidence": ["UP_TRI 76/80 of open positions; concentration risk."],
                    "additional_risks": ["Bear regime absent; promotion may not fire near-term."],
                    "confidence_override": None,
                    "disagreement_detected": False,
                }),
                "input_tokens": 2000,
                "output_tokens": 250,
            },
            {
                "text": json.dumps({
                    "decision": "approve",
                    "rationale": "Tier M cohort UP_TRI×Metal; clean record n=15 with 100% WR.",
                    "additional_counter_evidence": ["Sample size n=15 borderline for Tier M."],
                    "additional_risks": ["Metal sector concentration noted."],
                    "confidence_override": None,
                    "disagreement_detected": False,
                }),
                "input_tokens": 1900,
                "output_tokens": 230,
            },
        ],
        "regime_shift_detector": [
            {
                "text": json.dumps({
                    "decision": "no_alert",
                    "rationale": "Choppy stable 7 days; transition window passed.",
                    "alert_payload": None,
                }),
                "input_tokens": 1200,
                "output_tokens": 150,
            },
        ],
        "exposure_correlation_analyzer": [
            {
                "text": json.dumps({
                    "decision": "generate_warn",
                    "rationale": "100% Choppy regime + UP_TRI dominance; pause new entries.",
                    "warn_payload": {
                        "concentration_axis": "by_regime",
                        "concentration_value": "Choppy",
                        "share": 1.0,
                        "evidence": ["80/80 open positions in Choppy regime"],
                        "recommended_action": "Pause new entries until regime concentration drops below 80%",
                        "tail_risk_scenario": "If regime shifts to Bear, all 80 positions face simultaneous adverse exposure",
                    },
                }),
                "input_tokens": 2400,
                "output_tokens": 400,
            },
        ],
    }


def _canned_set_for_cost_test_high_tokens():
    """Generate calls with high token counts to drive costs."""
    return {
        "cohort_promotion_judge": [
            {"text": json.dumps({"decision": "approve", "rationale": "x",
                                  "additional_counter_evidence": [],
                                  "additional_risks": ["r"],
                                  "confidence_override": None,
                                  "disagreement_detected": False}),
             "input_tokens": 200_000, "output_tokens": 30_000},
            {"text": json.dumps({"decision": "approve", "rationale": "x",
                                  "additional_counter_evidence": [],
                                  "additional_risks": ["r"],
                                  "confidence_override": None,
                                  "disagreement_detected": False}),
             "input_tokens": 200_000, "output_tokens": 30_000},
        ],
        "regime_shift_detector": [
            {"text": json.dumps({"decision": "no_alert", "rationale": "x",
                                  "alert_payload": None}),
             "input_tokens": 200_000, "output_tokens": 30_000},
        ],
        "exposure_correlation_analyzer": [
            {"text": json.dumps({"decision": "no_warn", "rationale": "x",
                                  "warn_payload": None}),
             "input_tokens": 200_000, "output_tokens": 30_000},
        ],
    }


# ── Smoke groups ────────────────────────────────────────────────────

def _make_step4_candidates(cohort_health):
    from scanner.brain.brain_verify import generate_boost_promote_candidates
    return generate_boost_promote_candidates(cohort_health)


def _run_group_A(sbx_output):
    """Each gate's output parsed correctly + decision dispatch."""
    from scanner.brain import brain_reason

    cohort_health = json.load(open(REAL_COHORT_HEALTH))
    regime_watch = json.load(open(REAL_REGIME))
    portfolio_exposure = json.load(open(REAL_EXPOSURE))
    derived = {
        "cohort_health": cohort_health,
        "regime_watch": regime_watch,
        "portfolio_exposure": portfolio_exposure,
    }
    step4_cands = _make_step4_candidates(cohort_health)
    assert len(step4_cands) == 2, f"A precondition fail: expected 2 step4 candidates, got {len(step4_cands)}"

    mock = _MockClient(_canned_set_basic())
    result = brain_reason.run_step5(
        derived, step4_cands,
        prior_reasoning_log=None, prior_decisions_journal=None,
        output_dir=sbx_output, mode="smoke", client=mock)

    # 4 calls total (2 cohort + 1 regime + 1 exposure)
    assert result["cost_summary"]["total_calls"] == 4, \
        f"A1 fail: expected 4 calls, got {result['cost_summary']['total_calls']}"

    # No regime_alert, 1 exposure_warn, 2 boost_promote enriched
    types = [c["type"] for c in result["candidates"]]
    assert types.count("boost_promote") == 2, f"A2 fail: types={types}"
    assert types.count("regime_alert") == 0, f"A3 fail: types={types}"
    assert types.count("exposure_warn") == 1, f"A4 fail: types={types}"

    # Enrichment landed
    bp_a = next(c for c in result["candidates"] if c["type"] == "boost_promote")
    evidence_strings = " ".join(bp_a["counter"]["evidence"])
    assert "concentration risk" in evidence_strings.lower() or \
           "UP_TRI" in evidence_strings, \
        f"A5 fail: enrichment not applied: {bp_a['counter']['evidence']}"


def _run_group_B(sbx_output):
    """Cost tracking + circuit breaker."""
    from scanner.brain import brain_reason

    cohort_health = json.load(open(REAL_COHORT_HEALTH))
    derived = {
        "cohort_health": cohort_health,
        "regime_watch": json.load(open(REAL_REGIME)),
        "portfolio_exposure": json.load(open(REAL_EXPOSURE)),
    }
    step4_cands = _make_step4_candidates(cohort_health)

    # Use high-token canned to drive cost
    mock = _MockClient(_canned_set_for_cost_test_high_tokens())
    result = brain_reason.run_step5(
        derived, step4_cands,
        prior_reasoning_log=None, prior_decisions_journal=None,
        output_dir=sbx_output, mode="smoke", client=mock)

    # Each call: 200k input × $5/M + 30k output × $25/M = $1.00 + $0.75 = $1.75
    # 1st call: cumulative $1.75 → soft_warning fires
    # 2nd call: cumulative $3.50
    # 3rd call: cumulative $5.25 → would fire abort AFTER this call
    # 4th gate: skipped due to abort
    # Expected: 3 calls completed, abort fired, 1 gate skipped due to abort
    cs = result["cost_summary"]
    assert cs["soft_warning_fired"] is True, "B1 fail: soft warning should fire"
    assert cs["circuit_breaker_aborted"] is True, "B2 fail: abort should fire"
    assert cs["total_calls"] == 3, f"B3 fail: expected 3 calls before abort, got {cs['total_calls']}"
    assert len(cs["gates_skipped_due_to_abort"]) >= 1, \
        f"B4 fail: at least 1 gate should be skipped, got {cs['gates_skipped_due_to_abort']}"


def _run_group_C(sbx_output):
    """reasoning_log append: 4 mocked calls → 4 entries; schema correct."""
    from scanner.brain import brain_reason

    cohort_health = json.load(open(REAL_COHORT_HEALTH))
    derived = {
        "cohort_health": cohort_health,
        "regime_watch": json.load(open(REAL_REGIME)),
        "portfolio_exposure": json.load(open(REAL_EXPOSURE)),
    }
    step4_cands = _make_step4_candidates(cohort_health)

    mock = _MockClient(_canned_set_basic())
    brain_reason.run_step5(
        derived, step4_cands,
        prior_reasoning_log=None, prior_decisions_journal=None,
        output_dir=sbx_output, mode="smoke", client=mock)

    log_path = os.path.join(sbx_output, "brain", "reasoning_log.json")
    assert os.path.exists(log_path), "C1 fail: reasoning_log not written"
    log = json.load(open(log_path))
    assert log.get("schema_version") == 1, "C2 fail: schema_version"
    assert log.get("view_name") == "reasoning_log", "C3 fail: view_name"
    assert len(log["entries"]) == 4, f"C4 fail: expected 4 entries, got {len(log['entries'])}"

    # Each entry has required fields
    for e in log["entries"]:
        for k in ("timestamp", "run_id", "gate_name", "model", "input_tokens",
                  "output_tokens", "cost_usd", "request_id", "decision",
                  "rationale", "gate_input_summary", "aborted_by_circuit_breaker"):
            assert k in e, f"C5 fail: entry missing {k}"
        assert e["model"] == "claude-opus-4-7"


def _run_group_D(sbx_output):
    """Failure handling: gate raises → retry → succeed on attempt 2."""
    from scanner.brain import brain_reason

    cohort_health = json.load(open(REAL_COHORT_HEALTH))
    derived = {
        "cohort_health": cohort_health,
        "regime_watch": json.load(open(REAL_REGIME)),
        "portfolio_exposure": json.load(open(REAL_EXPOSURE)),
    }
    step4_cands = _make_step4_candidates(cohort_health)

    mock = _MockClient(_canned_set_basic())
    # First call to regime_shift_detector fails, second succeeds
    mock.fail_modes = {"regime_shift_detector": 1}

    # The retry logic has the wrapper retry once on Timeout. With fail_modes=1,
    # first call raises, retry succeeds.
    result = brain_reason.run_step5(
        derived, step4_cands,
        prior_reasoning_log=None, prior_decisions_journal=None,
        output_dir=sbx_output, mode="smoke", client=mock)

    # Should still produce a valid result (regime gate retried successfully)
    assert "regime_shift_detector" in result["cost_summary"]["gates_completed"], \
        f"D1 fail: regime gate should complete after retry: {result['cost_summary']}"


def _run_group_E(sbx_output):
    """Verify integration: all output candidates pass verify_proposal."""
    from scanner.brain import brain_reason, brain_verify

    cohort_health = json.load(open(REAL_COHORT_HEALTH))
    derived = {
        "cohort_health": cohort_health,
        "regime_watch": json.load(open(REAL_REGIME)),
        "portfolio_exposure": json.load(open(REAL_EXPOSURE)),
    }
    step4_cands = _make_step4_candidates(cohort_health)

    mock = _MockClient(_canned_set_basic())
    result = brain_reason.run_step5(
        derived, step4_cands,
        prior_reasoning_log=None, prior_decisions_journal=None,
        output_dir=sbx_output, mode="smoke", client=mock)

    for c in result["candidates"]:
        ok, viols = brain_verify.verify_proposal(c)
        assert ok, f"E fail: {c['candidate_id']} failed verify: {viols}"


def main():
    inv_files = [REAL_HISTORY, REAL_PROPOSED, REAL_MINI,
                 REAL_COHORT_HEALTH, REAL_REGIME, REAL_EXPOSURE, REAL_GTG]
    inv_before = {f: _sha256(f) for f in inv_files}

    sbx = tempfile.mkdtemp(prefix="smoke_brain_reason_")
    sbx_output = os.path.join(sbx, "output")
    os.makedirs(os.path.join(sbx_output, "brain"), exist_ok=True)

    try:
        # Each group gets its own clean sandbox subfolder so reasoning_log
        # writes don't carry between groups
        for group_name, fn in [
            ("A — gate output parsing", _run_group_A),
            ("B — cost tracking + circuit breaker", _run_group_B),
            ("C — reasoning_log append", _run_group_C),
            ("D — failure handling (retry success)", _run_group_D),
            ("E — verify integration", _run_group_E),
        ]:
            sbx_group = os.path.join(sbx, group_name.split(" ")[0])
            os.makedirs(os.path.join(sbx_group, "brain"), exist_ok=True)
            fn(sbx_group)
            print(f"Group {group_name}: PASS")

        # F — SHA256 invariants
        for f in inv_files:
            assert _sha256(f) == inv_before[f], f"REAL FILE MUTATED: {f}"
        print(f"Group F — SHA256 invariants on {len(inv_files)} real files: PASS")

        print("\nALL GROUPS PASS — Step 5 LLM gates verified")
        return 0
    except AssertionError as e:
        print(f"FAIL: {e}")
        return 1
    except Exception as e:
        print(f"FAIL: unexpected {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        return 1
    finally:
        shutil.rmtree(sbx, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
