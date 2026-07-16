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

    @classmethod
    def load(cls, path: Path) -> Settings:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
        bridge = raw["bridge"]
        panel = raw["panel"]
        devices = raw["devices"]
        wyss = raw["wyss"]
        provider = str(devices["provider"])
        provider_config = dict(raw[provider])
        for key, value in tuple(provider_config.items()):
            if key.endswith("_env"):
                provider_config[key.removesuffix("_env")] = _env(str(value))
                del provider_config[key]
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
        )

