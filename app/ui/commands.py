"""Undoable commands for manual student reassignment."""
from __future__ import annotations
from typing import Callable

from PySide6.QtGui import QUndoCommand

from app.core.models import AllocationResult
from app.utils.logger import get_logger

log = get_logger("commands")


class ReassignCommand(QUndoCommand):
    """Move a student from one mentor to another (fully undoable)."""

    def __init__(self, result: AllocationResult, student_idx: int,
                 old_mentor: str, new_mentor: str,
                 on_change: Callable[[], None]) -> None:
        student = result.students[student_idx]
        full_name = (f"{student.first} {student.last}".strip()
                     or student.counter)
        super().__init__(
            f"انتقال {full_name}: {old_mentor} → {new_mentor}")
        self._result    = result
        self._idx       = student_idx
        self._old       = old_mentor
        self._new       = new_mentor
        self._on_change = on_change

    # ── helpers ──────────────────────────────────────────────────
    def _apply(self, frm: str, to: str) -> None:
        if frm and self._idx in self._result.assigned.get(frm, []):
            self._result.assigned[frm].remove(self._idx)
        self._result.assigned.setdefault(to, []).append(self._idx)
        self._result.students[self._idx].final_supporter = to
        log.debug("انتقال: idx=%d  %s → %s", self._idx, frm, to)
        self._on_change()

    def redo(self) -> None:  # noqa: D102
        self._apply(self._old, self._new)

    def undo(self) -> None:  # noqa: D102
        self._apply(self._new, self._old)
