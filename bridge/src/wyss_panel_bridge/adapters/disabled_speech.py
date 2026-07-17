"""Proveedor seguro mientras O-01 no tenga una decisión del operador."""

from __future__ import annotations

from wyss_panel_bridge.domain.voice import VoiceError


class DisabledSpeechGateway:
    async def transcribe(self, _audio: memoryview, _content_type: str) -> str:
        raise VoiceError(
            "provider_unavailable",
            "El motor STT local sigue desactivado hasta cerrar la decisión O-01",
        )
