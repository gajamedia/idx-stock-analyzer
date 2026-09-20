import requests
from bs4 import BeautifulSoup
import time
import re
import json


class InvestingComSource:
    YAHOO_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def __init__(self):
        self.enabled = True

    def fetch(self, symbol):
        try:
            data = self._fetch_fundamentals(symbol)
            if data:
                data["source"] = "investing_com"
                data["period"] = time.strftime("%Y")
                return data
            return None
        except Exception as e:
            print(f"Investing.com error for {symbol}: {e}")
            return None

    def _fetch_fundamentals(self, symbol):
        yahoo_sym = f"{symbol}.JK"

        try:
            url = f"https://www.investing.com/equities/{symbol.lower()}-indonesia"
            resp = requests.get(url, headers=self.YAHOO_HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                return self._parse_investing_page(resp.text, symbol)
        except Exception:
            pass

        try:
            url = f"https://www.google.com/finance/quote/{yahoo_sym}"
            resp = requests.get(url, headers=self.YAHOO_HEADERS, timeout=15)
            if resp.status_code == 200:
                return self._parse_google_finance(resp.text, symbol)
        except Exception:
            pass

        return None

    def _parse_investing_page(self, html, symbol):
        soup = BeautifulSoup(html, "html.parser")
        data = {"symbol": symbol}

        try:
            title = soup.find("h1")
            if title:
                data["company_name"] = title.get_text(strip=True).split(" - ")[0].strip()
        except Exception:
            pass

        try:
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        parsed = self._parse_ratio(label, value)
                        if parsed:
                            data.update(parsed)
        except Exception:
            pass

        return data if len(data) > 1 else None

    def _parse_google_finance(self, html, symbol):
        soup = BeautifulSoup(html, "html.parser")
        data = {"symbol": symbol}

        try:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "AF_initDataCallback" in (script.string or ""):
                    json_match = re.search(r'AF_initDataCallback\(({.*?})\)', script.string, re.DOTALL)
                    if json_match:
                        try:
                            json_data = json.loads(json_match.group(1))
                            self._extract_google_data(json_data, data)
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass

        try:
            meta_divs = soup.find_all("div", {"data-last-price": True})
            for div in meta_divs:
                price = div.get("data-last-price")
                if price:
                    data["current_price"] = float(price)
                mcap = div.get("data-market-cap")
                if mcap:
                    data["market_cap"] = float(mcap)
        except Exception:
            pass

        return data if len(data) > 1 else None

    def _extract_google_data(self, json_data, data):
        try:
            if isinstance(json_data, dict):
                for key, val in json_data.items():
                    if isinstance(val, str) and val.replace(".", "").replace("-", "").isdigit():
                        pass
        except Exception:
            pass

    def _parse_ratio(self, label, value):
        mappings = {
            "pe ratio": "pe_ratio",
            "price/book": "pb_ratio",
            "price-to-book": "pb_ratio",
            "dividend yield": "dividend_yield",
            "return on equity": "roe",
            "return on assets": "roa",
            "profit margin": "net_margin",
            "gross margin": "gross_margin",
            "debt/equity": "debt_to_equity",
            "debt to equity": "debt_to_equity",
            "market cap": "market_cap",
            "beta": "beta",
            "eps": "eps",
            "book value": "book_value",
        }

        for key, field in mappings.items():
            if key in label:
                cleaned = value.replace(",", "").replace("%", "").replace("$", "").replace("Rp", "").strip()
                cleaned = re.sub(r'[^\d.\-eE+]', '', cleaned)
                try:
                    num = float(cleaned)
                    if "margin" in field or "yield" in field or "roe" in field or "roa" in field:
                        if abs(num) > 1:
                            num = num / 100
                    return {field: num}
                except (ValueError, TypeError):
                    pass
        return None
