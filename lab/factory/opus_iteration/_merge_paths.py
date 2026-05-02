"""P3 — Best-of-both merge of Path 1 and Path 2 rules.

Strategy:
- For shared rule slots (existing rules + numbered rule_NNN with same
  source_finding), pick the path whose version validated better.
- Rules with same intent but different implementation: prefer the one
  with PASS over WARNING over FAIL.
- Rules unique to one path: include if they passed validation.
- Output: unified_rules_final.json + validation_predictions_final.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

P1_RULES = _HERE / "path1_disciplined" / "output" / "unified_rules_path1.json"
P1_PREDS = _HERE / "path1_disciplined" / "output" / "validation_predictions_path1.json"
P1_VAL = _HERE / "validation_path1.json"

P2_RULES = _HERE / "path2_trust" / "output" / "unified_rules_path2.json"
P2_PREDS = _HERE / "path2_trust" / "output" / "validation_predictions_path2.json"
P2_VAL = _HERE / "validation_path2.json"

FINAL_RULES = _HERE / "unified_rules_final.json"
FINAL_PREDS = _HERE / "validation_predictions_final.json"
COMPARISON = _HERE / "comparison_report.md"


VERDICT_RANK = {"PASS": 3, "WARNING": 2, "FAIL": 1}


def _load(p):
    return json.loads(p.read_text())


def main():
    p1_rules_data = _load(P1_RULES)
    p1_preds_data = _load(P1_PREDS)
    p1_val_data = _load(P1_VAL)

    p2_rules_data = _load(P2_RULES)
    p2_preds_data = _load(P2_PREDS)
    p2_val_data = _load(P2_VAL)

    # Index by id
    p1_rules = {r["id"]: r for r in p1_rules_data["rules"]}
    p1_preds = {p["rule_id"]: p for p in p1_preds_data["predictions"]}
    p1_val = {r["rule_id"]: r for r in p1_val_data["results"]}

    p2_rules = {r["id"]: r for r in p2_rules_data["rules"]}
    p2_preds = {p["rule_id"]: p for p in p2_preds_data["predictions"]}
    p2_val = {r["rule_id"]: r for r in p2_val_data["results"]}

    print(f"Path 1: {len(p1_rules)} rules; Path 2: {len(p2_rules)} rules")

    # Match rules by id (existing) or by signature for numbered ones
    # Existing rules have stable ids (kill_001, win_001..win_007, watch_001)
    EXISTING_IDS = ["kill_001", "watch_001", "win_001", "win_002", "win_003",
                    "win_004", "win_005", "win_006", "win_007"]

    def signature(rule):
        """Logical signature — coarse: signal × sector × regime × sub_regime × verdict.

        Conditions deliberately excluded — rules with same target slot but
        different filter conditions are considered same logical rule;
        validation picks the better-calibrated one.
        """
        mf = rule.get("match_fields", {})
        sub = rule.get("sub_regime_constraint", "")
        verd = rule.get("verdict", "")
        # Also include single key calendar/feature condition for a
        # rule like "Bear UP_TRI Dec SKIP" vs "Bear UP_TRI Sep SKIP"
        # which need to stay distinct.
        cal_keys = sorted([
            f"{c.get('feature')}={c.get('value')}"
            for c in rule.get("conditions", [])
            if c.get("feature") in (
                "feat_month", "feat_day_of_month_bucket", "feat_day_of_week",
                "feat_vol_climax_flag",
            )
        ])
        return (
            mf.get("signal", ""),
            mf.get("sector", "") or "",
            mf.get("regime", "") or "",
            sub or "",
            verd,
            tuple(cal_keys),
        )

    # Build signatures
    p1_sigs = {rid: signature(r) for rid, r in p1_rules.items()}
    p2_sigs = {rid: signature(r) for rid, r in p2_rules.items()}

    # Build sig → list of (path, rule_id, validation_verdict, rule, pred)
    sig_groups = {}
    for rid, sig in p1_sigs.items():
        sig_groups.setdefault(sig, []).append({
            "path": "path1", "rule_id": rid,
            "rule": p1_rules[rid], "pred": p1_preds.get(rid),
            "val": p1_val.get(rid),
        })
    for rid, sig in p2_sigs.items():
        sig_groups.setdefault(sig, []).append({
            "path": "path2", "rule_id": rid,
            "rule": p2_rules[rid], "pred": p2_preds.get(rid),
            "val": p2_val.get(rid),
        })

    # Best-of merge per signature
    merged_rules = []
    merged_preds = []
    comparison_log = []
    seen_ids = set()
    next_id = 1

    for sig, candidates in sig_groups.items():
        if len(candidates) == 1:
            c = candidates[0]
            chosen = c
            note = f"unique to {c['path']}"
        else:
            # Two candidates; pick the one with better validation
            best = max(candidates, key=lambda c: VERDICT_RANK.get(
                (c["val"] or {}).get("validation_verdict", "FAIL"), 0
            ))
            other = [c for c in candidates if c is not best][0]
            note = (
                f"chose {best['path']} ({(best['val'] or {}).get('validation_verdict')}) "
                f"over {other['path']} ({(other['val'] or {}).get('validation_verdict')})"
            )
            chosen = best

        # Re-id rules to avoid collisions
        rule = dict(chosen["rule"])
        original_id = rule["id"]

        # Prefer EXISTING ids verbatim
        if original_id in EXISTING_IDS and original_id not in seen_ids:
            new_id = original_id
        else:
            # Generate sequential id for synthesized rules
            while f"rule_{next_id:03d}" in seen_ids:
                next_id += 1
            new_id = f"rule_{next_id:03d}"
            next_id += 1
        seen_ids.add(new_id)

        # Update id and preserve original_path / original_id
        rule["id"] = new_id
        rule["_merge_origin"] = chosen["path"]
        rule["_merge_original_id"] = original_id
        merged_rules.append(rule)

        # Carry prediction
        if chosen["pred"]:
            new_pred = dict(chosen["pred"])
            new_pred["rule_id"] = new_id
            merged_preds.append(new_pred)

        comparison_log.append({
            "merged_id": new_id,
            "signature_summary": (
                f"{sig[0] or 'any'}×{sig[1] or 'any'}×{sig[2] or 'any'} "
                f"sub={sig[3] or '-'} verdict={sig[4]}"
            ),
            "candidates": [
                {
                    "path": c["path"],
                    "rule_id": c["rule_id"],
                    "validation_verdict": (c["val"] or {}).get("validation_verdict"),
                    "n_actual": (c["val"] or {}).get("actual_match_count"),
                    "wr_actual": (c["val"] or {}).get("actual_match_wr"),
                }
                for c in candidates
            ],
            "chosen": chosen["path"],
            "chosen_validation": (chosen["val"] or {}).get("validation_verdict"),
            "note": note,
        })

    # Sort merged rules: existing first, then by priority HIGH/MEDIUM/LOW
    PRIO_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    def sort_key(r):
        is_existing = 0 if r["id"] in EXISTING_IDS else 1
        prio = PRIO_RANK.get(r.get("priority", "MEDIUM"), 9)
        return (is_existing, prio, r["id"])
    merged_rules.sort(key=sort_key)

    final_rules_payload = {
        "schema_version": 4,
        "merge_strategy": "best-of-both validated; tie → Path 1 (disciplined)",
        "n_rules": len(merged_rules),
        "rules": merged_rules,
    }
    FINAL_RULES.write_text(json.dumps(final_rules_payload, indent=2))

    # Predictions
    pred_by_id = {p["rule_id"]: p for p in merged_preds}
    final_preds_payload = {
        "schema_version": 4,
        "predictions": [pred_by_id[r["id"]] for r in merged_rules if r["id"] in pred_by_id],
    }
    FINAL_PREDS.write_text(json.dumps(final_preds_payload, indent=2))

    # Comparison report
    p1s = p1_val_data["summary"]
    p2s = p2_val_data["summary"]
    md = [f"# Path 1 vs Path 2 — Comparison + Best-of-Both Merge",
          "",
          f"**Date:** 2026-05-03",
          "",
          "## Aggregate validation results",
          "",
          f"| Metric | Path 1 (Disciplined) | Path 2 (Trust-Opus) |",
          f"|---|---|---|",
          f"| Total rules | {p1_val_data['n_rules']} | {p2_val_data['n_rules']} |",
          f"| PASS | {p1s['PASS']} | {p2s['PASS']} |",
          f"| WARNING | {p1s['WARNING']} | {p2s['WARNING']} |",
          f"| FAIL | {p1s['FAIL']} | {p2s['FAIL']} |",
          f"| Pass rate | {p1s['pass_rate']*100:.1f}% | {p2s['pass_rate']*100:.1f}% |",
          f"| Pass+Warning | {p1s['pass_or_warning_rate']*100:.1f}% | {p2s['pass_or_warning_rate']*100:.1f}% |",
          "",
          "## Merge result",
          "",
          f"- Total signatures (deduped logical rules): {len(sig_groups)}",
          f"- Final merged rule count: {len(merged_rules)}",
          f"- Predictions: {len(merged_preds)}",
          "",
          "## Per-signature merge decisions",
          ""]

    md.append("| merged_id | signature | path1 verdict | path2 verdict | chosen | reason |")
    md.append("|---|---|---|---|---|---|")
    for log in comparison_log:
        sig = log["signature_summary"][:60]
        cands = log["candidates"]
        p1c = next((c for c in cands if c["path"] == "path1"), None)
        p2c = next((c for c in cands if c["path"] == "path2"), None)
        p1v = p1c["validation_verdict"] if p1c else "—"
        p2v = p2c["validation_verdict"] if p2c else "—"
        md.append(
            f"| {log['merged_id']} | {sig} | {p1v} | {p2v} | {log['chosen']} | {log['note']} |"
        )
    COMPARISON.write_text("\n".join(md))

    print(f"\nMerge complete:")
    print(f"  Total signatures: {len(sig_groups)}")
    print(f"  Final rules: {len(merged_rules)}")
    print(f"  Saved: {FINAL_RULES}")
    print(f"  Saved: {FINAL_PREDS}")
    print(f"  Saved: {COMPARISON}")

    # Quick stats
    p1_chosen = sum(1 for log in comparison_log if log["chosen"] == "path1")
    p2_chosen = sum(1 for log in comparison_log if log["chosen"] == "path2")
    print(f"\n  Path 1 contributions: {p1_chosen}")
    print(f"  Path 2 contributions: {p2_chosen}")


if __name__ == "__main__":
    main()
