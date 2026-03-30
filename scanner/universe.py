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
