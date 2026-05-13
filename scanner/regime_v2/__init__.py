"""
TIE TIY regime classifier v2 — 5-state rule-based.

Design: doc/regime_v2_design/MASTER_DESIGN.md
States: Bull / Bull-Recovery / Choppy / Bear-Recovery / Bear
"""
from .classifier import classify_regime
from .features import compute_features
from .io import load_ohlcv, write_regime_state, write_regime_features

__all__ = [
    "classify_regime",
    "compute_features",
    "load_ohlcv",
    "write_regime_state",
    "write_regime_features",
]
