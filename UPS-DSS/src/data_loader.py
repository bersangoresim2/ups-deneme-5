import pandas as pd

def load_data(file="data/denemeDATA.xlsx"):
    print(">>> ENTERED DATA LOADER", flush=True)
    print(">>> FILE:", file, flush=True)

    try:
        print(">>> EXCELFILE STARTING", flush=True)
        xls = pd.ExcelFile(file, engine="openpyxl")
        print(">>> EXCELFILE FINISHED", flush=True)
    except Exception as e:
        raise FileNotFoundError(f"Excel file could not be opened: {e}")

    required_sheets = ["S", "K", "I", "O", "d", "dh", "p", "ph", "c", "q", "tf", "af", "v", "apc"]
    missing_sheets = [sheet for sheet in required_sheets if sheet not in xls.sheet_names]

    if missing_sheets:
        raise ValueError(f"Missing sheet(s) in Excel file: {missing_sheets}")

    print(">>> SHEETS OK", flush=True)

    scenarios = xls.parse("S")
    print(">>> S OK", flush=True)

    vehicles = xls.parse("K")
    print(">>> K OK", flush=True)

    customers = xls.parse("I")
    print(">>> I OK", flush=True)

    orders = xls.parse("O")
    print(">>> O OK", flush=True)

    d = xls.parse("d")
    print(">>> d OK", flush=True)

    dh = xls.parse("dh")
    print(">>> dh OK", flush=True)

    p = xls.parse("p")
    print(">>> p OK", flush=True)

    ph = xls.parse("ph")
    print(">>> ph OK", flush=True)

    c = xls.parse("c")
    print(">>> c OK", flush=True)

    q = xls.parse("q")
    print(">>> q OK", flush=True)

    tf = xls.parse("tf")
    print(">>> tf OK", flush=True)

    af = xls.parse("af")
    print(">>> af OK", flush=True)

    v = xls.parse("v")
    print(">>> v OK", flush=True)

    apc = xls.parse("apc")
    print(">>> apc OK", flush=True)

    print(">>> DATA LOADING FINISHED INSIDE DATA_LOADER", flush=True)

    return {
        "S": scenarios,
        "K": vehicles,
        "I": customers,
        "O": orders,
        "d": d,
        "dh": dh,
        "p": p,
        "ph": ph,
        "c": c,
        "q": q,
        "tf": tf,
        "af": af,
        "v": v,
        "apc": apc
    }