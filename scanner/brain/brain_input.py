"""Brain input — read truth files, normalize, surface as derived-view inputs.

Mirrors scanner/bridge/core/evidence_collector.load_truth_files style but
brain-specific: no error_handler coupling. Missing files log a loud
warning to stderr and return {} for that key (per project_anchor §6 P-12
discipline + Step 3 design audit Part C-1).

See doc/brain_design_v1.md §2 + §4 Step 3 for the full read contract.
"""
import json
import os
import sys


_TRUTH_FILE_SPECS = (
    # (key,                    base_dir, filename,                       default)
    ("signal_history",         "output", "signal_history.json",          {}),
    ("patterns",               "output", "patterns.json",                {}),
    ("proposed_rules",         "output", "proposed_rules.json",          {}),
    ("contra_shadow",          "output", "contra_shadow.json",           {}),
    ("weekly_intelligence",    "output", "weekly_intelligence_latest.json", {}),
    ("mini_scanner_rules",     "data",   "mini_scanner_rules.json",      {}),
)


def load_truth_files(output_dir: str = "output",
                     data_dir: str = "data") -> dict:
    """
    Load all truth files brain Step 3 derivers consume. Returns dict
    keyed by canonical names; missing files become empty dict default
    with a loud stderr warning (no silent failure per P-12).

    Step 3's 4 derivers select keys they need:
    - derive_cohort_health → signal_history
    - derive_regime_watch → signal_history + weekly_intelligence
    - derive_portfolio_exposure → signal_history (fallback) + bridge_state_history (read separately)
    - derive_ground_truth_gaps → signal_history + mini_scanner_rules + patterns
    """
    bases = {"output": output_dir, "data": data_dir}
    out: dict = {}
    for key, base, fname, default in _TRUTH_FILE_SPECS:
        path = os.path.join(bases[base], fname)
        loaded = _load_json_file(path)
        if loaded is None:
            print(f"[brain_input] WARNING: {path} missing or "
                  f"unreadable — using empty dict default for {key!r}",
                  file=sys.stderr)
            out[key] = default
        else:
            out[key] = loaded
    return out


def _load_json_file(path: str):
    """Returns parsed JSON, or None if file missing/unreadable."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
