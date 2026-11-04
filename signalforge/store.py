from __future__ import annotations

import json
import sqlite3
from threading import RLock
from pathlib import Path

from .models import ScoredTrace, Trace


class TraceStore:
    def __init__(self, path: str | Path = "signalforge.db") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = RLock()
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY, payload TEXT NOT NULL, score REAL NOT NULL,
                risk TEXT NOT NULL, created_at TEXT NOT NULL
            )"""
        )
        self.connection.commit()

    def save(self, result: ScoredTrace) -> None:
        with self.lock:
            self.connection.execute(
                """INSERT OR REPLACE INTO traces(trace_id, payload, score, risk, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    result.trace.trace_id,
                    json.dumps(result.to_dict()),
                    result.score,
                    result.risk,
                    result.trace.timestamp,
                ),
            )
            self.connection.commit()

    def list(self, limit: int = 100) -> list[ScoredTrace]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT payload FROM traces ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [self._decode(row["payload"]) for row in rows]

    @staticmethod
    def _decode(payload: str) -> ScoredTrace:
        data = json.loads(payload)
        trace = Trace.from_dict(data)
        from .models import Finding

        findings = [Finding(**finding) for finding in data["findings"]]
        return ScoredTrace(trace=trace, score=data["score"], risk=data["risk"], findings=findings)

    def close(self) -> None:
        self.connection.close()
