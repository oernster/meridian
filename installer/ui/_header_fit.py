"""Resilient header sizing for the installer UI.

Centralizes header sizing logic to keep InstallerMainWindow small and handle
Windows DPI/font metric edge cases that can produce 1-2px glyph clipping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication


@dataclass(slots=True)
class HeaderFitController:
    """Ensure the installer header title is never visually truncated."""

    window: Any
    title_attr: str = "_header_title"
    _scheduled: bool = False
    _in_progress: bool = False

    def on_theme_applied(self) -> None:
        title = getattr(self.window, self.title_attr, None)
        if title is None:
            return

        f: QFont = title.font()
        base_px = f.pixelSize() if f.pixelSize() > 0 else None
        base_pt = f.pointSizeF() if f.pointSizeF() > 0 else None
        title.setProperty("_base_header_font_px", base_px)
        title.setProperty("_base_header_font_pt", base_pt)

        # A size hint is unavailable until the label has been laid out at least
        # once. Skipping the floor here costs nothing: `_ensure_fits` runs again
        # on the next resize and sets it then.
        try:
            title.setMinimumSize(title.sizeHint())
        except Exception:
            pass

    def schedule(self) -> None:
        if self._scheduled:
            return
        self._scheduled = True
        QTimer.singleShot(0, self._ensure_fits)
        QTimer.singleShot(50, self._ensure_fits)

    def ensure_now(self) -> None:
        self._ensure_fits()

    def should_watch_event_type(self, et) -> bool:  # noqa: ANN001
        watched = {
            QEvent.Type.ScreenChangeInternal,
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
            QEvent.Type.ApplicationFontChange,
        }
        dpi_change = getattr(QEvent.Type, "DpiChange", None)
        if dpi_change is not None:
            watched.add(dpi_change)
        return et in watched

    def _ensure_fits(self) -> None:
        self._scheduled = False
        if self._in_progress:
            return

        w = self.window
        title = getattr(w, self.title_attr, None)
        if title is None:
            return
        if not w.isVisible():
            return

        self._in_progress = True
        try:
            QApplication.processEvents()

            missing_w, missing_h = self._ensure_label_has_bbox_room(title)
            if self._fits(title):
                return

            self._try_grow_window(missing_w=missing_w, missing_h=missing_h)
            self._ensure_window_minimum_for_layout()
            if self._fits(title):
                return

            self._shrink_font_until_fit(title)
            self._ensure_window_minimum_for_layout()
        finally:
            self._in_progress = False

    def _ensure_window_minimum_for_layout(self) -> None:
        w = self.window
        cw = w.centralWidget()
        if cw is None:
            return

        hint = cw.sizeHint()
        if not hint.isValid():
            return

        screen = w.screen() or QApplication.primaryScreen()
        if screen is not None:
            max_w = int(screen.availableGeometry().width() * 0.98)
            max_h = int(screen.availableGeometry().height() * 0.98)
        else:
            max_w = w.width()
            max_h = w.height()

        min_w = min(max_w, max(w.minimumWidth(), hint.width()))
        min_h = min(max_h, max(w.minimumHeight(), hint.height()))
        w.setMinimumSize(min_w, min_h)

        target_w = min(max_w, max(w.width(), min_w))
        target_h = min(max_h, max(w.height(), min_h))
        if target_w != w.width() or target_h != w.height():
            w.resize(target_w, target_h)
            QApplication.processEvents()

    @staticmethod
    def _fits(title) -> bool:  # noqa: ANN001
        fm = QFontMetrics(title.font())

        available = max(0, title.contentsRect().width())
        elided = fm.elidedText(title.text(), Qt.ElideRight, available)
        if elided != title.text():
            return False

        # Tight bounds need a glyph raster, which some fonts decline to give.
        # Reporting "it fits" is the safe answer: the elision check above has
        # already passed, so the worst case is a header that is not shrunk
        # further rather than one that is clipped.
        try:
            tight = fm.tightBoundingRect(title.text())
            return title.contentsRect().width() >= int(
                tight.width() + 4
            ) and title.contentsRect().height() >= int(tight.height() + 4)
        except Exception:
            return True

    @staticmethod
    def _tight_requirements_px(title) -> tuple[int, int]:  # noqa: ANN001
        fm = QFontMetrics(title.font())
        # Same missing raster as above. Advance width plus line height is a
        # looser measure of the same thing, so the header is given slightly
        # more room than it needs rather than none.
        try:
            tight = fm.tightBoundingRect(title.text())
            req_w = int(tight.width() + 6)
            req_h = int(tight.height() + 6)
        except Exception:
            req_w = int(fm.horizontalAdvance(title.text()) + 10)
            req_h = int(fm.height() + 6)
        return req_w, req_h

    def _ensure_label_has_bbox_room(self, title) -> tuple[int, int]:  # noqa: ANN001
        req_w, req_h = self._tight_requirements_px(title)
        have_w = max(0, title.contentsRect().width())
        have_h = max(0, title.contentsRect().height())

        missing_w = max(0, req_w - have_w)
        missing_h = max(0, req_h - have_h)

        if missing_h > 0:
            title.setMinimumHeight(max(title.minimumHeight(), req_h))
        if missing_w > 0:
            title.setMinimumWidth(max(title.minimumWidth(), req_w))

        return missing_w, missing_h

    def _try_grow_window(self, *, missing_w: int, missing_h: int) -> None:
        w = self.window

        screen = w.screen() or QApplication.primaryScreen()
        if screen is not None:
            max_w = int(screen.availableGeometry().width() * 0.98)
            max_h = int(screen.availableGeometry().height() * 0.98)
        else:
            max_w = w.width()
            max_h = w.height()

        if missing_w > 0 and w.width() < max_w:
            new_w = min(max_w, w.width() + missing_w + 24)
            if new_w > w.width():
                w.setMinimumWidth(new_w)
                w.resize(new_w, w.height())
                QApplication.processEvents()

        if missing_h > 0 and w.height() < max_h:
            new_h = min(max_h, w.height() + missing_h + 16)
            if new_h > w.height():
                w.setMinimumHeight(new_h)
                w.resize(w.width(), new_h)
                QApplication.processEvents()

    def _shrink_font_until_fit(self, title) -> None:  # noqa: ANN001
        base_px = title.property("_base_header_font_px")
        base_pt = title.property("_base_header_font_pt")

        if not base_px and not base_pt:
            cur = title.font()
            base_px = cur.pixelSize() if cur.pixelSize() > 0 else None
            base_pt = cur.pointSizeF() if cur.pointSizeF() > 0 else None

        f = QFont(title.font())
        if base_px:
            size = int(base_px)
            min_px = 22
            while size > min_px:
                size -= 1
                f.setPixelSize(size)
                title.setFont(f)
                QApplication.processEvents()
                self._ensure_label_has_bbox_room(title)
                if self._fits(title):
                    return
        elif base_pt:
            size = float(base_pt)
            min_pt = 10.0
            while size > min_pt:
                size -= 0.5
                f.setPointSizeF(size)
                title.setFont(f)
                QApplication.processEvents()
                self._ensure_label_has_bbox_room(title)
                if self._fits(title):
                    return
