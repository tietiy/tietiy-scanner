"""
Bull UP_TRI cell — BU2: sub-regime stratification + cross-cell
direction-flip prediction tests.

Tests architectural predictions from Bear synthesis at lifetime scale:

  H1: trend_persistence (200d_return) is a WINNER feature for Bull UP_TRI
      Predicted: high 200d_return → higher WR (parallel to Bear UP_TRI's
      nifty_60d_return=low anchor)

  H2: trend_persistence inverts for Bull DOWN_TRI (lifetime-only test
      since 0 live Bull data; this validates the meta-pattern)

  H3: leadership_concentration (breadth) modulates within Bull UP_TRI
      Predicted: low breadth + recovery_bull = highest WR cell
      (already confirmed in BU1 axis discovery)

  H4: Bullish setup architecture parallels Bear UP_TRI:
      - inside_bar=True compression preference
      - wk4 calendar winner
      - similar sector ordering (defensives top?)

Saves: lab/factory/bull_uptri/lifetime/stratification.json
       lab/factory/bull_uptri/lifetime/stratification_llm.md
"""
from __future__ import annotations

import importlib.util as _ilu
import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))
sys.path.insert(0, str(_LAB_ROOT / "infrastructure" / "analyzer"))

from feature_loader import FeatureRegistry  # noqa: E402

# Reuse matches_level
_filter_path = (_LAB_ROOT / "factory" / "bear_uptri" / "filter_test.py")
_spec = _ilu.spec_from_file_location("bear_uptri_filter_bu2", _filter_path)
_filter_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_filter_mod)
matches_level = _filter_mod.matches_level

# Reuse Bull sub-regime detector
_detector_path = (_LAB_ROOT / "factory" / "bull" / "subregime"
                   / "detector.py")
_dspec = _ilu.spec_from_file_location("bull_subregime_bu2", _detector_path)
_detector_mod = _ilu.module_from_spec(_dspec)
sys.modules["bull_subregime_bu2"] = _detector_mod
_dspec.loader.exec_module(_detector_mod)
detect_bull_subregime = _detector_mod.detect_bull_subregime

ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _HERE / "stratification.json"
LLM_OUTPUT_PATH = _HERE / "stratification_llm.md"


def _wlf(o: str) -> str:
    if o in ("DAY6_WIN", "TARGET_HIT"):
        return "W"
    if o in ("DAY6_LOSS", "STOP_HIT"):
        return "L"
    if o == "DAY6_FLAT":
        return "F"
    return "?"


def _wr(grp: pd.DataFrame) -> dict:
    nw = int((grp["wlf"] == "W").sum())
    nl = int((grp["wlf"] == "L").sum())
    nf = int((grp["wlf"] == "F").sum())
    return {
        "n": len(grp), "n_w": nw, "n_l": nl, "n_f": nf,
        "wr": (nw / (nw + nl)) if (nw + nl) > 0 else None,
    }


def feature_test(df: pd.DataFrame, fid: str, lvl: str,
                    spec_by_id: dict, bounds_cache: dict, label: str,
                    min_n: int = 100) -> dict:
    """Test a single feature × level: presence_wr vs absence_wr."""
    spec = spec_by_id.get(fid)
    if spec is None:
        return {"label": label, "error": "spec missing"}
    col = f"feat_{fid}"
    if col not in df.columns:
        return {"label": label, "error": "column missing"}
    mask = df[col].apply(
        lambda v: matches_level(spec, v, lvl, bounds_cache)
    ).fillna(False)
    p = df[mask]
    a = df[~mask]
    p_wr = _wr(p)
    a_wr = _wr(a)
    if p_wr["n_w"] + p_wr["n_l"] < min_n:
        return {"label": label, "error": "presence n too small"}
    delta = ((p_wr["wr"] - a_wr["wr"]) * 100
              if p_wr["wr"] is not None and a_wr["wr"] is not None
              else None)
    return {
        "label": label,
        "feature_id": fid, "level": lvl,
        "presence_n": p_wr["n_w"] + p_wr["n_l"],
        "presence_wr": p_wr["wr"],
        "absence_wr": a_wr["wr"],
        "delta_pp": float(delta) if delta is not None else None,
    }


def main():
    print("─" * 80)
    print("BU2: Bull UP_TRI sub-regime stratification + cross-cell predictions")
    print("─" * 80)

    df = pd.read_parquet(ENRICHED_PATH)
    bu = df[(df["regime"] == "Bull") & (df["signal"] == "UP_TRI")].copy()
    bu["wlf"] = bu["outcome"].apply(_wlf)
    bu_wl = bu[bu["wlf"].isin(["W", "L", "F"])].copy()
    bu_wl["scan_date"] = pd.to_datetime(bu_wl["scan_date"])
    bu_wl["month"] = bu_wl["scan_date"].dt.month

    baseline_wr = _wr(bu_wl)["wr"]
    print(f"\nLifetime Bull UP_TRI: n={len(bu_wl)}, baseline {baseline_wr*100:.1f}%")

    # Apply Bull sub-regime detector
    bu_wl["sub"] = bu_wl.apply(
        lambda r: detect_bull_subregime(
            r.get("feat_nifty_200d_return_pct"),
            r.get("feat_market_breadth_pct"),
        ).subregime,
        axis=1,
    )

    registry = FeatureRegistry.load_all()
    spec_by_id = {s.feature_id: s for s in registry.list_all()}
    bounds_cache: dict = {}

    findings = {
        "lifetime_baseline_wr": baseline_wr,
        "subregime_distribution": {},
        "cross_cell_predictions": {},
        "bullish_setup_architecture": {},
        "sector_distribution": {},
        "calendar_effects": {},
    }

    # ── A. Sub-regime stratification ────────────────────────────────
    print(f"\n══ A. Sub-regime stratification ══")
    print(f"  {'sub-regime':<14}{'n':>7}{'%':>7}{'WR':>8}{'lift':>8}")
    for sub in ["recovery_bull", "healthy_bull", "normal_bull", "late_bull",
                "unknown"]:
        grp = bu_wl[bu_wl["sub"] == sub]
        if len(grp) == 0:
            continue
        wr = _wr(grp)
        lift = (wr["wr"] - baseline_wr) * 100 if wr["wr"] else 0
        findings["subregime_distribution"][sub] = {
            "n": int(wr["n"]),
            "pct": float(wr["n"] / len(bu_wl)),
            "wr": float(wr["wr"]) if wr["wr"] is not None else None,
            "lift_pp": float(lift),
        }
        print(f"  {sub:<14}{wr['n']:>7}{wr['n']/len(bu_wl)*100:>6.1f}%"
              f"{(wr['wr'] or 0)*100:>7.1f}%{lift:>+7.1f}pp")

    # ── B. Cross-cell direction-flip prediction tests ───────────────
    print(f"\n══ B. Cross-cell direction-flip predictions ══")

    # H1: nifty_200d_return=high should be WINNER for Bull UP_TRI
    print(f"\n  H1: nifty_200d_return=high winner-feature for Bull UP_TRI")
    h1 = feature_test(bu_wl, "nifty_200d_return_pct", "high",
                          spec_by_id, bounds_cache, "H1_high200d")
    findings["cross_cell_predictions"]["H1_high200d"] = h1
    if "delta_pp" in h1 and h1["delta_pp"] is not None:
        print(f"    high 200d: WR={h1['presence_wr']*100:.1f}% vs absent "
              f"{h1['absence_wr']*100:.1f}%  delta={h1['delta_pp']:+.1f}pp")
        if h1["delta_pp"] > 2:
            print(f"    ✓ CONFIRMED — high 200d is winner for Bull UP_TRI")
        elif h1["delta_pp"] < -2:
            print(f"    ✗ INVERTED — surprising, may need investigation")
        else:
            print(f"    NEUTRAL — weak signal")

    # H1b: nifty_200d_return=low (recovery_bull anchor) should be WINNER
    print(f"\n  H1b: nifty_200d_return=low (recovery anchor) winner")
    h1b = feature_test(bu_wl, "nifty_200d_return_pct", "low",
                            spec_by_id, bounds_cache, "H1b_low200d")
    findings["cross_cell_predictions"]["H1b_low200d"] = h1b
    if "delta_pp" in h1b and h1b["delta_pp"] is not None:
        print(f"    low 200d: WR={h1b['presence_wr']*100:.1f}% vs absent "
              f"{h1b['absence_wr']*100:.1f}%  delta={h1b['delta_pp']:+.1f}pp")

    # H3: leadership_concentration (breadth) modulates within Bull UP_TRI
    print(f"\n  H3: market_breadth=high (broad participation) winner")
    h3 = feature_test(bu_wl, "market_breadth_pct", "high",
                          spec_by_id, bounds_cache, "H3_high_breadth")
    findings["cross_cell_predictions"]["H3_high_breadth"] = h3
    if "delta_pp" in h3 and h3["delta_pp"] is not None:
        print(f"    high breadth: WR={h3['presence_wr']*100:.1f}% vs absent "
              f"{h3['absence_wr']*100:.1f}%  delta={h3['delta_pp']:+.1f}pp")

    # H2: Test Bull DOWN_TRI for inversion (lifetime data exists for that too)
    print(f"\n  H2: Bull DOWN_TRI direction-flip prediction (lifetime-only)")
    bd = df[(df["regime"] == "Bull") & (df["signal"] == "DOWN_TRI")].copy()
    bd["wlf"] = bd["outcome"].apply(_wlf)
    bd_wl = bd[bd["wlf"].isin(["W", "L", "F"])].copy()
    print(f"    Bull DOWN_TRI lifetime n={len(bd_wl)}")
    if len(bd_wl) > 100:
        bd_baseline = _wr(bd_wl)["wr"]
        print(f"    Bull DOWN_TRI baseline WR: {bd_baseline*100:.1f}%")
        h2 = feature_test(bd_wl, "nifty_200d_return_pct", "high",
                              spec_by_id, bounds_cache, "H2_high200d_DOWN_TRI")
        findings["cross_cell_predictions"]["H2_high200d_DOWN_TRI"] = h2
        if "delta_pp" in h2 and h2["delta_pp"] is not None:
            uptri_delta = (h1.get("delta_pp", 0) if "delta_pp" in h1 else 0)
            downtri_delta = h2["delta_pp"]
            print(f"    high 200d in Bull DOWN_TRI: delta="
                  f"{downtri_delta:+.1f}pp")
            print(f"    UP_TRI delta: {uptri_delta:+.1f}pp")
            if downtri_delta * uptri_delta < 0 and abs(uptri_delta) > 2:
                print(f"    ✓ INVERSION CONFIRMED — direction-flip pattern holds")
            elif abs(downtri_delta) < 2:
                print(f"    NEUTRAL on Bull DOWN_TRI — possibly noise")
            else:
                print(f"    NO INVERSION — same-direction signal")

    # ── C. Bullish setup architecture test ──────────────────────────
    print(f"\n══ C. Bullish setup architecture (vs Bear UP_TRI parallels) ══")
    arch_features = [
        ("inside_bar_flag", "True", "compression preference (Bear UP_TRI: +4.9pp)"),
        ("inside_bar_flag", "False", "expansion (BULL_PROXY-like: +9.4pp Bear)"),
        ("day_of_month_bucket", "wk4", "Bear UP_TRI calendar winner: +7.5pp"),
        ("day_of_month_bucket", "wk2", "Bear UP_TRI anti: -6.4pp"),
        ("higher_highs_intact_flag", "True", "Bear UP_TRI: weak"),
        ("nifty_vol_regime", "High", "Bear UP_TRI: hot sub-regime tier"),
        ("ema_alignment", "bull", "natural for Bull regime"),
        ("multi_tf_alignment_score", "high", "trend confirmation"),
    ]
    print(f"  {'feature':<32}{'level':<10}{'pres_wr':>10}{'delta':>10}  context")
    for fid, lvl, context in arch_features:
        r = feature_test(bu_wl, fid, lvl, spec_by_id, bounds_cache,
                             f"{fid}={lvl}")
        if "delta_pp" in r and r["delta_pp"] is not None:
            findings["bullish_setup_architecture"][f"{fid}={lvl}"] = r
            print(f"  {fid:<32}{lvl:<10}{r['presence_wr']*100:>9.1f}%"
                  f"{r['delta_pp']:>+9.1f}pp  {context}")

    # ── D. Sector + calendar ────────────────────────────────────────
    print(f"\n══ D. Sector × WR (lifetime, n>=200) ══")
    sec_rows = []
    for sec, grp in bu_wl.groupby("sector"):
        if pd.isna(sec):
            continue
        wr = _wr(grp)
        if wr["n"] < 200 or wr["wr"] is None:
            continue
        lift = (wr["wr"] - baseline_wr) * 100
        findings["sector_distribution"][str(sec)] = {
            "n": int(wr["n"]), "wr": float(wr["wr"]),
            "lift_pp": float(lift),
        }
        sec_rows.append((str(sec), wr["n"], wr["wr"], lift))
    sec_rows.sort(key=lambda t: -t[3])
    for sec, n, wr, lift in sec_rows:
        print(f"  {sec:<12}n={n:>5} WR={wr*100:.1f}% lift={lift:+.1f}pp")

    print(f"\n══ E. Calendar effects ══")
    print(f"  Week-of-month:")
    for wk in ("wk1", "wk2", "wk3", "wk4"):
        grp = bu_wl[bu_wl["feat_day_of_month_bucket"] == wk]
        if len(grp) < 200:
            continue
        wr = _wr(grp)
        lift = (wr["wr"] - baseline_wr) * 100 if wr["wr"] else 0
        findings["calendar_effects"][wk] = {
            "n": int(wr["n"]), "wr": float(wr["wr"] or 0),
            "lift_pp": float(lift),
        }
        print(f"    {wk}: n={wr['n']:>5} WR={(wr['wr'] or 0)*100:.1f}% "
              f"lift={lift:+.1f}pp")

    print(f"\n  Month (top 4 + bottom 4):")
    month_rows = []
    for m in range(1, 13):
        grp = bu_wl[bu_wl["month"] == m]
        if len(grp) < 200:
            continue
        wr = _wr(grp)
        if wr["wr"] is None:
            continue
        lift = (wr["wr"] - baseline_wr) * 100
        month_rows.append((m, wr["n"], wr["wr"], lift))
        findings["calendar_effects"][f"month_{m}"] = {
            "n": int(wr["n"]), "wr": float(wr["wr"]),
            "lift_pp": float(lift),
        }
    month_rows.sort(key=lambda t: -t[3])
    mon_lbl = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for m, n, wr, lift in month_rows[:4] + month_rows[-3:]:
        print(f"    {mon_lbl[m-1]:<5}: n={n:>5} WR={wr*100:.1f}% "
              f"lift={lift:+.1f}pp")

    OUTPUT_PATH.write_text(json.dumps(findings, indent=2, default=str))
    print(f"\nSaved: {OUTPUT_PATH}")

    # ── LLM analysis ────────────────────────────────────────────────
    print()
    print("─" * 80)
    print("Calling Sonnet 4.5 for cross-cell architectural analysis...")
    print("─" * 80)

    from llm_client import LLMClient
    pred_lines = "\n".join(
        f"  • {k}: delta={v.get('delta_pp', '?'):+.1f}pp"
        if v.get("delta_pp") is not None else f"  • {k}: error={v.get('error')}"
        for k, v in findings["cross_cell_predictions"].items()
    )
    arch_lines = "\n".join(
        f"  • {k}: delta={v.get('delta_pp', '?'):+.1f}pp"
        if v.get("delta_pp") is not None else f"  • {k}: skipped"
        for k, v in findings["bullish_setup_architecture"].items()
    )
    sec_lines = "\n".join(
        f"  • {sec}: lift={p['lift_pp']:+.1f}pp (n={p['n']})"
        for sec, p in sorted(findings["sector_distribution"].items(),
                                  key=lambda x: -x[1]["lift_pp"])[:8]
    )

    prompt = f"""You are interpreting Bull UP_TRI cell stratification +
cross-cell direction-flip predictions at lifetime scale (n=38,100,
no live Bull data).

## Sub-regime stratification (Bull tri-modal detector)

{json.dumps(findings['subregime_distribution'], indent=2, default=str)}

## Cross-cell direction-flip predictions tested

{pred_lines}

## Bullish setup architecture (Bear UP_TRI parallel comparison)

{arch_lines}

## Sector ranking (top by lift)

{sec_lines}

## Calendar effects

Week-of-month + month rankings — see findings JSON.

## Cross-cell context

Bear UP_TRI (HIGH confidence cell, for comparison):
- Top winner: nifty_60d_return=low (+14.1pp)
- Second winner: swing_high_count_20d=low (+23.3pp)
- inside_bar=True (+4.9pp compression)
- wk4 (+7.5pp)

Bear DOWN_TRI:
- nifty_60d_return=low INVERTED (-4.1pp)
- wk2 (+15pp), wk4 (-17.5pp) — calendar inversion

## Your task

1. **Bullish architecture parallel/divergence.** Does Bull UP_TRI
   parallel Bear UP_TRI architecture (same anchors, same calendar
   inversion) or diverge? What's the trader narrative for Bull UP_TRI
   distinct from Bear UP_TRI?

2. **Direction-flip pattern in Bull regime.** Does the cross-cell
   direction inversion (UP_TRI vs DOWN_TRI on the regime anchor)
   replicate in Bull as it did in Bear?

3. **Recovery_bull's 60.2% WR cell.** Is this a real edge or a
   regime-classification artifact (Bull regime classified before
   200d_return catches up)? What's the trader operationally supposed
   to do with this?

4. **Bull vs Bear UP_TRI sector ranking.** Bear UP_TRI top sectors
   were CapGoods/Auto/Other (defensives + cyclicals). What does Bull
   UP_TRI's sector ranking suggest about which sectors lead in Bull
   vs Bear?

5. **Production posture for PROVISIONAL Bull UP_TRI cell.** No live
   Bull data exists. The cell is lifetime-only. What's the right
   default behavior, and what's the activation criteria?

Format: markdown, ## sections per question, 3-4 short paragraphs each.
Be specific, reference actual numbers."""

    client = LLMClient()
    response = client.synthesize_findings(prompt, max_tokens=3500)
    LLM_OUTPUT_PATH.write_text(
        f"# Bull UP_TRI Stratification — Sonnet 4.5 Analysis\n\n"
        f"**Date:** 2026-05-02\n"
        f"**Model:** `claude-sonnet-4-5-20250929`\n\n"
        f"{response}\n"
    )
    print(f"Saved: {LLM_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
