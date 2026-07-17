"""Persistencia local de hashes de identidad; nunca almacena tokens en claro."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from wyss_panel_bridge.domain.identity import ClientIdentity


class SqliteIdentityStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS client_identities (
                    client_id TEXT PRIMARY KEY,
                    token_sha256 TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    revoked INTEGER NOT NULL CHECK (revoked IN (0, 1)),
                    updated_at TEXT NOT NULL
                )
                """
            )
        os.chmod(path, 0o600)

    def get(self, client_id: str) -> ClientIdentity | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT client_id, token_sha256, capabilities_json, generation, revoked, updated_at
                FROM client_identities WHERE client_id = ?
                """,
                (client_id,),
            ).fetchone()
        if row is None:
            return None
        capabilities = json.loads(str(row[2]))
        if not isinstance(capabilities, list) or not all(
            isinstance(item, str) for item in capabilities
        ):
            raise RuntimeError("identity store corrupto")
        return ClientIdentity(
            client_id=str(row[0]),
            token_sha256=str(row[1]),
            capabilities=frozenset(capabilities),
            generation=int(row[3]),
            revoked=bool(row[4]),
            updated_at=str(row[5]),
        )

    def save(self, identity: ClientIdentity) -> None:
        capabilities = json.dumps(sorted(identity.capabilities), separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO client_identities (
                    client_id, token_sha256, capabilities_json, generation, revoked, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                    token_sha256 = excluded.token_sha256,
                    capabilities_json = excluded.capabilities_json,
                    generation = excluded.generation,
                    revoked = excluded.revoked,
                    updated_at = excluded.updated_at
                """,
                (
                    identity.client_id,
                    identity.token_sha256,
                    capabilities,
                    identity.generation,
                    int(identity.revoked),
                    identity.updated_at,
                ),
            )

    def list_redacted(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT client_id, capabilities_json, generation, revoked, updated_at
                FROM client_identities ORDER BY client_id
                """
            ).fetchall()
        return [
            {
                "client_id": str(row[0]),
                "capabilities": json.loads(str(row[1])),
                "generation": int(row[2]),
                "revoked": bool(row[3]),
                "updated_at": str(row[4]),
            }
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
