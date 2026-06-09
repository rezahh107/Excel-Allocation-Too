"""Drag & drop allocation tree: mentors → students.

Enhancement:
    - valid drop targets are highlighted in green during drag
    - full mentors are highlighted in red
    - students are paged with show_more()
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem

from app.core.models import AllocationResult
from app.utils.theme import ColorPalette as P

ROLE_STUDENT_IDX = Qt.ItemDataRole.UserRole + 1
ROLE_MENTOR_NAME = Qt.ItemDataRole.UserRole + 2

_PAGE_SIZE = 20


class AllocationTree(QTreeWidget):
    """Top-level items = mentors, children = students, paged globally.

    Emits:
        moveRequested(student_idx, old_mentor, new_mentor)
    """

    moveRequested = Signal(int, str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setColumnCount(3)
        self.setHeaderLabels(
            ["پشتیبان / دانش‌آموز", "پشتیبان اولیه", "وضعیت"]
        )
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)

        self._result: AllocationResult | None = None
        self._offset: int = _PAGE_SIZE
        self._mentor_items: dict[str, QTreeWidgetItem] = {}

    # ── public ──────────────────────────────────────────────────
    def load(self, result: AllocationResult) -> None:
        """Populate from an allocation result."""
        self._result = result
        self._offset = _PAGE_SIZE
        self.reload()

    def reload(self) -> None:
        """Rebuild the tree from the current result state."""
        if self._result is None:
            return

        self.clear()
        self._mentor_items.clear()

        shown = 0
        for mentor in self._result.mentors:
            load = len(self._result.assigned.get(mentor.name, []))
            cap = self._result.capacity
            pct = load / cap if cap else 0

            icon = (
                "🔴" if pct >= 1.0 else
                "🟡" if pct >= 0.8 else
                "🟢"
            )
            bar_len = 10
            filled = min(bar_len, int(pct * bar_len))
            bar = "█" * filled + "░" * (bar_len - filled)

            top = QTreeWidgetItem([
                f"{icon}  {mentor.name}",
                "",
                f"[{bar}]  {load}/{cap}",
            ])
            top.setData(0, ROLE_MENTOR_NAME, mentor.name)
            top.setFlags(
                (top.flags() | Qt.ItemFlag.ItemIsDropEnabled)
                & ~Qt.ItemFlag.ItemIsDragEnabled
            )

            color = (
                QColor(P.ERROR) if pct >= 1.0 else
                QColor(P.WARNING) if pct >= 0.8 else
                QColor(P.SUCCESS_LIGHT)
            )
            top.setForeground(0, color)
            top.setForeground(2, color)
            top.setToolTip(
                0,
                f"بار فعلی: {load} از ظرفیت {cap}"
            )
            top.setToolTip(
                2,
                f"بار فعلی: {load} از ظرفیت {cap}"
            )

            self.addTopLevelItem(top)
            self._mentor_items[mentor.name] = top

        for mentor_name, idxs in self._result.assigned.items():
            parent = self._mentor_items.get(mentor_name)
            if parent is None:
                continue

            for student_idx in idxs:
                if shown >= self._offset:
                    break

                student = self._result.students[student_idx]
                stable = student_idx in self._result.stabilized
                full_name = (
                    f"{student.first} {student.last}".strip()
                    or student.counter
                )

                child = QTreeWidgetItem([
                    full_name,
                    student.initial_supporter,
                    "تثبیت‌شده 🔒" if stable else "قابل انتقال",
                ])
                child.setData(0, ROLE_STUDENT_IDX, student_idx)

                flags = child.flags() & ~Qt.ItemFlag.ItemIsDropEnabled
                if stable:
                    flags &= ~Qt.ItemFlag.ItemIsDragEnabled
                    child.setForeground(2, QColor(P.TEXT_MUTED))
                    child.setToolTip(
                        0,
                        "این دانش‌آموز تثبیت‌شده است و قابل انتقال نیست."
                    )
                else:
                    flags |= Qt.ItemFlag.ItemIsDragEnabled
                    child.setForeground(2, QColor(P.SUCCESS_LIGHT))
                    child.setToolTip(
                        0,
                        "برای انتقال، این دانش‌آموز را روی پشتیبان مقصد رها کنید."
                    )

                child.setFlags(flags)
                parent.addChild(child)
                shown += 1

            # Continue outer loop so all mentor headers remain visible.
            # Student rows stop globally at self._offset.

        self.expandAll()

    def show_more(self) -> None:
        """Increase visible student limit and reload."""
        if self._result is None:
            return
        self._offset = min(
            self._offset + _PAGE_SIZE,
            self.total_students_count(),
        )
        self.reload()

    def visible_students_count(self) -> int:
        """Return number of currently visible student rows."""
        return min(self._offset, self.total_students_count())

    def total_students_count(self) -> int:
        """Return total student count for current result."""
        if self._result is None:
            return 0
        return int(getattr(self._result, "total_students", 0) or 0)

    def can_show_more(self) -> bool:
        """Whether there are hidden students left."""
        return self.visible_students_count() < self.total_students_count()

    # ── drag highlight ──────────────────────────────────────────
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.ignore()
            return
        self._highlight_targets()
        super().dragEnterEvent(event)

    def dragLeaveEvent(self, event):  # noqa: N802
        self._reset_highlights()
        super().dragLeaveEvent(event)

    def _highlight_targets(self) -> None:
        if self._result is None:
            return

        cap = self._result.capacity
        for mentor_name, top in self._mentor_items.items():
            load = len(self._result.assigned.get(mentor_name, []))
            if load < cap:
                color = QColor(P.SUCCESS + "44")
            else:
                color = QColor(P.ERROR + "44")

            for col in range(self.columnCount()):
                top.setBackground(col, color)

    def _reset_highlights(self) -> None:
        for top in self._mentor_items.values():
            for col in range(self.columnCount()):
                top.setBackground(col, QColor(0, 0, 0, 0))

    # ── drop ────────────────────────────────────────────────────
    def dropEvent(self, event):  # noqa: N802
        self._reset_highlights()

        item = self.currentItem()
        if item is None or item.data(0, ROLE_STUDENT_IDX) is None:
            event.ignore()
            return

        target = self.itemAt(event.position().toPoint())
        if target is None:
            event.ignore()
            return

        mentor_item = target
        while (
            mentor_item is not None
            and mentor_item.data(0, ROLE_MENTOR_NAME) is None
        ):
            mentor_item = mentor_item.parent()

        if mentor_item is None:
            event.ignore()
            return

        new_mentor = mentor_item.data(0, ROLE_MENTOR_NAME)

        old_parent = item.parent()
        old_mentor = (
            old_parent.data(0, ROLE_MENTOR_NAME)
            if old_parent
            else ""
        )
        student_idx = item.data(0, ROLE_STUDENT_IDX)

        # Prevent Qt from moving item visually; the command/result reload owns
        # the real state transition.
        event.ignore()

        if new_mentor and new_mentor != old_mentor:
            self.moveRequested.emit(student_idx, old_mentor, new_mentor)
