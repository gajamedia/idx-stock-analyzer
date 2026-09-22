import pandas as pd
import numpy as np
import math


# ============================================================
# TECHNICAL ANALYSIS ENGINE v3
#
# Features:
#   - RSI Wilder
#   - MACD
#   - Bollinger Bands
#   - MA7 / MA20 / MA50 / MA200
#   - Stochastic
#   - ATR Wilder
#   - Volume Ratio
#   - OBV
#   - ADX / +DI / -DI
#   - Support / Resistance
#   - Breakout / Breakdown
#   - Market Regime
#   - Weighted Scoring
#   - ATR-based Entry / Stop Loss / Take Profit
#   - Risk / Reward
#   - Confidence Score
#
# NOTE:
# Confidence is a signal-consistency score, NOT probability.
# ============================================================


# ============================================================
# SAFE UTILITIES
# ============================================================

def safe_float(value, default=None):

    if value is None:
        return default

    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def safe_round(value, decimals=2, default=None):

    value = safe_float(value)

    if value is None:
        return default

    return round(value, decimals)


# ============================================================
# WILDER RMA
# ============================================================

def wilder_rma(series, period):

    return series.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


# ============================================================
# RSI
# ============================================================

def calculate_rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = wilder_rma(
        gain,
        period
    )

    avg_loss = wilder_rma(
        loss,
        period
    )

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    # No losses => RSI 100, no gains => RSI 0
    rsi = rsi.where(
        avg_loss != 0,
        np.where(
            avg_gain > 0,
            100,
            50
        )
    )

    return rsi.clip(0, 100)


# ============================================================
# MACD
# ============================================================

def calculate_macd(
    close,
    fast=12,
    slow=26,
    signal=9
):

    ema_fast = close.ewm(
        span=fast,
        adjust=False,
        min_periods=fast
    ).mean()

    ema_slow = close.ewm(
        span=slow,
        adjust=False,
        min_periods=slow
    ).mean()

    macd = ema_fast - ema_slow

    signal_line = macd.ewm(
        span=signal,
        adjust=False,
        min_periods=signal
    ).mean()

    histogram = macd - signal_line

    return (
        macd,
        signal_line,
        histogram
    )


# ============================================================
# BOLLINGER BANDS
# ============================================================

def calculate_bollinger(
    close,
    period=20,
    std_dev=2
):

    middle = close.rolling(
        period,
        min_periods=period
    ).mean()

    std = close.rolling(
        period,
        min_periods=period
    ).std(ddof=0)

    upper = middle + (
        std_dev * std
    )

    lower = middle - (
        std_dev * std
    )

    return (
        upper,
        middle,
        lower
    )


# ============================================================
# MOVING AVERAGES
# ============================================================

def calculate_moving_averages(close):

    ma7 = close.rolling(
        7,
        min_periods=7
    ).mean()

    ma20 = close.rolling(
        20,
        min_periods=20
    ).mean()

    ma50 = close.rolling(
        50,
        min_periods=50
    ).mean()

    ma200 = close.rolling(
        200,
        min_periods=200
    ).mean()

    return (
        ma7,
        ma20,
        ma50,
        ma200
    )


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

    lowest_low = low.rolling(
        k_period,
        min_periods=k_period
    ).min()

    highest_high = high.rolling(
        k_period,
        min_periods=k_period
    ).max()

    range_value = (
        highest_high -
        lowest_low
    )

    k = (
        100 *
        (close - lowest_low) /
        range_value.replace(
            0,
            np.nan
        )
    )

    d = k.rolling(
        d_period,
        min_periods=d_period
    ).mean()

    return (
        k,
        d
    )


# ============================================================
# ATR
# ============================================================

def calculate_atr(
    high,
    low,
    close,
    period=14
):

    previous_close = close.shift(1)

    tr1 = high - low

    tr2 = (
        high -
        previous_close
    ).abs()

    tr3 = (
        low -
        previous_close
    ).abs()

    true_range = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1)

    atr = wilder_rma(
        true_range,
        period
    )

    return atr


# ============================================================
# OBV
# ============================================================

def calculate_obv(close, volume):

    direction = np.sign(
        close.diff()
    ).fillna(0)

    obv = (
        direction *
        volume.fillna(0)
    ).cumsum()

    return obv


# ============================================================
# ADX
# ============================================================

def calculate_adx(
    high,
    low,
    close,
    period=14
):

    previous_high = high.shift(1)
    previous_low = low.shift(1)
    previous_close = close.shift(1)

    # --------------------------------------------------------
    # True Range
    # --------------------------------------------------------

    tr1 = high - low

    tr2 = (
        high -
        previous_close
    ).abs()

    tr3 = (
        low -
        previous_close
    ).abs()

    tr = pd.concat(
        [
            tr1,
            tr2,
            tr3
        ],
        axis=1
    ).max(axis=1)

    # --------------------------------------------------------
    # Directional Movement
    # --------------------------------------------------------

    up_move = (
        high -
        previous_high
    )

    down_move = (
        previous_low -
        low
    )

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move) &
            (up_move > 0),
            up_move,
            0
        ),
        index=high.index
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move) &
            (down_move > 0),
            down_move,
            0
        ),
        index=high.index
    )

    # --------------------------------------------------------
    # Wilder smoothing
    # --------------------------------------------------------

    atr = wilder_rma(
        tr,
        period
    )

    plus_dm_smoothed = wilder_rma(
        plus_dm,
        period
    )

    minus_dm_smoothed = wilder_rma(
        minus_dm,
        period
    )

    # --------------------------------------------------------
    # DI
    # --------------------------------------------------------

    plus_di = (
        100 *
        plus_dm_smoothed /
        atr.replace(0, np.nan)
    )

    minus_di = (
        100 *
        minus_dm_smoothed /
        atr.replace(0, np.nan)
    )

    # --------------------------------------------------------
    # DX
    # --------------------------------------------------------

    di_sum = (
        plus_di +
        minus_di
    )

    dx = (
        100 *
        (plus_di - minus_di).abs() /
        di_sum.replace(
            0,
            np.nan
        )
    )

    # --------------------------------------------------------
    # ADX
    # --------------------------------------------------------

    adx = wilder_rma(
        dx,
        period
    )

    return (
        adx,
        plus_di,
        minus_di
    )


# ============================================================
# VOLUME ANALYSIS
# ============================================================

def calculate_volume_ratio(
    volume,
    period=20
):

    average_volume = volume.rolling(
        period,
        min_periods=period
    ).mean()

    ratio = (
        volume /
        average_volume.replace(
            0,
            np.nan
        )
    )

    return ratio


# ============================================================
# OBV TREND
# ============================================================

def calculate_obv_trend(
    obv,
    period=20
):

    obv_ma = obv.rolling(
        period,
        min_periods=period
    ).mean()

    return obv_ma


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def calculate_support_resistance(
    high,
    low,
    close,
    lookback=20
):

    resistance = high.shift(1).rolling(
        lookback,
        min_periods=lookback
    ).max()

    support = low.shift(1).rolling(
        lookback,
        min_periods=lookback
    ).min()

    return (
        support,
        resistance
    )


# ============================================================
# BREAKOUT DETECTION
# ============================================================

def detect_breakout(
    close,
    high,
    low,
    volume,
    support,
    resistance,
    volume_ratio,
    breakout_buffer=0.002,
    volume_threshold=1.2
):

    current_close = close.iloc[-1]

    previous_resistance = resistance.iloc[-1]
    previous_support = support.iloc[-1]

    current_volume_ratio = (
        safe_float(
            volume_ratio.iloc[-1]
        )
    )

    breakout = False
    breakdown = False

    # --------------------------------------------------------
    # Breakout
    # --------------------------------------------------------

    if previous_resistance is not None:

        if current_close > (
            previous_resistance *
            (1 + breakout_buffer)
        ):

            breakout = True

    # --------------------------------------------------------
    # Breakdown
    # --------------------------------------------------------

    if previous_support is not None:

        if current_close < (
            previous_support *
            (1 - breakout_buffer)
        ):

            breakdown = True

    # --------------------------------------------------------
    # Volume confirmation
    # --------------------------------------------------------

    volume_confirmed = (
        current_volume_ratio is not None
        and
        current_volume_ratio >= volume_threshold
    )

    return {
        "breakout": breakout,
        "breakdown": breakdown,
        "volume_confirmed": volume_confirmed
    }


# ============================================================
# MA SLOPE
# ============================================================

def calculate_slope(
    series,
    periods=5
):

    current = safe_float(
        series.iloc[-1]
    )

    previous = safe_float(
        series.iloc[-1 - periods]
    )

    if (
        current is None
        or previous is None
        or previous == 0
    ):
        return None

    return (
        (current - previous) /
        abs(previous)
    ) * 100


# ============================================================
# MARKET REGIME
# ============================================================

def determine_market_regime(
    close,
    ma20,
    ma50,
    ma200,
    adx,
    plus_di,
    minus_di
):

    price = safe_float(
        close.iloc[-1]
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

    adx_val = safe_float(
        adx.iloc[-1]
    )

    plus_di_val = safe_float(
        plus_di.iloc[-1]
    )

    minus_di_val = safe_float(
        minus_di.iloc[-1]
    )

    slope20 = calculate_slope(
        ma20,
        5
    )

    slope50 = calculate_slope(
        ma50,
        5
    )

    # --------------------------------------------------------
    # Insufficient data
    # --------------------------------------------------------

    if price is None:

        return {
            "regime": "UNKNOWN",
            "trend": "UNKNOWN",
            "strength": "UNKNOWN"
        }

    # --------------------------------------------------------
    # Strong Uptrend
    # --------------------------------------------------------

    if (
        ma200_val is not None
        and ma50_val is not None
        and ma20_val is not None
        and adx_val is not None
        and plus_di_val is not None
        and minus_di_val is not None
        and
        price > ma20_val > ma50_val > ma200_val
        and adx_val >= 25
        and plus_di_val > minus_di_val
    ):

        return {
            "regime": "STRONG_UPTREND",
            "trend": "BULLISH",
            "strength": "STRONG",
            "adx": adx_val,
            "ma20_slope": slope20,
            "ma50_slope": slope50
        }

    # --------------------------------------------------------
    # Uptrend
    # --------------------------------------------------------

    if (
        ma50_val is not None
        and
        price > ma50_val
        and
        adx_val is not None
        and
        adx_val >= 18
        and
        plus_di_val is not None
        and
        minus_di_val is not None
        and
        plus_di_val > minus_di_val
    ):

        return {
            "regime": "UPTREND",
            "trend": "BULLISH",
            "strength": "MODERATE",
            "adx": adx_val,
            "ma20_slope": slope20,
            "ma50_slope": slope50
        }

    # --------------------------------------------------------
    # Strong Downtrend
    # --------------------------------------------------------

    if (
        ma200_val is not None
        and ma50_val is not None
        and ma20_val is not None
        and adx_val is not None
        and plus_di_val is not None
        and minus_di_val is not None
        and
        price < ma20_val < ma50_val < ma200_val
        and adx_val >= 25
        and minus_di_val > plus_di_val
    ):

        return {
            "regime": "STRONG_DOWNTREND",
            "trend": "BEARISH",
            "strength": "STRONG",
            "adx": adx_val,
            "ma20_slope": slope20,
            "ma50_slope": slope50
        }

    # --------------------------------------------------------
    # Downtrend
    # --------------------------------------------------------

    if (
        ma50_val is not None
        and
        price < ma50_val
        and
        adx_val is not None
        and
        adx_val >= 18
        and
        plus_di_val is not None
        and
        minus_di_val is not None
        and
        minus_di_val > plus_di_val
    ):

        return {
            "regime": "DOWNTREND",
            "trend": "BEARISH",
            "strength": "MODERATE",
            "adx": adx_val,
            "ma20_slope": slope20,
            "ma50_slope": slope50
        }

    # --------------------------------------------------------
    # Sideways
    # --------------------------------------------------------

    return {
        "regime": "SIDEWAYS",
        "trend": "NEUTRAL",
        "strength": "WEAK",
        "adx": adx_val,
        "ma20_slope": slope20,
        "ma50_slope": slope50
    }


# ============================================================
# WEIGHTED SCORE
# ============================================================

def calculate_weighted_score(
    regime,
    rsi,
    macd,
    macd_signal,
    histogram,
    stoch_k,
    stoch_d,
    price,
    ma20,
    ma50,
    ma200,
    adx,
    plus_di,
    minus_di,
    volume_ratio,
    obv,
    obv_ma,
    breakout,
    breakdown,
    volume_confirmed
):

    score = 0

    max_score = 0

    components = []

    def add_component(
        name,
        value,
        weight,
        reason
    ):

        nonlocal score
        nonlocal max_score

        contribution = (
            value *
            weight
        )

        score += contribution
        max_score += weight

        components.append({
            "indicator": name,
            "raw_score": value,
            "weight": weight,
            "contribution": round(
                contribution,
                2
            ),
            "reason": reason
        })

    # ========================================================
    # TREND
    # ========================================================

    trend_score = 0

    if regime in [
        "STRONG_UPTREND",
        "UPTREND"
    ]:

        trend_score = 1

    elif regime in [
        "STRONG_DOWNTREND",
        "DOWNTREND"
    ]:

        trend_score = -1

    add_component(
        "MARKET_REGIME",
        trend_score,
        3.0,
        regime
    )

    # ========================================================
    # MA ALIGNMENT
    # ========================================================

    ma_score = 0

    if (
        ma20 is not None
        and ma50 is not None
        and price is not None
    ):

        if price > ma20 > ma50:

            ma_score = 1

        elif price < ma20 < ma50:

            ma_score = -1

    add_component(
        "MA_ALIGNMENT",
        ma_score,
        2.0,
        "Trend alignment"
    )

    # ========================================================
    # RSI
    # ========================================================

    rsi_score = 0

    if rsi is not None:

        if 50 <= rsi < 70:

            rsi_score = 1

        elif rsi >= 70:

            rsi_score = -0.5

        elif 30 < rsi < 50:

            rsi_score = -1

        elif rsi <= 30:

            # Oversold alone is not strong BUY
            rsi_score = 0.5

    add_component(
        "RSI",
        rsi_score,
        1.5,
        f"RSI={safe_round(rsi, 2)}"
    )

    # ========================================================
    # MACD
    # ========================================================

    macd_score = 0

    if (
        macd is not None
        and macd_signal is not None
    ):

        if macd > macd_signal:

            macd_score = 1

            if histogram is not None and histogram > 0:
                macd_score = 1.25

        else:

            macd_score = -1

            if histogram is not None and histogram < 0:
                macd_score = -1.25

    add_component(
        "MACD",
        macd_score,
        2.0,
        "MACD momentum"
    )

    # ========================================================
    # STOCHASTIC
    # ========================================================

    stochastic_score = 0

    if (
        stoch_k is not None
        and stoch_d is not None
    ):

        if (
            stoch_k > stoch_d
            and stoch_k < 80
        ):

            stochastic_score = 1

        elif (
            stoch_k < stoch_d
            and stoch_k > 20
        ):

            stochastic_score = -1

        elif stoch_k <= 20:

            stochastic_score = 0.5

        elif stoch_k >= 80:

            stochastic_score = -0.5

    add_component(
        "STOCHASTIC",
        stochastic_score,
        1.0,
        "Momentum"
    )

    # ========================================================
    # ADX
    # ========================================================

    adx_score = 0

    if (
        adx is not None
        and plus_di is not None
        and minus_di is not None
    ):

        if adx >= 25:

            if plus_di > minus_di:

                adx_score = 1

            else:

                adx_score = -1

        elif adx >= 18:

            if plus_di > minus_di:

                adx_score = 0.5

            else:

                adx_score = -0.5

    add_component(
        "ADX",
        adx_score,
        1.5,
        f"ADX={safe_round(adx, 2)}"
    )

    # ========================================================
    # VOLUME
    # ========================================================

    volume_score = 0

    if volume_ratio is not None:

        if volume_ratio >= 1.5:

            if breakout:

                volume_score = 1

            elif breakdown:

                volume_score = -1

        elif volume_ratio >= 1.2:

            if price is not None and ma20 is not None:

                if price > ma20:

                    volume_score = 0.5

                elif price < ma20:

                    volume_score = -0.5

    add_component(
        "VOLUME",
        volume_score,
        1.5,
        f"Volume ratio={safe_round(volume_ratio, 2)}"
    )

    # ========================================================
    # OBV
    # ========================================================

    obv_score = 0

    if (
        obv is not None
        and obv_ma is not None
    ):

        if obv > obv_ma:

            obv_score = 1

        elif obv < obv_ma:

            obv_score = -1

    add_component(
        "OBV",
        obv_score,
        1.0,
        "Volume flow"
    )

    # ========================================================
    # BREAKOUT
    # ========================================================

    breakout_score = 0

    if breakout:

        if volume_confirmed:

            breakout_score = 1

        else:

            breakout_score = 0.5

    elif breakdown:

        if volume_confirmed:

            breakout_score = -1

        else:

            breakout_score = -0.5

    add_component(
        "BREAKOUT",
        breakout_score,
        2.5,
        "Price structure"
    )

    # ========================================================
    # NORMALIZE
    # ========================================================

    if max_score == 0:

        normalized_score = 0

    else:

        normalized_score = min(
            (score /
            max_score
        ) * 100, 100)

    return {
        "raw_score": round(score, 2),
        "max_score": round(max_score, 2),
        "normalized_score": round(
            normalized_score,
            2
        ),
        "components": components
    }


# ============================================================
# SIGNAL CLASSIFICATION
# ============================================================

def classify_signal(
    score,
    regime,
    breakout=False,
    breakdown=False
):

    # Strong breakout
    if (
        breakout
        and score >= 60
    ):

        return "STRONG BUY"

    if (
        breakdown
        and score <= -60
    ):

        return "STRONG SELL"

    # Regime confirmation: upgrade borderline signal if regime confirms
    is_uptrend = regime and "UPTREND" in regime
    is_downtrend = regime and "DOWNTREND" in regime

    if score >= 35 and is_uptrend:
        return "BUY"

    if score <= -35 and is_downtrend:
        return "SELL"

    # General signal without regime confirmation
    if score >= 45:

        return "BUY"

    if score <= -45:

        return "SELL"

    return "HOLD"


# ============================================================
# SETUP DETECTION
# ============================================================

def detect_setup(
    regime,
    rsi,
    macd,
    macd_signal,
    price,
    ma20,
    ma50,
    breakout,
    breakdown,
    volume_confirmed
):

    # --------------------------------------------------------
    # Breakout
    # --------------------------------------------------------

    if (
        breakout
        and volume_confirmed
    ):

        return "BULLISH_BREAKOUT"

    if (
        breakdown
        and volume_confirmed
    ):

        return "BEARISH_BREAKDOWN"

    # --------------------------------------------------------
    # Bullish pullback
    # --------------------------------------------------------

    if (
        regime in [
            "UPTREND",
            "STRONG_UPTREND"
        ]
        and rsi is not None
        and 40 <= rsi <= 55
        and macd is not None
        and macd_signal is not None
        and macd >= macd_signal
        and price is not None
        and ma20 is not None
        and price >= ma20
    ):

        return "BULLISH_PULLBACK"

    # --------------------------------------------------------
    # Bearish rally
    # --------------------------------------------------------

    if (
        regime in [
            "DOWNTREND",
            "STRONG_DOWNTREND"
        ]
        and rsi is not None
        and 45 <= rsi <= 60
        and macd is not None
        and macd_signal is not None
        and macd <= macd_signal
        and price is not None
        and ma20 is not None
        and price <= ma20
    ):

        return "BEARISH_RALLY"

    # --------------------------------------------------------
    # Trend
    # --------------------------------------------------------

    if regime == "STRONG_UPTREND":

        return "STRONG_UPTREND"

    if regime == "UPTREND":

        return "UPTREND"

    if regime == "STRONG_DOWNTREND":

        return "STRONG_DOWNTREND"

    if regime == "DOWNTREND":

        return "DOWNTREND"

    return "RANGE"


# ============================================================
# ATR BASED RISK MANAGEMENT
# ============================================================

def calculate_trade_levels(
    price,
    atr,
    support,
    resistance,
    signal,
    atr_stop_multiplier=1.5,
    reward_ratio=2.0
):

    if (
        price is None
        or atr is None
        or atr <= 0
    ):

        return {
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "risk": None,
            "reward": None,
            "risk_reward": None
        }

    # ========================================================
    # BUY
    # ========================================================

    if signal in [
        "BUY",
        "STRONG BUY"
    ]:

        entry = price

        atr_stop = (
            entry -
            (
                atr *
                atr_stop_multiplier
            )
        )

        # Use support only if it gives a meaningful stop
        if (
            support is not None
            and support < entry
        ):

            stop_loss = max(
                atr_stop,
                support - (
                    atr * 0.25
                )
            )

        else:

            stop_loss = atr_stop

        risk = (
            entry -
            stop_loss
        )

        if risk <= 0:

            return {
                "entry": entry,
                "stop_loss": None,
                "take_profit": None,
                "risk": None,
                "reward": None,
                "risk_reward": None
            }

        # Resistance can become target
        resistance_target = None

        if (
            resistance is not None
            and resistance > entry
        ):

            resistance_target = resistance

        atr_target = (
            entry +
            (
                risk *
                reward_ratio
            )
        )

        if resistance_target is not None:

            # Target cannot be below minimum R:R
            take_profit = max(
                resistance_target,
                atr_target
            )

        else:

            take_profit = atr_target

    # ========================================================
    # SELL
    # ========================================================

    elif signal in [
        "SELL",
        "STRONG SELL"
    ]:

        entry = price

        atr_stop = (
            entry +
            (
                atr *
                atr_stop_multiplier
            )
        )

        if (
            resistance is not None
            and resistance > entry
        ):

            stop_loss = min(
                atr_stop,
                resistance + (
                    atr * 0.25
                )
            )

        else:

            stop_loss = atr_stop

        risk = (
            stop_loss -
            entry
        )

        if risk <= 0:

            return {
                "entry": entry,
                "stop_loss": None,
                "take_profit": None,
                "risk": None,
                "reward": None,
                "risk_reward": None
            }

        support_target = None

        if (
            support is not None
            and support < entry
        ):

            support_target = support

        atr_target = (
            entry -
            (
                risk *
                reward_ratio
            )
        )

        if support_target is not None:

            take_profit = min(
                support_target,
                atr_target
            )

        else:

            take_profit = atr_target

    else:

        return {
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "risk": None,
            "reward": None,
            "risk_reward": None
        }

    reward = abs(
        take_profit -
        entry
    )

    risk_reward = (
        reward /
        risk
        if risk > 0
        else None
    )

    return {
        "entry": safe_round(
            entry,
            2
        ),
        "stop_loss": safe_round(
            stop_loss,
            2
        ),
        "take_profit": safe_round(
            take_profit,
            2
        ),
        "risk": safe_round(
            risk,
            2
        ),
        "reward": safe_round(
            reward,
            2
        ),
        "risk_reward": safe_round(
            risk_reward,
            2
        )
    }


# ============================================================
# CONFIDENCE SCORE
# ============================================================

def calculate_confidence(
    weighted_score,
    regime,
    breakout,
    volume_confirmed,
    adx,
    data_length
):

    # --------------------------------------------------------
    # Base confidence
    # --------------------------------------------------------

    confidence = abs(
        weighted_score
    )

    # Score already 0-100
    confidence = min(
        confidence,
        100
    )

    # --------------------------------------------------------
    # Regime confirmation (only if regime aligns with score direction)
    # --------------------------------------------------------

    is_bullish_regime = regime in ["STRONG_UPTREND", "UPTREND"]
    is_bearish_regime = regime in ["STRONG_DOWNTREND", "DOWNTREND"]

    if weighted_score > 0 and is_bullish_regime:
        confidence += 8 if regime == "STRONG_UPTREND" else 4
    elif weighted_score < 0 and is_bearish_regime:
        confidence += 8 if regime == "STRONG_DOWNTREND" else 4
    elif weighted_score > 0 and is_bearish_regime:
        confidence -= 5
    elif weighted_score < 0 and is_bullish_regime:
        confidence -= 5

    # --------------------------------------------------------
    # ADX confirmation (only if ADX confirms score direction)
    # --------------------------------------------------------

    if adx is not None:

        if adx >= 30 and (
            (weighted_score > 0 and is_bullish_regime) or
            (weighted_score < 0 and is_bearish_regime)
        ):
            confidence += 8

        elif adx >= 25 and (
            (weighted_score > 0 and is_bullish_regime) or
            (weighted_score < 0 and is_bearish_regime)
        ):
            confidence += 5

        elif adx < 15:
            confidence -= 5

    # --------------------------------------------------------
    # Breakout + volume confirmation
    # --------------------------------------------------------

    if breakout and volume_confirmed:

        confidence += 8

    # --------------------------------------------------------
    # Data quality
    # --------------------------------------------------------

    if data_length >= 200:

        confidence += 3

    elif data_length < 100:

        confidence -= 5

    return int(
        max(
            0,
            min(
                confidence,
                100
            )
        )
    )


# ============================================================
# MAIN ENGINE
# ============================================================

def analyze_stock_v2(
    prices_data,
    support_resistance_period=20,
    atr_stop_multiplier=1.5,
    reward_ratio=2.0
):

    # ========================================================
    # VALIDATION
    # ========================================================

    if not prices_data:

        return {
            "error": "No price data"
        }

    df = pd.DataFrame(
        prices_data
    )

    # Normalize columns
    df.columns = [
        str(c).capitalize()
        for c in df.columns
    ]

    required = [
        "Close",
        "High",
        "Low"
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:

        return {
            "error": (
                "Missing columns: "
                + ", ".join(missing)
            )
        }

    # ========================================================
    # NUMERIC CONVERSION
    # ========================================================

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
        subset=[
            "High",
            "Low",
            "Close"
        ]
    ).reset_index(
        drop=True
    )

    # ========================================================
    # VOLUME
    # ========================================================

    has_volume = (
        "Volume" in df.columns
    )

    if not has_volume:

        df["Volume"] = np.nan

    # ========================================================
    # MINIMUM DATA
    # ========================================================

    if len(df) < 50:

        return {
            "error": (
                "Insufficient data. "
                "Minimum 50 candles."
            )
        }

    # 200 candles recommended for MA200
    data_quality = (
        "GOOD"
        if len(df) >= 200
        else "LIMITED"
    )

    # ========================================================
    # SERIES
    # ========================================================

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    current_price = safe_float(
        close.iloc[-1]
    )

    # ========================================================
    # INDICATORS
    # ========================================================

    rsi = calculate_rsi(
        close
    )

    macd, macd_signal, macd_hist = calculate_macd(
        close
    )

    upper_bb, middle_bb, lower_bb = calculate_bollinger(
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

    # ========================================================
    # VOLUME INDICATORS
    # ========================================================

    if has_volume:

        volume_ratio = calculate_volume_ratio(
            volume
        )

        obv = calculate_obv(
            close,
            volume
        )

        obv_ma = calculate_obv_trend(
            obv
        )

    else:

        volume_ratio = pd.Series(
            np.nan,
            index=df.index
        )

        obv = pd.Series(
            np.nan,
            index=df.index
        )

        obv_ma = pd.Series(
            np.nan,
            index=df.index
        )

    # ========================================================
    # ADX
    # ========================================================

    adx, plus_di, minus_di = calculate_adx(
        high,
        low,
        close
    )

    # ========================================================
    # SUPPORT / RESISTANCE
    # ========================================================

    support, resistance = calculate_support_resistance(
        high,
        low,
        close,
        support_resistance_period
    )

    # ========================================================
    # CURRENT VALUES
    # ========================================================

    rsi_val = safe_float(
        rsi.iloc[-1]
    )

    macd_val = safe_float(
        macd.iloc[-1]
    )

    macd_signal_val = safe_float(
        macd_signal.iloc[-1]
    )

    macd_hist_val = safe_float(
        macd_hist.iloc[-1]
    )

    stoch_k_val = safe_float(
        stoch_k.iloc[-1]
    )

    stoch_d_val = safe_float(
        stoch_d.iloc[-1]
    )

    atr_val = safe_float(
        atr.iloc[-1]
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

    adx_val = safe_float(
        adx.iloc[-1]
    )

    plus_di_val = safe_float(
        plus_di.iloc[-1]
    )

    minus_di_val = safe_float(
        minus_di.iloc[-1]
    )

    volume_ratio_val = safe_float(
        volume_ratio.iloc[-1]
    )

    obv_val = safe_float(
        obv.iloc[-1]
    )

    obv_ma_val = safe_float(
        obv_ma.iloc[-1]
    )

    support_val = safe_float(
        support.iloc[-1]
    )

    resistance_val = safe_float(
        resistance.iloc[-1]
    )

    # ========================================================
    # MARKET REGIME
    # ========================================================

    regime = determine_market_regime(
        close,
        ma20,
        ma50,
        ma200,
        adx,
        plus_di,
        minus_di
    )

    regime_name = regime[
        "regime"
    ]

    # ========================================================
    # BREAKOUT
    # ========================================================

    breakout_info = detect_breakout(
        close,
        high,
        low,
        volume,
        support,
        resistance,
        volume_ratio
    )

    breakout = breakout_info[
        "breakout"
    ]

    breakdown = breakout_info[
        "breakdown"
    ]

    volume_confirmed = breakout_info[
        "volume_confirmed"
    ]

    # ========================================================
    # WEIGHTED SCORE
    # ========================================================

    scoring = calculate_weighted_score(

        regime_name,

        rsi_val,

        macd_val,

        macd_signal_val,

        macd_hist_val,

        stoch_k_val,

        stoch_d_val,

        current_price,

        ma20_val,

        ma50_val,

        ma200_val,

        adx_val,

        plus_di_val,

        minus_di_val,

        volume_ratio_val,

        obv_val,

        obv_ma_val,

        breakout,

        breakdown,

        volume_confirmed
    )

    normalized_score = scoring[
        "normalized_score"
    ]

    # ========================================================
    # SETUP
    # ========================================================

    setup = detect_setup(

        regime_name,

        rsi_val,

        macd_val,

        macd_signal_val,

        current_price,

        ma20_val,

        ma50_val,

        breakout,

        breakdown,

        volume_confirmed
    )

    # ========================================================
    # SIGNAL
    # ========================================================

    overall_signal = classify_signal(

        normalized_score,

        regime_name,

        breakout,

        breakdown
    )

    # ========================================================
    # TRADE LEVELS
    # ========================================================

    trade_levels = calculate_trade_levels(

        current_price,

        atr_val,

        support_val,

        resistance_val,

        overall_signal,

        atr_stop_multiplier,

        reward_ratio
    )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    confidence = calculate_confidence(

        normalized_score,

        regime_name,

        breakout or breakdown,

        volume_confirmed,

        adx_val,

        len(df)
    )

    # ========================================================
    # ATR %
    # ========================================================

    atr_percent = None

    if (
        atr_val is not None
        and current_price
        and current_price != 0
    ):

        atr_percent = (
            atr_val /
            current_price
        ) * 100

    # ========================================================
    # CHART DATA
    # ========================================================

    chart_data = []

    start_index = max(
        0,
        len(df) - 120
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
                2
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

            "macd": safe_round(
                macd.iloc[i],
                4
            ),

            "macd_signal": safe_round(
                macd_signal.iloc[i],
                4
            ),

            "macd_histogram": safe_round(
                macd_hist.iloc[i],
                4
            ),

            "stoch_k": safe_round(
                stoch_k.iloc[i],
                2
            ),

            "stoch_d": safe_round(
                stoch_d.iloc[i],
                2
            ),

            "atr": safe_round(
                atr.iloc[i],
                2
            ),

            "adx": safe_round(
                adx.iloc[i],
                2
            ),

            "plus_di": safe_round(
                plus_di.iloc[i],
                2
            ),

            "minus_di": safe_round(
                minus_di.iloc[i],
                2
            ),

            "volume_ratio": safe_round(
                volume_ratio.iloc[i],
                2
            ),

            "obv": safe_round(
                obv.iloc[i],
                0
            ),

            "support": safe_round(
                support.iloc[i],
                2
            ),

            "resistance": safe_round(
                resistance.iloc[i],
                2
            )
        })

    # ========================================================
    # SIGNALS (compatibility)
    # ========================================================

    signals = []

    if rsi_val is not None:
        if rsi_val < 30:
            signals.append({"indicator": "RSI", "signal": "OVERSOLD", "value": rsi_val, "recommendation": "BUY"})
        elif rsi_val > 70:
            signals.append({"indicator": "RSI", "signal": "OVERBOUGHT", "value": rsi_val, "recommendation": "SELL"})
        else:
            signals.append({"indicator": "RSI", "signal": "NEUTRAL", "value": rsi_val, "recommendation": "HOLD"})

    if macd_val is not None and macd_signal_val is not None:
        macd_prev = safe_float(macd.iloc[-2]) if len(macd) > 1 else None
        macd_signal_prev = safe_float(macd_signal.iloc[-2]) if len(macd_signal) > 1 else None
        is_cross_up = (macd_prev is not None and macd_signal_prev is not None
                       and macd_val > macd_signal_val and macd_prev <= macd_signal_prev)
        is_cross_down = (macd_prev is not None and macd_signal_prev is not None
                         and macd_val < macd_signal_val and macd_prev >= macd_signal_prev)
        if is_cross_up:
            signals.append({"indicator": "MACD", "signal": "BULLISH CROSS", "value": macd_val, "recommendation": "BUY"})
        elif is_cross_down:
            signals.append({"indicator": "MACD", "signal": "BEARISH CROSS", "value": macd_val, "recommendation": "SELL"})
        elif macd_val > macd_signal_val:
            signals.append({"indicator": "MACD", "signal": "BULLISH", "value": macd_val, "recommendation": "HOLD"})
        else:
            signals.append({"indicator": "MACD", "signal": "BEARISH", "value": macd_val, "recommendation": "HOLD"})

    lower_bb_val = safe_float(lower_bb.iloc[-1])
    upper_bb_val = safe_float(upper_bb.iloc[-1])
    middle_bb_val = safe_float(middle_bb.iloc[-1])

    if lower_bb_val is not None and current_price is not None:
        if current_price <= lower_bb_val:
            signals.append({"indicator": "BOLLINGER", "signal": "AT LOWER BAND", "value": lower_bb_val, "recommendation": "BUY"})
        elif current_price >= upper_bb_val:
            signals.append({"indicator": "BOLLINGER", "signal": "AT UPPER BAND", "value": upper_bb_val, "recommendation": "SELL"})
        else:
            signals.append({"indicator": "BOLLINGER", "signal": "IN RANGE", "value": middle_bb_val, "recommendation": "HOLD"})

    if ma50_val is not None and ma200_val is not None:
        ma50_prev = safe_float(ma50.iloc[-2]) if len(ma50) > 1 else None
        ma200_prev = safe_float(ma200.iloc[-2]) if len(ma200) > 1 else None
        is_golden = (ma50_prev is not None and ma200_prev is not None
                     and ma50_val > ma200_val and ma50_prev <= ma200_prev)
        is_death = (ma50_prev is not None and ma200_prev is not None
                    and ma50_val < ma200_val and ma50_prev >= ma200_prev)
        if is_golden:
            signals.append({"indicator": "GOLDEN CROSS", "signal": "MA50 crossed above MA200", "recommendation": "STRONG BUY"})
        elif is_death:
            signals.append({"indicator": "DEATH CROSS", "signal": "MA50 crossed below MA200", "recommendation": "STRONG SELL"})
        elif ma50_val > ma200_val:
            signals.append({"indicator": "MA TREND", "signal": "MA50 above MA200 (UPTREND)", "recommendation": "BUY"})
        else:
            signals.append({"indicator": "MA TREND", "signal": "MA50 below MA200 (DOWNTREND)", "recommendation": "SELL"})

    if regime_name and "UPTREND" in regime_name:
        signals.append({"indicator": "TREND", "signal": regime_name, "recommendation": "BUY"})
    elif regime_name and "DOWNTREND" in regime_name:
        signals.append({"indicator": "TREND", "signal": regime_name, "recommendation": "SELL"})
    else:
        signals.append({"indicator": "TREND", "signal": regime_name or "SIDEWAYS", "recommendation": "HOLD"})

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        "current_price": safe_round(
            current_price,
            2
        ),

        # ----------------------------------------------------
        # SIGNAL
        # ----------------------------------------------------

        "overall_signal": overall_signal,

        "setup": setup,

        "confidence": confidence,

        "signals": signals,

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        "score": {

            "raw": scoring[
                "raw_score"
            ],

            "max": scoring[
                "max_score"
            ],

            "normalized": normalized_score
        },

        "score_components": scoring[
            "components"
        ],

        # ----------------------------------------------------
        # MARKET REGIME
        # ----------------------------------------------------

        "market_regime": regime_name,

        "trend": regime.get(
            "trend"
        ),

        "trend_strength": regime.get(
            "strength"
        ),

        # ----------------------------------------------------
        # RSI
        # ----------------------------------------------------

        "rsi": safe_round(
            rsi_val,
            2
        ),

        # ----------------------------------------------------
        # MACD
        # ----------------------------------------------------

        "macd": {

            "macd": safe_round(
                macd_val,
                4
            ),

            "signal": safe_round(
                macd_signal_val,
                4
            ),

            "histogram": safe_round(
                macd_hist_val,
                4
            )
        },

        # ----------------------------------------------------
        # MOVING AVERAGE
        # ----------------------------------------------------

        "moving_averages": {

            "ma7": safe_round(
                ma7.iloc[-1],
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

        # ----------------------------------------------------
        # BOLLINGER
        # ----------------------------------------------------

        "bollinger": {

            "upper": safe_round(
                upper_bb.iloc[-1],
                2
            ),

            "middle": safe_round(
                middle_bb.iloc[-1],
                2
            ),

            "lower": safe_round(
                lower_bb.iloc[-1],
                2
            )
        },

        # ----------------------------------------------------
        # STOCHASTIC
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ATR
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # ADX
        # ----------------------------------------------------

        "adx": {

            "adx": safe_round(
                adx_val,
                2
            ),

            "plus_di": safe_round(
                plus_di_val,
                2
            ),

            "minus_di": safe_round(
                minus_di_val,
                2
            )
        },

        # ----------------------------------------------------
        # VOLUME
        # ----------------------------------------------------

        "volume": {

            "available": has_volume,

            "ratio": safe_round(
                volume_ratio_val,
                2
            ),

            "obv": safe_round(
                obv_val,
                0
            ),

            "obv_ma": safe_round(
                obv_ma_val,
                0
            )
        },

        # ----------------------------------------------------
        # SUPPORT / RESISTANCE
        # ----------------------------------------------------

        "support_resistance": {

            "support": safe_round(
                support_val,
                2
            ),

            "resistance": safe_round(
                resistance_val,
                2
            )
        },

        # ----------------------------------------------------
        # BREAKOUT
        # ----------------------------------------------------

        "breakout": {

            "breakout": breakout,

            "breakdown": breakdown,

            "volume_confirmed": volume_confirmed
        },

        # ----------------------------------------------------
        # TRADE PLAN
        # ----------------------------------------------------

        "trade_plan": trade_levels,

        # ----------------------------------------------------
        # DATA QUALITY
        # ----------------------------------------------------

        "data_quality": {

            "candles": len(df),

            "status": data_quality,

            "ma200_available": (
                ma200_val is not None
            ),

            "volume_available": has_volume
        },

        # ----------------------------------------------------
        # CHART
        # ----------------------------------------------------

        "chart_data": chart_data
    }


analyze_stock = analyze_stock_v2

