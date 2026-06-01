from enum import Enum


class SourceType(str, Enum):
    MFEED = "mfeed"
    RSS = "rss"
    ATOM = "atom"
    PODCAST = "podcast"
    PLATFORM = "platform"
