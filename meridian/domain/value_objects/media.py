from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Author:
    name: str
    url: str | None = None
    avatar: str | None = None


@dataclass(frozen=True, slots=True)
class Media:
    url: str
    mime_type: str
    size_bytes: int | None = None
    duration: int | None = None
    width: int | None = None
    height: int | None = None
    bitrate_kbps: int | None = None
    role: str = "primary"
    quality_label: str | None = None


@dataclass(frozen=True, slots=True)
class Thumbnail:
    url: str
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, slots=True)
class Chapter:
    title: str
    start_seconds: int
    end_seconds: int | None = None
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class Transcript:
    url: str
    mime_type: str
    language: str | None = None


@dataclass(frozen=True, slots=True)
class Caption:
    url: str
    mime_type: str
    language: str
    label: str | None = None


@dataclass(frozen=True, slots=True)
class Series:
    id: str
    title: str
    episode_number: int | None = None
    season_number: int | None = None
    total_episodes: int | None = None


@dataclass(frozen=True, slots=True)
class ContentRating:
    rating: str
    system: str | None = None
    descriptors: tuple[str, ...] = ()
    spoiler: bool = False


@dataclass(frozen=True, slots=True)
class GeoRestriction:
    type: str
    regions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Paywall:
    paywalled: bool
    preview_available: bool = False


@dataclass(frozen=True, slots=True)
class ItemSource:
    type: str
    feed_url: str
    feed_title: str | None = None
