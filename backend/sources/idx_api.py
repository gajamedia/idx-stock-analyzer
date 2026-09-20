import requests
from bs4 import BeautifulSoup
import time
import re


class IDXSource:
    BEI_URL = "https://www.idx.co.id"
    YAHOO_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def __init__(self):
        self.enabled = True

    def fetch(self, symbol):
        try:
            data = self._fetch_from_idx_emiten(symbol)
            if not data:
                data = self._fetch_from_yahoo_summary(symbol)

            if data:
                data["source"] = "idx_bei"
                data["period"] = time.strftime("%Y")
                return data

            return None

        except Exception as e:
            print(f"IDX/BEI error for {symbol}: {e}")
            return None

    def _fetch_from_idx_emiten(self, symbol):
        try:
            url = f"https://www.idx.co.id/primary/StockData/GetStockSummary?code={symbol}"
            resp = requests.get(url, headers=self.YAHOO_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return self._parse_idx_summary(data, symbol)
        except Exception:
            pass

        try:
            url = f"https://webapi.idx.co.id/v1/emiten/{symbol}"
            resp = requests.get(url, headers=self.YAHOO_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return self._parse_idx_api_response(data, symbol)
        except Exception:
            pass

        return None

    def _fetch_from_yahoo_summary(self, symbol):
        try:
            yahoo_sym = f"{symbol}.JK"
            url = f"https://finance.yahoo.com/quote/{yahoo_sym}/key-statistics/"
            resp = requests.get(url, headers=self.YAHOO_HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                data = {"symbol": symbol}

                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            parsed = self._parse_yahoo_stat(label, value)
                            if parsed:
                                data.update(parsed)

                if len(data) > 2:
                    return data
        except Exception:
            pass
        return None

    def _parse_yahoo_stat(self, label, value):
        mappings = {
            "trailing pe": "pe_ratio",
            "forward pe": "forward_pe",
            "price to book": "pb_ratio",
            "price to sales": "ps_ratio",
            "peg ratio": "peg_ratio",
            "return on equity": "roe",
            "return on assets": "roa",
            "profit margin": "net_margin",
            "gross margin": "gross_margin",
            "operating margin": "operating_margin",
            "debt to equity": "debt_to_equity",
            "dividend yield": "dividend_yield",
            "book value": "book_value",
            "beta": "beta",
            "market cap": "market_cap",
            "enterprise value": "enterprise_value",
        }
        for key, field in mappings.items():
            if key in label:
                cleaned = value.replace(",", "").replace("%", "").replace("T", "e12").replace("B", "e9").replace("M", "e6").replace("K", "e3")
                try:
                    return {field: float(cleaned)}
                except (ValueError, TypeError):
                    pass
        return None

    def _parse_idx_summary(self, data, symbol):
        result = {"symbol": symbol}
        field_map = {
            "Sebelumnya": "previous_close",
            "Tertinggi": "fifty_two_week_high",
            "Terendah": "fifty_two_week_low",
            "Value": "market_cap",
            "Volume": "volume",
        }
        for item in data if isinstance(data, list) else []:
            for key, field in field_map.items():
                if item.get("label") == key or item.get("Name") == key:
                    val = item.get("value") or item.get("Value")
                    if val:
                        try:
                            result[field] = float(val.replace(",", "").replace(".", ""))
                        except (ValueError, TypeError):
                            pass
        return result if len(result) > 1 else None

    def _parse_idx_api_response(self, data, symbol):
        result = {"symbol": symbol}
        if isinstance(data, dict):
            result["company_name"] = data.get("NamaEmiten") or data.get("company_name")
            result["sector"] = data.get("Sektor") or data.get("sector")
            result["industry"] = data.get("Industri") or data.get("industry")
            try:
                result["current_price"] = float(str(data.get("Last", 0)).replace(",", ""))
                result["market_cap"] = float(str(data.get("MarketCap", 0)).replace(",", ""))
            except (ValueError, TypeError):
                pass
        return result if len(result) > 1 else None
