"""Re-parse the cached Opus raw response without re-calling the API."""
from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _run_opus import parse_deliverables, OUTPUT_DIR, RAW_RESPONSE_PATH, DELIVERABLES  # noqa: E402

text = RAW_RESPONSE_PATH.read_text()
parts = parse_deliverables(text)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
for fname in DELIVERABLES:
    if fname in parts:
        (OUTPUT_DIR / fname).write_text(parts[fname])
        print(f"  ✓ {fname:38s} ({len(parts[fname]):,} chars)")
    else:
        print(f"  ✗ {fname:38s} MISSING")

import json
rules_path = OUTPUT_DIR / "unified_rules_v4.json"
if rules_path.exists():
    try:
        data = json.loads(rules_path.read_text())
        n_rules = len(data.get("rules", []))
        print(f"\n  unified_rules_v4.json parses OK: {n_rules} rules, schema_version={data.get('schema_version')}")
    except json.JSONDecodeError as e:
        print(f"\n  ⚠ unified_rules_v4.json fails to parse: {e}")
