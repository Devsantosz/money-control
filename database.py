"""Persistência e relatórios do controle financeiro."""

import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo


DATABASE_PATH = os.getenv("DATABASE_PATH", "financeiro.db")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "America/Sao_Paulo"))


def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('expense', 'income')),
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                description TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                message_id TEXT UNIQUE
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_sender_date "
            "ON transactions(sender, occurred_at)"
        )


def now_local():
    return datetime.now(TIMEZONE)


def add_transaction(sender, kind, amount_cents, description, message_id=None):
    timestamp = now_local().isoformat(timespec="seconds")
    with connect() as connection:
        cursor = connection.execute(
            """INSERT INTO transactions
               (sender, kind, amount_cents, description, occurred_at, message_id)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(message_id) DO NOTHING""",
            (sender, kind, amount_cents, description, timestamp, message_id),
        )
        return cursor.rowcount == 1, timestamp


def monthly_report(sender, year, month):
    start = datetime(year, month, 1, tzinfo=TIMEZONE)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=TIMEZONE)
    else:
        end = datetime(year, month + 1, 1, tzinfo=TIMEZONE)

    with connect() as connection:
        totals = connection.execute(
            """SELECT kind, SUM(amount_cents) AS total
               FROM transactions
               WHERE sender = ? AND occurred_at >= ? AND occurred_at < ?
               GROUP BY kind""",
            (sender, start.isoformat(), end.isoformat()),
        ).fetchall()
        rows = connection.execute(
            """SELECT kind, amount_cents, description, occurred_at
               FROM transactions
               WHERE sender = ? AND occurred_at >= ? AND occurred_at < ?
               ORDER BY occurred_at DESC""",
            (sender, start.isoformat(), end.isoformat()),
        ).fetchall()

    totals_by_kind = {row["kind"]: row["total"] or 0 for row in totals}
    weekly = {}
    daily = {}
    for row in rows:
        local_time = datetime.fromisoformat(row["occurred_at"])
        iso_year, iso_week, _ = local_time.isocalendar()
        key_week = f"{iso_year}-S{iso_week:02d}"
        key_day = local_time.strftime("%d/%m")
        bucket = weekly.setdefault(key_week, {"expense": 0, "income": 0})
        bucket[row["kind"]] += row["amount_cents"]
        bucket = daily.setdefault(key_day, {"expense": 0, "income": 0})
        bucket[row["kind"]] += row["amount_cents"]

    return {
        "income": totals_by_kind.get("income", 0),
        "expense": totals_by_kind.get("expense", 0),
        "balance": totals_by_kind.get("income", 0) - totals_by_kind.get("expense", 0),
        "weekly": weekly,
        "daily": daily,
        "transactions": [dict(row) for row in rows[:20]],
    }
