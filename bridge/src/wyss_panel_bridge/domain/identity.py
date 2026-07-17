"""Identidad de cliente v2 sin persistencia ni transporte."""

from __future__ import annotations

import re
from dataclasses import dataclass

CLIENT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{2,63}:[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ALLOWED_CAPABILITIES = frozenset(
    {
        "panel.read_projection",
        "panel.light.fast",
        "panel.submit_intent",
        "panel.answer_plan",
        "android.submit_intent",
        "android.answer_plan",
        "android.voice",
        "pc.submit_intent",
        "pc.answer_plan",
        "pc.voice",
        "edge.device.execute",
        "edge.publish_state",
    }
)


class IdentityError(ValueError):
    """Fallo seguro de pairing, autenticación o revocación."""


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    client_id: str
    token_sha256: str
    capabilities: frozenset[str]
    generation: int
    revoked: bool
    updated_at: str
