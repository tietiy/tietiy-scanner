import requests
import pandas as pd
from datetime import date
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import FO_UNIVERSE_URL, DATA_DIR

def load_universe():
    """Load F&O universe from GitHub CSV"""
    try:
        df = pd.read_csv(FO_UNIVERSE_URL, header=None, names=['symbol'])
        symbols = df['symbol'].str.strip().tolist()
        symbols = [s for s in symbols if s and not s.startswith('#')]
        return symbols
    except Exception as e:
        print(f"Failed to load universe from URL: {e}")
        return load_universe_local()

def load_universe_local():
    """Fallback — load from local file"""
    path = f"{DATA_DIR}/fo_universe.csv"
    try:
        df = pd.read_csv(path, header=None, names=['symbol'])
        return df['symbol'].str.strip().tolist()
    except Exception as e:
        print(f"Failed to load local universe: {e}")
        return []

def get_sector_map():
    """Returns dict mapping symbol to sector"""
    sector_map = {}
    bank = ["HDFCBANK.NS","ICICIBANK.NS","AXISBANK.NS","KOTAKBANK.NS",
            "SBIN.NS","INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS",
            "IDFCFIRSTB.NS","PNB.NS","CANBK.NS","BANKBARODA.NS",
            "AUBANK.NS","RBLBANK.NS","BAJFINANCE.NS","BAJAJFINSV.NS",
            "HDFCLIFE.NS","SBILIFE.NS","ICICIPRULI.NS","CHOLAFIN.NS",
            "MUTHOOTFIN.NS","LICHSGFIN.NS","RECLTD.NS","PFC.NS",
            "MANAPPURAM.NS","ICICIGI.NS"]
    it = ["TCS.NS","INFY.NS","HCLTECH.NS","WIPRO.NS","TECHM.NS",
          "MPHASIS.NS","LTIM.NS","PERSISTENT.NS","COFORGE.NS",
          "OFSS.NS","LTTS.NS","KPITTECH.NS"]
    auto = ["MARUTI.NS","TATAMOTORS.NS","M&M.NS","BAJAJ-AUTO.NS",
            "HEROMOTOCO.NS","EICHERMOT.NS","ASHOKLEY.NS","TVSMOTOR.NS",
            "BALKRISIND.NS","MOTHERSON.NS","BHARATFORG.NS","APOLLOTYRE.NS"]
    pharma = ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","AUROPHARMA.NS",
              "DIVISLAB.NS","LUPIN.NS","BIOCON.NS","ALKEM.NS",
              "TORNTPHARM.NS","IPCALAB.NS","GLENMARK.NS","LAURUSLABS.NS"]
    metal = ["TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","VEDL.NS",
             "COALINDIA.NS","NMDC.NS","SAIL.NS","JINDALSTEL.NS",
             "NATIONALUM.NS","HINDCOPPER.NS"]
    energy = ["RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS","GAIL.NS",
              "POWERGRID.NS","NTPC.NS","TATAPOWER.NS","ADANIGREEN.NS",
              "CESC.NS"]
    fmcg = ["HINDUNILVR.NS","ITC.NS","BRITANNIA.NS","DABUR.NS",
            "MARICO.NS","GODREJCP.NS","TATACONSUM.NS","TRENT.NS",
            "TITAN.NS","DMART.NS","ZOMATO.NS","PAGEIND.NS"]
    infra = ["ULTRACEMCO.NS","AMBUJACEM.NS","ACC.NS","SHREECEM.NS",
             "LT.NS","ADANIPORTS.NS","DLF.NS","GODREJPROP.NS",
             "PHOENIXLTD.NS","PRESTIGE.NS","CONCOR.NS","IRCTC.NS",
             "GMRINFRA.NS","IRFC.NS"]
    capgoods = ["BHEL.NS","SIEMENS.NS","ABB.NS","HAVELLS.NS",
                "VOLTAS.NS","CUMMINSIND.NS","HAL.NS","BEL.NS",
                "COCHINSHIP.NS","GRSE.NS"]
    chemical = ["PIDILITIND.NS","AARTIIND.NS","DEEPAKNTR.NS",
                "NAVINFLUOR.NS","SRF.NS","ASIANPAINT.NS",
                "BERGERPAINTS.NS","TATACHEMICALS.NS",
                "ALKYLAMINE.NS","VINATIORGA.NS"]
    consumer = ["DIXON.NS","AMBER.NS","VGUARD.NS","CROMPTON.NS",
                "WHIRLPOOL.NS","BATAINDIA.NS"]
    other = ["BHARTIARTL.NS","NAUKRI.NS","MCDOWELL-N.NS",
             "PVRINOX.NS"]

    for s in bank:     sector_map[s] = "Bank"
    for s in it:       sector_map[s] = "IT"
    for s in auto:     sector_map[s] = "Auto"
    for s in pharma:   sector_map[s] = "Pharma"
    for s in metal:    sector_map[s] = "Metal"
    for s in energy:   sector_map[s] = "Energy"
    for s in fmcg:     sector_map[s] = "FMCG"
    for s in infra:    sector_map[s] = "Infra"
    for s in capgoods: sector_map[s] = "CapGoods"
    for s in chemical: sector_map[s] = "Chemical"
    for s in consumer: sector_map[s] = "Consumer"
    for s in other:    sector_map[s] = "Other"
    return sector_map

def get_grade_map():
    """Returns Grade A stocks from backtest"""
    from config import GRADE_A_STOCKS
    grade_map = {}
    universe = load_universe()
    for sym in universe:
        name = sym.replace('.NS','')
        if name in GRADE_A_STOCKS:
            grade_map[sym] = 'A'
        else:
            grade_map[sym] = 'B'
    return grade_map

if __name__ == '__main__':
    symbols = load_universe()
    print(f"Universe loaded: {len(symbols)} stocks")
    print(f"First 5: {symbols[:5]}")
    sector_map = get_sector_map()
    print(f"Sectors mapped: {len(sector_map)}")
