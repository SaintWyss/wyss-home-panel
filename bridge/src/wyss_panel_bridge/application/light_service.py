"""Ejecución autoritativa de luces con estado verificado y audit trail durable."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from wyss_panel_bridge.domain.events import EventDraft
from wyss_panel_bridge.domain.lights import LightAuditRecord, LightConflict, LightError
from wyss_panel_bridge.domain.models import DeviceState, FastCommand, PolicyError
from wyss_panel_bridge.domain.policy import validate_fast_command
from wyss_panel_bridge.domain.v2_types import ProjectionEvent
from wyss_panel_bridge.ports_v2 import EventStorePort, LightAuditPort, LightPort


@dataclass(frozen=True, slots=True)
class LightCommandResult:
    event: ProjectionEvent
    replayed: bool


class LightService:
    def __init__(
        self,
        lights: LightPort,
        events: EventStorePort,
        audit: LightAuditPort,
        allowed_entities: frozenset[str],
        *,
        instance_id: str | None = None,
        max_request_locks: int = 2048,
    ) -> None:
        if not allowed_entities or max_request_locks <= 0:
            raise ValueError("configuración de luces inválida")
        self._lights = lights
        self._events = events
        self._audit = audit
        self._allowed = allowed_entities
        self._instance_id = instance_id or secrets.token_hex(12)
        self._max_request_locks = max_request_locks
        self._cache: dict[str, DeviceState] = {}
        self._entity_locks = {entity: asyncio.Lock() for entity in allowed_entities}
        self._request_locks: OrderedDict[str, asyncio.Lock] = OrderedDict()
        self._request_guard = asyncio.Lock()
        self._projection_lock = asyncio.Lock()
        self._bootstrap_lock = asyncio.Lock()
        self._bootstrapped = False
        self._event_sink: Callable[[ProjectionEvent], Awaitable[None]] | None = None

    def set_event_sink(
        self,
        sink: Callable[[ProjectionEvent], Awaitable[None]] | None,
    ) -> None:
        self._event_sink = sink

    async def ensure_snapshot(self) -> ProjectionEvent | None:
        """Relee el proveedor y publica sólo cuando el estado cambió.

        La primera llamada fuerza el snapshot inicial. Las siguientes vuelven a consultar
        el foco para que una reconexión del panel pueda recuperar dispositivos que estaban
        temporalmente fuera de línea, sin emitir eventos duplicados si nada cambió.
        """
        async with self._bootstrap_lock:
            return await self.refresh(force=not self._bootstrapped)

    async def refresh(self, *, force: bool = False) -> ProjectionEvent | None:
        states = await self._lights.snapshot(sorted(self._allowed))
        async with self._projection_lock:
            changed = force or self._projection_changed(states)
            self._merge(states)
            self._bootstrapped = True
            if not changed:
                return None
            payload = self._projection_payload()
            fingerprint = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            event = self._events.append(
                EventDraft("home.entity.changed", "home", payload),
                f"home:snapshot:{fingerprint}",
            )
        await self._emit(event)
        return event

    async def execute(
        self,
        source: str,
        command: FastCommand,
        *,
        expected_revision: int | None = None,
    ) -> LightCommandResult:
        try:
            validate_fast_command(command, self._allowed)
        except PolicyError as error:
            raise LightError("policy_rejected", str(error)) from error
        idempotency_key = command.idempotency_key or command.request_id
        lock = await self._request_lock(idempotency_key)
        async with lock:
            fingerprint = self._fingerprint(source, command, expected_revision)
            try:
                record = self._audit.claim(
                    idempotency_key,
                    command.request_id,
                    fingerprint,
                    source,
                    command.entity_id,
                    command.action,
                )
            except LightConflict:
                raise
            if record.status == "verified":
                return LightCommandResult(self._event_from_record(record), True)
            if record.status in {"failed", "ambiguous"}:
                raise LightError(
                    record.error_code or "internal_error",
                    record.error_message or "El comando anterior falló",
                    replayed=True,
                )
            if (
                record.status == "accepted"
                and record.replayed
                and command.action == "toggle"
            ):
                self._audit.failed(
                    idempotency_key,
                    "conflict",
                    "No repito un toggle cuya ejecución anterior quedó ambigua",
                    ambiguous=True,
                )
                raise LightError(
                    "conflict",
                    "No repito un toggle cuya ejecución anterior quedó ambigua",
                    replayed=True,
                )
            await self.ensure_snapshot()
            entity_lock = self._entity_locks[command.entity_id]
            async with entity_lock:
                current = self._cache.get(command.entity_id)
                if expected_revision is not None and (
                    current is None or current.revision != expected_revision
                ):
                    return self._fail(
                        idempotency_key,
                        "conflict",
                        "La revisión esperada de la luz ya cambió",
                    )
                try:
                    states = await self._lights.execute(command)
                except (RuntimeError, ValueError) as error:
                    return self._fail(
                        idempotency_key,
                        "provider_unavailable",
                        str(error),
                    )
            async with self._projection_lock:
                self._merge(states)
                payload = self._projection_payload(command.request_id)
                self._audit.verified(idempotency_key, payload)
                event = self._events.append(
                    EventDraft(
                        "home.entity.changed",
                        "home",
                        payload,
                        correlation_id=command.request_id,
                        causation_id=command.request_id,
                    ),
                    f"light:{idempotency_key}:verified",
                )
            await self._emit(event)
            return LightCommandResult(event, False)

    def cached_states(self) -> tuple[DeviceState, ...]:
        return tuple(self._cache[key] for key in sorted(self._cache))

    def _fail(self, idempotency_key: str, code: str, message: str) -> LightCommandResult:
        self._audit.failed(idempotency_key, code, message)
        raise LightError(code, message)

    def _event_from_record(self, record: LightAuditRecord) -> ProjectionEvent:
        if record.result is None:
            raise LightError("internal_error", "El audit trail verificado no contiene resultado")
        return self._events.append(
            EventDraft(
                "home.entity.changed",
                "home",
                record.result,
                correlation_id=record.request_id,
                causation_id=record.request_id,
            ),
            f"light:{record.idempotency_key}:verified",
        )

    async def _request_lock(self, request_id: str) -> asyncio.Lock:
        async with self._request_guard:
            lock = self._request_locks.get(request_id)
            if lock is None:
                lock = asyncio.Lock()
                self._request_locks[request_id] = lock
            self._request_locks.move_to_end(request_id)
            while len(self._request_locks) > self._max_request_locks:
                oldest, candidate = next(iter(self._request_locks.items()))
                if candidate.locked():
                    self._request_locks.move_to_end(oldest)
                    break
                self._request_locks.popitem(last=False)
            return lock

    def _merge(self, states: Sequence[DeviceState]) -> None:
        for state in states:
            if state.entity_id not in self._allowed:
                raise LightError("forbidden", "El adapter devolvió una entidad no autorizada")
            current = self._cache.get(state.entity_id)
            if current is None or state.revision > current.revision:
                self._cache[state.entity_id] = state

    def _projection_changed(self, states: Sequence[DeviceState]) -> bool:
        incoming = {state.entity_id: state.as_wire() for state in states}
        current = {entity_id: state.as_wire() for entity_id, state in self._cache.items()}
        return incoming != current

    async def _emit(self, event: ProjectionEvent) -> None:
        if self._event_sink is not None:
            await self._event_sink(event)

    def _projection_payload(self, request_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "entities": [state.as_wire() for state in self.cached_states()],
            "verified": True,
        }
        if request_id is not None:
            payload["request_id"] = request_id
        return payload

    @staticmethod
    def _fingerprint(
        source: str,
        command: FastCommand,
        expected_revision: int | None,
    ) -> str:
        canonical = json.dumps(
            {
                "action": command.action,
                "brightness": command.brightness,
                "entity_id": command.entity_id,
                "expected_revision": expected_revision,
                "request_id": command.request_id,
                "rgb": command.rgb,
                "source": source,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()
