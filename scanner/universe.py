import os
import csv

current_dir = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(
    current_dir, '..', 'data', 'fno_universe.csv')


def load_universe():
    symbols = []
    try:
        with open(CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = row.get('symbol','').strip()
                if sym:
                    symbols.append(sym)
    except Exception as e:
        print(f"Universe load error: {e}")
    return symbols


def get_sector_map():
    sector_map = {}
    try:
        with open(CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = row.get('symbol','').strip()
                sec = row.get('sector','Other').strip()
                if sym:
                    sector_map[sym] = sec
    except Exception as e:
        print(f"Sector map error: {e}")
    return sector_map


def get_grade_map():
    grade_map = {}
    try:
        with open(CSV_PATH, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym   = row.get('symbol','').strip()
                grade = row.get('grade','B').strip()
                if sym:
                    grade_map[sym] = grade
    except Exception as e:
        print(f"Grade map error: {e}")
    return grade_map
