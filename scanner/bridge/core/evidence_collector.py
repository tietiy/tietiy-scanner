"""
evidence_collector — orchestrates background queries to build the SDR.evidence dict.

Loads truth files ONCE per compose, passes pre-loaded dicts to query plugins.
Each query wrapped in error_handler.safe_run so one failure doesn't kill the
whole evidence collection. Result is the exact shape bucket_engine consumes.

Performance target: <500ms per signal across all 10 queries (7 background +
boost + kill + pattern).

See doc/bridge_design_v1.md §9 (background queries), §4 (SDR schema).
"""

import json
import os
from typing import Any, Optional

from scanner.bridge.core import error_handler
from scanner.bridge.queries import (
    q_anti_pattern,
    q_cluster_check,
    q_exact_cohort,
    q_pattern_match,
    q_regime_baseline,
    q_score_bucket,
    q_sector_recent_30d,
    q_stock_recency,
)
from scanner.bridge.rules import boost_matcher, kill_matcher


_TRUTH_FILE_SPECS = (
    # (key,                base_dir, filename,                  default)
    ("signal_history",     "output", "signal_history.json",     {}),
    ("patterns",           "output", "patterns.json",           {}),
    ("proposed_rules",     "output", "proposed_rules.json",     {}),
    ("contra_shadow",      "output", "contra_shadow.json",      {}),
    ("colab_insights",     "output", "colab_insights.json",     {}),
    ("mini_scanner_rules", "data",   "mini_scanner_rules.json", {}),
)


_last_executed_queries: list = []
_last_failed_queries: list = []


# =====================================================================
# Truth file loading (called once per compose)
# =====================================================================

def load_truth_files(output_dir: str = "output",
                     data_dir: str = "data") -> dict:
    """
    Load all truth files. Missing/malformed files become {} with an
    error_handler DEGRADED entry — caller can inspect via
    error_handler.has_degraded_errors() / get_error_log().
    """
    bases = {"output": output_dir, "data": data_dir}
    out: dict = {}
    for key, base, fname, default in _TRUTH_FILE_SPECS:
        path = os.path.join(bases[base], fname)
        loaded = error_handler.safe_run(
            _load_json_file, path,
            severity="DEGRADED",
            context=f"load_truth_files:{fname}",
        )
        out[key] = loaded if loaded is not None else default
    return out


def _load_json_file(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# Per-signal evidence collection
# =====================================================================

def collect_evidence(signal: dict, truth_files: dict) -> dict:
    """
    Run all 10 queries for one signal; assemble into the SDR.evidence
    dict shape. Never raises — failed queries leave their key at the
    safe default.
    """
    _last_executed_queries.clear()
    _last_failed_queries.clear()

    truth_files = truth_files or {}
    history = truth_files.get("signal_history", {})
    patterns_data = truth_files.get("patterns", {})
    rules_data = truth_files.get("mini_scanner_rules", {}) or {}
    proposals_data = truth_files.get("proposed_rules", {}) or {}
    colab_data = truth_files.get("colab_insights", {}) or {}

    # --- Pattern matching (supporting + opposing) ---
    pattern_result = _run("q_pattern_match",
                          q_pattern_match.run,
                          signal, patterns_data)
    patterns_supporting, patterns_opposing = (
        _split_pattern_result(pattern_result)
    )

    # --- Boost / kill matchers (live in rules/, not queries/) ---
    boost_match = _run("q_boost_match",
                       boost_matcher.check_match,
                       signal,
                       (rules_data or {}).get("boost_patterns", []))
    kill_match  = _run("q_kill_match",
                       kill_matcher.check_match,
                       signal,
                       (rules_data or {}).get("kill_patterns", []))

    # --- Cohort + recency + baseline queries ---
    exact_cohort = _run("q_exact_cohort",
                        q_exact_cohort.run, signal, history)
    sector_recent_30d = _run("q_sector_recent_30d",
                             q_sector_recent_30d.run, signal, history)
    regime_baseline = _run("q_regime_baseline",
                           q_regime_baseline.run, signal, history)
    score_bucket = _run("q_score_bucket",
                        q_score_bucket.run, signal, history)
    stock_recency = _run("q_stock_recency",
                         q_stock_recency.run, signal, history)
    anti_pattern_check = _run("q_anti_pattern",
                              q_anti_pattern.run,
                              signal, patterns_data)
    cluster_warnings = _run("q_cluster_check",
                            q_cluster_check.run, signal, history)
    if cluster_warnings is None:
        cluster_warnings = []

    # --- Non-query auxiliaries (filled directly from truth files) ---
    active_proposals_relevant = _filter_relevant_proposals(
        signal, proposals_data)
    colab_insight_excerpt = _extract_colab_excerpt(
        signal, colab_data)

    return {
        "patterns_supporting":       patterns_supporting,
        "patterns_opposing":         patterns_opposing,
        "boost_match":               boost_match,
        "kill_match":                kill_match,
        "exact_cohort":              exact_cohort,
        "sector_recent_30d":         sector_recent_30d,
        "regime_baseline":           regime_baseline,
        "score_bucket":              score_bucket,
        "stock_recency":             stock_recency,
        "anti_pattern_check":        anti_pattern_check,
        "cluster_warnings":          cluster_warnings,
        "active_proposals_relevant": active_proposals_relevant,
        "colab_insight_excerpt":     colab_insight_excerpt,
        "narrative_context":         None,
    }


def get_queries_executed_list() -> list:
    """Names of queries attempted in most recent collect_evidence call."""
    return list(_last_executed_queries)


def get_queries_failed_list() -> list:
    """Names of queries that raised in most recent collect_evidence call."""
    return list(_last_failed_queries)


# =====================================================================
# Helpers
# =====================================================================

def _run(name: str, fn, *args) -> Any:
    """
    Execute fn(*args) under error_handler.safe_run with WARNING severity.
    Tracks execution + failure into module-level lists.
    Detects failure by snapshotting error_handler's log size.
    """
    _last_executed_queries.append(name)
    log_before = len(error_handler.get_error_log())
    result = error_handler.safe_run(
        fn, *args, severity="WARNING", context=name)
    log_after = len(error_handler.get_error_log())
    if log_after > log_before:
        _last_failed_queries.append(name)
    return result


def _split_pattern_result(result: Any) -> tuple:
    """
    q_pattern_match may return:
      - dict with 'supporting'/'opposing' keys
      - flat list (treated as supporting; opposing empty)
      - None (failure) → both empty
    """
    if isinstance(result, dict):
        return (
            list(result.get("supporting", []) or []),
            list(result.get("opposing", []) or []),
        )
    if isinstance(result, list):
        return list(result), []
    return [], []


def _filter_relevant_proposals(signal: dict,
                               proposals_data: dict) -> list:
    """
    Filter proposed_rules.json proposals to those targeting this
    signal's cohort. Wave 2: minimal — match on target_signal or
    target_sector top-level fields (real proposal schema per
    rule_proposer._build_proposal). Real filtering lives in a
    future query plugin.

    Note: bridge-side signal uses 'signal_type' / 'sector'; proposal
    records use 'target_signal' / 'target_sector' at top level (no
    nested cohort dict).
    """
    if not isinstance(proposals_data, dict):
        return []
    proposals = proposals_data.get("proposals", []) or []
    sig_type = signal.get("signal_type")
    sector   = signal.get("sector")
    out = []
    for p in proposals:
        if not isinstance(p, dict):
            continue
        if (p.get("target_signal") == sig_type
                or p.get("target_sector") == sector):
            out.append(p)
    return out


def _extract_colab_excerpt(signal: dict,
                           colab_data: dict) -> Optional[str]:
    """
    Pull a sector-relevant excerpt from colab_insights.json if present.
    Falls back to top-level 'excerpt' or None.
    """
    if not isinstance(colab_data, dict):
        return None
    sector = signal.get("sector")
    by_sector = colab_data.get("by_sector", {}) or {}
    if isinstance(by_sector, dict) and sector in by_sector:
        v = by_sector[sector]
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return v.get("excerpt") or v.get("text")
    return colab_data.get("excerpt")
