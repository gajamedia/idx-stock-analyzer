import requests
import feedparser
import re

from datetime import datetime, timedelta


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

POSITIVE_WORDS = [
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
]

NEGATIVE_WORDS = [
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
]

NEGATION_WORDS = ["tidak", "bukan", "belum", "tanpa", "enggan", "tak"]


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
            news_items.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "CNBC Indonesia",
                "url": entry.get("link", ""),
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
            news_items.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "Kontan",
                "url": entry.get("link", ""),
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
            news_items.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "Bisnis.com",
                "url": entry.get("link", ""),
            })

    return news_items


def fetch_google_news_rss(symbol):
    """Fetch news from Google News RSS - works for ANY stock."""
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
            })

        return news_items
    except Exception as e:
        print(f"Error fetching Google News RSS for {symbol}: {e}")
        return []


def calculate_sentiment_score(text):
    if not text:
        return 0.5

    text_lower = text.lower()
    words = re.findall(r"\w+", text_lower)

    positive_count = 0
    negative_count = 0

    for i, word in enumerate(words):
        has_negation = False
        if i > 0:
            prev_words = words[max(0, i-3):i]
            for neg in NEGATION_WORDS:
                if neg in prev_words:
                    has_negation = True
                    break

        if word in POSITIVE_WORDS:
            if has_negation:
                negative_count += 1
            else:
                positive_count += 1
        elif word in NEGATIVE_WORDS:
            if has_negation:
                positive_count += 0.5
            else:
                negative_count += 1

    total = positive_count + negative_count
    if total == 0:
        return 0.5

    score = positive_count / total
    return round(score, 2)


def fetch_stock_news(symbol):
    """Fetch news for any stock - guaranteed to find news."""
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
            all_news.append({
                "title": entry.get("title", ""),
                "snippet": entry.get("summary", entry.get("description", ""))[:200],
                "source": "CNBC Indonesia",
                "url": entry.get("link", ""),
            })

    seen_titles = set()
    unique_news = []
    for item in all_news:
        title_key = item["title"][:50].lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_news.append(item)

    return unique_news[:10]


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
            "news": [],
        }

    scored_news = []
    for item in news:
        combined_text = f"{item['title']} {item['snippet']}"
        sentiment = calculate_sentiment_score(combined_text)

        if sentiment > 0.6:
            label = "POSITIVE"
        elif sentiment < 0.4:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        scored_news.append({
            "title": item["title"],
            "snippet": item["snippet"],
            "source": item["source"],
            "url": item.get("url", ""),
            "sentiment_score": sentiment,
            "sentiment_label": label,
        })

    title_scores = [calculate_sentiment_score(n["title"]) for n in news]
    avg_title_score = sum(title_scores) / len(title_scores) if title_scores else 0.5

    snippet_scores = [calculate_sentiment_score(n["snippet"]) for n in news]
    avg_snippet_score = sum(snippet_scores) / len(snippet_scores) if snippet_scores else 0.5

    avg_score = (avg_title_score * 0.6) + (avg_snippet_score * 0.4)

    if avg_score > 0.6:
        overall = "BULLISH"
    elif avg_score > 0.5:
        overall = "SLIGHTLY BULLISH"
    elif avg_score == 0.5:
        overall = "NEUTRAL"
    elif avg_score > 0.4:
        overall = "SLIGHTLY BEARISH"
    else:
        overall = "BEARISH"

    return {
        "symbol": symbol,
        "overall_sentiment": overall,
        "sentiment_score": round(avg_score, 2),
        "news_count": len(scored_news),
        "positive_count": sum(1 for n in scored_news if n["sentiment_label"] == "POSITIVE"),
        "negative_count": sum(1 for n in scored_news if n["sentiment_label"] == "NEGATIVE"),
        "neutral_count": sum(1 for n in scored_news if n["sentiment_label"] == "NEUTRAL"),
        "news": scored_news[:5],
    }
