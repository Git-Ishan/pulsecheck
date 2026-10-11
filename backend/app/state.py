from dataclasses import dataclass


@dataclass
class Transition:
    status: str
    consecutive_failures: int
    event: str | None  # "went_down", "recovered", or None


def next_state(
    status: str, failures: int, healthy: bool, threshold: int, stale: bool = False
) -> Transition:
    if stale:
        failures = 0  # the old streak is too old to count as evidence

    if healthy:
        event = "recovered" if status == "DOWN" else None
        return Transition("UP", 0, event)

    failures += 1
    if failures >= threshold:
        event = "went_down" if status != "DOWN" else None
        return Transition("DOWN", failures, event)

    return Transition(status, failures, None)
