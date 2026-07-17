"""Log SQLite ordenado e idempotente para proyecciones v2."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from wyss_panel_bridge.domain.events import EventConflict, EventDraft, EventError
from wyss_panel_bridge.domain.v2_types import ProjectionEvent


class SqliteEventStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projection_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    fingerprint TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    aggregate_name TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    correlation_id TEXT,
                    causation_id TEXT,
                    UNIQUE (aggregate_name, revision)
                )
                """
            )
        os.chmod(path, 0o600)

    def append(self, draft: EventDraft, idempotency_key: str) -> ProjectionEvent:
        payload_json, fingerprint = self._encode(draft, idempotency_key)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT event_id, event_type, aggregate_name, revision, payload_json,
                       correlation_id, causation_id, fingerprint
                FROM projection_events WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if str(existing[7]) != fingerprint:
                    raise EventConflict("idempotency key reutilizada con contenido diferente")
                return self._from_row(existing[:7])
            revision = int(
                connection.execute(
                    """
                    SELECT COALESCE(MAX(revision), 0) + 1
                    FROM projection_events WHERE aggregate_name = ?
                    """,
                    (draft.aggregate,),
                ).fetchone()[0]
            )
            cursor = connection.execute(
                """
                INSERT INTO projection_events (
                    idempotency_key, fingerprint, event_type, aggregate_name, revision,
                    payload_json, correlation_id, causation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    idempotency_key,
                    fingerprint,
                    draft.event_type,
                    draft.aggregate,
                    revision,
                    payload_json,
                    draft.correlation_id,
                    draft.causation_id,
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("event store no devolvió event_id")
            event_id = cursor.lastrowid
        return ProjectionEvent(
            event_id=event_id,
            aggregate=draft.aggregate,
            revision=revision,
            payload=json.loads(payload_json),
            event_type=draft.event_type,
            correlation_id=draft.correlation_id,
            causation_id=draft.causation_id,
        )

    def after(self, event_id: int, limit: int) -> list[ProjectionEvent]:
        if event_id < 0 or not 1 <= limit <= 256:
            raise EventError("cursor o límite inválido")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, event_type, aggregate_name, revision, payload_json,
                       correlation_id, causation_id
                FROM projection_events WHERE event_id > ? ORDER BY event_id LIMIT ?
                """,
                (event_id, limit),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def latest_event_id(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(event_id), 0) FROM projection_events"
            ).fetchone()
        return int(row[0])

    @staticmethod
    def _encode(draft: EventDraft, idempotency_key: str) -> tuple[str, str]:
        if not idempotency_key or len(idempotency_key) > 128:
            raise EventError("idempotency key inválida")
        if not draft.event_type or not draft.aggregate:
            raise EventError("tipo o agregado vacío")
        try:
            payload_json = json.dumps(
                dict(draft.payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            canonical = json.dumps(
                {
                    "aggregate": draft.aggregate,
                    "causation_id": draft.causation_id,
                    "correlation_id": draft.correlation_id,
                    "event_type": draft.event_type,
                    "payload": json.loads(payload_json),
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        except (TypeError, ValueError) as error:
            raise EventError("payload no serializable") from error
        return payload_json, hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> ProjectionEvent:
        payload = json.loads(str(row[4]))
        if not isinstance(payload, Mapping):
            raise RuntimeError("event store corrupto")
        return ProjectionEvent(
            event_id=int(row[0]),
            event_type=str(row[1]),
            aggregate=str(row[2]),
            revision=int(row[3]),
            payload=dict(payload),
            correlation_id=str(row[5]) if row[5] is not None else None,
            causation_id=str(row[6]) if row[6] is not None else None,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
