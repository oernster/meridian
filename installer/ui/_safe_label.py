"""QLabel with a small size-hint safety buffer for DPI/font edge cases."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QLabel, QStyle, QStyleOption, QStylePainter


class SafeLabel(QLabel):
    def __init__(
        self,
        *args,
        extra_width_px: int = 6,
        extra_height_px: int = 6,
        draw_dx_px: int = 0,
        draw_dy_px: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._extra_width_px = int(extra_width_px)
        self._extra_height_px = int(extra_height_px)
        self._draw_dx_px = int(draw_dx_px)
        self._draw_dy_px = int(draw_dy_px)

    def sizeHint(self) -> QSize:  # noqa: N802
        base = super().sizeHint()
        return QSize(
            base.width() + self._extra_width_px,
            base.height() + self._extra_height_px,
        )

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        base = super().minimumSizeHint()
        return QSize(
            base.width() + self._extra_width_px,
            base.height() + self._extra_height_px,
        )

    def paintEvent(self, event) -> None:  # noqa: ANN001,N802
        if self._draw_dx_px == 0 and self._draw_dy_px == 0:
            super().paintEvent(event)
            return

        painter = QStylePainter(self)

        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

        r = self.contentsRect().adjusted(
            self._draw_dx_px,
            self._draw_dy_px,
            self._draw_dx_px,
            self._draw_dy_px,
        )

        flags = int(self.alignment())
        if self.wordWrap():
            flags |= int(Qt.TextWordWrap)

        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.drawText(r, flags, self.text())
