from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout


class FlowLayout(QLayout):
    """Layout tipo flujo para pools de widgets pequenos."""

    def __init__(self, parent=None, spacing: int = 4):
        super().__init__(parent)
        self._spacing = spacing
        self._items = []

    def addItem(self, item) -> None:
        self._items.append(item)
        self.invalidate()
        parent = self.parentWidget()
        if parent is not None:
            parent.updateGeometry()
            parent.update()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            parent = self.parentWidget()
            if parent is not None:
                parent.updateGeometry()
                parent.update()
            return item
        return None

    def removeItem(self, item) -> None:
        if item in self._items:
            self._items.remove(item)
            self.invalidate()
            parent = self.parentWidget()
            if parent is not None:
                parent.updateGeometry()
                parent.update()

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def setSpacing(self, spacing: int) -> None:
        self._spacing = spacing

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            widget = item.widget()
            if widget and not widget.isVisible():
                continue

            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._spacing
            if next_x - self._spacing > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y += line_height + self._spacing
                next_x = x + item_size.width() + self._spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))

            x = next_x
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y() + bottom
