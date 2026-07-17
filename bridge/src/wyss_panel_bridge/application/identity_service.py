"""Pairing, rotación y revocación por dispositivo."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from wyss_panel_bridge.domain.identity import (
    ALLOWED_CAPABILITIES,
    CLIENT_ID_RE,
    ClientIdentity,
    IdentityError,
)
from wyss_panel_bridge.ports_v2 import IdentityStorePort


class IdentityService:
    def __init__(
        self,
        store: IdentityStorePort,
        now: Callable[[], datetime] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        self._store = store
        self._now = now or (lambda: datetime.now(UTC))
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))

    def pair(self, client_id: str, capabilities: Iterable[str]) -> str:
        if self._store.get(client_id) is not None:
            raise IdentityError("client_id ya existe; use rotate")
        return self._issue(client_id, capabilities, generation=1)

    def rotate(self, client_id: str) -> str:
        current = self._required(client_id)
        return self._issue(client_id, current.capabilities, generation=current.generation + 1)

    def revoke(self, client_id: str) -> None:
        current = self._required(client_id)
        self._store.save(
            ClientIdentity(
                client_id=current.client_id,
                token_sha256=current.token_sha256,
                capabilities=current.capabilities,
                generation=current.generation,
                revoked=True,
                updated_at=self._timestamp(),
            )
        )

    def authenticate(self, client_id: str, token: str, capability: str | None = None) -> bool:
        current = self._store.get(client_id)
        if current is None or current.revoked or not token:
            return False
        if capability is not None and capability not in current.capabilities:
            return False
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, current.token_sha256)

    def _issue(self, client_id: str, capabilities: Iterable[str], generation: int) -> str:
        if CLIENT_ID_RE.fullmatch(client_id) is None:
            raise IdentityError("client_id inválido")
        granted = frozenset(capabilities)
        if not granted or not granted <= ALLOWED_CAPABILITIES:
            raise IdentityError("capabilities inválidas")
        token = self._token_factory()
        if len(token) < 32:
            raise IdentityError("token generado demasiado corto")
        self._store.save(
            ClientIdentity(
                client_id=client_id,
                token_sha256=hashlib.sha256(token.encode("utf-8")).hexdigest(),
                capabilities=granted,
                generation=generation,
                revoked=False,
                updated_at=self._timestamp(),
            )
        )
        return token

    def _required(self, client_id: str) -> ClientIdentity:
        current = self._store.get(client_id)
        if current is None:
            raise IdentityError("client_id desconocido")
        return current

    def _timestamp(self) -> str:
        return self._now().astimezone(UTC).isoformat().replace("+00:00", "Z")
