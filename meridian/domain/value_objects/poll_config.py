from dataclasses import dataclass

POLL_FLOOR_SECONDS = 300


@dataclass(frozen=True, slots=True)
class PollConfig:
    min_interval_seconds: int = POLL_FLOOR_SECONDS
    recommended_interval_seconds: int | None = None
    ttl_seconds: int | None = None

    def __post_init__(self) -> None:
        if self.min_interval_seconds < POLL_FLOOR_SECONDS:
            object.__setattr__(self, "min_interval_seconds", POLL_FLOOR_SECONDS)

    @property
    def effective_interval(self) -> int:
        return max(self.min_interval_seconds, POLL_FLOOR_SECONDS)
