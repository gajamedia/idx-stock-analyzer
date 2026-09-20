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
        df["Date"] = pd.to_datetime(df["Date"])
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
        return {"support": [], "resistance": []}

    df = pd.DataFrame(prices_data)
    close = df["Close"].values
    high = df["High"].values if "High" in df.columns else close
    low = df["Low"].values if "Low" in df.columns else close

    n = min(lookback, len(close))
    recent_close = close[-n:]
    recent_high = high[-n:]
    recent_low = low[-n:]

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

    return {"support": supports, "resistance": resistances}


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
        return {"trend": "NEUTRAL", "strength": 0, "slope": 0, "ma20": 0, "ma50": 0}

    df = pd.DataFrame(prices_data)
    close = df["Close"].values
    n = len(close)

    valid_close = close[~np.isnan(close)]
    if len(valid_close) < 20:
        return {"trend": "NEUTRAL", "strength": 0, "slope": 0, "ma20": 0, "ma50": 0}

    ma20 = np.nanmean(close[-20:])
    ma50 = np.nanmean(close[-50:]) if n >= 50 else np.nanmean(close)

    x = np.arange(20)
    recent_close = close[-20:]
    valid_recent = recent_close[~np.isnan(recent_close)]
    if len(valid_recent) < 5:
        return {"trend": "NEUTRAL", "strength": 0, "slope": 0, "ma20": safe_round(ma20, 2, 0), "ma50": safe_round(ma50, 2, 0)}

    slope = np.polyfit(x[-len(valid_recent):], valid_recent, 1)[0]
    last_valid_price = valid_recent[-1]
    normalized_slope = slope / last_valid_price * 100 if last_valid_price != 0 else 0

    if last_valid_price > ma20 > ma50:
        trend = "STRONG UPTREND"
        strength = min(100, int(abs(normalized_slope) * 10 + 50))
    elif last_valid_price > ma20:
        trend = "UPTREND"
        strength = min(80, int(abs(normalized_slope) * 10 + 30))
    elif last_valid_price < ma20 < ma50:
        trend = "STRONG DOWNTREND"
        strength = max(-100, int(-abs(normalized_slope) * 10 - 50))
    elif last_valid_price < ma20:
        trend = "DOWNTREND"
        strength = max(-80, int(-abs(normalized_slope) * 10 - 30))
    else:
        trend = "NEUTRAL"
        strength = 0

    return {
        "trend": trend,
        "strength": strength,
        "slope": safe_round(normalized_slope, 4, 0),
        "ma20": safe_round(ma20, 2, 0),
        "ma50": safe_round(ma50, 2, 0),
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
    elif trend_info["trend"] in ["STRONG DOWNTREND", "DOWNTREND"]:
        take_profit = current_price + (atr_targets * 1.0)
        stop_loss = current_price - (atr_targets * 2.0)
        entry_zone_low = current_price - (atr_targets * 0.5)
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
    slope_val = safe_float(trend_info.get("slope"), 0)
    base_monthly_return = slope_val / 100

    vol_adjustment = 1.0
    vol_val = safe_float(volatility)
    if vol_val is not None:
        if vol_val > 0.5:
            vol_adjustment = 0.6
        elif vol_val > 0.3:
            vol_adjustment = 0.8
        elif vol_val < 0.15:
            vol_adjustment = 1.2

    fund_val = safe_float(fundamental_score, 0)
    fundamental_boost = fund_val / 20.0

    monthly_returns = []
    cumulative = 1.0
    for m in range(1, horizon_months + 1):
        monthly_r = base_monthly_return * vol_adjustment * (1 + fundamental_boost)
        cumulative *= (1 + monthly_r)
        monthly_returns.append({
            "month": m,
            "estimated_return": round((cumulative - 1) * 100, 2),
            "estimated_price": round(current_price * cumulative, 2),
        })

    return {
        "horizon_months": horizon_months,
        "monthly_estimate": monthly_returns,
        "expected_return_pct": round((cumulative - 1) * 100, 2),
        "expected_price": round(current_price * cumulative, 2),
    }


def calculate_timeframe_score(daily_signals, weekly_signals, trend_info, support_resistance, price_targets, holding_return):
    score = 0
    details = []

    daily_buy = sum(1 for s in daily_signals if "BUY" in s.get("recommendation", ""))
    daily_sell = sum(1 for s in daily_signals if "SELL" in s.get("recommendation", ""))
    daily_net = daily_buy - daily_sell
    score += daily_net
    details.append({
        "factor": "Daily Technical Signals",
        "value": f"Buy: {daily_buy}, Sell: {daily_sell}",
        "impact": daily_net,
    })

    if weekly_signals:
        weekly_buy = sum(1 for s in weekly_signals if "BUY" in s.get("recommendation", ""))
        weekly_sell = sum(1 for s in weekly_signals if "SELL" in s.get("recommendation", ""))
        weekly_net = weekly_buy - weekly_sell
        score += weekly_net
        details.append({
            "factor": "Weekly Technical Signals",
            "value": f"Buy: {weekly_buy}, Sell: {weekly_sell}",
            "impact": weekly_net,
        })

    trend = trend_info["trend"]
    if "STRONG UPTREND" in trend:
        score += 3
        details.append({"factor": "Trend", "value": trend, "impact": 3})
    elif "UPTREND" in trend:
        score += 2
        details.append({"factor": "Trend", "value": trend, "impact": 2})
    elif "STRONG DOWNTREND" in trend:
        score -= 3
        details.append({"factor": "Trend", "value": trend, "impact": -3})
    elif "DOWNTREND" in trend:
        score -= 2
        details.append({"factor": "Trend", "value": trend, "impact": -2})
    else:
        details.append({"factor": "Trend", "value": trend, "impact": 0})

    rr = price_targets.get("risk_reward_ratio", 0)
    if rr >= 2.0:
        score += 2
        details.append({"factor": "Risk/Reward", "value": f"{rr}x", "impact": 2})
    elif rr >= 1.5:
        score += 1
        details.append({"factor": "Risk/Reward", "value": f"{rr}x", "impact": 1})
    elif rr < 1.0:
        score -= 1
        details.append({"factor": "Risk/Reward", "value": f"{rr}x", "impact": -1})

    expected_return = holding_return.get("expected_return_pct", 0)
    if expected_return > 10:
        score += 2
        details.append({"factor": "Expected Return", "value": f"{expected_return}%", "impact": 2})
    elif expected_return > 5:
        score += 1
        details.append({"factor": "Expected Return", "value": f"{expected_return}%", "impact": 1})
    elif expected_return < -5:
        score -= 1
        details.append({"factor": "Expected Return", "value": f"{expected_return}%", "impact": -1})

    return score, details


def format_rp(value):
    if value is None:
        return "N/A"
    f = safe_float(value)
    if f is None:
        return "N/A"
    return "Rp {:,.0f}".format(f).replace(",", ".")


def generate_horizon_recommendation(score):
    if score >= 8:
        return "STRONG BUY", "Sangat direkomendasikan untuk dibeli"
    elif score >= 5:
        return "BUY", "Direkomendasikan untuk dibeli"
    elif score >= 2:
        return "LEAN BUY", "Cenderung bagus untuk dibeli"
    elif score >= -1:
        return "HOLD", "Tahan atau tunggu sinyal lebih jelas"
    elif score >= -4:
        return "LEAN SELL", "Cenderung hindari"
    else:
        return "SELL", "Tidak direkomendasikan untuk dibeli"


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
            "dan MA50 ({})".format(
                trend,
                format_rp(trend_info.get("ma20")),
                format_rp(trend_info.get("ma50")),
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
        key_factors.append(
            "Proyeksi return sangat menarik untuk jangka waktu yang dipilih. "
            "Pertimbangkan untuk mengambil posisi lebih besar."
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


def analyze_horizon(daily_data, stock_info, horizon_months=3, sentiment_data=None, fundamental_data=None):
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
    }


def get_all_horizons(daily_data, stock_info, sentiment_data=None, fundamental_data=None):
    horizons = {}
    for months in [1, 3, 6, 12]:
        result = analyze_horizon(daily_data, stock_info, months, sentiment_data, fundamental_data)
        horizons["{}m".format(months)] = result

    return horizons
