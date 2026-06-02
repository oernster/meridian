from meridian.domain.value_objects.source_type import SourceType


def infer_source_type(url: str) -> SourceType:
    lower = url.lower().rstrip("/")
    if lower.endswith(".json") or "mmsp" in lower:
        return SourceType.MFEED
    if lower.endswith(".atom"):
        return SourceType.ATOM
    if "youtube.com" in lower:
        return SourceType.ATOM
    if "podcast" in lower:
        return SourceType.PODCAST
    return SourceType.RSS
