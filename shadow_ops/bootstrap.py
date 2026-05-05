"""shadow_ops/bootstrap.py — Step 11 of shadow_ops v1.

Initialize a fresh shadow campaign. Operator runs this once at the start of
a campaign; never again for that run_dir.

Creates run_dir if absent, writes run_config.json freezing the campaign's
configuration (rules SHA, git SHA, audit-faithful constants), then emits a
BOOTSTRAP_COMPLETE INFO alert.

run_config.json is the AUDIT TRAIL for "what configuration was the audit's
calibration validated against". Never modified after bootstrap. pre_scan_check
verifies it stays consistent with current state on every subsequent scan.

Refuses to bootstrap if any of:
  1. run_dir contains run_config.json (existing campaign — never overwrite)
  2. run_dir contains any JSONL events (would mix campaigns)
  3. Git working tree dirty in shadow_ops/
  4. Rules JSON missing or unreadable
  5. Required rule_id missing from rules JSON
  6. Required rule has active=false

CLI exit codes: 0 success, 2 refused (validation fail), 3 internal error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from shadow_ops.alerts import emit_alert
from shadow_ops.daily_scan import ACTIVE_RULE_IDS, DEFAULT_RULES_PATH
from shadow_ops.lifecycle import (
    FLAT_THRESHOLD_PCT,
    HOLDING_DAYS,
    TARGET_R_MULTIPLE,
)


_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent

RUN_CONFIG_FILENAME = "run_config.json"
RUN_CONFIG_SCHEMA_VERSION = "v1"
ENTRY_LOGIC_LABEL = "audit_faithful_t1_open_unconditional"


# ============================================================
# Errors
# ============================================================

class BootstrapError(Exception):
    pass


# ============================================================
# Result dataclass
# ============================================================

@dataclass
class BootstrapResult:
    run_dir: str
    run_config_path: str
    campaign_id: str
    campaign_start_date: str
    git_commit_sha: str
    git_branch: str
    rules_sha256_at_bootstrap: str
    bootstrap_at_utc: str
    status: str = "OK"


# ============================================================
# Validation helpers
# ============================================================

def _git_status_clean() -> Tuple[bool, str]:
    """True if shadow_ops/ working tree has no uncommitted changes."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "shadow_ops/"],
            cwd=str(_REPO_ROOT),
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"git status failed: {e}"
    if out.returncode != 0:
        return False, f"git status returned {out.returncode}: {out.stderr}"
    dirty = out.stdout.strip()
    if dirty:
        return False, f"shadow_ops/ has uncommitted changes:\n{dirty}"
    return True, ""


def _git_head_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(_REPO_ROOT),
        capture_output=True, text=True, timeout=10, check=True,
    )
    return out.stdout.strip()


def _git_current_branch() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(_REPO_ROOT),
        capture_output=True, text=True, timeout=10, check=True,
    )
    return out.stdout.strip()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _has_journal_events(run_dir: Path) -> bool:
    """True if run_dir contains any JSONL files (existing campaign)."""
    if not run_dir.exists():
        return False
    for p in run_dir.glob("*.jsonl"):
        if p.exists() and p.stat().st_size > 0:
            return True
    return False


def _validate_rules(rules_path: Path) -> Tuple[bool, str, dict]:
    if not rules_path.exists():
        return False, f"rules JSON missing at {rules_path}", {}
    try:
        payload = json.loads(rules_path.read_text())
    except Exception as e:
        return False, f"rules JSON unreadable: {e}", {}
    rules = {r["id"]: r for r in payload.get("rules", [])}
    missing = [rid for rid in ACTIVE_RULE_IDS if rid not in rules]
    if missing:
        return False, f"missing required rule(s): {missing}", payload
    inactive = [rid for rid in ACTIVE_RULE_IDS if not rules[rid].get("active")]
    if inactive:
        return False, f"required rule(s) marked inactive: {inactive}", payload
    return True, "", payload


# ============================================================
# Public API
# ============================================================

def bootstrap_campaign(run_dir: Path,
                       campaign_id: str,
                       campaign_start_date: date,
                       *,
                       operator: Optional[str] = None,
                       notes: Optional[str] = None,
                       rules_path: Path = DEFAULT_RULES_PATH,
                       allow_dirty_git: bool = False) -> BootstrapResult:
    """Initialize a shadow campaign run_dir.

    Raises BootstrapError on any validation failure (caller catches and
    decides exit code).
    """
    run_dir = Path(run_dir)
    rules_path = Path(rules_path)

    # 1. Refuse if existing campaign
    if (run_dir / RUN_CONFIG_FILENAME).exists():
        raise BootstrapError(
            f"run_config.json already exists at {run_dir / RUN_CONFIG_FILENAME}; "
            f"refuse to overwrite. Remove it manually if re-bootstrap is intended.")
    if _has_journal_events(run_dir):
        raise BootstrapError(
            f"run_dir {run_dir} already contains JSONL events; refuse to "
            f"bootstrap on top of an existing campaign.")

    # 2. Git tree clean
    if not allow_dirty_git:
        ok, msg = _git_status_clean()
        if not ok:
            raise BootstrapError(f"git tree not clean: {msg}")

    # 3. Rules JSON
    rules_ok, rules_msg, _ = _validate_rules(rules_path)
    if not rules_ok:
        raise BootstrapError(f"rules JSON invalid: {rules_msg}")

    # 4. Compute git + rules SHAs
    git_sha = _git_head_sha()
    git_branch = _git_current_branch()
    rules_sha = _file_sha256(rules_path)

    # 5. Build run_config payload
    bootstrap_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rel_rules_path = (
        str(rules_path.resolve().relative_to(_REPO_ROOT))
        if rules_path.resolve().is_relative_to(_REPO_ROOT) else str(rules_path)
    )
    config = {
        "schema_version": RUN_CONFIG_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "campaign_start_date": campaign_start_date.isoformat(),
        "bootstrap_at_utc": bootstrap_at,
        "git_commit_sha": git_sha,
        "git_branch": git_branch,
        "entry_logic": ENTRY_LOGIC_LABEL,
        "holding_days": HOLDING_DAYS,
        "target_r_multiple": TARGET_R_MULTIPLE,
        "flat_threshold_pct": FLAT_THRESHOLD_PCT,
        "slippage_bps_assumption": 0,
        "rules_enabled": list(ACTIVE_RULE_IDS),
        "rules_path_at_bootstrap": rel_rules_path,
        "rules_sha256_at_bootstrap": rules_sha,
        "operator": operator,
        "notes": notes,
        "_audit_faithful_constants_note": (
            "holding_days, target_r_multiple, flat_threshold_pct record the "
            "audit-faithful contract at bootstrap time. They are NOT runtime-"
            "verified. If shadow_ops module constants change between bootstrap "
            "and a daily scan, results diverge silently from this record. "
            "Future schema versions may add runtime verification."
        ),
    }

    # 6. Write atomically (tmp + os.replace)
    run_dir.mkdir(parents=True, exist_ok=True)
    target = run_dir / RUN_CONFIG_FILENAME
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    tmp.replace(target)

    # 7. INFO alert documenting the bootstrap event
    emit_alert(
        run_dir, "INFO", "BOOTSTRAP_COMPLETE",
        module="bootstrap",
        message=(f"campaign {campaign_id!r} bootstrapped for "
                 f"start_date={campaign_start_date.isoformat()}, "
                 f"git={git_sha[:12]}"),
        context={
            "campaign_id": campaign_id,
            "campaign_start_date": campaign_start_date.isoformat(),
            "git_commit_sha": git_sha,
            "git_branch": git_branch,
            "rules_sha256_at_bootstrap": rules_sha,
            "operator": operator,
        },
        logical_date=campaign_start_date.isoformat(),
    )

    return BootstrapResult(
        run_dir=str(run_dir),
        run_config_path=str(target),
        campaign_id=campaign_id,
        campaign_start_date=campaign_start_date.isoformat(),
        git_commit_sha=git_sha,
        git_branch=git_branch,
        rules_sha256_at_bootstrap=rules_sha,
        bootstrap_at_utc=bootstrap_at,
    )


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    ap = argparse.ArgumentParser(
        description="Bootstrap a fresh shadow_ops campaign.")
    ap.add_argument("--run-dir", type=str, required=True,
                    help="path to the new campaign's run directory")
    ap.add_argument("--campaign-id", type=str, required=True,
                    help="operator-chosen identifier for this campaign")
    ap.add_argument("--start-date", type=str, required=True,
                    help="YYYY-MM-DD: first trading day to scan")
    ap.add_argument("--operator", type=str, default=None,
                    help="optional operator identifier")
    ap.add_argument("--notes", type=str, default=None,
                    help="optional free-text notes")
    ap.add_argument("--rules-path", type=str, default=None,
                    help=f"override rules JSON path (default: {DEFAULT_RULES_PATH})")
    ap.add_argument("--allow-dirty-git", action="store_true",
                    help="bypass the git-clean check (NOT recommended)")
    args = ap.parse_args()

    try:
        start_date = date.fromisoformat(args.start_date)
    except ValueError as e:
        print(f"[bootstrap] invalid --start-date: {e}", file=sys.stderr)
        return 2

    rules_path = Path(args.rules_path) if args.rules_path else DEFAULT_RULES_PATH

    try:
        result = bootstrap_campaign(
            run_dir=Path(args.run_dir),
            campaign_id=args.campaign_id,
            campaign_start_date=start_date,
            operator=args.operator,
            notes=args.notes,
            rules_path=rules_path,
            allow_dirty_git=args.allow_dirty_git,
        )
    except BootstrapError as e:
        print(f"[bootstrap] REFUSED: {e}", file=sys.stderr)
        return 2
    except Exception:
        traceback.print_exc()
        return 3

    print(json.dumps(asdict(result), indent=2))
    print()
    print("Bootstrap complete. Next steps for daily operation:")
    print()
    print(f"  python -m shadow_ops.pre_scan_check --run-dir {result.run_dir} && \\")
    print(f"  python -m shadow_ops.daily_scan      --run-dir {result.run_dir} && \\")
    print(f"  python -m shadow_ops.lifecycle       --run-dir {result.run_dir} && \\")
    print(f"  python -m shadow_ops.daily_report    --run-dir {result.run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
