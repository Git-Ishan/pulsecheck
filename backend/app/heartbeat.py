from dataclasses import dataclass
from datetime import datetime

HEALTHY = {"ok", "starting"}


@dataclass
class HeartbeatState:
    started_at: datetime | None = None
    last_cycle_finished_at: datetime | None = None
    cycles_completed: int = 0


state = HeartbeatState()


def reset() -> None:
    state.started_at = None
    state.last_cycle_finished_at = None
    state.cycles_completed = 0


def mark_started(now: datetime) -> None:
    state.started_at = now


def mark_cycle_finished(now: datetime) -> None:
    state.last_cycle_finished_at = now
    state.cycles_completed += 1


def evaluate(
    now: datetime,
    started_at: datetime | None,
    last_cycle_finished_at: datetime | None,
    task_alive: bool,
    max_age_seconds: float,
) -> str:
    if not task_alive:
        return "stopped"
    reference = last_cycle_finished_at or started_at
    if reference is None:
        return "not_started"
    if (now - reference).total_seconds() > max_age_seconds:
        return "stalled"
    return "ok" if last_cycle_finished_at is not None else "starting"
