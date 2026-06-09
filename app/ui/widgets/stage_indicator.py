"""Step-by-step execution stage indicator for Step 5."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.utils.theme import ColorPalette as P

_STAGES = [
    ("load",     "بارگذاری داده"),
    ("domain",   "ساخت domain"),
    ("allocate", "اجرای تخصیص"),
    ("validate", "اعتبارسنجی"),
    ("done",     "تکمیل"),
]

_ICON = {
    "pending": "⬜",
    "running": "⏳",
    "done":    "✅",
    "error":   "❌",
}
_COLOR = {
    "pending": P.TEXT_MUTED,
    "running": P.WARNING_LIGHT,
    "done":    P.SUCCESS_LIGHT,
    "error":   P.ERROR_LIGHT,
}


class StageIndicator(QWidget):
    """Horizontal row of labelled stage badges."""

    def __init__(self) -> None:
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._labels: dict[str, QLabel] = {}
        for key, text in _STAGES:
            lbl = QLabel(f"{_ICON['pending']} {text}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color:{P.TEXT_MUTED}; padding:4px 10px;"
                f"border:1px solid {P.BORDER};"
                f"border-radius:14px; font-size:11px;")
            self._labels[key] = lbl
            lay.addWidget(lbl)
        lay.addStretch()
        self._statuses: dict[str, str] = {k: "pending"
                                          for k, _ in _STAGES}

    def set_stage(self, key: str,
                  status: str = "running") -> None:
        """Update *key* stage to *status* (pending|running|done|error)."""
        self._statuses[key] = status
        lbl = self._labels.get(key)
        if lbl is None:
            return
        text = dict(_STAGES).get(key, key)
        lbl.setText(f"{_ICON.get(status, '?')} {text}")
        color  = _COLOR.get(status, P.TEXT_PRIMARY)
        border = P.BORDER_FOCUS if status == "running" else P.BORDER
        lbl.setStyleSheet(
            f"color:{color}; padding:4px 10px;"
            f"border:1px solid {border};"
            f"border-radius:14px; font-size:11px;")

    def reset(self) -> None:
        """Reset all stages to *pending*."""
        for key in self._labels:
            self.set_stage(key, "pending")
