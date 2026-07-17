"""Proyección materializada SQLite derivada únicamente del event log."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from wyss_panel_bridge.domain.projection import AggregateProjection, ProjectionGap, reduce_event
from wyss_panel_bridge.domain.v2_types import ProjectionEvent, Snapshot


class SqliteProjectionStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projection_aggregates (
                    aggregate_name TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projection_meta (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    last_event_id INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO projection_meta (singleton, last_event_id) VALUES (1, 0);
                """
            )
        os.chmod(path, 0o600)

    def apply(self, event: ProjectionEvent) -> bool:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            last_event_id = int(
                connection.execute(
                    "SELECT last_event_id FROM projection_meta WHERE singleton = 1"
                ).fetchone()[0]
            )
            if event.event_id <= last_event_id:
                return False
            if event.event_id != last_event_id + 1:
                raise ProjectionGap("hueco de event_id")
            row = connection.execute(
                """
                SELECT revision, payload_json FROM projection_aggregates
                WHERE aggregate_name = ?
                """,
                (event.aggregate,),
            ).fetchone()
            current = None
            if row is not None:
                payload = json.loads(str(row[1]))
                if not isinstance(payload, dict):
                    raise RuntimeError("projection store corrupto")
                current = AggregateProjection(int(row[0]), payload)
            reduced = reduce_event(current, event)
            payload_json = json.dumps(
                dict(reduced.payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            connection.execute(
                """
                INSERT INTO projection_aggregates (aggregate_name, revision, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(aggregate_name) DO UPDATE SET
                    revision = excluded.revision,
                    payload_json = excluded.payload_json
                """,
                (event.aggregate, reduced.revision, payload_json),
            )
            connection.execute(
                "UPDATE projection_meta SET last_event_id = ? WHERE singleton = 1",
                (event.event_id,),
            )
        return True

    def snapshot(self) -> Snapshot:
        with self._connect() as connection:
            last_event_id = int(
                connection.execute(
                    "SELECT last_event_id FROM projection_meta WHERE singleton = 1"
                ).fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT aggregate_name, payload_json FROM projection_aggregates
                ORDER BY aggregate_name
                """
            ).fetchall()
        payload: dict[str, object] = {}
        for aggregate, encoded in rows:
            decoded = json.loads(str(encoded))
            if not isinstance(decoded, dict):
                raise RuntimeError("projection store corrupto")
            payload[str(aggregate)] = decoded
        return Snapshot(last_event_id, payload)

    def last_event_id(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT last_event_id FROM projection_meta WHERE singleton = 1"
            ).fetchone()
        return int(row[0])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
