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


def safe_float(val, default=None):
    """Convert value to float safely, returning default if not valid."""
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
    """Round a value safely, returning default if not a valid number."""
    if not is_valid_number(val):
        return default
    return round(float(val), decimals)


def format_large_number(val):
    """Format large numbers: 1.5T, 500B, 100M, etc."""
    if not is_valid_number(val):
        return "N/A"
    val = float(val)
    if val >= 1_000_000_000_000:
        return f"{val/1_000_000_000_000:.1f}T"
    elif val >= 1_000_000_000:
        return f"{val/1_000_000_000:.1f}B"
    elif val >= 1_000_000:
        return f"{val/1_000_000:.1f}M"
    elif val >= 1_000:
        return f"{val/1_000:.1f}K"
    else:
        return f"{val:.0f}"


# ============================================================
# SECTOR-SPECIFIC THRESHOLDS
# Based on IDX sector norms and global standards
# ============================================================

SECTOR_THRESHOLDS = {
    "Finance": {
        "pe": {"undervalued": 10, "fair": 15, "slightly_high": 20, "overvalued": 25},
        "pb": {"undervalued": 1.0, "fair": 2.0, "slightly_high": 3.0, "overvalued": 4.0},
        "roe": {"excellent": 0.20, "good": 0.15, "average": 0.10, "poor": 0.05},
        "profit_margin": {"high": 0.40, "good": 0.25, "average": 0.15, "low": 0.05},
        "debt_equity": {"low": 50, "moderate": 100, "high": 200, "very_high": 500},
        "dividend_yield": {"high": 0.06, "good": 0.03, "low": 0.01},
        "description": "Banks & Financial Institutions — high leverage is normal, focus on ROE and NIM",
    },
    "Technology": {
        "pe": {"undervalued": 15, "fair": 25, "slightly_high": 40, "overvalued": 60},
        "pb": {"undervalued": 2.0, "fair": 5.0, "slightly_high": 10.0, "overvalued": 15.0},
        "roe": {"excellent": 0.25, "good": 0.15, "average": 0.08, "poor": 0.02},
        "profit_margin": {"high": 0.25, "good": 0.15, "average": 0.08, "low": 0.02},
        "debt_equity": {"low": 30, "moderate": 80, "high": 150, "very_high": 250},
        "dividend_yield": {"high": 0.03, "good": 0.01, "low": 0.005},
        "description": "Tech companies — high PE normal if growth is strong, focus on revenue growth",
    },
    "Consumer Cyclical": {
        "pe": {"undervalued": 10, "fair": 18, "slightly_high": 25, "overvalued": 35},
        "pb": {"undervalued": 1.5, "fair": 3.0, "slightly_high": 5.0, "overvalued": 8.0},
        "roe": {"excellent": 0.22, "good": 0.15, "average": 0.08, "poor": 0.03},
        "profit_margin": {"high": 0.20, "good": 0.12, "average": 0.06, "low": 0.02},
        "debt_equity": {"low": 40, "moderate": 100, "high": 180, "very_high": 300},
        "dividend_yield": {"high": 0.05, "good": 0.02, "low": 0.01},
        "description": "Auto, retail, hospitality — cyclical, PE varies with business cycle",
    },
    "Consumer Defensive": {
        "pe": {"undervalued": 15, "fair": 22, "slightly_high": 30, "overvalued": 40},
        "pb": {"undervalued": 2.0, "fair": 5.0, "slightly_high": 8.0, "overvalued": 12.0},
        "roe": {"excellent": 0.25, "good": 0.18, "average": 0.10, "poor": 0.05},
        "profit_margin": {"high": 0.25, "good": 0.15, "average": 0.08, "low": 0.03},
        "debt_equity": {"low": 30, "moderate": 80, "high": 150, "very_high": 250},
        "dividend_yield": {"high": 0.05, "good": 0.025, "low": 0.01},
        "description": "FMCG, consumer staples — stable earnings, premium valuation normal",
    },
    "Healthcare": {
        "pe": {"undervalued": 12, "fair": 22, "slightly_high": 35, "overvalued": 50},
        "pb": {"undervalued": 2.0, "fair": 5.0, "slightly_high": 8.0, "overvalued": 12.0},
        "roe": {"excellent": 0.22, "good": 0.15, "average": 0.08, "poor": 0.03},
        "profit_margin": {"high": 0.25, "good": 0.15, "average": 0.08, "low": 0.03},
        "debt_equity": {"low": 30, "moderate": 80, "high": 150, "very_high": 250},
        "dividend_yield": {"high": 0.04, "good": 0.02, "low": 0.005},
        "description": "Pharma, healthcare — steady growth, R&D intensive",
    },
    "Basic Materials": {
        "pe": {"undervalued": 6, "fair": 12, "slightly_high": 18, "overvalued": 25},
        "pb": {"undervalued": 0.8, "fair": 1.5, "slightly_high": 2.5, "overvalued": 4.0},
        "roe": {"excellent": 0.18, "good": 0.12, "average": 0.06, "poor": 0.02},
        "profit_margin": {"high": 0.20, "good": 0.12, "average": 0.06, "low": 0.02},
        "debt_equity": {"low": 30, "moderate": 80, "high": 150, "very_high": 250},
        "dividend_yield": {"high": 0.07, "good": 0.03, "low": 0.01},
        "description": "Mining, metals, chemicals — cyclical, commodity-dependent",
    },
    "Energy": {
        "pe": {"undervalued": 5, "fair": 10, "slightly_high": 15, "overvalued": 22},
        "pb": {"undervalued": 0.8, "fair": 1.5, "slightly_high": 2.5, "overvalued": 4.0},
        "roe": {"excellent": 0.18, "good": 0.12, "average": 0.06, "poor": 0.02},
        "profit_margin": {"high": 0.25, "good": 0.15, "average": 0.08, "low": 0.03},
        "debt_equity": {"low": 30, "moderate": 80, "high": 150, "very_high": 250},
        "dividend_yield": {"high": 0.08, "good": 0.04, "low": 0.01},
        "description": "Oil, gas, coal — highly cyclical, commodity price driven",
    },
    "Telecommunication": {
        "pe": {"undervalued": 12, "fair": 18, "slightly_high": 25, "overvalued": 35},
        "pb": {"undervalued": 1.5, "fair": 3.0, "slightly_high": 5.0, "overvalued": 8.0},
        "roe": {"excellent": 0.20, "good": 0.12, "average": 0.06, "poor": 0.02},
        "profit_margin": {"high": 0.25, "good": 0.15, "average": 0.08, "low": 0.03},
        "debt_equity": {"low": 40, "moderate": 100, "high": 180, "very_high": 300},
        "dividend_yield": {"high": 0.05, "good": 0.025, "low": 0.01},
        "description": "Telco — capital intensive, steady cash flow",
    },
    "Real Estate": {
        "pe": {"undervalued": 8, "fair": 15, "slightly_high": 22, "overvalued": 30},
        "pb": {"undervalued": 0.7, "fair": 1.2, "slightly_high": 2.0, "overvalued": 3.0},
        "roe": {"excellent": 0.15, "good": 0.10, "average": 0.05, "poor": 0.02},
        "profit_margin": {"high": 0.25, "good": 0.15, "average": 0.08, "low": 0.03},
        "debt_equity": {"low": 50, "moderate": 100, "high": 200, "very_high": 350},
        "dividend_yield": {"high": 0.06, "good": 0.03, "low": 0.01},
        "description": "Property, REITs — asset-heavy, PB more meaningful than PE",
    },
    "Utilities": {
        "pe": {"undervalued": 10, "fair": 16, "slightly_high": 22, "overvalued": 30},
        "pb": {"undervalued": 1.0, "fair": 2.0, "slightly_high": 3.5, "overvalued": 5.0},
        "roe": {"excellent": 0.18, "good": 0.12, "average": 0.06, "poor": 0.02},
        "profit_margin": {"high": 0.25, "good": 0.15, "average": 0.08, "low": 0.03},
        "debt_equity": {"low": 50, "moderate": 120, "high": 200, "very_high": 350},
        "dividend_yield": {"high": 0.06, "good": 0.03, "low": 0.01},
        "description": "Power, water — regulated, stable dividends",
    },
}

DEFAULT_THRESHOLDS = {
    "pe": {"undervalued": 10, "fair": 18, "slightly_high": 25, "overvalued": 35},
    "pb": {"undervalued": 1.0, "fair": 2.5, "slightly_high": 5.0, "overvalued": 8.0},
    "roe": {"excellent": 0.20, "good": 0.12, "average": 0.06, "poor": 0.02},
    "profit_margin": {"high": 0.20, "good": 0.12, "average": 0.06, "low": 0.02},
    "debt_equity": {"low": 40, "moderate": 100, "high": 180, "very_high": 300},
    "dividend_yield": {"high": 0.05, "good": 0.025, "low": 0.01},
    "description": "Generic thresholds for unknown sectors",
}


def get_sector_thresholds(sector):
    """Get thresholds for a specific sector, with fallback to defaults."""
    if sector and sector in SECTOR_THRESHOLDS:
        return SECTOR_THRESHOLDS[sector]
    return DEFAULT_THRESHOLDS


# ============================================================
# SCORING FUNCTIONS
# ============================================================

def score_valuation(pe, pb, thresholds):
    """Score valuation metrics using sector-specific thresholds."""
    score = 0
    details = []
    t = thresholds["pe"]

    if is_valid_number(pe):
        pe_val = float(pe)
        if pe_val < 0:
            score -= 1
            details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "NEGATIVE EARNINGS", "score": -1})
        elif pe_val < t["undervalued"]:
            score += 2
            details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "UNDERVALUED", "score": 2})
        elif pe_val < t["fair"]:
            score += 1
            details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "FAIR", "score": 1})
        elif pe_val < t["slightly_high"]:
            details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "SLIGHTLY HIGH", "score": 0})
        elif pe_val < t["overvalued"]:
            score -= 1
            details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "HIGH", "score": -1})
        else:
            score -= 2
            details.append({"metric": "PE Ratio", "value": round(pe_val, 2), "status": "OVERVALUED", "score": -2})

    t = thresholds["pb"]
    if is_valid_number(pb):
        pb_val = float(pb)
        if pb_val < 0:
            score -= 1
            details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "NEGATIVE BOOK VALUE", "score": -1})
        elif pb_val < t["undervalued"]:
            score += 2
            details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "UNDERVALUED", "score": 2})
        elif pb_val < t["fair"]:
            score += 1
            details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "FAIR", "score": 1})
        elif pb_val < t["slightly_high"]:
            details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "SLIGHTLY HIGH", "score": 0})
        elif pb_val < t["overvalued"]:
            score -= 1
            details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "HIGH", "score": -1})
        else:
            score -= 2
            details.append({"metric": "PB Ratio", "value": round(pb_val, 2), "status": "OVERVALUED", "score": -2})

    return score, details


def score_quality(roe, profit_margin, gross_margin, operating_margin, thresholds):
    """Score quality metrics using sector-specific thresholds."""
    score = 0
    details = []

    t = thresholds["roe"]
    if is_valid_number(roe):
        roe_val = float(roe)
        roe_pct = roe_val * 100
        if roe_val < 0:
            score -= 2
            details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "NEGATIVE", "score": -2})
        elif roe_val >= t["excellent"]:
            score += 3
            details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "EXCELLENT", "score": 3})
        elif roe_val >= t["good"]:
            score += 2
            details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "GOOD", "score": 2})
        elif roe_val >= t["average"]:
            score += 1
            details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "AVERAGE", "score": 1})
        elif roe_val >= t["poor"]:
            details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "BELOW AVERAGE", "score": 0})
        else:
            score -= 1
            details.append({"metric": "ROE", "value": f"{roe_pct:.1f}%", "status": "POOR", "score": -1})

    t = thresholds["profit_margin"]
    if is_valid_number(profit_margin):
        pm_val = float(profit_margin)
        pm_pct = pm_val * 100
        if pm_val < 0:
            score -= 1
            details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "NEGATIVE", "score": -1})
        elif pm_val >= t["high"]:
            score += 2
            details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "HIGH", "score": 2})
        elif pm_val >= t["good"]:
            score += 1
            details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "GOOD", "score": 1})
        elif pm_val >= t["average"]:
            details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "AVERAGE", "score": 0})
        else:
            score -= 1
            details.append({"metric": "Profit Margin", "value": f"{pm_pct:.1f}%", "status": "LOW", "score": -1})

    if is_valid_number(gross_margin):
        gm_val = float(gross_margin)
        gm_pct = gm_val * 100
        if gm_val > 0.50:
            score += 1
            details.append({"metric": "Gross Margin", "value": f"{gm_pct:.1f}%", "status": "EXCELLENT", "score": 1})
        elif gm_val > 0.30:
            details.append({"metric": "Gross Margin", "value": f"{gm_pct:.1f}%", "status": "GOOD", "score": 0})
        elif gm_val > 0.15:
            details.append({"metric": "Gross Margin", "value": f"{gm_pct:.1f}%", "status": "AVERAGE", "score": 0})
        else:
            score -= 1
            details.append({"metric": "Gross Margin", "value": f"{gm_pct:.1f}%", "status": "LOW", "score": -1})

    if is_valid_number(operating_margin):
        om_val = float(operating_margin)
        om_pct = om_val * 100
        if om_val > 0.25:
            score += 1
            details.append({"metric": "Operating Margin", "value": f"{om_pct:.1f}%", "status": "EXCELLENT", "score": 1})
        elif om_val > 0.15:
            details.append({"metric": "Operating Margin", "value": f"{om_pct:.1f}%", "status": "GOOD", "score": 0})
        elif om_val > 0.05:
            details.append({"metric": "Operating Margin", "value": f"{om_pct:.1f}%", "status": "AVERAGE", "score": 0})
        else:
            score -= 1
            details.append({"metric": "Operating Margin", "value": f"{om_pct:.1f}%", "status": "LOW", "score": -1})

    return score, details


def score_health(debt_equity, current_ratio, interest_coverage, thresholds):
    """Score financial health metrics using sector-specific thresholds."""
    score = 0
    details = []

    t = thresholds["debt_equity"]
    if is_valid_number(debt_equity):
        de_val = float(debt_equity)
        if de_val < t["low"]:
            score += 2
            details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "LOW", "score": 2})
        elif de_val < t["moderate"]:
            score += 1
            details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "MODERATE", "score": 1})
        elif de_val < t["high"]:
            details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "HIGH", "score": 0})
        elif de_val < t["very_high"]:
            score -= 1
            details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "VERY HIGH", "score": -1})
        else:
            score -= 2
            details.append({"metric": "Debt/Equity", "value": f"{de_val:.1f}%", "status": "DANGEROUS", "score": -2})

    if is_valid_number(current_ratio):
        cr_val = float(current_ratio)
        if cr_val >= 2.0:
            score += 1
            details.append({"metric": "Current Ratio", "value": f"{cr_val:.2f}", "status": "STRONG", "score": 1})
        elif cr_val >= 1.2:
            details.append({"metric": "Current Ratio", "value": f"{cr_val:.2f}", "status": "ADEQUATE", "score": 0})
        elif cr_val >= 0.8:
            score -= 1
            details.append({"metric": "Current Ratio", "value": f"{cr_val:.2f}", "status": "WEAK", "score": -1})
        else:
            score -= 2
            details.append({"metric": "Current Ratio", "value": f"{cr_val:.2f}", "status": "DISTRESSED", "score": -2})

    if is_valid_number(interest_coverage):
        ic_val = float(interest_coverage)
        if ic_val >= 5.0:
            score += 1
            details.append({"metric": "Interest Coverage", "value": f"{ic_val:.2f}x", "status": "STRONG", "score": 1})
        elif ic_val >= 2.0:
            details.append({"metric": "Interest Coverage", "value": f"{ic_val:.2f}x", "status": "ADEQUATE", "score": 0})
        elif ic_val >= 1.0:
            score -= 1
            details.append({"metric": "Interest Coverage", "value": f"{ic_val:.2f}x", "status": "WEAK", "score": -1})
        else:
            score -= 2
            details.append({"metric": "Interest Coverage", "value": f"{ic_val:.2f}x", "status": "DISTRESSED", "score": -2})

    return score, details


def score_growth(revenue_growth, eps_growth, roe_trend):
    """Score growth metrics."""
    score = 0
    details = []

    if is_valid_number(revenue_growth):
        rg_val = float(revenue_growth) * 100
        if rg_val > 20:
            score += 2
            details.append({"metric": "Revenue Growth", "value": f"{rg_val:.1f}%", "status": "HIGH GROWTH", "score": 2})
        elif rg_val > 10:
            score += 1
            details.append({"metric": "Revenue Growth", "value": f"{rg_val:.1f}%", "status": "GROWING", "score": 1})
        elif rg_val > 0:
            details.append({"metric": "Revenue Growth", "value": f"{rg_val:.1f}%", "status": "SLOW GROWTH", "score": 0})
        elif rg_val > -10:
            score -= 1
            details.append({"metric": "Revenue Growth", "value": f"{rg_val:.1f}%", "status": "DECLINING", "score": -1})
        else:
            score -= 2
            details.append({"metric": "Revenue Growth", "value": f"{rg_val:.1f}%", "status": "SHARP DECLINE", "score": -2})

    if is_valid_number(eps_growth):
        eg_val = float(eps_growth) * 100
        if eg_val > 25:
            score += 2
            details.append({"metric": "EPS Growth", "value": f"{eg_val:.1f}%", "status": "HIGH GROWTH", "score": 2})
        elif eg_val > 10:
            score += 1
            details.append({"metric": "EPS Growth", "value": f"{eg_val:.1f}%", "status": "GROWING", "score": 1})
        elif eg_val > 0:
            details.append({"metric": "EPS Growth", "value": f"{eg_val:.1f}%", "status": "SLOW GROWTH", "score": 0})
        elif eg_val > -15:
            score -= 1
            details.append({"metric": "EPS Growth", "value": f"{eg_val:.1f}%", "status": "DECLINING", "score": -1})
        else:
            score -= 2
            details.append({"metric": "EPS Growth", "value": f"{eg_val:.1f}%", "status": "SHARP DECLINE", "score": -2})

    if is_valid_number(roe_trend):
        rt_val = float(roe_trend)
        if rt_val > 0.02:
            score += 1
            details.append({"metric": "ROE Trend", "value": "Improving", "status": "POSITIVE", "score": 1})
        elif rt_val < -0.02:
            score -= 1
            details.append({"metric": "ROE Trend", "value": "Declining", "status": "NEGATIVE", "score": -1})
        else:
            details.append({"metric": "ROE Trend", "value": "Stable", "status": "STABLE", "score": 0})

    return score, details


def score_dividend(dividend_yield, payout_ratio, thresholds):
    """Score dividend metrics."""
    details = []

    t = thresholds["dividend_yield"]
    if is_valid_number(dividend_yield):
        dy_val = float(dividend_yield)
        dy_pct = dy_val * 100
        if dy_val >= t["high"]:
            details.append({"metric": "Dividend Yield", "value": f"{dy_pct:.1f}%", "status": "HIGH YIELD", "score": 0})
        elif dy_val >= t["good"]:
            details.append({"metric": "Dividend Yield", "value": f"{dy_pct:.1f}%", "status": "GOOD YIELD", "score": 0})
        elif dy_val >= t["low"]:
            details.append({"metric": "Dividend Yield", "value": f"{dy_pct:.1f}%", "status": "LOW YIELD", "score": 0})
        elif dy_val > 0:
            details.append({"metric": "Dividend Yield", "value": f"{dy_pct:.1f}%", "status": "MINIMAL", "score": 0})
        else:
            details.append({"metric": "Dividend Yield", "value": "0%", "status": "NO DIVIDEND", "score": 0})
    else:
        details.append({"metric": "Dividend Yield", "value": "N/A", "status": "NO DATA", "score": 0})

    if is_valid_number(payout_ratio):
        pr_val = float(payout_ratio) * 100
        if pr_val > 80:
            details.append({"metric": "Payout Ratio", "value": f"{pr_val:.1f}%", "status": "HIGH — may not be sustainable", "score": 0})
        elif pr_val > 50:
            details.append({"metric": "Payout Ratio", "value": f"{pr_val:.1f}%", "status": "MODERATE", "score": 0})
        elif pr_val > 0:
            details.append({"metric": "Payout Ratio", "value": f"{pr_val:.1f}%", "status": "CONSERVATIVE — room to grow", "score": 0})

    return details


def calculate_dupont(roe, profit_margin, asset_turnover, equity_multiplier):
    """Calculate DuPont analysis components."""
    details = []

    if not all(is_valid_number(x) for x in [roe, profit_margin, asset_turnover, equity_multiplier]):
        return 0, details

    pm = float(profit_margin)
    at = float(asset_turnover)
    em = float(equity_multiplier)
    roe_calc = pm * at * em

    score = 0

    if pm > 0.15:
        details.append({"component": "Profit Margin", "value": f"{pm*100:.1f}%", "assessment": "STRONG"})
    elif pm > 0.08:
        details.append({"component": "Profit Margin", "value": f"{pm*100:.1f}%", "assessment": "AVERAGE"})
    else:
        details.append({"component": "Profit Margin", "value": f"{pm*100:.1f}%", "assessment": "WEAK"})

    if at > 1.0:
        details.append({"component": "Asset Turnover", "value": f"{at:.2f}x", "assessment": "EFFICIENT"})
    elif at > 0.5:
        details.append({"component": "Asset Turnover", "value": f"{at:.2f}x", "assessment": "AVERAGE"})
    else:
        details.append({"component": "Asset Turnover", "value": f"{at:.2f}x", "assessment": "INEFFICIENT"})

    if em > 3.0:
        score -= 1
        details.append({"component": "Equity Multiplier", "value": f"{em:.2f}x", "assessment": "HIGH LEVERAGE"})
    elif em > 2.0:
        details.append({"component": "Equity Multiplier", "value": f"{em:.2f}x", "assessment": "MODERATE LEVERAGE"})
    else:
        score += 1
        details.append({"component": "Equity Multiplier", "value": f"{em:.2f}x", "assessment": "LOW LEVERAGE"})

    if is_valid_number(roe):
        roe_diff = abs(float(roe) - roe_calc)
        if roe_diff > 0.05:
            details.append({"component": "Calculation Match", "value": "MISMATCH", "assessment": "Check data quality"})

    return score, details


# ============================================================
# PIOTROSKI F-SCORE (0-9)
# ============================================================

def calculate_piotroski(stock_info, prev_stock_info=None):
    """
    Calculate Piotroski F-Score — 9-point financial strength indicator.
    Score 8-9: Very Strong | 6-7: Strong | 4-5: Average | 0-3: Weak
    """
    score = 0
    details = []

    roe = safe_float(stock_info.get("roe"))
    profit_margin = safe_float(stock_info.get("profit_margin"))
    debt_equity = safe_float(stock_info.get("debt_to_equity"))
    current_ratio = safe_float(stock_info.get("current_ratio"))
    gross_margin = safe_float(stock_info.get("gross_margin"))
    asset_turnover = safe_float(stock_info.get("asset_turnover"))
    market_cap = safe_float(stock_info.get("market_cap"))
    total_assets = safe_float(stock_info.get("total_assets"))
    total_debt = safe_float(stock_info.get("total_debt"))
    revenue = safe_float(stock_info.get("revenue"))
    net_profit = safe_float(stock_info.get("net_profit"))
    operating_cashflow = safe_float(stock_info.get("operating_cashflow"))
    shares_outstanding = safe_float(stock_info.get("shares_outstanding"))
    prev_shares = safe_float(prev_stock_info.get("shares_outstanding")) if prev_stock_info else None

    # 1. Positive Net Income
    if net_profit is not None and net_profit > 0:
        score += 1
        details.append({"indicator": "Positive Net Income", "value": "YES", "score": 1})
    else:
        details.append({"indicator": "Positive Net Income", "value": "NO", "score": 0})

    # 2. Positive Operating Cash Flow
    if operating_cashflow is not None and operating_cashflow > 0:
        score += 1
        details.append({"indicator": "Positive CFO", "value": "YES", "score": 1})
    elif net_profit is not None and net_profit > 0:
        details.append({"indicator": "Positive CFO", "value": "ESTIMATED YES", "score": 0})
    else:
        details.append({"indicator": "Positive CFO", "value": "NO", "score": 0})

    # 3. ROA Positive (using ROE as proxy if ROA not available)
    roa = safe_float(stock_info.get("roa"))
    if roa is not None:
        roa_positive = roa > 0
    elif roe is not None:
        roa_positive = roe > 0
    else:
        roa_positive = net_profit is not None and net_profit > 0

    if roa_positive:
        score += 1
        details.append({"indicator": "Positive ROA", "value": "YES", "score": 1})
    else:
        details.append({"indicator": "Positive ROA", "value": "NO", "score": 0})

    # 4. CFO > Net Income (earnings quality)
    if operating_cashflow is not None and net_profit is not None and net_profit > 0:
        if operating_cashflow > net_profit:
            score += 1
            details.append({"indicator": "CFO > Net Income", "value": "YES", "score": 1})
        else:
            details.append({"indicator": "CFO > Net Income", "value": "NO", "score": 0})
    else:
        details.append({"indicator": "CFO > Net Income", "value": "N/A", "score": 0})

    # 5. Decreasing Debt Ratio (lower is better)
    if debt_equity is not None:
        if debt_equity < 100:
            score += 1
            details.append({"indicator": "Low Debt Ratio", "value": f"{debt_equity:.1f}%", "score": 1})
        else:
            details.append({"indicator": "Low Debt Ratio", "value": f"{debt_equity:.1f}%", "score": 0})
    else:
        details.append({"indicator": "Low Debt Ratio", "value": "N/A", "score": 0})

    # 6. Increasing Current Ratio (liquidity improving)
    if current_ratio is not None:
        if current_ratio > 1.5:
            score += 1
            details.append({"indicator": "Strong Current Ratio", "value": f"{current_ratio:.2f}", "score": 1})
        else:
            details.append({"indicator": "Strong Current Ratio", "value": f"{current_ratio:.2f}", "score": 0})
    else:
        details.append({"indicator": "Strong Current Ratio", "value": "N/A", "score": 0})

    # 7. No Share Dilution
    if prev_shares is not None and shares_outstanding is not None:
        if shares_outstanding <= prev_shares:
            score += 1
            details.append({"indicator": "No Dilution", "value": "YES", "score": 1})
        else:
            details.append({"indicator": "No Dilution", "value": "DILUTED", "score": 0})
    else:
        if shares_outstanding is not None:
            score += 1
            details.append({"indicator": "No Dilution", "value": "ASSUMED YES", "score": 1})
        else:
            details.append({"indicator": "No Dilution", "value": "N/A", "score": 0})

    # 8. Gross Margin Improving or High
    if gross_margin is not None:
        if gross_margin > 0.30:
            score += 1
            details.append({"indicator": "High Gross Margin", "value": f"{gross_margin*100:.1f}%", "score": 1})
        elif gross_margin > 0.15:
            score += 1
            details.append({"indicator": "Decent Gross Margin", "value": f"{gross_margin*100:.1f}%", "score": 1})
        else:
            details.append({"indicator": "Low Gross Margin", "value": f"{gross_margin*100:.1f}%", "score": 0})
    else:
        details.append({"indicator": "Gross Margin", "value": "N/A", "score": 0})

    # 9. Asset Turnover Improving or High
    if asset_turnover is not None:
        if asset_turnover > 0.8:
            score += 1
            details.append({"indicator": "High Asset Turnover", "value": f"{asset_turnover:.2f}x", "score": 1})
        elif asset_turnover > 0.5:
            score += 1
            details.append({"indicator": "Decent Asset Turnover", "value": f"{asset_turnover:.2f}x", "score": 1})
        else:
            details.append({"indicator": "Low Asset Turnover", "value": f"{asset_turnover:.2f}x", "score": 0})
    else:
        details.append({"indicator": "Asset Turnover", "value": "N/A", "score": 0})

    if score >= 8:
        assessment = "VERY STRONG — High quality, low bankruptcy risk"
        assessment_id = "SANGAT KUAT — Kualitas tinggi, risiko bangkrut rendah"
    elif score >= 6:
        assessment = "STRONG — Solid financials"
        assessment_id = "KUAT — Keuangan solid"
    elif score >= 4:
        assessment = "AVERAGE — Some concerns to monitor"
        assessment_id = "RATA-RATA — Beberapa catatan perlu diperhatikan"
    elif score >= 2:
        assessment = "WEAK — Significant financial issues"
        assessment_id = "LEMAH — Masalah keuangan signifikan"
    else:
        assessment = "VERY WEAK — High risk"
        assessment_id = "SANGAT LEMAH — Risiko tinggi"

    return {
        "score": score,
        "max_score": 9,
        "assessment": assessment,
        "assessment_id": assessment_id,
        "details": details,
    }


# ============================================================
# ALTMAN Z-SCORE (Bankruptcy Prediction)
# ============================================================

def calculate_altman_z(stock_info):
    """
    Calculate Altman Z-Score for bankruptcy prediction.
    Z > 2.99: Safe | 1.81-2.99: Grey Zone | < 1.81: Distress
    """
    details = []

    total_assets = safe_float(stock_info.get("total_assets"))
    total_debt = safe_float(stock_info.get("total_debt"))
    current_assets = safe_float(stock_info.get("current_assets"))
    current_liabilities = safe_float(stock_info.get("current_liabilities"))
    retained_earnings = safe_float(stock_info.get("retained_earnings"))
    ebit = safe_float(stock_info.get("ebit"))
    market_cap = safe_float(stock_info.get("market_cap"))
    revenue = safe_float(stock_info.get("revenue"))
    working_capital = safe_float(stock_info.get("working_capital"))

    if total_assets is None or total_assets <= 0:
        return {
            "score": None,
            "zone": "INSUFFICIENT DATA",
            "assessment": "Data tidak cukup untuk menghitung Z-Score",
            "details": [{"component": "Total Assets", "value": "N/A", "assessment": "REQUIRED DATA MISSING"}],
        }

    if working_capital is None and current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    if working_capital is not None and total_assets > 0:
        x1 = working_capital / total_assets
    else:
        x1 = 0
        details.append({"component": "X1: Working Capital/Assets", "value": "N/A", "assessment": "Estimated as 0"})

    if retained_earnings is not None and total_assets > 0:
        x2 = retained_earnings / total_assets
    else:
        x2 = 0
        details.append({"component": "X2: Retained Earnings/Assets", "value": "N/A", "assessment": "Estimated as 0"})

    if ebit is not None and total_assets > 0:
        x3 = ebit / total_assets
    elif net_profit := safe_float(stock_info.get("net_profit")):
        x3 = net_profit / total_assets
    else:
        x3 = 0
        details.append({"component": "X3: EBIT/Assets", "value": "N/A", "assessment": "Estimated as 0"})

    if market_cap is not None and total_debt is not None and total_debt > 0:
        x4 = market_cap / total_debt
    elif market_cap is not None and total_assets is not None:
        equity = total_assets - (total_debt or 0)
        if equity > 0:
            x4 = market_cap / equity
        else:
            x4 = 0
    else:
        x4 = 0
        details.append({"component": "X4: Market Cap/Debt", "value": "N/A", "assessment": "Estimated as 0"})

    if revenue is not None and total_assets > 0:
        x5 = revenue / total_assets
    else:
        x5 = 0
        details.append({"component": "X5: Sales/Assets", "value": "N/A", "assessment": "Estimated as 0"})

    z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    details = [
        {"component": "X1: Working Capital/Assets", "value": f"{x4:.4f}", "weight": "1.2x"},
        {"component": "X2: Retained Earnings/Assets", "value": f"{x2:.4f}", "weight": "1.4x"},
        {"component": "X3: EBIT/Assets", "value": f"{x3:.4f}", "weight": "3.3x"},
        {"component": "X4: Market Cap/Debt", "value": f"{x4:.4f}", "weight": "0.6x"},
        {"component": "X5: Sales/Assets", "value": f"{x5:.4f}", "weight": "1.0x"},
    ]

    if z_score > 2.99:
        zone = "SAFE"
        assessment = "Low bankruptcy risk — financial position strong"
        assessment_id = "Risiko bangkrut rendah — posisi keuangan kuat"
    elif z_score > 1.81:
        zone = "GREY"
        assessment = "Moderate risk — needs monitoring"
        assessment_id = "Risiko moderat — perlu dipantau"
    else:
        zone = "DISTRESS"
        assessment = "High bankruptcy risk — financial distress"
        assessment_id = "Risiko bangkrut tinggi — keuangan terganggu"

    return {
        "score": safe_round(z_score, 4),
        "zone": zone,
        "assessment": assessment,
        "assessment_id": assessment_id,
        "details": details,
    }


# ============================================================
# MAGIC FORMULA (Joel Greenblatt)
# ============================================================

def calculate_magic_formula(stock_info):
    """
    Calculate Magic Formula metrics: Earnings Yield and Return on Capital.
    Lower Magic Formula Rank = Better (1 = Best)
    """
    details = []

    ebit = safe_float(stock_info.get("ebit"))
    net_profit = safe_float(stock_info.get("net_profit"))
    market_cap = safe_float(stock_info.get("market_cap"))
    total_debt = safe_float(stock_info.get("total_debt"))
    total_assets = safe_float(stock_info.get("total_assets"))
    current_assets = safe_float(stock_info.get("current_assets"))
    current_liabilities = safe_float(stock_info.get("current_liabilities"))
    net_fixed_assets = safe_float(stock_info.get("net_fixed_assets"))
    cash = safe_float(stock_info.get("cash"))
    pe_ratio = safe_float(stock_info.get("pe_ratio"))
    pb_ratio = safe_float(stock_info.get("pb_ratio"))

    enterprise_value = None
    if market_cap is not None:
        ev = market_cap
        if total_debt is not None:
            ev += total_debt
        if cash is not None:
            ev -= cash
        enterprise_value = ev

    earnings_yield = None
    if ebit is not None and enterprise_value is not None and enterprise_value > 0:
        earnings_yield = ebit / enterprise_value
    elif pe_ratio is not None and pe_ratio > 0:
        earnings_yield = 1 / pe_ratio
    elif net_profit is not None and market_cap is not None and market_cap > 0:
        earnings_yield = net_profit / market_cap

    roc = None
    if ebit is not None and total_assets is not None:
        invested_capital = total_assets
        if current_liabilities is not None:
            invested_capital -= current_liabilities
        if cash is not None:
            invested_capital -= cash
        if invested_capital > 0:
            roc = ebit / invested_capital

    details.append({
        "metric": "Enterprise Value",
        "value": format_large_number(enterprise_value) if enterprise_value else "N/A",
        "status": "Market Cap + Debt - Cash",
    })

    if earnings_yield is not None:
        ey_pct = earnings_yield * 100
        if ey_pct > 15:
            assessment = "EXCELLENT — High earnings yield (value)"
            assessment_id = "EXCELLENT — Earnings yield tinggi (value)"
        elif ey_pct > 8:
            assessment = "GOOD — Reasonable earnings yield"
            assessment_id = "BAGUS — Earnings yield wajar"
        elif ey_pct > 4:
            assessment = "FAIR — Low earnings yield"
            assessment_id = "CUKUP — Earnings yield rendah"
        else:
            assessment = "POOR — Very low earnings yield (expensive)"
            assessment_id = "BURUK — Earnings yield sangat rendah (mahal)"
    else:
        assessment = "N/A"

    details.append({
        "metric": "Earnings Yield",
        "value": f"{ey_pct:.1f}%" if earnings_yield else "N/A",
        "status": assessment,
        "formula": "EBIT / Enterprise Value",
    })

    if roc is not None:
        roc_pct = roc * 100
        if roc_pct > 25:
            assessment_roc = "EXCELLENT — Very high return on capital"
            assessment_roc_id = "EXCELLENT — Return on capital sangat tinggi"
        elif roc_pct > 15:
            assessment_roc = "GOOD — High return on capital"
            assessment_roc_id = "BAGUS — Return on capital tinggi"
        elif roc_pct > 8:
            assessment_roc = "FAIR — Average return on capital"
            assessment_roc_id = "CUKUP — Return on capital rata-rata"
        else:
            assessment_roc = "POOR — Low return on capital"
            assessment_roc_id = "BURUK — Return on capital rendah"
    else:
        assessment_roc = "N/A"

    details.append({
        "metric": "Return on Capital (ROC)",
        "value": f"{roc_pct:.1f}%" if roc else "N/A",
        "status": assessment_roc,
        "formula": "EBIT / Invested Capital",
    })

    magic_rank = None
    if earnings_yield is not None and roc is not None:
        magic_score = (earnings_yield * 100) + (roc * 100)
        if magic_score > 40:
            magic_rank = "TOP TIER"
        elif magic_score > 25:
            magic_rank = "STRONG"
        elif magic_score > 15:
            magic_rank = "AVERAGE"
        else:
            magic_rank = "WEAK"
        details.append({
            "metric": "Magic Score",
            "value": f"{magic_score:.1f}",
            "status": magic_rank,
            "formula": "Earnings Yield + ROC",
        })
    else:
        details.append({
            "metric": "Magic Score",
            "value": "N/A",
            "status": "Insufficient data",
        })

    return {
        "earnings_yield": safe_round(earnings_yield * 100, 2) if earnings_yield else None,
        "roc": safe_round(roc * 100, 2) if roc else None,
        "magic_score": safe_round((earnings_yield * 100) + (roc * 100), 2) if earnings_yield and roc else None,
        "magic_rank": magic_rank,
        "enterprise_value": safe_round(enterprise_value, 0) if enterprise_value else None,
        "details": details,
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_fundamental(stock_info):
    if not stock_info:
        return {"error": "No data available"}

    pe = stock_info.get("pe_ratio")
    pb = stock_info.get("pb_ratio")
    roe = stock_info.get("roe")
    profit_margin = stock_info.get("profit_margin")
    gross_margin = stock_info.get("gross_margin")
    operating_margin = stock_info.get("operating_margin")
    debt_equity = stock_info.get("debt_to_equity")
    dividend_yield = stock_info.get("dividend_yield")
    market_cap = stock_info.get("market_cap", 0)
    sector = stock_info.get("sector")

    roa = stock_info.get("roa")
    revenue_growth = stock_info.get("revenue_growth")
    eps_growth = stock_info.get("eps_growth")
    current_ratio = stock_info.get("current_ratio")
    interest_coverage = stock_info.get("interest_coverage")
    payout_ratio = stock_info.get("payout_ratio")
    roe_trend = stock_info.get("roe_trend")

    asset_turnover = stock_info.get("asset_turnover")
    equity_multiplier = stock_info.get("equity_multiplier")

    thresholds = get_sector_thresholds(sector)

    valuation_score, valuation_details = score_valuation(pe, pb, thresholds)
    quality_score, quality_details = score_quality(roe, profit_margin, gross_margin, operating_margin, thresholds)
    health_score, health_details = score_health(debt_equity, current_ratio, interest_coverage, thresholds)
    growth_score, growth_details = score_growth(revenue_growth, eps_growth, roe_trend)
    dividend_details = score_dividend(dividend_yield, payout_ratio, thresholds)
    dupont_score, dupont_details = calculate_dupont(roe, profit_margin, asset_turnover, equity_multiplier)
    piotroski = calculate_piotroski(stock_info)
    altman_z = calculate_altman_z(stock_info)
    magic_formula = calculate_magic_formula(stock_info)

    total_score = valuation_score + quality_score + health_score + growth_score + dupont_score

    if total_score >= 8:
        recommendation = "STRONG BUY — High quality undervalued stock"
        recommendation_id = "BELI KUAT — Saham berkualitas tinggi yang undervalued"
    elif total_score >= 5:
        recommendation = "BUY — Good quality at fair price"
        recommendation_id = "BELI — Kualitas bagus di harga wajar"
    elif total_score >= 2:
        recommendation = "LEAN BUY — Decent value with some concerns"
        recommendation_id = "CENDERUNG BELI — Nilai cukup baik dengan beberapa catatan"
    elif total_score >= -1:
        recommendation = "HOLD — Fairly valued, monitor closely"
        recommendation_id = "TAHAN — Nilai wajar, pantau perkembangan"
    elif total_score >= -4:
        recommendation = "LEAN SELL — Overvalued or weak fundamentals"
        recommendation_id = "CENDERUNG JUAL — Overvalued atau fundamental lemah"
    elif total_score >= -7:
        recommendation = "SELL — Poor fundamentals or overvalued"
        recommendation_id = "JUAL — Fundamental lemah atau overvalued"
    else:
        recommendation = "STRONG SELL — Avoid"
        recommendation_id = "JUAL KUAT — Hindari"

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

    return {
        "symbol": stock_info.get("symbol"),
        "name": stock_info.get("name"),
        "sector": sector,
        "sector_description": thresholds.get("description", ""),
        "industry": stock_info.get("industry"),
        "market_cap": market_cap,
        "market_cap_category": market_cap_category,
        "revenue": stock_info.get("revenue"),
        "net_profit": stock_info.get("net_profit"),
        "valuation": {"score": valuation_score, "details": valuation_details},
        "quality": {"score": quality_score, "details": quality_details},
        "financial_health": {"score": health_score, "details": health_details},
        "growth": {"score": growth_score, "details": growth_details},
        "dupont": {"score": dupont_score, "details": dupont_details},
        "dividend": {"details": dividend_details},
        "piotroski": piotroski,
        "altman_z": altman_z,
        "magic_formula": magic_formula,
        "total_score": total_score,
        "recommendation": recommendation,
        "recommendation_id": recommendation_id,
        "report_info": {
            "period": stock_info.get("report_period"),
            "type": stock_info.get("report_type"),
            "source": stock_info.get("report_source"),
            "updated_at": stock_info.get("report_updated_at"),
            "available_periods": stock_info.get("available_periods"),
        },
    }
