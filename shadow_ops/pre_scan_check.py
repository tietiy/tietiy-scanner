"""shadow_ops/pre_scan_check.py — Step 9 of shadow_ops v1.

Operational gate that runs BEFORE daily_scan to verify preconditions. If any
check fails, exits non-zero so the operator's daily-script chain halts:

    python -m shadow_ops.pre_scan_check --run-dir <c> && \
    python -m shadow_ops.daily_scan      --run-dir <c> && \
    ...

Per arch §14.10: any unacknowledged CRITICAL alert blocks the next scan.

Checks (7 total):
  1. Git working tree clean (no uncommitted changes in shadow_ops/)
  2. Universe CSV exists, ~188 symbols, correct columns
  3. Rules JSON exists, contains active rule_019/031/kill_001
  4. Lab cache freshness: nifty parquet's latest_date ≥ scan_date − 1 business day
  5. Run-dir consistency: if exists, has expected files; latest scan_date < scan_date
  6. No unacknowledged CRITICAL alerts on or before scan_date
  7. Lifecycle integrity: no orphan lifecycle/fill events (only if events exist)

Block-by-default; --force bypasses (emits PRE_SCAN_CHECK_BYPASSED warning).
--skip-check NAME skips a single named check.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from shadow_ops.alerts import (
    emit_alert,
    unacknowledged_critical,
)
from shadow_ops.data_ingest import DEFAULT_CACHE_DIR, DEFAULT_UNIVERSE_CSV
from shadow_ops.daily_scan import ACTIVE_RULE_IDS, DEFAULT_RULES_PATH
from shadow_ops.journal import JournalReader


_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent

EXPECTED_UNIVERSE_SIZE = 188
CACHE_FRESHNESS_BDAYS = 1


# ============================================================
# Check result
# ============================================================

@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str = ""
    context: Dict[str, object] = field(default_factory=dict)


@dataclass
class PreScanCheckResult:
    scan_date: str
    run_dir: str
    checks: List[CheckResult]
    forced: bool = False
    skipped: List[str] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def failed(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.ok]


# ============================================================
# Individual checks
# ============================================================

def _check_git_clean() -> CheckResult:
    """Working tree must have no uncommitted changes in shadow_ops/."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "shadow_ops/"],
            cwd=str(_REPO_ROOT),
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return CheckResult("git_clean", False,
                            f"git status failed: {e}",
                            {"error_type": type(e).__name__})
    if out.returncode != 0:
        return CheckResult("git_clean", False,
                            f"git status returned {out.returncode}",
                            {"stderr": out.stderr})
    dirty = out.stdout.strip().splitlines()
    if dirty:
        return CheckResult("git_clean", False,
                            f"shadow_ops/ has {len(dirty)} uncommitted changes",
                            {"dirty_files": dirty[:20]})
    return CheckResult("git_clean", True, "shadow_ops/ working tree clean")


def _check_universe_csv(universe_csv: Path) -> CheckResult:
    if not universe_csv.exists():
        return CheckResult("universe_csv", False,
                            f"universe csv missing at {universe_csv}",
                            {"path": str(universe_csv)})
    try:
        df = pd.read_csv(universe_csv)
    except Exception as e:
        return CheckResult("universe_csv", False,
                            f"universe csv unreadable: {e}",
                            {"path": str(universe_csv)})
    if not {"symbol", "sector"}.issubset(df.columns):
        return CheckResult("universe_csv", False,
                            "universe csv missing required columns",
                            {"columns": list(df.columns)})
    n = len(df)
    if n != EXPECTED_UNIVERSE_SIZE:
        return CheckResult("universe_csv", False,
                            f"universe size {n} != expected {EXPECTED_UNIVERSE_SIZE}",
                            {"actual_size": n, "expected": EXPECTED_UNIVERSE_SIZE})
    return CheckResult("universe_csv", True,
                        f"universe loaded ({n} symbols)",
                        {"size": n})


def _check_rules_json(rules_path: Path) -> CheckResult:
    if not rules_path.exists():
        return CheckResult("rules_json", False,
                            f"rules json missing at {rules_path}",
                            {"path": str(rules_path)})
    try:
        payload = json.loads(rules_path.read_text())
    except Exception as e:
        return CheckResult("rules_json", False,
                            f"rules json unreadable: {e}")
    rules = {r["id"]: r for r in payload.get("rules", [])}
    missing = [rid for rid in ACTIVE_RULE_IDS if rid not in rules]
    if missing:
        return CheckResult("rules_json", False,
                            f"missing required rule(s): {missing}",
                            {"missing": missing})
    inactive = [rid for rid in ACTIVE_RULE_IDS
                if not rules[rid].get("active", False)]
    if inactive:
        return CheckResult("rules_json", False,
                            f"required rule(s) marked inactive: {inactive}",
                            {"inactive": inactive})
    return CheckResult("rules_json", True,
                        f"all {len(ACTIVE_RULE_IDS)} active rules present")


def _check_cache_freshness(cache_dir: Path, scan_date: date) -> CheckResult:
    nifty = cache_dir / "_index_NSEI.parquet"
    if not nifty.exists():
        return CheckResult("cache_freshness", False,
                            f"nifty parquet missing at {nifty}",
                            {"path": str(nifty)})
    try:
        df = pd.read_parquet(nifty)
    except Exception as e:
        return CheckResult("cache_freshness", False,
                            f"nifty parquet unreadable: {e}")
    df.index = pd.to_datetime(df.index)
    latest = df.index.max().date()
    threshold = (pd.Timestamp(scan_date)
                 - pd.tseries.offsets.BDay(CACHE_FRESHNESS_BDAYS)).date()
    if latest < threshold:
        return CheckResult("cache_freshness", False,
                            f"nifty parquet stale: latest={latest} < threshold={threshold} "
                            f"(scan_date={scan_date}, threshold = scan_date − {CACHE_FRESHNESS_BDAYS} BDay)",
                            {"latest": latest.isoformat(),
                             "threshold": threshold.isoformat(),
                             "scan_date": scan_date.isoformat()})
    return CheckResult("cache_freshness", True,
                        f"nifty parquet fresh (latest={latest}, scan_date={scan_date})",
                        {"latest": latest.isoformat()})


def _check_run_dir_consistency(run_dir: Path, scan_date: date) -> CheckResult:
    """If run_dir is empty/new: pass (first scan of campaign).
    If has scan events: latest scan_date < scan_date (no re-scan)."""
    if not run_dir.exists():
        return CheckResult("run_dir_consistency", True,
                            "run_dir is new (will be created)")
    scan_jsonl = run_dir / "scan_events.jsonl"
    if not scan_jsonl.exists():
        return CheckResult("run_dir_consistency", True,
                            "run_dir has no scan events yet (new campaign)")
    try:
        scans = JournalReader(run_dir).all_scan_events()
    except Exception as e:
        return CheckResult("run_dir_consistency", False,
                            f"failed to read scan_events.jsonl: {e}")
    if not scans:
        return CheckResult("run_dir_consistency", True,
                            "scan_events.jsonl exists but is empty")
    latest = max(s.scan_date for s in scans)
    if latest >= scan_date.isoformat():
        return CheckResult("run_dir_consistency", False,
                            f"latest scan_date={latest} ≥ requested scan_date={scan_date} "
                            f"(re-scan attempt — would collide on event_id)",
                            {"latest_scan_date": latest,
                             "requested_scan_date": scan_date.isoformat()})
    return CheckResult("run_dir_consistency", True,
                        f"latest scan_date={latest} < requested {scan_date}")


def _check_unacked_critical(run_dir: Path, scan_date: date) -> CheckResult:
    if not run_dir.exists():
        return CheckResult("unacked_critical", True,
                            "run_dir doesn't exist yet — no alerts to check")
    unacked = unacknowledged_critical(run_dir, on_or_before_date=scan_date)
    if unacked:
        return CheckResult("unacked_critical", False,
                            f"{len(unacked)} unacknowledged CRITICAL alert(s)",
                            {"alert_ids": [a.alert_id for a in unacked][:20]})
    return CheckResult("unacked_critical", True,
                        "no unacknowledged CRITICAL alerts")


def _check_lifecycle_integrity(run_dir: Path) -> CheckResult:
    """Check there are no orphan lifecycle/fill events (events whose card_id
    has no matching TradeCard in the journal). Only meaningful when events exist."""
    if not run_dir.exists():
        return CheckResult("lifecycle_integrity", True,
                            "run_dir doesn't exist yet")
    try:
        r = JournalReader(run_dir)
        cards = r.all_trade_cards()
        lcs = r.all_lifecycle_events()
        fills = r.all_fill_simulations()
    except Exception as e:
        return CheckResult("lifecycle_integrity", False,
                            f"failed to read journals: {e}")
    if not cards and not lcs and not fills:
        return CheckResult("lifecycle_integrity", True,
                            "no events yet — nothing to check")
    known = {c.card_id for c in cards}
    orphans = ([("lifecycle_event", lc.event_id, lc.card_id)
                for lc in lcs if lc.card_id not in known]
               + [("fill_simulation", f.event_id, f.card_id)
                  for f in fills if f.card_id not in known])
    if orphans:
        return CheckResult("lifecycle_integrity", False,
                            f"{len(orphans)} orphan event(s) without matching trade_card",
                            {"orphans": orphans[:10]})
    return CheckResult("lifecycle_integrity", True,
                        f"all {len(lcs)} lc + {len(fills)} fill events linked to known cards")


# ============================================================
# Orchestration
# ============================================================

CHECK_NAMES = (
    "git_clean",
    "universe_csv",
    "rules_json",
    "cache_freshness",
    "run_dir_consistency",
    "unacked_critical",
    "lifecycle_integrity",
    "run_config_consistency",
)


RUN_CONFIG_FILENAME = "run_config.json"


def _file_sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_run_config_consistency(run_dir: Path,
                                   rules_path: Path) -> CheckResult:
    """If run_config.json present: verify rules SHA matches bootstrap and
    current git HEAD descends from bootstrap_sha. If absent: pass silently
    (backward compat for pre-Step-11 campaigns)."""
    cfg_path = run_dir / RUN_CONFIG_FILENAME
    if not cfg_path.exists():
        return CheckResult("run_config_consistency", True,
                            "run_config.json absent (pre-Step-11 campaign or new run)")
    try:
        cfg = json.loads(cfg_path.read_text())
    except Exception as e:
        return CheckResult("run_config_consistency", False,
                            f"run_config.json unreadable: {e}",
                            {"path": str(cfg_path)})

    # (a) Rules SHA match
    bootstrap_sha = cfg.get("rules_sha256_at_bootstrap")
    if not bootstrap_sha:
        return CheckResult("run_config_consistency", False,
                            "run_config.json missing rules_sha256_at_bootstrap",
                            {"path": str(cfg_path)})
    if not rules_path.exists():
        return CheckResult("run_config_consistency", False,
                            f"current rules JSON missing at {rules_path}")
    current_sha = _file_sha256(rules_path)
    if current_sha != bootstrap_sha:
        return CheckResult("run_config_consistency", False,
                            (f"rules SHA drift: bootstrap={bootstrap_sha[:16]}..., "
                             f"current={current_sha[:16]}... "
                             f"(rules library changed mid-campaign)"),
                            {"bootstrap_sha": bootstrap_sha,
                             "current_sha": current_sha,
                             "rules_path": str(rules_path)})

    # (b) Git lineage: HEAD descends from bootstrap_sha
    bootstrap_git_sha = cfg.get("git_commit_sha")
    if bootstrap_git_sha:
        try:
            out = subprocess.run(
                ["git", "merge-base", "--is-ancestor", bootstrap_git_sha, "HEAD"],
                cwd=str(_REPO_ROOT),
                capture_output=True, text=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return CheckResult("run_config_consistency", False,
                                f"git merge-base failed: {e}")
        if out.returncode != 0:
            return CheckResult("run_config_consistency", False,
                                (f"git lineage broken: HEAD does not descend from "
                                 f"bootstrap commit {bootstrap_git_sha[:12]} "
                                 f"(checkout drifted to unrelated branch?)"),
                                {"bootstrap_git_sha": bootstrap_git_sha})

    return CheckResult("run_config_consistency", True,
                        f"run_config consistent (rules SHA + git lineage both match)")


def run_pre_scan_checks(run_dir: Path,
                        scan_date: Optional[date] = None,
                        *,
                        cache_dir: Path = DEFAULT_CACHE_DIR,
                        universe_csv: Path = DEFAULT_UNIVERSE_CSV,
                        rules_path: Path = DEFAULT_RULES_PATH,
                        skip: Optional[List[str]] = None
                        ) -> PreScanCheckResult:
    """Run the 7 preconditions. Return a PreScanCheckResult capturing each
    check's outcome. Doesn't raise; doesn't mutate alerts. Caller decides
    what to do with the result (CLI emits an alert, library users may not)."""
    if scan_date is None:
        scan_date = datetime.now(timezone.utc).date()
    skip_set = set(skip or [])

    runners: List[Tuple[str, Callable[[], CheckResult]]] = [
        ("git_clean",                _check_git_clean),
        ("universe_csv",             lambda: _check_universe_csv(universe_csv)),
        ("rules_json",               lambda: _check_rules_json(rules_path)),
        ("cache_freshness",          lambda: _check_cache_freshness(cache_dir, scan_date)),
        ("run_dir_consistency",      lambda: _check_run_dir_consistency(run_dir, scan_date)),
        ("unacked_critical",         lambda: _check_unacked_critical(run_dir, scan_date)),
        ("lifecycle_integrity",      lambda: _check_lifecycle_integrity(run_dir)),
        ("run_config_consistency",   lambda: _check_run_config_consistency(run_dir, rules_path)),
    ]

    results: List[CheckResult] = []
    for name, fn in runners:
        if name in skip_set:
            continue
        try:
            results.append(fn())
        except Exception as e:
            results.append(CheckResult(name, False,
                                        f"check raised: {type(e).__name__}: {e}",
                                        {"error_type": type(e).__name__}))

    return PreScanCheckResult(
        scan_date=scan_date.isoformat(),
        run_dir=str(run_dir),
        checks=results,
        skipped=sorted(skip_set & set(CHECK_NAMES)),
    )


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    ap = argparse.ArgumentParser(description="shadow_ops pre-scan check")
    ap.add_argument("--run-dir", type=str, required=True)
    ap.add_argument("--scan-date", type=str, default=None,
                    help="YYYY-MM-DD; defaults to today UTC")
    ap.add_argument("--force", action="store_true",
                    help="bypass check failures (still emits a WARNING alert)")
    ap.add_argument("--skip-check", action="append", default=[],
                    metavar="NAME",
                    help=f"skip a named check; repeatable. Names: {sorted(CHECK_NAMES)}")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    scan_date = (date.fromisoformat(args.scan_date) if args.scan_date
                 else datetime.now(timezone.utc).date())

    try:
        result = run_pre_scan_checks(
            run_dir, scan_date, skip=args.skip_check)
    except Exception:
        traceback.print_exc()
        return 3

    # Print one line per check
    for c in result.checks:
        status = "OK " if c.ok else "FAIL"
        print(f"[pre_scan_check] {status}  {c.name:<22}  {c.message}")
    if result.skipped:
        print(f"[pre_scan_check] SKIPPED checks: {result.skipped}")

    if result.all_passed:
        return 0

    failed_names = [c.name for c in result.failed]
    fail_msg = (f"pre_scan_check FAILED: {len(failed_names)} check(s) failed: "
                f"{failed_names}")

    if args.force:
        # Emit WARNING that bypass was used
        emit_alert(
            run_dir, "WARNING", "PRE_SCAN_CHECK_BYPASSED",
            module="pre_scan_check",
            message=f"--force bypass: {fail_msg}",
            context={
                "failed_checks": failed_names,
                "failed_messages": [c.message for c in result.failed],
                "scan_date": result.scan_date,
            },
            logical_date=result.scan_date,
        )
        print(f"[pre_scan_check] BYPASSED (--force): proceeding despite failures",
              file=sys.stderr)
        return 0

    # Emit CRITICAL alert documenting the failure
    emit_alert(
        run_dir, "CRITICAL", "PRE_SCAN_CHECK_FAILURE",
        module="pre_scan_check",
        message=fail_msg,
        context={
            "failed_checks": failed_names,
            "failed_messages": [c.message for c in result.failed],
            "failed_contexts": [c.context for c in result.failed],
            "scan_date": result.scan_date,
        },
        logical_date=result.scan_date,
    )
    print(f"[pre_scan_check] {fail_msg}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main_cli())
