from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Dict

DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect():
    return sqlite3.connect(DB_PATH)


SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    user_id TEXT,
    rating INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bandit_arm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT,
    arm TEXT,
    pulls INTEGER DEFAULT 0,
    reward_sum REAL DEFAULT 0.0,
    UNIQUE(agent, arm)
);
"""


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def record_feedback(event_id: str, user_id: str, rating: int, reason: str | None):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO feedback(event_id, user_id, rating, reason) VALUES (?, ?, ?, ?)",
            (event_id, user_id, rating, reason),
        )
        conn.commit()


def get_arms(agent: str) -> List[Dict]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT agent, arm, pulls, reward_sum FROM bandit_arm WHERE agent=?", (agent,)
        )
        rows = cur.fetchall()
    return [
        {"agent": row[0], "arm": row[1], "pulls": row[2], "reward_sum": row[3]}
        for row in rows
    ]


def upsert_arm(agent: str, arm: str, reward: float | None = None, pulled: bool = False):
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO bandit_arm(agent, arm, pulls, reward_sum) VALUES (?, ?, 0, 0.0)",
            (agent, arm),
        )
        if pulled or reward is not None:
            conn.execute(
                "UPDATE bandit_arm SET pulls = pulls + ?, reward_sum = reward_sum + ? WHERE agent = ? AND arm = ?",
                (1 if pulled else 0, reward or 0.0, agent, arm),
            )
        conn.commit()
