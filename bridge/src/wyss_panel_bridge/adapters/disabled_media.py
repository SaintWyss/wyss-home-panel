"""Adapter de media fail-closed para rollback y gate O-07."""

from __future__ import annotations

from wyss_panel_bridge.domain.media import MediaCommand, MediaError, MediaState


class DisabledMediaGateway:
    async def state(self) -> MediaState:
        return MediaState(linked=False, available=False, error_code="module_disabled")

    async def execute(self, command: MediaCommand) -> MediaState:
        del command
        raise MediaError("policy_rejected", "Spotify está desactivado")
