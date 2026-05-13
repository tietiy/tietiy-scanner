"""Validation 2 — Visual Sanity Check.

Produces 4 charts:
  - sanity_plot_60d.png — last 60 trading days
  - sanity_plot_365d.png — last 365 calendar days
  - sanity_plot_full_2010_2026.png — full historical window
  - sanity_plot_v1_vs_v2_90d.png — V1 vs V2 side-by-side last 90 days
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd


STATE_COLORS = {
    "BULL": "#2ecc71",          # green
    "BULL_RECOVERY": "#aed581",  # light green
    "CHOPPY": "#bdc3c7",         # grey
    "BEAR_RECOVERY": "#f4a261",  # orange
    "BEAR": "#e74c3c",           # red
}


def plot_with_regime(ax, prices: pd.Series, states: pd.Series, title: str):
    # Plot Nifty price line
    ax.plot(prices.index, prices.values, color="#1c2833", linewidth=1.0)
    # Color bands for each state
    if not states.empty:
        # Group consecutive same-state runs
        prev_state = None
        run_start = None
        for ts, state in states.items():
            if state != prev_state:
                if prev_state is not None and run_start is not None:
                    ax.axvspan(run_start, ts, color=STATE_COLORS.get(prev_state, "#cccccc"), alpha=0.25)
                run_start = ts
                prev_state = state
        # Close final run
        if prev_state is not None and run_start is not None:
            ax.axvspan(run_start, states.index[-1], color=STATE_COLORS.get(prev_state, "#cccccc"), alpha=0.25)
    ax.set_title(title)
    ax.set_ylabel("Nifty Close")
    ax.grid(alpha=0.2)


def state_legend():
    return [mpatches.Patch(color=c, alpha=0.4, label=s) for s, c in STATE_COLORS.items()]


def run(out_dir: str = "doc/regime_v2_design") -> dict:
    os.makedirs(out_dir, exist_ok=True)
    v2 = pd.read_parquet("output/regime_v2/regime_historical.parquet")
    v2.index = pd.to_datetime(v2.index)
    nifty = pd.read_parquet("data/historical/nifty.parquet")
    nifty.index = pd.to_datetime(nifty.index)

    aligned = v2.join(nifty[["Close"]], how="left")

    # 60-day plot
    last_60 = aligned.iloc[-60:]
    fig, ax = plt.subplots(figsize=(14, 5))
    plot_with_regime(ax, last_60["Close"], last_60["state"], "Nifty + V2 Regime — Last 60 Trading Days")
    ax.legend(handles=state_legend(), loc="upper left", ncol=5, fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "sanity_plot_60d.png"), dpi=100)
    plt.close(fig)

    # 365-day plot
    last_365 = aligned.loc[aligned.index >= aligned.index.max() - pd.Timedelta(days=365)]
    fig, ax = plt.subplots(figsize=(14, 5))
    plot_with_regime(ax, last_365["Close"], last_365["state"], "Nifty + V2 Regime — Last 365 Days")
    ax.legend(handles=state_legend(), loc="upper left", ncol=5, fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "sanity_plot_365d.png"), dpi=100)
    plt.close(fig)

    # Full historical
    fig, ax = plt.subplots(figsize=(20, 6))
    plot_with_regime(ax, aligned["Close"], aligned["state"], "Nifty + V2 Regime — Full History 2011-2026")
    ax.legend(handles=state_legend(), loc="upper left", ncol=5, fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "sanity_plot_full_2010_2026.png"), dpi=100)
    plt.close(fig)

    # V1 vs V2 side-by-side last 90 days
    v1_baseline = pd.read_parquet("data/historical/regime_history_v1_baseline.parquet")
    v1_baseline.index = pd.to_datetime(v1_baseline.index)
    last_90 = aligned.loc[aligned.index >= aligned.index.max() - pd.Timedelta(days=90)]
    last_90_v1 = v1_baseline.loc[v1_baseline.index.isin(last_90.index)]

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    plot_with_regime(axes[0], last_90["Close"], last_90["state"], "V2 — Last 90 Days")
    axes[0].legend(handles=state_legend(), loc="upper left", ncol=5, fontsize=8)
    v1_states_normalized = last_90_v1["regime"].map(
        {"Bull": "BULL", "Bear": "BEAR", "Choppy": "CHOPPY"}).fillna("CHOPPY")
    plot_with_regime(axes[1], last_90["Close"], v1_states_normalized, "V1 (current production) — Last 90 Days")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "sanity_plot_v1_vs_v2_90d.png"), dpi=100)
    plt.close(fig)

    files = [
        "sanity_plot_60d.png",
        "sanity_plot_365d.png",
        "sanity_plot_full_2010_2026.png",
        "sanity_plot_v1_vs_v2_90d.png",
    ]
    print(f"[V2 visual sanity] generated {len(files)} charts in {out_dir}/")
    for f in files:
        path = os.path.join(out_dir, f)
        size_kb = os.path.getsize(path) / 1024 if os.path.exists(path) else 0
        print(f"  - {f} ({size_kb:.0f} KB)")
    return {"charts": files, "READY_FOR_REVIEW": True}


if __name__ == "__main__":
    run()
