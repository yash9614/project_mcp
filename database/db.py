"""
db.py - SQLite connection + helpers.

The schema lives in schema.sql and the demo data in seed.sql.
Application code does NOT write SQL directly - it goes through the classes in models.py.

Run `python -m database.db` (from the project root) to DELETE and re-create the database with fresh demo data.
All seeded users have the password: password123
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from common.config import DB_PATH

BASE_DIR = Path(__file__).parent
SCHEMA_FILE = BASE_DIR / "schema.sql"
SEED_FILE = BASE_DIR / "seed.sql"

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@contextmanager
def get_conn():
    """
    Usage:  with get_conn() as conn: conn.execute(...)
    Rows behave like dicts (row["name"]). Commits on success, rolls back on error, always closes.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def now_str(delta: timedelta = timedelta()) -> str:
    """Current time as 'YYYY-MM-DD HH:MM:SS', optionally shifted by `delta`."""
    return (datetime.now() + delta).strftime(TIME_FORMAT)


def parse_ts(ts: str) -> datetime:
    return datetime.strptime(ts, TIME_FORMAT)


def migrate() -> None:
    with get_conn() as conn:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]
        if columns and "scopes" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN scopes TEXT")


def reset_db() -> None:
    """Run schema.sql (drops + creates tables) and then seed.sql."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_FILE.read_text())
        conn.executescript(SEED_FILE.read_text())


if __name__ == "__main__":
    reset_db()
    print(f"Database reset and seeded at {DB_PATH}")
    print("Logins (password: password123):")
    print("  learner: rahul@learner.com, priya@learner.com, aman@learner.com")
    print("  support: neha@telusko.com, vikram@telusko.com")
    print("  admin:   akshay@telusko.com")