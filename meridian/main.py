"""Explicit composition root for Meridian."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)

from PySide6.QtCore import QSize, QUrl  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402
from PySide6.QtWebEngineQuick import QtWebEngineQuick  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from meridian.application.services.discovery_service import (  # noqa: E402
    DiscoveryService,
)
from meridian.application.services.item_service import ItemService  # noqa: E402
from meridian.application.services.poll_orchestrator import (  # noqa: E402
    PollOrchestrator,
)
from meridian.application.services.subscription_service import (  # noqa: E402
    SubscriptionService,
)
from meridian.infrastructure.db.session import build_session_factory  # noqa: E402
from meridian.infrastructure.fetching.feedsearch_fetcher import (  # noqa: E402
    FeedsearchFetcher,
)
from meridian.infrastructure.fetching.http_fetcher import HttpFetcher  # noqa: E402
from meridian.infrastructure.fetching.scheduler import PollScheduler  # noqa: E402
from meridian.infrastructure.repositories.sqlite_feed_repository import (  # noqa: E402
    SqliteFeedRepository,
)
from meridian.infrastructure.repositories.sqlite_item_repository import (  # noqa: E402
    SqliteItemRepository,
)
from meridian.infrastructure.repositories.sqlite_poll_state_repository import (  # noqa: E402, E501
    SqlitePollStateRepository,
)
from meridian.ui.bridge import AppController  # noqa: E402
from meridian.version import APP_APPUSERMODELID, __version__  # noqa: E402


def _acquire_single_instance_lock() -> object:
    """Return a mutex handle that keeps this process the sole running instance.

    Returns None on non-Windows platforms (no-op). Exits immediately if another
    instance already holds the mutex (ERROR_ALREADY_EXISTS = 183).
    """
    if sys.platform != "win32":
        return None
    import ctypes

    ERROR_ALREADY_EXISTS = 183
    handle = ctypes.windll.kernel32.CreateMutexW(
        None, False, f"Global\\{APP_APPUSERMODELID}"
    )
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        sys.exit(0)
    return handle


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _BASE = Path(sys._MEIPASS)
    _QML_MAIN = _BASE / "meridian" / "ui" / "qml" / "main.qml"
    _ICON_DIR = _BASE
    _ICON_PATH = _BASE / "meridian.png"
    _LICENCE_PATH = _BASE / "LICENSE"
else:
    _QML_MAIN = Path(__file__).parent / "ui" / "qml" / "main.qml"
    _ICON_DIR = Path(__file__).parent.parent
    _ICON_PATH = _ICON_DIR / "meridian.png"
    _LICENCE_PATH = _ICON_DIR / "LICENSE"

_ICON_SIZES = (16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 96, 128, 256, 512)


def _build_app_icon() -> QIcon:
    icon = QIcon()
    for size in _ICON_SIZES:
        p = _ICON_DIR / f"meridian_{size}.png"
        if p.exists():
            icon.addFile(str(p), QSize(size, size))
    if icon.isNull() and _ICON_PATH.exists():
        icon = QIcon(str(_ICON_PATH))
    return icon


def _read_licence() -> str:
    try:
        return _LICENCE_PATH.read_text(encoding="utf-8")
    except OSError:
        return "Licence text unavailable."


def main() -> None:
    _lock = _acquire_single_instance_lock()  # noqa: F841 — held for process lifetime
    QtWebEngineQuick.initialize()
    QQuickStyle.setStyle("Fusion")
    app = QApplication(sys.argv)
    app.setOrganizationName("Meridian")
    app.setApplicationName("Meridian")
    app.setApplicationVersion(__version__)
    app_icon = _build_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    session_factory = build_session_factory()
    feed_repo = SqliteFeedRepository(session_factory)
    item_repo = SqliteItemRepository(session_factory)
    poll_state_repo = SqlitePollStateRepository(session_factory)
    fetcher = HttpFetcher()

    discovery_fetcher = FeedsearchFetcher()
    sub_svc = SubscriptionService(feed_repo, item_repo)
    item_svc = ItemService(item_repo, feed_repo)
    discovery_svc = DiscoveryService(discovery_fetcher, feed_repo)
    orchestrator = PollOrchestrator(feed_repo, item_repo, poll_state_repo, fetcher)
    controller = AppController(sub_svc, item_svc, discovery_svc)

    async def on_new_items(feed_id: int, count: int) -> None:
        controller.notify_new_items(feed_id, count)

    scheduler = PollScheduler(feed_repo, orchestrator, on_new_items)

    icon_url = (
        QUrl.fromLocalFile(str(_ICON_PATH)).toString() if _ICON_PATH.exists() else ""
    )

    engine = QQmlApplicationEngine()

    # In a PyInstaller frozen build the QML import path must be set explicitly
    # because the engine cannot auto-discover it relative to sys.executable.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        qml_import_path = str(Path(sys._MEIPASS) / "PySide6" / "qml")
        engine.addImportPath(qml_import_path)

    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("appVersion", __version__)
    engine.rootContext().setContextProperty("appIconUrl", icon_url)
    engine.rootContext().setContextProperty("appLicenceText", _read_licence())
    engine.load(QUrl.fromLocalFile(str(_QML_MAIN)))

    if not engine.rootObjects():
        sys.exit(1)

    try:
        import pyi_splash  # type: ignore

        pyi_splash.close()
    except Exception:
        pass

    root_window = engine.rootObjects()[0]
    root_window.raise_()
    root_window.requestActivate()

    scheduler.start_in_thread()
    exit_code = app.exec()
    controller.shutdown()
    if scheduler._loop and not scheduler._loop.is_closed():
        future = asyncio.run_coroutine_threadsafe(fetcher.aclose(), scheduler._loop)
        try:
            future.result(timeout=5)
        except Exception:
            pass
    scheduler.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
