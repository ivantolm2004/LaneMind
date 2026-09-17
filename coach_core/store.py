from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS matches (
              match_id TEXT PRIMARY KEY,
              account_id INTEGER,
              source TEXT NOT NULL,
              raw_json TEXT NOT NULL,
              report_json TEXT NOT NULL,
              imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )

    def save_match(self, match: dict[str, Any], report: dict[str, Any], account_id: int | None, source: str) -> None:
        self.connection.execute(
            """INSERT INTO matches(match_id, account_id, source, raw_json, report_json)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(match_id) DO UPDATE SET account_id=excluded.account_id,
                 source=excluded.source, raw_json=excluded.raw_json,
                 report_json=excluded.report_json, imported_at=CURRENT_TIMESTAMP""",
            (report["match_id"], account_id, source, json.dumps(match), json.dumps(report)),
        )
        self.connection.commit()

    def reports(self, limit: int = 30) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT report_json, source, imported_at FROM matches ORDER BY imported_at DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for row in rows:
            report = json.loads(row["report_json"])
            report["source"] = row["source"]
            report["imported_at"] = row["imported_at"]
            result.append(report)
        return result

    def close(self) -> None:
        self.connection.close()
