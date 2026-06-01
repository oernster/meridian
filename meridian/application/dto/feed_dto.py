from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedDTO:
    id: int
    url: str
    source_type: str
    title: str | None
    description: str | None
    icon: str | None
    language: str | None
    filter_expr: str | None
    unread_count: int
    platform_id: str | None = None
    rss_fallback_url: str | None = None
