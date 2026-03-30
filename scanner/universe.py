import requests
import pandas as pd
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import FO_UNIVERSE_URL, DATA_DIR

# ── CORRECTED TICKER SYMBOLS ──────────────────────
# BERGERPAINTS.NS  → BERGEPAINT.NS
# TATACHEMICALS.NS → TATACHEM.NS
# MCDOWELL-N.NS    → UBL.NS
# GMRINFRA.NS      → GMRAIRPORT.NS

FO_UNIVERSE = [
    # ── Bank / Finance ────────────────────────────
    "HDFCBANK.NS","ICICIBANK.NS","AXISBANK.NS",
    "KOTAKBANK.NS","SBIN.NS","INDUSINDBK.NS",
    "BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS",
    "PNB.NS","CANBK.NS","BANKBARODA.NS","AUBANK.NS",
    "RBLBANK.NS","BAJFINANCE.NS","BAJAJFINSV.NS",
    "HDFCLIFE.NS","SBILIFE.NS","ICICIPRULI.NS",
    "CHOLAFIN.NS","MUTHOOTFIN.NS","LICHSGFIN.NS",
    "RECLTD.NS","PFC.NS","MANAPPURAM.NS","ICICIGI.NS",
    # ── IT ───────────────────────────────────────
    "TCS.NS","INFY.NS","HCLTECH.NS","WIPRO.NS",
    "TECHM.NS","MPHASIS.NS","LTIM.NS","PERSISTENT.NS",
    "COFORGE.NS","OFSS.NS","KPITTECH.NS",
    # ── Auto ─────────────────────────────────────
    "MARUTI.NS","TATAMOTORS.NS","M&M.NS","BAJAJ-AUTO.NS",
    "HEROMOTOCO.NS","EICHERMOT.NS","ASHOKLEY.NS",
    "TVSMOTOR.NS","BALKRISIND.NS","MOTHERSON.NS",
    "BHARATFORG.NS","APOLLOTYRE.NS",
    # ── Pharma ───────────────────────────────────
    "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS",
    "AUROPHARMA.NS","DIVISLAB.NS","LUPIN.NS",
    "BIOCON.NS","ALKEM.NS","TORNTPHARM.NS",
    "IPCALAB.NS","GLENMARK.NS","LAURUSLABS.NS",
    # ── Metal ────────────────────────────────────
    "TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS",
    "VEDL.NS","COALINDIA.NS","NMDC.NS","SAIL.NS",
    "JINDALSTEL.NS","NATIONALUM.NS","HINDCOPPER.NS",
    # ── Energy / Power ───────────────────────────
    "RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS",
    "GAIL.NS","POWERGRID.NS","NTPC.NS","TATAPOWER.NS",
    "ADANIGREEN.NS","CESC.NS",
    # ── FMCG / Consumer ──────────────────────────
    "HINDUNILVR.NS","ITC.NS","BRITANNIA.NS",
    "DABUR.NS","MARICO.NS","GODREJCP.NS",
    "TATACONSUM.NS","TRENT.NS","TITAN.NS","DMART.NS",
    "ZOMATO.NS","PAGEIND.NS",
    # ── Cement / Infra ───────────────────────────
    "ULTRACEMCO.NS","AMBUJACEM.NS","ACC.NS",
    "SHREECEM.NS","LT.NS","ADANIPORTS.NS","DLF.NS",
    "GODREJPROP.NS","PHOENIXLTD.NS","PRESTIGE.NS",
    # ── Capital Goods ────────────────────────────
    "BHEL.NS","SIEMENS.NS","ABB.NS","HAVELLS.NS",
    "VOLTAS.NS","CUMMINSIND.NS","HAL.NS","BEL.NS",
    # ── Chemicals / Paint ────────────────────────
    "PIDILITIND.NS","DEEPAKNTR.NS","NAVINFLUOR.NS",
    "SRF.NS","ASIANPAINT.NS","BERGEPAINT.NS",
    "TATACHEM.NS","ALKYLAMINE.NS",
    # ── Others ───────────────────────────────────
    "DIXON.NS","BHARTIARTL.NS","IRCTC.NS",
    "CONCOR.NS","NAUKRI.NS","UBL.NS",
    "PVRINOX.NS","GMRAIRPORT.NS","IRFC.NS",
]

FO_UNIVERSE = list(dict.fromkeys(FO_UNIVERSE))

# ── SECTOR MAP ────────────────────────────────────
SECTOR_MAP = {}
for s in ["HDFCBANK.NS","ICICIBANK.NS","AXISBANK.NS",
          "KOTAKBANK.NS","SBIN.NS","INDUSINDBK.NS",
          "BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS",
          "PNB.NS","CANBK.NS","BANKBARODA.NS","AUBANK.NS",
          "RBLBANK.NS","BAJFINANCE.NS","BAJAJFINSV.NS",
          "HDFCLIFE.NS","SBILIFE.NS","ICICIPRULI.NS",
          "CHOLAFIN.NS","MUTHOOTFIN.NS","LICHSGFIN.NS",
          "RECLTD.NS","PFC.NS","MANAPPURAM.NS","ICICIGI.NS"]:
    SECTOR_MAP[s] = "Bank"
for s in ["TCS.NS","INFY.NS","HCLTECH.NS","WIPRO.NS",
          "TECHM.NS","MPHASIS.NS","LTIM.NS","PERSISTENT.NS",
          "COFORGE.NS","OFSS.NS","KPITTECH.NS"]:
    SECTOR_MAP[s] = "IT"
for s in ["MARUTI.NS","TATAMOTORS.NS","M&M.NS","BAJAJ-AUTO.NS",
          "HEROMOTOCO.NS","EICHERMOT.NS","ASHOKLEY.NS",
          "TVSMOTOR.NS","BALKRISIND.NS","MOTHERSON.NS",
          "BHARATFORG.NS","APOLLOTYRE.NS"]:
    SECTOR_MAP[s] = "Auto"
for s in ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS",
          "AUROPHARMA.NS","DIVISLAB.NS","LUPIN.NS",
          "BIOCON.NS","ALKEM.NS","TORNTPHARM.NS",
          "IPCALAB.NS","GLENMARK.NS","LAURUSLABS.NS"]:
    SECTOR_MAP[s] = "Pharma"
for s in ["TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS",
          "VEDL.NS","COALINDIA.NS","NMDC.NS","SAIL.NS",
          "JINDALSTEL.NS","NATIONALUM.NS","HINDCOPPER.NS"]:
    SECTOR_MAP[s] = "Metal"
for s in ["RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS",
          "GAIL.NS","POWERGRID.NS","NTPC.NS","TATAPOWER.NS",
          "ADANIGREEN.NS","CESC.NS"]:
    SECTOR_MAP[s] = "Energy"
for s in ["HINDUNILVR.NS","ITC.NS","BRITANNIA.NS",
          "DABUR.NS","MARICO.NS","GODREJCP.NS",
          "TATACONSUM.NS","TRENT.NS","TITAN.NS",
          "DMART.NS","ZOMATO.NS","PAGEIND.NS"]:
    SECTOR_MAP[s] = "FMCG"
for s in ["ULTRACEMCO.NS","AMBUJACEM.NS","ACC.NS",
          "SHREECEM.NS","LT.NS","ADANIPORTS.NS","DLF.NS",
          "GODREJPROP.NS","PHOENIXLTD.NS","PRESTIGE.NS"]:
    SECTOR_MAP[s] = "Infra"
for s in ["BHEL.NS","SIEMENS.NS","ABB.NS","HAVELLS.NS",
          "VOLTAS.NS","CUMMINSIND.NS","HAL.NS","BEL.NS"]:
    SECTOR_MAP[s] = "CapGoods"
for s in ["PIDILITIND.NS","DEEPAKNTR.NS","NAVINFLUOR.NS",
          "SRF.NS","ASIANPAINT.NS","BERGEPAINT.NS",
          "TATACHEM.NS","ALKYLAMINE.NS"]:
    SECTOR_MAP[s] = "Chem"
for s in ["DIXON.NS","BHARTIARTL.NS","IRCTC.NS",
          "CONCOR.NS","NAUKRI.NS","UBL.NS",
          "PVRINOX.NS","GMRAIRPORT.NS","IRFC.NS"]:
    SECTOR_MAP[s] = "Other"

# ── GRADE A STOCKS ────────────────────────────────
GRADE_A = {
    "PRESTIGE.NS","JINDALSTEL.NS","KPITTECH.NS",
    "DLF.NS","HINDALCO.NS","DIXON.NS",
    "CANBK.NS","TITAN.NS","TATASTEEL.NS",
    "JSWSTEEL.NS","SBIN.NS","AXISBANK.NS",
}

def load_universe():
    """Load from hardcoded list — always reliable"""
    return FO_UNIVERSE

def get_sector_map():
    return SECTOR_MAP

def get_grade_map():
    return {sym: ('A' if sym in GRADE_A else 'B')
            for sym in FO_UNIVERSE}
