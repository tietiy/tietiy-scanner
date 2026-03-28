import os

# ── TELEGRAM ──────────────────────────────────────
TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# ── GITHUB ────────────────────────────────────────
GH_TOKEN    = os.environ.get('GH_TOKEN', '')
GH_REPO     = 'tietiy/tietiy-scanner'
GH_BRANCH   = 'main'

# ── CAPITAL & RISK ────────────────────────────────
CAPITAL          = 100000
RISK_PCT_HIGH    = 0.015   # 1.5% for score 8-10
RISK_PCT_NORMAL  = 0.010   # 1.0% for score 5-7
RISK_PCT_LOW     = 0.005   # 0.5% for score 3-4

# ── SIGNAL PARAMETERS (scanner-exact) ────────────
PIVOT_LOOKBACK   = 10
ATR_PERIOD       = 14
EMA_FAST         = 20
EMA_MID          = 50
EMA_SLOW         = 200
ZONE_ATR         = 0.50
SMC_COOLDOWN     = 5
STOP_MULT        = 1.0
EXIT_BARS        = 6

# ── BULL PROXY THRESHOLDS (corrected) ────────────
BP_CLOSE_POS_MIN  = 0.60
BP_LOWER_WICK_MIN = 0.40

# ── SCORING WEIGHTS (from backtest) ──────────────
SCORE_AGE_0       = 3
SCORE_AGE_1       = 1
SCORE_BEAR_BONUS  = 2
SCORE_BULL_CHOPPY = 1
SCORE_VOL_CONFIRM = 1
SCORE_SEC_LEADING = 1
SCORE_RS_STRONG   = 1
SCORE_GRADE_A     = 1

# ── GRADE A STOCKS (from backtest top performers) ─
GRADE_A_STOCKS = [
    'PRESTIGE', 'JINDALSTEL', 'KPITTECH', 'DLF',
    'HINDALCO', 'DIXON', 'CANBK', 'TITAN',
    'MANAPPURAM', 'COCHINSHIP', 'SRF', 'BHEL',
    'SAIL', 'LICHSGFIN', 'HAL', 'BANDHANBNK',
    'BAJFINANCE', 'RBLBANK', 'PFC', 'COFORGE',
    'RECLTD', 'MARUTI', 'TATASTEEL',
]

# ── EXIT RULES (from backtest) ────────────────────
# UP_TRI Bear → Target2x | All others → Day6
EXIT_UPTRI_BEAR  = 'Target2x'
EXIT_DEFAULT     = 'Day6'

# ── ALERT THRESHOLDS ──────────────────────────────
LARGE_MOVE_ATR_MULT  = 2.0   # alert if move > 2x ATR
STOP_CHECK_INTERVAL  = 30    # minutes

# ── PATHS ─────────────────────────────────────────
DATA_DIR    = 'data'
OUTPUT_DIR  = 'output'
JOURNAL_DIR = 'journal'

# ── NSE UNIVERSE SOURCE ───────────────────────────
FO_UNIVERSE_URL = (
    'https://raw.githubusercontent.com/'
    'tietiy/tietiy-scanner/main/data/fo_universe.csv'
)
