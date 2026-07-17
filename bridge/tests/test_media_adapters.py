from __future__ import annotations

import httpx
import pytest

from wyss_panel_bridge.adapters.wyss_media import WyssMediaGateway
from wyss_panel_bridge.domain.media import MediaAction, MediaCommand, MediaError


def _command(action: MediaAction = MediaAction.NEXT) -> MediaCommand:
    return MediaCommand("request:1", "spotify:1", action)


@pytest.mark.asyncio
async def test_wyss_media_maps_safe_playback_without_forwarding_oauth() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "linked": True,
                "available": True,
                "playing": True,
                "track_uri": "spotify:track:safe",
                "title": "Canción",
                "artist": "Artista",
                "progress_ms": 12_000,
                "duration_ms": 180_000,
                "favorite": True,
                "device": {
                    "id": "device-safe",
                    "name": "Escritorio",
                    "type": "Computer",
                    "active": True,
                    "restricted": False,
                    "supports_volume": True,
                    "volume": 34,
                },
            },
        )

    gateway = WyssMediaGateway(
        "https://wyss.test",
        "internal-service-secret",
        transport=httpx.MockTransport(handler),
    )
    state = await gateway.execute(_command())

    assert state.title == "Canción"
    assert state.device is not None and state.device.volume == 34
    assert requests[0].url.path == "/api/media/spotify/commands"
    body = requests[0].content.decode()
    assert "internal-service-secret" not in body
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert requests[0].headers["authorization"] == "Bearer internal-service-secret"
    projection = str(state.projection())
    assert "secret" not in projection
    assert "token" not in projection


@pytest.mark.asyncio
async def test_wyss_media_maps_no_active_playback_from_204() -> None:
    gateway = WyssMediaGateway(
        "https://wyss.test",
        "service-token",
        transport=httpx.MockTransport(lambda _request: httpx.Response(204)),
    )

    state = await gateway.state()

    assert state.linked is True
    assert state.available is False
    assert state.error_code == "no_active_playback"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected", "retry_after"),
    [
        (401, "reauthorization_required", None),
        (403, "premium_or_scope_required", None),
        (404, "device_inactive", None),
        (429, "rate_limited", 7),
    ],
)
async def test_wyss_media_maps_provider_failures_without_response_body_leak(
    status: int,
    expected: str,
    retry_after: int | None,
) -> None:
    gateway = WyssMediaGateway(
        "https://wyss.test",
        "service-token",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                status,
                headers={"Retry-After": "7"} if status == 429 else {},
                json={"provider_detail": "must-not-leak", "message": "secret-provider-body"},
            )
        ),
    )

    with pytest.raises(MediaError) as captured:
        await gateway.execute(_command())

    assert captured.value.code == expected
    assert captured.value.retry_after == retry_after
    assert "must-not-leak" not in str(captured.value)
    assert "secret-provider-body" not in str(captured.value)


@pytest.mark.asyncio
async def test_wyss_media_fails_closed_on_malformed_json() -> None:
    gateway = WyssMediaGateway(
        "https://wyss.test",
        "service-token",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, content=b"not-json")),
    )

    with pytest.raises(MediaError, match="media inválida") as captured:
        await gateway.state()

    assert captured.value.code == "provider_unavailable"
