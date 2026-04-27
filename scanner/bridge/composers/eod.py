"""
eod — L4 (EOD) bridge composer.

Run at 16:00 IST after eod_master.yml (15:35) has executed
outcome_evaluator, pattern_miner, rule_proposer, and chain_validator.
By the time this fires, signal_history.json is already mutated with
today's resolutions. The EOD composer is READ-ONLY: it reads the fresh
state and produces:

  - Per-resolution EOD SDRs (one per signal where outcome_date ==
    market_date AND outcome != 'OPEN'). Not decision records — these
    are resolution records. No bucket field; outcome block embedded.
  - bridge_state.json (phase=EOD) summarizing today's resolutions.
  - bridge_state_history/{date}_EOD.json archive (via state_writer).

Read-only by design EXCEPT for one deliberate future path (NOT Session
A): kill auto-revert when an invert_to_long contra pattern collapses
below threshold. Per design §7.6 — deferred to Wave 4 contra track.

Sessions B/C/D add: Telegram digest renderer, demotion warnings,
workflow YAML.

See doc/bridge_design_v1.md §3 (EOD day-flow), §12.3 (digest template),
§13 (workflow), §7.6 (auto-revert — deferred).
"""

import time
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo


# Helpers shared with L1/L2 — imported from premarket.py to avoid duplication.
# If this list grows past ~12 imports, refactor to
# scanner/bridge/composers/_common.py.
from scanner.bridge.composers.premarket import (
    _strip_ns_suffix,
    _infer_direction,
    _today_ist,
    _now_iso,
    _build_contra_block,
    _build_basic_alerts,
    _build_audit,
)

from scanner.bridge.core import (
    error_handler,
    evidence_collector,
    state_writer,
    upstream_health,
)
from scanner.bridge.queries import q_open_positions
from scanner.bridge.rules.thresholds import (
    BOOST_DEMOTION_WINDOW_N,
    BOOST_DEMOTION_WR,
    BRIDGE_STATE_SCHEMA_VERSION,
)


_PHASE = "EOD"
_BRIDGE_VERSION = "1.0.0"
_IST = ZoneInfo("Asia/Kolkata")

_BANNER_COLOR = {
    "OK":       "green",
    "DEGRADED": "orange",
    "ERROR":    "red",
    "SKIPPED":  "neutral",
}

# Outcome categorization for summary counters
_WIN_OUTCOMES  = ("TARGET_HIT", "DAY6_WIN")
_LOSS_OUTCOMES = ("STOP_HIT", "DAY6_LOSS")
_FLAT_OUTCOMES = ("DAY6_FLAT",)


# =====================================================================
# Public entry point
# =====================================================================

def compose(market_date: Optional[str] = None,
            output_dir: str = "output",
            data_dir: str = "data") -> dict:
    """Run the full EOD compose. Always returns a summary dict; never
    raises. On FATAL error, writes emergency state and returns
    phase_status=ERROR.

    EOD summary shape:
        phase, phase_status, market_date, signals_count (resolutions),
        outcomes (count by outcome type), open_positions_count,
        alerts_count, errors_logged, state_file_written, duration_ms.
    """
    start_time = time.monotonic()

    try:
        return _compose_unsafe(
            start_time, market_date, output_dir, data_dir)
    except Exception as e:
        md = market_date or _today_ist()
        emergency = error_handler.build_emergency_state(
            phase=_PHASE,
            market_date=md,
            error_summary=(
                f"compose crashed: {type(e).__name__}: {e}"
            ),
        )
        try:
            state_writer.write_state(emergency, output_dir=output_dir)
        except Exception:
            pass

        return {
            "phase":                _PHASE,
            "phase_status":         "ERROR",
            "market_date":          md,
            "signals_count":        0,
            "outcomes":             _empty_outcome_counts(),
            "open_positions_count": 0,
            "alerts_count":         1,
            "errors_logged":        len(error_handler.get_error_log()),
            "state_file_written":   "",
            "duration_ms":          int((time.monotonic() - start_time) * 1000),
            "error":                f"{type(e).__name__}: {e}",
        }


def _compose_unsafe(start_time: float,
                    market_date: Optional[str],
                    output_dir: str,
                    data_dir: str) -> dict:
    """Main compose flow. Wrapped by compose() for catastrophic safety."""
    error_handler.reset_error_log()

    if market_date is None:
        market_date = _today_ist()

    # Step 1: Load truth files (ONCE)
    truth_files = evidence_collector.load_truth_files(
        output_dir=output_dir, data_dir=data_dir)

    # Step 2: Select today's resolutions from signal_history
    resolutions = _select_resolutions_today(
        truth_files.get("signal_history", {}),
        market_date=market_date,
    )

    # Step 3: Per-resolution compose. Each resolution → one EOD SDR
    # (plain dict — see module docstring on why we don't use the SDR
    # dataclass for resolution records).
    sdrs: list = []
    for signal in resolutions:
        if not isinstance(signal, dict):
            continue
        sig_id = signal.get("id") or "unknown"
        sdr = error_handler.safe_run(
            _process_one_resolution,
            signal, market_date,
            severity="WARNING",
            context=f"compose_resolution:{sig_id}",
        )
        if sdr is not None:
            sdrs.append(sdr)

    # Step 4: Open positions (still-PENDING signals from prior days)
    open_positions = q_open_positions.run(
        truth_files.get("signal_history", {}),
        market_date=market_date,
    ) or []

    # Step 5: Contra block (same as L1/L2)
    contra_block = _build_contra_block(truth_files)

    # Step 6: Upstream health + alerts (same as L1/L2)
    upstream = upstream_health.get_upstream_health(
        output_dir=output_dir, market_date=market_date)
    alerts = _build_basic_alerts(upstream)

    # Step 7: Phase status from logged errors
    phase_status = error_handler.compute_phase_status(default_status="OK")

    # Step 8: Outcome counters (drive summary + banner)
    outcomes = _count_outcomes(sdrs)

    # Step 9: Assemble bridge_state
    state = {
        "schema_version":  BRIDGE_STATE_SCHEMA_VERSION,
        "phase":           _PHASE,
        "phase_status":    phase_status,
        "phase_timestamp": _now_iso(),
        "market_date":     market_date,
        "banner":          _build_eod_banner(
            phase_status, len(sdrs), outcomes),
        "summary":         _build_eod_summary(
            sdrs, open_positions, outcomes,
            truth_files.get("signal_history") or {},
            truth_files.get("mini_scanner_rules") or {},
        ),
        "signals":         sdrs,
        "open_positions":  open_positions,
        "contra":          contra_block,
        "alerts":          alerts,
        "self_queries":    [],   # Wave 5
        "upstream_health": upstream,
        "audit":           _build_audit(
            start_time, resolutions, sdrs, truth_files),
    }

    # Step 10: Single write
    write_result = state_writer.write_state(state, output_dir=output_dir)

    # Step 11: Summary
    return {
        "phase":                _PHASE,
        "phase_status":         phase_status,
        "market_date":          market_date,
        "signals_count":        len(sdrs),
        "outcomes":             outcomes,
        "open_positions_count": len(open_positions),
        "alerts_count":         len(alerts),
        "errors_logged":        len(error_handler.get_error_log()),
        "state_file_written":   write_result["state_file"],
        "duration_ms":          int((time.monotonic() - start_time) * 1000),
    }


# =====================================================================
# Resolution selection
# =====================================================================

def _select_resolutions_today(history_data: dict,
                              market_date: str) -> list:
    """Select signal_history records resolved today.

    Criterion: outcome_date == market_date AND outcome != 'OPEN'.
    Empty list if no matches or malformed input.
    """
    if not isinstance(history_data, dict):
        return []
    history = history_data.get("history") or []
    if not isinstance(history, list):
        return []

    out = []
    for record in history:
        if not isinstance(record, dict):
            continue
        if record.get("outcome_date") != market_date:
            continue
        outcome = record.get("outcome")
        if not outcome or outcome == "OPEN":
            continue
        out.append(record)
    return out


# =====================================================================
# Per-resolution processing — safe_run wraps this
# =====================================================================

def _process_one_resolution(signal: dict,
                            market_date: str) -> dict:
    """Build an EOD SDR (plain dict) for a single resolved signal.
    Raises on failure; caller wraps in safe_run."""
    return _build_eod_sdr_dict(signal, market_date)


# =====================================================================
# EOD SDR construction (plain dict — no bucket field)
# =====================================================================

def _build_eod_sdr_dict(signal: dict, market_date: str) -> dict:
    """Construct EOD SDR as a plain dict.

    Differs from L1/L2 SDR (dataclass-backed) in three ways:
      1. No `bucket` / `bucket_reason_*` / `bucket_changed` fields —
         the signal is closed; bucket-assignment metadata is stale.
      2. Adds an `outcome` block with realized P&L, R-multiple,
         outcome type, days_to_outcome, failure_reason, etc.
      3. `evidence` defaults to {} this session (Sessions B/C may
         populate pattern updates / demotion warnings).
    """
    sig_type     = signal.get("signal") or signal.get("signal_type") or "?"
    raw_symbol   = signal.get("symbol") or "?"
    symbol_clean = _strip_ns_suffix(raw_symbol)
    sector       = signal.get("sector") or "?"
    regime       = signal.get("regime") or "?"
    direction    = (
        signal.get("direction") or _infer_direction(sig_type)
    )

    age = signal.get("age")
    if not isinstance(age, (int, float)):
        age = signal.get("age_days") or 0
    age = int(age)

    sdr_id = (
        f"sdr_{market_date}_{_PHASE}_{symbol_clean}_{sig_type}"
    )
    signal_id = signal.get("id") or sdr_id

    return {
        "sdr_id":          sdr_id,
        "signal_id":       signal_id,
        "phase":           _PHASE,
        "phase_timestamp": _now_iso(),
        "market_date":     market_date,
        "symbol":          symbol_clean,
        "signal_type":     sig_type,
        "direction":       direction,
        "sector":          sector,
        "regime":          regime,
        "age_days":        age,
        "signal_date":     signal.get("date"),
        "outcome_date":    signal.get("outcome_date"),
        "is_sa_variant":   bool(signal.get("is_sa", False)),
        "origin":          signal.get("parent_signal_id") or None,
        "outcome":         _build_outcome_block(signal),
        "trade_plan":      _build_eod_trade_plan(signal),
        "evidence":        {},  # Session A leaves empty; Sessions B/C populate
        "audit": {
            "composed_by_version":     f"bridge_v{_BRIDGE_VERSION}",
            "compose_phase_timestamp": _now_iso(),
        },
    }


def _build_outcome_block(signal: dict) -> dict:
    """Extract outcome fields from a resolved signal_history record."""
    return {
        "outcome":         signal.get("outcome"),
        "result":          signal.get("result"),
        "exit_type":       signal.get("exit_type"),
        "outcome_price":   signal.get("outcome_price"),
        "pnl_pct":         signal.get("pnl_pct"),
        "r_multiple":      signal.get("r_multiple"),
        "mae_pct":         signal.get("mae_pct"),
        "mfe_pct":         signal.get("mfe_pct"),
        "days_to_outcome": signal.get("days_to_outcome"),
        "failure_reason":  signal.get("failure_reason"),
    }


def _build_eod_trade_plan(signal: dict) -> dict:
    """Trade plan with realized values: planned entry, actual_open,
    stop, target, exit price. No `rr` (irrelevant post-resolution)."""
    return {
        "scan_price":    signal.get("scan_price"),
        "actual_open":   signal.get("actual_open"),
        "entry":         signal.get("entry"),
        "stop":          signal.get("stop"),
        "target":        signal.get("target_price") or signal.get("target"),
        "outcome_price": signal.get("outcome_price"),
        "atr":           signal.get("atr"),
        "score":         signal.get("score"),
    }


# =====================================================================
# Outcome counters (drive summary + banner)
# =====================================================================

def _count_outcomes(sdrs: list) -> dict:
    """Count resolutions by outcome type."""
    counts = _empty_outcome_counts()
    for sdr in sdrs:
        if not isinstance(sdr, dict):
            continue
        outcome = (sdr.get("outcome") or {}).get("outcome")
        if outcome and outcome in counts:
            counts[outcome] += 1
    return counts


def _empty_outcome_counts() -> dict:
    return {
        "TARGET_HIT": 0,
        "STOP_HIT":   0,
        "DAY6_WIN":   0,
        "DAY6_LOSS":  0,
        "DAY6_FLAT":  0,
    }


def _bucket_outcome_aggregates(outcomes: dict) -> tuple:
    """Roll outcome counts into (won, lost, flat) aggregates."""
    won  = sum(outcomes.get(o, 0) for o in _WIN_OUTCOMES)
    lost = sum(outcomes.get(o, 0) for o in _LOSS_OUTCOMES)
    flat = sum(outcomes.get(o, 0) for o in _FLAT_OUTCOMES)
    return won, lost, flat


# =====================================================================
# EOD summary block
# =====================================================================

def _build_eod_summary(sdrs: list,
                       open_positions: list,
                       outcomes: dict,
                       history_data: dict,
                       mini_rules: dict) -> dict:
    """Summary block surfaced in bridge_state.summary."""
    won, lost, flat = _bucket_outcome_aggregates(outcomes)

    total_pnl = 0.0
    pnl_count = 0
    for sdr in sdrs:
        if not isinstance(sdr, dict):
            continue
        pnl = (sdr.get("outcome") or {}).get("pnl_pct")
        if isinstance(pnl, (int, float)):
            total_pnl += pnl
            pnl_count += 1

    pattern_updates = _build_pattern_updates(history_data, mini_rules)

    return {
        "total_resolutions_today": len(sdrs),
        "outcomes":                outcomes,
        "win_count":               won,
        "loss_count":              lost,
        "flat_count":              flat,
        "total_pnl_pct":           round(total_pnl, 2) if pnl_count else 0.0,
        "open_positions_count":    len(open_positions),
        "pattern_updates":         pattern_updates,
    }


# =====================================================================
# Boost demotion warnings (LE-06) — read-only metadata, no auto-mutation
# =====================================================================

_BOOST_WILDCARD_VALUES = (None, "ANY")


def _build_pattern_updates(history_data: dict, mini_rules: dict) -> list:
    """Iterate active boost_patterns; emit demotion warnings for any
    whose rolling-window WR has fallen below the demotion floor.

    Returns list of pattern_updates entries (per design spec); empty
    list when no pattern crosses threshold or inputs are malformed.
    Read-only: never mutates mini_scanner_rules.json or any state.
    """
    if not isinstance(mini_rules, dict):
        return []
    boost_patterns = mini_rules.get("boost_patterns") or []
    if not isinstance(boost_patterns, list):
        return []

    out = []
    for pattern in boost_patterns:
        if not isinstance(pattern, dict):
            continue
        stats = _compute_boost_rolling_wr(history_data, pattern)
        if stats is None:
            continue
        if stats["window_wr"] >= BOOST_DEMOTION_WR:
            continue
        out.append(_build_demotion_entry(pattern, stats))
    return out


def _compute_boost_rolling_wr(history_data: dict,
                              pattern: dict) -> Optional[dict]:
    """Return rolling-window WR stats for one boost_pattern.

    Filter signal_history records matching pattern (signal exact +
    sector/regime wildcard via None / "ANY"), keep only WIN_OUTCOMES |
    LOSS_OUTCOMES (flats excluded), sort by outcome_date desc, take
    most-recent BOOST_DEMOTION_WINDOW_N. Return None when:
      - pattern.active is False
      - n_in_window < BOOST_DEMOTION_WINDOW_N (insufficient history)
      - history_data malformed
    """
    if pattern.get("active") is False:
        return None

    p_signal = pattern.get("signal")
    p_sector = pattern.get("sector")
    p_regime = pattern.get("regime")
    if not p_signal:
        return None

    if not isinstance(history_data, dict):
        return None
    history = history_data.get("history")
    if not isinstance(history, list):
        return None

    matches = []
    for r in history:
        if not isinstance(r, dict):
            continue
        if r.get("signal") != p_signal:
            continue
        if (p_sector not in _BOOST_WILDCARD_VALUES
                and r.get("sector") != p_sector):
            continue
        if (p_regime not in _BOOST_WILDCARD_VALUES
                and r.get("regime") != p_regime):
            continue
        outcome = r.get("outcome")
        if outcome not in _WIN_OUTCOMES and outcome not in _LOSS_OUTCOMES:
            continue
        if not isinstance(r.get("outcome_date"), str):
            continue
        matches.append(r)

    matches.sort(key=lambda r: r["outcome_date"], reverse=True)
    window = matches[:BOOST_DEMOTION_WINDOW_N]
    if len(window) < BOOST_DEMOTION_WINDOW_N:
        return None

    wins = sum(1 for r in window if r["outcome"] in _WIN_OUTCOMES)
    losses = sum(1 for r in window if r["outcome"] in _LOSS_OUTCOMES)
    denom = wins + losses
    if denom == 0:
        return None

    dates = [r["outcome_date"] for r in window]
    return {
        "window_size":        BOOST_DEMOTION_WINDOW_N,
        "window_wr":          wins / denom,
        "window_wins":        wins,
        "window_losses":      losses,
        "window_oldest_date": min(dates),
        "window_newest_date": max(dates),
    }


def _build_demotion_entry(pattern: dict, stats: dict) -> dict:
    """Build a single pattern_updates entry per the Session C schema.

    13 fields: kind, pattern_id, signal, sector, regime, current_tier,
    window_size, window_wr, window_wins, window_losses,
    window_oldest_date, window_newest_date, threshold_wr, message.
    """
    sector = pattern.get("sector")
    regime = pattern.get("regime")
    sector_label = "any" if sector in _BOOST_WILDCARD_VALUES else sector
    regime_label = "any" if regime in _BOOST_WILDCARD_VALUES else regime
    pid = pattern.get("id") or "?"
    sig = pattern.get("signal") or "?"
    wr_pct = int(round(stats["window_wr"] * 100))
    message = (
        f"⚠ {pid}: {sig} × {sector_label} × {regime_label}, "
        f"last-{stats['window_size']} WR {wr_pct}% "
        f"({stats['window_wins']}/{stats['window_size']}) — "
        f"below {int(round(BOOST_DEMOTION_WR * 100))}% floor"
    )
    return {
        "kind":               "boost_demotion_warning",
        "pattern_id":         pid,
        "signal":             sig,
        "sector":             sector,
        "regime":             regime,
        "current_tier":       pattern.get("tier"),
        "window_size":        stats["window_size"],
        "window_wr":          stats["window_wr"],
        "window_wins":        stats["window_wins"],
        "window_losses":      stats["window_losses"],
        "window_oldest_date": stats["window_oldest_date"],
        "window_newest_date": stats["window_newest_date"],
        "threshold_wr":       BOOST_DEMOTION_WR,
        "message":            message,
    }


# =====================================================================
# EOD banner
# =====================================================================

def _build_eod_banner(phase_status: str,
                      n_resolved: int,
                      outcomes: dict) -> dict:
    """EOD-specific banner.

    Edge cases:
      n_resolved == 0  → "EOD — no resolutions today"
      otherwise        → "EOD — N resolved (W won, L stopped, F flat)"
                         where W/L/F is the win/loss/flat triplet.

    DEGRADED prepends "(partial data)"; ERROR replaces with degraded
    message.
    """
    color = _BANNER_COLOR.get(phase_status, "neutral")

    if n_resolved == 0:
        core_text = "no resolutions today"
    else:
        won, lost, flat = _bucket_outcome_aggregates(outcomes)
        parts = [f"{n_resolved} resolved"]
        triplet = []
        if won:
            triplet.append(f"{won} won")
        if lost:
            triplet.append(f"{lost} stopped")
        if flat:
            triplet.append(f"{flat} flat")
        if triplet:
            parts.append(f"({', '.join(triplet)})")
        core_text = " ".join(parts)

    if phase_status == "DEGRADED":
        message = "EOD — partial data"
        subtext = core_text
    elif phase_status == "ERROR":
        message = "Bridge degraded"
        subtext = "Check Actions logs for details"
    else:
        message = f"EOD — {core_text}"
        subtext = "Computed after eod_master finalized outcomes"

    return {
        "state":   phase_status,
        "color":   color,
        "message": message,
        "subtext": subtext,
    }
