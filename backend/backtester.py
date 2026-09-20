import pandas as pd
import numpy as np
from datetime import datetime


def calculate_returns(prices):
    return prices.pct_change().dropna()


def backtest_rsi_strategy(prices, period=14, oversold=30, overbought=70, initial_capital=1000000):
    df = pd.DataFrame(prices)
    close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]

    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    position = 0
    cash = initial_capital
    shares = 0
    trades = []
    equity_curve = []

    for i in range(period, len(close)):
        current_price = float(close.iloc[i])
        current_rsi = float(rsi.iloc[i])

        if pd.isna(current_rsi) or current_price <= 0:
            equity = cash + (shares * current_price)
            equity_curve.append({"date": str(close.index[i]), "equity": round(equity, 2)})
            continue

        if current_rsi < oversold and position == 0:
            shares = int(cash / current_price)
            if shares > 0:
                cost = shares * current_price
                cash -= cost
                position = 1
                trades.append({"date": str(close.index[i]), "action": "BUY", "price": round(current_price, 2), "shares": shares, "rsi": round(current_rsi, 2)})

        elif current_rsi > overbought and position == 1:
            revenue = shares * current_price
            cash += revenue
            trades.append({"date": str(close.index[i]), "action": "SELL", "price": round(current_price, 2), "shares": shares, "rsi": round(current_rsi, 2), "pnl": round(revenue - (initial_capital - cash), 2)})
            shares = 0
            position = 0

        equity = cash + (shares * current_price)
        equity_curve.append({"date": str(close.index[i]), "equity": round(equity, 2)})

    final_price = float(close.iloc[-1]) if not pd.isna(close.iloc[-1]) else 0
    final_equity = cash + (shares * final_price)
    total_return = ((final_equity - initial_capital) / initial_capital) * 100

    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    total_trades = sum(1 for t in trades if t["action"] == "SELL")
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    return {
        "strategy": "RSI Oversold/Overbought",
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return, 2),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "trades": trades,
        "equity_curve": equity_curve,
    }


def backtest_macd_crossover(prices, fast=12, slow=26, signal_period=9, initial_capital=1000000):
    df = pd.DataFrame(prices)
    close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    position = 0
    cash = initial_capital
    shares = 0
    trades = []
    equity_curve = []

    for i in range(1, len(close)):
        current_price = close.iloc[i]

        if macd_line.iloc[i] > signal_line.iloc[i] and macd_line.iloc[i - 1] <= signal_line.iloc[i - 1] and position == 0:
            shares = int(cash / current_price)
            if shares > 0:
                cash -= shares * current_price
                position = 1
                trades.append({"date": str(close.index[i]), "action": "BUY", "price": round(current_price, 2), "shares": shares})

        elif macd_line.iloc[i] < signal_line.iloc[i] and macd_line.iloc[i - 1] >= signal_line.iloc[i - 1] and position == 1:
            revenue = shares * current_price
            cash += revenue
            trades.append({"date": str(close.index[i]), "action": "SELL", "price": round(current_price, 2), "shares": shares})
            shares = 0
            position = 0

        equity = cash + (shares * current_price)
        equity_curve.append({"date": str(close.index[i]), "equity": round(equity, 2)})

    final_equity = cash + (shares * close.iloc[-1])
    total_return = ((final_equity - initial_capital) / initial_capital) * 100
    wins = sum(1 for i in range(1, len(trades), 2) if i < len(trades) and trades[i].get("price", 0) > trades[i - 1].get("price", 0))
    total_trades = sum(1 for t in trades if t["action"] == "SELL")
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    return {
        "strategy": "MACD Crossover",
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return, 2),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "trades": trades,
        "equity_curve": equity_curve,
    }


def backtest_ma_crossover(prices, short_period=20, long_period=50, initial_capital=1000000):
    df = pd.DataFrame(prices)
    close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]

    ma_short = close.rolling(window=short_period).mean()
    ma_long = close.rolling(window=long_period).mean()

    position = 0
    cash = initial_capital
    shares = 0
    trades = []
    equity_curve = []

    for i in range(long_period, len(close)):
        current_price = close.iloc[i]

        if pd.notna(ma_short.iloc[i]) and pd.notna(ma_long.iloc[i]):
            if ma_short.iloc[i] > ma_long.iloc[i] and ma_short.iloc[i - 1] <= ma_long.iloc[i - 1] and position == 0:
                shares = int(cash / current_price)
                if shares > 0:
                    cash -= shares * current_price
                    position = 1
                    trades.append({"date": str(close.index[i]), "action": "BUY", "price": round(current_price, 2), "shares": shares})

            elif ma_short.iloc[i] < ma_long.iloc[i] and ma_short.iloc[i - 1] >= ma_long.iloc[i - 1] and position == 1:
                revenue = shares * current_price
                cash += revenue
                trades.append({"date": str(close.index[i]), "action": "SELL", "price": round(current_price, 2), "shares": shares})
                shares = 0
                position = 0

        equity = cash + (shares * current_price)
        equity_curve.append({"date": str(close.index[i]), "equity": round(equity, 2)})

    final_equity = cash + (shares * close.iloc[-1])
    total_return = ((final_equity - initial_capital) / initial_capital) * 100
    wins = sum(1 for i in range(1, len(trades), 2) if i < len(trades) and trades[i].get("price", 0) > trades[i - 1].get("price", 0))
    total_trades = sum(1 for t in trades if t["action"] == "SELL")
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    return {
        "strategy": f"MA Crossover ({short_period}/{long_period})",
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return, 2),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "trades": trades,
        "equity_curve": equity_curve,
    }


def run_backtest(symbol, strategy="all", initial_capital=1000000):
    from data_fetcher import fetch_stock_history

    prices = fetch_stock_history(symbol, period="2y")
    if not prices:
        return {"error": "Cannot fetch historical data"}

    results = []
    if strategy in ["all", "rsi"]:
        results.append(backtest_rsi_strategy(prices, initial_capital=initial_capital))
    if strategy in ["all", "macd"]:
        results.append(backtest_macd_crossover(prices, initial_capital=initial_capital))
    if strategy in ["all", "ma"]:
        results.append(backtest_ma_crossover(prices, initial_capital=initial_capital))

    best = max(results, key=lambda x: x.get("total_return_pct", 0)) if results else None

    return {
        "symbol": symbol,
        "strategies": results,
        "best_strategy": best["strategy"] if best else "N/A",
        "best_return": best["total_return_pct"] if best else 0,
    }
