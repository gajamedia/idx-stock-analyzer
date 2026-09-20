import requests
from bs4 import BeautifulSoup
import time
import re


class MarketWatchSource:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self):
        self.enabled = True

    def fetch(self, symbol):
        try:
            data = self._fetch_from_marketwatch(symbol)
            if data:
                data["source"] = "marketwatch"
                data["period"] = time.strftime("%Y")
                return data
            return None
        except Exception as e:
            print(f"MarketWatch error for {symbol}: {e}")
            return None

    def _fetch_from_marketwatch(self, symbol):
        yahoo_sym = f"{symbol}.JK"

        try:
            url = f"https://www.marketwatch.com/investing/stock/{yahoo_sym}"
            resp = requests.get(url, headers=self.HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                return self._parse_marketwatch_page(resp.text, symbol)
        except Exception:
            pass

        try:
            url = f"https://www.wsj.com/market-data/quotes/ID/{symbol}"
            resp = requests.get(url, headers=self.HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                return self._parse_wsj_page(resp.text, symbol)
        except Exception:
            pass

        return None

    def _parse_marketwatch_page(self, html, symbol):
        soup = BeautifulSoup(html, "html.parser")
        data = {"symbol": symbol}

        try:
            title = soup.find("h1", class_="company-name") or soup.find("h1")
            if title:
                data["company_name"] = title.get_text(strip=True)
        except Exception:
            pass

        try:
            price_elem = soup.find("bg-quote", class_="value") or soup.find("span", class_="last-value")
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace(",", "")
                data["current_price"] = float(re.sub(r'[^\d.]', '', price_text))
        except (ValueError, TypeError):
            pass

        try:
            for row in soup.find_all("li", class_="kv__item"):
                label_elem = row.find("small", class_="kv__label")
                value_elem = row.find("span", class_="kv__primary")
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)
                    parsed = self._parse_mw_stat(label, value)
                    if parsed:
                        data.update(parsed)
        except Exception:
            pass

        return data if len(data) > 1 else None

    def _parse_wsj_page(self, html, symbol):
        soup = BeautifulSoup(html, "html.parser")
        data = {"symbol": symbol}

        try:
            title = soup.find("h1", class_="company-name")
            if title:
                data["company_name"] = title.get_text(strip=True)
        except Exception:
            pass

        try:
            for item in soup.find_all("div", class_="kv__item"):
                label = item.find("small")
                value = item.find("span", class_="primary")
                if label and value:
                    parsed = self._parse_mw_stat(
                        label.get_text(strip=True).lower(),
                        value.get_text(strip=True)
                    )
                    if parsed:
                        data.update(parsed)
        except Exception:
            pass

        return data if len(data) > 1 else None

    def _parse_mw_stat(self, label, value):
        mappings = {
            "p/e ratio": "pe_ratio",
            "price-to-book": "pb_ratio",
            "dividend yield": "dividend_yield",
            "return on equity": "roe",
            "profit margin": "net_margin",
            "debt/equity": "debt_to_equity",
            "market cap": "market_cap",
            "beta": "beta",
            "eps": "eps",
            "52 week range": "fifty_two_week_high",
        }

        for key, field in mappings.items():
            if key in label:
                cleaned = value.replace(",", "").replace("$", "").replace("%", "").strip()
                if "52 week" in label and "-" in cleaned:
                    parts = cleaned.split("-")
                    try:
                        data["fifty_two_week_high"] = float(parts[-1].strip().replace(",", ""))
                        data["fifty_two_week_low"] = float(parts[0].strip().replace(",", ""))
                        return data
                    except (ValueError, TypeError, IndexError):
                        pass
                cleaned = re.sub(r'[^\d.\-eE+]', '', cleaned)
                try:
                    num = float(cleaned)
                    if "yield" in field or "margin" in field or "roe" in field:
                        if abs(num) > 1:
                            num = num / 100
                    return {field: num}
                except (ValueError, TypeError):
                    pass
        return None
