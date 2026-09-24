import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from data_fetcher import fetch_stock_history, fetch_stock_info
from technical import analyze_stock
from fundamental import analyze_fundamental
from sentiment import analyze_sentiment
from horizon import analyze_horizon, horizon_label
from financial_updater import get_financial_data

LOT_SIZE = 100


def _financial_status(symbol):
    fin = get_financial_data(symbol)
    return {
        "exists": fin is not None,
        "period": fin.get("period") if fin else None,
    }

DISCLAIMER = (
    "Hasil konsultasi ini dihasilkan secara otomatis dari data teknikal, fundamental, "
    "sentimen, dan horizon analisis. Bukan nasihat keuangan. Keputusan investasi tetap "
    "kewajiban Anda dan sesuaikan dengan toleransi risiko pribadi."
)

DECISION_LABELS = {
    "CUT LOSS": "POTONG RUGI",
    "EXIT": "KELUAR (AMBIL POSISI)",
    "TRIM": "JUAL SEBAGIAN",
    "AVERAGE DOWN": "AVERAGE DOWN (BERTAHAP)",
    "HOLD": "TAHAN",
}

DECISION_COLORS = {
    "CUT LOSS": "bear",
    "EXIT": "bear",
    "TRIM": "warn",
    "AVERAGE DOWN": "info",
    "HOLD": "hold",
}

ENTRY_DECISION_LABELS = {
    "BUY_NOW": "BELI SEKARANG",
    "WAIT": "TUNGGU",
    "AVOID": "HINDARI",
}

ENTRY_DECISION_COLORS = {
    "BUY_NOW": "buy",
    "WAIT": "wait",
    "AVOID": "avoid",
}


def format_rp(value):
    if value is None:
        return "N/A"
    try:
        return "Rp {:,.0f}".format(float(value)).replace(",", ".")
    except (TypeError, ValueError):
        return "N/A"


def format_pct(value):
    if value is None:
        return "N/A"
    try:
        return "{:+.1f}%".format(float(value))
    except (TypeError, ValueError):
        return "N/A"


def compute_holding_metrics(lots, avg_price, current_price):
    shares = float(lots) * LOT_SIZE
    cost = shares * float(avg_price)
    market_value = shares * float(current_price) if current_price else 0.0
    pnl_abs = market_value - cost
    pnl_pct = (pnl_abs / cost * 100.0) if cost else 0.0
    return {
        "lots": float(lots),
        "shares": int(shares),
        "avg_price": float(avg_price),
        "current_price": current_price,
        "cost": round(cost, 2),
        "market_value": round(market_value, 2),
        "pnl_abs": round(pnl_abs, 2),
        "pnl_pct": round(pnl_pct, 2),
    }


def _extract_levels(technical, horizon):
    sr = technical.get("support_resistance", {}) if technical else {}
    support = sr.get("support")
    resistance = sr.get("resistance")

    price_targets = horizon.get("price_targets", {}) if horizon else {}
    stop_loss = price_targets.get("stop_loss")
    take_profit = price_targets.get("take_profit")
    entry_zone = price_targets.get("entry_zone", {}) if price_targets else {}

    hz_sr = horizon.get("support_resistance", {}) if horizon else {}
    if support is None:
        supports = hz_sr.get("support") or []
        supports = [s for s in supports if s]
        support = max(supports) if supports else None
    if resistance is None:
        resistances = hz_sr.get("resistance") or []
        resistances = [r for r in resistances if r]
        resistance = min(resistances) if resistances else None

    critical_support = support if support is not None else stop_loss
    if critical_support is None:
        critical_support = round(float(technical.get("current_price", 0)) * 0.95, 2) or None

    return {
        "support": support,
        "resistance": resistance,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "entry_zone_low": entry_zone.get("low"),
        "entry_zone_high": entry_zone.get("high"),
        "critical_support": critical_support,
    }


def _collect_votes(pnl_pct, levels, technical, fundamental, sentiment, horizon, horizon_error):
    bull = []
    bear = []

    tech_signal = (technical or {}).get("overall_signal") or "HOLD"
    rsi = (technical or {}).get("rsi")
    current_price = (technical or {}).get("current_price") or (horizon or {}).get("current_price")
    support = levels.get("critical_support")
    resistance = levels.get("resistance")

    if tech_signal in ("SELL", "STRONG SELL"):
        bear.append("Sinyal teknikal {} ({})".format(tech_signal, (technical or {}).get("market_regime", "N/A")))
    elif tech_signal in ("BUY", "STRONG BUY"):
        bull.append("Sinyal teknikal {} ({})".format(tech_signal, (technical or {}).get("market_regime", "N/A")))

    hz_score = None
    hz_rec = None
    if horizon_error is None and horizon:
        hz_score = horizon.get("score", 0)
        hz_rec = horizon.get("recommendation", "HOLD")
        hz_lbl = horizon.get("horizon", {}).get("label") or horizon_label(horizon.get("horizon", {}).get("months", 3))
        if hz_score <= -7 or hz_rec in ("SELL", "STRONG SELL"):
            bear.append("Horizon {}: {} (skor {:+.0f})".format(hz_lbl, hz_rec, hz_score or 0))
        elif hz_score >= 5 or hz_rec in ("BUY", "STRONG BUY"):
            bull.append("Horizon {}: {} (skor {:+.0f})".format(hz_lbl, hz_rec, hz_score or 0))

    fund_score = (fundamental or {}).get("total_score", 0) or 0
    if fund_score <= -4:
        bear.append("Fundamental lemah (skor {:+.0f}: {})".format(
            fund_score, (fundamental or {}).get("recommendation_id", "").split("—")[0].strip()))
    elif fund_score >= 5:
        bull.append("Fundamental kuat (skor {:+.0f}: {})".format(
            fund_score, (fundamental or {}).get("recommendation_id", "").split("—")[0].strip()))

    news_count = (sentiment or {}).get("news_count", 0)
    sent_label = (sentiment or {}).get("overall_sentiment", "NO DATA")
    sent_score = (sentiment or {}).get("sentiment_score", 0.5)
    if news_count > 0 and sent_label != "NO DATA":
        if sent_score <= 0.45:
            bear.append("Sentimen berita {} (skor {:.2f}, {} berita)".format(sent_label, sent_score, news_count))
        elif sent_score >= 0.55:
            bull.append("Sentimen berita {} (skor {:.2f}, {} berita)".format(sent_label, sent_score, news_count))

    if support is not None and current_price and current_price < support:
        bear.append("Harga {} di bawah support kritis {}".format(format_rp(current_price), format_rp(support)))

    if rsi is not None:
        if rsi <= 30 and (support is None or not current_price or current_price >= support):
            bull.append("RSI oversold ({:.1f}) di atas support".format(rsi))
        elif rsi >= 70:
            bear.append("RSI overbought ({:.1f})".format(rsi))

    near_resistance = False
    if resistance and current_price:
        near_resistance = current_price >= resistance * 0.97

    above_support = support is None or current_price is None or current_price >= support

    return {
        "bull": bull,
        "bear": bear,
        "tech_signal": tech_signal,
        "rsi": rsi,
        "current_price": current_price,
        "fund_score": fund_score,
        "hz_score": hz_score,
        "hz_rec": hz_rec,
        "near_resistance": near_resistance,
        "above_support": above_support,
        "sent_label": sent_label,
        "sent_score": sent_score,
        "news_count": news_count,
    }


def decide_position_action(pnl_pct, votes, levels):
    bull = votes["bull"]
    bear = votes["bear"]
    rsi = votes["rsi"]
    current_price = votes["current_price"]
    resistance = levels.get("resistance")
    take_profit = levels.get("take_profit")

    if len(bear) >= 3 and pnl_pct < -2:
        decision = "CUT LOSS"
        reason = "Kombinasi sinyal melemah ({}). Posisi rugi mengambang {} dan konfirmasi bearish kuat — lebih baik keluar sebelum kerugian membesar.".format(
            "; ".join(bear[:3]), format_pct(pnl_pct))
    elif len(bear) >= 3:
        decision = "EXIT"
        reason = "Sinyal melemah di beberapa sisi ({}) meski posisi masih {} — amankan posisi dengan keluar.".format(
            "; ".join(bear[:3]), format_pct(pnl_pct))
    elif pnl_pct > 0 and (rsi is not None and rsi >= 70 or votes["near_resistance"] or len(bear) >= 2):
        triggers = []
        if rsi is not None and rsi >= 70:
            triggers.append("RSI overbought {:.1f}".format(rsi))
        if votes["near_resistance"] and resistance:
            triggers.append("harga di dekat resistance {}".format(format_rp(resistance)))
        if len(bear) >= 2:
            triggers.append("mulai ada sinyal penguat ({})".format("; ".join(bear[:2])))
        decision = "TRIM"
        reason = "Posisi menguntungkan {} dengan pemicu: {}. Ambil sebagian untuk mengunci profit.".format(
            format_pct(pnl_pct), ", ".join(triggers))
    elif pnl_pct <= -5 and len(bull) >= 2 and len(bear) <= 1 and votes["above_support"]:
        decision = "AVERAGE DOWN"
        reason = "Rugi mengambang {} namun ada landasan kuat ({}). Average down boleh dilakukan bertahap selama support bertahan.".format(
            format_pct(pnl_pct), "; ".join(bull[:3]))
    else:
        decision = "HOLD"
        if bull and bear:
            reason = "Sinyal campuran (positif: {}; negatif: {}). Belum ada keunggulan yang jelas — tahan posisi dan pantau level kunci.".format(
                "; ".join(bull[:2]) or "-", "; ".join(bear[:2]) or "-")
        elif bull:
            reason = "Kondisi masih mendukung ({}). Tahan posisi dan ikuti rencana level di bawah.".format("; ".join(bull[:2]))
        elif bear:
            reason = "Ada tekanan ({}) tetapi belum cukup kuat untuk memaksa keluar. Tahan dengan disiplin stop.".format("; ".join(bear[:2]))
        else:
            reason = "Tidak ada sinyal kuat dari sisi mana pun. Tahan posisi, pantau support {} dan resistance {}.".format(
                format_rp(levels.get("critical_support")), format_rp(resistance))

    return decision, reason


def generate_action_steps(decision, metrics, votes, levels, horizon):
    lots = int(metrics["lots"]) if metrics["lots"].is_integer() else metrics["lots"]
    shares = metrics["shares"]
    avg = metrics["avg_price"]
    current = metrics["current_price"] or 0
    pnl_pct = metrics["pnl_pct"]
    support = levels.get("critical_support")
    resistance = levels.get("resistance")
    stop_loss = levels.get("stop_loss")
    take_profit = levels.get("take_profit")
    entry_low = levels.get("entry_zone_low")
    rsi = votes.get("rsi")
    hz_label = horizon.get("horizon", {}).get("label") if horizon else None

    steps = []

    if decision == "CUT LOSS":
        steps.append(
            "Keluarkan seluruh posisi {} lot ({} lembar) — rencana POTONG RUGI karena kerugian mengambang {} dengan konfirmasi sinyal melemah.".format(
                lots, shares, format_pct(pnl_pct)))
        if resistance and current and current < resistance:
            steps.append(
                "Bila masih mungkin, jual pada bounce terdekat menuju {} (resistance); jika tidak tersentuh, eksekusi di harga pasar — jangan tunggu balik modal.".format(
                    format_rp(resistance)))
        else:
            steps.append("Eksekusi di harga pasar pada saat likuid, tanpa menunda.")
        if support:
            steps.append(
                "Hard stop psikologis {}: jika harga sempat pulih lalu kembali break {} dengan volume, jangan tahan kembali.".format(
                    format_rp(support), format_rp(support)))
        steps.append(
            "Setelah keluar, tunggu konfirmasi reversal sebelum masuk kembali (mis. RSI kembali di atas 40 dan harga {} di atas resistance terdekat).".format(
                "close"))
    elif decision == "EXIT":
        steps.append(
            "Ambil seluruh posisi {} lot ({} lembar) untuk mengunci profit/loss mengambang {} — beberapa sinyal sudah mulai melemah.".format(
                lots, shares, format_pct(pnl_pct)))
        target_zone = None
        if resistance and take_profit:
            target_zone = min(resistance, take_profit)
        elif resistance:
            target_zone = resistance
        elif take_profit:
            target_zone = take_profit
        if target_zone and current and current < target_zone:
            steps.append("Pasang limit order bertahap di area {} — jika tidak tereksekusi dalam 1–2 sesi, lepas di pasar.".format(format_rp(target_zone)))
        else:
            steps.append("Eksekusi di harga pasar sesegera mungkin.")
        steps.append("Simpan hasil penjualan sebagai cash; re-entry hanya dengan sinyal beli baru yang terkonfirmasi.")
    elif decision == "TRIM":
        trim_lots = max(1, int(round(lots / 3.0)))
        if trim_lots >= lots:
            trim_lots = max(1, lots // 2)
        remain_lots = lots - trim_lots
        steps.append(
            "Jual sebagian: {} lot (dari total {} lot, {} lembar) untuk mengunci profit {}.".format(
                trim_lots, lots, trim_lots * LOT_SIZE, format_pct(pnl_pct)))
        if resistance:
            steps.append("Sisa {} lot: lepas bertahap jika harga mendekati/menetap di atas resistance {}.".format(remain_lots, format_rp(resistance)))
        trail_level = stop_loss or (support if support else round(current * 0.93, 2))
        steps.append("Untuk sisa posisi, jaga level keluar di {} — jika break dengan volume, habiskan sisanya.".format(format_rp(trail_level)))
        if rsi is not None and rsi >= 70:
            steps.append("RSI saat ini {:.1f} (overbought) — hindari menambah posisi sampai kembali di bawah 70.".format(rsi))
    elif decision == "AVERAGE DOWN":
        max_add = max(1, lots)
        steps.append(
            "Jangan menambah di harga sembarangan — tunggu di zona support {} s.d. {} (RSI mulai stabil di bawah 40).".format(
                format_rp(entry_low if entry_low else support), format_rp(support)))
        steps.append(
            "Bila syarat terpenuhi, tambah maksimal {} lot ({} lembar) sehingga total maksimal {} lot — bertahap, bukan sekaligus.".format(
                max_add, max_add * LOT_SIZE, lots + max_add))
        if support:
            critical = round(support * 0.97, 2)
            steps.append(
                "Batalkan rencana average down jika close di bawah {} (break support {}). Evaluasi ulang: kondisi berubah, bukan saatnya menambah.".format(
                    format_rp(critical), format_rp(support)))
        if resistance:
            steps.append(
                "Setelah tambahan tereksekusi, prioritaskan trim kembali di area {} untuk menekan bobot posisi.".format(
                    format_rp(resistance)))
        steps.append("Evaluasi ulang mengikuti horizon investasi Anda{}.".format(" ({})".format(hz_label) if hz_label else ""))
    else:
        steps.append(
            "Tahan posisi {} lot ({} lembar) dengan average {} — tidak perlu menambah maupun mengurangi saat ini.".format(
                lots, shares, format_rp(avg)))
        if support:
            steps.append("Pantau support kritis {}: jika close di bawah level tersebut dengan volume, pertimbangkan potong rugi.".format(format_rp(support)))
        exit_level = take_profit or resistance
        if exit_level:
            steps.append("Target ambil untung/trim berikutnya di area {} — jual sebagian bila tersentuh.".format(format_rp(exit_level)))
        if rsi is not None:
            steps.append("RSI terkini {:.1f} — tidak ada tekanan beli/jual ekstrem, biarkan posisi berjalan.".format(rsi))
        steps.append("Evaluasi ulang setelah rilis laporan keuangan berikutnya{}.".format(
            " atau dalam horizon {}".format(hz_label) if hz_label else ""))

    return steps


def generate_risk_notes(metrics, votes, levels, fundamental, sentiment, horizon_error):
    notes = []
    if votes["fund_score"] == 0 and not (fundamental or {}).get("market_cap"):
        notes.append("Data fundamental terbatas untuk emiten ini — keputusan lebih bertumpu pada teknikal dan horizon.")
    if votes["news_count"] == 0:
        notes.append("Tidak ada berita terpantau untuk emiten ini — analisis sentimen tidak signifikan.")
    if horizon_error:
        notes.append("Analisis horizon tidak dapat dihitung ({}).".format(horizon_error))
    if levels.get("critical_support") is None:
        notes.append("Support kritis tidak terdeteksi otomatis — gunakan level psikologis/ATR sebagai panduan.")
    if metrics is None:
        return notes
    if metrics["pnl_pct"] <= -20:
        notes.append("Kerugian mengambang {} sudah dalam, hindari keputusan emosional dan ikuti langkah sistematis.".format(format_pct(metrics["pnl_pct"])))
    if metrics["pnl_pct"] >= 30:
        notes.append("Profit mengambang {} cukup besar — pertimbangkan amankan modal (trim) bila sinyal mulai melemah.".format(format_pct(metrics["pnl_pct"])))
    return notes


def run_full_analysis(symbol, horizon_months=3, benchmark_data=None):
    symbol = symbol.upper()

    history = fetch_stock_history(symbol, period="1y")
    if not history:
        return {"symbol": symbol, "error": "Data harga tidak ditemukan untuk {}".format(symbol)}

    stock_info = fetch_stock_info(symbol)
    fundamental = analyze_fundamental(stock_info)
    sentiment = analyze_sentiment(symbol)
    technical = analyze_stock(history)

    horizon = analyze_horizon(
        daily_data=history,
        stock_info=stock_info,
        horizon_months=horizon_months,
        sentiment_data=sentiment,
        fundamental_data=fundamental,
        benchmark_data=benchmark_data,
    )
    horizon_error = None
    if isinstance(horizon, dict) and horizon.get("error"):
        horizon_error = horizon.get("error")
        horizon = None

    current_price = technical.get("current_price") or history[-1].get("Close")
    if not current_price:
        return {"symbol": symbol, "error": "Harga terkini tidak tersedia untuk {}".format(symbol)}

    company_name = None
    if technical.get("company_name"):
        company_name = technical.get("company_name")
    elif stock_info:
        company_name = stock_info.get("name")
    elif horizon:
        company_name = horizon.get("company_name")

    return {
        "symbol": symbol,
        "company_name": company_name,
        "stock_info": stock_info,
        "fundamental": fundamental,
        "sentiment": sentiment,
        "technical": technical,
        "horizon": horizon,
        "horizon_error": horizon_error,
        "current_price": current_price,
    }


def _analysis_payload(votes, fundamental, sentiment, horizon, horizon_error, horizon_months):
    hz_action_plan = []
    hz_rationale = None
    position_sizing = None
    if horizon:
        detailed = horizon.get("detailed_analysis") or {}
        hz_action_plan = detailed.get("action_plan") or []
        hz_rationale = horizon.get("rationale")
        position_sizing = horizon.get("position_sizing")

    return {
        "technical": {
            "signal": votes["tech_signal"],
            "rsi": votes["rsi"],
            "market_regime": (votes.get("technical") or {}).get("market_regime"),
            "trend": (votes.get("technical") or {}).get("trend"),
            "setup": (votes.get("technical") or {}).get("setup"),
            "confidence": (votes.get("technical") or {}).get("confidence"),
            "score": ((votes.get("technical") or {}).get("score") or {}).get("normalized"),
        },
        "fundamental": {
            "total_score": fundamental.get("total_score"),
            "recommendation": fundamental.get("recommendation"),
            "recommendation_id": fundamental.get("recommendation_id"),
            "sector": fundamental.get("sector"),
        },
        "sentiment": {
            "overall_sentiment": votes["sent_label"],
            "sentiment_score": votes["sent_score"],
            "news_count": votes["news_count"],
            "momentum": (sentiment.get("momentum") or {}).get("momentum") if sentiment else None,
        },
        "horizon": {
            "months": horizon_months,
            "label": horizon_label(horizon_months),
            "recommendation": horizon.get("recommendation") if horizon else None,
            "score": horizon.get("score") if horizon else None,
            "rationale": hz_rationale,
            "action_plan": hz_action_plan,
            "position_sizing": position_sizing,
            "error": horizon_error,
        },
    }


def analyze_holding(symbol, lots, avg_price, horizon_months=3, benchmark_data=None):
    bundle = run_full_analysis(symbol, horizon_months, benchmark_data=benchmark_data)
    if bundle.get("error"):
        return {"symbol": bundle["symbol"], "error": bundle["error"]}

    technical = bundle["technical"]
    fundamental = bundle["fundamental"]
    sentiment = bundle["sentiment"]
    horizon = bundle["horizon"]
    horizon_error = bundle["horizon_error"]
    current_price = bundle["current_price"]

    metrics = compute_holding_metrics(lots, avg_price, current_price)
    levels = _extract_levels(technical, horizon or {})
    votes = _collect_votes(metrics["pnl_pct"], levels, technical, fundamental, sentiment, horizon, horizon_error)
    votes["technical"] = technical
    decision, reason = decide_position_action(metrics["pnl_pct"], votes, levels)
    steps = generate_action_steps(decision, metrics, votes, levels, horizon or {})
    risk_notes = generate_risk_notes(metrics, votes, levels, fundamental, sentiment, horizon_error)

    return {
        "symbol": bundle["symbol"],
        "company_name": bundle["company_name"],
        "analysis_date": datetime.now().isoformat(),
        "holding": metrics,
        "decision": decision,
        "decision_label": DECISION_LABELS.get(decision, decision),
        "decision_color": DECISION_COLORS.get(decision, "hold"),
        "decision_reason": reason,
        "action_steps": steps,
        "decision_factors": {
            "bullish": votes["bull"],
            "bearish": votes["bear"],
        },
        "price_reference": {
            "avg_price": metrics["avg_price"],
            "current_price": metrics["current_price"],
            "support": levels.get("support"),
            "resistance": levels.get("resistance"),
            "critical_support": levels.get("critical_support"),
            "stop_loss": levels.get("stop_loss"),
            "take_profit": levels.get("take_profit"),
        },
        "analysis": _analysis_payload(votes, fundamental, sentiment, horizon, horizon_error, horizon_months),
        "risk_notes": risk_notes,
        "financial_data_status": _financial_status(symbol),
        "disclaimer": DISCLAIMER,
    }


def decide_entry_action(votes, levels):
    bull = votes["bull"]
    bear = votes["bear"]
    rsi = votes["rsi"]
    current_price = votes["current_price"]
    resistance = levels.get("resistance")
    support = levels.get("critical_support")
    stop_loss = levels.get("stop_loss")
    take_profit = levels.get("take_profit")

    if len(bear) >= 3 or (support is not None and current_price and current_price < support):
        decision = "AVOID"
        if len(bear) >= 3:
            reason = "Terlalu banyak sinyal melemah ({}){}. Belum layak dibeli — tunggu perubahan struktur harga.".format(
                "; ".join(bear[:3]),
                " dan harga di bawah support kritis {}".format(format_rp(support))
                if support is not None and current_price and current_price < support else "")
        else:
            reason = "Harga {} berada di bawah support kritis {} — risiko tinggi menangkap pisau jatuh. Tunggu harga kembali di atas support dengan konfirmasi.".format(
                format_rp(current_price), format_rp(support))
    elif votes["near_resistance"] or (rsi is not None and rsi >= 70):
        decision = "WAIT"
        triggers = []
        if rsi is not None and rsi >= 70:
            triggers.append("RSI overbought {:.1f}".format(rsi))
        if votes["near_resistance"] and resistance:
            triggers.append("harga di dekat resistance {}".format(format_rp(resistance)))
        reason = "Waktu masuk kurang ideal ({}) meski beberapa sinyal masih positif. Tunggu koreksi/reaksi di sekitar zona entry sebelum membeli.".format(
            ", ".join(triggers))
    elif len(bear) >= 2:
        decision = "WAIT"
        reason = "Sinyal masih berat ke bawah ({}) meski belum cukup ekstrem untuk menyatakan hindari total. Tunggu konfirmasi perbaikan dulu.".format(
            "; ".join(bear[:2]))
    elif len(bull) >= 3 or (len(bull) >= 2 and not bear):
        decision = "BUY_NOW"
        reason = "Kombinasi sinyal mendukung pembelian ({}) dengan harga masih di zona layak masuk — entry dapat dilakukan sekarang secara bertahap.".format(
            "; ".join(bull[:3]))
    elif len(bull) >= 1 and not bear:
        decision = "BUY_NOW"
        reason = "Sinyal positif terdeteksi ({}) tanpa tekanan berarti — layak mulai membangun posisi bertahap sesuai toleransi risiko.".format(
            "; ".join(bull[:2]))
    else:
        decision = "WAIT"
        if bull and bear:
            reason = "Sinyal campuran (positif: {}; negatif: {}). Belum ada keunggulan jelas — tunggu konfirmasi sebelum masuk.".format(
                "; ".join(bull[:2]) or "-", "; ".join(bear[:2]) or "-")
        else:
            level_hint = ""
            if support and resistance:
                level_hint = " Pantau support {} dan resistance {} sebagai pemicu keputusan.".format(
                    format_rp(support), format_rp(resistance))
            reason = "Belum ada sinyal beli yang cukup kuat dari sisi mana pun. Lebih aman menunggu setup yang lebih jelas.{}".format(level_hint)

    if decision == "BUY_NOW" and take_profit and resistance and current_price:
        rr_target = min(resistance, take_profit)
        if rr_target <= current_price:
            decision = "WAIT"
            reason = "Meski sinyal positif ({}), target terdekat {} tidak lebih tinggi dari harga sekarang {} — risk/reward jelek, tunggu koreksi atau breakout dulu.".format(
                "; ".join(bull[:2]) or "sinyal moderat", format_rp(rr_target), format_rp(current_price))

    return decision, reason


def generate_entry_steps(decision, votes, levels, horizon, capital, entry_plan, lots=None):
    current = votes["current_price"] or 0
    support = levels.get("critical_support")
    resistance = levels.get("resistance")
    stop_loss = levels.get("stop_loss")
    take_profit = levels.get("take_profit")
    entry_low = levels.get("entry_zone_low")
    entry_high = levels.get("entry_zone_high")
    rsi = votes.get("rsi")
    hz_label = horizon.get("horizon", {}).get("label") if horizon else None

    steps = []

    if decision == "BUY_NOW":
        tranche = entry_plan.get("lots_per_tranche")
        total_lots = entry_plan.get("suggested_lots")
        if total_lots and tranche:
            steps.append(
                "Bangun posisi bertahap: beli {} lot ({} lembar) terlebih dahulu dari total rencana {} lot — jangan all-in sekaligus.".format(
                    tranche, tranche * LOT_SIZE, total_lots))
        else:
            steps.append(
                "Mulai masuk bertahap (mis. 1/3–1/2 dari alokasi yang direncanakan) — jangan all-in di satu harga.")
        if entry_low and entry_high:
            steps.append(
                "Idealnya isi tranche pertama di zona entry {} s.d. {}; bila harga sudah jauh di atas zona itu, tunggu retrace singkat dulu.".format(
                    format_rp(entry_low), format_rp(entry_high)))
        else:
            steps.append("Isi tranche pertama di kisaran harga {} (harga pasar bila likuid, tunggu pullback bila spread/volatilitas tinggi).".format(format_rp(current)))
        if total_lots and tranche and total_lots > tranche:
            steps.append(
                "Sisa {} lot: tambahkan hanya setelah konfirmasi (close di atas resistance {} atau pullback bertahan di zona entry).".format(
                    total_lots - tranche, format_rp(resistance) if resistance else "terdekat"))
        if support:
            critical = stop_loss or support
            steps.append(
                "Pasang stop/invalidation di {} (support kritis {}). Jika close di bawah level itu, batalkan rencana beli/evaluasi ulang — jangan di average down membabi buta.".format(
                    format_rp(critical), format_rp(support)))
        if take_profit or resistance:
            target = min([t for t in [take_profit, resistance] if t]) if (take_profit and resistance) else (take_profit or resistance)
            steps.append(
                "Target keluar bertahap di area {} — ambil sebagian (trim) saat tersentuh, sisanya trailing dengan stop di bawah support.".format(
                    format_rp(target)))
        source = entry_plan.get("lots_source")
        if source == "input":
            short_txt = ""
            if entry_plan.get("capital_shortfall"):
                short_txt = " — modal kurang {} untuk rencana ini".format(format_rp(entry_plan.get("capital_shortfall")))
            steps.append(
                "Lot dari input: rencana {} lot ({} lembar) — modal {}{}.".format(
                    entry_plan.get("suggested_lots"),
                    (entry_plan.get("suggested_lots") or 0) * LOT_SIZE,
                    format_rp(capital) if capital else "belum diisi",
                    short_txt))
        elif source == "from_capital":
            if entry_plan.get("suggested_lots") == 0 and entry_plan.get("insufficient_for_min_lot"):
                steps.append(
                    "Modal {} belum cukup untuk 1 lot ({} per lot) — tambah modal minimal {} dulu sebelum mengejar emiten ini.".format(
                        format_rp(capital), format_rp(entry_plan.get("lot_cost")), format_rp(entry_plan.get("min_lot_shortfall") or entry_plan.get("lot_cost"))))
            elif entry_plan.get("suggested_lots"):
                steps.append(
                    "Modal {} cukup untuk ~{} lot (≈{}% modal; sisa untuk fee/buffer). Bila ingin porsi lebih kecil dari seluruh modal, isi jumlah lot manual.".format(
                        format_rp(capital),
                        entry_plan.get("suggested_lots"),
                        entry_plan.get("allocation_pct_of_capital")))
        elif source == "from_pct" and entry_plan.get("recommended_pct") is not None:
            if entry_plan.get("insufficient_for_min_lot"):
                lot_cost = entry_plan.get("lot_cost")
                if capital and lot_cost and capital < lot_cost:
                    steps.append(
                        "Modal {} belum cukup untuk 1 lot ({} per lot) — tambah modal minimal {} dulu sebelum mengejar emiten ini.".format(
                            format_rp(capital), format_rp(lot_cost), format_rp(entry_plan.get("min_lot_shortfall") or lot_cost)))
                else:
                    steps.append(
                        "Alokasi {}% dari modal tidak mencapai 1 lot ({}) — belum bisa eksekusi beli. Naikkan modal agar porsi aman masih muat 1 lot, atau lewati emiten ini.".format(
                            entry_plan.get("recommended_pct"), format_rp(entry_plan.get("lot_cost"))))
            elif capital and entry_plan.get("suggested_lots"):
                steps.append(
                    "Ukuran posisi maksimal ~{}% dari total modal (conviction: {}). Untuk modal {}, alokasi ≈ {} dan total rencana {} lot.".format(
                        entry_plan.get("recommended_pct"),
                        entry_plan.get("conviction", "N/A"),
                        format_rp(capital),
                        format_rp(entry_plan.get("allocation_rupiah")),
                        entry_plan.get("suggested_lots")))
            else:
                steps.append(
                    "Ukuran posisi maksimal ~{}% dari total modal (conviction: {}).{}".format(
                        entry_plan.get("recommended_pct"),
                        entry_plan.get("conviction", "N/A"),
                        " Isi lot atau modal untuk menghitung jumlah lot konkret." if not capital and not lots else ""))
        steps.append("Evaluasi ulang setelah rilis laporan keuangan berikutnya{}.".format(
            " atau dalam horizon {}".format(hz_label) if hz_label else ""))
    elif decision == "WAIT":
        steps.append("Jangan beli dulu di harga {} — tunggu setup yang lebih jelas.".format(format_rp(current)))
        if entry_low and entry_high:
            steps.append(
                "Siapkan rencana beli di zona entry {} s.d. {} — pasang alert/order di area tersebut, jangan kejar harga.".format(
                    format_rp(entry_low), format_rp(entry_high)))
        elif support:
            steps.append("Siapkan rencana beli saat harga mendekati/menguji ulang support {} dengan RSI yang sudah tidak overbought.".format(
                format_rp(support)))
        if rsi is not None and rsi >= 70:
            steps.append("Tunggu RSI turun di bawah 70 terlebih dahulu (saat ini {:.1f}) agar tidak membeli di puncak jangka pendek.".format(rsi))
        if resistance:
            steps.append("Alternatif trigger: konfirmasi close di atas {} dengan volume — baru masuk, meski harga sedikit lebih mahal.".format(
                format_rp(resistance)))
        steps.append("Batal-kan rencana beli bila muncul sinyal baru yang lebih kuat ke bawah (mis. break support {} dengan volume).".format(
            format_rp(support) if support else "kunci"))
        steps.append("Pantau kembali dalam horizon {} untuk keputusan lanjutan.".format(hz_label) if hz_label else "Pantau kembali secara berkala.")
    else:
        steps.append("Tidak disarankan membeli {} saat ini.".format(votes.get("symbol") or "emiten ini"))
        if support and current and current < support:
            steps.append("Harga masih di bawah support kritis {} — tunggu sampai kembali di atas level itu dan bertahan minimal beberapa sesi.".format(
                format_rp(support)))
        steps.append("Syarat evaluasi ulang untuk jadi calon beli: sinyal teknikal membaik ke BUY, fundamental tidak memburuk, dan harga kembali membentuk struktur higher-low.")
        if resistance:
            steps.append("Level yang harus ditembus lebih dulu: {} (diiringi volume) sebelum layak dipertimbangkan masuk.".format(format_rp(resistance)))
        steps.append("Alihkan perhatian ke emiten lain dengan setup lebih baik; jangan terikat pada satu saham yang sedang lemah.")
        steps.append("Evaluasi ulang setelah rilis laporan keuangan berikutnya{}.".format(
            " atau dalam horizon {}".format(hz_label) if hz_label else ""))

    return steps


def generate_entry_risk_notes(votes, levels, fundamental, sentiment, horizon_error, capital, lots=None):
    notes = generate_risk_notes(None, votes, levels, fundamental, sentiment, horizon_error)
    if capital is None and lots is None:
        notes.append("Modal dan lot tidak diisi — saran lot bersifat indikatif (% horizon saja). Isi lot atau modal untuk rencana konkret.")
    if votes["near_resistance"]:
        notes.append("Harga mendekati resistance — entry di harga sekarang menurunkan risk/reward; lebih sabar menunggu zona entry.")
    if votes["rsi"] is not None and votes["rsi"] >= 70:
        notes.append("RSI overbought — risiko koreksi jangka pendek meningkat bila memaksa masuk sekarang.")
    return notes


def compute_entry_allocation(capital, requested_lots, recommended_pct, ref_price):
    """Hitung alokasi dana & lot dengan prioritas: input LOT > MODAL > % horizon.

    - 1 lot = 100 lembar, biaya 1 lot = ref_price * 100.
    - requested_lots diisi → pakai lot itu langsung (lots_source="input").
    - hanya capital → lot = modal // biaya 1 lot (lots_source="from_capital").
    - keduanya kosong → pakai % conviction horizon (lots_source="from_pct").
    - Alokasi selalu kelipatan 1 lot; insufficient_for_min_lot bila tak muat 1 lot.
    """
    result = {
        "recommended_pct": recommended_pct,
        "lots_source": None,
        "lot_cost": None,
        "raw_allocation": None,
        "allocation_rupiah": None,
        "suggested_lots": None,
        "lots_per_tranche": None,
        "allocation_pct_of_capital": None,
        "one_lot_pct_of_capital": None,
        "min_lot_shortfall": None,
        "capital_shortfall": None,
        "insufficient_for_min_lot": False,
    }
    if not ref_price:
        return result

    lot_cost = round(float(ref_price) * LOT_SIZE, 2)
    result["lot_cost"] = lot_cost

    capital_f = float(capital) if capital else None
    if capital_f:
        result["one_lot_pct_of_capital"] = round(lot_cost / capital_f * 100.0, 2)

    if requested_lots is not None:
        total_lots = int(requested_lots)
        allocation = round(total_lots * lot_cost, 2)
        result["lots_source"] = "input"
        result["suggested_lots"] = total_lots
        result["lots_per_tranche"] = max(1, (total_lots + 1) // 2)
        result["allocation_rupiah"] = allocation
        if capital_f:
            result["allocation_pct_of_capital"] = round(allocation / capital_f * 100.0, 2)
            if allocation > capital_f:
                result["capital_shortfall"] = round(allocation - capital_f, 2)
        if capital_f is not None and capital_f < lot_cost:
            result["insufficient_for_min_lot"] = True
            result["min_lot_shortfall"] = round(lot_cost - capital_f, 2)
        return result

    if capital_f:
        result["lots_source"] = "from_capital"
        if capital_f < lot_cost:
            result["insufficient_for_min_lot"] = True
            result["min_lot_shortfall"] = round(lot_cost - capital_f, 2)
            result["allocation_rupiah"] = 0
            result["suggested_lots"] = 0
            result["lots_per_tranche"] = 0
            return result
        total_lots = int(capital_f // lot_cost)
        allocation = round(total_lots * lot_cost, 2)
        result["suggested_lots"] = total_lots
        result["lots_per_tranche"] = max(1, (total_lots + 1) // 2)
        result["allocation_rupiah"] = allocation
        result["allocation_pct_of_capital"] = round(allocation / capital_f * 100.0, 2)
        return result

    result["lots_source"] = "from_pct"
    if recommended_pct is None or capital_f is None:
        return result

    raw = capital_f * (float(recommended_pct) / 100.0)
    result["raw_allocation"] = round(raw, 2)
    if raw < lot_cost:
        result["insufficient_for_min_lot"] = True
        result["allocation_rupiah"] = 0
        result["suggested_lots"] = 0
        result["lots_per_tranche"] = 0
        return result

    total_lots = int(raw // lot_cost)
    allocation = round(total_lots * lot_cost, 2)
    result["allocation_rupiah"] = allocation
    result["suggested_lots"] = total_lots
    result["lots_per_tranche"] = max(1, (total_lots + 1) // 2)
    result["allocation_pct_of_capital"] = round(allocation / capital_f * 100.0, 2)
    return result


def _allocation_risk_notes(entry_plan, capital, decision):
    if decision == "AVOID" or not entry_plan.get("lot_cost"):
        return []
    notes = []
    lot_cost = entry_plan["lot_cost"]
    source = entry_plan.get("lots_source")

    if entry_plan.get("capital_shortfall"):
        notes.append(
            "Modal {} kurang untuk rencana {} lot (butuh {}) — tambah minimal {} atau kurangi jumlah lot.".format(
                format_rp(capital),
                entry_plan.get("suggested_lots"),
                format_rp(entry_plan.get("allocation_rupiah")),
                format_rp(entry_plan.get("capital_shortfall"))))

    if source == "input" and entry_plan.get("insufficient_for_min_lot") and capital and capital < lot_cost:
        notes.append(
            "Modal {} kurang untuk membeli 1 lot ({} per lot @ 100 lembar) — tambah minimal {} atau pilih emiten dengan harga per lembar lebih rendah.".format(
                format_rp(capital), format_rp(lot_cost), format_rp(entry_plan.get("min_lot_shortfall") or lot_cost)))
        return notes

    if source == "from_capital":
        if entry_plan.get("insufficient_for_min_lot") and capital and capital < lot_cost:
            notes.append(
                "Modal {} kurang untuk membeli 1 lot ({} per lot @ 100 lembar) — tambah minimal {} atau pilih emiten dengan harga per lembar lebih rendah.".format(
                    format_rp(capital), format_rp(lot_cost), format_rp(entry_plan.get("min_lot_shortfall") or lot_cost)))
        elif entry_plan.get("suggested_lots") == 0:
            notes.append("Modal tidak cukup untuk 1 lot pun pada harga referensi {}.".format(format_rp(lot_cost)))
        return notes

    if source == "from_pct" and entry_plan.get("insufficient_for_min_lot") and capital:
        raw = entry_plan.get("raw_allocation")
        one_lot_pct = entry_plan.get("one_lot_pct_of_capital")
        notes.append(
            "Saran alokasi {}% ({}) kurang dari harga 1 lot ({}) — tidak ada lot yang bisa dibeli. Modal cukup untuk 1 lot, tapi itu setara {}% dari modal (melebihi batas maksimum per saham {}). Tambah modal agar 1 lot tetap dalam porsi aman, atau abaikan emiten ini bila disiplin pada position sizing.".format(
                entry_plan.get("recommended_pct") if entry_plan.get("recommended_pct") is not None else "?",
                format_rp(raw) if raw is not None else "N/A",
                format_rp(lot_cost),
                one_lot_pct if one_lot_pct is not None else "?",
                "{}%".format(entry_plan.get("max_position_pct")) if entry_plan.get("max_position_pct") else "25%"))
    return notes


def analyze_entry(symbol, horizon_months=3, capital=None, lots=None, benchmark_data=None):
    bundle = run_full_analysis(symbol, horizon_months, benchmark_data=benchmark_data)
    if bundle.get("error"):
        return {"symbol": bundle["symbol"], "error": bundle["error"]}

    technical = bundle["technical"]
    fundamental = bundle["fundamental"]
    sentiment = bundle["sentiment"]
    horizon = bundle["horizon"]
    horizon_error = bundle["horizon_error"]
    current_price = bundle["current_price"]

    levels = _extract_levels(technical, horizon or {})
    votes = _collect_votes(0.0, levels, technical, fundamental, sentiment, horizon, horizon_error)
    votes["technical"] = technical
    votes["symbol"] = bundle["symbol"]
    decision, reason = decide_entry_action(votes, levels)

    position_sizing = None
    if horizon:
        position_sizing = horizon.get("position_sizing")
    alloc = (position_sizing or {}).get("recommended_allocation") or {}
    recommended_pct = alloc.get("recommended_pct")
    conviction = alloc.get("conviction_level")

    entry_plan = {
        "current_price": current_price,
        "entry_zone_low": levels.get("entry_zone_low"),
        "entry_zone_high": levels.get("entry_zone_high"),
        "stop_loss": levels.get("stop_loss") or levels.get("critical_support"),
        "take_profit": levels.get("take_profit"),
        "support": levels.get("support"),
        "resistance": levels.get("resistance"),
        "recommended_pct": recommended_pct,
        "conviction": conviction,
        "max_position_pct": (position_sizing or {}).get("recommended_allocation", {}).get("max_position_pct"),
        "kelly": (position_sizing or {}).get("kelly_criterion"),
        "allocation_rupiah": None,
        "suggested_lots": None,
        "lots_per_tranche": None,
        "lots_source": None,
        "capital_shortfall": None,
        "capital": capital,
        "requested_lots": lots,
    }

    ref_price = levels.get("entry_zone_low") or current_price
    if decision == "AVOID":
        entry_plan["recommended_pct"] = 0
        entry_plan["conviction"] = "NONE"
        entry_plan["suggested_lots"] = 0
        entry_plan["lots_per_tranche"] = 0
        entry_plan["allocation_rupiah"] = 0
        entry_plan["lots_source"] = "none"
        if ref_price:
            entry_plan["lot_cost"] = round(float(ref_price) * LOT_SIZE, 2)
    else:
        entry_plan.update(compute_entry_allocation(capital, lots, recommended_pct, ref_price))

    steps = generate_entry_steps(decision, votes, levels, horizon or {}, capital, entry_plan, lots)
    risk_notes = generate_entry_risk_notes(votes, levels, fundamental, sentiment, horizon_error, capital, lots)
    risk_notes.extend(_allocation_risk_notes(entry_plan, capital, decision))

    return {
        "symbol": bundle["symbol"],
        "company_name": bundle["company_name"],
        "analysis_date": datetime.now().isoformat(),
        "mode": "entry",
        "decision": decision,
        "decision_label": ENTRY_DECISION_LABELS.get(decision, decision),
        "decision_color": ENTRY_DECISION_COLORS.get(decision, "hold"),
        "decision_reason": reason,
        "action_steps": steps,
        "decision_factors": {
            "bullish": votes["bull"],
            "bearish": votes["bear"],
        },
        "entry_plan": entry_plan,
        "price_reference": {
            "current_price": current_price,
            "entry_zone_low": levels.get("entry_zone_low"),
            "entry_zone_high": levels.get("entry_zone_high"),
            "support": levels.get("support"),
            "resistance": levels.get("resistance"),
            "critical_support": levels.get("critical_support"),
            "stop_loss": levels.get("stop_loss"),
            "take_profit": levels.get("take_profit"),
        },
        "analysis": _analysis_payload(votes, fundamental, sentiment, horizon, horizon_error, horizon_months),
        "risk_notes": risk_notes,
        "financial_data_status": _financial_status(symbol),
        "disclaimer": DISCLAIMER,
    }


def analyze_entry_consultation(symbols, horizon_months=3, capital=None, lots=None):
    if not symbols:
        return {"error": "Minimal satu emiten harus diberikan."}

    benchmark_data = fetch_stock_history("^JKSE", period="1y")

    results = []
    seen = set()
    for raw in symbols:
        symbol = (raw or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        try:
            result = analyze_entry(symbol, horizon_months, capital=capital, lots=lots, benchmark_data=benchmark_data)
        except Exception as exc:
            result = {"symbol": symbol, "error": "Gagal menganalisis {}: {}".format(symbol, exc)}
        results.append(result)

    if not results:
        return {"error": "Tidak ada emiten valid pada input."}

    valid = [r for r in results if not r.get("error")]
    decisions_count = {}
    for r in valid:
        decisions_count[r["decision"]] = decisions_count.get(r["decision"], 0) + 1

    total_alloc = 0.0
    if capital:
        total_alloc = sum((r.get("entry_plan") or {}).get("allocation_rupiah") or 0 for r in valid)

    missing_fin = [
        r["symbol"] for r in valid
        if (r.get("financial_data_status") or {}).get("exists") is False
    ]

    return {
        "analysis_date": datetime.now().isoformat(),
        "mode": "entry",
        "horizon_months": horizon_months,
        "horizon_label": horizon_label(horizon_months),
        "capital": capital,
        "lots": lots,
        "results": results,
        "missing_financial_symbols": missing_fin,
        "summary": {
            "requested_count": len(results),
            "analyzed_count": len(valid),
            "decisions_count": decisions_count,
            "total_allocation": round(total_alloc, 2) if (capital or lots) else None,
        },
        "disclaimer": DISCLAIMER,
    }


def analyze_portfolio_consultation(holdings, horizon_months=3):
    if not holdings:
        return {"error": "Belum ada holdings. Tambahkan emiten terlebih dahulu."}

    benchmark_data = fetch_stock_history("^JKSE", period="1y")

    results = []
    for h in holdings:
        symbol = h.get("symbol")
        lots = h.get("lots")
        avg_price = h.get("avg_price")
        if not symbol or not lots or not avg_price:
            results.append({"symbol": symbol or "?", "error": "Data holding tidak lengkap (symbol/lots/avg_price)"})
            continue
        try:
            result = analyze_holding(symbol, lots, avg_price, horizon_months, benchmark_data=benchmark_data)
        except Exception as exc:
            result = {"symbol": symbol, "error": "Gagal menganalisis {}: {}".format(symbol, exc)}
        results.append(result)

    valid = [r for r in results if not r.get("error")]
    total_cost = sum(r["holding"]["cost"] for r in valid)
    total_mv = sum(r["holding"]["market_value"] for r in valid)
    total_pnl = total_mv - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100.0) if total_cost else 0.0

    weights = []
    for r in valid:
        w = (r["holding"]["market_value"] / total_mv * 100.0) if total_mv else 0.0
        r["holding"]["weight_pct"] = round(w, 2)
        weights.append({"symbol": r["symbol"], "weight_pct": round(w, 2)})

    weights.sort(key=lambda x: x["weight_pct"], reverse=True)
    decisions_count = {}
    for r in valid:
        decisions_count[r["decision"]] = decisions_count.get(r["decision"], 0) + 1

    missing_fin = [
        r["symbol"] for r in valid
        if (r.get("financial_data_status") or {}).get("exists") is False
    ]

    return {
        "analysis_date": datetime.now().isoformat(),
        "horizon_months": horizon_months,
        "horizon_label": horizon_label(horizon_months),
        "holdings": results,
        "missing_financial_symbols": missing_fin,
        "summary": {
            "holding_count": len(results),
            "analyzed_count": len(valid),
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_mv, 2),
            "total_pnl_abs": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "decisions_count": decisions_count,
            "largest_position": weights[0] if weights else None,
        },
        "disclaimer": DISCLAIMER,
    }
