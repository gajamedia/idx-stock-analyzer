import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta


def safe_float(val, default=None):
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
    f = safe_float(val)
    if f is None:
        return default
    return round(f, decimals)


def aggregate_to_weekly(daily_data):
    if not daily_data or len(daily_data) < 10:
        return None

    df = pd.DataFrame(daily_data)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=False)
        df.set_index("Date", inplace=True)

    weekly = df.resample("W").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()

    weekly = weekly.reset_index()
    return weekly.to_dict("records")


def calculate_support_resistance(prices_data, lookback=60):
    if not prices_data or len(prices_data) < 10:
        return {"support": [], "resistance": [], "volume_levels": []}

    df = pd.DataFrame(prices_data)
    close = df["Close"].values
    high = df["High"].values if "High" in df.columns else close
    low = df["Low"].values if "Low" in df.columns else close
    volume = df["Volume"].values if "Volume" in df.columns else np.ones(len(close))

    n = min(lookback, len(close))
    recent_close = close[-n:]
    recent_high = high[-n:]
    recent_low = low[-n:]
    recent_vol = volume[-n:]

    supports = []
    resistances = []

    for i in range(2, n - 2):
        if recent_low[i] <= recent_low[i - 1] and recent_low[i] <= recent_low[i - 2] and \
           recent_low[i] <= recent_low[i + 1] and recent_low[i] <= recent_low[i + 2]:
            supports.append(round(float(recent_low[i]), 2))
        if recent_high[i] >= recent_high[i - 1] and recent_high[i] >= recent_high[i - 2] and \
           recent_high[i] >= recent_high[i + 1] and recent_high[i] >= recent_high[i + 2]:
            resistances.append(round(float(recent_high[i]), 2))

    supports = sorted(list(set(supports)), reverse=True)[:3]
    resistances = sorted(list(set(resistances)))[:3]

    if not supports:
        recent_low_sorted = sorted(recent_low)
        supports = [round(float(recent_low_sorted[0]), 2), round(float(recent_low_sorted[1]), 2)]

    if not resistances:
        recent_high_sorted = sorted(recent_high, reverse=True)
        resistances = [round(float(recent_high_sorted[0]), 2), round(float(recent_high_sorted[1]), 2)]

    price_range = float(np.max(recent_high) - np.min(recent_low))
    if price_range <= 0:
        price_range = 1.0
    num_bins = min(20, n // 3)
    bin_size = price_range / num_bins

    volume_profile = {}
    for i in range(n):
        bin_center = round(float(recent_low[i]) + bin_size * (int((recent_high[i] - recent_low[i]) / bin_size / 2) + 0.5) * bin_size, 2)
        bin_center = round(float(recent_close[i]) / bin_size) * bin_size
        bin_key = round(bin_center, 2)
        if bin_key not in volume_profile:
            volume_profile[bin_key] = 0
        volume_profile[bin_key] += float(recent_vol[i])

    if volume_profile:
        max_volume = max(volume_profile.values())
        if max_volume > 0:
            high_vol_levels = sorted(
                [price for price, vol in volume_profile.items() if vol > max_volume * 0.6],
                key=lambda x: abs(x - float(recent_close[-1]))
            )[:3]
        else:
            high_vol_levels = []
    else:
        high_vol_levels = []

    all_supports = sorted(set(supports + [l for l in high_vol_levels if l < float(recent_close[-1])]), reverse=True)[:3]
    all_resistances = sorted(set(resistances + [l for l in high_vol_levels if l > float(recent_close[-1])]))[:3]

    return {
        "support": all_supports,
        "resistance": all_resistances,
        "volume_levels": sorted(high_vol_levels)[:5],
    }


def calculate_volatility(prices_data, period=20):
    if not prices_data or len(prices_data) < period + 1:
        return None

    df = pd.DataFrame(prices_data)
    close = df["Close"]
    returns = close.pct_change().dropna()
    vol_series = returns.rolling(window=period).std()
    volatility = vol_series.iloc[-1]
    if pd.isna(volatility):
        return None
    annualized_vol = volatility * np.sqrt(252)
    return safe_round(annualized_vol, 4)


def calculate_atr_value(prices_data, period=14):
    if not prices_data or len(prices_data) < period + 1:
        return None

    df = pd.DataFrame(prices_data)
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = tr.rolling(window=period).mean()
    atr = atr_series.iloc[-1]
    if pd.isna(atr):
        return None
    return safe_round(atr, 2)


def calculate_trend_strength(prices_data):
    if not prices_data or len(prices_data) < 50:
        return {"trend": "NEUTRAL", "strength": 0, "slope": 0, "ma20": 0, "ma50": 0, "ma200": 0}

    df = pd.DataFrame(prices_data)
    close = df["Close"].values
    n = len(close)

    valid_close = close[~np.isnan(close)]
    if len(valid_close) < 20:
        return {"trend": "NEUTRAL", "strength": 0, "slope": 0, "ma20": 0, "ma50": 0, "ma200": 0}

    ma20 = np.nanmean(close[-20:])
    ma50 = np.nanmean(close[-50:]) if n >= 50 else np.nanmean(close)
    ma200 = np.nanmean(close[-200:]) if n >= 200 else None

    x = np.arange(20)
    recent_close = close[-20:]
    valid_recent = recent_close[~np.isnan(recent_close)]
    if len(valid_recent) < 5:
        return {"trend": "NEUTRAL", "strength": 0, "slope": 0, "ma20": safe_round(ma20, 2, 0), "ma50": safe_round(ma50, 2, 0), "ma200": safe_round(ma200, 2, 0) if ma200 else None}

    slope = np.polyfit(x[-len(valid_recent):], valid_recent, 1)[0]
    last_valid_price = valid_recent[-1]
    normalized_slope = slope / last_valid_price * 100 if last_valid_price != 0 else 0

    if ma200 is not None and last_valid_price > ma20 > ma50 > ma200:
        trend = "STRONG UPTREND"
        strength = min(100, int(abs(normalized_slope) * 10 + 60))
    elif last_valid_price > ma20 > ma50:
        trend = "UPTREND"
        strength = min(85, int(abs(normalized_slope) * 10 + 40))
    elif last_valid_price > ma20:
        trend = "WEAK UPTREND"
        strength = min(60, int(abs(normalized_slope) * 10 + 20))
    elif ma200 is not None and last_valid_price < ma20 < ma50 < ma200:
        trend = "STRONG DOWNTREND"
        strength = max(-100, int(-abs(normalized_slope) * 10 - 60))
    elif last_valid_price < ma20 < ma50:
        trend = "DOWNTREND"
        strength = max(-85, int(-abs(normalized_slope) * 10 - 40))
    elif last_valid_price < ma20:
        trend = "WEAK DOWNTREND"
        strength = max(-60, int(-abs(normalized_slope) * 10 - 20))
    else:
        trend = "NEUTRAL"
        strength = 0

    return {
        "trend": trend,
        "strength": strength,
        "slope": safe_round(normalized_slope, 4, 0),
        "ma20": safe_round(ma20, 2, 0),
        "ma50": safe_round(ma50, 2, 0),
        "ma200": safe_round(ma200, 2, 0) if ma200 else None,
    }


def calculate_price_targets(current_price, atr, support_resistance, trend_info, horizon_months):
    volatility_factor = {
        1: 1.0,
        3: 1.7,
        6: 2.4,
        12: 3.5,
    }
    factor = volatility_factor.get(horizon_months, 1.0)

    atr_val = safe_float(atr)
    if atr_val is not None and atr_val > 0:
        atr_targets = atr_val * factor
    else:
        atr_targets = current_price * 0.02 * factor

    if trend_info["trend"] in ["STRONG UPTREND", "UPTREND"]:
        take_profit = current_price + (atr_targets * 2.0)
        stop_loss = current_price - (atr_targets * 1.5)
        entry_zone_low = current_price - (atr_targets * 0.3)
        entry_zone_high = current_price + (atr_targets * 0.3)
    elif trend_info["trend"] in ["WEAK UPTREND"]:
        take_profit = current_price + (atr_targets * 1.5)
        stop_loss = current_price - (atr_targets * 1.3)
        entry_zone_low = current_price - (atr_targets * 0.2)
        entry_zone_high = current_price + (atr_targets * 0.2)
    elif trend_info["trend"] in ["STRONG DOWNTREND", "DOWNTREND"]:
        take_profit = current_price + (atr_targets * 1.0)
        stop_loss = current_price - (atr_targets * 2.0)
        entry_zone_low = current_price - (atr_targets * 0.5)
        entry_zone_high = current_price + (atr_targets * 0.2)
    elif trend_info["trend"] in ["WEAK DOWNTREND"]:
        take_profit = current_price + (atr_targets * 1.2)
        stop_loss = current_price - (atr_targets * 1.5)
        entry_zone_low = current_price - (atr_targets * 0.3)
        entry_zone_high = current_price + (atr_targets * 0.2)
    else:
        take_profit = current_price + (atr_targets * 1.5)
        stop_loss = current_price - (atr_targets * 1.5)
        entry_zone_low = current_price - (atr_targets * 0.3)
        entry_zone_high = current_price + (atr_targets * 0.3)

    supports = support_resistance.get("support", [])
    resistances = support_resistance.get("resistance", [])

    if supports:
        valid_supports = [s for s in supports if s < current_price]
        if valid_supports:
            nearest_support = max(valid_supports)
            stop_loss = max(stop_loss, nearest_support * 0.98)

    if resistances:
        valid_resistances = [r for r in resistances if r > current_price]
        if valid_resistances:
            nearest_resistance = min(valid_resistances)
            take_profit = min(take_profit, nearest_resistance * 1.02)

    risk = current_price - stop_loss
    reward = take_profit - current_price
    risk_reward = round(reward / risk, 2) if risk > 0 else 0

    return {
        "entry_zone": {
            "low": round(entry_zone_low, 2),
            "high": round(entry_zone_high, 2),
        },
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "risk_reward_ratio": risk_reward,
        "risk_per_share": round(risk, 2),
        "reward_per_share": round(reward, 2),
    }


def estimate_holding_period_return(current_price, trend_info, volatility, horizon_months, fundamental_score):
    """
    Professional return estimation using log-normal distribution.
    Provides confidence intervals and scenario analysis.
    """
    vol_val = safe_float(volatility, 0.3)
    if vol_val is None or vol_val <= 0:
        vol_val = 0.3

    slope_val = safe_float(trend_info.get("slope"), 0)
    trend_strength = abs(safe_float(trend_info.get("strength"), 0))

    base_monthly_drift = slope_val / 100.0

    trend_boost = 0
    if trend_strength > 50:
        trend_boost = 0.002
    elif trend_strength > 30:
        trend_boost = 0.001

    fund_val = safe_float(fundamental_score, 0)
    fundamental_boost = fund_val / 500.0

    annual_drift = base_monthly_drift * 12 + trend_boost + fundamental_boost
    monthly_drift = annual_drift / 12

    T = horizon_months / 12.0
    mu = monthly_drift
    sigma = vol_val / np.sqrt(12)

    z_scores = {
        "p10": -1.28,
        "p25": -0.67,
        "p50": 0.0,
        "p75": 0.67,
        "p90": 1.28,
    }

    percentiles = {}
    for label, z in z_scores.items():
        exponent = (mu - 0.5 * sigma**2) * horizon_months + sigma * np.sqrt(horizon_months) * z
        price = current_price * np.exp(exponent)
        ret = ((price / current_price) - 1) * 100
        percentiles[label] = {
            "price": safe_round(price, 2),
            "return_pct": safe_round(ret, 2),
        }

    scenarios = {
        "bull": {
            "probability": 25,
            "label": "Bull Case",
            "description": "Optimistic scenario — trend continues, momentum strengthens",
            "z_score": 0.67,
        },
        "base": {
            "probability": 50,
            "label": "Base Case",
            "description": "Most likely scenario — current trend persists",
            "z_score": 0.0,
        },
        "bear": {
            "probability": 25,
            "label": "Bear Case",
            "description": "Pessimistic scenario — trend weakens or reverses",
            "z_score": -0.67,
        },
    }

    scenario_results = {}
    for key, scenario in scenarios.items():
        z = scenario["z_score"]
        exponent = (mu - 0.5 * sigma**2) * horizon_months + sigma * np.sqrt(horizon_months) * z
        price = current_price * np.exp(exponent)
        ret = ((price / current_price) - 1) * 100
        scenario_results[key] = {
            **scenario,
            "price": safe_round(price, 2),
            "return_pct": safe_round(ret, 2),
        }

    monthly_estimates = []
    cumulative_base = 1.0
    cumulative_bull = 1.0
    cumulative_bear = 1.0

    for m in range(1, horizon_months + 1):
        exp_base = (mu - 0.5 * sigma**2) * m + sigma * np.sqrt(m) * 0.0
        exp_bull = (mu - 0.5 * sigma**2) * m + sigma * np.sqrt(m) * 0.67
        exp_bear = (mu - 0.5 * sigma**2) * m + sigma * np.sqrt(m) * -0.67

        price_base = current_price * np.exp(exp_base)
        price_bull = current_price * np.exp(exp_bull)
        price_bear = current_price * np.exp(exp_bear)

        monthly_estimates.append({
            "month": m,
            "base": safe_round(price_base, 2),
            "bull": safe_round(price_bull, 2),
            "bear": safe_round(price_bear, 2),
            "base_return": safe_round(((price_base / current_price) - 1) * 100, 2),
            "bull_return": safe_round(((price_bull / current_price) - 1) * 100, 2),
            "bear_return": safe_round(((price_bear / current_price) - 1) * 100, 2),
        })

    expected_return = percentiles["p50"]["return_pct"]
    expected_price = percentiles["p50"]["price"]

    return {
        "horizon_months": horizon_months,
        "expected_return_pct": expected_return,
        "expected_price": expected_price,
        "confidence_intervals": {
            "p10": percentiles["p10"],
            "p25": percentiles["p25"],
            "p50": percentiles["p50"],
            "p75": percentiles["p75"],
            "p90": percentiles["p90"],
        },
        "scenarios": scenario_results,
        "monthly_estimate": monthly_estimates,
        "volatility_monthly": safe_round(sigma * 100, 2),
        "drift_monthly": safe_round(mu * 100, 4),
    }


def calculate_timeframe_score(daily_signals, weekly_signals, trend_info, support_resistance, price_targets, holding_return):
    score = 0
    details = []

    signal_values = {}
    for s in daily_signals:
        ind = s.get("indicator", "")
        val = s.get("value")
        rec = s.get("recommendation", "HOLD")
        signal_values[ind] = {"value": val, "recommendation": rec, "signal": s.get("signal", "")}

    rsi_info = signal_values.get("RSI", {})
    rsi_val = safe_float(rsi_info.get("value"))
    if rsi_val is not None:
        if rsi_val <= 20:
            rsi_score = 3
        elif rsi_val <= 30:
            rsi_score = 2
        elif rsi_val <= 45:
            rsi_score = 0.5
        elif rsi_val <= 55:
            rsi_score = 0
        elif rsi_val <= 65:
            rsi_score = 0.5
        elif rsi_val <= 75:
            rsi_score = 1.5
        else:
            rsi_score = 1
        score += rsi_score
        details.append({
            "factor": "RSI",
            "value": "{:.1f}".format(rsi_val),
            "impact": rsi_score,
        })

    macd_info = signal_values.get("MACD", {})
    macd_rec = macd_info.get("recommendation", "HOLD")
    if macd_rec == "BUY":
        macd_score = 2
    elif macd_rec == "SELL":
        macd_score = -2
    else:
        macd_rec_type = macd_info.get("signal", "")
        if "BULLISH" in macd_rec_type:
            macd_score = 1
        elif "BEARISH" in macd_rec_type:
            macd_score = -1
        else:
            macd_score = 0
    score += macd_score
    details.append({
        "factor": "MACD",
        "value": macd_info.get("signal", "N/A"),
        "impact": macd_score,
    })

    bb_info = signal_values.get("BOLLINGER", {})
    bb_rec = bb_info.get("recommendation", "HOLD")
    if bb_rec == "BUY":
        bb_score = 1.5
    elif bb_rec == "SELL":
        bb_score = -1.5
    else:
        bb_score = 0
    score += bb_score
    details.append({
        "factor": "Bollinger Band",
        "value": bb_info.get("signal", "N/A"),
        "impact": bb_score,
    })

    ma_info = signal_values.get("MA TREND", {})
    ma_rec = ma_info.get("recommendation", "HOLD")
    if ma_rec == "STRONG BUY":
        ma_score = 3
    elif ma_rec == "BUY":
        ma_score = 2
    elif ma_rec == "STRONG SELL":
        ma_score = -3
    elif ma_rec == "SELL":
        ma_score = -2
    else:
        ma_score = 0
    score += ma_score
    details.append({
        "factor": "MA Trend",
        "value": ma_info.get("signal", "N/A"),
        "impact": ma_score,
    })

    cross_info = signal_values.get("GOLDEN CROSS", signal_values.get("DEATH CROSS", {}))
    if cross_info:
        cross_rec = cross_info.get("recommendation", "HOLD")
        if cross_rec == "STRONG BUY":
            cross_score = 3
        elif cross_rec == "STRONG SELL":
            cross_score = -3
        else:
            cross_score = 0
        score += cross_score
        details.append({
            "factor": "Crossover",
            "value": cross_info.get("signal", "N/A"),
            "impact": cross_score,
        })

    trend_regime = signal_values.get("TREND", {})
    trend_regime_signal = trend_regime.get("signal", "")
    if "STRONG" in trend_regime_signal and "UPTREND" in trend_regime_signal:
        regime_score = 2
    elif "UPTREND" in trend_regime_signal:
        regime_score = 1.5
    elif "STRONG" in trend_regime_signal and "DOWNTREND" in trend_regime_signal:
        regime_score = -2
    elif "DOWNTREND" in trend_regime_signal:
        regime_score = -1.5
    else:
        regime_score = 0
    score += regime_score
    details.append({
        "factor": "Trend Regime",
        "value": trend_regime_signal,
        "impact": regime_score,
    })

    if weekly_signals:
        weekly_buy = sum(1 for s in weekly_signals if "BUY" in s.get("recommendation", ""))
        weekly_sell = sum(1 for s in weekly_signals if "SELL" in s.get("recommendation", ""))
        weekly_net = weekly_buy - weekly_sell
        weekly_score = weekly_net * 0.5
        score += weekly_score
        details.append({
            "factor": "Weekly Confirmation",
            "value": "Buy: {}, Sell: {}".format(weekly_buy, weekly_sell),
            "impact": weekly_score,
        })

    trend = trend_info.get("trend", "NEUTRAL")
    trend_strength = abs(trend_info.get("strength", 0))
    if "STRONG UPTREND" in trend:
        trend_score = 2 + min(trend_strength / 50, 1)
    elif "UPTREND" in trend:
        trend_score = 1.5 + min(trend_strength / 60, 0.5)
    elif "WEAK UPTREND" in trend:
        trend_score = 0.5
    elif "STRONG DOWNTREND" in trend:
        trend_score = -(2 + min(trend_strength / 50, 1))
    elif "DOWNTREND" in trend:
        trend_score = -(1.5 + min(trend_strength / 60, 0.5))
    elif "WEAK DOWNTREND" in trend:
        trend_score = -0.5
    else:
        trend_score = 0
    score += trend_score
    details.append({
        "factor": "Trend Quality",
        "value": "{} (strength: {})".format(trend, trend_strength),
        "impact": safe_round(trend_score, 2),
    })

    rr = price_targets.get("risk_reward_ratio", 0)
    if rr >= 3.0:
        rr_score = 3
    elif rr >= 2.0:
        rr_score = 2
    elif rr >= 1.5:
        rr_score = 1
    elif rr >= 1.0:
        rr_score = 0
    else:
        rr_score = -1
    score += rr_score
    details.append({
        "factor": "Risk/Reward",
        "value": "{}x".format(rr),
        "impact": rr_score,
    })

    ci = holding_return.get("confidence_intervals", {})
    p10_return = ci.get("p10", {}).get("return_pct", 0)
    p90_return = ci.get("p90", {}).get("return_pct", 0)
    upside = p90_return
    downside = abs(p10_return)
    if downside > 0:
        risk_reward_ci = upside / downside
    else:
        risk_reward_ci = 999
    if risk_reward_ci >= 2.0:
        ci_score = 2
    elif risk_reward_ci >= 1.5:
        ci_score = 1
    elif risk_reward_ci >= 1.0:
        ci_score = 0
    else:
        ci_score = -1
    score += ci_score
    details.append({
        "factor": "Risk Profile (CI)",
        "value": "Upside: +{:.1f}%, Downside: {:.1f}%, Ratio: {:.2f}".format(upside, downside, risk_reward_ci),
        "impact": ci_score,
    })

    scenarios = holding_return.get("scenarios", {})
    bull_return = scenarios.get("bull", {}).get("return_pct", 0)
    bear_return = scenarios.get("bear", {}).get("return_pct", 0)
    if bull_return > 0 and bear_return > -5:
        scenario_score = 2
    elif bull_return > 0 and bear_return > -10:
        scenario_score = 1
    elif bull_return < 0:
        scenario_score = -1
    else:
        scenario_score = 0
    score += scenario_score
    details.append({
        "factor": "Scenario Analysis",
        "value": "Bull: +{:.1f}%, Bear: {:.1f}%".format(bull_return, bear_return),
        "impact": scenario_score,
    })

    return safe_round(score, 2), details


def format_rp(value):
    if value is None:
        return "N/A"
    f = safe_float(value)
    if f is None:
        return "N/A"
    return "Rp {:,.0f}".format(f).replace(",", ".")


def generate_horizon_recommendation(score):
    if score >= 15:
        return "STRONG BUY", "Sangat direkomendasikan untuk dibeli"
    elif score >= 10:
        return "BUY", "Direkomendasikan untuk dibeli"
    elif score >= 5:
        return "LEAN BUY", "Cenderung bagus untuk dibeli"
    elif score >= -2:
        return "HOLD", "Tahan atau tunggu sinyal lebih jelas"
    elif score >= -7:
        return "LEAN SELL", "Cenderung hindari"
    elif score >= -12:
        return "SELL", "Tidak direkomendasikan untuk dibeli"
    else:
        return "STRONG SELL", "Hindari sepenuhnya"


def calculate_position_sizing(score, holding_return, price_targets, volatility):
    """
    Calculate position sizing recommendation using simplified Kelly Criterion
    and fixed fraction methods.
    """
    ci = holding_return.get("confidence_intervals", {})
    scenarios = holding_return.get("scenarios", {})

    p50_return = ci.get("p50", {}).get("return_pct", 0)
    p10_return = ci.get("p10", {}).get("return_pct", 0)
    p90_return = ci.get("p90", {}).get("return_pct", 0)

    if p90_return > 0 and abs(p10_return) > 0:
        win_loss_ratio = p90_return / abs(p10_return)
    else:
        win_loss_ratio = 1.0

    bull_prob = scenarios.get("bull", {}).get("probability", 25) / 100.0
    base_prob = scenarios.get("base", {}).get("probability", 50) / 100.0
    win_rate = bull_prob + base_prob * 0.5

    if win_loss_ratio > 0 and win_rate > 0:
        kelly_raw = win_rate - (1 - win_rate) / win_loss_ratio
        kelly_fraction = max(0, min(kelly_raw, 0.5))
    else:
        kelly_fraction = 0

    kelly_half = kelly_fraction * 0.5

    vol_val = safe_float(volatility, 0.3)
    if vol_val is not None and vol_val > 0:
        vol_adjusted = max(0.02, min(0.25, 0.10 / vol_val))
    else:
        vol_adjusted = 0.10

    rr = price_targets.get("risk_reward_ratio", 0)
    if rr >= 3.0:
        rr_adjusted = 0.20
    elif rr >= 2.0:
        rr_adjusted = 0.15
    elif rr >= 1.5:
        rr_adjusted = 0.10
    else:
        rr_adjusted = 0.05

    if score >= 15:
        conviction = "VERY HIGH"
        recommended_pct = min(0.25, kelly_half * 1.2)
    elif score >= 10:
        conviction = "HIGH"
        recommended_pct = min(0.20, kelly_half)
    elif score >= 5:
        conviction = "MODERATE"
        recommended_pct = min(0.15, kelly_half * 0.8)
    elif score >= -2:
        conviction = "LOW"
        recommended_pct = min(0.05, kelly_half * 0.3)
    else:
        conviction = "VERY LOW"
        recommended_pct = 0

    recommended_pct = max(0, min(0.25, recommended_pct))

    account_risk_pct = 2.0
    stop_loss_distance = abs(price_targets.get("risk_per_share", 0))
    current_price = price_targets.get("entry_zone", {}).get("low", 0)
    if current_price and stop_loss_distance > 0:
        risk_based_shares = (account_risk_pct / 100) / (stop_loss_distance / current_price)
        risk_based_pct = min(risk_based_shares, 0.25)
    else:
        risk_based_pct = recommended_pct

    final_pct = (recommended_pct * 0.5 + risk_based_pct * 0.3 + vol_adjusted * 0.1 + rr_adjusted * 0.1)
    final_pct = max(0, min(0.25, final_pct))

    return {
        "kelly_criterion": {
            "raw_kelly": safe_round(kelly_fraction * 100, 2),
            "half_kelly": safe_round(kelly_half * 100, 2),
            "win_rate": safe_round(win_rate * 100, 2),
            "win_loss_ratio": safe_round(win_loss_ratio, 2),
        },
        "recommended_allocation": {
            "conviction_level": conviction,
            "recommended_pct": safe_round(final_pct * 100, 2),
            "max_position_pct": 25.0,
            "method": "Weighted: Kelly(50%) + Risk-based(30%) + Vol-adjusted(10%) + R/R(10%)",
        },
        "risk_parameters": {
            "account_risk_per_trade_pct": account_risk_pct,
            "volatility_adjusted_pct": safe_round(vol_adjusted * 100, 2),
            "rr_adjusted_pct": safe_round(rr_adjusted * 100, 2),
        },
        "disclaimer": "Position sizing ini untuk referensi saja. Selalu sesuaikan dengan toleransi risiko pribadi dan ukuran akun.",
    }


def generate_detailed_analysis(
    current_price, trend_info, price_targets, holding_return,
    daily_signals, weekly_signals, support_resistance, volatility,
    fundamental_data, sentiment_data, horizon_months, score
):
    strengths = []
    weaknesses = []
    opportunities = []
    risks = []
    key_factors = []
    action_plan = []

    trend = trend_info.get("trend", "NEUTRAL")
    slope = trend_info.get("slope", 0)
    rr = price_targets.get("risk_reward_ratio", 0)
    expected_return = holding_return.get("expected_return_pct", 0)
    entry_zone = price_targets.get("entry_zone", {})
    take_profit = price_targets.get("take_profit", 0)
    stop_loss = price_targets.get("stop_loss", 0)

    if "UPTREND" in trend and "DOWN" not in trend:
        strengths.append(
            "Saham dalam tren naik ({}) - harga bergerak di atas MA20 ({}) "
            "dan MA50 ({}){}".format(
                trend,
                format_rp(trend_info.get("ma20")),
                format_rp(trend_info.get("ma50")),
                " dan MA200 ({})".format(format_rp(trend_info.get("ma200"))) if trend_info.get("ma200") else "",
            )
        )
    elif "STRONG DOWNTREND" in trend:
        weaknesses.append(
            "Saham dalam tren turun kuat ({}) - harga jauh di bawah rata-rata bergerak "
            "MA20 ({}) dan MA50 ({})".format(
                trend,
                format_rp(trend_info.get("ma20")),
                format_rp(trend_info.get("ma50")),
            )
        )
    elif "DOWNTREND" in trend:
        weaknesses.append(
            "Saham dalam tren turun ({}) - harga di bawah MA20 ({})".format(
                trend, format_rp(trend_info.get("ma20"))
            )
        )

    daily_buy = sum(1 for s in daily_signals if "BUY" in s.get("recommendation", ""))
    daily_sell = sum(1 for s in daily_signals if "SELL" in s.get("recommendation", ""))
    if daily_buy > daily_sell:
        strengths.append(
            "Sinyal teknikal harian cenderung bullish ({} BUY vs {} SELL) "
            "- indikator seperti RSI, MACD, dan Bollinger memberikan sinyal beli".format(
                daily_buy, daily_sell
            )
        )
    elif daily_sell > daily_buy:
        weaknesses.append(
            "Sinyal teknikal harian cenderung bearish ({} SELL vs {} BUY) "
            "- beberapa indikator memberikan sinyal jual".format(
                daily_sell, daily_buy
            )
        )

    if weekly_signals:
        weekly_buy = sum(1 for s in weekly_signals if "BUY" in s.get("recommendation", ""))
        weekly_sell = sum(1 for s in weekly_signals if "SELL" in s.get("recommendation", ""))
        if weekly_buy > weekly_sell:
            strengths.append(
                "Sinyal teknikal mingguan bullish ({} BUY vs {} SELL) "
                "- konfirmasi dari timeframe lebih besar".format(
                    weekly_buy, weekly_sell
                )
            )
        elif weekly_sell > weekly_buy:
            weaknesses.append(
                "Sinyal teknikal mingguan bearish ({} SELL vs {} BUY) "
                "- konfirmasi negatif dari timeframe lebih besar".format(
                    weekly_sell, weekly_buy
                )
            )

    if rr >= 2.0:
        strengths.append(
            "Risk/Reward ratio sangat baik ({}x) - untuk setiap Rp 1 yang dirisiko, "
            "potensi keuntungan Rp {}. Take profit di {} dan stop loss di {}".format(
                rr, round(rr, 1), format_rp(take_profit), format_rp(stop_loss)
            )
        )
        key_factors.append(
            "Rasio ini memberikan margin of safety yang lebar. Jika salah prediksi, "
            "kerugian masih bisa ditolerir karena potensi keuntungan jauh lebih besar."
        )
    elif rr >= 1.5:
        strengths.append(
            "Risk/Reward ratio cukup baik ({}x) - take profit di {}, stop loss di {}".format(
                rr, format_rp(take_profit), format_rp(stop_loss)
            )
        )
    elif rr >= 1.0:
        key_factors.append(
            "Risk/Reward ratio seimbang ({}x) - keuntungan dan risiko hampir sama. "
            "Pertimbangkan faktor lain sebelum entry. TP: {}, SL: {}".format(
                rr, format_rp(take_profit), format_rp(stop_loss)
            )
        )
    elif rr > 0:
        weaknesses.append(
            "Risk/Reward ratio rendah ({}x) - potensi kerugian lebih besar dari keuntungan. "
            "Untuk setiap Rp 1 yang dirisiko, hanya Rp {} yang berpotensi didapat".format(
                rr, round(rr, 1)
            )
        )
        risks.append(
            "Potensi kerugian lebih besar dibanding potensi keuntungan. "
            "Pertimbangkan untuk menunggu harga lebih rendah atau cari alternatif lain."
        )

    if expected_return > 15:
        opportunities.append(
            "Potensi return sangat tinggi ({:.1f}%) dalam {} bulan "
            "- dari {} diperkirakan naik ke {}".format(
                expected_return, horizon_months, format_rp(current_price),
                format_rp(holding_return.get("expected_price"))
            )
        )
        scenarios = holding_return.get("scenarios", {})
        if scenarios.get("bear"):
            bear_ret = scenarios["bear"].get("return_pct", 0)
            if bear_ret < -5:
                key_factors.append(
                    "Proyeksi return sangat menarik untuk jangka waktu yang dipilih. "
                    "Namun bear case masih bisa turun {:.1f}% — tetap gunakan stop loss.".format(bear_ret)
                )
            else:
                key_factors.append(
                    "Proyeksi return sangat menarik untuk jangka waktu yang dipilih. "
                    "Bahkan bear case relatif aman ({:.1f}%).".format(bear_ret)
                )
    elif expected_return > 10:
        opportunities.append(
            "Potensi return tinggi ({:.1f}%) dalam {} bulan "
            "- target harga {}".format(
                expected_return, horizon_months,
                format_rp(holding_return.get("expected_price"))
            )
        )
    elif expected_return > 5:
        opportunities.append(
            "Potensi return moderat ({:.1f}%) dalam {} bulan "
            "- target harga {}".format(
                expected_return, horizon_months,
                format_rp(holding_return.get("expected_price"))
            )
        )
    elif expected_return > 0:
        key_factors.append(
            "Proyeksi return positif namun kecil ({:.1f}%) - "
            "mungkin lebih baik menunggu konfirmasi lebih jelas".format(expected_return)
        )
    elif expected_return > -5:
        weaknesses.append(
            "Proyeksi return negatif ({:.1f}%) dalam {} bulan "
            "- harga diperkirakan turun ke {}".format(
                expected_return, horizon_months,
                format_rp(holding_return.get("expected_price"))
            )
        )
        risks.append(
            "Jika tetap beli, ada kemungkinan mengalami kerugian dalam jangka waktu ini. "
            "Pertimbangkan untuk menunggu reversal atau cari saham lain."
        )
    else:
        risks.append(
            "Potensi kerugian signifikan ({:.1f}%) dalam {} bulan. "
            "Harga diperkirakan turun ke {}".format(
                expected_return, horizon_months,
                format_rp(holding_return.get("expected_price"))
            )
        )

    scenarios = holding_return.get("scenarios", {})
    if scenarios:
        bull_ret = scenarios.get("bull", {}).get("return_pct", 0)
        bear_ret = scenarios.get("bear", {}).get("return_pct", 0)
        if bull_ret > 0 and bear_ret > -5:
            key_factors.append(
                "Risk profile menarik — bull case +{:.1f}%, bear case hanya {:.1f}%. "
                "Potensi upside lebih besar dari downside.".format(bull_ret, bear_ret)
            )
        elif bear_ret < -15:
            risks.append(
                "Bear case mengindikasikan potensi kerugian hingga {:.1f}% — "
                "pertimbangkan position sizing yang lebih kecil.".format(bear_ret)
            )

    supports = support_resistance.get("support", [])
    resistances = support_resistance.get("resistance", [])

    if supports:
        valid_supports = [s for s in supports if s < current_price]
        if valid_supports:
            nearest_support = max(valid_supports)
            distance_pct = ((current_price - nearest_support) / current_price) * 100
            if distance_pct < 3:
                opportunities.append(
                    "Harga dekat level support ({}) - jarak hanya {:.1f}% "
                    "- potensi bounce dari level ini".format(
                        format_rp(nearest_support), distance_pct
                    )
                )
            else:
                key_factors.append(
                    "Support terdekat di {} ({:.1f}% di bawah harga saat ini) "
                    "- level ini bisa jadi area beli yang lebih aman".format(
                        format_rp(nearest_support), distance_pct
                    )
                )

    if resistances:
        valid_resistances = [r for r in resistances if r > current_price]
        if valid_resistances:
            nearest_resistance = min(valid_resistances)
            distance_pct = ((nearest_resistance - current_price) / current_price) * 100
            if distance_pct < 5:
                opportunities.append(
                    "Resistance terdekat di {} ({:.1f}% di atas) "
                    "- jika breakout, bisa lanjut naik".format(
                        format_rp(nearest_resistance), distance_pct
                    )
                )
            else:
                key_factors.append(
                    "Resistance terdekat di {} ({:.1f}% di atas) "
                    "- target ini bisa jadi take profit".format(
                        format_rp(nearest_resistance), distance_pct
                    )
                )

    if volatility:
        vol_pct = volatility * 100
        if vol_pct > 40:
            risks.append(
                "Volatilitas tahunan tinggi ({:.1f}%) - harga bisa bergerak fluktuatif, "
                "persiapkan mental untuk pergerakan tajam".format(vol_pct)
            )
        elif vol_pct > 25:
            key_factors.append(
                "Volatilitas tahunan moderat ({:.1f}%) - pergerakan harga cukup stabil".format(vol_pct)
            )
        elif vol_pct < 15:
            key_factors.append(
                "Volatilitas tahunan rendah ({:.1f}%) - pergerakan harga relatif tenang".format(vol_pct)
            )

    if fundamental_data:
        val_score = fundamental_data.get("valuation", {}).get("score", 0)
        quality_score = fundamental_data.get("quality", {}).get("score", 0)
        health_score = fundamental_data.get("financial_health", {}).get("score", 0)
        fund_total = val_score + quality_score + health_score

        valuation_detail = fundamental_data.get("valuation", {})
        pe = valuation_detail.get("pe_ratio")
        pb = valuation_detail.get("pb_ratio")

        if fund_total >= 4:
            strengths.append(
                "Fundamental kuat (score: {}) - valuasi, kualitas, dan kesehatan keuangan baik".format(
                    fund_total
                )
            )
            if pe and pe > 0:
                key_factors.append("P/E Ratio: {:.1f}".format(pe))
            if pb and pb > 0:
                key_factors.append("P/B Ratio: {:.1f}".format(pb))
        elif fund_total >= 2:
            key_factors.append(
                "Fundamental cukup (score: {}) - ada beberapa catatan yang perlu diperhatikan".format(
                    fund_total
                )
            )
        elif fund_total < 0:
            weaknesses.append(
                "Fundamental lemah (score: {}) - perlu evaluasi lebih dalam tentang kondisi keuangan".format(
                    fund_total
                )
            )

    if sentiment_data:
        sentiment_score = sentiment_data.get("sentiment_score", 0.5)
        sentiment_label = sentiment_data.get("overall_sentiment", "NEUTRAL")
        if sentiment_score > 0.6:
            strengths.append(
                "Sentimen pasar positif ({}) - berita dan analisis cenderung bullish".format(
                    sentiment_label
                )
            )
        elif sentiment_score < 0.4:
            weaknesses.append(
                "Sentimen pasar negatif ({}) - berita dan analisis cenderung bearish".format(
                    sentiment_label
                )
            )

    volatility_ann = None
    if volatility:
        volatility_ann = round(volatility * 100, 2)

    if score >= 8:
        action_plan.append("Entry: Beli di zona entry {} - {}".format(
            format_rp(entry_zone.get("low")), format_rp(entry_zone.get("high"))
        ))
        action_plan.append("Take Profit: {}".format(format_rp(take_profit)))
        action_plan.append("Stop Loss: {}".format(format_rp(stop_loss)))
        action_plan.append("Posisi bisa agak agresif karena konfirmasi kuat dari semua sisi")
    elif score >= 5:
        action_plan.append("Entry: Beli di zona entry {} - {}".format(
            format_rp(entry_zone.get("low")), format_rp(entry_zone.get("high"))
        ))
        action_plan.append("Take Profit: {}".format(format_rp(take_profit)))
        action_plan.append("Stop Loss: {}".format(format_rp(stop_loss)))
        action_plan.append("Gunakan position sizing yang wajar, tidak perlu terlalu agresif")
    elif score >= 2:
        action_plan.append("Entry: Pertimbangkan beli di support terdekat untuk harga lebih aman")
        action_plan.append("Take Profit: {}".format(format_rp(take_profit)))
        action_plan.append("Stop Loss: {}".format(format_rp(stop_loss)))
        action_plan.append("Gunakan position sizing kecil, tunggu konfirmasi tambahan jika memungkinkan")
    elif score >= -1:
        action_plan.append("Rekomendasi: Tahan posisi jika sudah punya, atau tunggu sinyal lebih jelas")
        action_plan.append("Jika ingin entry, tunggu harga di support terdekat")
        action_plan.append("Perhatikan breakout dari range saat ini sebagai trigger")
    else:
        action_plan.append("Rekomendasi: Hindari entry baru atau pertimbangkan sell jika sudah punya posisi")
        action_plan.append("Jika tetap entry, gunakan stop loss yang ketat dan position sizing kecil")
        action_plan.append("Tunggu reversal signal sebelum entry kembali")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "risks": risks,
        "key_factors": key_factors,
        "action_plan": action_plan,
        "volatility_ann": volatility_ann,
    }


def compare_with_benchmark(daily_data, benchmark_data, horizon_months=3):
    """
    Compare stock performance with benchmark (IHSG, sector index).
    Returns relative strength, correlation, and alpha/beta.
    """
    if not daily_data or not benchmark_data or len(daily_data) < 30 or len(benchmark_data) < 30:
        return None

    try:
        df_stock = pd.DataFrame(daily_data)
        df_bench = pd.DataFrame(benchmark_data)

        stock_close = df_stock["Close"].values
        bench_close = df_bench["Close"].values

        min_len = min(len(stock_close), len(bench_close))
        stock_close = stock_close[-min_len:]
        bench_close = bench_close[-min_len:]

        stock_returns = np.diff(stock_close) / stock_close[:-1]
        bench_returns = np.diff(bench_close) / bench_close[:-1]

        valid = ~(np.isnan(stock_returns) | np.isnan(bench_returns))
        stock_returns = stock_returns[valid]
        bench_returns = bench_returns[valid]

        if len(stock_returns) < 20:
            return None

        cov_matrix = np.cov(stock_returns, bench_returns)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1.0

        avg_stock = np.mean(stock_returns) * 252
        avg_bench = np.mean(bench_returns) * 252
        alpha = avg_stock - beta * avg_bench

        correlation = np.corrcoef(stock_returns, bench_returns)[0, 1]

        lookback = min(horizon_months * 21, min_len)
        stock_period_return = (stock_close[-1] / stock_close[-lookback] - 1) * 100
        bench_period_return = (bench_close[-1] / bench_close[-lookback] - 1) * 100
        relative_strength = stock_period_return - bench_period_return

        if relative_strength > 5:
            rs_label = "OUTPERFORM"
            rs_desc = "Saham mengunggulkan benchmark {:.1f}% dalam {} bulan terakhir".format(relative_strength, horizon_months)
        elif relative_strength > 0:
            rs_label = "SLIGHT OUTPERFORM"
            rs_desc = "Saham sedikit lebih baik dari benchmark ({:.1f}%)".format(relative_strength)
        elif relative_strength > -5:
            rs_label = "SLIGHT UNDERPERFORM"
            rs_desc = "Saham sedikit di bawah benchmark ({:.1f}%)".format(relative_strength)
        else:
            rs_label = "UNDERPERFORM"
            rs_desc = "Saham tertinggal dari benchmark {:.1f}% dalam {} bulan terakhir".format(abs(relative_strength), horizon_months)

        return {
            "benchmark_name": "IHSG",
            "stock_return_pct": safe_round(stock_period_return, 2),
            "benchmark_return_pct": safe_round(bench_period_return, 2),
            "relative_strength_pct": safe_round(relative_strength, 2),
            "relative_strength_label": rs_label,
            "relative_strength_desc": rs_desc,
            "correlation": safe_round(correlation, 4),
            "beta": safe_round(beta, 4),
            "alpha_annual": safe_round(alpha * 100, 4),
            "interpretation": {
                "beta": "Beta > 1 berarti lebih volatil dari market, < 1 lebih stabil" if beta != 1 else None,
                "alpha": "Alpha positif berarti mengunggulkan risk-adjusted return" if alpha > 0 else "Alpha negatif berarti underperform risk-adjusted",
                "correlation": "Korelasi tinggi (>{:.1f}) berarti bergerak sejalan market".format(0.7) if abs(correlation) > 0.7 else "Korelasi rendah (<{:.1f}) berarti independent dari market".format(0.3),
            }
        }
    except Exception:
        return None


def analyze_horizon(daily_data, stock_info, horizon_months=3, sentiment_data=None, fundamental_data=None, benchmark_data=None):
    if not daily_data or len(daily_data) < 30:
        return {"error": "Data tidak cukup untuk analisis horizon"}

    current_price = daily_data[-1]["Close"]
    atr = calculate_atr_value(daily_data)
    volatility = calculate_volatility(daily_data)
    trend_info = calculate_trend_strength(daily_data)
    support_resistance = calculate_support_resistance(daily_data)
    price_targets = calculate_price_targets(current_price, atr, support_resistance, trend_info, horizon_months)

    from technical import analyze_stock
    daily_analysis = analyze_stock(daily_data)
    daily_signals = daily_analysis.get("signals", [])

    weekly_data = aggregate_to_weekly(daily_data)
    weekly_signals = []
    weekly_analysis = None
    if weekly_data and len(weekly_data) >= 30:
        weekly_analysis = analyze_stock(weekly_data)
        weekly_signals = weekly_analysis.get("signals", [])

    fundamental_score = 0
    if fundamental_data:
        fundamental_score = fundamental_data.get("total_score", 0)

    holding_return = estimate_holding_period_return(
        current_price, trend_info, volatility, horizon_months, fundamental_score
    )

    tf_score, tf_details = calculate_timeframe_score(
        daily_signals, weekly_signals, trend_info, support_resistance,
        price_targets, holding_return
    )

    sentiment_score = 0
    sentiment_label = "NEUTRAL"
    if sentiment_data:
        sentiment_score = sentiment_data.get("sentiment_score", 0.5)
        sentiment_label = sentiment_data.get("overall_sentiment", "NEUTRAL")
        if sentiment_score > 0.6:
            tf_score += 1
            tf_details.append({"factor": "Sentiment", "value": sentiment_label, "impact": 1})
        elif sentiment_score < 0.4:
            tf_score -= 1
            tf_details.append({"factor": "Sentiment", "value": sentiment_label, "impact": -1})

    if fundamental_data:
        val_score = fundamental_data.get("valuation", {}).get("score", 0)
        quality_score = fundamental_data.get("quality", {}).get("score", 0)
        health_score = fundamental_data.get("financial_health", {}).get("score", 0)
        fund_total = val_score + quality_score + health_score
        if fund_total >= 4:
            tf_score += 2
            tf_details.append({"factor": "Fundamental", "value": "Score: {}".format(fund_total), "impact": 2})
        elif fund_total >= 2:
            tf_score += 1
            tf_details.append({"factor": "Fundamental", "value": "Score: {}".format(fund_total), "impact": 1})
        elif fund_total < 0:
            tf_score -= 1
            tf_details.append({"factor": "Fundamental", "value": "Score: {}".format(fund_total), "impact": -1})

    recommendation, rationale = generate_horizon_recommendation(tf_score)

    position_sizing = calculate_position_sizing(
        tf_score, holding_return, price_targets, volatility
    )

    detailed = generate_detailed_analysis(
        current_price, trend_info, price_targets, holding_return,
        daily_signals, weekly_signals, support_resistance, volatility,
        fundamental_data, sentiment_data, horizon_months, tf_score
    )

    horizon_labels = {
        1: "1 Bulan",
        3: "3 Bulan",
        6: "6 Bulan",
        12: "12 Bulan (1 Tahun)",
    }

    return {
        "symbol": stock_info.get("symbol") if stock_info else None,
        "company_name": stock_info.get("name") if stock_info else None,
        "current_price": current_price,
        "analysis_date": datetime.now().isoformat(),
        "horizon": {
            "months": horizon_months,
            "label": horizon_labels.get(horizon_months, "{} Bulan".format(horizon_months)),
        },
        "recommendation": recommendation,
        "rationale": rationale,
        "score": tf_score,
        "score_details": tf_details,
        "detailed_analysis": detailed,
        "technical": {
            "daily_signals": daily_signals,
            "weekly_signals": weekly_signals,
            "overall_daily": daily_analysis.get("overall_signal"),
            "trend": trend_info,
        },
        "support_resistance": support_resistance,
        "price_targets": price_targets,
        "holding_period_estimate": holding_return,
        "risk_metrics": {
            "volatility_annualized": safe_round(safe_float(volatility, 0) * 100, 2) if safe_float(volatility) is not None else None,
            "atr": safe_round(atr, 2),
        },
        "sentiment": {
            "label": sentiment_label,
            "score": sentiment_score,
        },
        "fundamental_score": fundamental_score,
        "benchmark": compare_with_benchmark(daily_data, benchmark_data, horizon_months) if benchmark_data else None,
        "position_sizing": position_sizing,
    }


def get_all_horizons(daily_data, stock_info, sentiment_data=None, fundamental_data=None, benchmark_data=None):
    horizons = {}
    for months in [1, 3, 6, 12]:
        result = analyze_horizon(daily_data, stock_info, months, sentiment_data, fundamental_data, benchmark_data)
        horizons["{}m".format(months)] = result

    return horizons
