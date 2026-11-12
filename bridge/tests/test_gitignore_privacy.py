"""Comprueba que Git ignore secretos locales creados durante la instalación."""

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ignored(path: str) -> bool:
    git = shutil.which("git")
    assert git is not None
    # Rutas fijas de prueba; no se usa un shell ni se ejecuta contenido de entrada.
    result = subprocess.run(  # noqa: S603
        [git, "check-ignore", "--no-index", "--quiet", "--", path],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    assert result.returncode in (0, 1), result.stderr.decode(errors="replace")
    return result.returncode == 0


def test_local_secrets_are_ignored_and_example_is_available() -> None:
    assert ignored("config/private/panel-token.once")
    assert ignored("config/private/server.crt")
    assert ignored(".env.local")
    assert ignored("bridge/.env.production")
    assert not ignored(".env.example")
