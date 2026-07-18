"""Cache privado de recordatorios y outbox durable de notificaciones."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, cast

from wyss_panel_bridge.domain.reminders import (
    Reminder,
    ReminderNotification,
    ReminderSnapshot,
)


class SqliteReminderStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reminder_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    revision INTEGER NOT NULL,
                    synced_at REAL NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )
        os.chmod(path, 0o600)

    def load(self) -> ReminderSnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT revision, synced_at, payload_json FROM reminder_state WHERE singleton = 1"
            ).fetchone()
        if row is None:
            return None
        try:
            decoded = json.loads(str(row[2]))
            if not isinstance(decoded, list):
                raise ValueError
            reminders = tuple(Reminder(**cast(dict[str, Any], item)) for item in decoded)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError("cache de recordatorios corrupta") from error
        return ReminderSnapshot(reminders, int(row[0]), float(row[1]))

    def save(self, snapshot: ReminderSnapshot) -> None:
        encoded = json.dumps(
            [
                {
                    "reminder_id": reminder.reminder_id,
                    "text": reminder.text,
                    "due_at": reminder.due_at,
                    "timezone": reminder.timezone,
                    "recurrence": reminder.recurrence,
                    "status": reminder.status,
                    "revision": reminder.revision,
                    "notification_id": reminder.notification_id,
                }
                for reminder in snapshot.reminders
            ],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reminder_state (singleton, revision, synced_at, payload_json)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(singleton) DO UPDATE SET
                    revision = excluded.revision,
                    synced_at = excluded.synced_at,
                    payload_json = excluded.payload_json
                """,
                (snapshot.revision, snapshot.synced_at, encoded),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection


class SqliteNotificationOutbox:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS notification_outbox (
                    notification_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1))
                );
                """
            )
        os.chmod(path, 0o600)

    def enqueue(self, notification: ReminderNotification) -> None:
        encoded = json.dumps(
            notification.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO notification_outbox (notification_id, payload_json)
                VALUES (?, ?)
                """,
                (notification.notification_id, encoded),
            )

    def pending(self, limit: int = 32) -> tuple[ReminderNotification, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM notification_outbox
                WHERE delivered = 0 ORDER BY rowid LIMIT ?
                """,
                (limit,),
            ).fetchall()
        notifications: list[ReminderNotification] = []
        for (encoded,) in rows:
            try:
                decoded = json.loads(str(encoded))
                if not isinstance(decoded, dict):
                    raise ValueError
                notifications.append(ReminderNotification(**cast(dict[str, str], decoded)))
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise RuntimeError("outbox de notificaciones corrupto") from error
        return tuple(notifications)

    def record_attempt(self, notification_id: str, *, accepted: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE notification_outbox
                SET attempts = attempts + 1, delivered = CASE WHEN ? THEN 1 ELSE delivered END
                WHERE notification_id = ?
                """,
                (accepted, notification_id),
            )

    def is_delivered(self, notification_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT delivered FROM notification_outbox WHERE notification_id = ?",
                (notification_id,),
            ).fetchone()
        return row is not None and bool(row[0])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
