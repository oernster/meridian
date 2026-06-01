from enum import Enum


class ItemType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    ARTICLE = "article"
    IMAGE = "image"
    SHORT = "short"
    DOCUMENT = "document"
    GALLERY = "gallery"
    EVENT = "event"
    RELEASE = "release"
    NEWSLETTER = "newsletter"
    COURSE = "course"
    LIVESTREAM = "livestream"

    @classmethod
    def from_str(cls, value: str) -> "ItemType":
        try:
            return cls(value)
        except ValueError:
            return cls.ARTICLE
