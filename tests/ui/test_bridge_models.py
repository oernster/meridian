"""The three QAbstractListModels the QML views bind to.

Role numbering is the contract with the QML: a view asks for `Qt.UserRole +
n` and nothing states the mapping but this. The roles are therefore asserted
by number rather than by name.
"""

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO
from meridian.ui.bridge import FeedCandidateModel, FeedListModel, ItemListModel
from tests.ui.bridge_dtos import candidate_dto, feed_dto, item_dto


class TestFeedListModel:
    def test_empty_model(self, qapp):
        model = FeedListModel()
        assert model.rowCount() == 0

    def test_refresh_sets_rows(self, qapp):
        model = FeedListModel()
        model.refresh([feed_dto(1), feed_dto(2)])
        assert model.rowCount() == 2

    def test_data_all_roles(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        model.refresh([feed_dto(1, unread=3)])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) == 1  # feedId
        assert model.data(idx, Qt.UserRole + 1) is not None  # feedUrl
        assert model.data(idx, Qt.UserRole + 2) == "Feed 1"  # feedTitle
        assert model.data(idx, Qt.UserRole + 3) == ""  # feedIcon (None -> "")
        assert model.data(idx, Qt.UserRole + 4) == "mfeed"  # feedSourceType
        assert model.data(idx, Qt.UserRole + 5) == 3  # feedUnreadCount
        assert model.data(idx, Qt.UserRole + 6) == ""  # feedDescription (None -> "")
        assert model.data(idx, Qt.UserRole + 7) == ""  # feedFilterExpr (None -> "")
        assert model.data(idx, 9999) is None  # unknown role

    def test_data_feed_filter_expr_present(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        dto = FeedDTO(
            id=1,
            url="https://example.com/feed/1",
            source_type="mfeed",
            title="Feed 1",
            description=None,
            icon=None,
            language=None,
            filter_expr="type:video",
            unread_count=0,
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 7) == "type:video"

    def test_data_feed_title_fallback_to_url(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        dto = FeedDTO(
            id=1,
            url="https://example.com/feed",
            source_type="mfeed",
            title=None,
            description=None,
            icon=None,
            language=None,
            filter_expr=None,
            unread_count=0,
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 2) == "https://example.com/feed"

    def test_data_invalid_index(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        idx = model.index(99, 0)
        assert model.data(idx, Qt.UserRole + 0) is None

    def test_role_names(self, qapp):
        model = FeedListModel()
        assert b"feedId" in model.roleNames().values()

    def test_remove_rows_by_ids(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        model.refresh([feed_dto(1), feed_dto(2), feed_dto(3)])
        model.remove_rows_by_ids({1, 3})
        assert model.rowCount() == 1
        assert model.data(model.index(0, 0), Qt.UserRole + 0) == 2

    def test_remove_rows_by_ids_unknown_ids_no_op(self, qapp):
        model = FeedListModel()
        model.refresh([feed_dto(1), feed_dto(2)])
        model.remove_rows_by_ids({99})
        assert model.rowCount() == 2


class TestItemListModel:
    def test_empty_model(self, qapp):
        model = ItemListModel()
        assert model.rowCount() == 0

    def test_refresh_sets_rows(self, qapp):
        model = ItemListModel()
        model.refresh([item_dto(1), item_dto(2)])
        assert model.rowCount() == 2

    def test_data_all_roles(self, qapp):
        from PySide6.QtCore import Qt

        from meridian.application.dto.item_dto import MediaDTO

        model = ItemListModel()
        dto = ItemDTO(
            id=1,
            feed_id=1,
            item_id="https://example.com/item/1",
            type="video",
            title="Item 1",
            url="https://example.com/item/1",
            published_iso="2026-01-01T00:00:00+00:00",
            description="A description",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=600,
            is_read=False,
            language="en",
            live_status="live",
            media=(
                MediaDTO(
                    url="https://example.com/video.mp4",
                    mime_type="video/mp4",
                    role="primary",
                ),
            ),
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) == 1
        assert model.data(idx, Qt.UserRole + 1) == "Item 1"
        assert model.data(idx, Qt.UserRole + 2) == "video"
        assert model.data(idx, Qt.UserRole + 3) == "https://example.com/item/1"
        assert "2026" in model.data(idx, Qt.UserRole + 4)
        assert model.data(idx, Qt.UserRole + 5) == "https://example.com/thumb.jpg"
        assert model.data(idx, Qt.UserRole + 6) == 600
        assert model.data(idx, Qt.UserRole + 7) is False
        assert model.data(idx, Qt.UserRole + 8) == "A description"
        assert model.data(idx, Qt.UserRole + 9) == "live"
        assert model.data(idx, Qt.UserRole + 10) == "https://example.com/video.mp4"
        assert model.data(idx, 9999) is None

    def test_data_item_no_media_url(self, qapp):
        from PySide6.QtCore import Qt

        model = ItemListModel()
        model.refresh([item_dto(1)])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 10) == ""

    def test_data_invalid_index(self, qapp):
        from PySide6.QtCore import Qt

        model = ItemListModel()
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) is None

    def test_role_names(self, qapp):
        model = ItemListModel()
        assert b"itemTitle" in model.roleNames().values()


class TestFeedCandidateModel:
    def test_empty_model(self, qapp):
        model = FeedCandidateModel()
        assert model.rowCount() == 0

    def test_refresh_sets_rows(self, qapp):
        model = FeedCandidateModel()
        model.refresh([candidate_dto(), candidate_dto("https://b.com/feed")])
        assert model.rowCount() == 2

    def test_data_all_roles(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        model.refresh([candidate_dto()])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) == "https://example.com/feed"
        assert model.data(idx, Qt.UserRole + 1) == "Feed"
        assert model.data(idx, Qt.UserRole + 2) == "A feed"
        assert model.data(idx, Qt.UserRole + 3) == ""
        assert model.data(idx, Qt.UserRole + 4) == "rss"
        assert model.data(idx, Qt.UserRole + 5) is False
        assert model.data(idx, 9999) is None

    def test_data_title_fallback_to_url(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        dto = FeedCandidateDTO(
            url="https://example.com/feed",
            title=None,
            description=None,
            favicon_url=None,
            source_type="rss",
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 1) == "https://example.com/feed"

    def test_data_invalid_index(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        assert model.data(model.index(99, 0), Qt.UserRole + 0) is None

    def test_role_names(self, qapp):
        model = FeedCandidateModel()
        assert b"candidateUrl" in model.roleNames().values()

    def test_mark_subscribed(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        model.refresh([candidate_dto("https://a.com"), candidate_dto("https://b.com")])
        model.mark_subscribed("https://a.com")
        assert model.data(model.index(0, 0), Qt.UserRole + 5) is True
        assert model.data(model.index(1, 0), Qt.UserRole + 5) is False

    def test_mark_subscribed_unknown_url_no_op(self, qapp):
        model = FeedCandidateModel()
        model.refresh([candidate_dto()])
        model.mark_subscribed("https://nonexistent.com/feed")
        assert model.rowCount() == 1
