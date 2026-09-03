"""SQLite usage ledger: tokens / USD / model / group per gateway call."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  task_id TEXT,
  caller TEXT,
  grp TEXT,
  provider TEXT,
  model TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  usd REAL,
  elapsed_ms INTEGER
);
CREATE INDEX IF NOT EXISTS idx_usage_task ON usage(task_id);
"""


class UsageLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as c:
            c.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5)

    def record(
        self,
        *,
        task_id: str | None,
        caller: str,
        group: str,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        usd: float,
        elapsed_ms: int,
    ) -> None:
        with self._lock, self._connect() as c:
            c.execute(
                "INSERT INTO usage(ts,task_id,caller,grp,provider,model,tokens_in,tokens_out,usd,elapsed_ms)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    time.time(),
                    task_id,
                    caller,
                    group,
                    provider,
                    model,
                    tokens_in,
                    tokens_out,
                    usd,
                    elapsed_ms,
                ),
            )

    def totals_for(self, task_id: str) -> dict[str, float]:
        with self._connect() as c:
            row = c.execute(
                "SELECT COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0), COALESCE(SUM(usd),0), COUNT(*)"
                " FROM usage WHERE task_id=?",
                (task_id,),
            ).fetchone()
        return {"tokens_in": row[0], "tokens_out": row[1], "usd": round(row[2], 6), "calls": row[3]}

    def totals(self) -> dict[str, float]:
        with self._connect() as c:
            row = c.execute(
                "SELECT COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0),"
                " COALESCE(SUM(usd),0), COUNT(*) FROM usage"
            ).fetchone()
        return {"tokens_in": row[0], "tokens_out": row[1], "usd": round(row[2], 6), "calls": row[3]}
