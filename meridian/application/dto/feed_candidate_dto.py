from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedCandidateDTO:
    url: str
    title: str | None
    description: str | None
    favicon_url: str | None
    source_type: str
    is_subscribed: bool = False
