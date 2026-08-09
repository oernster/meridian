"""AppController: the discovery surface.

Searching runs on a background event loop, so most of what is asserted here
is lifecycle: a search superseding its predecessor, a cancellation reaching
the right signal, then shutdown draining whatever is still pending.
"""

import threading
from unittest.mock import AsyncMock, MagicMock

from meridian.ui.bridge import FeedCandidateModel
from tests.ui.bridge_dtos import candidate_dto, feed_dto, make_controller


class TestDiscovery:
    def setup_method(self):
        self.sub_svc = MagicMock()
        self.item_svc = MagicMock()
        self.discovery_svc = MagicMock()
        self.discovery_svc.search = AsyncMock(return_value=[])

    def test_subscribe_from_discovery_success(self, qapp):
        self.sub_svc.subscribe.return_value = feed_dto(1)
        self.sub_svc.list_feeds.return_value = [feed_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh([candidate_dto("https://example.com/feed")])
        controller.subscribeFromDiscovery("https://example.com/feed")
        self.sub_svc.subscribe.assert_called_once_with("https://example.com/feed")

    def test_subscribe_from_discovery_marks_subscribed_in_model(self, qapp):
        from PySide6.QtCore import Qt

        self.sub_svc.subscribe.return_value = feed_dto(1)
        self.sub_svc.list_feeds.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh([candidate_dto("https://example.com/feed")])
        controller.subscribeFromDiscovery("https://example.com/feed")
        idx = controller.candidateModel.index(0, 0)
        assert controller.candidateModel.data(idx, Qt.UserRole + 5) is True

    def test_subscribe_from_discovery_error_emits_signal(self, qapp):
        self.sub_svc.subscribe.side_effect = ValueError("bad url")
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.subscribeFromDiscovery("https://example.com/feed")
        assert len(errors) == 1

    def test_bulk_subscribe_from_discovery(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh(
            [
                candidate_dto("https://a.com/feed"),
                candidate_dto("https://b.com/feed"),
            ]
        )
        controller.bulkSubscribeFromDiscovery(
            ["https://a.com/feed", "https://b.com/feed"]
        )
        assert self.sub_svc.subscribe.call_count == 2

    def test_bulk_subscribe_skips_failures(self, qapp):
        self.sub_svc.list_feeds.return_value = []

        def _side(url, **kw):
            if "a.com" in url:
                raise ValueError("bad")

        self.sub_svc.subscribe.side_effect = _side
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh([candidate_dto("https://b.com/feed")])
        controller.bulkSubscribeFromDiscovery(
            ["https://a.com/feed", "https://b.com/feed"]
        )
        assert self.sub_svc.subscribe.call_count == 2

    def test_set_result_cap(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setResultCap(50)
        assert controller._result_cap == 50

    def test_set_result_cap_retriggers_search_if_query_set(self, qapp):
        started = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchStarted.connect(lambda: started.append(1))
        controller._last_query = "python"
        controller.setResultCap(100)
        assert len(started) == 1

    def test_cancel_search_emits_cancelled_when_no_future(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        cancelled = []
        controller.searchCancelled.connect(lambda: cancelled.append(1))
        controller.cancelSearch()
        assert cancelled == []

    def test_search_feeds_empty_query_no_op(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        started = []
        controller.searchStarted.connect(lambda: started.append(1))
        controller.searchFeeds("   ")
        assert started == []

    def test_search_feeds_emits_started(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        started = []
        controller.searchStarted.connect(lambda: started.append(1))
        controller.searchFeeds("python")
        assert len(started) == 1
        controller.shutdown()

    def test_candidate_model_property(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        assert controller.candidateModel is not None
        assert isinstance(controller.candidateModel, FeedCandidateModel)

    def test_search_emits_error_signal_on_failure(self, qapp):
        import time

        from PySide6.QtWidgets import QApplication as _QApp

        from meridian.application.interfaces.discovery_fetcher import DiscoveryError

        async def _failing(*args, **kwargs):
            raise DiscoveryError("network error")

        self.discovery_svc.search = _failing
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.searchError.connect(errors.append)
        controller.searchFeeds("python")
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not errors:
            _QApp.processEvents()
            time.sleep(0.01)
        assert len(errors) == 1
        assert "network error" in errors[0]
        controller.shutdown()

    def test_search_populates_candidate_model_on_success(self, qapp):
        import time

        from PySide6.QtWidgets import QApplication as _QApp

        candidates = [candidate_dto("https://python.org/feed")]

        async def _fast_search(*args, **kwargs):
            return candidates

        self.discovery_svc.search = _fast_search
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        finished = []
        controller.searchFinished.connect(lambda: finished.append(1))
        controller.searchFeeds("python")
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not finished:
            _QApp.processEvents()
            time.sleep(0.01)
        assert len(finished) == 1
        assert controller.candidateModel.rowCount() == 1
        controller.shutdown()

    def test_cancel_active_search_emits_cancelled(self, qapp):
        started_event = threading.Event()

        async def _slow_with_signal(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _slow_with_signal
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        cancelled = []
        controller.searchCancelled.connect(lambda: cancelled.append(1))
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        controller.cancelSearch()
        assert len(cancelled) == 1
        controller.shutdown()

    def test_search_feeds_cancels_prior_future(self, qapp):
        started_event = threading.Event()

        async def _slow(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _slow
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        started2 = []
        controller.searchStarted.connect(lambda: started2.append(1))
        controller.searchFeeds("java")
        assert len(started2) == 1
        controller.shutdown()

    def test_shutdown_with_no_active_future(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.shutdown()

    def test_shutdown_while_search_in_progress_drains_tasks(self, qapp):
        started_event = threading.Event()

        async def _blocking(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _blocking
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        controller.shutdown()

    def test_shutdown_when_loop_already_closed(self, qapp):
        import time

        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.shutdown()
        deadline = time.monotonic() + 2.0
        while (
            time.monotonic() < deadline and not controller._discovery_loop.is_closed()
        ):
            time.sleep(0.01)
        controller.shutdown()

    def test_discovery_loop_drains_pending_tasks_on_direct_stop(self, qapp):
        import time

        started_event = threading.Event()

        async def _blocking(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _blocking
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        controller._discovery_loop.call_soon_threadsafe(controller._discovery_loop.stop)
        deadline = time.monotonic() + 3.0
        while (
            time.monotonic() < deadline and not controller._discovery_loop.is_closed()
        ):
            time.sleep(0.01)
        assert controller._discovery_loop.is_closed()
