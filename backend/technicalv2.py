import pandas as pd
import numpy as np
import math


# ============================================================
# SAFE UTILITIES
# ============================================================

def safe_float(val, default=None):
    """
    Convert value to float.
    Return default if None, NaN or infinity.
    """
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
    """
    Safe rounding.
    """
    f = safe_float(val)

    if f is None:
        return default

    return round(f, decimals)


# ============================================================
# WILDER RMA
# ============================================================

def wilder_rma(series, period):
    """
    Wilder's Moving Average / RMA.

    RMA:
        RMA_t = ((RMA_(t-1) * (period - 1)) + value_t) / period

    Equivalent to EMA with alpha = 1 / period.
    """

    return series.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


# ============================================================
# RSI
# ============================================================

def calculate_rsi(prices, period=14):
    """
    RSI menggunakan Wilder's smoothing.
    """

    delta = prices.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = wilder_rma(gain, period)
    avg_loss = wilder_rma(loss, period)

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    # Jika gain ada tetapi loss = 0 -> RSI = 100
    rsi = rsi.where(
        avg_loss != 0,
        np.where(avg_gain > 0, 100, 50)
    )

    return rsi.clip(0, 100)


# ============================================================
# MACD
# ============================================================

def calculate_macd(
    prices,
    fast=12,
    slow=26,
    signal=9
):
    """
    MACD standard:

        MACD = EMA12 - EMA26
        Signal = EMA9(MACD)
        Histogram = MACD - Signal
    """

    ema_fast = prices.ewm(
        span=fast,
        adjust=False,
        min_periods=fast
    ).mean()

    ema_slow = prices.ewm(
        span=slow,
        adjust=False,
        min_periods=slow
    ).mean()

    macd_line = ema_fast - ema_slow

    signal_line = macd_line.ewm(
        span=signal,
        adjust=False,
        min_periods=signal
    ).mean()

    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


# ============================================================
# BOLLINGER BANDS
# ============================================================

def calculate_bollinger_bands(
    prices,
    period=20,
    std_dev=2
):
    """
    Bollinger Bands:

        Middle = SMA20
        Upper  = Middle + 2 * StdDev
        Lower  = Middle - 2 * StdDev
    """

    middle = prices.rolling(
        window=period,
        min_periods=period
    ).mean()

    std = prices.rolling(
        window=period,
        min_periods=period
    ).std(ddof=0)

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    return upper, middle, lower


# ============================================================
# MOVING AVERAGES
# ============================================================

def calculate_moving_averages(prices):
    """
    Simple Moving Average.
    """

    ma7 = prices.rolling(
        window=7,
        min_periods=7
    ).mean()

    ma20 = prices.rolling(
        window=20,
        min_periods=20
    ).mean()

    ma50 = prices.rolling(
        window=50,
        min_periods=50
    ).mean()

    ma200 = prices.rolling(
        window=200,
        min_periods=200
    ).mean()

    return ma7, ma20, ma50, ma200


# ============================================================
# STOCHASTIC
# ============================================================

def calculate_stochastic(
    high,
    low,
    close,
    k_period=14,
    d_period=3
):
    """
    Stochastic Oscillator.

        %K = 100 * (Close - LowestLow)
                    / (HighestHigh - LowestLow)

        %D = SMA3(%K)
    """

    lowest_low = low.rolling(
        window=k_period,
        min_periods=k_period
    ).min()

    highest_high = high.rolling(
        window=k_period,
        min_periods=k_period
    ).max()

    range_val = highest_high - lowest_low

    k = (
        100 *
        (close - lowest_low) /
        range_val.replace(0, np.nan)
    )

    d = k.rolling(
        window=d_period,
        min_periods=d_period
    ).mean()

    return k, d


# ============================================================
# ATR
# ============================================================

def calculate_atr(
    high,
    low,
    close,
    period=14
):
    """
    ATR menggunakan True Range + Wilder RMA.
    """

    previous_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - previous_close).abs()
    tr3 = (low - previous_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = wilder_rma(
        true_range,
        period
    )

    return atr


# ============================================================
# CROSSOVER
# ============================================================

def crossed_above(current_a, current_b, previous_a, previous_b):
    """
    A melakukan bullish crossover terhadap B.
    """

    return (
        current_a > current_b
        and previous_a <= previous_b
    )


def crossed_below(current_a, current_b, previous_a, previous_b):
    """
    A melakukan bearish crossover terhadap B.
    """

    return (
        current_a < current_b
        and previous_a >= previous_b
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_stock(prices_data):

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not prices_data:
        return {
            "error": "No price data"
        }

    df = pd.DataFrame(prices_data)

    # Normalize column names
    df.columns = [str(c).capitalize() for c in df.columns]

    required_columns = [
        "Close",
        "High",
        "Low"
    ]

    missing = [
        c for c in required_columns
        if c not in df.columns
    ]

    if missing:
        return {
            "error": f"Missing columns: {', '.join(missing)}"
        }

    # --------------------------------------------------------
    # CLEAN DATA
    # --------------------------------------------------------

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    df = df.dropna(
        subset=["High", "Low", "Close"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # MINIMUM DATA
    # --------------------------------------------------------

    if len(df) < 50:
        return {
            "error": (
                "Insufficient data. "
                "At least 50 candles are recommended."
            )
        }

    # --------------------------------------------------------
    # PRICE SERIES
    # --------------------------------------------------------

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    current_price = safe_float(
        close.iloc[-1]
    )

    # --------------------------------------------------------
    # INDICATORS
    # --------------------------------------------------------

    rsi = calculate_rsi(close)

    macd_line, signal_line, macd_hist = calculate_macd(
        close
    )

    upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(
        close
    )

    ma7, ma20, ma50, ma200 = calculate_moving_averages(
        close
    )

    stoch_k, stoch_d = calculate_stochastic(
        high,
        low,
        close
    )

    atr = calculate_atr(
        high,
        low,
        close
    )

    # --------------------------------------------------------
    # CURRENT VALUES
    # --------------------------------------------------------

    rsi_val = safe_float(
        rsi.iloc[-1]
    )

    rsi_prev = safe_float(
        rsi.iloc[-2]
    )

    macd_val = safe_float(
        macd_line.iloc[-1]
    )

    signal_val = safe_float(
        signal_line.iloc[-1]
    )

    macd_prev = safe_float(
        macd_line.iloc[-2]
    )

    signal_prev = safe_float(
        signal_line.iloc[-2]
    )

    histogram_val = safe_float(
        macd_hist.iloc[-1]
    )

    histogram_prev = safe_float(
        macd_hist.iloc[-2]
    )

    upper_val = safe_float(
        upper_bb.iloc[-1]
    )

    middle_val = safe_float(
        middle_bb.iloc[-1]
    )

    lower_val = safe_float(
        lower_bb.iloc[-1]
    )

    stoch_k_val = safe_float(
        stoch_k.iloc[-1]
    )

    stoch_d_val = safe_float(
        stoch_d.iloc[-1]
    )

    stoch_k_prev = safe_float(
        stoch_k.iloc[-2]
    )

    stoch_d_prev = safe_float(
        stoch_d.iloc[-2]
    )

    ma7_val = safe_float(
        ma7.iloc[-1]
    )

    ma20_val = safe_float(
        ma20.iloc[-1]
    )

    ma50_val = safe_float(
        ma50.iloc[-1]
    )

    ma200_val = safe_float(
        ma200.iloc[-1]
    )

    atr_val = safe_float(
        atr.iloc[-1]
    )

    # ========================================================
    # SIGNALS
    # ========================================================

    signals = []

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if rsi_val is not None:

        if rsi_val < 30:

            signals.append({
                "indicator": "RSI",
                "signal": "OVERSOLD",
                "value": round(rsi_val, 2),
                "score": 1,
                "recommendation": "BUY"
            })

        elif rsi_val > 70:

            signals.append({
                "indicator": "RSI",
                "signal": "OVERBOUGHT",
                "value": round(rsi_val, 2),
                "score": -1,
                "recommendation": "SELL"
            })

        elif rsi_val > 50:

            signals.append({
                "indicator": "RSI",
                "signal": "BULLISH",
                "value": round(rsi_val, 2),
                "score": 1,
                "recommendation": "BUY"
            })

        else:

            signals.append({
                "indicator": "RSI",
                "signal": "BEARISH",
                "value": round(rsi_val, 2),
                "score": -1,
                "recommendation": "SELL"
            })

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if (
        macd_val is not None
        and signal_val is not None
        and macd_prev is not None
        and signal_prev is not None
    ):

        if crossed_above(
            macd_val,
            signal_val,
            macd_prev,
            signal_prev
        ):

            signals.append({
                "indicator": "MACD",
                "signal": "BULLISH CROSS",
                "value": round(macd_val, 4),
                "score": 2,
                "recommendation": "BUY"
            })

        elif crossed_below(
            macd_val,
            signal_val,
            macd_prev,
            signal_prev
        ):

            signals.append({
                "indicator": "MACD",
                "signal": "BEARISH CROSS",
                "value": round(macd_val, 4),
                "score": -2,
                "recommendation": "SELL"
            })

        elif macd_val > signal_val:

            signals.append({
                "indicator": "MACD",
                "signal": "BULLISH",
                "value": round(macd_val, 4),
                "score": 1,
                "recommendation": "BUY"
            })

        else:

            signals.append({
                "indicator": "MACD",
                "signal": "BEARISH",
                "value": round(macd_val, 4),
                "score": -1,
                "recommendation": "SELL"
            })

    # --------------------------------------------------------
    # BOLLINGER
    # --------------------------------------------------------

    if (
        upper_val is not None
        and middle_val is not None
        and lower_val is not None
    ):

        if current_price < lower_val:

            signals.append({
                "indicator": "BOLLINGER",
                "signal": "BELOW LOWER BAND",
                "value": round(lower_val, 2),
                "score": 1,
                "recommendation": "BUY"
            })

        elif current_price > upper_val:

            signals.append({
                "indicator": "BOLLINGER",
                "signal": "ABOVE UPPER BAND",
                "value": round(upper_val, 2),
                "score": -1,
                "recommendation": "SELL"
            })

        elif current_price > middle_val:

            signals.append({
                "indicator": "BOLLINGER",
                "signal": "ABOVE MIDDLE",
                "value": round(middle_val, 2),
                "score": 1,
                "recommendation": "BUY"
            })

        else:

            signals.append({
                "indicator": "BOLLINGER",
                "signal": "BELOW MIDDLE",
                "value": round(middle_val, 2),
                "score": -1,
                "recommendation": "SELL"
            })

    # --------------------------------------------------------
    # MOVING AVERAGE TREND
    # --------------------------------------------------------

    if ma20_val is not None and ma50_val is not None:

        if ma20_val > ma50_val:

            signals.append({
                "indicator": "TREND",
                "signal": "MA20 > MA50",
                "value": round(ma20_val, 2),
                "score": 1,
                "recommendation": "BUY"
            })

        else:

            signals.append({
                "indicator": "TREND",
                "signal": "MA20 < MA50",
                "value": round(ma20_val, 2),
                "score": -1,
                "recommendation": "SELL"
            })

    # --------------------------------------------------------
    # LONG TERM TREND
    # --------------------------------------------------------

    if (
        ma50_val is not None
        and ma200_val is not None
    ):

        ma50_prev = safe_float(
            ma50.iloc[-2]
        )

        ma200_prev = safe_float(
            ma200.iloc[-2]
        )

        if (
            ma50_prev is not None
            and ma200_prev is not None
        ):

            if crossed_above(
                ma50_val,
                ma200_val,
                ma50_prev,
                ma200_prev
            ):

                signals.append({
                    "indicator": "MA",
                    "signal": "GOLDEN CROSS",
                    "value": round(ma50_val, 2),
                    "score": 3,
                    "recommendation": "BUY"
                })

            elif crossed_below(
                ma50_val,
                ma200_val,
                ma50_prev,
                ma200_prev
            ):

                signals.append({
                    "indicator": "MA",
                    "signal": "DEATH CROSS",
                    "value": round(ma50_val, 2),
                    "score": -3,
                    "recommendation": "SELL"
                })

            elif ma50_val > ma200_val:

                signals.append({
                    "indicator": "LONG TERM TREND",
                    "signal": "BULLISH",
                    "value": round(ma50_val, 2),
                    "score": 2,
                    "recommendation": "BUY"
                })

            else:

                signals.append({
                    "indicator": "LONG TERM TREND",
                    "signal": "BEARISH",
                    "value": round(ma50_val, 2),
                    "score": -2,
                    "recommendation": "SELL"
                })

    # --------------------------------------------------------
    # STOCHASTIC
    # --------------------------------------------------------

    if (
        stoch_k_val is not None
        and stoch_d_val is not None
        and stoch_k_prev is not None
        and stoch_d_prev is not None
    ):

        if crossed_above(
            stoch_k_val,
            stoch_d_val,
            stoch_k_prev,
            stoch_d_prev
        ) and stoch_k_val < 30:

            signals.append({
                "indicator": "STOCHASTIC",
                "signal": "BULLISH CROSS IN OVERSOLD",
                "value": round(stoch_k_val, 2),
                "score": 2,
                "recommendation": "BUY"
            })

        elif crossed_below(
            stoch_k_val,
            stoch_d_val,
            stoch_k_prev,
            stoch_d_prev
        ) and stoch_k_val > 70:

            signals.append({
                "indicator": "STOCHASTIC",
                "signal": "BEARISH CROSS IN OVERBOUGHT",
                "value": round(stoch_k_val, 2),
                "score": -2,
                "recommendation": "SELL"
            })

        elif stoch_k_val > 50:

            signals.append({
                "indicator": "STOCHASTIC",
                "signal": "BULLISH",
                "value": round(stoch_k_val, 2),
                "score": 1,
                "recommendation": "BUY"
            })

        else:

            signals.append({
                "indicator": "STOCHASTIC",
                "signal": "BEARISH",
                "value": round(stoch_k_val, 2),
                "score": -1,
                "recommendation": "SELL"
            })

    # ========================================================
    # TOTAL SCORE
    # ========================================================

    total_score = sum(
        s.get("score", 0)
        for s in signals
    )

    buy_count = sum(
        1 for s in signals
        if s.get("score", 0) > 0
    )

    sell_count = sum(
        1 for s in signals
        if s.get("score", 0) < 0
    )

    # --------------------------------------------------------
    # OVERALL SIGNAL
    # --------------------------------------------------------

    if total_score >= 5:

        overall = "STRONG BUY"

    elif total_score >= 2:

        overall = "BUY"

    elif total_score <= -5:

        overall = "STRONG SELL"

    elif total_score <= -2:

        overall = "SELL"

    else:

        overall = "HOLD"

    # ========================================================
    # VOLATILITY
    # ========================================================

    atr_percent = None

    if (
        atr_val is not None
        and current_price is not None
        and current_price != 0
    ):

        atr_percent = (
            atr_val / current_price
        ) * 100

    # ========================================================
    # CHART DATA
    # ========================================================

    chart_data = []

    start_index = max(
        0,
        len(df) - 90
    )

    for i in range(
        start_index,
        len(df)
    ):

        chart_data.append({

            "date": (
                str(df["Date"].iloc[i])
                if "Date" in df.columns
                else str(i)
            ),

            "close": safe_round(
                close.iloc[i],
                2,
                0
            ),

            "ma7": safe_round(
                ma7.iloc[i],
                2
            ),

            "ma20": safe_round(
                ma20.iloc[i],
                2
            ),

            "ma50": safe_round(
                ma50.iloc[i],
                2
            ),

            "ma200": safe_round(
                ma200.iloc[i],
                2
            ),

            "upper_bb": safe_round(
                upper_bb.iloc[i],
                2
            ),

            "middle_bb": safe_round(
                middle_bb.iloc[i],
                2
            ),

            "lower_bb": safe_round(
                lower_bb.iloc[i],
                2
            ),

            "rsi": safe_round(
                rsi.iloc[i],
                2
            ),

            "stoch_k": safe_round(
                stoch_k.iloc[i],
                2
            ),

            "stoch_d": safe_round(
                stoch_d.iloc[i],
                2
            ),

            "macd": safe_round(
                macd_line.iloc[i],
                4
            ),

            "macd_signal": safe_round(
                signal_line.iloc[i],
                4
            ),

            "macd_histogram": safe_round(
                macd_hist.iloc[i],
                4
            ),

            "atr": safe_round(
                atr.iloc[i],
                2
            )
        })

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "current_price": safe_round(
            current_price,
            2,
            0
        ),

        "rsi": safe_round(
            rsi_val,
            2
        ),

        "macd": {

            "macd": safe_round(
                macd_val,
                4
            ),

            "signal": safe_round(
                signal_val,
                4
            ),

            "histogram": safe_round(
                histogram_val,
                4
            )
        },

        "bollinger": {

            "upper": safe_round(
                upper_val,
                2
            ),

            "middle": safe_round(
                middle_val,
                2
            ),

            "lower": safe_round(
                lower_val,
                2
            )
        },

        "moving_averages": {

            "ma7": safe_round(
                ma7_val,
                2
            ),

            "ma20": safe_round(
                ma20_val,
                2
            ),

            "ma50": safe_round(
                ma50_val,
                2
            ),

            "ma200": safe_round(
                ma200_val,
                2
            )
        },

        "stochastic": {

            "k": safe_round(
                stoch_k_val,
                2
            ),

            "d": safe_round(
                stoch_d_val,
                2
            )
        },

        "atr": {

            "value": safe_round(
                atr_val,
                2
            ),

            "percent": safe_round(
                atr_percent,
                2
            )
        },

        "score": total_score,

        "buy_count": buy_count,

        "sell_count": sell_count,

        "signals": signals,

        "overall_signal": overall,

        "chart_data": chart_data
    }

