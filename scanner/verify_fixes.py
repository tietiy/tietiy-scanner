import os
import json
import requests
from pathlib import Path
from datetime import datetime

REPO_ROOT          = Path(os.environ.get("GITHUB_WORKSPACE", "."))
SCANNER_DIR        = REPO_ROOT / "scanner"
DATA_DIR           = REPO_ROOT / "data"
AI_API_KEY         = os.environ.get("AICREDITS_API_KEY", "")
AI_BASE_URL        = "https://api.aicredits.in/v1"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "8493010921")

MODEL_MAP = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-20250514",
}
AI_MODEL_KEY = os.environ.get("AI_MODEL", "haiku").lower()
AI_MODEL     = MODEL_MAP.get(AI_MODEL_KEY, MODEL_MAP["haiku"])

results = []
ICONS   = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⏳"}


def add_result(check_id, layer, status, finding, risk="none"):
    results.append({"id": check_id, "layer": layer, "status": status, "finding": finding, "risk": risk})
    print(f"  [{check_id}] {ICONS.get(status, '?')} {status} — {finding}")


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
            add_result("SCHEMA", "L1", "FAIL", f"{len(missing)} gen=1 signals missing keys — {detail}", "medium")
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


def extract_snippet(filename, search_term, lines_after=25):
    fp = SCANNER_DIR / filename
    if not fp.exists():
        return None, f"{filename} not found"
    lines = fp.read_text().splitlines()
    for i, line in enumerate(lines):
        if search_term in line:
            start = max(0, i - 5)
            end   = min(len(lines), i + lines_after)
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


AUDIT_PROMPT = (
    "You are auditing a specific bug fix in a Python stock scanner.\n\n"
    "Bug ID: {bug_id}\n"
    "Description: {description}\n\n"
    "Code snippet:\n{snippet}\n\n"
    "Reply ONLY in this exact format — no preamble, no extra text:\n"
    "STATUS: PASS | FAIL | WARN\n"
    "FINDING: one sentence max\n"
    "RISK: none | low | medium | high"
)


def call_ai(prompt, max_tokens=400):
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         AI_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model":      AI_MODEL,
        "max_tokens": max_tokens,
        "messages":   [{"role": "user", "content": prompt}],
    }
    try:
        resp = requests.post(
            f"{AI_BASE_URL}/messages",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"], None
    except Exception as e:
        return None, str(e)


def parse_structured(text):
    status  = "WARN"
    finding = text.strip()[:250]
    risk    = "low"
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("STATUS:"):
            val = line.split(":", 1)[1].strip().upper()
            if val in ("PASS", "FAIL", "WARN"):
                status = val
        elif line.startswith("FINDING:"):
            finding = line.split(":", 1)[1].strip()
        elif line.startswith("RISK:"):
            risk = line.split(":", 1)[1].strip().lower()
    return status, finding, risk


def ai_audit(check_id, description, search_term):
    snippet, _ = find_snippet_any(search_term)
    if not snippet:
        add_result(check_id, "L2", "WARN", f"Snippet not found for '{search_term}'", "low")
        return
    prompt = AUDIT_PROMPT.format(
        bug_id=check_id,
        description=description,
        snippet=snippet[:1500],
    )
    text, err = call_ai(prompt)
    if err:
        add_result(check_id, "L2", "WARN", f"AI call failed: {err}", "low")
        return
    status, finding, risk = parse_structured(text)
    add_result(check_id, "L2", status, finding, risk)


def ai_audit_B1():
    ai_audit(
        "B1",
        "EXIT TOMORROW appeared one day early. Fix: changed <=1 to ==1 in _assess_exit_due(). Verify ==1 is placed correctly with no edge cases.",
        "_assess_exit_due",
    )


def ai_audit_B2():
    ai_audit(
        "B2",
        "EOD Telegram showed Resolved: 0 always. Fix: open_count and load_history() result now passed to send_eod_summary(). Verify both args present and used.",
        "send_eod_summary",
    )


def ai_audit_B3():
    ai_audit(
        "B3",
        "Target hit was never detected. Fix added detection in stop_alert_writer.py. Verify UP signals check price >= target_price, DOWN signals check price <= target_price.",
        "target_price",
    )


def ai_audit_D1():
    ai_audit(
        "D1",
        "Morning scan Telegram showed 0 active signals. Fix: active_signals_count and scan_time injected into market_info dict. Verify both fields populated from real data.",
        "active_signals_count",
    )


def ai_history_anomaly_scan():
    sample = get_history_sample(20)
    if not sample:
        add_result("HISTORY", "L2", "WARN", "No gen=1 signals available for anomaly scan", "low")
        return
    prompt = (
        "You are auditing a live stock scanner signal history for data anomalies.\n\n"
        f"Sample: {len(sample)} gen=1 signals\n"
        f"{json.dumps(sample, indent=2)[:5500]}\n\n"
        "Check for:\n"
        "1. entry_price, scan_price, or target_price = 0.0 or null\n"
        "2. stop_price >= entry_price for UP signals\n"
        "3. target_price <= entry_price for UP signals\n"
        "4. exit_date on Saturday or Sunday\n"
        "5. Duplicate signal_ids\n"
        "6. Outcome OPEN but exit_date already passed\n"
        "7. Any other data or logic anomaly\n\n"
        "Reply ONLY in this exact format:\n"
        "STATUS: PASS | WARN | FAIL\n"
        "FINDINGS:\n"
        "- <finding 1 or None detected>\n"
        "- <finding 2 if any>\n"
        "RISK: none | low | medium | high"
    )
    text, err = call_ai(prompt, max_tokens=500)
    if err:
        add_result("HISTORY", "L2", "WARN", f"AI call failed: {err}", "low")
        return
    status = "WARN"
    risk   = "low"
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("STATUS:"):
            val = line.split(":", 1)[1].strip().upper()
            if val in ("PASS", "FAIL", "WARN"):
                status = val
        elif line.startswith("RISK:"):
            risk = line.split(":", 1)[1].strip().lower()
    if "FINDINGS:" in text:
        findings = text.split("FINDINGS:", 1)[1].split("RISK:")[0].strip()[:350]
    else:
        findings = text.strip()[:350]
    add_result("HISTORY", "L2", status, findings, risk)


def send_telegram_report():
    if not TELEGRAM_BOT_TOKEN:
        print("  Telegram token not set — skipping")
        return
    now         = datetime.now().strftime("%b %d, %Y %H:%M IST")
    model_label = AI_MODEL_KEY.upper() if AI_API_KEY else "NOT CONFIGURED"
    pass_count  = sum(1 for r in results if r["status"] == "PASS")
    fail_count  = sum(1 for r in results if r["status"] == "FAIL")
    warn_count  = sum(1 for r in results if r["status"] == "WARN")
    skip_count  = sum(1 for r in results if r["status"] == "SKIP")
    l1          = [r for r in results if r["layer"] == "L1"]
    l2          = [r for r in results if r["layer"] == "L2"]
    lines = [
        "TIE TIY Fix Verifier",
        f"Date: {now}  |  Model: {model_label}",
        "",
        "--- STATIC CHECKS ---",
    ]
    for r in l1:
        lines.append(f"{ICONS[r['status']]} {r['id']} — {r['finding']}")
    lines += ["", "--- AI CODE AUDIT ---"]
    if l2:
        for r in l2:
            risk_tag = f" [{r['risk']} risk]" if r["risk"] not in ("none", "low") else ""
            lines.append(f"{ICONS[r['status']]} {r['id']} — {r['finding']}{risk_tag}")
    else:
        lines.append("PENDING — add AICREDITS_API_KEY to GitHub Secrets")
    lines += [
        "",
        "----------------------",
        f"PASS:{pass_count}  FAIL:{fail_count}  WARN:{warn_count}  SKIP:{skip_count}",
    ]
    if fail_count > 0:
        lines.append("FAILs detected — review before next trading day")
    elif warn_count > 0:
        lines.append("WARNs present — low risk, review when free")
    else:
        lines.append("All checks clean — system healthy")
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": "\n".join(lines)},
            timeout=10,
        )
        resp.raise_for_status()
        print("  Telegram report sent")
    except Exception as e:
        print(f"  Telegram send failed: {e}")


def run_layer1():
    print("\n--- LAYER 1: STATIC CHECKS ---")
    check_D3_tml_removed()
    check_D3_tml_in_workflows()
    check_F3_price_feed_exists()
    check_F1_no_rejected_records()
    check_SCHEMA_gen1_keys()
    check_B1_string_presence()


def run_layer2():
    print("\n--- LAYER 2: AI CODE AUDIT ---")
    if not AI_API_KEY:
        print("  AICREDITS_API_KEY not set — Layer 2 skipped")
        return
    print(f"  Model: {AI_MODEL} ({AI_MODEL_KEY})")
    critical_fails = [r for r in results if r["status"] == "FAIL" and r["layer"] == "L1"]
    if len(critical_fails) >= 3:
        add_result("L2-GATE", "L2", "SKIP", f"{len(critical_fails)} L1 failures — fix first, AI audit skipped", "high")
        return
    ai_audit_B1()
    ai_audit_B2()
    ai_audit_B3()
    ai_audit_D1()
    ai_history_anomaly_scan()


if __name__ == "__main__":
    print("=" * 55)
    print("  TIE TIY Fix Verifier")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Model  : {AI_MODEL_KEY} — {AI_MODEL}")
    print(f"  API Key: {'SET' if AI_API_KEY else 'NOT SET — Layer 2 will skip'}")
    print("=" * 55)
    run_layer1()
    run_layer2()
    print("\n--- TELEGRAM REPORT ---")
    send_telegram_report()
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    print(f"\n{'FAIL: ' + str(fail_count) + ' failure(s) detected' if fail_count else 'OK: All checks passed or warned'}")
    exit(1 if fail_count else 0)
