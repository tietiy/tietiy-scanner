"""
Live signal feature joiner — match resolved live signals from
`output/signal_history.json` to the Phase-1 enriched_signals.parquet,
producing a unified DataFrame with 114 features attached to live W/L/F
outcomes.

Phase 2 prereq per `lab/COMBINATION_ENGINE_PLAN.md`. NO production scanner
modifications. Lab-only.

Usage:
    from live_feature_joiner import LiveFeatureJoiner
    j = LiveFeatureJoiner()
    enriched_live = j.build()
    enriched_live.to_parquet("lab/output/live_signals_with_features.parquet")
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_REPO_ROOT = _LAB_ROOT.parent

sys.path.insert(0, str(_HERE))
from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import (  # noqa: E402
    FeatureExtractor, _FEAT_PREFIX, _EXPECTED_FEATURE_COUNT,
)

# ── Constants ─────────────────────────────────────────────────────────
DEFAULT_LIVE_PATH = _REPO_ROOT / "output" / "signal_history.json"
DEFAULT_ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
DEFAULT_OUTPUT_PATH = _LAB_ROOT / "output" / "live_signals_with_features.parquet"

# Outcomes considered "resolved" for W/L analysis
WIN_OUTCOMES = ("DAY6_WIN", "TARGET_HIT")
LOSS_OUTCOMES = ("DAY6_LOSS", "STOP_HIT")
FLAT_OUTCOMES = ("DAY6_FLAT",)
RESOLVED_OUTCOMES = WIN_OUTCOMES + LOSS_OUTCOMES + FLAT_OUTCOMES


def _wlf_label(outcome: str) -> str:
    if outcome in WIN_OUTCOMES:
        return "W"
    if outcome in LOSS_OUTCOMES:
        return "L"
    if outcome in FLAT_OUTCOMES:
        return "F"
    return "?"  # not resolved


@dataclass
class JoinReport:
    """Diagnostic from a build() run."""
    total_live_records: int = 0
    total_resolved: int = 0
    total_after_dedup: int = 0
    total_dedup_dropped: int = 0
    total_matched_to_enriched: int = 0
    total_orphans: int = 0
    total_orphans_extracted_fresh: int = 0
    total_orphans_unrecoverable: int = 0
    label_distribution: dict = field(default_factory=dict)
    cohort_n: dict = field(default_factory=dict)


class LiveFeatureJoiner:
    """Builds enriched live-signal DataFrame for Phase 2 importance analysis."""

    def __init__(self,
                 live_path: Path = DEFAULT_LIVE_PATH,
                 enriched_path: Path = DEFAULT_ENRICHED_PATH):
        self.live_path = Path(live_path)
        self.enriched_path = Path(enriched_path)
        self._registry: Optional[FeatureRegistry] = None
        self._extractor: Optional[FeatureExtractor] = None
        self.report = JoinReport()

    def build(self) -> pd.DataFrame:
        """Run the full join pipeline. Returns enriched live DataFrame."""
        live = self._load_resolved_live()
        live_dedup = self._dedupe(live)
        enriched = self._load_enriched()
        joined = self._join(live_dedup, enriched)
        self._populate_report(live_dedup, joined)
        return joined

    # ── Pipeline steps ────────────────────────────────────────────────

    def _load_resolved_live(self) -> pd.DataFrame:
        if not self.live_path.exists():
            raise FileNotFoundError(f"signal_history not found: {self.live_path}")
        with open(self.live_path) as fh:
            data = json.load(fh)
        records = data["history"] if isinstance(data, dict) else data
        df = pd.DataFrame(records)
        self.report.total_live_records = len(df)
        df = df[df["outcome"].isin(RESOLVED_OUTCOMES)].copy()
        self.report.total_resolved = len(df)
        df["wlf"] = df["outcome"].apply(_wlf_label)
        df["date"] = pd.to_datetime(df["date"])
        return df

    @staticmethod
    def _dedupe(live: pd.DataFrame) -> pd.DataFrame:
        """Drop -REJ duplicates; keep canonical record per (date, symbol, signal)."""
        # Sort: rows whose id does NOT end with '-REJ' come first
        live = live.copy()
        live["_is_rej"] = live["id"].str.endswith("-REJ", na=False)
        live = live.sort_values(["date", "symbol", "signal", "_is_rej"])
        deduped = live.drop_duplicates(
            subset=["date", "symbol", "signal"], keep="first")
        deduped = deduped.drop(columns=["_is_rej"])
        return deduped.reset_index(drop=True)

    def _load_enriched(self) -> pd.DataFrame:
        if not self.enriched_path.exists():
            raise FileNotFoundError(
                f"enriched parquet not found: {self.enriched_path}")
        enriched = pd.read_parquet(self.enriched_path)
        enriched["scan_date"] = pd.to_datetime(enriched["scan_date"])
        return enriched

    def _join(self, live: pd.DataFrame,
                enriched: pd.DataFrame) -> pd.DataFrame:
        """Match live → enriched on (date/scan_date, symbol, signal).
        For orphans (no enriched match), extract features fresh via
        FeatureExtractor against the stock parquet."""
        feat_cols = [c for c in enriched.columns
                       if c.startswith(_FEAT_PREFIX)
                       and c != _FEAT_PREFIX + "_extractor_error"]

        # Left-join attempt
        live_keys = live[["date", "symbol", "signal"]].copy()
        live_keys.columns = ["scan_date", "symbol", "signal"]
        merged = live.merge(
            enriched[["scan_date", "symbol", "signal"] + feat_cols],
            left_on=["date", "symbol", "signal"],
            right_on=["scan_date", "symbol", "signal"],
            how="left",
            suffixes=("", "_enr"),
        )
        # Drop the duplicated scan_date column from enriched side
        if "scan_date" in merged.columns:
            merged = merged.drop(columns=["scan_date"])

        # Identify orphans: rows where ALL feat_* values are NaN (no enriched match)
        orphan_mask = merged[feat_cols].isna().all(axis=1)
        n_orphans = int(orphan_mask.sum())
        self.report.total_matched_to_enriched = len(merged) - n_orphans
        self.report.total_orphans = n_orphans

        if n_orphans > 0:
            # Re-extract features for orphans via FeatureExtractor
            orphan_idx = merged.index[orphan_mask].tolist()
            self._extract_for_orphans(merged, orphan_idx, feat_cols)

        return merged

    def _extract_for_orphans(self, df: pd.DataFrame,
                                orphan_idx: list,
                                feat_cols: list) -> None:
        """Run FeatureExtractor on orphan signals; fill in feat_* columns in place."""
        if self._registry is None:
            self._registry = FeatureRegistry.load_all()
        if self._extractor is None:
            self._extractor = FeatureExtractor(registry=self._registry)

        cache_dir = self._extractor.cache_dir
        feat_ids = sorted(s.feature_id for s in self._registry.list_all())

        # Build pseudo signal-rows that look like enriched_signals format
        n_extracted = 0
        n_unrecov = 0
        for idx in orphan_idx:
            row = df.loc[idx]
            symbol = row["symbol"]
            scan_date = pd.Timestamp(row["date"])
            sym_path = cache_dir / f"{symbol.replace('.NS', '_NS')}.parquet"
            if not sym_path.exists():
                n_unrecov += 1
                continue
            try:
                stock_df = pd.read_parquet(sym_path)
                stock_df.index = pd.to_datetime(stock_df.index)
                stock_df = stock_df.sort_index().dropna(subset=["Close"])
                # Build minimal signal_row mirroring enriched_signals fields the
                # extractor reads: scan_date, symbol, sector, direction,
                # regime, regime_score, sec_mom, rs_q, vol_q
                pseudo = pd.Series({
                    "scan_date": scan_date,
                    "symbol": symbol,
                    "sector": row.get("sector", "Other"),
                    "direction": row.get("direction", "LONG"),
                    "regime": row.get("regime", "Choppy"),
                    "regime_score": row.get("regime_score", 0),
                    "sec_mom": row.get("sec_mom", "Neutral"),
                    "rs_q": row.get("rs_q", "Neutral"),
                    "vol_q": row.get("vol_q", "Average"),
                })
                feats = self._extractor.extract_single(pseudo, stock_df)
                for fid in feat_ids:
                    df.at[idx, f"{_FEAT_PREFIX}{fid}"] = feats.get(fid, np.nan)
                n_extracted += 1
            except Exception as exc:  # noqa: BLE001
                n_unrecov += 1
                print(f"  WARN: orphan {symbol} {scan_date.date()} extract "
                      f"failed: {exc}", file=sys.stderr)

        self.report.total_orphans_extracted_fresh = n_extracted
        self.report.total_orphans_unrecoverable = n_unrecov

    def _populate_report(self, live_dedup: pd.DataFrame,
                            joined: pd.DataFrame) -> None:
        self.report.total_after_dedup = len(live_dedup)
        self.report.total_dedup_dropped = (
            self.report.total_resolved - self.report.total_after_dedup)
        self.report.label_distribution = (
            joined["wlf"].value_counts().to_dict())
        self.report.cohort_n = {
            "universal": len(joined),
            "Bear": int((joined["regime"] == "Bear").sum()),
            "Bull": int((joined["regime"] == "Bull").sum()),
            "Choppy": int((joined["regime"] == "Choppy").sum()),
            "UP_TRI": int((joined["signal"] == "UP_TRI").sum()),
            "DOWN_TRI": int((joined["signal"] == "DOWN_TRI").sum()),
            "BULL_PROXY": int((joined["signal"] == "BULL_PROXY").sum()),
        }

    # ── Convenience CLI ───────────────────────────────────────────────

    def print_report(self) -> None:
        r = self.report
        print("─" * 72)
        print("LiveFeatureJoiner report")
        print("─" * 72)
        print(f"signal_history total records: {r.total_live_records}")
        print(f"  resolved (W/L/F outcomes): {r.total_resolved}")
        print(f"  after dedup (drop -REJ dups): {r.total_after_dedup} "
              f"({r.total_dedup_dropped} dropped)")
        print(f"  matched to enriched_signals: {r.total_matched_to_enriched}")
        print(f"  orphans (no enriched match): {r.total_orphans}")
        print(f"    extracted fresh: {r.total_orphans_extracted_fresh}")
        print(f"    unrecoverable: {r.total_orphans_unrecoverable}")
        print()
        print(f"W/L/F label distribution: {r.label_distribution}")
        wlf = r.label_distribution
        nw = wlf.get("W", 0); nl = wlf.get("L", 0)
        wr = nw / (nw + nl) if (nw + nl) > 0 else float("nan")
        print(f"WR (excl F): {wr:.1%}  (n_w={nw}, n_l={nl})")
        print()
        print("Cohort sizes:")
        for k, v in r.cohort_n.items():
            print(f"  {k}: {v}")


def main():
    j = LiveFeatureJoiner()
    out = j.build()
    j.print_report()
    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(DEFAULT_OUTPUT_PATH, index=False)
    size_mb = DEFAULT_OUTPUT_PATH.stat().st_size / 1024 / 1024
    print(f"\nSaved: {DEFAULT_OUTPUT_PATH} ({size_mb:.2f} MB, "
          f"{out.shape[0]} rows × {out.shape[1]} cols)")


if __name__ == "__main__":
    main()
