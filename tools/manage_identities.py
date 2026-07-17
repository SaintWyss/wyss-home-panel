#!/usr/bin/env python3
"""Administra identidades v2 sin registrar tokens en claro."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wyss_panel_bridge.adapters.sqlite_identity import SqliteIdentityStore
from wyss_panel_bridge.application.identity_service import IdentityService
from wyss_panel_bridge.domain.identity import IdentityError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="SQLite privado de identidades")
    commands = parser.add_subparsers(dest="command", required=True)

    pair = commands.add_parser("pair", help="Crear una identidad y mostrar el token una vez")
    pair.add_argument("--client-id", required=True)
    pair.add_argument("--capability", action="append", required=True)

    rotate = commands.add_parser("rotate", help="Invalidar el token anterior y emitir uno nuevo")
    rotate.add_argument("--client-id", required=True)

    revoke = commands.add_parser("revoke", help="Revocar inmediatamente una identidad")
    revoke.add_argument("--client-id", required=True)

    commands.add_parser("list", help="Listar identidades sin hashes ni tokens")
    return parser


def _token_result(
    store: SqliteIdentityStore, client_id: str, token: str
) -> dict[str, object]:
    identity = store.get(client_id)
    if identity is None:
        raise RuntimeError("identity store inconsistente")
    return {
        "client_id": client_id,
        "generation": identity.generation,
        "token": token,
        "warning": "guardar ahora; este token no vuelve a mostrarse",
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    store = SqliteIdentityStore(args.db)
    service = IdentityService(store)
    try:
        if args.command == "pair":
            result: object = _token_result(
                store,
                args.client_id,
                service.pair(args.client_id, args.capability),
            )
        elif args.command == "rotate":
            result = _token_result(store, args.client_id, service.rotate(args.client_id))
        elif args.command == "revoke":
            service.revoke(args.client_id)
            result = {"client_id": args.client_id, "revoked": True}
        else:
            result = store.list_redacted()
    except IdentityError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
