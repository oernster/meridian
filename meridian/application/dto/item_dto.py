from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AuthorDTO:
    name: str
    url: str | None = None
    avatar: str | None = None


@dataclass(frozen=True, slots=True)
class MediaDTO:
    url: str
    mime_type: str
    role: str = "primary"
    duration: int | None = None
    width: int | None = None
    height: int | None = None
    quality_label: str | None = None


@dataclass(frozen=True, slots=True)
class ItemDTO:
    id: int
    feed_id: int
    item_id: str
    type: str
    title: str
    url: str
    published_iso: str
    description: str | None
    thumbnail_url: str | None
    duration: int | None
    is_read: bool
    language: str | None = None
    live_status: str | None = None
    authors: tuple[AuthorDTO, ...] = ()
    tags: tuple[str, ...] = ()
    media: tuple[MediaDTO, ...] = ()
