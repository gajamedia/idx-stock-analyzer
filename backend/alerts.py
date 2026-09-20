from database import get_db
from datetime import datetime


def create_alert(symbol, alert_type, target_value):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO alerts (symbol, alert_type, target_value) VALUES (?, ?, ?)",
        (symbol.upper(), alert_type, target_value),
    )
    db.commit()
    alert_id = cursor.lastrowid
    db.close()
    return {"id": alert_id, "symbol": symbol.upper(), "alert_type": alert_type, "target_value": target_value, "status": "ACTIVE"}


def get_active_alerts(symbol=None):
    db = get_db()
    if symbol:
        rows = db.execute("SELECT * FROM alerts WHERE symbol = ? AND is_active = 1", (symbol.upper(),)).fetchall()
    else:
        rows = db.execute("SELECT * FROM alerts WHERE is_active = 1").fetchall()
    db.close()
    return [dict(row) for row in rows]


def check_alerts(current_prices):
    db = get_db()
    alerts = db.execute("SELECT * FROM alerts WHERE is_active = 1").fetchall()
    triggered = []

    for alert in alerts:
        symbol = alert["symbol"]
        if symbol not in current_prices:
            continue

        price = current_prices[symbol]
        alert_type = alert["alert_type"]
        target = alert["target_value"]

        should_trigger = False
        if alert_type == "PRICE_ABOVE" and price >= target:
            should_trigger = True
        elif alert_type == "PRICE_BELOW" and price <= target:
            should_trigger = True
        elif alert_type == "RSI_ABOVE" and price >= target:
            should_trigger = True
        elif alert_type == "RSI_BELOW" and price <= target:
            should_trigger = True

        if should_trigger:
            db.execute(
                "UPDATE alerts SET is_active = 0, triggered_at = ? WHERE id = ?",
                (datetime.now().isoformat(), alert["id"]),
            )
            triggered.append({
                "id": alert["id"],
                "symbol": symbol,
                "alert_type": alert_type,
                "target_value": target,
                "current_price": price,
                "triggered_at": datetime.now().isoformat(),
            })

    db.commit()
    db.close()
    return triggered


def delete_alert(alert_id):
    db = get_db()
    db.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    db.commit()
    db.close()
    return {"status": "deleted", "id": alert_id}


def get_triggered_alerts():
    db = get_db()
    rows = db.execute("SELECT * FROM alerts WHERE is_active = 0 AND triggered_at IS NOT NULL ORDER BY triggered_at DESC LIMIT 50").fetchall()
    db.close()
    return [dict(row) for row in rows]
