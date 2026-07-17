from __future__ import annotations

import asyncio

import pytest

from wyss_panel_bridge.application.voice_service import VoiceService
from wyss_panel_bridge.domain.voice import VoiceError
from wyss_panel_bridge.ports_v2 import SpeechPort


class Speech:
    def __init__(self, result: str = "Prendé la luz del living") -> None:
        self.result = result
        self.audio = b""
        self.content_type = ""

    async def transcribe(self, audio: memoryview, content_type: str) -> str:
        self.audio = bytes(audio)
        self.content_type = content_type
        return self.result


class FailedSpeech:
    async def transcribe(self, _audio: memoryview, _content_type: str) -> str:
        raise RuntimeError("detalle interno que no debe filtrarse")


class NoiseSpeech:
    async def transcribe(self, _audio: memoryview, _content_type: str) -> str:
        raise VoiceError("noise", "Detecté ruido, pero no una instrucción")


class SlowSpeech:
    async def transcribe(self, _audio: memoryview, _content_type: str) -> str:
        await asyncio.sleep(0.05)
        return "tarde"


@pytest.mark.asyncio
async def test_transcription_is_editable_and_raw_buffer_is_zeroed() -> None:
    speech = Speech()
    service = VoiceService(speech, max_bytes=4096, timeout_seconds=1)
    audio = bytearray(b"audio-efimero")

    result = await service.transcribe(audio, "audio/webm")

    assert result.text == "Prendé la luz del living"
    assert result.retained_audio is False
    assert result.requires_explicit_send is True
    assert speech.audio == b"audio-efimero"
    assert audio == bytearray(len(audio))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("speech", "expected"),
    [
        (Speech("   "), "silence"),
        (NoiseSpeech(), "noise"),
        (FailedSpeech(), "provider_unavailable"),
    ],
)
async def test_recoverable_failures_never_retain_audio(speech: SpeechPort, expected: str) -> None:
    service = VoiceService(speech, max_bytes=4096, timeout_seconds=1)
    audio = bytearray(b"sensible")

    with pytest.raises(VoiceError, match="voz|ruido|disponible") as raised:
        await service.transcribe(audio, "audio/webm")

    assert raised.value.code == expected
    assert audio == bytearray(len(audio))


@pytest.mark.asyncio
async def test_provider_timeout_is_recoverable_and_zeroes_audio() -> None:
    audio = bytearray(b"sensible")
    service = VoiceService(SlowSpeech(), max_bytes=4096, timeout_seconds=0.001)

    with pytest.raises(VoiceError, match="tiempo") as raised:
        await service.transcribe(audio, "audio/ogg")

    assert raised.value.code == "provider_timeout"
    assert audio == bytearray(len(audio))


@pytest.mark.asyncio
async def test_unsupported_or_oversized_audio_is_rejected_before_provider() -> None:
    speech = Speech()
    service = VoiceService(speech, max_bytes=1024, timeout_seconds=1)

    with pytest.raises(VoiceError) as unsupported:
        await service.transcribe(bytearray(b"x"), "audio/mpeg")
    with pytest.raises(VoiceError) as oversized:
        await service.transcribe(bytearray(b"x" * 1025), "audio/webm")

    assert unsupported.value.code == "unsupported_audio"
    assert oversized.value.code == "audio_too_large"
    assert speech.audio == b""
