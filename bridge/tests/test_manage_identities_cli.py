from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from wyss_panel_bridge.adapters.sqlite_identity import SqliteIdentityStore
from wyss_panel_bridge.application.identity_service import IdentityService

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "tools/manage_identities.py"


def _run(database: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - ejecutable fijo y argumentos sin shell
        [sys.executable, str(SCRIPT), "--db", str(database), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_pair_list_rotate_and_revoke_without_token_leak(tmp_path: Path) -> None:
    database = tmp_path / "identities.sqlite3"
    paired = _run(
        database,
        "pair",
        "--client-id",
        "panel:living",
        "--capability",
        "panel.read_projection",
    )
    assert paired.returncode == 0
    first = json.loads(paired.stdout)
    assert first["generation"] == 1
    assert len(first["token"]) >= 32

    listed = _run(database, "list")
    assert listed.returncode == 0
    assert "token" not in listed.stdout.lower()
    assert json.loads(listed.stdout)[0]["client_id"] == "panel:living"

    rotated = _run(database, "rotate", "--client-id", "panel:living")
    assert rotated.returncode == 0
    second = json.loads(rotated.stdout)
    assert second["generation"] == 2
    assert second["token"] != first["token"]
    service = IdentityService(SqliteIdentityStore(database))
    assert not service.authenticate("panel:living", first["token"])
    assert service.authenticate("panel:living", second["token"])

    revoked = _run(database, "revoke", "--client-id", "panel:living")
    assert revoked.returncode == 0
    assert json.loads(revoked.stdout) == {"client_id": "panel:living", "revoked": True}
    assert not service.authenticate("panel:living", second["token"])


def test_cli_fails_closed_for_unknown_client(tmp_path: Path) -> None:
    result = _run(
        tmp_path / "identities.sqlite3",
        "rotate",
        "--client-id",
        "panel:unknown",
    )

    assert result.returncode == 2
    assert json.loads(result.stdout) == {"error": "client_id desconocido"}
