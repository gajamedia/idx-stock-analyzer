import math


def is_valid_number(val):
    """Check if a value is a valid finite number (not None, NaN, or inf)."""
    if val is None:
        return False
    try:
        f = float(val)
        return not math.isnan(f) and not math.isinf(f)
    except (TypeError, ValueError):
        return False


def safe_round(val, decimals=2, default=None):
    """Round a value safely, returning default if not a valid number."""
    if not is_valid_number(val):
        return default
    return round(float(val), decimals)


def analyze_fundamental(stock_info):
    if not stock_info:
        return {"error": "No data available"}

    pe = stock_info.get("pe_ratio")
    pb = stock_info.get("pb_ratio")
    roe = stock_info.get("roe")
    profit_margin = stock_info.get("profit_margin")
    debt_equity = stock_info.get("debt_to_equity")
    dividend_yield = stock_info.get("dividend_yield")
    market_cap = stock_info.get("market_cap", 0)

    valuation_score = 0
    valuation_details = []

    if is_valid_number(pe):
        pe_val = float(pe)
        if pe_val < 10:
            valuation_score += 2
            valuation_details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "UNDERVALUED", "score": 2})
        elif pe_val < 15:
            valuation_score += 1
            valuation_details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "FAIR", "score": 1})
        elif pe_val < 25:
            valuation_details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "SLIGHTLY HIGH", "score": 0})
        else:
            valuation_score -= 1
            valuation_details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "OVERVALUED", "score": -1})

    if is_valid_number(pb):
        pb_val = float(pb)
        if pb_val < 1:
            valuation_score += 2
            valuation_details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "UNDERVALUED", "score": 2})
        elif pb_val < 2:
            valuation_score += 1
            valuation_details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "FAIR", "score": 1})
        elif pb_val < 4:
            valuation_details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "SLIGHTLY HIGH", "score": 0})
        else:
            valuation_score -= 1
            valuation_details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "OVERVALUED", "score": -1})

    quality_score = 0
    quality_details = []

    if is_valid_number(roe):
        roe_val = float(roe)
        roe_pct = roe_val * 100 if roe_val < 1 else roe_val
        if roe_pct > 20:
            quality_score += 2
            quality_details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "EXCELLENT", "score": 2})
        elif roe_pct > 15:
            quality_score += 1
            quality_details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "GOOD", "score": 1})
        elif roe_pct > 10:
            quality_details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "AVERAGE", "score": 0})
        else:
            quality_score -= 1
            quality_details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "POOR", "score": -1})

    if is_valid_number(profit_margin):
        pm_val = float(profit_margin)
        pm_pct = pm_val * 100 if pm_val < 1 else pm_val
        if pm_pct > 20:
            quality_score += 2
            quality_details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "HIGH", "score": 2})
        elif pm_pct > 10:
            quality_score += 1
            quality_details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "GOOD", "score": 1})
        elif pm_pct > 5:
            quality_details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "AVERAGE", "score": 0})
        else:
            quality_score -= 1
            quality_details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "LOW", "score": -1})

    health_score = 0
    health_details = []

    if is_valid_number(debt_equity):
        de_val = float(debt_equity)
        if de_val < 50:
            health_score += 2
            health_details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "LOW", "score": 2})
        elif de_val < 100:
            health_score += 1
            health_details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "MODERATE", "score": 1})
        elif de_val < 200:
            health_details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "HIGH", "score": 0})
        else:
            health_score -= 1
            health_details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "VERY HIGH", "score": -1})

    dividend_info = None
    if is_valid_number(dividend_yield):
        div_val = float(dividend_yield)
        div_pct = div_val * 100 if div_val < 1 else div_val
        if div_pct > 5:
            dividend_info = {"value": f"{div_pct:.1f}%", "status": "HIGH YIELD"}
        elif div_pct > 2:
            dividend_info = {"value": f"{div_pct:.1f}%", "status": "GOOD YIELD"}
        elif div_pct > 0:
            dividend_info = {"value": f"{div_pct:.1f}%", "status": "LOW YIELD"}
        else:
            dividend_info = {"value": "0%", "status": "NO DIVIDEND"}

    market_cap_category = "N/A"
    mc_val = safe_round(market_cap, 0, 0)
    if mc_val and mc_val > 0:
        if mc_val > 100_000_000_000_000:
            market_cap_category = "MEGA CAP (>100T)"
        elif mc_val > 10_000_000_000_000:
            market_cap_category = "LARGE CAP (10T-100T)"
        elif mc_val > 2_000_000_000_000:
            market_cap_category = "MID CAP (2T-10T)"
        elif mc_val > 500_000_000_000:
            market_cap_category = "SMALL CAP (500B-2T)"
        else:
            market_cap_category = "MICRO CAP (<500B)"

    total_score = valuation_score + quality_score + health_score
    if total_score >= 4:
        recommendation = "STRONG BUY - Undervalued quality stock"
    elif total_score >= 2:
        recommendation = "BUY - Good value"
    elif total_score >= 0:
        recommendation = "HOLD - Fairly valued"
    elif total_score >= -2:
        recommendation = "SELL - Overvalued"
    else:
        recommendation = "STRONG SELL - Avoid"

    return {
        "symbol": stock_info.get("symbol"),
        "name": stock_info.get("name"),
        "sector": stock_info.get("sector"),
        "industry": stock_info.get("industry"),
        "market_cap": market_cap,
        "market_cap_category": market_cap_category,
        "revenue": stock_info.get("revenue"),
        "net_profit": stock_info.get("net_profit"),
        "gross_margin": stock_info.get("gross_margin"),
        "valuation": {"score": valuation_score, "details": valuation_details},
        "quality": {"score": quality_score, "details": quality_details},
        "financial_health": {"score": health_score, "details": health_details},
        "dividend": dividend_info,
        "total_score": total_score,
        "recommendation": recommendation,
        "report_info": {
            "period": stock_info.get("report_period"),
            "type": stock_info.get("report_type"),
            "source": stock_info.get("report_source"),
            "updated_at": stock_info.get("report_updated_at"),
            "available_periods": stock_info.get("available_periods"),
        },
    }
