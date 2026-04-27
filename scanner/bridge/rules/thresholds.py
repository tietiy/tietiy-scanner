"""
TIE TIY Bridge thresholds — central source of truth for all numeric constants.

Principle: never hardcode a threshold in any other bridge file. Always import from here.
Changing a value is a single edit. All modules pick up the new value on next compose.

See doc/bridge_design_v1.md for rationale on each threshold.
"""

# === Bucket assignment thresholds (Gate 4 evidence consensus) ===
COHORT_STRONG_N = 10              # Min n for "strong cohort" classification
COHORT_STRONG_WR = 0.75           # Min WR for strong cohort
COHORT_MODERATE_N = 5             # Min n for "moderate cohort" classification
COHORT_MODERATE_WR = 0.65         # Min WR for moderate cohort
COHORT_THIN_FALLBACK_N = 5        # Below this, only WATCH if sector_recent + regime_baseline supportive
COHORT_THIN_FALLBACK_SECTOR_WR = 0.70  # Min sector_recent_30d WR for thin-fallback WATCH (companion to COHORT_THIN_FALLBACK_N)
COHORT_THIN_FALLBACK_REGIME_WR = 0.65  # Min regime_baseline WR for thin-fallback WATCH (companion to COHORT_THIN_FALLBACK_N)
COHORT_MODERATE_SECTOR_WR = 0.65  # Min sector_recent_30d WR for moderate-cohort qualification

# === Validity gate (Gate 2) ===
VALIDITY_MIN_RR = 1.5             # Minimum acceptable risk:reward ratio
VALIDITY_MAX_AGE_DAYS_DEFAULT = 1  # Most signals: age 0-1 valid
VALIDITY_MAX_AGE_DOWN_TRI = 0     # DOWN_TRI: only age 0 (per backtest finding)

# === Boost pattern tier definitions ===
BOOST_TIER_A_MIN_N = 15           # Tier A boost requires sample size
BOOST_TIER_A_MIN_WR = 0.95        # Tier A requires near-perfect WR
BOOST_TIER_B_MIN_N = 10           # Tier B threshold for sample
BOOST_TIER_B_MIN_WR = 0.80        # Tier B WR floor

# === Gap caveat (Path C, locked 2026-04-26) ===
GAP_CAVEAT_THRESHOLD_PCT = 2.0    # Gap > this % adverse → reconsider entry
GAP_CAVEAT_DIRECTION = "adverse"  # For LONG: above scan_price. For SHORT: below.

# === Sector recency lookback ===
SECTOR_RECENT_WINDOW_DAYS = 30
SECTOR_RECENT_MIN_N = 5           # Min signals in window for stat to be meaningful

# === Stock-specific recency ===
STOCK_RECENCY_LOOKBACK_DAYS = 30

# === Score bucket analysis ===
SCORE_BUCKET_MIN_N = 8            # Need at least 8 signals at same score level

# === Regime baseline ===
REGIME_BASELINE_MIN_N = 20        # Need 20 signals to establish regime baseline

# === Contra-tracker thresholds (locked 2026-04-26 §7.2) ===
CONTRA_REVIEW_N = 30              # n_resolved threshold for review eligibility
CONTRA_REVIEW_WR = 0.80           # WR threshold for promotion review
CONTRA_PROMOTION_TAKE_SMALL_DAYS = 30  # First 30 days post-approval = TAKE_SMALL only
CONTRA_PROMOTION_TAKE_FULL_WR = 0.75   # Steady-state WR to graduate to TAKE_FULL
CONTRA_REVERT_WINDOW = 10         # Rolling window size for revert check
CONTRA_REVERT_WR = 0.65           # WR below this in window → auto-revert
CONTRA_PROPOSAL_AUTO_EXPIRE_DAYS = 7   # Re-propose after this if not acted on
CONTRA_REJECT_LIMIT = 2           # 2 rejections → INSUFFICIENT

# === Bridge state retention ===
BRIDGE_STATE_HISTORY_RETENTION_DAYS = 30  # Keep daily history files for 30 days
BRIDGE_STATE_BACKUP_AFTER_DAYS = 30       # Move to backups/ after this many days

# === Compose performance ===
COMPOSE_MAX_DURATION_SEC = 30     # Composer should complete within 30 sec; warn if exceeded
QUERY_MAX_DURATION_MS = 200       # Each query plugin should run < 200ms; log if exceeded

# === Display priorities (used in display_hints.py) ===
PRIORITY_TAKE_FULL = 95
PRIORITY_TAKE_SMALL = 80
PRIORITY_WATCH = 50
PRIORITY_SKIP = 10

# === Schema versions ===
SDR_SCHEMA_VERSION = 1
BRIDGE_STATE_SCHEMA_VERSION = 1
QUERY_PROPOSALS_SCHEMA_VERSION = 1
CONTRA_BLOCK_SCHEMA_VERSION = 1
