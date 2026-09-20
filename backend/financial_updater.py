import requests
import sqlite3
import os
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "stock_analyzer.db")

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_financial_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS financial_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            period TEXT NOT NULL,
            company_name TEXT,
            sector TEXT,
            industry TEXT,
            current_price REAL,
            market_cap REAL,
            enterprise_value REAL,
            revenue REAL,
            net_profit REAL,
            eps REAL,
            pe_ratio REAL,
            forward_pe REAL,
            pb_ratio REAL,
            ps_ratio REAL,
            roe REAL,
            roa REAL,
            gross_margin REAL,
            net_margin REAL,
            ebitda_margin REAL,
            operating_margin REAL,
            debt_to_equity REAL,
            dividend_yield REAL,
            total_cash REAL,
            total_debt REAL,
            total_assets REAL,
            total_equity REAL,
            book_value REAL,
            free_cashflow REAL,
            operating_cashflow REAL,
            shares_outstanding REAL,
            beta REAL,
            fifty_two_week_high REAL,
            fifty_two_week_low REAL,
            target_price REAL,
            recommendation TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            UNIQUE(symbol, period)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS update_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    db.close()


init_financial_db()


def fetch_yahoo_finance_full(symbol):
    yahoo_sym = f"{symbol}.JK"
    data = {}

    try:
        import time

        session = requests.Session()
        session.headers.update(YAHOO_HEADERS)

        # Step 1: Get crumb + cookies
        session.get("https://finance.yahoo.com/quote/" + yahoo_sym + "/", timeout=15)
        crumb_resp = session.get(
            "https://query2.finance.yahoo.com/v1/test/getcrumb",
            timeout=10,
        )
        crumb = crumb_resp.text if crumb_resp.status_code == 200 else None
        cookies = session.cookies.get_dict()

        # Step 2: Fetch quoteSummary
        modules = "summaryDetail,defaultKeyStatistics,financialData,price,earnings,assetProfile"
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{yahoo_sym}?modules={modules}"
        if crumb:
            url += f"&crumb={crumb}"

        resp = session.get(url, timeout=20)

        if resp.status_code == 200:
            result = resp.json().get("quoteSummary", {}).get("result", [{}])[0]

            summary = result.get("summaryDetail", {})
            stats = result.get("defaultKeyStatistics", {})
            financial = result.get("financialData", {})
            price_data = result.get("price", {})
            earnings = result.get("earnings", {})
            profile = result.get("assetProfile", {})

            def raw(val):
                if val is None:
                    return None
                if isinstance(val, dict):
                    return val.get("raw")
                return val

            data["symbol"] = symbol
            data["company_name"] = raw(price_data.get("longName")) or raw(price_data.get("shortName")) or symbol
            data["currency"] = raw(price_data.get("currency")) or "IDR"
            data["sector"] = profile.get("sector")
            data["industry"] = profile.get("industry")

            data["current_price"] = raw(price_data.get("regularMarketPrice"))
            data["previous_close"] = raw(summary.get("previousClose"))
            data["market_cap"] = raw(summary.get("marketCap"))
            data["enterprise_value"] = raw(stats.get("enterpriseValue"))

            data["pe_ratio"] = raw(summary.get("trailingPE"))
            data["forward_pe"] = raw(summary.get("forwardPE")) or raw(stats.get("forwardPE"))
            data["pb_ratio"] = raw(stats.get("priceToBook"))
            data["ps_ratio"] = raw(summary.get("priceToSalesTrailing12Months"))
            data["peg_ratio"] = raw(stats.get("pegRatio"))

            data["roe"] = raw(financial.get("returnOnEquity"))
            data["roa"] = raw(financial.get("returnOnAssets"))
            data["gross_margin"] = raw(financial.get("grossMargins"))
            data["net_margin"] = raw(financial.get("profitMargins"))
            data["ebitda_margin"] = raw(financial.get("ebitdaMargins"))
            data["operating_margin"] = raw(financial.get("operatingMargins"))

            data["debt_to_equity"] = raw(financial.get("debtToEquity"))
            data["dividend_yield"] = raw(summary.get("dividendYield")) or raw(summary.get("trailingAnnualDividendYield"))

            data["total_cash"] = raw(financial.get("totalCash"))
            data["total_debt"] = raw(financial.get("totalDebt"))
            data["revenue"] = raw(financial.get("totalRevenue"))
            data["net_profit"] = raw(financial.get("netIncomeToCommon"))
            data["ebitda"] = raw(financial.get("ebitda"))
            data["gross_profit"] = raw(financial.get("grossProfits"))
            data["free_cashflow"] = raw(financial.get("freeCashflow"))
            data["operating_cashflow"] = raw(financial.get("operatingCashflow"))

            data["book_value"] = raw(stats.get("bookValue"))
            data["shares_outstanding"] = raw(stats.get("sharesOutstanding"))
            data["beta"] = raw(summary.get("beta"))

            data["fifty_two_week_high"] = raw(summary.get("fiftyTwoWeekHigh"))
            data["fifty_two_week_low"] = raw(summary.get("fiftyTwoWeekLow"))

            data["target_price"] = raw(financial.get("targetMeanPrice"))
            data["recommendation"] = raw(financial.get("recommendationKey")) or "N/A"

            data["period"] = str(datetime.now().year)
        else:
            print(f"Quote API returned {resp.status_code} for {symbol}: {resp.text[:200]}")

        # Step 3: Fallback - chart API for price
        if not data.get("current_price"):
            time.sleep(1)
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}?range=1d&interval=1d"
            resp2 = session.get(chart_url, timeout=15)
            if resp2.status_code == 200:
                chart = resp2.json().get("chart", {}).get("result", [{}])[0]
                meta = chart.get("meta", {})
                data["symbol"] = symbol
                data["company_name"] = data.get("company_name") or symbol
                data["current_price"] = meta.get("regularMarketPrice")
                data["fifty_two_week_high"] = data.get("fifty_two_week_high") or meta.get("fiftyTwoWeekHigh")
                data["fifty_two_week_low"] = data.get("fifty_two_week_low") or meta.get("fiftyTwoWeekLow")
                if not data.get("period"):
                    data["period"] = str(datetime.now().year)

        return data if data.get("current_price") else None

    except Exception as e:
        print(f"Error fetching Yahoo Finance for {symbol}: {e}")
        return None


def calculate_metrics(data):
    if not data:
        return data

    if data.get("total_equity") and data.get("net_profit"):
        data["roe_calculated"] = data["net_profit"] / data["total_equity"]

    if data.get("total_assets") and data.get("net_profit"):
        data["roa_calculated"] = data["net_profit"] / data["total_assets"]

    if data.get("revenue") and data.get("gross_profit"):
        data["gross_margin_calculated"] = data["gross_profit"] / data["revenue"]

    return data


def save_financial_data(data):
    db = get_db()
    try:
        period = data.get("period", datetime.now().strftime("%Y"))

        db.execute("""
            INSERT OR REPLACE INTO financial_data
            (symbol, period, company_name, sector, industry, current_price, market_cap,
             enterprise_value, revenue, net_profit, eps, pe_ratio, forward_pe, pb_ratio,
             ps_ratio, roe, roa, gross_margin, net_margin, ebitda_margin, operating_margin,
             debt_to_equity, dividend_yield, total_cash, total_debt, total_assets, total_equity,
             book_value, free_cashflow, operating_cashflow, shares_outstanding, beta,
             fifty_two_week_high, fifty_two_week_low, target_price, recommendation,
             updated_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("symbol"),
            period,
            data.get("company_name"),
            data.get("sector"),
            data.get("industry"),
            data.get("current_price"),
            data.get("market_cap"),
            data.get("enterprise_value"),
            data.get("revenue") or data.get("annual_revenue"),
            data.get("net_profit") or data.get("annual_earnings"),
            data.get("latest_quarter_eps") or data.get("eps"),
            data.get("pe_ratio"),
            data.get("forward_pe"),
            data.get("pb_ratio"),
            data.get("ps_ratio"),
            data.get("roe") or data.get("roe_calculated"),
            data.get("roa") or data.get("roa_calculated"),
            data.get("gross_margin") or data.get("gross_margin_calculated"),
            data.get("net_margin"),
            data.get("ebitda_margin"),
            data.get("operating_margin"),
            data.get("debt_to_equity"),
            data.get("dividend_yield"),
            data.get("total_cash"),
            data.get("total_debt"),
            data.get("total_assets"),
            data.get("total_equity"),
            data.get("book_value"),
            data.get("free_cashflow"),
            data.get("operating_cashflow"),
            data.get("shares_outstanding"),
            data.get("beta"),
            data.get("fifty_two_week_high"),
            data.get("fifty_two_week_low"),
            data.get("target_price"),
            data.get("recommendation"),
            datetime.now().isoformat(),
            "yahoo_finance",
        ))
        db.commit()

        db.execute("""
            INSERT INTO update_history (symbol, status, message)
            VALUES (?, ?, ?)
        """, (data.get("symbol"), "success", f"Auto-fetched from Yahoo Finance - Period: {period}"))
        db.commit()

        return {"status": "saved", "symbol": data.get("symbol"), "period": period}
    except Exception as e:
        db.execute("""
            INSERT INTO update_history (symbol, status, message)
            VALUES (?, ?, ?)
        """, (data.get("symbol"), "error", str(e)))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def auto_fetch_and_save(symbol, source="auto", sources=None):
    symbol = symbol.upper()

    if source == "auto" or (sources and len(sources) > 1):
        try:
            from multi_source_fetcher import multi_source_fetcher
            if sources:
                data = multi_source_fetcher.fetch_multi_source(symbol, sources=sources)
            else:
                data, _ = multi_source_fetcher.fetch_best(symbol)
        except ImportError:
            data = fetch_yahoo_finance_full(symbol)
    elif source == "yahoo":
        data = fetch_yahoo_finance_full(symbol)
    else:
        try:
            from multi_source_fetcher import multi_source_fetcher
            data = multi_source_fetcher.fetch_from_source(symbol, source)
        except ImportError:
            data = fetch_yahoo_finance_full(symbol)

    if not data or not data.get("current_price"):
        return {
            "symbol": symbol,
            "status": "error",
            "message": f"Could not fetch data for {symbol}. Make sure the symbol is correct and listed on IDX.",
        }

    data = calculate_metrics(data)

    result = save_financial_data(data)

    return {
        "symbol": symbol,
        "status": "success",
        "data": {
            "company_name": data.get("company_name"),
            "current_price": data.get("current_price"),
            "market_cap": data.get("market_cap"),
            "pe_ratio": data.get("pe_ratio"),
            "forward_pe": data.get("forward_pe"),
            "pb_ratio": data.get("pb_ratio"),
            "roe": data.get("roe"),
            "roa": data.get("roa"),
            "gross_margin": data.get("gross_margin"),
            "net_margin": data.get("net_margin"),
            "debt_to_equity": data.get("debt_to_equity"),
            "dividend_yield": data.get("dividend_yield"),
            "revenue": data.get("revenue") or data.get("annual_revenue"),
            "net_profit": data.get("net_profit") or data.get("annual_earnings"),
            "total_cash": data.get("total_cash"),
            "total_debt": data.get("total_debt"),
            "book_value": data.get("book_value"),
            "target_price": data.get("target_price"),
            "recommendation": data.get("recommendation"),
            "fifty_two_week_high": data.get("fifty_two_week_high"),
            "fifty_two_week_low": data.get("fifty_two_week_low"),
            "beta": data.get("beta"),
        },
        "source": data.get("source", "yahoo"),
        "source_label": data.get("source_label", "Yahoo Finance"),
        "sources_used": data.get("sources_used", []),
        "save_result": result,
    }


def get_financial_data(symbol):
    db = get_db()
    row = db.execute(
        "SELECT * FROM financial_data WHERE symbol = ? ORDER BY period DESC LIMIT 1",
        (symbol.upper(),)
    ).fetchone()
    db.close()
    return dict(row) if row else None


def get_all_financial_data():
    db = get_db()
    rows = db.execute("SELECT * FROM financial_data ORDER BY symbol, period DESC").fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_update_history(symbol=None, limit=50):
    db = get_db()
    if symbol:
        rows = db.execute(
            "SELECT * FROM update_history WHERE symbol = ? ORDER BY updated_at DESC LIMIT ?",
            (symbol.upper(), limit)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM update_history ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def batch_auto_fetch(symbols):
    results = []
    for symbol in symbols:
        try:
            result = auto_fetch_and_save(symbol)
            results.append(result)
        except Exception as e:
            results.append({"symbol": symbol, "status": "error", "message": str(e)})
    return results
