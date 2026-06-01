"""Explicit composition root for Meridian."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from meridian.application.services.item_service import ItemService
from meridian.application.services.poll_orchestrator import PollOrchestrator
from meridian.application.services.subscription_service import SubscriptionService
from meridian.infrastructure.db.session import build_session_factory
from meridian.infrastructure.fetching.http_fetcher import HttpFetcher
from meridian.infrastructure.fetching.scheduler import PollScheduler
from meridian.infrastructure.repositories.sqlite_feed_repository import SqliteFeedRepository
from meridian.infrastructure.repositories.sqlite_item_repository import SqliteItemRepository
from meridian.infrastructure.repositories.sqlite_poll_state_repository import SqlitePollStateRepository
from meridian.ui.bridge import AppController

_QML_MAIN = Path(__file__).parent / "ui" / "qml" / "main.qml"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Meridian")
    app.setApplicationVersion("0.1.0")

    session_factory = build_session_factory()
    feed_repo = SqliteFeedRepository(session_factory)
    item_repo = SqliteItemRepository(session_factory)
    poll_state_repo = SqlitePollStateRepository(session_factory)
    fetcher = HttpFetcher()

    sub_svc = SubscriptionService(feed_repo, item_repo)
    item_svc = ItemService(item_repo, feed_repo)
    orchestrator = PollOrchestrator(feed_repo, item_repo, poll_state_repo, fetcher)
    controller = AppController(sub_svc, item_svc)

    async def on_new_items(feed_id: int, count: int) -> None:
        controller.notify_new_items(feed_id, count)

    scheduler = PollScheduler(feed_repo, orchestrator, on_new_items)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(_QML_MAIN)))

    if not engine.rootObjects():
        sys.exit(1)

    scheduler.start_in_thread()
    exit_code = app.exec()
    scheduler.stop()
    asyncio.run(fetcher.aclose())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
