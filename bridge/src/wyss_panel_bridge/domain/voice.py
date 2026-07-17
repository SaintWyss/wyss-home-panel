"""Tipos efímeros de voz; el audio crudo nunca es un dato de dominio persistente."""

from __future__ import annotations

from dataclasses import dataclass


class VoiceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class VoiceTranscript:
    text: str
    retained_audio: bool = False
    requires_explicit_send: bool = True
