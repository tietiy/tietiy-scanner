"""Wave 5 Step 3 smoke — derived views layer.

Per CLAUDE.md §4 sandbox pattern + brain_design §4 Step 3 smoke spec.

Sequence:
1. SHA256 capture of real output/signal_history.json
2. Sandbox tempdir; copy real truth files
3. Run brain_derive.run_all against sandbox
4. Per-view assertions (4 views): file exists + schema_version=1 +
   generated_at + as_of_date + non-empty per-view content + shape checks
5. History archive assertions (4 views): file exists at history/<date>_<view>.json
6. list_brain_archives + load_brain_archive primitives smoke
7. Idempotency: run brain_derive a second time; diff outputs (strip
   generated_at); assert identical
8. Real signal_history SHA256 invariant
9. Cleanup sandbox; print PASS/FAIL summary
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

# Ensure repo root on path
ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)

REAL_HISTORY = os.path.join(ROOT, "output", "signal_history.json")
REAL_OUTPUT = os.path.join(ROOT, "output")
REAL_DATA = os.path.join(ROOT, "data")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _strip_volatile(d: dict) -> dict:
    """Remove generated_at + warnings (warnings may include timestamps
    indirectly via age_days computed against today)."""
    out = json.loads(json.dumps(d))  # deep copy
    out.pop("generated_at", None)
    if "_metadata" in out:
        out["_metadata"].pop("warnings", None)
    return out


def _assert_cohort_health_shape(data: dict):
    assert data.get("schema_version") == 1, f"cohort_health schema_version: {data.get('schema_version')!r}"
    assert data.get("view_name") == "cohort_health"
    assert data.get("as_of_date"), "cohort_health missing as_of_date"
    assert "cohorts" in data and isinstance(data["cohorts"], list)
    assert "baselines" in data and isinstance(data["baselines"], dict)
    assert "_metadata" in data
    md = data["_metadata"]
    assert md["n_min_for_inclusion"] == 3
    assert md["wilson_confidence"] == 0.95
    assert "axes_evaluated" in md
    assert isinstance(md.get("warnings"), list)
    if data["cohorts"]:
        c = data["cohorts"][0]
        for k in ("cohort_id", "cohort_axis", "cohort_filter", "n",
                  "wins", "losses", "flat", "wr", "wr_wilson_lower",
                  "avg_pnl_pct", "edge_vs_baseline_pp", "tier"):
            assert k in c, f"cohort missing field: {k}"
        assert c["tier"] in {"S", "M", "W", "Candidate"}, f"invalid tier: {c['tier']}"
        assert 0 <= c["wr"] <= 1, f"wr out of [0,1]: {c['wr']}"
        assert 0 <= c["wr_wilson_lower"] <= 1, f"wilson out of [0,1]"


def _assert_regime_watch_shape(data: dict):
    assert data.get("schema_version") == 1
    assert data.get("view_name") == "regime_watch"
    assert data.get("current_regime")
    assert data.get("regime_stability") in {"stable", "shifting", "unclear"}
    assert "weekly_intelligence_snapshot" in data
    assert "transition_evidence" in data
    assert isinstance(data["_metadata"].get("warnings"), list)


def _assert_portfolio_exposure_shape(data: dict):
    assert data.get("schema_version") == 1
    assert data.get("view_name") == "portfolio_exposure"
    assert "total_open" in data and isinstance(data["total_open"], int)
    assert "by_signal_type" in data
    assert "by_sector" in data
    assert "by_regime" in data
    rc = data.get("regime_concentration")
    assert rc is not None, "regime_concentration must be always-present per K-3"
    assert "triggered" in rc and isinstance(rc["triggered"], bool)
    assert "threshold" in rc
    assert "observed" in rc
    assert "axis" in rc
    if rc["triggered"]:
        assert "dominant_regime" in rc
    assert "concentrations" in data and isinstance(data["concentrations"], list)
    assert isinstance(data["_metadata"].get("warnings"), list)


def _assert_ground_truth_gaps_shape(data: dict):
    assert data.get("schema_version") == 1
    assert data.get("view_name") == "ground_truth_gaps"
    assert "thin_rules" in data and isinstance(data["thin_rules"], list)
    assert "thin_patterns" in data and isinstance(data["thin_patterns"], list)
    assert "summary" in data
    assert isinstance(data["_metadata"].get("warnings"), list)


SHAPE_CHECKERS = {
    "cohort_health": _assert_cohort_health_shape,
    "regime_watch": _assert_regime_watch_shape,
    "portfolio_exposure": _assert_portfolio_exposure_shape,
    "ground_truth_gaps": _assert_ground_truth_gaps_shape,
}


def main():
    real_sha_before = _sha256(REAL_HISTORY)
    sbx = tempfile.mkdtemp(prefix="smoke_brain_derive_")
    sbx_output = os.path.join(sbx, "output")
    sbx_data = os.path.join(sbx, "data")
    sbx_history_dir = os.path.join(sbx_output, "bridge_state_history")
    os.makedirs(sbx_output, exist_ok=True)
    os.makedirs(sbx_data, exist_ok=True)
    os.makedirs(sbx_history_dir, exist_ok=True)

    # Copy truth files
    truth_files = ("signal_history.json", "patterns.json",
                   "proposed_rules.json", "contra_shadow.json",
                   "weekly_intelligence_latest.json")
    for f in truth_files:
        src = os.path.join(REAL_OUTPUT, f)
        if os.path.exists(src):
            shutil.copy(src, sbx_output)
    shutil.copy(os.path.join(REAL_DATA, "mini_scanner_rules.json"), sbx_data)
    # Copy today's EOD archive if exists
    real_history_dir = os.path.join(REAL_OUTPUT, "bridge_state_history")
    if os.path.isdir(real_history_dir):
        for f in os.listdir(real_history_dir):
            if f.endswith("_EOD.json"):
                shutil.copy(os.path.join(real_history_dir, f), sbx_history_dir)

    try:
        from scanner.brain import brain_derive, brain_state

        # Run #1
        result1 = brain_derive.run_all(output_dir=sbx_output, data_dir=sbx_data)
        assert not result1["errors"], f"errors in run_all: {result1['errors']}"

        sbx_brain = os.path.join(sbx_output, "brain")
        sbx_brain_history = os.path.join(sbx_brain, "history")

        run1_data = {}
        for view in ("cohort_health", "regime_watch", "portfolio_exposure", "ground_truth_gaps"):
            current_path = os.path.join(sbx_brain, f"{view}.json")
            assert os.path.exists(current_path), f"missing current: {view}"
            data = json.load(open(current_path))
            SHAPE_CHECKERS[view](data)
            run1_data[view] = data

            # History archive exists with today's date prefix
            today = data["as_of_date"]
            history_path = os.path.join(sbx_brain_history, f"{today}_{view}.json")
            assert os.path.exists(history_path), f"missing history: {view}"

        # Cross-day primitives smoke
        cohort_archives = brain_state.list_brain_archives("cohort_health", sbx_output)
        assert len(cohort_archives) >= 1, "list_brain_archives empty"
        loaded = brain_state.load_brain_archive("cohort_health", cohort_archives[0], sbx_output)
        assert loaded is not None and loaded.get("view_name") == "cohort_health"

        # Idempotency: run again
        result2 = brain_derive.run_all(output_dir=sbx_output, data_dir=sbx_data)
        assert not result2["errors"], f"errors in run #2: {result2['errors']}"
        for view in ("cohort_health", "regime_watch", "portfolio_exposure", "ground_truth_gaps"):
            data2 = json.load(open(os.path.join(sbx_brain, f"{view}.json")))
            stripped1 = _strip_volatile(run1_data[view])
            stripped2 = _strip_volatile(data2)
            assert json.dumps(stripped1, sort_keys=True) == json.dumps(stripped2, sort_keys=True), \
                f"{view} not idempotent across runs (sans generated_at + warnings)"

        # Real-history SHA256 invariant per P-9 / CLAUDE.md §4
        real_sha_after = _sha256(REAL_HISTORY)
        assert real_sha_before == real_sha_after, "REAL signal_history MUTATED!"

        print("PASS — 4 views + history archives + cross-day primitives "
              "+ idempotency + SHA256 invariant")
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
