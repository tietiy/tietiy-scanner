"""Validation 3 — Transition Reasonableness.

Per doc/regime_v2_design/05_validation.md §"Validation 3".

Pass:
  T1: 6 ≤ transitions in last 12 months ≤ 20
  T2: ≥75% of known inflection points captured within ±5 trading days
  T3: ≤20% false transitions (reversal within 5 days)
"""
from __future__ import annotations

import json
import os
from typing import List

import pandas as pd


def detect_known_inflections(nifty_path: str = "data/historical/nifty.parquet",
                              window_start: str = "2025-05-01",
                              window_end: str = "2026-05-05") -> List[pd.Timestamp]:
    """Auto-detect inflection points: 5-day moves > 5%."""
    df = pd.read_parquet(nifty_path)
    df.index = pd.to_datetime(df.index)
    df = df.loc[(df.index >= window_start) & (df.index <= window_end)]
    close = df["Close"].astype(float)
    rolling_5d_ret = (close / close.shift(5) - 1.0) * 100.0
    # Inflection: any day where 5d return |x| > 5%
    candidates = rolling_5d_ret[abs(rolling_5d_ret) > 5.0].index.tolist()
    # Dedupe — keep only first occurrence within any 10-day window
    deduped = []
    for d in candidates:
        if not deduped or (d - deduped[-1]).days > 10:
            deduped.append(d)
    return deduped


def run(out_dir: str = "output/regime_v2/validation",
        window_start: str = "2025-05-01",
        window_end: str = "2026-05-05") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    v2 = pd.read_parquet("output/regime_v2/regime_historical.parquet")
    v2.index = pd.to_datetime(v2.index)
    v2_window = v2.loc[(v2.index >= window_start) & (v2.index <= window_end)]

    # Identify transitions: where state changes from prior row
    transitions = v2_window[v2_window["state"] != v2_window["state"].shift()].index.tolist()
    # Drop the first row (it's a "transition" from nothing)
    if len(transitions) > 0 and transitions[0] == v2_window.index.min():
        transitions = transitions[1:]
    n_transitions = len(transitions)

    # T1
    t1_pass = 6 <= n_transitions <= 20

    # T2: known inflections captured within ±5 trading days
    inflections = detect_known_inflections(window_start=window_start, window_end=window_end)
    n_inflections = len(inflections)

    captured = 0
    capture_log = []
    for infl in inflections:
        # Find closest transition
        if not transitions:
            capture_log.append({"inflection": str(infl.date()), "captured": False, "nearest_transition": None, "days_off": None})
            continue
        diffs = [(t, abs((t - infl).days)) for t in transitions]
        nearest_t, days_off = min(diffs, key=lambda x: x[1])
        is_captured = days_off <= 5
        if is_captured:
            captured += 1
        capture_log.append({
            "inflection": str(infl.date()),
            "nearest_transition": str(nearest_t.date()),
            "days_off": days_off,
            "captured": is_captured,
        })

    t2_pct = (captured / n_inflections * 100) if n_inflections > 0 else 100.0
    t2_pass = t2_pct >= 75.0

    # T3: false transitions (reverse within 5 days)
    false_count = 0
    for i, t in enumerate(transitions):
        if i + 1 >= len(transitions):
            continue
        next_t = transitions[i + 1]
        days_to_next = (next_t - t).days
        if days_to_next <= 5:
            # Check if state reverted to pre-transition
            prior_state = v2_window.loc[:t]["state"].iloc[-2] if len(v2_window.loc[:t]) >= 2 else None
            next_state = v2_window.loc[next_t]["state"]
            if prior_state == next_state:
                false_count += 1
    t3_pct = (false_count / n_transitions * 100) if n_transitions > 0 else 0.0
    t3_pass = t3_pct <= 20.0

    all_pass = t1_pass and t2_pass and t3_pass

    report = {
        "validation": "V3 Transition Reasonableness",
        "design_ref": "doc/regime_v2_design/05_validation.md §V3",
        "window": [window_start, window_end],
        "T1_transitions_count": {
            "value": n_transitions,
            "range": "6 ≤ x ≤ 20",
            "pass": t1_pass,
        },
        "T2_inflection_capture": {
            "n_inflections": n_inflections,
            "n_captured": captured,
            "pct": round(t2_pct, 1),
            "threshold": "≥ 75%",
            "pass": t2_pass,
            "log": capture_log,
        },
        "T3_false_transition_rate": {
            "n_false": false_count,
            "n_transitions": n_transitions,
            "pct": round(t3_pct, 1),
            "threshold": "≤ 20%",
            "pass": t3_pass,
        },
        "OVERALL": "PASS" if all_pass else "FAIL",
    }

    md_path = os.path.join(out_dir, "v3_transition_reasonableness.md")
    with open(md_path, "w") as f:
        f.write(_render_md(report))
    print(_render_md(report))
    return report


def _render_md(r: dict) -> str:
    s = f"# Validation 3 — Transition Reasonableness\n\n"
    s += f"**Design ref:** {r['design_ref']}\n"
    s += f"**Window:** {r['window'][0]} → {r['window'][1]}\n"
    s += f"**Outcome:** **{r['OVERALL']}**\n\n"
    s += f"## Criteria\n\n"
    for code, payload in [
        ("T1", r["T1_transitions_count"]),
        ("T2", r["T2_inflection_capture"]),
        ("T3", r["T3_false_transition_rate"]),
    ]:
        status = "✅ PASS" if payload["pass"] else "❌ FAIL"
        s += f"### {code} — {status}\n\n"
        for k, v in payload.items():
            if k == "pass":
                continue
            if k == "log" and isinstance(v, list):
                s += f"  - **{k}**:\n"
                for item in v:
                    s += f"    - {item}\n"
            else:
                s += f"  - **{k}**: {v}\n"
        s += "\n"
    return s


if __name__ == "__main__":
    run()
