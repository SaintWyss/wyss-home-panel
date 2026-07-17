"""Journal durable de comandos de luces, separado de proyecciones cliente."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from wyss_panel_bridge.domain.lights import LightAuditRecord, LightAuditStatus, LightConflict


class SqliteLightAuditStore:
    def __init__(self, path: Path, *, now: Callable[[], float] = time.time) -> None:
        self._path = path
        self._now = now
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS light_command_audit (
                    idempotency_key TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    source TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('accepted', 'verified', 'failed', 'ambiguous')
                    ),
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
        os.chmod(path, 0o600)

    def claim(
        self,
        idempotency_key: str,
        request_id: str,
        fingerprint: str,
        source: str,
        entity_id: str,
        action: str,
    ) -> LightAuditRecord:
        if not idempotency_key or not request_id or not fingerprint or not source:
            raise ValueError("claim de luz incompleta")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._select(connection, idempotency_key)
            replayed = row is not None
            if not replayed:
                current = self._now()
                connection.execute(
                    """
                    INSERT INTO light_command_audit (
                        idempotency_key, request_id, fingerprint, source, entity_id, action, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'accepted', ?, ?)
                    """,
                    (
                        idempotency_key,
                        request_id,
                        fingerprint,
                        source,
                        entity_id,
                        action,
                        current,
                        current,
                    ),
                )
                row = self._select(connection, idempotency_key)
            if row is None:
                raise RuntimeError("el journal no persistió el comando de luz")
            record = replace(self._from_row(row), replayed=replayed)
            if record.fingerprint != fingerprint:
                raise LightConflict(
                    "conflict",
                    "La idempotency key fue reutilizada con otro comando",
                )
            return record

    def verified(self, idempotency_key: str, result: Mapping[str, Any]) -> LightAuditRecord:
        encoded = json.dumps(
            dict(result), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return self._finish(idempotency_key, "verified", encoded, None, None)

    def failed(
        self,
        idempotency_key: str,
        code: str,
        message: str,
        *,
        ambiguous: bool = False,
    ) -> LightAuditRecord:
        status = "ambiguous" if ambiguous else "failed"
        return self._finish(idempotency_key, status, None, code, message)

    def _finish(
        self,
        idempotency_key: str,
        status: str,
        result_json: str | None,
        error_code: str | None,
        error_message: str | None,
    ) -> LightAuditRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._select(connection, idempotency_key)
            if row is None:
                raise RuntimeError("el comando de luz no fue reclamado")
            current = self._from_row(row)
            if current.status != "accepted":
                return current
            connection.execute(
                """
                UPDATE light_command_audit
                SET status = ?, result_json = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE idempotency_key = ? AND status = 'accepted'
                """,
                (status, result_json, error_code, error_message, self._now(), idempotency_key),
            )
            completed = self._select(connection, idempotency_key)
        if completed is None:
            raise RuntimeError("el journal perdió el comando de luz")
        return self._from_row(completed)

    @staticmethod
    def _select(connection: sqlite3.Connection, idempotency_key: str) -> tuple[Any, ...] | None:
        return cast(
            tuple[Any, ...] | None,
            connection.execute(
                """
                SELECT idempotency_key, request_id, fingerprint, source, entity_id, action, status,
                       result_json, error_code, error_message
                FROM light_command_audit WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone(),
        )

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> LightAuditRecord:
        result = None
        if row[7] is not None:
            decoded = json.loads(str(row[7]))
            if not isinstance(decoded, Mapping):
                raise RuntimeError("journal de luces corrupto")
            result = dict(decoded)
        return LightAuditRecord(
            idempotency_key=str(row[0]),
            request_id=str(row[1]),
            fingerprint=str(row[2]),
            source=str(row[3]),
            entity_id=str(row[4]),
            action=str(row[5]),
            status=cast(LightAuditStatus, str(row[6])),
            result=result,
            error_code=str(row[8]) if row[8] is not None else None,
            error_message=str(row[9]) if row[9] is not None else None,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
