import requests
from bs4 import BeautifulSoup
import time
import re


class StockAnalysisSource:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self):
        self.enabled = True

    def fetch(self, symbol):
        try:
            data = self._fetch_key_statistics(symbol)
            if data:
                data["source"] = "stockanalysis"
                data["period"] = time.strftime("%Y")
                return data
            return None
        except Exception as e:
            print(f"StockAnalysis error for {symbol}: {e}")
            return None

    def _fetch_key_statistics(self, symbol):
        yahoo_sym = f"{symbol}.JK"

        try:
            url = f"https://stockanalysis.com/quote/jkse/{symbol}/financials/"
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            if resp.status_code == 200:
                data = self._parse_stockanalysis(resp.text, symbol)
                if data:
                    return data
        except Exception:
            pass

        try:
            url = f"https://stockanalysis.com/quote/jkse/{symbol}/"
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            if resp.status_code == 200:
                data = self._parse_overview_page(resp.text, symbol)
                if data:
                    return data
        except Exception:
            pass

        return None

    def _parse_stockanalysis(self, html, symbol):
        soup = BeautifulSoup(html, "html.parser")
        data = {"symbol": symbol}

        try:
            title = soup.find("h1")
            if title:
                data["company_name"] = title.get_text(strip=True).split(" (")[0].strip()
        except Exception:
            pass

        try:
            tables = soup.find_all("table")
            for table in tables:
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[-1].get_text(strip=True)
                        parsed = self._parse_sa_stat(label, value)
                        if parsed:
                            data.update(parsed)
        except Exception:
            pass

        try:
            stat_divs = soup.find_all("div", {"data-test-id": True})
            for div in stat_divs:
                label_elem = div.find("span", {"data-test-id": re.compile("label")})
                value_elem = div.find("span", {"data-test-id": re.compile("value")})
                if label_elem and value_elem:
                    parsed = self._parse_sa_stat(
                        label_elem.get_text(strip=True).lower(),
                        value_elem.get_text(strip=True)
                    )
                    if parsed:
                        data.update(parsed)
        except Exception:
            pass

        return data if len(data) > 1 else None

    def _parse_overview_page(self, html, symbol):
        soup = BeautifulSoup(html, "html.parser")
        data = {"symbol": symbol}

        try:
            title = soup.find("h1")
            if title:
                data["company_name"] = title.get_text(strip=True).split(" (")[0].strip()
        except Exception:
            pass

        try:
            for stat_row in soup.find_all("div", class_=re.compile("statistics")):
                label = stat_row.find("span", class_=re.compile("label"))
                value = stat_row.find("span", class_=re.compile("value"))
                if label and value:
                    parsed = self._parse_sa_stat(
                        label.get_text(strip=True).lower(),
                        value.get_text(strip=True)
                    )
                    if parsed:
                        data.update(parsed)
        except Exception:
            pass

        return data if len(data) > 1 else None

    def _parse_sa_stat(self, label, value):
        mappings = {
            "pe ratio": "pe_ratio",
            "forward pe": "forward_pe",
            "peg ratio": "peg_ratio",
            "price to book": "pb_ratio",
            "price/sales": "ps_ratio",
            "dividend yield": "dividend_yield",
            "return on equity": "roe",
            "return on assets": "roa",
            "profit margin": "net_margin",
            "gross margin": "gross_margin",
            "operating margin": "operating_margin",
            "debt/equity": "debt_to_equity",
            "debt to equity": "debt_to_equity",
            "market cap": "market_cap",
            "enterprise value": "enterprise_value",
            "beta": "beta",
            "eps": "eps",
            "book value": "book_value",
            "revenue": "revenue",
            "net income": "net_profit",
        }

        for key, field in mappings.items():
            if key in label:
                cleaned = value.replace(",", "").replace("$", "").replace("Rp", "").strip()
                if "b" in cleaned.lower():
                    cleaned = cleaned.lower().replace("b", "")
                    try:
                        return {field: float(cleaned) * 1e9}
                    except ValueError:
                        pass
                elif "m" in cleaned.lower() and "market" not in label:
                    cleaned = cleaned.lower().replace("m", "")
                    try:
                        return {field: float(cleaned) * 1e6}
                    except ValueError:
                        pass
                elif "t" in cleaned.lower() and len(cleaned) > 1:
                    cleaned = cleaned.lower().replace("t", "")
                    try:
                        return {field: float(cleaned) * 1e12}
                    except ValueError:
                        pass

                cleaned = re.sub(r'[^\d.\-eE+]', '', cleaned)
                try:
                    num = float(cleaned)
                    if any(x in field for x in ["margin", "yield", "roe", "roa"]):
                        if abs(num) > 1:
                            num = num / 100
                    return {field: num}
                except (ValueError, TypeError):
                    pass
        return None
