import os

TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
GH_TOKEN         = os.environ.get('GH_TOKEN', '')
GH_REPO          = 'tietiy/tietiy-scanner'
GH_BRANCH        = 'main'

CAPITAL          = 100_000
RISK_PCT_HIGH    = 0.05
RISK_PCT_NORMAL  = 0.03
RISK_PCT_LOW     = 0.01

PIVOT_LOOKBACK   = 10
ATR_PERIOD       = 14
EMA_FAST         = 20
EMA_MID          = 50
EMA_SLOW         = 200
ZONE_ATR         = 0.50
SMC_COOLDOWN     = 5
STOP_MULT        = 1.0
EXIT_BARS        = 6

# === prop_005: target multiplier (live) + shadow track ===
# Live target distance = TARGET_R_MULTIPLE × abs(entry - stop).
# Shadow target distance = TARGET_R_MULTIPLE_SHADOW × abs(entry - stop),
# computed alongside live for parallel-track measurement. Live trade
# decisions use TARGET_R_MULTIPLE only; shadow is metadata for analyst
# comparison post-resolution. shadow_target / shadow_outcome /
# shadow_r_multiple fields are forward-only (V6): pre-prop_005 records
# do not carry them; recover_stuck_signals does not backfill.
#
# Why 3.0 (not 2.5, not 4.0):
# - 2.5 is too close to live (2.0) to detect a meaningful difference at
#   the sample sizes we'll accumulate over a quarter
# - 4.0 is too aggressive given the 6-day hold — most signals never
#   reach 4× risk, so shadow_TARGET_HIT events become near-zero and the
#   shadow cohort can't be statistically compared
# - 3.0 (50% wider) is the natural "next test" value
TARGET_R_MULTIPLE        = 2.0
TARGET_R_MULTIPLE_SHADOW = 3.0

BP_CLOSE_POS_MIN  = 0.60
BP_LOWER_WICK_MIN = 0.40

SCORE_AGE_0       = 3
SCORE_AGE_1       = 2
SCORE_BEAR_BONUS  = 3
SCORE_BULL_CHOPPY = 1
SCORE_VOL_CONFIRM = 1
SCORE_SEC_LEADING = 1
SCORE_RS_STRONG   = 1
SCORE_GRADE_A     = 1

EXIT_UPTRI_BEAR  = 'Target2x'
EXIT_DEFAULT     = 'Day6'

# ── PRICE FEED ────────────────────────────────────────
# F3: Plug-in price source abstraction
# Switch here only — no other file changes needed
# Options: "yfinance" | "5paisa"
PRICE_SOURCE = os.environ.get('PRICE_SOURCE', 'yfinance')

# ── ABSOLUTE PATHS ────────────────────────────────────
_BASE      = os.path.dirname(
                 os.path.dirname(
                     os.path.abspath(__file__)))

DATA_DIR    = os.path.join(_BASE, 'data')
OUTPUT_DIR  = os.path.join(_BASE, 'output')

FO_UNIVERSE_URL = ''
