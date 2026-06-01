from dataclasses import dataclass

from meridian.domain.value_objects.source_type import SourceType

UNSET_ID = 0


@dataclass(frozen=True, slots=True)
class Feed:
    url: str
    source_type: SourceType
    id: int = UNSET_ID
    platform_id: str | None = None
    rss_fallback_url: str | None = None
    filter_expr: str | None = None
    title: str | None = None
    description: str | None = None
    icon: str | None = None
    language: str | None = None

    def __post_init__(self) -> None:
        if not self.url.startswith("https://"):
            raise ValueError(f"Feed URL must use HTTPS: {self.url}")
        if self.source_type == SourceType.PLATFORM and self.platform_id is None:
            raise ValueError("Platform source type requires platform_id")

    def is_saved(self) -> bool:
        return self.id != UNSET_ID

    def with_metadata(
        self,
        title: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        language: str | None = None,
    ) -> "Feed":
        return Feed(
            url=self.url,
            source_type=self.source_type,
            id=self.id,
            platform_id=self.platform_id,
            rss_fallback_url=self.rss_fallback_url,
            filter_expr=self.filter_expr,
            title=title,
            description=description,
            icon=icon,
            language=language,
        )
