import threading
import time
from datetime import datetime
from data_fetcher import fetch_stock_history
from technical import analyze_stock
from database import get_db
from notifications import telegram_notifier, email_notifier


class BackgroundMonitor:
    def __init__(self):
        self.running = False
        self.thread = None
        self.interval = 60
        self.listeners = []
        self.last_prices = {}
        self.price_callbacks = []

    def add_listener(self, callback):
        self.listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def add_price_callback(self, callback):
        self.price_callbacks.append(callback)

    def _notify_listeners(self, event_type, data):
        for callback in self.listeners:
            try:
                callback(event_type, data)
            except Exception:
                pass

    def _notify_price_update(self, prices):
        for callback in self.price_callbacks:
            try:
                callback(prices)
            except Exception:
                pass

    def get_active_symbols(self):
        db = get_db()
        rows = db.execute("SELECT DISTINCT symbol FROM alerts WHERE is_active = 1").fetchall()
        watchlist_rows = db.execute("SELECT symbol FROM watchlist").fetchall()
        db.close()

        symbols = list(set([r["symbol"] for r in rows] + [r["symbol"] for r in watchlist_rows]))

        if not symbols:
            symbols = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"]

        return symbols

    def check_alerts(self, current_prices):
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
                })

                telegram_notifier.send_stock_alert(
                    symbol=symbol,
                    alert_type=alert_type,
                    target=target,
                    current_price=price,
                )

        db.commit()
        db.close()
        return triggered

    def _monitor_loop(self):
        while self.running:
            try:
                symbols = self.get_active_symbols()
                current_prices = {}

                for symbol in symbols:
                    try:
                        history = fetch_stock_history(symbol, period="5d")
                        if history and len(history) > 0:
                            latest_price = history[-1].get("Close") or history[-1].get("close", 0)
                            current_prices[symbol] = latest_price
                    except Exception:
                        pass

                    time.sleep(0.5)

                if current_prices:
                    self.last_prices = current_prices
                    self._notify_price_update(current_prices)

                    triggered = self.check_alerts(current_prices)
                    if triggered:
                        self._notify_listeners("alert_triggered", triggered)

                self._notify_listeners("price_update", current_prices)

            except Exception as e:
                print(f"Monitor error: {e}")

            time.sleep(self.interval)

    def start(self, interval=60):
        if self.running:
            return

        self.interval = interval
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print(f"Background monitor started (interval: {interval}s)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Background monitor stopped")

    def get_status(self):
        return {
            "running": self.running,
            "interval": self.interval,
            "last_prices": self.last_prices,
            "symbols": self.get_active_symbols(),
        }


monitor = BackgroundMonitor()
