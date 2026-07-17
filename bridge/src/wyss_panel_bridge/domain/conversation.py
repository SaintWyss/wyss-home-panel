"""Tipos acotados del funnel conversacional cuya autoridad permanece en Wyss."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from wyss_panel_bridge.domain.models import Plan

TerminalState = Literal["verified", "failed"]


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    text: str
    state: TerminalState
    plan: Plan | None = None


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    text: str
    state: TerminalState
    policy_reevaluated: bool


class ConversationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
