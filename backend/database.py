import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "stock_analyzer.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            name TEXT,
            notes TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            target_value REAL NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            triggered_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            UNIQUE(symbol, date)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            buy_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            buy_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def watchlist_add(symbol, name=None, notes=None):
    db = get_db()
    try:
        db.execute(
            "INSERT INTO watchlist (symbol, name, notes) VALUES (?, ?, ?)",
            (symbol.upper(), name, notes),
        )
        db.commit()
        return {"status": "added", "symbol": symbol.upper()}
    except sqlite3.IntegrityError:
        return {"status": "exists", "symbol": symbol.upper()}
    finally:
        db.close()


def watchlist_remove(symbol):
    db = get_db()
    db.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
    db.commit()
    db.close()
    return {"status": "removed", "symbol": symbol.upper()}


def watchlist_get_all():
    db = get_db()
    rows = db.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()
    db.close()
    return [dict(row) for row in rows]


def watchlist_exists(symbol):
    db = get_db()
    row = db.execute("SELECT 1 FROM watchlist WHERE symbol = ?", (symbol.upper(),)).fetchone()
    db.close()
    return row is not None


def watchlist_clear():
    db = get_db()
    db.execute("DELETE FROM watchlist")
    db.commit()
    db.close()
    return {"status": "cleared"}


init_db()
