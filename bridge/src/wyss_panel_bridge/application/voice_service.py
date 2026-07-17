"""Transcripción acotada con borrado best-effort del buffer y sin envío implícito."""

from __future__ import annotations

import asyncio

from wyss_panel_bridge.domain.voice import VoiceError, VoiceTranscript
from wyss_panel_bridge.ports_v2 import SpeechPort

ALLOWED_AUDIO_TYPES = frozenset(
    {"audio/mp4", "audio/ogg", "audio/wav", "audio/webm", "audio/webm;codecs=opus"}
)


class VoiceService:
    def __init__(self, speech: SpeechPort, max_bytes: int, timeout_seconds: float) -> None:
        if max_bytes < 1024 or timeout_seconds <= 0:
            raise ValueError("Configuración de voz inválida")
        self._speech = speech
        self.max_bytes = max_bytes
        self._timeout_seconds = timeout_seconds

    async def transcribe(self, audio: bytearray, content_type: str) -> VoiceTranscript:
        normalized_type = content_type.lower().strip()
        if normalized_type not in ALLOWED_AUDIO_TYPES:
            self._wipe(audio)
            raise VoiceError("unsupported_audio", "El formato de audio no está permitido")
        if not audio:
            raise VoiceError("silence", "No recibí audio para transcribir")
        if len(audio) > self.max_bytes:
            self._wipe(audio)
            raise VoiceError("audio_too_large", "El audio supera el límite permitido")

        try:
            text = await asyncio.wait_for(
                self._speech.transcribe(memoryview(audio), normalized_type),
                timeout=self._timeout_seconds,
            )
            transcript = text.strip()
            if not transcript:
                raise VoiceError("silence", "No detecté voz")
            if len(transcript) > 1000:
                raise VoiceError("transcript_too_large", "La transcripción supera 1.000 caracteres")
            return VoiceTranscript(transcript)
        except TimeoutError as error:
            raise VoiceError("provider_timeout", "El motor de voz no respondió a tiempo") from error
        except VoiceError:
            raise
        except Exception as error:
            raise VoiceError(
                "provider_unavailable", "El motor de voz no está disponible"
            ) from error
        finally:
            self._wipe(audio)

    @staticmethod
    def _wipe(audio: bytearray) -> None:
        audio[:] = b"\x00" * len(audio)
