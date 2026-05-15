"""
SQLite-backed user memory. Stores linked Chess.com accounts and preferences
so users don't need to re-enter info every session.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "users.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chess_username TEXT UNIQUE NOT NULL,
                linked_at TEXT NOT NULL,
                last_session TEXT,
                preferred_time_control TEXT DEFAULT 'all',
                white_opening TEXT,
                black_vs_e4 TEXT,
                black_vs_d4 TEXT,
                goals TEXT
            )
        """)
        conn.commit()


def get_user(chess_username: str) -> Optional[dict]:
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(chess_username) = LOWER(?)",
            (chess_username,)
        ).fetchone()
        return dict(row) if row else None


def save_user(chess_username: str, preferences: dict = None) -> None:
    init_db()
    prefs = preferences or {}
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO users (chess_username, linked_at, last_session,
                preferred_time_control, white_opening, black_vs_e4, black_vs_d4, goals)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chess_username) DO UPDATE SET
                last_session = excluded.last_session,
                preferred_time_control = COALESCE(excluded.preferred_time_control, preferred_time_control),
                white_opening = COALESCE(excluded.white_opening, white_opening),
                black_vs_e4 = COALESCE(excluded.black_vs_e4, black_vs_e4),
                black_vs_d4 = COALESCE(excluded.black_vs_d4, black_vs_d4),
                goals = COALESCE(excluded.goals, goals)
        """, (
            chess_username,
            now,
            now,
            prefs.get("preferred_time_control"),
            prefs.get("white_opening"),
            prefs.get("black_vs_e4"),
            prefs.get("black_vs_d4"),
            prefs.get("main_goal"),
        ))
        conn.commit()


def update_last_session(chess_username: str) -> None:
    init_db()
    with _get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_session = ? WHERE LOWER(chess_username) = LOWER(?)",
            (datetime.now().isoformat(), chess_username)
        )
        conn.commit()
