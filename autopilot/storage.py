"""Local SQLite ledger; keep the database outside the public repository."""
import sqlite3
from pathlib import Path
import os

class Ledger:
    def __init__(self, path=None):
        path = Path(path or Path.home() / ".careerdojo" / "autopilot.sqlite3")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, title TEXT NOT NULL, score INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'review_required')")
        self.db.commit()

    def ingest(self, jobs):
        with self.db:
            self.db.executemany("INSERT OR IGNORE INTO jobs(id,url,title,score) VALUES (:id,:url,:title,:score)", jobs)

    def pending(self):
        return self.db.execute("SELECT id,url,title,score FROM jobs WHERE status='review_required' ORDER BY score DESC").fetchall()

    def close(self):
        self.db.close()
