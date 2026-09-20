import requests
from datetime import datetime
import time

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

STOCK_DB = {
    "BBCA": {"name": "Bank Central Asia", "sector": "Finance", "market_cap": 938000000000000, "pe_ratio": 21.5, "pb_ratio": 4.2, "dividend_yield": 0.021, "roe": 0.221, "profit_margin": 0.435, "debt_to_equity": 28.5},
    "BBRI": {"name": "Bank Rakyat Indonesia", "sector": "Finance", "market_cap": 505000000000000, "pe_ratio": 12.8, "pb_ratio": 2.1, "dividend_yield": 0.058, "roe": 0.182, "profit_margin": 0.385, "debt_to_equity": 35.2},
    "BMRI": {"name": "Bank Mandiri", "sector": "Finance", "market_cap": 555000000000000, "pe_ratio": 13.5, "pb_ratio": 2.3, "dividend_yield": 0.052, "roe": 0.195, "profit_margin": 0.402, "debt_to_equity": 32.8},
    "BBNI": {"name": "Bank Negara Indonesia", "sector": "Finance", "market_cap": 320000000000000, "pe_ratio": 11.2, "pb_ratio": 1.8, "dividend_yield": 0.065, "roe": 0.168, "profit_margin": 0.352, "debt_to_equity": 38.5},
    "TLKM": {"name": "Telkom Indonesia", "sector": "Telecommunication", "market_cap": 310000000000000, "pe_ratio": 16.8, "pb_ratio": 3.5, "dividend_yield": 0.042, "roe": 0.215, "profit_margin": 0.185, "debt_to_equity": 22.3},
    "ASII": {"name": "Astra International", "sector": "Consumer Cyclical", "market_cap": 235000000000000, "pe_ratio": 14.2, "pb_ratio": 2.8, "dividend_yield": 0.035, "roe": 0.198, "profit_margin": 0.142, "debt_to_equity": 45.2},
    "UNVR": {"name": "Unilever Indonesia", "sector": "Consumer Defensive", "market_cap": 85000000000000, "pe_ratio": 25.5, "pb_ratio": 8.2, "dividend_yield": 0.028, "roe": 0.325, "profit_margin": 0.225, "debt_to_equity": 15.8},
    "HMSP": {"name": "HM Sampoerna", "sector": "Consumer Defensive", "market_cap": 90000000000000, "pe_ratio": 15.8, "pb_ratio": 4.5, "dividend_yield": 0.062, "roe": 0.285, "profit_margin": 0.182, "debt_to_equity": 18.5},
    "GGRM": {"name": "Gudang Garam", "sector": "Consumer Defensive", "market_cap": 52000000000000, "pe_ratio": 12.5, "pb_ratio": 3.2, "dividend_yield": 0.045, "roe": 0.258, "profit_margin": 0.152, "debt_to_equity": 22.8},
    "KLBF": {"name": "Kalbe Farma", "sector": "Healthcare", "market_cap": 55000000000000, "pe_ratio": 22.8, "pb_ratio": 5.5, "dividend_yield": 0.025, "roe": 0.245, "profit_margin": 0.168, "debt_to_equity": 12.5},
    "ICBP": {"name": "Indofood CBP Sukses Makmur", "sector": "Consumer Defensive", "market_cap": 82000000000000, "pe_ratio": 18.5, "pb_ratio": 6.2, "dividend_yield": 0.032, "roe": 0.335, "profit_margin": 0.125, "debt_to_equity": 35.5},
    "INDF": {"name": "Indofood Sukses Makmur", "sector": "Consumer Defensive", "market_cap": 90000000000000, "pe_ratio": 12.2, "pb_ratio": 2.1, "dividend_yield": 0.048, "roe": 0.175, "profit_margin": 0.085, "debt_to_equity": 42.5},
    "TOWR": {"name": "Tower Bersama Infrastructure", "sector": "Real Estate", "market_cap": 48000000000000, "pe_ratio": 18.2, "pb_ratio": 4.8, "dividend_yield": 0.038, "roe": 0.265, "profit_margin": 0.325, "debt_to_equity": 55.8},
    "EXCL": {"name": "XL Axiata", "sector": "Telecommunication", "market_cap": 33000000000000, "pe_ratio": 15.5, "pb_ratio": 1.8, "dividend_yield": 0.028, "roe": 0.118, "profit_margin": 0.125, "debt_to_equity": 48.5},
    "ISAT": {"name": "Indosat Ooredoo Hutchison", "sector": "Telecommunication", "market_cap": 35000000000000, "pe_ratio": 18.8, "pb_ratio": 2.2, "dividend_yield": 0.018, "roe": 0.125, "profit_margin": 0.108, "debt_to_equity": 62.5},
    "SMGR": {"name": "Semen Indonesia", "sector": "Basic Materials", "market_cap": 32000000000000, "pe_ratio": 15.2, "pb_ratio": 1.5, "dividend_yield": 0.042, "roe": 0.098, "profit_margin": 0.082, "debt_to_equity": 58.5},
    "GOTO": {"name": "GoTo Gojek Tokopedia", "sector": "Technology", "market_cap": 18000000000000, "pe_ratio": None, "pb_ratio": 3.8, "dividend_yield": None, "roe": -0.085, "profit_margin": -0.125, "debt_to_equity": 85.5},
    "BUKA": {"name": "Bukalapak.com", "sector": "Technology", "market_cap": 5500000000000, "pe_ratio": None, "pb_ratio": 2.2, "dividend_yield": None, "roe": -0.125, "profit_margin": -0.285, "debt_to_equity": 72.5},
    "BREN": {"name": "Barito Renewables Energy", "sector": "Utilities", "market_cap": 115000000000000, "pe_ratio": 45.8, "pb_ratio": 12.5, "dividend_yield": 0.008, "roe": 0.275, "profit_margin": 0.185, "debt_to_equity": 38.5},
    "ARTO": {"name": "Bank Jago", "sector": "Finance", "market_cap": 42000000000000, "pe_ratio": None, "pb_ratio": 8.5, "dividend_yield": None, "roe": 0.052, "profit_margin": -0.085, "debt_to_equity": 75.5},
    "BBYB": {"name": "Bank Neo Commerce", "sector": "Finance", "market_cap": 15000000000000, "pe_ratio": None, "pb_ratio": 2.8, "dividend_yield": None, "roe": 0.028, "profit_margin": -0.052, "debt_to_equity": 82.5},
    "MTEL": {"name": "Dayamitra Telekomunikasi", "sector": "Telecommunication", "market_cap": 28000000000000, "pe_ratio": 22.5, "pb_ratio": 2.8, "dividend_yield": 0.032, "roe": 0.128, "profit_margin": 0.285, "debt_to_equity": 18.5},
    "ANTM": {"name": "Aneka Tambang", "sector": "Basic Materials", "market_cap": 35000000000000, "pe_ratio": 18.5, "pb_ratio": 3.2, "dividend_yield": 0.028, "roe": 0.175, "profit_margin": 0.125, "debt_to_equity": 25.5},
    "INCO": {"name": "Vale Indonesia", "sector": "Basic Materials", "market_cap": 32000000000000, "pe_ratio": 8.5, "pb_ratio": 1.2, "dividend_yield": 0.085, "roe": 0.145, "profit_margin": 0.185, "debt_to_equity": 12.5},
    "MDKA": {"name": "Merdeka Copper Gold", "sector": "Basic Materials", "market_cap": 18000000000000, "pe_ratio": None, "pb_ratio": 2.5, "dividend_yield": None, "roe": 0.085, "profit_margin": 0.052, "debt_to_equity": 65.5},
    "SIDO": {"name": "Sido Muncul", "sector": "Healthcare", "market_cap": 8000000000000, "pe_ratio": 25.5, "pb_ratio": 6.8, "dividend_yield": 0.022, "roe": 0.268, "profit_margin": 0.185, "debt_to_equity": 8.5},
    "HRUM": {"name": "Harum Energy", "sector": "Energy", "market_cap": 8500000000000, "pe_ratio": 8.2, "pb_ratio": 0.85, "dividend_yield": 0.095, "roe": 0.105, "profit_margin": 0.225, "debt_to_equity": 15.5},
    "ITMG": {"name": "Indo Tambangraya Megah", "sector": "Energy", "market_cap": 12000000000000, "pe_ratio": 6.8, "pb_ratio": 1.2, "dividend_yield": 0.125, "roe": 0.178, "profit_margin": 0.285, "debt_to_equity": 8.5},
    "ADMG": {"name": "Adaro Energy Indonesia", "sector": "Energy", "market_cap": 25000000000000, "pe_ratio": 7.5, "pb_ratio": 1.1, "dividend_yield": 0.088, "roe": 0.148, "profit_margin": 0.215, "debt_to_equity": 22.5},
    "PTBA": {"name": "Bukit Asam", "sector": "Energy", "market_cap": 32000000000000, "pe_ratio": 8.8, "pb_ratio": 2.2, "dividend_yield": 0.078, "roe": 0.252, "profit_margin": 0.325, "debt_to_equity": 18.5},
    "AALI": {"name": "Astra Agro Lestari", "sector": "Basic Materials", "market_cap": 10000000000000, "pe_ratio": 10.5, "pb_ratio": 1.5, "dividend_yield": 0.058, "roe": 0.145, "profit_margin": 0.125, "debt_to_equity": 25.5},
    "SSMS": {"name": "Sawit Sumbermas Sarana", "sector": "Basic Materials", "market_cap": 5000000000000, "pe_ratio": 8.2, "pb_ratio": 1.2, "dividend_yield": 0.085, "roe": 0.152, "profit_margin": 0.185, "debt_to_equity": 18.5},
    "EMTK": {"name": "Emitra Digi Niaga", "sector": "Technology", "market_cap": 2000000000000, "pe_ratio": None, "pb_ratio": 1.5, "dividend_yield": None, "roe": -0.185, "profit_margin": -0.425, "debt_to_equity": 92.5},
    "AMRT": {"name": "Sumber Alfaria Trijaya", "sector": "Consumer Defensive", "market_cap": 57000000000000, "pe_ratio": 16.7, "pb_ratio": 2.9, "dividend_yield": 0.023, "roe": 0.184, "profit_margin": 0.027, "debt_to_equity": 22.0},
    "DKHH": {"name": "PT Cipta Sarana Medika Tbk", "sector": "Healthcare", "market_cap": 166000000000, "pe_ratio": 32.51, "pb_ratio": None, "dividend_yield": None, "roe": None, "profit_margin": 0.0416, "debt_to_equity": None},
    "VKTR": {"name": "PT VKTR Teknologi Mobilitas Tbk", "sector": "Consumer Cyclicals", "market_cap": 30840000000000, "pe_ratio": None, "pb_ratio": None, "dividend_yield": None, "roe": None, "profit_margin": -0.0104, "debt_to_equity": None},
}


def get_yahoo_symbol(idx_symbol):
    return f"{idx_symbol}.JK"


def fetch_stock_history(symbol, period="1y"):
    yahoo_sym = get_yahoo_symbol(symbol)

    try:
        end_date = int(time.time())
        period_map = {"1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}
        days = period_map.get(period, 365)
        start_date = end_date - (days * 86400)

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
        params = {"period1": start_date, "period2": end_date, "interval": "1d"}

        resp = requests.get(url, headers=YAHOO_HEADERS, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            records = []
            for i in range(len(timestamps)):
                dt = datetime.fromtimestamp(timestamps[i])
                c = quote["close"][i]
                if c is not None:
                    records.append({
                        "Date": dt.strftime("%Y-%m-%d"),
                        "Open": round(quote["open"][i], 2) if quote["open"][i] else round(c, 2),
                        "High": round(quote["high"][i], 2) if quote["high"][i] else round(c, 2),
                        "Low": round(quote["low"][i], 2) if quote["low"][i] else round(c, 2),
                        "Close": round(c, 2),
                        "Volume": quote["volume"][i] or 0,
                    })

            if records:
                return records
    except Exception as e:
        print(f"Yahoo API error for {symbol}: {e}")

    return None


def get_report_type(period):
    """Determine report type from period string."""
    if not period:
        return None
    p = period.upper()
    if p.startswith("FY"):
        return "Laporan Tahunan (Audited)"
    if p.startswith("Q"):
        return "Laporan Kuartalan (Interim)"
    if p.isdigit() and len(p) == 4:
        return "Laporan Tahunan (Audited)"
    return "Laporan Keuangan"


def fetch_stock_info(symbol):
    yahoo_sym = get_yahoo_symbol(symbol)
    db_info = STOCK_DB.get(symbol, {}).copy()

    # Always cek database untuk report metadata dan data tambahan
    db_report_info = {}
    try:
        import sqlite3, os
        db_path = os.path.join(os.path.dirname(__file__), "..", "stock_analyzer.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM financial_data WHERE symbol = ? ORDER BY period DESC",
            (symbol.upper(),)
        ).fetchall()
        conn.close()
        if rows:
            row = rows[0]  # Latest period for main data
            db_report_info = {
                "report_period": row["period"],
                "report_type": get_report_type(row["period"]),
                "report_source": row["source"],
                "report_updated_at": row["updated_at"],
            }
            # Include all available periods
            if len(rows) > 1:
                db_report_info["available_periods"] = [
                    {"period": r["period"], "type": get_report_type(r["period"]), "source": r["source"]}
                    for r in rows
                ]
            # Merge DB data ke db_info (isi field yang kosong dari STOCK_DB)
            db_fields = {
                "name": row["company_name"],
                "sector": row["sector"],
                "market_cap": row["market_cap"],
                "pe_ratio": row["pe_ratio"],
                "pb_ratio": row["pb_ratio"],
                "dividend_yield": row["dividend_yield"],
                "roe": row["roe"],
                "profit_margin": row["net_margin"],
                "debt_to_equity": row["debt_to_equity"],
                "revenue": row["revenue"],
                "total_assets": row["total_assets"],
                "total_equity": row["total_equity"],
                "total_debt": row["total_debt"],
                "target_price": row["target_price"],
                "recommendation": row["recommendation"],
                "current_price_db": row["current_price"],
                "gross_margin": row["gross_margin"],
                "roa": row["roa"],
                "net_profit": row["net_profit"],
            }
            for key, val in db_fields.items():
                if val is not None and (key not in db_info or db_info[key] is None):
                    db_info[key] = val
    except Exception as e:
        print(f"DB fallback error for {symbol}: {e}")

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
        params = {"period1": int(time.time()) - 86400, "period2": int(time.time()), "interval": "1d"}
        resp = requests.get(url, headers=YAHOO_HEADERS, params=params, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            result = data["chart"]["result"][0]
            meta = result["meta"]

            current_price = meta.get("regularMarketPrice", 0)
            prev_close = meta.get("chartPreviousClose", 0) or meta.get("previousClose", 0)
            high_52w = meta.get("fiftyTwoWeekHigh", 0)
            low_52w = meta.get("fiftyTwoWeekLow", 0)
            shares_outstanding = meta.get("sharesOutstanding", 0)

            market_cap = db_info.get("market_cap", 0) or 0
            if shares_outstanding and current_price:
                calculated_mcap = shares_outstanding * current_price
                if calculated_mcap > 0:
                    market_cap = calculated_mcap

            return {
                "symbol": symbol,
                "name": db_info.get("name", meta.get("shortName", symbol)),
                "sector": db_info.get("sector", "N/A"),
                "industry": "N/A",
                "market_cap": market_cap,
                "pe_ratio": db_info.get("pe_ratio"),
                "forward_pe": None,
                "pb_ratio": db_info.get("pb_ratio"),
                "dividend_yield": db_info.get("dividend_yield"),
                "revenue": db_info.get("revenue"),
                "net_profit": db_info.get("net_profit"),
                "total_assets": db_info.get("total_assets"),
                "total_equity": db_info.get("total_equity"),
                "total_debt": db_info.get("total_debt"),
                "target_price": db_info.get("target_price"),
                "recommendation": db_info.get("recommendation"),
                "profit_margin": db_info.get("profit_margin"),
                "gross_margin": db_info.get("gross_margin"),
                "roe": db_info.get("roe"),
                "roa": db_info.get("roa"),
                "debt_to_equity": db_info.get("debt_to_equity"),
                "current_price": current_price or db_info.get("current_price_db"),
                "previous_close": prev_close,
                "fifty_two_week_high": high_52w,
                "fifty_two_week_low": low_52w,
                "shares_outstanding": shares_outstanding,
                "currency": meta.get("currency", "IDR"),
                "report_period": db_report_info.get("report_period"),
                "report_type": db_report_info.get("report_type"),
                "report_source": db_report_info.get("report_source"),
                "report_updated_at": db_report_info.get("report_updated_at"),
                "available_periods": db_report_info.get("available_periods"),
            }
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")

    return {
        "symbol": symbol,
        "name": db_info.get("name", symbol),
        "sector": db_info.get("sector", "N/A"),
        "industry": "N/A",
        "market_cap": db_info.get("market_cap", 0),
        "pe_ratio": db_info.get("pe_ratio"),
        "forward_pe": None,
        "pb_ratio": db_info.get("pb_ratio"),
        "dividend_yield": db_info.get("dividend_yield"),
        "revenue": db_info.get("revenue"),
        "net_profit": db_info.get("net_profit"),
        "total_assets": db_info.get("total_assets"),
        "total_equity": db_info.get("total_equity"),
        "total_debt": db_info.get("total_debt"),
        "target_price": db_info.get("target_price"),
        "recommendation": db_info.get("recommendation"),
        "profit_margin": db_info.get("profit_margin"),
        "gross_margin": db_info.get("gross_margin"),
        "roe": db_info.get("roe"),
        "roa": db_info.get("roa"),
        "debt_to_equity": db_info.get("debt_to_equity"),
        "current_price": db_info.get("current_price_db"),
        "currency": "IDR",
        "report_period": db_report_info.get("report_period"),
        "report_type": db_report_info.get("report_type"),
        "report_source": db_report_info.get("report_source"),
        "report_updated_at": db_report_info.get("report_updated_at"),
        "available_periods": db_report_info.get("available_periods"),
    }


def fetch_idx_stock_list():
    stocks = []
    for sym, info in STOCK_DB.items():
        stocks.append({"symbol": sym, "name": info["name"]})
    return stocks


def fetch_market_overview():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EJKSE"
        params = {"period1": int(time.time()) - 172800, "period2": int(time.time()), "interval": "1d"}
        resp = requests.get(url, headers=YAHOO_HEADERS, params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            result = data["chart"]["result"][0]
            quote = result["indicators"]["quote"][0]
            timestamps = result.get("timestamp", [])

            if timestamps:
                last_idx = len(timestamps) - 1
                close = quote["close"][last_idx]
                open_price = quote["open"][last_idx]

                if close and open_price:
                    return {
                        "ihsg": round(close, 2),
                        "change": round(close - open_price, 2),
                        "change_pct": round(((close - open_price) / open_price) * 100, 2),
                    }

            meta = result.get("meta", {})
            price = meta.get("regularMarketPrice", 0)
            prev = meta.get("chartPreviousClose", 0)
            if price and prev:
                return {
                    "ihsg": round(price, 2),
                    "change": round(price - prev, 2),
                    "change_pct": round(((price - prev) / prev) * 100, 2),
                }
    except Exception as e:
        print(f"Error fetching IHSG: {e}")

    return {"ihsg": 0, "change": 0, "change_pct": 0}
