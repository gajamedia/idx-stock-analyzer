import sys
import os
import asyncio
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from data_fetcher import fetch_stock_history, fetch_stock_info, fetch_idx_stock_list, fetch_market_overview
from technical import analyze_stock
from fundamental import analyze_fundamental
from sentiment import analyze_sentiment
from backtester import run_backtest
from alerts import create_alert, get_active_alerts, check_alerts, delete_alert, get_triggered_alerts
from reporter import generate_report, generate_quick_summary
from notifications import email_notifier, telegram_notifier
from monitor import monitor
from database import (
    init_db, watchlist_add, watchlist_remove, watchlist_get_all, watchlist_clear,
    portfolio_get_all, portfolio_upsert, portfolio_delete, portfolio_clear,
)
from financial_updater import (
    auto_fetch_and_save, get_financial_data, get_all_financial_data,
    get_update_history, batch_auto_fetch, save_financial_data,
    delete_financial_data, update_financial_data
)
from horizon import analyze_horizon, get_all_horizons
from consultation import analyze_portfolio_consultation, analyze_entry_consultation

try:
    from multi_source_fetcher import multi_source_fetcher, SOURCE_LABELS
except ImportError:
    multi_source_fetcher = None
    SOURCE_LABELS = {}

app = FastAPI(title="IDX Stock Analyzer", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class AlertRequest(BaseModel):
    symbol: str
    alert_type: str
    target_value: float


class MonitorConfig(BaseModel):
    interval: int = 60


class NotificationConfig(BaseModel):
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class FinancialUpdateRequest(BaseModel):
    symbol: str
    period: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    eps: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    dividend_yield: Optional[float] = None
    total_assets: Optional[float] = None
    total_equity: Optional[float] = None
    total_debt: Optional[float] = None


class BatchUpdateRequest(BaseModel):
    symbols: List[str]


class PortfolioHoldingRequest(BaseModel):
    symbol: str
    lots: float
    avg_price: float


class ConsultationRequest(BaseModel):
    horizon_months: int = 3


class EntryConsultationRequest(BaseModel):
    symbols: List[str]
    horizon_months: int = 3
    capital: Optional[float] = None
    lots: Optional[int] = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


ws_manager = ConnectionManager()


def price_update_callback(prices):
    asyncio.run(ws_manager.broadcast({
        "type": "price_update",
        "data": prices,
        "timestamp": datetime.now().isoformat(),
    }))


def alert_callback(event_type, data):
    asyncio.run(ws_manager.broadcast({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }))


@app.on_event("startup")
async def startup():
    init_db()
    monitor.add_price_callback(price_update_callback)
    monitor.add_listener(alert_callback)
    print("Server ready. Monitor can be started manually via /api/monitor/start")


@app.on_event("shutdown")
async def shutdown():
    monitor.stop()


@app.get("/")
async def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "subscribe":
                symbols = msg.get("symbols", [])
                prices = {}
                for sym in symbols:
                    history = fetch_stock_history(sym, period="1d")
                    if history and len(history) > 0:
                        prices[sym] = history[-1].get("Close", 0)
                await websocket.send_json({
                    "type": "initial_prices",
                    "data": prices,
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


class WatchlistRequest(BaseModel):
    symbol: str
    name: Optional[str] = None
    notes: Optional[str] = None


@app.get("/api/stocks")
async def get_stock_list():
    stocks = fetch_idx_stock_list()
    return {"stocks": stocks}


@app.get("/api/watchlist")
async def get_watchlist():
    items = watchlist_get_all()
    return {"watchlist": items, "count": len(items)}


@app.post("/api/watchlist")
async def add_to_watchlist(request: WatchlistRequest):
    return watchlist_add(request.symbol, request.name, request.notes)


@app.delete("/api/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    return watchlist_remove(symbol)


@app.delete("/api/watchlist")
async def clear_watchlist():
    return watchlist_clear()


@app.get("/api/watchlist/analyze")
async def analyze_watchlist():
    items = watchlist_get_all()
    if not items:
        return {"stocks": []}

    results = []
    for item in items:
        sym = item["symbol"]
        try:
            history = fetch_stock_history(sym, period="1y")
            if history:
                stock_info = fetch_stock_info(sym)
                technical = analyze_stock(history)
                fundamental = analyze_fundamental(stock_info)
                results.append({
                    "symbol": sym,
                    "name": item.get("name") or (stock_info.get("name") if stock_info else sym),
                    "notes": item.get("notes", ""),
                    "technical": technical,
                    "fundamental": fundamental,
                })
        except Exception:
            results.append({"symbol": sym, "error": "Failed to fetch data"})

    return {"stocks": results}


@app.get("/api/market")
async def get_market_overview():
    overview = fetch_market_overview()
    return overview


@app.get("/api/stock/{symbol}")
async def get_stock_analysis(symbol: str):
    symbol = symbol.upper()

    history = fetch_stock_history(symbol, period="1y")
    if not history:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    stock_info = fetch_stock_info(symbol)
    technical = analyze_stock(history)
    fundamental = analyze_fundamental(stock_info)
    sentiment = analyze_sentiment(symbol)

    return {
        "symbol": symbol,
        "technical": technical,
        "fundamental": fundamental,
        "sentiment": sentiment,
        "info": stock_info,
    }


@app.get("/api/stock/{symbol}/technical")
async def get_technical_analysis(symbol: str):
    history = fetch_stock_history(symbol.upper(), period="1y")
    if not history:
        raise HTTPException(status_code=404, detail="No data available")
    return analyze_stock(history)


@app.get("/api/stock/{symbol}/fundamental")
async def get_fundamental_analysis(symbol: str):
    stock_info = fetch_stock_info(symbol.upper())
    if not stock_info:
        raise HTTPException(status_code=404, detail="No data available")
    return analyze_fundamental(stock_info)


@app.get("/api/stock/{symbol}/sentiment")
async def get_sentiment_analysis(symbol: str):
    return analyze_sentiment(symbol.upper())


@app.get("/api/backtest/{symbol}")
async def get_backtest(
    symbol: str,
    strategy: str = Query("all", enum=["all", "rsi", "macd", "ma"]),
    capital: int = Query(1000000, ge=100000),
):
    result = run_backtest(symbol.upper(), strategy, capital)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/alerts")
async def add_alert(request: AlertRequest):
    return create_alert(request.symbol, request.alert_type, request.target_value)


@app.get("/api/alerts")
async def list_alerts(symbol: Optional[str] = None):
    return get_active_alerts(symbol)


@app.delete("/api/alerts/{alert_id}")
async def remove_alert(alert_id: int):
    return delete_alert(alert_id)


@app.get("/api/alerts/triggered")
async def triggered_alerts():
    return get_triggered_alerts()


@app.post("/api/monitor/start")
async def start_monitor(config: MonitorConfig):
    monitor.start(interval=config.interval)
    return {"status": "started", "interval": config.interval}


@app.post("/api/monitor/stop")
async def stop_monitor():
    monitor.stop()
    return {"status": "stopped"}


@app.get("/api/monitor/status")
async def monitor_status():
    return monitor.get_status()


@app.get("/api/monitor/prices")
async def get_live_prices():
    return {"prices": monitor.last_prices, "timestamp": datetime.now().isoformat()}


@app.post("/api/notifications/test-email")
async def test_email(config: NotificationConfig):
    if not config.email:
        raise HTTPException(status_code=400, detail="Email required")
    result = email_notifier.send_alert(
        to_email=config.email,
        subject="Test Notification",
        message="This is a test notification from IDX Stock Analyzer.",
    )
    return result


@app.post("/api/notifications/test-telegram")
async def test_telegram():
    result = telegram_notifier.send_alert("Test notification from IDX Stock Analyzer")
    return result


@app.get("/api/notifications/status")
async def notification_status():
    return {
        "email": {"enabled": email_notifier.enabled},
        "telegram": {"enabled": telegram_notifier.enabled},
    }


@app.post("/api/financial/update")
async def update_financial(request: FinancialUpdateRequest):
    manual_data = {"symbol": request.symbol.upper()}
    if request.sector:
        manual_data["sector"] = request.sector
    if request.market_cap is not None:
        manual_data["market_cap"] = request.market_cap
    for field in ["period", "revenue", "net_profit", "eps", "pe_ratio", "pb_ratio",
                   "roe", "roa", "gross_margin", "net_margin", "debt_to_equity",
                   "dividend_yield", "total_assets", "total_equity", "total_debt"]:
        val = getattr(request, field)
        if val is not None:
            manual_data[field] = val

    result = save_financial_data(manual_data)
    return result


class QuickFetchRequest(BaseModel):
    symbol: str
    source: Optional[str] = "auto"
    sources: Optional[List[str]] = None


@app.post("/api/financial/fetch")
async def quick_fetch_financial(request: QuickFetchRequest):
    result = auto_fetch_and_save(request.symbol, source=request.source, sources=request.sources)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.get("/api/sources")
async def get_available_sources():
    if multi_source_fetcher:
        available = multi_source_fetcher.get_available_sources()
    else:
        available = ["yahoo"]
    return {
        "sources": [
            {"id": s, "name": SOURCE_LABELS.get(s, s), "available": s in available}
            for s in ["yahoo", "alpha_vantage", "finnhub", "idx", "investing_com", "marketwatch", "stockanalysis"]
        ]
    }


@app.get("/api/sources/labels")
async def get_source_labels():
    return {"labels": SOURCE_LABELS}


class MultiSourceFetchRequest(BaseModel):
    symbol: str
    sources: Optional[List[str]] = None


@app.post("/api/financial/fetch-multi")
async def fetch_multi_source(request: MultiSourceFetchRequest):
    if not multi_source_fetcher:
        raise HTTPException(status_code=500, detail="Multi-source fetcher not available")

    symbol = request.symbol.upper()
    sources = request.sources or None

    results = multi_source_fetcher.fetch_all_sources(symbol)
    if not results:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol} from any source")

    merged = multi_source_fetcher.merge_data(*results.values())
    sources_used = list(results.keys())

    return {
        "symbol": symbol,
        "merged_data": merged,
        "by_source": {
            name: {
                "source_label": SOURCE_LABELS.get(name, name),
                "data_available": True,
                "pe_ratio": d.get("pe_ratio"),
                "pb_ratio": d.get("pb_ratio"),
                "roe": d.get("roe"),
                "net_margin": d.get("net_margin"),
                "debt_to_equity": d.get("debt_to_equity"),
                "dividend_yield": d.get("dividend_yield"),
                "current_price": d.get("current_price"),
            }
            for name, d in results.items()
        },
        "sources_used": sources_used,
        "source_label": ", ".join([SOURCE_LABELS.get(s, s) for s in sources_used]),
    }


@app.get("/api/financial/{symbol}")
async def get_financial(symbol: str):
    data = get_financial_data(symbol.upper())
    if not data:
        return {"symbol": symbol.upper(), "data": None, "message": "No financial data found. Use POST /api/financial/update to add data."}
    return {"symbol": symbol.upper(), "data": data}


@app.put("/api/financial/{symbol}/{period}")
async def edit_financial(symbol: str, period: str, request: FinancialUpdateRequest):
    update_data = {"symbol": symbol.upper(), "period": period}
    for field in ["sector", "market_cap", "revenue", "net_profit", "eps", "pe_ratio", "pb_ratio",
                   "roe", "roa", "gross_margin", "net_margin", "debt_to_equity",
                   "dividend_yield", "total_assets", "total_equity", "total_debt"]:
        val = getattr(request, field)
        if val is not None:
            update_data[field] = val
    if request.sector:
        update_data["sector"] = request.sector
    if request.market_cap is not None:
        update_data["market_cap"] = request.market_cap
    result = update_financial_data(update_data)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.delete("/api/financial/{symbol}/{period}")
async def delete_financial(symbol: str, period: str):
    result = delete_financial_data(symbol, period)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.get("/api/financial")
async def list_financial_data():
    data = get_all_financial_data()
    return {"stocks": data, "count": len(data)}


@app.post("/api/financial/batch-update")
async def batch_update(request: BatchUpdateRequest):
    results = batch_auto_fetch(request.symbols)
    return {"results": results}


@app.get("/api/financial/history")
async def financial_history(symbol: Optional[str] = None, limit: int = Query(50)):
    history = get_update_history(symbol, limit)
    return {"history": history}


@app.get("/api/report")
async def generate_full_report(symbols: str = Query("BBCA,BBRI,TLKM")):
    symbol_list = [s.strip().upper() for s in symbols.split(",")]

    stocks_data = []
    backtest_results = []

    for sym in symbol_list:
        history = fetch_stock_history(sym, period="1y")
        if history:
            stock_info = fetch_stock_info(sym)
            stocks_data.append({
                "symbol": sym,
                "technical": analyze_stock(history),
                "fundamental": analyze_fundamental(stock_info),
                "sentiment": analyze_sentiment(sym),
            })
            backtest_results.append(run_backtest(sym, "all"))

    market_data = fetch_market_overview()
    report = generate_report(stocks_data, backtest_results, market_data)

    return {
        "report": report,
        "summary": generate_quick_summary(stocks_data),
    }


class HorizonRequest(BaseModel):
    symbol: str
    horizon_months: Optional[int] = 3


@app.get("/api/stock/{symbol}/horizon")
async def get_horizon_analysis(symbol: str, months: int = Query(3, ge=1, le=12)):
    symbol = symbol.upper()

    history = fetch_stock_history(symbol, period="1y")
    if not history:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    stock_info = fetch_stock_info(symbol)
    fundamental = analyze_fundamental(stock_info)
    sentiment = analyze_sentiment(symbol)
    benchmark = fetch_stock_history("^JKSE", period="1y")

    result = analyze_horizon(
        daily_data=history,
        stock_info=stock_info,
        horizon_months=months,
        sentiment_data=sentiment,
        fundamental_data=fundamental,
        benchmark_data=benchmark,
    )

    return {
        "symbol": symbol,
        "horizon": result,
        "fundamental": fundamental,
        "sentiment": sentiment,
    }


@app.get("/api/stock/{symbol}/horizons")
async def get_all_horizon_analysis(symbol: str):
    symbol = symbol.upper()

    history = fetch_stock_history(symbol, period="1y")
    if not history:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    stock_info = fetch_stock_info(symbol)
    fundamental = analyze_fundamental(stock_info)
    sentiment = analyze_sentiment(symbol)
    benchmark = fetch_stock_history("^JKSE", period="1y")

    all_horizons = get_all_horizons(
        daily_data=history,
        stock_info=stock_info,
        sentiment_data=sentiment,
        fundamental_data=fundamental,
        benchmark_data=benchmark,
    )

    return {
        "symbol": symbol,
        "horizons": all_horizons,
        "fundamental": fundamental,
        "sentiment": sentiment,
    }


@app.post("/api/horizon/analyze")
async def post_horizon_analysis(request: HorizonRequest):
    symbol = request.symbol.upper()

    history = fetch_stock_history(symbol, period="1y")
    if not history:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

    stock_info = fetch_stock_info(symbol)
    fundamental = analyze_fundamental(stock_info)
    sentiment = analyze_sentiment(symbol)
    benchmark = fetch_stock_history("^JKSE", period="1y")

    result = analyze_horizon(
        daily_data=history,
        stock_info=stock_info,
        horizon_months=request.horizon_months,
        sentiment_data=sentiment,
        fundamental_data=fundamental,
        benchmark_data=benchmark,
    )

    return {
        "symbol": symbol,
        "horizon": result,
        "fundamental": fundamental,
        "sentiment": sentiment,
    }


@app.get("/api/portfolio/analyze")
async def analyze_portfolio(symbols: str = Query("BBCA,BBRI,TLKM")):
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    results = []

    for sym in symbol_list:
        history = fetch_stock_history(sym, period="1y")
        if history:
            stock_info = fetch_stock_info(sym)
            results.append({
                "symbol": sym,
                "technical": analyze_stock(history),
                "fundamental": analyze_fundamental(stock_info),
            })

    return {"portfolio": results}


@app.get("/api/portfolio")
async def get_portfolio():
    return {"holdings": portfolio_get_all()}


@app.post("/api/portfolio")
async def upsert_portfolio_holding(request: PortfolioHoldingRequest):
    symbol = request.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol wajib diisi")
    if request.lots <= 0:
        raise HTTPException(status_code=400, detail="Lots harus lebih dari 0")
    if request.avg_price <= 0:
        raise HTTPException(status_code=400, detail="Average price harus lebih dari 0")
    return portfolio_upsert(symbol, request.lots, request.avg_price)


@app.delete("/api/portfolio/{symbol}")
async def delete_portfolio_holding(symbol: str):
    return portfolio_delete(symbol)


@app.delete("/api/portfolio")
async def clear_portfolio():
    return portfolio_clear()


@app.post("/api/consultation/analyze")
async def run_consultation(request: ConsultationRequest):
    holdings = portfolio_get_all()
    if not holdings:
        raise HTTPException(status_code=400, detail="Belum ada holdings. Tambahkan emiten terlebih dahulu.")
    if request.horizon_months < 1 or request.horizon_months > 12:
        raise HTTPException(status_code=400, detail="horizon_months harus 1-12")
    return analyze_portfolio_consultation(holdings, horizon_months=request.horizon_months)


@app.post("/api/consultation/entry")
async def run_entry_consultation(request: EntryConsultationRequest):
    symbols = [s.strip().upper() for s in (request.symbols or []) if s and s.strip()]
    symbols = [s for s in symbols if s]
    if not symbols:
        raise HTTPException(status_code=400, detail="Minimal satu emiten harus diberikan.")
    if len(symbols) > 20:
        raise HTTPException(status_code=400, detail="Maksimal 20 emiten per konsultasi.")
    if request.horizon_months < 1 or request.horizon_months > 12:
        raise HTTPException(status_code=400, detail="horizon_months harus 1-12")
    if request.capital is not None and request.capital <= 0:
        raise HTTPException(status_code=400, detail="capital harus lebih dari 0")
    if request.lots is not None and request.lots < 1:
        raise HTTPException(status_code=400, detail="lots harus lebih dari 0")
    return analyze_entry_consultation(
        symbols,
        horizon_months=request.horizon_months,
        capital=request.capital,
        lots=request.lots,
    )
