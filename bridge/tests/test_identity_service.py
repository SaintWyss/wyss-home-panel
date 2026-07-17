from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from wyss_panel_bridge.adapters.sqlite_identity import SqliteIdentityStore
from wyss_panel_bridge.application.identity_service import IdentityService
from wyss_panel_bridge.domain.identity import IdentityError


def _tokens() -> Iterator[str]:
    yield "panel-token-abcdefghijklmnopqrstuvwxyz0123456789"
    yield "android-token-abcdefghijklmnopqrstuvwxyz0123456789"
    yield "rotated-token-abcdefghijklmnopqrstuvwxyz0123456789"


def _service(path: Path) -> tuple[IdentityService, SqliteIdentityStore]:
    tokens = _tokens()
    store = SqliteIdentityStore(path)
    service = IdentityService(
        store,
        now=lambda: datetime(2026, 7, 17, 20, 0, tzinfo=UTC),
        token_factory=lambda: next(tokens),
    )
    return service, store


def test_pair_creates_independent_least_privilege_identities(tmp_path: Path) -> None:
    service, store = _service(tmp_path / "identities.sqlite3")

    panel_token = service.pair("panel:living", {"panel.read_projection"})
    android_token = service.pair("android:phone", {"android.submit_intent"})

    assert service.authenticate("panel:living", panel_token, "panel.read_projection")
    assert not service.authenticate("panel:living", panel_token, "panel.submit_intent")
    assert service.authenticate("android:phone", android_token, "android.submit_intent")
    assert not service.authenticate("android:phone", panel_token)
    assert {item["client_id"] for item in store.list_redacted()} == {
        "android:phone",
        "panel:living",
    }


def test_rotate_invalidates_old_token_and_revoke_is_immediate(tmp_path: Path) -> None:
    service, store = _service(tmp_path / "identities.sqlite3")
    original = service.pair("panel:living", {"panel.read_projection"})

    rotated = service.rotate("panel:living")

    assert not service.authenticate("panel:living", original)
    assert service.authenticate("panel:living", rotated)
    assert store.get("panel:living") is not None
    assert store.get("panel:living").generation == 2  # type: ignore[union-attr]

    service.revoke("panel:living")

    assert not service.authenticate("panel:living", rotated)
    assert store.get("panel:living").revoked is True  # type: ignore[union-attr]


def test_store_never_persists_or_lists_raw_tokens(tmp_path: Path) -> None:
    database = tmp_path / "identities.sqlite3"
    service, store = _service(database)
    raw_token = service.pair("panel:living", {"panel.read_projection"})

    persisted_bytes = database.read_bytes()
    listing = store.list_redacted()

    assert raw_token.encode() not in persisted_bytes
    assert "token" not in repr(listing).lower()
    assert database.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("client_id", "capabilities"),
    [
        ("invalid", {"panel.read_projection"}),
        ("panel:living", set()),
        ("panel:living", {"panel.admin"}),
    ],
)
def test_pair_rejects_invalid_identity_or_capabilities(
    tmp_path: Path,
    client_id: str,
    capabilities: set[str],
) -> None:
    service, _ = _service(tmp_path / "identities.sqlite3")

    with pytest.raises(IdentityError):
        service.pair(client_id, capabilities)


def test_pair_rejects_duplicate_and_management_requires_known_client(tmp_path: Path) -> None:
    service, _ = _service(tmp_path / "identities.sqlite3")
    service.pair("panel:living", {"panel.read_projection"})

    with pytest.raises(IdentityError, match="ya existe"):
        service.pair("panel:living", {"panel.read_projection"})
    with pytest.raises(IdentityError, match="desconocido"):
        service.rotate("panel:unknown")
    with pytest.raises(IdentityError, match="desconocido"):
        service.revoke("panel:unknown")


def test_corrupt_capability_payload_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "identities.sqlite3"
    service, store = _service(database)
    service.pair("panel:living", {"panel.read_projection"})
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE client_identities SET capabilities_json = ? WHERE client_id = ?",
            ('{"unexpected":true}', "panel:living"),
        )

    with pytest.raises(RuntimeError, match="corrupto"):
        store.get("panel:living")
