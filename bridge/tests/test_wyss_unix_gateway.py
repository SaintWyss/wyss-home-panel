from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from wyss_panel_bridge.adapters.wyss import WyssUnixGateway
from wyss_panel_bridge.domain.models import RiskLevel


class UnixRpcStub:
    def __init__(self, socket_path: Path, results: list[dict[str, object]]) -> None:
        self.socket_path = socket_path
        self.results = results
        self.requests: list[dict[str, Any]] = []

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        request = json.loads(await reader.readline())
        assert isinstance(request, dict)
        self.requests.append(request)
        result = self.results.pop(0)
        writer.write(
            json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}).encode() + b"\n"
        )
        await writer.drain()
        writer.close()
        await writer.wait_closed()


@pytest.fixture
async def unix_stub(tmp_path: Path) -> AsyncIterator[UnixRpcStub]:
    stub = UnixRpcStub(
        tmp_path / "wyss-home.sock",
        [
            {
                "outcome": "pending",
                "pending_id": "pending:1",
                "risk": "B",
                "summary": "Mover archivo",
                "steps": [
                    {
                        "description": "file.move",
                        "target": "/home/owner/a",
                        "parameters": {"destination": "/home/owner/b"},
                    }
                ],
                "expires_in_ms": 30_000,
                "revision": 4,
            },
            {
                "outcome": "resolved",
                "status": "verified",
                "message": "Plan ejecutado",
                "policy_reevaluated": True,
                "revision": 5,
            },
            {
                "outcome": "already_resolved",
                "message": "El plan ya fue resuelto",
                "policy_reevaluated": False,
                "revision": 5,
            },
        ],
    )
    server = await asyncio.start_unix_server(stub.handle, stub.socket_path)
    try:
        yield stub
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_unix_gateway_maps_home_contract_without_http(unix_stub: UnixRpcStub) -> None:
    gateway = WyssUnixGateway(unix_stub.socket_path)

    turn = await gateway.submit_turn("request:1", "Mové el archivo", "panel:living", "text")
    assert turn.plan is not None
    assert turn.plan.risk == RiskLevel.B
    assert turn.plan.revision == 4
    assert turn.plan.steps[0].parameters == {"destination": "/home/owner/b"}

    result = await gateway.confirm_turn("pending:1", True, "s", 4, "panel:living")
    assert result.state == "verified"
    assert result.policy_reevaluated is True
    duplicate = await gateway.confirm_turn("pending:1", True, "s", 4, "android:phone")
    assert duplicate.outcome == "already_resolved"

    intent_request, answer_request, duplicate_request = unix_stub.requests
    assert intent_request["method"] == "home.intent"
    assert intent_request["params"]["message_id"].startswith("intent:")
    assert intent_request["params"] | {"message_id": "stable"} == {
        "message_id": "stable",
        "request_id": "request:1",
        "source": "panel:living",
        "text": "Mové el archivo",
        "input": "text",
    }
    assert answer_request["method"] == "home.plan.answer"
    assert answer_request["params"]["confirmation"] == "s"
    assert answer_request["params"]["expected_revision"] == 4
    assert answer_request["id"] != duplicate_request["id"]


@pytest.mark.asyncio
async def test_unix_gateway_fails_closed_without_exposing_transport_error(tmp_path: Path) -> None:
    gateway = WyssUnixGateway(tmp_path / "missing.sock", timeout_seconds=0.1)

    with pytest.raises(RuntimeError) as captured:
        await gateway.submit_turn("request:2", "hola", "panel:living")

    assert "missing.sock" not in str(captured.value)


@pytest.mark.asyncio
async def test_legacy_answer_preserves_c_risk_and_authority_revision(tmp_path: Path) -> None:
    stub = UnixRpcStub(
        tmp_path / "wyss-home.sock",
        [
            {
                "outcome": "resolved",
                "status": "verified",
                "policy_reevaluated": True,
                "revision": 8,
            }
        ],
    )
    server = await asyncio.start_unix_server(stub.handle, stub.socket_path)
    try:
        await WyssUnixGateway(stub.socket_path).answer_plan("pending:c", True, int(RiskLevel.C), 7)
    finally:
        server.close()
        await server.wait_closed()

    params = stub.requests[0]["params"]
    assert params["confirmation"] == "CONFIRMAR"
    assert params["expected_revision"] == 7
