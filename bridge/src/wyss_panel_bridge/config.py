from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Yo necesito la variable de entorno {name}")
    return value


def _resolve_env(value: Any) -> Any:
    if isinstance(value, list):
        return [_resolve_env(item) for item in value]
    if not isinstance(value, dict):
        return value
    resolved: dict[str, Any] = {}
    for raw_key, child in value.items():
        key = str(raw_key)
        if key.endswith("_env"):
            key = key.removesuffix("_env")
            if key in value or key in resolved:
                raise RuntimeError(f"Yo recibí una configuración duplicada para {key}")
            resolved[key] = _env(str(child))
        else:
            resolved[key] = _resolve_env(child)
    return resolved


@dataclass(frozen=True, slots=True)
class Settings:
    host: str
    port: int
    certfile: Path
    keyfile: Path
    panel_id: str
    panel_token_sha256: str
    allowed_entities: frozenset[str]
    primary_entity: str
    provider: str
    provider_config: dict[str, Any]
    wyss_url: str
    wyss_token: str
    v2_enabled: bool = False
    v2_identity_db: Path = Path("bridge/data/identities.sqlite3")
    v2_event_db: Path = Path("bridge/data/events.sqlite3")
    v2_projection_db: Path = Path("bridge/data/projections.sqlite3")
    v2_light_audit_db: Path = Path("bridge/data/light-audit.sqlite3")
    v2_rate_limit: int = 12
    v2_heartbeat_seconds: float = 12.0
    v2_snapshot_fallback: bool = False
    v2_lights_enabled: bool = False
    v2_conversation_enabled: bool = False
    v2_conversation_streaming: bool = True

    @classmethod
    def load(cls, path: Path) -> Settings:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
        bridge = raw["bridge"]
        panel = raw["panel"]
        devices = raw["devices"]
        wyss = raw["wyss"]
        v2 = raw.get("protocol_v2", {})
        provider = str(devices["provider"])
        provider_config = _resolve_env(dict(raw[provider]))
        if not isinstance(provider_config, dict):
            raise RuntimeError("Yo recibí una configuración de proveedor inválida")
        return cls(
            host=str(bridge.get("host", "0.0.0.0")),
            port=int(bridge.get("port", 8443)),
            certfile=Path(bridge["certfile"]),
            keyfile=Path(bridge["keyfile"]),
            panel_id=str(panel["id"]),
            panel_token_sha256=str(panel["token_sha256"]),
            allowed_entities=frozenset(str(item) for item in panel["allowed_entities"]),
            primary_entity=str(panel["primary_entity"]),
            provider=provider,
            provider_config=provider_config,
            wyss_url=str(wyss["url"]).rstrip("/"),
            wyss_token=_env(str(wyss["token_env"])),
            v2_enabled=bool(v2.get("enabled", False)),
            v2_identity_db=Path(v2.get("identity_db", "bridge/data/identities.sqlite3")),
            v2_event_db=Path(v2.get("event_db", "bridge/data/events.sqlite3")),
            v2_projection_db=Path(v2.get("projection_db", "bridge/data/projections.sqlite3")),
            v2_light_audit_db=Path(v2.get("light_audit_db", "bridge/data/light-audit.sqlite3")),
            v2_rate_limit=int(v2.get("rate_limit", 12)),
            v2_heartbeat_seconds=float(v2.get("heartbeat_seconds", 12.0)),
            v2_snapshot_fallback=bool(v2.get("snapshot_fallback", False)),
            v2_lights_enabled=bool(v2.get("lights_enabled", False)),
            v2_conversation_enabled=bool(v2.get("conversation_enabled", False)),
            v2_conversation_streaming=bool(v2.get("conversation_streaming", True)),
        )
