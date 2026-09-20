import os
import requests
import time


class AlphaVantageSource:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.enabled = bool(self.api_key)

    def fetch(self, symbol):
        if not self.enabled:
            return None

        try:
            overview = self._fetch_overview(symbol)
            if not overview:
                return None

            income = self._fetch_income_statement(symbol)
            balance = self._fetch_balance_sheet(symbol)

            data = {}
            data["symbol"] = symbol
            data["company_name"] = overview.get("Name", symbol)
            data["sector"] = overview.get("Sector")
            data["industry"] = overview.get("Industry")

            data["market_cap"] = self._safe_float(overview.get("MarketCapitalization"))
            data["pe_ratio"] = self._safe_float(overview.get("PERatio"))
            data["pb_ratio"] = self._safe_float(overview.get("PriceToBookRatio"))
            data["ps_ratio"] = self._safe_float(overview.get("PriceToSalesRatioTTM"))
            data["peg_ratio"] = self._safe_float(overview.get("PEGRatio"))

            data["dividend_yield"] = self._safe_float(overview.get("DividendYield"))
            data["eps"] = self._safe_float(overview.get("EPS"))
            data["revenue"] = self._safe_float(overview.get("RevenueTTM"))
            data["net_profit"] = self._safe_float(overview.get("NetIncomeTTM"))

            data["roe"] = self._safe_float(overview.get("ReturnOnEquityTTM"))
            data["roa"] = self._safe_float(overview.get("ReturnOnAssetsTTM"))
            data["profit_margin"] = self._safe_float(overview.get("ProfitMargin"))
            data["gross_margin"] = self._safe_float(overview.get("GrossProfitTTM"))
            data["operating_margin"] = self._safe_float(overview.get("OperatingMarginTTM"))

            data["debt_to_equity"] = self._safe_float(overview.get("DebtToEquity"))
            data["book_value"] = self._safe_float(overview.get("BookValue"))
            data["beta"] = self._safe_float(overview.get("Beta"))

            data["fifty_two_week_high"] = self._safe_float(overview.get("52WeekHigh"))
            data["fifty_two_week_low"] = self._safe_float(overview.get("52WeekLow"))
            data["shares_outstanding"] = self._safe_float(overview.get("SharesOutstanding"))

            data["total_assets"] = None
            data["total_equity"] = None
            data["total_debt"] = None
            if balance:
                latest = balance.get("annualReports", balance.get("quarterlyReports", []))
                if latest:
                    b = latest[0]
                    data["total_assets"] = self._safe_float(b.get("totalAssets"))
                    data["total_equity"] = self._safe_float(
                        self._safe_float(b.get("totalShareholderEquity"))
                        or self._safe_float(b.get("totalAssets")) - self._safe_float(b.get("totalLiabilities"))
                    )
                    data["total_debt"] = self._safe_float(b.get("totalLiabilities"))

            data["net_margin"] = data.get("profit_margin")
            data["gross_margin"] = data.get("gross_margin")
            if data["gross_margin"] and data["revenue"] and data["revenue"] > 0:
                data["gross_margin"] = data["gross_margin"] / data["revenue"]

            data["source"] = "alpha_vantage"
            data["period"] = time.strftime("%Y")

            return data

        except Exception as e:
            print(f"Alpha Vantage error for {symbol}: {e}")
            return None

    def _fetch_overview(self, symbol):
        params = {
            "function": "OVERVIEW",
            "symbol": symbol + ".JK",
            "apikey": self.api_key,
        }
        resp = requests.get(self.BASE_URL, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("Name"):
                return data
        time.sleep(0.5)

        params["symbol"] = symbol
        resp = requests.get(self.BASE_URL, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("Name"):
                return data
        return None

    def _fetch_income_statement(self, symbol):
        for sym in [symbol + ".JK", symbol]:
            params = {
                "function": "INCOME_STATEMENT",
                "symbol": sym,
                "apikey": self.api_key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "annualReports" in data or "quarterlyReports" in data:
                    return data
            time.sleep(0.5)
        return None

    def _fetch_balance_sheet(self, symbol):
        for sym in [symbol + ".JK", symbol]:
            params = {
                "function": "BALANCE_SHEET",
                "symbol": sym,
                "apikey": self.api_key,
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "annualReports" in data or "quarterlyReports" in data:
                    return data
            time.sleep(0.5)
        return None

    @staticmethod
    def _safe_float(val):
        if val is None or val == "" or val == "None":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
