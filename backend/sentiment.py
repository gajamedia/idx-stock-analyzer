import requests
import feedparser
import re
import math
from datetime import datetime, timedelta
from collections import defaultdict


STOCK_NAMES = {
    "BBCA": ["bank central asia", "bcasi"],
    "BBRI": ["bank rakyat indonesia"],
    "BMRI": ["bank mandiri"],
    "BBNI": ["bank negara indonesia"],
    "TLKM": ["telkom", "telkom indonesia"],
    "ASII": ["astra internasional", "astra"],
    "UNVR": ["unilever"],
    "HMSP": ["hutan masyur"],
    "GGRM": ["gudang garam"],
    "KLBF": ["kalbe farma"],
    "ICBP": ["indofood cbp"],
    "INDF": ["indofood"],
    "TBIG": ["tower bersama"],
    "TOWR": ["telkom infrastructure"],
    "EXCL": ["xl axiata"],
    "ISAT": ["indosat"],
    "SMGR": ["semen indonesia"],
    "INTP": ["semen indonesiaprime"],
    "ADRO": ["adaro"],
    "PTBA": ["bukit asam"],
    "ITMG": ["indonesia prima energy"],
    "MDKA": ["merdeka copper gold"],
    "EMAS": ["emas digital"],
    "BSDE": ["bsd city"],
    "CTRA": ["ciputra"],
    "SMRA": ["summarecon"],
    "PANI": ["pondok indah"],
    "ERAA": ["erajaya"],
    "GOTO": ["gojek tokopedia", "gojek", "tokopedia"],
    "BUKA": ["bukalapak"],
    "EMTK": ["emtek"],
    "MTEL": ["telkom metra"],
    "AMRT": ["sumber alfaria", "alfamart"],
    "ACES": ["ace hardware"],
    "MAPI": ["matahari"],
    "LPPF": ["lippo retail"],
    "RALS": ["ramayana"],
    "SIDO": ["sido muncul"],
    "BRPT": ["barito pacific"],
    "TPIA": ["chandra asri"],
    "INKP": ["indorama"],
    "BRMS": ["bumi resources"],
    "AGII": ["agincourt"],
    "DKHH": ["cipta sarana medika", "dkh hospitals"],
    "VKTR": ["vektor", "vktr teknologi mobilitas", "vktr mobilitas"],
}

SOURCE_CREDIBILITY = {
    "CNBC Indonesia": 1.0,
    "Kontan": 0.95,
    "Bisnis.com": 0.9,
    "Google News": 0.7,
    "Default": 0.5,
}

INTENSITY_WORDS = {
    # Strong Positive (weight +2.0)
    "surge": 2.0, "soar": 2.0, "skyrocket": 2.0, "melambung": 2.0,
    "melesat": 2.0, "meroket": 2.0, "moncer": 2.0, "cuan": 2.0,
    "jackpot": 2.0, "rekor": 2.0, "tertinggi": 2.0, "all-time high": 2.0,

    # Positive (weight +1.5)
    "rally": 1.5, "breakout": 1.5, "bullish": 1.5, "rebound": 1.5,
    "pulih": 1.5, "outperform": 1.5, "upgrade": 1.5, "superior": 1.5,
    "ekspansi": 1.5, "akuisisi": 1.5, "partnership": 1.5,
    "meningkat": 1.5, "positif": 1.5, "optimis": 1.5,
    "hijau": 1.5, "naik": 1.5,

    # Moderate Positive (weight +1.0)
    "profit": 1.0, "growth": 1.0, "gain": 1.0, "rise": 1.0,
    "laba": 1.0, "untung": 1.0, "surplus": 1.0,
    "kuat": 1.0, "solid": 1.0, "baik": 1.0, "sehat": 1.0,
    "robust": 1.0, "resilien": 1.0, "stabil": 1.0, "konsisten": 1.0,
    "dividen": 1.0, "berkembang": 1.0, "inovasi": 1.0,
    "transformasi": 1.0, "efisiensi": 1.0, "high": 1.0,
    "excellent": 1.0, "strong": 1.0, "target": 1.0,

    # Slight Positive (weight +0.5)
    "boom": 0.5, "potential": 0.5, "opportunity": 0.5,
    "prospek": 0.5, "peluang": 0.5, "permintaan": 0.5,

    # Strong Negative (weight -2.0)
    "crash": -2.0, "collapse": -2.0, "plunge": -2.0, "tank": -2.0,
    "kolaps": -2.0, "ambruk": -2.0, "bangkrut": -2.0,
    "default": -2.0, "fraud": -2.0, "korupsi": -2.0,
    "skandal": -2.0, "penipuan": -2.0, "manipulasi": -2.0,
    "likuidasi": -2.0, "resesi": -2.0,

    # Negative (weight -1.5)
    "bearish": -1.5, "breakdown": -1.5, "crash": -1.5,
    "anjlok": -1.5, "merosot": -1.5, "pesimis": -1.5,
    "krisis": -1.5, "gagal": -1.5, "inflasi": -1.5,
    "sanksi": -1.5, "denda": -1.5, "downgrade": -1.5,
    "underperform": -1.5, "jatuh": -1.5, "bocor": -1.5,
    "bubar": -1.5, "merah": -1.5, "suspend": -1.5,

    # Moderate Negative (weight -1.0)
    "turun": -1.0, "rugi": -1.0, "loss": -1.0, "deficit": -1.0,
    "penurunan": -1.0, "melemah": -1.0, "negatif": -1.0,
    "lemah": -1.0, "buruk": -1.0, "risiko": -1.0, "utang": -1.0,
    "drop": -1.0, "fall": -1.0, "slump": -1.0, "decline": -1.0,
    "low": -1.0, "terendah": -1.0, "bottom": -1.0,
    "phk": -1.0, "merumahkan": -1.0,

    # Slight Negative (weight -0.5)
    "tekanan": -0.5, "volatilitas": -0.5, "ketidakpastian": -0.5,
    "warning": -0.5, "peringatan": -0.5, "teguran": -0.5,
    "investigasi": -0.5, "pelanggaran": -0.5,
}

POSITIVE_WORDS = list(set([
    "naik", "untung", "laba", "profit", "growth", "surplus",
    "optimis", "rally", "breakout", "bullish", "rebound", "pulih",
    "meningkat", "positif", "kuat", "solid", "baik",
    "dividen", "ekspansi", "akuisisi", "partnership", "berkembang",
    "surge", "soar", "gain", "rise", "boom", "high", "outperform",
    "upgrade", "superior", "excellent", "strong",
    "cuan", "moncer", "melesat", "meroket", "hijau",
    "sehat", "robust", "resilien", "stabil", "konsisten",
    "inovasi", "transformasi", "digitalisasi", "efisiensi",
    "target", "rekor", "tertinggi",
    "prospek", "peluang", "permintaan", "potensi",
]))

NEGATIVE_WORDS = list(set([
    "turun", "rugi", "loss", "deficit", "penurunan", "melemah",
    "pesimis", "crash", "breakdown", "bearish", "jatuh", "anjlok",
    "merosot", "negatif", "lemah", "buruk", "krisis", "gagal",
    "resesi", "inflasi", "sanksi", "denda", "risiko", "utang",
    "drop", "fall", "plunge", "slump", "decline", "low", "underperform",
    "downgrade", "default", "bangkrut", "kolaps", "ambruk",
    "merah", "bocor", "bubar", "likuidasi",
    "penipuan", "fraud", "korupsi", "skandal", "manipulasi",
    "terendah", "bottom",
    "peringatan", "cecar", "dicecar",
    "tersangka", "investigasi", "pelanggaran", "penggelapan",
    "gugatan", "sengketa", "phk", "merumahkan",
    "teguran", "suspensi", "suspend", "banned",
    "tekanan", "volatilitas", "ketidakpastian",
]))

NEGATION_WORDS = ["tidak", "bukan", "belum", "tanpa", "enggan", "tak", "tanpa",
                   "belum", "jangan", "bukanlah", "tidaklah"]


def fetch_rss_feed(url, timeout=5):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        feed = feedparser.parse(response.text)
        return feed.entries
    except Exception as e:
        print(f"Error fetching RSS from {url}: {e}")
        return []


def fetch_cnbc_indonesia_news(symbol):
    entries = fetch_rss_feed("https://www.cnbcindonesia.com/news/rss")
    news_items = []

    for entry in entries[:30]:
        title = entry.get("title", "").lower()
        summary = entry.get("summary", entry.get("description", "")).lower()
        combined = f"{title} {summary}"

        company_names = STOCK_NAMES.get(symbol.upper(), [])
        is_match = symbol.upper() in combined

        if not is_match:
            for name in company_names:
                if name.lower() in combined:
                    is_match = True
                    break

        if is_match:
            published = entry.get("published", "")
            news_items.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "CNBC Indonesia",
                "url": entry.get("link", ""),
                "published": published,
                "published_dt": _parse_date(published),
            })

    return news_items


def fetch_kontan_news(symbol):
    entries = fetch_rss_feed("https://www.kontan.co.id/feed")
    news_items = []

    for entry in entries[:30]:
        title = entry.get("title", "").lower()
        summary = entry.get("summary", entry.get("description", "")).lower()
        combined = f"{title} {summary}"

        company_names = STOCK_NAMES.get(symbol.upper(), [])
        is_match = symbol.upper() in combined

        if not is_match:
            for name in company_names:
                if name.lower() in combined:
                    is_match = True
                    break

        if is_match:
            published = entry.get("published", "")
            news_items.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "Kontan",
                "url": entry.get("link", ""),
                "published": published,
                "published_dt": _parse_date(published),
            })

    return news_items


def fetch_bisnis_news(symbol):
    entries = fetch_rss_feed("https://rss.bisnis.com/")
    news_items = []

    for entry in entries[:30]:
        title = entry.get("title", "").lower()
        summary = entry.get("summary", entry.get("description", "")).lower()
        combined = f"{title} {summary}"

        company_names = STOCK_NAMES.get(symbol.upper(), [])
        is_match = symbol.upper() in combined

        if not is_match:
            for name in company_names:
                if name.lower() in combined:
                    is_match = True
                    break

        if is_match:
            published = entry.get("published", "")
            news_items.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "Bisnis.com",
                "url": entry.get("link", ""),
                "published": published,
                "published_dt": _parse_date(published),
            })

    return news_items


def fetch_google_news_rss(symbol):
    try:
        query = f"saham+{symbol}+IDX"
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=id&gl=ID&ceid=ID:id"
        entries = fetch_rss_feed(rss_url)
        news_items = []

        for entry in entries[:10]:
            title = entry.get("title", "")
            source = entry.get("source", {}).get("title", "Google News") if hasattr(entry.get("source", {}), "get") else "Google News"
            link = entry.get("link", "")
            published = entry.get("published", "")

            news_items.append({
                "title": title,
                "snippet": "",
                "source": source,
                "url": link,
                "published": published,
                "published_dt": _parse_date(published),
            })

        return news_items
    except Exception as e:
        print(f"Error fetching Google News RSS for {symbol}: {e}")
        return []


def _parse_date(date_str):
    """Parse various date formats from RSS feeds."""
    if not date_str:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y %H:%M:%S",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    return None


def _get_time_decay(published_dt):
    """Calculate time decay factor. Recent news has higher weight.
    - Today: 1.0
    - Yesterday: 0.85
    - 2-3 days: 0.7
    - 4-7 days: 0.5
    - 7-14 days: 0.3
    - >14 days: 0.1
    """
    if not published_dt:
        return 0.6

    now = datetime.now(published_dt.tzinfo) if published_dt.tzinfo else datetime.now()
    age = now - published_dt
    days = age.total_seconds() / 86400

    if days <= 1:
        return 1.0
    elif days <= 3:
        return 0.85
    elif days <= 7:
        return 0.7
    elif days <= 14:
        return 0.5
    elif days <= 30:
        return 0.3
    else:
        return 0.1


def _get_source_credibility(source_name):
    """Get credibility weight for news source."""
    return SOURCE_CREDIBILITY.get(source_name, SOURCE_CREDIBILITY["Default"])


def calculate_sentiment_score(text):
    """Calculate sentiment score with intensity and improved negation handling."""
    if not text:
        return 0.5

    text_lower = text.lower()
    words = re.findall(r"\w+", text_lower)
    text_len = len(words)

    if text_len == 0:
        return 0.5

    weighted_score = 0.0
    matched_count = 0

    for i, word in enumerate(words):
        has_negation = False
        if i > 0:
            prev_words = words[max(0, i - 4):i]
            for neg in NEGATION_WORDS:
                if neg in prev_words:
                    has_negation = True
                    break

        if word in INTENSITY_WORDS:
            intensity = INTENSITY_WORDS[word]
            if has_negation:
                weighted_score -= intensity * 0.7
            else:
                weighted_score += intensity
            matched_count += 1

        elif word in POSITIVE_WORDS:
            if has_negation:
                weighted_score -= 0.8
            else:
                weighted_score += 1.0
            matched_count += 1

        elif word in NEGATIVE_WORDS:
            if has_negation:
                weighted_score += 0.5
            else:
                weighted_score -= 1.0
            matched_count += 1

    if matched_count == 0:
        return 0.5

    max_possible = matched_count * 2.0
    normalized = (weighted_score + max_possible) / (2 * max_possible)
    normalized = max(0.0, min(1.0, normalized))

    return round(normalized, 3)


def _calculate_momentum(news_items):
    """Calculate sentiment momentum by comparing recent vs older news."""
    recent_scores = []
    older_scores = []

    for item in news_items:
        published_dt = item.get("published_dt")
        score = item.get("sentiment_score", 0.5)

        if published_dt:
            now = datetime.now(published_dt.tzinfo) if published_dt.tzinfo else datetime.now()
            age_days = (now - published_dt).total_seconds() / 86400

            if age_days <= 7:
                recent_scores.append(score)
            else:
                older_scores.append(score)

    if not recent_scores or not older_scores:
        return {
            "recent_avg": round(sum(recent_scores) / len(recent_scores), 3) if recent_scores else 0.5,
            "older_avg": round(sum(older_scores) / len(older_scores), 3) if older_scores else 0.5,
            "momentum": 0.0,
            "momentum_label": "INSUFFICIENT DATA",
        }

    recent_avg = sum(recent_scores) / len(recent_scores)
    older_avg = sum(older_scores) / len(older_scores)
    momentum = recent_avg - older_avg

    if momentum > 0.1:
        label = "IMPROVING"
    elif momentum > 0.03:
        label = "SLIGHTLY IMPROVING"
    elif momentum < -0.1:
        label = "DETERIORATING"
    elif momentum < -0.03:
        label = "SLIGHTLY DETERIORATING"
    else:
        label = "STABLE"

    return {
        "recent_avg": round(recent_avg, 3),
        "older_avg": round(older_avg, 3),
        "momentum": round(momentum, 3),
        "momentum_label": label,
    }


def _calculate_sentiment_distribution(news_items):
    """Calculate sentiment distribution with intensity levels."""
    distribution = {
        "very_positive": 0,
        "positive": 0,
        "slightly_positive": 0,
        "neutral": 0,
        "slightly_negative": 0,
        "negative": 0,
        "very_negative": 0,
    }

    for item in news_items:
        score = item.get("sentiment_score", 0.5)
        if score >= 0.75:
            distribution["very_positive"] += 1
        elif score >= 0.6:
            distribution["positive"] += 1
        elif score >= 0.55:
            distribution["slightly_positive"] += 1
        elif score <= 0.25:
            distribution["very_negative"] += 1
        elif score <= 0.4:
            distribution["negative"] += 1
        elif score <= 0.45:
            distribution["slightly_negative"] += 1
        else:
            distribution["neutral"] += 1

    return distribution


def fetch_stock_news(symbol):
    """Fetch news for any stock."""
    all_news = []

    google_news = fetch_google_news_rss(symbol)
    if google_news:
        all_news.extend(google_news)

    rss_news = []
    rss_news.extend(fetch_cnbc_indonesia_news(symbol))
    rss_news.extend(fetch_kontan_news(symbol))
    rss_news.extend(fetch_bisnis_news(symbol))

    if rss_news:
        all_news.extend(rss_news)

    if not all_news:
        general_entries = fetch_rss_feed("https://www.cnbcindonesia.com/news/rss")
        for entry in general_entries[:5]:
            published = entry.get("published", "")
            all_news.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "CNBC Indonesia",
                "url": entry.get("link", ""),
                "published": published,
                "published_dt": _parse_date(published),
            })

    seen_titles = set()
    unique_news = []
    for item in all_news:
        title_key = item["title"][:50].lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_news.append(item)

    return unique_news[:15]


def analyze_sentiment(symbol):
    news = fetch_stock_news(symbol)

    if not news:
        return {
            "symbol": symbol,
            "overall_sentiment": "NO DATA",
            "sentiment_score": 0.5,
            "news_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "momentum": _calculate_momentum([]),
            "distribution": {},
            "news": [],
        }

    scored_news = []
    for item in news:
        combined_text = f"{item['title']} {item['snippet']}"
        raw_sentiment = calculate_sentiment_score(combined_text)

        time_decay = _get_time_decay(item.get("published_dt"))
        source_cred = _get_source_credibility(item.get("source", "Default"))
        adjusted_score = raw_sentiment * time_decay * source_cred + 0.5 * (1 - time_decay * source_cred)

        adjusted_score = max(0.0, min(1.0, adjusted_score))

        if adjusted_score > 0.6:
            label = "POSITIVE"
        elif adjusted_score > 0.55:
            label = "SLIGHTLY POSITIVE"
        elif adjusted_score < 0.4:
            label = "NEGATIVE"
        elif adjusted_score < 0.45:
            label = "SLIGHTLY NEGATIVE"
        else:
            label = "NEUTRAL"

        scored_news.append({
            "title": item["title"],
            "snippet": item["snippet"],
            "source": item["source"],
            "url": item.get("url", ""),
            "published": item.get("published", ""),
            "raw_sentiment": round(raw_sentiment, 3),
            "time_decay": round(time_decay, 2),
            "source_credibility": source_cred,
            "sentiment_score": round(adjusted_score, 3),
            "sentiment_label": label,
        })

    total_weight = 0
    weighted_sum = 0
    for item in scored_news:
        time_decay = item["time_decay"]
        source_cred = item["source_credibility"]
        weight = time_decay * source_cred
        weighted_sum += item["sentiment_score"] * weight
        total_weight += weight

    avg_score = weighted_sum / total_weight if total_weight > 0 else 0.5

    if avg_score > 0.65:
        overall = "STRONGLY BULLISH"
    elif avg_score > 0.55:
        overall = "BULLISH"
    elif avg_score > 0.52:
        overall = "SLIGHTLY BULLISH"
    elif avg_score == 0.52:
        overall = "NEUTRAL"
    elif avg_score > 0.45:
        overall = "SLIGHTLY BEARISH"
    elif avg_score > 0.35:
        overall = "BEARISH"
    else:
        overall = "STRONGLY BEARISH"

    momentum = _calculate_momentum(scored_news)
    distribution = _calculate_sentiment_distribution(scored_news)

    return {
        "symbol": symbol,
        "overall_sentiment": overall,
        "sentiment_score": round(avg_score, 3),
        "news_count": len(scored_news),
        "positive_count": sum(1 for n in scored_news if "POSITIVE" in n["sentiment_label"]),
        "negative_count": sum(1 for n in scored_news if "NEGATIVE" in n["sentiment_label"]),
        "neutral_count": sum(1 for n in scored_news if n["sentiment_label"] == "NEUTRAL"),
        "momentum": momentum,
        "distribution": distribution,
        "avg_raw_sentiment": round(sum(n["raw_sentiment"] for n in scored_news) / len(scored_news), 3),
        "news": scored_news[:7],
    }
