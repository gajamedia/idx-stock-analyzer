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
            symbol TEXT NOT NULL UNIQUE,
            lots REAL NOT NULL,
            avg_price REAL NOT NULL,
            buy_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _migrate_portfolio_table(cursor)

    conn.commit()
    conn.close()


def _migrate_portfolio_table(cursor):
    cols = [row[1] for row in cursor.execute("PRAGMA table_info(portfolio)").fetchall()]
    if not cols or "lots" in cols:
        return

    count = cursor.execute("SELECT COUNT(*) FROM portfolio").fetchone()[0]
    if count == 0:
        cursor.execute("DROP TABLE portfolio")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                lots REAL NOT NULL,
                avg_price REAL NOT NULL,
                buy_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        return

    cursor.execute("ALTER TABLE portfolio ADD COLUMN lots REAL NOT NULL DEFAULT 0")
    cursor.execute("ALTER TABLE portfolio ADD COLUMN avg_price REAL NOT NULL DEFAULT 0")
    cursor.execute("UPDATE portfolio SET avg_price = buy_price")
    cursor.execute("UPDATE portfolio SET lots = CASE WHEN quantity >= 100 THEN quantity / 100.0 ELSE quantity END")


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


def portfolio_get_all():
    db = get_db()
    rows = db.execute("SELECT * FROM portfolio ORDER BY symbol ASC").fetchall()
    db.close()
    return [dict(row) for row in rows]


def portfolio_upsert(symbol, lots, avg_price):
    symbol = symbol.upper()
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO portfolio (symbol, lots, avg_price) VALUES (?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET lots = excluded.lots, avg_price = excluded.avg_price
            """,
            (symbol, float(lots), float(avg_price)),
        )
        db.commit()
        return {"status": "saved", "symbol": symbol}
    finally:
        db.close()


def portfolio_delete(symbol):
    db = get_db()
    db.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol.upper(),))
    db.commit()
    db.close()
    return {"status": "removed", "symbol": symbol.upper()}


def portfolio_clear():
    db = get_db()
    db.execute("DELETE FROM portfolio")
    db.commit()
    db.close()
    return {"status": "cleared"}


init_db()
