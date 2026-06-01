from meridian.domain.entities.item import Item


def deduplicate(items: list[Item]) -> list[Item]:
    """Remove duplicates by canonical_url, keeping the first occurrence."""
    seen_canonical: set[str] = set()
    seen_item_ids: set[str] = set()
    result: list[Item] = []
    for item in items:
        if item.canonical_url:
            if item.canonical_url in seen_canonical:
                continue
            seen_canonical.add(item.canonical_url)
        if item.item_id in seen_item_ids:
            continue
        seen_item_ids.add(item.item_id)
        result.append(item)
    return result
