"""
TIE TIY Fix Verifier
====================
Layer 1 — Static checks  (free, instant, always runs)
Layer 2 — AI semantic audit (Claude via AICredits, skipped if no key)

Trigger: GitHub Actions → verify_fixes.yml → workflow_dispatch
Output:  Telegram report + exit code (0=clean, 1=failures)
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT    = Path(os.environ.get("GITHUB_WORKSPACE", "."))
SCANNER_DIR  = REPO_ROOT / "scanner"
DATA_DIR     = REPO_ROOT / "data"

AI_API_KEY   = os.environ.get("AICREDITS_API_KEY", "")
AI_BASE_URL  = "https://api.aicredits.in/v1"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "8493010921")

MODEL_MAP = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-20250514",
}
AI_MODEL_KEY = os.environ.get("AI_MODEL", "haiku").lower()
AI_MODEL     = MODEL_MAP.get(AI_MODEL_KEY, MODEL_MAP["haiku"])

# ─────────────────────────────────────────────────────────────────────────────
# RESULT STORE
# ─────────────────────────────────────────────────────────────────────────────

results = []

ICONS = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⏳"}

def add_result(check_id, layer, status, finding, risk="none"):
    results.append({
        "id":      check_id,
        "layer":   layer,
        "status":  status,
        "finding": finding,
        "risk":    risk,
    })
    icon = ICONS.get(status, "❓")
    print(f"  [{check_id}] {icon} {status} — {finding}")


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1 — STATIC CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def check_D3_tml_removed():
    csv_path = DATA_DIR / "fno_universe.csv"
    if not csv_path.exists():
        add_result("D3", "L1", "FAIL", "fno_universe.csv not found", "high")
        return
    if "TML.NS" in csv_path.read_text():
        add_result("D3", "L1", "FAIL", "TML.NS still present in fno_universe.csv", "high")
    else:
        add_result("D3", "L1", "PASS", "TML.NS not found in universe — clean")


def check_D3_tml_in_workflows():
    wf_dir = REPO_ROOT / ".github" / "workflows"
    if not wf_dir.exists():
        return
    for f in wf_dir.glob("*.yml"):
        if "TML.NS" in f.read_text():
            add_result("D3-WF", "L1", "WARN", f"TML.NS still referenced in {f.name}", "low")
            return
    add_result("D3-WF", "L1", "PASS", "TML.NS not referenced in any workflow YAML")


def check_F3_price_feed_exists():
    if (SCANNER_DIR / "price_feed.py").exists():
        add_result("F3", "L1", "PASS", "price_feed.py exists")
    else:
        add_result("F3", "L1", "FAIL", "price_feed.py missing", "high")


def check_F1_no_rejected_records():
    hist = DATA_DIR / "signal_history.json"
    if not hist.exists():
        add_result("F1", "L1", "WARN", "signal_history.json not found — skipping", "low")
        return
    try:
        data    = json.loads(hist.read_text())
        signals = data if isinstance(data, list) else data.get("signals", [])
        bad     = [s for s in signals if s.get("outcome") == "REJECTED"]
        if bad:
            add_result("F1", "L1", "FAIL", f"{len(bad)} REJECTED outcome records found", "medium")
        else:
            add_result("F1", "L1", "PASS", "Zero REJECTED outcome records — clean")
    except Exception as e:
        add_result("F1", "L1", "WARN", f"Could not parse signal_history.json: {e}", "low")


def check_SCHEMA_gen1_keys():
    REQUIRED = [
        "signal_id", "symbol", "signal_type", "signal_date", "entry_date",
        "entry_price", "target_price", "stop_price", "scan_price",
        "score", "generation", "outcome", "exit_date",
    ]
    hist = DATA_DIR / "signal_history.json"
    if not hist.exists():
        add_result("SCHEMA", "L1", "WARN", "signal_history.json not found — skipping", "low")
        return
    try:
        data    = json.loads(hist.read_text())
        signals = data if isinstance(data, list) else data.get("signals", [])
        gen1    = [s for s in signals if s.get("generation") == 1]
        if not gen1:
            add_result("SCHEMA", "L1", "WARN", "No gen=1 signals found to validate", "low")
            return
        missing = {}
        for s in gen1:
            sid  = s.get("signal_id", "unknown")
            miss = [k for k in REQUIRED if k not in s]
            if miss:
                missing[sid] = miss
        if missing:
            sample = list(missing.items())[:3]
            detail = " | ".join([f"{sid}: {keys}" for sid, keys in sample])
            add_result("SCHEMA", "L1", "FAIL", f"{len(missing)} gen=1 signals missing keys → {detail}", "medium")
        else:
            add_result("SCHEMA", "L1", "PASS", f"All {len(gen1)} gen=1 signals have required keys")
    except Exception as e:
        add_result("SCHEMA", "L1", "WARN", f"Could not parse: {e}", "low")


def check_B1_string_presence():
    for f in SCANNER_DIR.glob("*.py"):
        content = f.read_text()
        if "_assess_exit_due" in content:
            if "== 1" in content or "==1" in content:
                add_result("B1-PRE", "L1", "PASS", f"==1 found near _assess_exit_due in {f.name}")
            else:
                add_result("B1-PRE", "L1", "WARN", f"_assess_exit_due in {f.name} but ==1 not detected", "medium")
            return
    add_result("B1-PRE", "L1", "WARN", "_assess_exit_due not found in scanner files", "medium")


# ─────────────────────────────────────────────────────────────────────────────
# SNIPPET EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def extract_snippet(filename, search_term, lines_after=25):
    fp = SCANNER_DIR / filename
    if not fp.exists():
        return None, f"{filename} not found"
    lines = fp.read_text().splitlines()
    for i, line in enumerate(lines):
        if search_term in line:
            start   = max(0, i - 5)
            end     = min(len(lines), i + lines_after)
            return "\n".join(lines[start:end]), None
    return None, f"'{search_term}' not found in {filename}"


def find_snippet_any(search_term, lines_after=25):
    for f in sorted(SCANNER_DIR.glob("*.py")):
        snippet, _ = extract_snippet(f.name, search_term, lines_after)
        if snippet:
            return snippet, f.name
    return None, None


def get_history_sample(n=20):
    hist = DATA_DIR / "signal_history.json"
    if not hist.exists():
        return None
    try:
        data    = json.loads(hist.read_text())
        signals = data if isinstance(data, list) else data.get("signals", [])
        return [s for s in signals if s.get("generation") == 1][:n]
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2 — AI AUDIT
# ─────────────────────────────────────────────────────────────────────────────

AUDIT_PROMPT = """You are auditing a specific bug fix in a Python stock scanner.

Bug ID: {bug_id}
Description: {description}

Code snippet:
```python
{snippet}
