"""AppController: the feed list leaving and re-entering the application.

Export writes the versioned JSON envelope; import has to survive whatever
comes back, which is why the malformed cases outnumber the happy one.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tests.ui.bridge_dtos import feed_dto, make_controller


class TestImportExport:
    def setup_method(self):
        self.sub_svc = MagicMock()
        self.item_svc = MagicMock()
        self.discovery_svc = MagicMock()
        self.discovery_svc.search = AsyncMock(return_value=[])

    def test_export_feeds(self, qapp):
        feeds = [feed_dto(1), feed_dto(2)]
        self.sub_svc.list_feeds.return_value = feeds
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        controller.exportFeeds(tmp.as_uri())
        data = json.loads(tmp.read_text())
        assert data["version"] == 1
        assert len(data["feeds"]) == 2
        tmp.unlink()

    def test_export_feeds_write_error_emits_signal(self, qapp):
        self.sub_svc.list_feeds.return_value = [feed_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.exportFeeds("file:///nonexistent_dir/out.json")
        assert len(errors) == 1

    def test_import_feeds(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        data = {
            "version": 1,
            "feeds": [
                {
                    "url": "https://example.com/feed/1",
                    "source_type": "rss",
                    "title": "Feed One",
                },
                {
                    "url": "https://example.com/feed/2",
                    "source_type": "atom",
                    "title": None,
                },
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        assert self.sub_svc.subscribe.call_count == 2
        tmp.unlink()

    def test_import_feeds_skips_bad_url(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.sub_svc.subscribe.side_effect = ValueError("bad url")
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        data = {
            "version": 1,
            "feeds": [{"url": "https://example.com/feed", "source_type": "rss"}],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        tmp.unlink()

    def test_import_feeds_skips_empty_url(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        data = {
            "version": 1,
            "feeds": [{"url": "", "source_type": "rss"}, {"url": "   "}],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        self.sub_svc.subscribe.assert_not_called()
        tmp.unlink()

    def test_import_feeds_bad_file_emits_error(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.importFeeds("file:///nonexistent/path.json")
        assert len(errors) == 1
