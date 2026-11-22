"""SQLite log of reviewed contracts for Clause Lens."""

import json
import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get(
    "CLAUSE_LENS_DB", os.path.join(BASE_DIR, "data", "reviews.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    title TEXT,
    contract_type TEXT,
    perspective TEXT,
    score REAL,
    verdict TEXT,
    rating INTEGER,
    notes TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at DESC);
"""


def connect():
    folder = os.path.dirname(os.path.abspath(DB_PATH))
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def save_review(result):
    meta = result.get("meta", {})
    score = result.get("score", {})
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO reviews (created_at, title, contract_type, perspective, score, verdict, payload)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                now_iso(),
                meta.get("title") or "Untitled agreement",
                meta.get("contract_type", "generic"),
                meta.get("perspective", "party"),
                score.get("overall", 0),
                score.get("verdict", ""),
                json.dumps(result),
            ),
        )
        return cur.lastrowid


def list_reviews(limit=50):
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, title, contract_type, perspective, score, verdict, rating, notes"
            " FROM reviews ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_review(review_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data["result"] = json.loads(data.pop("payload"))
    except (ValueError, TypeError):
        data["result"] = None
        data.pop("payload", None)
    return data


def rate_review(review_id, rating=None, notes=None):
    with connect() as conn:
        row = conn.execute("SELECT id FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if not row:
            return False
        if rating is None and notes is None:
            return True
        if rating is not None:
            conn.execute("UPDATE reviews SET rating = ? WHERE id = ?", (int(rating), review_id))
        if notes is not None:
            conn.execute("UPDATE reviews SET notes = ? WHERE id = ?", (notes, review_id))
    return True


def delete_review(review_id):
    with connect() as conn:
        cur = conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        return cur.rowcount > 0
