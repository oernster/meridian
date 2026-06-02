from sqlalchemy.orm import Session, sessionmaker

from meridian.application.interfaces.feed_repository import FeedRepository
from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.source_type import SourceType
from meridian.infrastructure.db.orm_models import FeedRow


class SqliteFeedRepository(FeedRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, feed: Feed) -> Feed:
        with self._session_factory() as session:
            if feed.is_saved():
                row = session.get(FeedRow, feed.id)
                if row is None:
                    raise ValueError(f"Feed {feed.id} not found")
                self._update_row(row, feed)
            else:
                row = self._to_row(feed)
                session.add(row)
            session.commit()
            return self._to_entity(row)

    def get_by_id(self, feed_id: int) -> Feed | None:
        with self._session_factory() as session:
            row = session.get(FeedRow, feed_id)
            return self._to_entity(row) if row else None

    def get_by_url(self, url: str) -> Feed | None:
        with self._session_factory() as session:
            row = session.query(FeedRow).filter_by(url=url).first()
            return self._to_entity(row) if row else None

    def list_all(self) -> list[Feed]:
        with self._session_factory() as session:
            rows = session.query(FeedRow).all()
            return [self._to_entity(r) for r in rows]

    def delete(self, feed_id: int) -> None:
        with self._session_factory() as session:
            row = session.get(FeedRow, feed_id)
            if row is not None:
                session.delete(row)
                session.commit()

    def update_filter(self, feed_id: int, filter_expr: str | None) -> None:
        with self._session_factory() as session:
            row = session.get(FeedRow, feed_id)
            if row is not None:
                row.filter_expr = filter_expr
                session.commit()

    def update_title(self, feed_id: int, title: str) -> None:
        with self._session_factory() as session:
            row = session.get(FeedRow, feed_id)
            if row is not None:
                row.title = title
                session.commit()

    def update_url(self, feed_id: int, new_url: str) -> None:
        with self._session_factory() as session:
            row = session.get(FeedRow, feed_id)
            if row is not None:
                row.url = new_url
                session.commit()

    def _to_row(self, feed: Feed) -> FeedRow:
        return FeedRow(
            url=feed.url,
            source_type=feed.source_type.value,
            platform_id=feed.platform_id,
            rss_fallback_url=feed.rss_fallback_url,
            filter_expr=feed.filter_expr,
            title=feed.title,
            description=feed.description,
            icon=feed.icon,
            language=feed.language,
        )

    def _update_row(self, row: FeedRow, feed: Feed) -> None:
        row.title = feed.title
        row.description = feed.description
        row.icon = feed.icon
        row.language = feed.language
        row.filter_expr = feed.filter_expr

    def _to_entity(self, row: FeedRow) -> Feed:
        return Feed(
            id=row.id,
            url=row.url,
            source_type=SourceType(row.source_type),
            platform_id=row.platform_id,
            rss_fallback_url=row.rss_fallback_url,
            filter_expr=row.filter_expr,
            title=row.title,
            description=row.description,
            icon=row.icon,
            language=row.language,
        )
