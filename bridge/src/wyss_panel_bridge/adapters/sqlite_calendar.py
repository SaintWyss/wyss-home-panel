"""Cache Calendar durable y privada con reemplazo full-sync atómico."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from wyss_panel_bridge.domain.calendar import CalendarCache, CalendarEvent


class SqliteCalendarStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS calendar_events (
                    event_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS calendar_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    sync_token TEXT NOT NULL,
                    synced_at REAL NOT NULL
                );
                """
            )
        os.chmod(path, 0o600)

    def load(self) -> CalendarCache | None:
        with self._connect() as connection:
            state = connection.execute(
                "SELECT sync_token, synced_at FROM calendar_state WHERE singleton = 1"
            ).fetchone()
            rows = connection.execute(
                "SELECT payload_json FROM calendar_events ORDER BY event_id"
            ).fetchall()
        if state is None:
            return None
        try:
            events = tuple(self._decode(row[0]) for row in rows)
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise RuntimeError("cache Calendar corrupta") from error
        return CalendarCache(events, str(state[0]), float(state[1]))

    def replace(self, cache: CalendarCache) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM calendar_events")
            self._upsert_events(connection, cache.events)
            self._save_state(connection, cache.sync_token, cache.synced_at)

    def apply(self, events: tuple[CalendarEvent, ...], sync_token: str, synced_at: float) -> None:
        with self._connect() as connection:
            for event in events:
                if event.status == "cancelled":
                    connection.execute(
                        "DELETE FROM calendar_events WHERE event_id = ?", (event.event_id,)
                    )
                else:
                    self._upsert_events(connection, (event,))
            self._save_state(connection, sync_token, synced_at)

    @staticmethod
    def _upsert_events(connection: sqlite3.Connection, events: tuple[CalendarEvent, ...]) -> None:
        connection.executemany(
            """
            INSERT INTO calendar_events (event_id, payload_json) VALUES (?, ?)
            ON CONFLICT(event_id) DO UPDATE SET payload_json = excluded.payload_json
            """,
            (
                (
                    event.event_id,
                    json.dumps(asdict(event), sort_keys=True, separators=(",", ":")),
                )
                for event in events
                if event.status != "cancelled"
            ),
        )

    @staticmethod
    def _save_state(connection: sqlite3.Connection, sync_token: str, synced_at: float) -> None:
        connection.execute(
            """
            INSERT INTO calendar_state (singleton, sync_token, synced_at) VALUES (1, ?, ?)
            ON CONFLICT(singleton) DO UPDATE SET
                sync_token = excluded.sync_token,
                synced_at = excluded.synced_at
            """,
            (sync_token, synced_at),
        )

    @staticmethod
    def _decode(encoded: object) -> CalendarEvent:
        raw = json.loads(str(encoded))
        if not isinstance(raw, dict):
            raise TypeError
        return CalendarEvent(**cast(dict[str, Any], raw))

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)
