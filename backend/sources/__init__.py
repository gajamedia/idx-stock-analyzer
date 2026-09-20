from .alpha_vantage import AlphaVantageSource
from .finnhub import FinnhubSource
from .idx_api import IDXSource
from .investing_com import InvestingComSource
from .marketwatch import MarketWatchSource
from .stockanalysis import StockAnalysisSource

ALL_SOURCES = {
    "alpha_vantage": AlphaVantageSource,
    "finnhub": FinnhubSource,
    "idx": IDXSource,
    "investing_com": InvestingComSource,
    "marketwatch": MarketWatchSource,
    "stockanalysis": StockAnalysisSource,
}
