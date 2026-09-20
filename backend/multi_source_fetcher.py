import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from sources.alpha_vantage import AlphaVantageSource
    from sources.finnhub import FinnhubSource
    from sources.idx_api import IDXSource
    from sources.investing_com import InvestingComSource
    from sources.marketwatch import MarketWatchSource
    from sources.stockanalysis import StockAnalysisSource
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from sources.alpha_vantage import AlphaVantageSource
    from sources.finnhub import FinnhubSource
    from sources.idx_api import IDXSource
    from sources.investing_com import InvestingComSource
    from sources.marketwatch import MarketWatchSource
    from sources.stockanalysis import StockAnalysisSource

from financial_updater import fetch_yahoo_finance_full


SOURCE_PRIORITY = [
    "yahoo",
    "alpha_vantage",
    "finnhub",
    "idx",
    "investing_com",
    "marketwatch",
    "stockanalysis",
]

SOURCE_LABELS = {
    "yahoo": "Yahoo Finance",
    "alpha_vantage": "Alpha Vantage",
    "finnhub": "Finnhub",
    "idx": "IDX / BEI",
    "investing_com": "Investing.com",
    "marketwatch": "MarketWatch",
    "stockanalysis": "StockAnalysis.com",
}


class MultiSourceFetcher:
    def __init__(self):
        self.sources = {
            "alpha_vantage": AlphaVantageSource(),
            "finnhub": FinnhubSource(),
            "idx": IDXSource(),
            "investing_com": InvestingComSource(),
            "marketwatch": MarketWatchSource(),
            "stockanalysis": StockAnalysisSource(),
        }

    def get_available_sources(self):
        available = ["yahoo"]
        for name, source in self.sources.items():
            if getattr(source, "enabled", True):
                available.append(name)
        return available

    def fetch_from_source(self, symbol, source_name):
        symbol = symbol.upper()
        if source_name == "yahoo":
            return fetch_yahoo_finance_full(symbol)
        elif source_name in self.sources:
            return self.sources[source_name].fetch(symbol)
        return None

    def fetch_best(self, symbol):
        symbol = symbol.upper()
        result = None
        source_used = None

        for source_name in SOURCE_PRIORITY:
            try:
                data = self.fetch_from_source(symbol, source_name)
                if data and data.get("current_price"):
                    data["source"] = source_name
                    data["source_label"] = SOURCE_LABELS.get(source_name, source_name)
                    return data, source_name
                elif data and not result:
                    result = data
                    source_used = source_name
            except Exception as e:
                print(f"Error from {source_name} for {symbol}: {e}")
                continue

        if result:
            result["source"] = source_used
            result["source_label"] = SOURCE_LABELS.get(source_used, source_used)
            return result, source_used

        return None, None

    def fetch_all_sources(self, symbol):
        symbol = symbol.upper()
        results = {}

        def try_source(name):
            try:
                data = self.fetch_from_source(symbol, name)
                if data:
                    data["source"] = name
                    data["source_label"] = SOURCE_LABELS.get(name, name)
                    return name, data
            except Exception as e:
                print(f"Error from {name} for {symbol}: {e}")
            return name, None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(try_source, name): name for name in SOURCE_PRIORITY}
            for future in as_completed(futures):
                name, data = future.result()
                if data:
                    results[name] = data

        return results

    def merge_data(self, *data_list):
        merged = {}
        for data in data_list:
            if not data:
                continue
            for key, value in data.items():
                if value is not None and key not in ("source", "source_label", "period"):
                    if key not in merged or merged[key] is None:
                        merged[key] = value
        return merged

    def fetch_multi_source(self, symbol, sources=None):
        symbol = symbol.upper()
        if sources is None:
            sources = SOURCE_PRIORITY

        all_data = {}
        for source_name in sources:
            try:
                data = self.fetch_from_source(symbol, source_name)
                if data:
                    all_data[source_name] = data
            except Exception as e:
                print(f"Error fetching {source_name} for {symbol}: {e}")

        if not all_data:
            return None

        merged = self.merge_data(*all_data.values())
        sources_used = list(all_data.keys())
        merged["sources_used"] = sources_used
        merged["source"] = sources_used[0] if sources_used else "unknown"
        merged["source_label"] = ", ".join([SOURCE_LABELS.get(s, s) for s in sources_used])
        merged["period"] = time.strftime("%Y")

        return merged


multi_source_fetcher = MultiSourceFetcher()
