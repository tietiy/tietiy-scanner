"""Production backtest harness — applies 37 v4.1 rules to signals.

Two paths:
- Path A: signal_history.json (production scanner outputs, n=290)
- Path B: enriched_signals.parquet filtered to operational window
  (broader academic universe; n=816 in 2026-04-01 to 2026-04-29)

Joined where possible by (date, symbol, signal) — Path A signals get
their feat_* fields from enriched_signals when matched.

Rule precedence per v4.1 schema:
  1. KILL/REJECT terminating
  2. Sub-regime gate (eligibility)
  3. Sector/calendar pessimistic merge
  4. Phase-5 override (upgrade-only, not implemented in this harness;
     no Phase-5 combo data joined to signals here)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "factory" / "opus_iteration"))

from _validate_paths import add_derived_features  # noqa: E402

# Inputs
RULES_PATH = _LAB_ROOT / "factory" / "step5_finalization" / "L4_opus_output" / "unified_rules_v4_1_FINAL.json"
SIGNAL_HISTORY_PATH = _LAB_ROOT.parent / "output" / "signal_history.json"
ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"


# Verdict precedence (most conservative wins for layers 2-3)
VERDICT_RANK = {
    "REJECT": 0,
    "SKIP": 1,
    "WATCH": 2,
    "TAKE_SMALL": 3,
    "TAKE_FULL": 4,
}


@dataclass
class RuleMatch:
    rule_id: str
    verdict: str
    expected_wr: float
    confidence_tier: str
    priority: str
    rule_type: str
    sub_regime_constraint: Optional[str]


def load_rules(path: Path) -> list[dict]:
    return json.loads(path.read_text())["rules"]


def matches_rule(signal_row: pd.Series, rule: dict) -> bool:
    """Apply rule's match_fields + conditions + sub_regime_constraint."""
    mf = rule.get("match_fields", {})

    if mf.get("signal") is not None:
        sig_val = mf["signal"]
        actual = signal_row.get("signal")
        if isinstance(sig_val, list):
            if actual not in sig_val:
                return False
        elif actual != sig_val:
            return False

    if mf.get("sector") is not None:
        sec_val = mf["sector"]
        actual = signal_row.get("sector")
        if isinstance(sec_val, list):
            if actual not in sec_val:
                return False
        elif actual != sec_val:
            return False

    if mf.get("regime") is not None:
        reg_val = mf["regime"]
        actual = signal_row.get("regime")
        if isinstance(reg_val, list):
            if actual not in reg_val:
                return False
        elif actual != reg_val:
            return False

    sub = rule.get("sub_regime_constraint")
    if sub is not None:
        if signal_row.get("sub_regime") != sub:
            return False

    for cond in rule.get("conditions", []):
        feat = cond["feature"]
        val = cond["value"]
        op = cond.get("operator", "eq")

        col_name = feat
        # bucket-redirect
        if isinstance(val, str) and val.lower() in ("low", "medium", "high"):
            bucket_col = f"{feat}_bucket"
            if bucket_col in signal_row.index:
                col_name = bucket_col
                val = val.lower()

        if col_name not in signal_row.index:
            return False
        actual = signal_row.get(col_name)
        if pd.isna(actual):
            return False

        if op == "eq":
            if actual != val:
                return False
        elif op == "in":
            if isinstance(val, list):
                if actual not in val:
                    return False
            elif actual != val:
                return False
        elif op == "gt":
            if not (actual > val):
                return False
        elif op == "lt":
            if not (actual < val):
                return False
        elif op == "gte":
            if not (actual >= val):
                return False
        elif op == "lte":
            if not (actual <= val):
                return False
    return True


def evaluate_signal(signal_row: pd.Series, rules: list[dict]) -> dict:
    """Apply v4.1 rule precedence to a signal row.

    Returns:
      - matched_rule_ids: list of rule IDs that matched
      - winning_verdict: final verdict per precedence
      - calibrated_wr: from winning rule
      - confidence_tier: from winning rule
      - rule_layer: which precedence layer decided ('kill', 'subregime', 'sector_calendar', 'default')
    """
    matched: list[RuleMatch] = []
    for rule in rules:
        if matches_rule(signal_row, rule):
            matched.append(RuleMatch(
                rule_id=rule["id"],
                verdict=rule.get("verdict", "SKIP"),
                expected_wr=rule.get("expected_wr", 0.5),
                confidence_tier=rule.get("confidence_tier", "MEDIUM"),
                priority=rule.get("priority", "MEDIUM"),
                rule_type=rule.get("type", "boost"),
                sub_regime_constraint=rule.get("sub_regime_constraint"),
            ))

    matched_ids = [m.rule_id for m in matched]

    # Layer 1: KILL/REJECT terminating
    kill_match = next(
        (m for m in matched
         if m.rule_type == "kill" or m.verdict in ("REJECT", "SKIP")
        ),
        None,
    )
    if kill_match is not None:
        return {
            "matched_rule_ids": matched_ids,
            "winning_rule_id": kill_match.rule_id,
            "winning_verdict": kill_match.verdict,
            "calibrated_wr": kill_match.expected_wr,
            "confidence_tier": kill_match.confidence_tier,
            "winning_priority": kill_match.priority,
            "rule_layer": "kill",
        }

    # Layer 2-3: pessimistic merge among remaining matches
    if matched:
        # Pick worst-verdict (most conservative) — tie-break by highest expected_wr
        winner = min(matched, key=lambda m: (VERDICT_RANK.get(m.verdict, 99), -m.expected_wr))
        return {
            "matched_rule_ids": matched_ids,
            "winning_rule_id": winner.rule_id,
            "winning_verdict": winner.verdict,
            "calibrated_wr": winner.expected_wr,
            "confidence_tier": winner.confidence_tier,
            "winning_priority": winner.priority,
            "rule_layer": "boost_or_subregime",
        }

    # Default: no rules matched
    return {
        "matched_rule_ids": [],
        "winning_rule_id": None,
        "winning_verdict": "SKIP",  # default conservative
        "calibrated_wr": None,
        "confidence_tier": None,
        "winning_priority": None,
        "rule_layer": "default",
    }


def outcome_to_won(outcome: str) -> Optional[int]:
    if outcome in ("DAY6_WIN", "TARGET_HIT", "WON"):
        return 1
    if outcome in ("DAY6_LOSS", "STOP_HIT"):
        return 0
    return None


def hypothetical_pnl(verdict: str, won: Optional[int]) -> Optional[float]:
    """Simplified hypothetical PnL.

    TAKE_FULL: full position; outcome is +1/-1 (win/loss); flat=0
    TAKE_SMALL: half position; outcome is +0.5/-0.5
    WATCH: no position
    SKIP / REJECT: no position
    """
    if won is None:
        return None
    if verdict == "TAKE_FULL":
        return 1.0 if won == 1 else -1.0
    if verdict == "TAKE_SMALL":
        return 0.5 if won == 1 else -0.5
    return 0.0  # WATCH/SKIP/REJECT


def load_signal_history() -> pd.DataFrame:
    sh = json.loads(SIGNAL_HISTORY_PATH.read_text())
    df = pd.DataFrame(sh.get("history", []))
    return df


def load_enriched_op() -> pd.DataFrame:
    df = pd.read_parquet(ENRICHED_PATH)
    return df


def operational_window(df_sh: pd.DataFrame) -> tuple[str, str]:
    return (df_sh["date"].min(), df_sh["date"].max())


def join_signal_history_to_enriched(
    df_sh: pd.DataFrame, df_en: pd.DataFrame
) -> pd.DataFrame:
    """Join signal_history rows to enriched_signals by (date, symbol_clean, signal).

    Returns df_sh augmented with feat_* columns where match found.
    Unmatched rows keep their basic fields; feat_* columns will be NaN.
    """
    df_sh = df_sh.copy()
    df_en = df_en.copy()
    df_sh["symbol_clean"] = df_sh["symbol"].str.replace(".NS", "", regex=False)
    df_en["symbol_clean"] = df_en["symbol"].str.replace(".NS", "", regex=False)
    df_en = df_en.rename(columns={"scan_date": "date"})
    feat_cols = [c for c in df_en.columns if c.startswith("feat_")] + ["sub_regime", "won"]
    keep_cols = ["date", "symbol_clean", "signal"] + feat_cols
    df_en_keep = df_en[keep_cols].drop_duplicates(subset=["date", "symbol_clean", "signal"])

    merged = df_sh.merge(df_en_keep, on=["date", "symbol_clean", "signal"], how="left", suffixes=("", "_en"))
    return merged


__all__ = [
    "RULES_PATH", "SIGNAL_HISTORY_PATH", "ENRICHED_PATH",
    "load_rules", "load_signal_history", "load_enriched_op",
    "matches_rule", "evaluate_signal",
    "outcome_to_won", "hypothetical_pnl",
    "operational_window", "join_signal_history_to_enriched",
    "add_derived_features",
]


if __name__ == "__main__":
    # Smoke test
    rules = load_rules(RULES_PATH)
    print(f"Loaded {len(rules)} rules from {RULES_PATH.name}")

    df_sh = load_signal_history()
    print(f"Signal history: n={len(df_sh)}")
    op_start, op_end = operational_window(df_sh)
    print(f"  operational window: {op_start} → {op_end}")
    print(f"  outcome distribution: {df_sh['outcome'].value_counts().to_dict()}")
    print(f"  resolved (won/lost): {df_sh['outcome'].isin(['DAY6_WIN','TARGET_HIT','WON','DAY6_LOSS','STOP_HIT']).sum()}")

    df_en = load_enriched_op()
    df_en = add_derived_features(df_en)
    df_en_op = df_en[(df_en["scan_date"] >= op_start) & (df_en["scan_date"] <= op_end)]
    print(f"\nEnriched op-window: n={len(df_en_op)}")
    print(f"  regimes: {df_en_op['regime'].value_counts().to_dict()}")
    print(f"  resolved: {df_en_op['won'].notna().sum()}")

    # Test rule matching on a sample
    print("\nTesting rule application on first 3 enriched op signals:")
    for i in range(3):
        row = df_en_op.iloc[i]
        result = evaluate_signal(row, rules)
        print(f"  {row['scan_date']} {row['symbol']:15} {row['signal']:11} regime={row['regime']:6}: "
              f"matched={result['matched_rule_ids'][:3]}, "
              f"verdict={result['winning_verdict']}")
