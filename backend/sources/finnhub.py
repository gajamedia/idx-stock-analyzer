import os
import requests
import time


class FinnhubSource:
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "")
        self.enabled = bool(self.api_key)

    def fetch(self, symbol):
        if not self.enabled:
            return None

        try:
            quote = self._fetch_quote(symbol)
            profile = self._fetch_profile(symbol)
            financials = self._fetch_financials(symbol)

            if not profile and not financials:
                return None

            data = {}
            data["symbol"] = symbol
            data["company_name"] = profile.get("name", symbol) if profile else symbol
            data["sector"] = profile.get("finnhubIndustry") if profile else None
            data["industry"] = None

            if profile:
                data["market_cap"] = profile.get("marketCapitalization")
                data["shares_outstanding"] = profile.get("shareOutstanding")
                data["currency"] = profile.get("currency", "IDR")
                data["fifty_two_week_high"] = profile.get("weekHigh52")
                data["fifty_two_week_low"] = profile.get("weekLow52")
                data["pe_ratio"] = profile.get("pe")
                data["pb_ratio"] = profile.get("pb")
                data["dividend_yield"] = profile.get("dividendYield")

            if quote:
                data["current_price"] = quote.get("c")
                data["previous_close"] = quote.get("pc")

            if financials:
                annual = financials.get("annual", [])
                if annual:
                    latest = annual[0]
                    data["revenue"] = latest.get("revenue")
                    data["net_profit"] = latest.get("netIncome")
                    data["gross_profit"] = latest.get("grossProfit")
                    data["ebitda"] = latest.get("ebitda")
                    data["operating_cashflow"] = latest.get("operatingCashflow")
                    data["free_cashflow"] = latest.get("freeCashflow")
                    data["total_assets"] = latest.get("totalAssets")
                    data["total_debt"] = latest.get("totalDebt")
                    data["total_equity"] = latest.get("totalEquity")
                    data["total_cash"] = latest.get("totalCash")

            if data.get("total_equity") and data.get("net_profit"):
                data["roe"] = data["net_profit"] / data["total_equity"]
            if data.get("total_assets") and data.get("net_profit"):
                data["roa"] = data["net_profit"] / data["total_assets"]
            if data.get("revenue") and data.get("net_profit"):
                data["net_margin"] = data["net_profit"] / data["revenue"]
            if data.get("revenue") and data.get("gross_profit"):
                data["gross_margin"] = data["gross_profit"] / data["revenue"]
            if data.get("total_equity") and data.get("total_debt"):
                data["debt_to_equity"] = data["total_debt"] / data["total_equity"] if data["total_equity"] != 0 else None

            data["source"] = "finnhub"
            data["period"] = time.strftime("%Y")

            return data

        except Exception as e:
            print(f"Finnhub error for {symbol}: {e}")
            return None

    def _fetch_quote(self, symbol):
        for sym in [symbol + ".JK", symbol]:
            resp = requests.get(
                f"{self.BASE_URL}/quote",
                params={"symbol": sym, "token": self.api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("c") and data["c"] > 0:
                    return data
            time.sleep(0.3)
        return None

    def _fetch_profile(self, symbol):
        for sym in [symbol + ".JK", symbol]:
            resp = requests.get(
                f"{self.BASE_URL}/stock/profile2",
                params={"symbol": sym, "token": self.api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("name"):
                    return data
            time.sleep(0.3)
        return None

    def _fetch_financials(self, symbol):
        for sym in [symbol + ".JK", symbol]:
            resp = requests.get(
                f"{self.BASE_URL}/stock/financials",
                params={"symbol": sym, "statement": "all", "token": self.api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("annual") or data.get("quarterly"):
                    return data
            time.sleep(0.3)
        return None
