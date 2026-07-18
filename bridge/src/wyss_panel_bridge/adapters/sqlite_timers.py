"""Cache, dedupe de finalización y outbox privados para timers."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, cast

from wyss_panel_bridge.domain.timers import Timer, TimerNotification, TimerSnapshot


def _timer_payload(timer: Timer) -> dict[str, object]:
    return {
        "timer_id": timer.timer_id,
        "label": timer.label,
        "status": timer.status,
        "revision": timer.revision,
        "duration_seconds": timer.duration_seconds,
        "remaining_seconds": timer.remaining_seconds,
        "deadline_at": timer.deadline_at,
        "preset": timer.preset,
        "completion_id": timer.completion_id,
        "notification_id": timer.notification_id,
    }


class SqliteTimerStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS timer_state (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    revision INTEGER NOT NULL,
                    synced_at REAL NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS timer_completions (
                    completion_id TEXT PRIMARY KEY,
                    timer_id TEXT NOT NULL
                );
                """
            )
        os.chmod(path, 0o600)

    def load(self) -> TimerSnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT revision, synced_at, payload_json FROM timer_state WHERE singleton = 1"
            ).fetchone()
        if row is None:
            return None
        return TimerSnapshot(self._decode(str(row[2])), int(row[0]), float(row[1]))

    def save(self, snapshot: TimerSnapshot) -> None:
        encoded = self._encode(snapshot.timers)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO timer_state (singleton, revision, synced_at, payload_json)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(singleton) DO UPDATE SET
                    revision = excluded.revision,
                    synced_at = excluded.synced_at,
                    payload_json = excluded.payload_json
                """,
                (snapshot.revision, snapshot.synced_at, encoded),
            )

    def completion_recorded(self, completion_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM timer_completions WHERE completion_id = ?", (completion_id,)
            ).fetchone()
        return row is not None

    def record_completion(self, completion_id: str, timer_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO timer_completions (completion_id, timer_id) VALUES (?, ?)",
                (completion_id, timer_id),
            )

    def export_active(self) -> str:
        snapshot = self.load()
        timers = (
            ()
            if snapshot is None
            else tuple(timer for timer in snapshot.timers if timer.status in {"running", "paused"})
        )
        return self._encode(timers)

    def import_active(self, encoded: str, revision: int, synced_at: float) -> TimerSnapshot:
        timers = self._decode(encoded)
        if any(timer.status not in {"running", "paused"} for timer in timers):
            raise RuntimeError("export de timers contiene estado no activo")
        snapshot = TimerSnapshot(timers, revision, synced_at)
        self.save(snapshot)
        return snapshot

    @staticmethod
    def _encode(timers: tuple[Timer, ...]) -> str:
        return json.dumps(
            [_timer_payload(timer) for timer in timers],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @staticmethod
    def _decode(encoded: str) -> tuple[Timer, ...]:
        try:
            decoded = json.loads(encoded)
            if not isinstance(decoded, list):
                raise ValueError
            return tuple(Timer(**cast(dict[str, Any], item)) for item in decoded)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError("cache de timers corrupta") from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection


class SqliteTimerNotificationOutbox:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS timer_notification_outbox (
                    notification_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    delivered INTEGER NOT NULL DEFAULT 0 CHECK (delivered IN (0, 1))
                )
                """
            )
        os.chmod(path, 0o600)

    def enqueue(self, notification: TimerNotification) -> None:
        encoded = json.dumps(
            notification.payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO timer_notification_outbox
                    (notification_id, payload_json) VALUES (?, ?)
                """,
                (notification.notification_id, encoded),
            )

    def pending(self, limit: int = 128) -> tuple[TimerNotification, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM timer_notification_outbox
                WHERE delivered = 0 ORDER BY rowid LIMIT ?
                """,
                (limit,),
            ).fetchall()
        try:
            return tuple(
                TimerNotification(**cast(dict[str, str], json.loads(str(row[0])))) for row in rows
            )
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise RuntimeError("outbox de timers corrupto") from error

    def record_attempt(self, notification_id: str, *, accepted: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE timer_notification_outbox
                SET attempts = attempts + 1, delivered = CASE WHEN ? THEN 1 ELSE delivered END
                WHERE notification_id = ?
                """,
                (accepted, notification_id),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
