"""Timers apagados no consultan ni ejecutan un scheduler."""

from __future__ import annotations

from wyss_panel_bridge.domain.timers import TimerError, TimerNotification, TimerSnapshot


class DisabledTimerGateway:
    async def snapshot(self) -> TimerSnapshot:
        raise TimerError("policy_rejected", "Timers están desactivados")


class VolatileTimerStore:
    def load(self) -> TimerSnapshot | None:
        return None

    def save(self, snapshot: TimerSnapshot) -> None:
        del snapshot

    def completion_recorded(self, completion_id: str) -> bool:
        del completion_id
        return False

    def record_completion(self, completion_id: str, timer_id: str) -> None:
        del completion_id, timer_id


class VolatileTimerNotificationOutbox:
    def enqueue(self, notification: TimerNotification) -> None:
        del notification

    def pending(self, limit: int = 128) -> tuple[TimerNotification, ...]:
        del limit
        return ()

    def record_attempt(self, notification_id: str, *, accepted: bool) -> None:
        del notification_id, accepted
