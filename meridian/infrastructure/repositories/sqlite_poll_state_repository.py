from sqlalchemy.orm import Session, sessionmaker

from meridian.application.interfaces.poll_state_repository import (
    PollState,
    PollStateRepository,
)
from meridian.infrastructure.db.orm_models import PollStateRow


class SqlitePollStateRepository(PollStateRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self, feed_id: int) -> PollState:
        with self._session_factory() as session:
            row = session.get(PollStateRow, feed_id)
            if row is None:
                return PollState(feed_id=feed_id)
            return PollState(
                feed_id=row.feed_id,
                last_polled=row.last_polled,
                next_poll=row.next_poll,
                etag=row.etag,
                last_modified=row.last_modified,
                backoff_until=row.backoff_until,
                moved_to=row.moved_to,
                deprecated=row.deprecated,
                deprecated_reason=row.deprecated_reason,
            )

    def save(self, state: PollState) -> None:
        with self._session_factory() as session:
            row = session.get(PollStateRow, state.feed_id)
            if row is None:
                row = PollStateRow(feed_id=state.feed_id)
                session.add(row)
            row.last_polled = state.last_polled
            row.next_poll = state.next_poll
            row.etag = state.etag
            row.last_modified = state.last_modified
            row.backoff_until = state.backoff_until
            row.moved_to = state.moved_to
            row.deprecated = state.deprecated
            row.deprecated_reason = state.deprecated_reason
            session.commit()
