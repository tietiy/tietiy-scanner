#!/usr/bin/env python3
"""
TIE TIY Health Check System v1.0
================================
Single-file data integrity validation for the TIE TIY trading scanner.

Runs after every scan to detect:
- Schema violations
- Data corruption
- Cross-file inconsistencies
- UI contract violations

Usage:
    python health_check.py                # Full check
    python health_check.py --quick        # Critical checks only
    python health_check.py --json         # JSON output only
    python health_check.py --quarantine   # Enable backup on critical

Exit codes:
    0 = PASS
    1 = WARNING
    2 = FAIL (critical issues)

Author: TIE TIY System
Version: 1.0.0
"""

import json
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import argparse

# =============================================================================
# CONFIGURATION
# =============================================================================

# AI Debug Hook (prepared but disabled)
AI_DEBUG_ENABLED = False
AI_API_KEY = os.environ.get("AICREDITS_API_KEY", "")

# Valid enums
VALID_SIGNAL_TYPES = ["UP_TRI", "DOWN_TRI", "BULL_PROXY"]
VALID_LIFECYCLES = ["ACTIVE", "RESOLVED"]
VALID_REGIMES = ["bull", "bear", "choppy"]
VALID_OUTCOMES = ["TARGET_HIT", "STOP_HIT", "DAY6_WIN", "DAY6_LOSS", "DAY6_FLAT"]
VALID_ACTIONS = ["TOOK", "SKIP"]

# Business rules
RULES = {
    "schema_version": 4,
    "max_target_pct": 15.0,
    "max_stop_pct": 8.0,
    "min_rr_ratio": 1.0,
    "max_score": 10,
    "max_signal_age_days": 10,  # Buffer for weekends
}

# Required fields for each record type
REQUIRED_SIGNAL_FIELDS = [
    "signal_id", "symbol", "signal_type", "signal_date",
    "entry", "stop", "target", "score", "lifecycle", "gen"
]

UI_COMPACT_FIELDS = ["symbol", "signal_type", "entry", "score", "lifecycle"]
UI_EXPANDED_FIELDS = ["symbol", "signal_type", "entry", "stop", "target", "signal_date", "score"]

# =============================================================================
# DATA CLASSES
# =============================================================================

class Severity(Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"

class Status(Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"

@dataclass
class Issue:
    code: str
    severity: Severity
    message: str
    file: Optional[str] = None
    field: Optional[str] = None
    value: Optional[Any] = None
    fix_hint: Optional[str] = None

@dataclass
class HealthReport:
    timestamp: str
    status: Status
    issues: List[Issue] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    quarantine_triggered: bool = False
    backup_path: Optional[str] = None

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

class Paths:
    def __init__(self, base: str = None):
        if base:
            self.base = Path(base)
        else:
            # Auto-detect: check for scanner/ or output/ directory
            for candidate in [Path.cwd(), Path(__file__).parent.parent]:
                if (candidate / "scanner").exists() or (candidate / "output").exists():
                    self.base = candidate
                    break
            else:
                self.base = Path.cwd()
        
        self.output = self.base / "output"
        self.data = self.base / "data"
        self.quarantine = self.base / "quarantine"
        
        # Key files
        self.signal_history = self.output / "signal_history.json"
        self.signal_archive = self.output / "signal_archive.json"
        self.scan_log = self.output / "scan_log.json"
        self.mini_log = self.output / "mini_log.json"
        self.health_report = self.output / "health_report.json"
        self.fno_universe = self.data / "fno_universe.csv"

# =============================================================================
# HEALTH CHECK ENGINE
# =============================================================================

class HealthCheck:
    def __init__(self, base_path: str = None, enable_quarantine: bool = False):
        self.paths = Paths(base_path)
        self.enable_quarantine = enable_quarantine
        self.issues: List[Issue] = []
        self.checks_run = 0
        self.checks_passed = 0
        
        # Loaded data
        self.history_data: Optional[dict] = None
        self.archive_data: Optional[dict] = None
        self.scan_data: Optional[dict] = None
        self.mini_data: Optional[dict] = None
    
    # -------------------------------------------------------------------------
    # A. FILE EXISTENCE CHECKS
    # -------------------------------------------------------------------------
    
    def check_file_existence(self) -> None:
        """F1-F4: Verify required output files exist."""
        files = [
            ("F1", self.paths.scan_log, "scan_log.json", Severity.MAJOR),
            ("F2", self.paths.signal_history, "signal_history.json", Severity.CRITICAL),
            ("F3", self.paths.mini_log, "mini_log.json", Severity.MINOR),
            ("F4", self.paths.signal_archive, "signal_archive.json", Severity.MINOR),
        ]
        
        for code, path, name, severity in files:
            self.checks_run += 1
            if not path.exists():
                self.issues.append(Issue(
                    code=code,
                    severity=severity,
                    message=f"Required file missing: {name}",
                    file=name,
                    fix_hint=f"Ensure scanner creates {name}"
                ))
            else:
                self.checks_passed += 1
    
    # -------------------------------------------------------------------------
    # B. SCHEMA VALIDATION
    # -------------------------------------------------------------------------
    
    def check_schema(self) -> None:
        """S1-S6: Validate JSON structure and required fields."""
        
        # S1: signal_history.json parseable
        self.checks_run += 1
        if self.paths.signal_history.exists():
            try:
                with open(self.paths.signal_history) as f:
                    self.history_data = json.load(f)
                self.checks_passed += 1
            except json.JSONDecodeError as e:
                self.issues.append(Issue(
                    code="S1",
                    severity=Severity.CRITICAL,
                    message=f"signal_history.json parse error: {e}",
                    file="signal_history.json"
                ))
                return  # Can't continue without valid history
        
        if not self.history_data:
            return
        
        # S2: schema_version present and correct
        self.checks_run += 1
        sv = self.history_data.get("schema_version")
        if sv is None:
            self.issues.append(Issue(
                code="S2",
                severity=Severity.CRITICAL,
                message="schema_version field missing",
                file="signal_history.json",
                fix_hint=f"Add schema_version: {RULES['schema_version']}"
            ))
        elif sv != RULES["schema_version"]:
            self.issues.append(Issue(
                code="S2",
                severity=Severity.MAJOR,
                message=f"schema_version mismatch: got {sv}, expected {RULES['schema_version']}",
                file="signal_history.json"
            ))
        else:
            self.checks_passed += 1
        
        # S3: signals array exists
        self.checks_run += 1
        if "signals" not in self.history_data:
            self.issues.append(Issue(
                code="S3",
                severity=Severity.CRITICAL,
                message="signals array missing from signal_history.json",
                file="signal_history.json"
            ))
        elif not isinstance(self.history_data["signals"], list):
            self.issues.append(Issue(
                code="S3",
                severity=Severity.CRITICAL,
                message="signals must be an array",
                file="signal_history.json"
            ))
        else:
            self.checks_passed += 1
        
        # S4: scan_log.json parseable and has required fields
        self.checks_run += 1
        if self.paths.scan_log.exists():
            try:
                with open(self.paths.scan_log) as f:
                    self.scan_data = json.load(f)
                
                required = ["scan_date", "scan_time", "market_info", "signals"]
                missing = [f for f in required if f not in self.scan_data]
                if missing:
                    self.issues.append(Issue(
                        code="S4",
                        severity=Severity.MAJOR,
                        message=f"scan_log.json missing fields: {missing}",
                        file="scan_log.json"
                    ))
                else:
                    self.checks_passed += 1
            except json.JSONDecodeError as e:
                self.issues.append(Issue(
                    code="S4",
                    severity=Severity.MAJOR,
                    message=f"scan_log.json parse error: {e}",
                    file="scan_log.json"
                ))
        
        # S5: mini_log.json parseable
        self.checks_run += 1
        if self.paths.mini_log.exists():
            try:
                with open(self.paths.mini_log) as f:
                    self.mini_data = json.load(f)
                self.checks_passed += 1
            except json.JSONDecodeError as e:
                self.issues.append(Issue(
                    code="S5",
                    severity=Severity.MINOR,
                    message=f"mini_log.json parse error: {e}",
                    file="mini_log.json"
                ))
        else:
            self.checks_passed += 1  # Optional file
        
        # S6: signal_archive.json parseable
        self.checks_run += 1
        if self.paths.signal_archive.exists():
            try:
                with open(self.paths.signal_archive) as f:
                    self.archive_data = json.load(f)
                self.checks_passed += 1
            except json.JSONDecodeError as e:
                self.issues.append(Issue(
                    code="S6",
                    severity=Severity.MINOR,
                    message=f"signal_archive.json parse error: {e}",
                    file="signal_archive.json"
                ))
        else:
            self.checks_passed += 1  # Optional file
    
    # -------------------------------------------------------------------------
    # C. DATA SANITY CHECKS
    # -------------------------------------------------------------------------
    
    def check_data_sanity(self) -> None:
        """D1-D10: Validate data values and consistency."""
        if not self.history_data:
            return
        
        signals = self.history_data.get("signals", [])
        signal_ids = []
        
        for i, sig in enumerate(signals):
            sid = sig.get("signal_id", f"index_{i}")
            signal_ids.append(sid)
            
            # D1: Required fields present
            self.checks_run += 1
            missing = [f for f in REQUIRED_SIGNAL_FIELDS if sig.get(f) is None]
            if missing:
                self.issues.append(Issue(
                    code="D1",
                    severity=Severity.CRITICAL,
                    message=f"Signal {sid}: missing required fields: {missing}",
                    file="signal_history.json"
                ))
            else:
                self.checks_passed += 1
            
            # D2: Prices are numeric and > 0
            self.checks_run += 1
            price_ok = True
            for pf in ["entry", "stop", "target"]:
                val = sig.get(pf)
                if val is not None:
                    if not isinstance(val, (int, float)):
                        self.issues.append(Issue(
                            code="D2",
                            severity=Severity.CRITICAL,
                            message=f"Signal {sid}: {pf} is not numeric (got {type(val).__name__})",
                            file="signal_history.json",
                            field=pf,
                            value=val
                        ))
                        price_ok = False
                    elif val <= 0:
                        self.issues.append(Issue(
                            code="D2",
                            severity=Severity.CRITICAL,
                            message=f"Signal {sid}: {pf} is zero or negative: {val}",
                            file="signal_history.json",
                            field=pf,
                            value=val
                        ))
                        price_ok = False
            if price_ok:
                self.checks_passed += 1
            
            # D3: vol_confirm is boolean
            self.checks_run += 1
            vc = sig.get("vol_confirm")
            if vc is not None and not isinstance(vc, bool):
                self.issues.append(Issue(
                    code="D3",
                    severity=Severity.CRITICAL,
                    message=f"Signal {sid}: vol_confirm must be boolean, got {type(vc).__name__}",
                    file="signal_history.json",
                    field="vol_confirm",
                    value=vc,
                    fix_hint="Change 'true'/'false' string to true/false boolean"
                ))
            else:
                self.checks_passed += 1
            
            # D4: lifecycle valid enum
            self.checks_run += 1
            lc = sig.get("lifecycle")
            if lc not in VALID_LIFECYCLES:
                self.issues.append(Issue(
                    code="D4",
                    severity=Severity.MAJOR,
                    message=f"Signal {sid}: invalid lifecycle '{lc}'",
                    file="signal_history.json",
                    field="lifecycle",
                    value=lc
                ))
            else:
                self.checks_passed += 1
            
            # D5: signal_type valid enum
            self.checks_run += 1
            st = sig.get("signal_type")
            if st not in VALID_SIGNAL_TYPES:
                self.issues.append(Issue(
                    code="D5",
                    severity=Severity.MAJOR,
                    message=f"Signal {sid}: invalid signal_type '{st}'",
                    file="signal_history.json",
                    field="signal_type",
                    value=st
                ))
            else:
                self.checks_passed += 1
            
            # D6: gen is 0 or 1
            self.checks_run += 1
            gen = sig.get("gen")
            if gen not in [0, 1]:
                self.issues.append(Issue(
                    code="D6",
                    severity=Severity.MAJOR,
                    message=f"Signal {sid}: gen must be 0 or 1, got {gen}",
                    file="signal_history.json",
                    field="gen",
                    value=gen
                ))
            else:
                self.checks_passed += 1
            
            # D7: score in valid range
            self.checks_run += 1
            score = sig.get("score")
            if score is not None:
                if not isinstance(score, int) or score < 0 or score > RULES["max_score"]:
                    self.issues.append(Issue(
                        code="D7",
                        severity=Severity.MINOR,
                        message=f"Signal {sid}: score {score} out of range 0-{RULES['max_score']}",
                        file="signal_history.json",
                        field="score",
                        value=score
                    ))
                else:
                    self.checks_passed += 1
            else:
                self.checks_passed += 1
            
            # D8: outcome valid if RESOLVED
            self.checks_run += 1
            if sig.get("lifecycle") == "RESOLVED":
                outcome = sig.get("outcome")
                if outcome is not None and outcome not in VALID_OUTCOMES:
                    self.issues.append(Issue(
                        code="D8",
                        severity=Severity.MAJOR,
                        message=f"Signal {sid}: invalid outcome '{outcome}'",
                        file="signal_history.json",
                        field="outcome",
                        value=outcome
                    ))
                else:
                    self.checks_passed += 1
            else:
                self.checks_passed += 1
        
        # D9: No duplicate signal_id
        self.checks_run += 1
        seen = set()
        duplicates = []
        for sid in signal_ids:
            if sid in seen:
                duplicates.append(sid)
            seen.add(sid)
        
        if duplicates:
            self.issues.append(Issue(
                code="D9",
                severity=Severity.CRITICAL,
                message=f"Duplicate signal_id found: {duplicates[:5]}",
                file="signal_history.json",
                fix_hint="Remove duplicate signals"
            ))
        else:
            self.checks_passed += 1
        
        # D10: No ACTIVE with action=SKIP (should be removed)
        self.checks_run += 1
        bad_skips = [
            s.get("signal_id") for s in signals
            if s.get("lifecycle") == "ACTIVE" and s.get("action") == "SKIP"
        ]
        if bad_skips:
            self.issues.append(Issue(
                code="D10",
                severity=Severity.MAJOR,
                message=f"ACTIVE signals with action=SKIP: {bad_skips[:3]}",
                file="signal_history.json",
                fix_hint="SKIP signals should not remain ACTIVE"
            ))
        else:
            self.checks_passed += 1
    
    # -------------------------------------------------------------------------
    # D. CROSS-FILE CONSISTENCY
    # -------------------------------------------------------------------------
    
    def check_cross_file(self) -> None:
        """X1-X4: Validate consistency across files."""
        if not self.history_data:
            return
        
        signals = self.history_data.get("signals", [])
        active_signals = [s for s in signals if s.get("lifecycle") == "ACTIVE"]
        
        # X1: Active count matches scan_log
        if self.scan_data and "market_info" in self.scan_data:
            self.checks_run += 1
            reported = self.scan_data["market_info"].get("active_signals_count")
            actual = len(active_signals)
            
            if reported is not None and reported != actual:
                self.issues.append(Issue(
                    code="X1",
                    severity=Severity.CRITICAL,
                    message=f"Active count mismatch: scan_log={reported}, actual={actual}",
                    file="scan_log.json",
                    fix_hint="Check active_signals_count calculation"
                ))
            else:
                self.checks_passed += 1
        
        # X2: No stale ACTIVE signals (> max_signal_age_days old)
        self.checks_run += 1
        today = datetime.now().date()
        stale = []
        for s in active_signals:
            sd = s.get("signal_date")
            if sd:
                try:
                    sig_date = datetime.strptime(sd, "%Y-%m-%d").date()
                    age = (today - sig_date).days
                    if age > RULES["max_signal_age_days"]:
                        stale.append((s.get("signal_id"), age))
                except ValueError:
                    pass
        
        if stale:
            self.issues.append(Issue(
                code="X2",
                severity=Severity.MAJOR,
                message=f"Stale ACTIVE signals: {stale[:3]}",
                file="signal_history.json",
                fix_hint="Run outcome_evaluator to resolve old signals"
            ))
        else:
            self.checks_passed += 1
        
        # X3: gen=0 signals should all be RESOLVED
        self.checks_run += 1
        gen0_active = [s.get("signal_id") for s in signals
                       if s.get("gen") == 0 and s.get("lifecycle") == "ACTIVE"]
        if gen0_active:
            self.issues.append(Issue(
                code="X3",
                severity=Severity.MAJOR,
                message=f"gen=0 (backfill) signals still ACTIVE: {gen0_active[:3]}",
                file="signal_history.json",
                fix_hint="Backfill signals should be resolved"
            ))
        else:
            self.checks_passed += 1
        
        # X4: All symbols exist in universe
        if self.paths.fno_universe.exists():
            self.checks_run += 1
            with open(self.paths.fno_universe) as f:
                universe_content = f.read()
            
            invalid = []
            for s in signals:
                sym = s.get("symbol", "")
                sym_base = sym.replace(".NS", "")
                if sym_base not in universe_content and sym not in universe_content:
                    invalid.append(sym)
            
            if invalid:
                self.issues.append(Issue(
                    code="X4",
                    severity=Severity.MAJOR,
                    message=f"Symbols not in universe: {list(set(invalid))[:5]}",
                    file="signal_history.json",
                    fix_hint="Remove signals for delisted symbols"
                ))
            else:
                self.checks_passed += 1
    
    # -------------------------------------------------------------------------
    # E. TRADING LOGIC CHECKS
    # -------------------------------------------------------------------------
    
    def check_trading_logic(self) -> None:
        """T1-T7: Validate trading logic sanity."""
        if not self.history_data:
            return
        
        signals = self.history_data.get("signals", [])
        
        for sig in signals:
            sid = sig.get("signal_id", "unknown")
            st = sig.get("signal_type")
            entry = sig.get("entry")
            stop = sig.get("stop")
            target = sig.get("target")
            
            if not all([entry, stop, target]):
                continue
            if not all(isinstance(x, (int, float)) for x in [entry, stop, target]):
                continue
            
            # T1: UP_TRI/BULL_PROXY: stop < entry
            if st in ["UP_TRI", "BULL_PROXY"]:
                self.checks_run += 1
                if stop >= entry:
                    self.issues.append(Issue(
                        code="T1",
                        severity=Severity.CRITICAL,
                        message=f"Signal {sid}: stop ({stop}) >= entry ({entry}) for {st}",
                        file="signal_history.json",
                        fix_hint="Stop must be below entry for bullish signals"
                    ))
                else:
                    self.checks_passed += 1
            
            # T2: DOWN_TRI: stop > entry
            if st == "DOWN_TRI":
                self.checks_run += 1
                if stop <= entry:
                    self.issues.append(Issue(
                        code="T2",
                        severity=Severity.CRITICAL,
                        message=f"Signal {sid}: stop ({stop}) <= entry ({entry}) for DOWN_TRI",
                        file="signal_history.json",
                        fix_hint="Stop must be above entry for bearish signals"
                    ))
                else:
                    self.checks_passed += 1
            
            # T3: UP_TRI/BULL_PROXY: target > entry
            if st in ["UP_TRI", "BULL_PROXY"]:
                self.checks_run += 1
                if target <= entry:
                    self.issues.append(Issue(
                        code="T3",
                        severity=Severity.CRITICAL,
                        message=f"Signal {sid}: target ({target}) <= entry ({entry}) for {st}",
                        file="signal_history.json"
                    ))
                else:
                    self.checks_passed += 1
            
            # T4: DOWN_TRI: target < entry
            if st == "DOWN_TRI":
                self.checks_run += 1
                if target >= entry:
                    self.issues.append(Issue(
                        code="T4",
                        severity=Severity.CRITICAL,
                        message=f"Signal {sid}: target ({target}) >= entry ({entry}) for DOWN_TRI",
                        file="signal_history.json"
                    ))
                else:
                    self.checks_passed += 1
            
            # T5: Target % reasonable
            self.checks_run += 1
            target_pct = abs(target - entry) / entry * 100
            if target_pct > RULES["max_target_pct"]:
                self.issues.append(Issue(
                    code="T5",
                    severity=Severity.MAJOR,
                    message=f"Signal {sid}: target_pct {target_pct:.1f}% > {RULES['max_target_pct']}%",
                    file="signal_history.json"
                ))
            else:
                self.checks_passed += 1
            
            # T6: Stop % reasonable
            self.checks_run += 1
            stop_pct = abs(entry - stop) / entry * 100
            if stop_pct > RULES["max_stop_pct"]:
                self.issues.append(Issue(
                    code="T6",
                    severity=Severity.MAJOR,
                    message=f"Signal {sid}: stop_pct {stop_pct:.1f}% > {RULES['max_stop_pct']}%",
                    file="signal_history.json"
                ))
            else:
                self.checks_passed += 1
            
            # T7: R:R >= minimum
            self.checks_run += 1
            if stop_pct > 0:
                rr = target_pct / stop_pct
                if rr < RULES["min_rr_ratio"]:
                    self.issues.append(Issue(
                        code="T7",
                        severity=Severity.MAJOR,
                        message=f"Signal {sid}: R:R {rr:.2f} < {RULES['min_rr_ratio']}",
                        file="signal_history.json"
                    ))
                else:
                    self.checks_passed += 1
            else:
                self.checks_passed += 1
    
    # -------------------------------------------------------------------------
    # F. UI CONTRACT CHECKS
    # -------------------------------------------------------------------------
    
    def check_ui_contract(self) -> None:
        """U1-U4: Validate frontend-required fields."""
        if not self.history_data:
            return
        
        signals = self.history_data.get("signals", [])
        
        for sig in signals:
            sid = sig.get("signal_id", "unknown")
            
            # U1: Compact card fields
            self.checks_run += 1
            missing = [f for f in UI_COMPACT_FIELDS if sig.get(f) is None]
            if missing:
                self.issues.append(Issue(
                    code="U1",
                    severity=Severity.MAJOR,
                    message=f"Signal {sid}: missing compact card fields: {missing}",
                    file="signal_history.json"
                ))
            else:
                self.checks_passed += 1
            
            # U2: Expanded card fields
            self.checks_run += 1
            missing = [f for f in UI_EXPANDED_FIELDS if sig.get(f) is None]
            if missing:
                self.issues.append(Issue(
                    code="U2",
                    severity=Severity.MAJOR,
                    message=f"Signal {sid}: missing expanded card fields: {missing}",
                    file="signal_history.json"
                ))
            else:
                self.checks_passed += 1
            
            # U3: No NaN/undefined in display fields
            self.checks_run += 1
            numeric_fields = ["entry", "stop", "target", "score", "ltp"]
            bad_vals = []
            for nf in numeric_fields:
                val = sig.get(nf)
                if val is not None:
                    val_str = str(val).lower()
                    if val_str in ["nan", "none", "undefined", "null", "infinity", "-infinity"]:
                        bad_vals.append(nf)
            
            if bad_vals:
                self.issues.append(Issue(
                    code="U3",
                    severity=Severity.MINOR,
                    message=f"Signal {sid}: invalid display values in: {bad_vals}",
                    file="signal_history.json"
                ))
            else:
                self.checks_passed += 1
    
    # -------------------------------------------------------------------------
    # G. FAIL-SAFE / QUARANTINE
    # -------------------------------------------------------------------------
    
    def create_backup(self) -> Optional[str]:
        """Create backup of critical files before any modification."""
        if not self.enable_quarantine:
            return None
        
        self.paths.quarantine.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_dir = self.paths.quarantine / f"backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        files_backed_up = []
        for src in [self.paths.signal_history, self.paths.scan_log]:
            if src.exists():
                dst = backup_dir / src.name
                shutil.copy(src, dst)
                files_backed_up.append(src.name)
        
        return str(backup_dir) if files_backed_up else None
    
    # -------------------------------------------------------------------------
    # H. AI DEBUG HOOK (prepared but disabled)
    # -------------------------------------------------------------------------
    
    def ai_explain_issues(self, report: HealthReport) -> Optional[str]:
        """
        AI Debug Hook — sends report to AI for explanation.
        DISABLED by default. Set AI_DEBUG_ENABLED=True to enable.
        """
        if not AI_DEBUG_ENABLED:
            return None
        
        if not AI_API_KEY:
            print("⚠️ AI not configured: AICREDITS_API_KEY not set")
            return None
        
        # Placeholder for AI integration
        # When enabled, this would:
        # 1. Format the report as a prompt
        # 2. Send to AI API
        # 3. Return plain-language explanation
        
        print("ℹ️ AI debug hook called (implementation pending)")
        return None
    
    # -------------------------------------------------------------------------
    # ORCHESTRATION
    # -------------------------------------------------------------------------
    
    def run(self, quick: bool = False) -> HealthReport:
        """Run all health checks and generate report."""
        timestamp = datetime.now().isoformat()
        
        # Create backup if quarantine enabled
        backup_path = None
        if self.enable_quarantine:
            backup_path = self.create_backup()
        
        # Run checks in order
        self.check_file_existence()
        self.check_schema()
        
        if not quick:
            self.check_data_sanity()
            self.check_cross_file()
            self.check_trading_logic()
            self.check_ui_contract()
        
        # Count by severity
        critical = len([i for i in self.issues if i.severity == Severity.CRITICAL])
        major = len([i for i in self.issues if i.severity == Severity.MAJOR])
        minor = len([i for i in self.issues if i.severity == Severity.MINOR])
        
        # Determine status
        if critical > 0:
            status = Status.FAIL
        elif major > 0:
            status = Status.WARNING
        else:
            status = Status.PASS
        
        report = HealthReport(
            timestamp=timestamp,
            status=status,
            issues=self.issues,
            checks_run=self.checks_run,
            checks_passed=self.checks_passed,
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            quarantine_triggered=self.enable_quarantine and critical > 0,
            backup_path=backup_path
        )
        
        # AI explanation (if enabled)
        if AI_DEBUG_ENABLED and self.issues:
            self.ai_explain_issues(report)
        
        return report
    
    def save_report(self, report: HealthReport) -> None:
        """Save report to health_report.json."""
        self.paths.output.mkdir(parents=True, exist_ok=True)
        
        report_dict = {
            "timestamp": report.timestamp,
            "status": report.status.value,
            "summary": {
                "checks_run": report.checks_run,
                "checks_passed": report.checks_passed,
                "critical": report.critical_count,
                "major": report.major_count,
                "minor": report.minor_count
            },
            "quarantine": {
                "triggered": report.quarantine_triggered,
                "backup_path": report.backup_path
            },
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity.value,
                    "message": i.message,
                    "file": i.file,
                    "field": i.field,
                    "fix_hint": i.fix_hint
                }
                for i in report.issues
            ]
        }
        
        with open(self.paths.health_report, "w") as f:
            json.dump(report_dict, f, indent=2)

# =============================================================================
# OUTPUT FORMATTERS
# =============================================================================

def format_console(report: HealthReport) -> str:
    """Format report for console output."""
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append("TIE TIY HEALTH CHECK")
    lines.append("=" * 60)
    lines.append(f"Status: {report.status.value}")
    lines.append(f"Checks: {report.checks_passed}/{report.checks_run} passed")
    lines.append(f"Critical: {report.critical_count} | Major: {report.major_count} | Minor: {report.minor_count}")
    
    if report.quarantine_triggered:
        lines.append(f"\n⚠️ QUARANTINE TRIGGERED")
        lines.append(f"   Backup: {report.backup_path}")
    
    if report.issues:
        lines.append("\nISSUES:")
        lines.append("-" * 40)
        for issue in report.issues:
            lines.append(f"[{issue.severity.value}] {issue.code}: {issue.message}")
            if issue.fix_hint:
                lines.append(f"         → {issue.fix_hint}")
    else:
        lines.append("\n✅ No issues found")
    
    lines.append("=" * 60)
    return "\n".join(lines)

def format_telegram(report: HealthReport) -> str:
    """Format report for Telegram."""
    emoji = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}
    
    lines = [f"{emoji[report.status.value]} *Health Check: {report.status.value}*"]
    lines.append(f"Checks: {report.checks_passed}/{report.checks_run}")
    lines.append(f"Critical: {report.critical_count} | Major: {report.major_count}")
    
    if report.quarantine_triggered:
        lines.append("🔒 Quarantine active")
    
    if report.issues:
        lines.append("\nTop issues:")
        for issue in report.issues[:5]:
            lines.append(f"• {issue.code}: {issue.message[:50]}")
    
    return "\n".join(lines)

# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="TIE TIY Health Check v1.0")
    parser.add_argument("--quick", action="store_true", help="Quick mode (critical checks only)")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--telegram", action="store_true", help="Telegram format")
    parser.add_argument("--quarantine", action="store_true", help="Enable backup on critical")
    parser.add_argument("--path", type=str, help="Base project path")
    
    args = parser.parse_args()
    
    # Run checks
    checker = HealthCheck(
        base_path=args.path,
        enable_quarantine=args.quarantine
    )
    report = checker.run(quick=args.quick)
    
    # Save report
    checker.save_report(report)
    
    # Output
    if args.json:
        with open(checker.paths.health_report) as f:
            print(f.read())
    elif args.telegram:
        print(format_telegram(report))
    else:
        print(format_console(report))
    
    # Exit code
    if report.status == Status.FAIL:
        sys.exit(2)
    elif report.status == Status.WARNING:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
