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
            CREATE TABLE IF NOT EXISTS ai_summaries (
              match_id TEXT NOT NULL,
              model TEXT NOT NULL,
              language TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(match_id, model, language),
              FOREIGN KEY(match_id) REFERENCES matches(match_id)
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
            summary = self.connection.execute(
                """SELECT model, language, content, created_at FROM ai_summaries
                   WHERE match_id = ? ORDER BY created_at DESC LIMIT 1""",
                (report["match_id"],),
            ).fetchone()
            if summary:
                report["ai_summary"] = dict(summary)
            result.append(report)
        return result

    def report(self, match_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT report_json FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        return json.loads(row["report_json"]) if row else None

    def save_ai_summary(self, match_id: str, model: str, language: str, content: str) -> None:
        self.connection.execute(
            """INSERT INTO ai_summaries(match_id, model, language, content)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(match_id, model, language) DO UPDATE SET
                 content=excluded.content, created_at=CURRENT_TIMESTAMP""",
            (match_id, model, language, content),
        )
        self.connection.commit()

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.connection.execute(
            """INSERT INTO settings(key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
