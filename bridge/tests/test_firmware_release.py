from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from wyss_panel_bridge.operations.firmware_release import (
    HEALTH_COMPONENTS,
    FirmwareReleaseError,
    OtaHealthLedger,
    create_manifest,
    verify_manifest,
)

BOARD = "waveshare-esp32-s3-touch-lcd-7"


def _keys(path: Path) -> tuple[Path, Path]:
    executable = shutil.which("openssl")
    if executable is None:
        pytest.skip("OpenSSL no disponible")
    private = path / "release-private.pem"
    public = path / "release-public.pem"
    subprocess.run(  # noqa: S603 - fixture local sin shell
        [executable, "genpkey", "-algorithm", "ED25519", "-out", str(private)],
        check=True,
        capture_output=True,
    )
    subprocess.run(  # noqa: S603 - fixture local sin shell
        [
            executable,
            "pkey",
            "-in",
            str(private),
            "-pubout",
            "-out",
            str(public),
        ],
        check=True,
        capture_output=True,
    )
    return private, public


def test_ed25519_manifest_accepts_exact_image_and_rejects_corruption(
    tmp_path: Path,
) -> None:
    private, public = _keys(tmp_path)
    firmware = tmp_path / "firmware.bin"
    firmware.write_bytes(b"esp32-image-v2" * 100)
    manifest = create_manifest(
        firmware,
        private,
        version="2.0.0",
        board_id=BOARD,
        build_commit="a" * 40,
    )

    verified = verify_manifest(manifest, firmware, public, expected_board_id=BOARD)

    assert verified["firmware_size"] == firmware.stat().st_size
    assert verified["signature"]["algorithm"] == "ed25519"

    firmware.write_bytes(firmware.read_bytes() + b"corrupt")
    with pytest.raises(FirmwareReleaseError, match="checksum"):
        verify_manifest(manifest, firmware, public, expected_board_id=BOARD)


def test_manifest_rejects_tampering_wrong_board_and_wrong_signer(tmp_path: Path) -> None:
    private, public = _keys(tmp_path)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    _, other_public = _keys(other_dir)
    firmware = tmp_path / "firmware.bin"
    firmware.write_bytes(b"authorized-image")
    manifest = create_manifest(
        firmware,
        private,
        version="2.0.0",
        board_id=BOARD,
        build_commit="b" * 40,
    )

    changed = {**manifest, "version": "9.9.9"}
    with pytest.raises(FirmwareReleaseError, match="firma"):
        verify_manifest(changed, firmware, public, expected_board_id=BOARD)
    with pytest.raises(FirmwareReleaseError, match="placa"):
        verify_manifest(manifest, firmware, public, expected_board_id="wrong-board")
    with pytest.raises(FirmwareReleaseError, match="firma"):
        verify_manifest(manifest, firmware, other_public, expected_board_id=BOARD)


def _manifest(version: str, digest: str) -> dict[str, object]:
    return {
        "version": version,
        "firmware_sha256": digest,
        "build_commit": "c" * 40,
    }


def test_health_ledger_promotes_only_after_every_component_and_is_idempotent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ota-health.json"
    ledger = OtaHealthLedger(path)
    candidate = _manifest("2.0.0", "d" * 64)
    ledger.stage(candidate)
    ledger.stage(candidate)

    decisions = [ledger.record_health(component, True) for component in sorted(HEALTH_COMPONENTS)]

    assert all(decision.action == "wait" for decision in decisions[:-1])
    assert decisions[-1].action == "promote"
    assert OtaHealthLedger(path).recover_interrupted().action == "keep"
    assert path.stat().st_mode & 0o777 == 0o600


def test_health_failure_and_interrupted_boot_both_rollback(tmp_path: Path) -> None:
    path = tmp_path / "ota-health.json"
    ledger = OtaHealthLedger(path)
    ledger.stage(_manifest("2.0.0", "e" * 64))
    failed = ledger.record_health("touch", False)

    assert failed.action == "rollback"
    assert failed.reason == "health_failed:touch"

    ledger.stage(_manifest("2.0.1", "f" * 64))
    interrupted = OtaHealthLedger(path).recover_interrupted()

    assert interrupted.action == "rollback"
    assert interrupted.reason == "interrupted_before_promotion"
