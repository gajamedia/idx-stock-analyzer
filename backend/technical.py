import pandas as pd
import numpy as np
import math


def safe_float(val, default=None):
    """Convert a value to float, returning default if NaN or inf."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def safe_round(val, decimals=2, default=None):
    """Round a value safely, returning default if NaN or inf."""
    f = safe_float(val)
    if f is None:
        return default
    return round(f, decimals)


def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return upper_band, sma, lower_band


def calculate_moving_averages(prices):
    ma7 = prices.rolling(window=7).mean()
    ma20 = prices.rolling(window=20).mean()
    ma50 = prices.rolling(window=50).mean()
    ma200 = prices.rolling(window=200).mean()
    return ma7, ma20, ma50, ma200


def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    range_val = highest_high - lowest_low
    range_val = range_val.replace(0, np.nan)
    k = 100 * (close - lowest_low) / range_val
    d = k.rolling(window=d_period).mean()
    return k, d


def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def analyze_stock(prices_data):
    if not prices_data or len(prices_data) < 5:
        return {"error": "Insufficient data"}

    df = pd.DataFrame(prices_data)

    if "Close" not in df.columns and "close" in df.columns:
        df.columns = [c.capitalize() for c in df.columns]

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    rsi = calculate_rsi(close)
    macd_line, signal_line, macd_hist = calculate_macd(close)
    upper, middle, lower = calculate_bollinger_bands(close)
    ma7, ma20, ma50, ma200 = calculate_moving_averages(close)
    stoch_k, stoch_d = calculate_stochastic(high, low, close)
    atr = calculate_atr(high, low, close)

    current_price = safe_float(close.iloc[-1], 0)

    signals = []

    rsi_val = safe_float(rsi.iloc[-1])
    if rsi_val is not None:
        if rsi_val < 30:
            signals.append({"indicator": "RSI", "signal": "OVERSOLD", "value": round(rsi_val, 2), "recommendation": "BUY"})
        elif rsi_val > 70:
            signals.append({"indicator": "RSI", "signal": "OVERBOUGHT", "value": round(rsi_val, 2), "recommendation": "SELL"})
        else:
            signals.append({"indicator": "RSI", "signal": "NEUTRAL", "value": round(rsi_val, 2), "recommendation": "HOLD"})
    else:
        signals.append({"indicator": "RSI", "signal": "N/A", "value": None, "recommendation": "HOLD"})

    macd_val = safe_float(macd_line.iloc[-1], 0)
    signal_val = safe_float(signal_line.iloc[-1], 0)
    macd_val_prev = safe_float(macd_line.iloc[-2], 0)
    signal_val_prev = safe_float(signal_line.iloc[-2], 0)

    if macd_val > signal_val and macd_val_prev <= signal_val_prev:
        signals.append({"indicator": "MACD", "signal": "BULLISH CROSS", "value": round(macd_val, 2), "recommendation": "BUY"})
    elif macd_val < signal_val and macd_val_prev >= signal_val_prev:
        signals.append({"indicator": "MACD", "signal": "BEARISH CROSS", "value": round(macd_val, 2), "recommendation": "SELL"})
    elif macd_val > signal_val:
        signals.append({"indicator": "MACD", "signal": "BULLISH", "value": round(macd_val, 2), "recommendation": "HOLD"})
    else:
        signals.append({"indicator": "MACD", "signal": "BEARISH", "value": round(macd_val, 2), "recommendation": "HOLD"})

    lower_val = safe_float(lower.iloc[-1], current_price)
    upper_val = safe_float(upper.iloc[-1], current_price)
    middle_val = safe_float(middle.iloc[-1], current_price)

    if current_price <= lower_val:
        signals.append({"indicator": "BOLLINGER", "signal": "AT LOWER BAND", "value": round(lower_val, 2), "recommendation": "BUY"})
    elif current_price >= upper_val:
        signals.append({"indicator": "BOLLINGER", "signal": "AT UPPER BAND", "value": round(upper_val, 2), "recommendation": "SELL"})
    else:
        signals.append({"indicator": "BOLLINGER", "signal": "IN RANGE", "value": round(middle_val, 2), "recommendation": "HOLD"})

    ma50_val = safe_float(ma50.iloc[-1])
    ma200_val = safe_float(ma200.iloc[-1])
    if ma50_val is not None and ma200_val is not None:
        ma50_prev = safe_float(ma50.iloc[-2])
        ma200_prev = safe_float(ma200.iloc[-2])
        if ma50_prev is not None and ma200_prev is not None:
            if ma50_val > ma200_val and ma50_prev <= ma200_prev:
                signals.append({"indicator": "GOLDEN CROSS", "signal": "MA50 > MA200", "recommendation": "STRONG BUY"})
            elif ma50_val < ma200_val and ma50_prev >= ma200_prev:
                signals.append({"indicator": "DEATH CROSS", "signal": "MA50 < MA200", "recommendation": "STRONG SELL"})
            elif ma50_val > ma200_val:
                signals.append({"indicator": "TREND", "signal": "UPTREND", "recommendation": "BUY"})
            else:
                signals.append({"indicator": "TREND", "signal": "DOWNTREND", "recommendation": "SELL"})

    buy_count = sum(1 for s in signals if "BUY" in s.get("recommendation", ""))
    sell_count = sum(1 for s in signals if "SELL" in s.get("recommendation", ""))

    if buy_count > sell_count + 1:
        overall = "STRONG BUY"
    elif buy_count > sell_count:
        overall = "BUY"
    elif sell_count > buy_count + 1:
        overall = "STRONG SELL"
    elif sell_count > buy_count:
        overall = "SELL"
    else:
        overall = "HOLD"

    chart_data = []
    for i in range(max(0, len(close) - 90), len(close)):
        chart_data.append({
            "date": str(df["Date"].iloc[i]) if "Date" in df.columns else str(i),
            "close": safe_round(close.iloc[i], 2, 0),
            "ma7": safe_round(ma7.iloc[i], 2),
            "ma20": safe_round(ma20.iloc[i], 2),
            "ma50": safe_round(ma50.iloc[i], 2),
            "upper_bb": safe_round(upper.iloc[i], 2),
            "lower_bb": safe_round(lower.iloc[i], 2),
            "rsi": safe_round(rsi.iloc[i], 2),
            "macd": safe_round(macd_line.iloc[i], 2),
            "macd_signal": safe_round(signal_line.iloc[i], 2),
        })

    return {
        "current_price": safe_round(current_price, 2, 0),
        "rsi": safe_round(rsi_val, 2, 50),
        "macd": {"macd": safe_round(macd_val, 2, 0), "signal": safe_round(signal_val, 2, 0)},
        "bollinger": {"upper": safe_round(upper_val, 2, 0), "middle": safe_round(middle_val, 2, 0), "lower": safe_round(lower_val, 2, 0)},
        "moving_averages": {
            "ma7": safe_round(ma7.iloc[-1], 2),
            "ma20": safe_round(ma20.iloc[-1], 2),
            "ma50": safe_round(ma50.iloc[-1], 2),
            "ma200": safe_round(ma200.iloc[-1], 2),
        },
        "atr": safe_round(atr.iloc[-1], 2),
        "signals": signals,
        "overall_signal": overall,
        "chart_data": chart_data,
    }
