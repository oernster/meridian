from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from meridian.application.interfaces.item_repository import ItemRepository
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import (
    Author, Caption, Chapter, ContentRating, GeoRestriction,
    ItemSource, Media, Paywall, Series, Thumbnail, Transcript,
)
from meridian.infrastructure.db.orm_models import ItemRow


class SqliteItemRepository(ItemRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, item: Item) -> Item:
        with self._session_factory() as session:
            row = self._to_row(item)
            session.add(row)
            session.commit()
            return self._to_entity(row)

    def save_many(self, items: list[Item]) -> list[Item]:
        with self._session_factory() as session:
            rows = [self._to_row(i) for i in items]
            session.add_all(rows)
            session.commit()
            return [self._to_entity(r) for r in rows]

    def get_by_id(self, item_id: int) -> Item | None:
        with self._session_factory() as session:
            row = session.get(ItemRow, item_id)
            return self._to_entity(row) if row else None

    def list_by_feed(self, feed_id: int) -> list[Item]:
        with self._session_factory() as session:
            rows = (
                session.query(ItemRow)
                .filter_by(feed_id=feed_id)
                .order_by(ItemRow.published.desc())
                .all()
            )
            return [self._to_entity(r) for r in rows]

    def mark_read(self, item_id: int, read_at: datetime) -> None:
        with self._session_factory() as session:
            row = session.get(ItemRow, item_id)
            if row is not None:
                row.is_read = True
                row.read_at = read_at
                session.commit()

    def mark_all_read(self, feed_id: int, read_at: datetime) -> None:
        with self._session_factory() as session:
            session.query(ItemRow).filter_by(feed_id=feed_id, is_read=False).update(
                {"is_read": True, "read_at": read_at}
            )
            session.commit()

    def unread_count(self, feed_id: int) -> int:
        with self._session_factory() as session:
            return (
                session.query(ItemRow)
                .filter_by(feed_id=feed_id, is_read=False)
                .count()
            )

    def exists(self, feed_id: int, item_id_uri: str) -> bool:
        with self._session_factory() as session:
            return (
                session.query(ItemRow)
                .filter_by(feed_id=feed_id, item_id=item_id_uri)
                .count()
                > 0
            )

    def _to_row(self, item: Item) -> ItemRow:
        return ItemRow(
            feed_id=item.feed_id,
            item_id=item.item_id,
            type=item.type.value,
            title=item.title,
            url=item.url,
            published=item.published,
            updated=item.updated,
            description=item.description,
            language=item.language,
            duration=item.duration,
            canonical_url=item.canonical_url,
            preview_url=item.preview_url,
            license_id=item.license,
            live_status=item.live_status,
            scheduled_start=item.scheduled_start,
            expires=item.expires,
            is_read=item.is_read,
            authors=[{"name": a.name, "url": a.url, "avatar": a.avatar} for a in item.authors] or None,
            tags=list(item.tags) or None,
            media=[{
                "url": m.url, "mime_type": m.mime_type, "size_bytes": m.size_bytes,
                "duration": m.duration, "width": m.width, "height": m.height,
                "bitrate_kbps": m.bitrate_kbps, "role": m.role,
                "quality_label": m.quality_label,
            } for m in item.media] or None,
            thumbnail=[{"url": t.url, "width": t.width, "height": t.height} for t in item.thumbnail] or None,
            chapters=[{
                "title": c.title, "start_seconds": c.start_seconds,
                "end_seconds": c.end_seconds, "image_url": c.image_url,
            } for c in item.chapters] or None,
            captions=[{
                "url": c.url, "mime_type": c.mime_type,
                "language": c.language, "label": c.label,
            } for c in item.captions] or None,
            transcript={"url": item.transcript.url, "mime_type": item.transcript.mime_type, "language": item.transcript.language} if item.transcript else None,
            series={"id": item.series.id, "title": item.series.title, "episode_number": item.series.episode_number, "season_number": item.series.season_number, "total_episodes": item.series.total_episodes} if item.series else None,
            content_rating={"rating": item.content_rating.rating, "system": item.content_rating.system, "descriptors": list(item.content_rating.descriptors), "spoiler": item.content_rating.spoiler} if item.content_rating else None,
            geo_restriction={"type": item.geo_restriction.type, "regions": list(item.geo_restriction.regions)} if item.geo_restriction else None,
            paywall={"paywalled": item.paywall.paywalled, "preview_available": item.paywall.preview_available} if item.paywall else None,
            source={"type": item.source.type, "feed_url": item.source.feed_url, "feed_title": item.source.feed_title} if item.source else None,
        )

    def _to_entity(self, row: ItemRow) -> Item:
        authors = tuple(
            Author(name=a["name"], url=a.get("url"), avatar=a.get("avatar"))
            for a in (row.authors or [])
        )
        media = tuple(
            Media(
                url=m["url"], mime_type=m["mime_type"],
                size_bytes=m.get("size_bytes"), duration=m.get("duration"),
                width=m.get("width"), height=m.get("height"),
                bitrate_kbps=m.get("bitrate_kbps"),
                role=m.get("role", "primary"),
                quality_label=m.get("quality_label"),
            )
            for m in (row.media or [])
        )
        thumbnail = tuple(
            Thumbnail(url=t["url"], width=t.get("width"), height=t.get("height"))
            for t in (row.thumbnail or [])
        )
        chapters = tuple(
            Chapter(
                title=c["title"], start_seconds=c["start_seconds"],
                end_seconds=c.get("end_seconds"), image_url=c.get("image_url"),
            )
            for c in (row.chapters or [])
        )
        captions = tuple(
            Caption(url=c["url"], mime_type=c["mime_type"], language=c["language"], label=c.get("label"))
            for c in (row.captions or [])
        )
        tr = row.transcript
        transcript = Transcript(url=tr["url"], mime_type=tr["mime_type"], language=tr.get("language")) if tr else None
        s = row.series
        series = Series(id=s["id"], title=s["title"], episode_number=s.get("episode_number"), season_number=s.get("season_number"), total_episodes=s.get("total_episodes")) if s else None
        cr = row.content_rating
        content_rating = ContentRating(rating=cr["rating"], system=cr.get("system"), descriptors=tuple(cr.get("descriptors", [])), spoiler=cr.get("spoiler", False)) if cr else None
        gr = row.geo_restriction
        geo_restriction = GeoRestriction(type=gr["type"], regions=tuple(gr["regions"])) if gr else None
        pw = row.paywall
        paywall = Paywall(paywalled=pw["paywalled"], preview_available=pw.get("preview_available", False)) if pw else None
        src = row.source
        source = ItemSource(type=src["type"], feed_url=src["feed_url"], feed_title=src.get("feed_title")) if src else None
        return Item(
            id=row.id,
            feed_id=row.feed_id,
            item_id=row.item_id,
            type=ItemType.from_str(row.type),
            title=row.title,
            url=row.url,
            published=row.published,
            updated=row.updated,
            description=row.description,
            language=row.language,
            duration=row.duration,
            canonical_url=row.canonical_url,
            preview_url=row.preview_url,
            license=row.license_id,
            live_status=row.live_status,
            scheduled_start=row.scheduled_start,
            expires=row.expires,
            is_read=row.is_read,
            authors=authors,
            tags=tuple(row.tags or []),
            media=media,
            thumbnail=thumbnail,
            chapters=chapters,
            captions=captions,
            transcript=transcript,
            series=series,
            content_rating=content_rating,
            geo_restriction=geo_restriction,
            paywall=paywall,
            source=source,
        )
