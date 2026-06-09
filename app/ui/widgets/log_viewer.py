"""Colour-coded log viewer with timestamps, filters and actions."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.utils.theme import ColorPalette as P

_COLORS = {
    "INFO": P.SUCCESS_LIGHT,
    "WARNING": P.WARNING_LIGHT,
    "ERROR": P.ERROR_LIGHT,
}


class LogViewer(QWidget):
    """Filterable, colour-coded log list with basic operations."""

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[tuple[str, str, str]] = []
        self._filter: str | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # top action/filter bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        self.filter_all_btn = self._make_small_button("ALL")
        self.filter_info_btn = self._make_small_button("INFO")
        self.filter_warning_btn = self._make_small_button("WARNING")
        self.filter_error_btn = self._make_small_button("ERROR")

        self.filter_all_btn.clicked.connect(
            lambda: self._set_filter("ALL")
        )
        self.filter_info_btn.clicked.connect(
            lambda: self._set_filter("INFO")
        )
        self.filter_warning_btn.clicked.connect(
            lambda: self._set_filter("WARNING")
        )
        self.filter_error_btn.clicked.connect(
            lambda: self._set_filter("ERROR")
        )

        top_bar.addWidget(self.filter_all_btn)
        top_bar.addWidget(self.filter_info_btn)
        top_bar.addWidget(self.filter_warning_btn)
        top_bar.addWidget(self.filter_error_btn)
        top_bar.addStretch()

        self.copy_btn = self._make_small_button("کپی همه")
        self.clear_btn = self._make_small_button("پاک کردن")

        self.copy_btn.clicked.connect(self.copy_all)
        self.clear_btn.clicked.connect(self.clear_logs)

        top_bar.addWidget(self.copy_btn)
        top_bar.addWidget(self.clear_btn)

        lay.addLayout(top_bar)

        # counters row
        counters = QHBoxLayout()
        counters.setSpacing(10)

        self.info_count_lbl = QLabel()
        self.warn_count_lbl = QLabel()
        self.error_count_lbl = QLabel()

        self.info_count_lbl.setStyleSheet(f"color:{P.SUCCESS_LIGHT};")
        self.warn_count_lbl.setStyleSheet(f"color:{P.WARNING_LIGHT};")
        self.error_count_lbl.setStyleSheet(f"color:{P.ERROR_LIGHT};")

        counters.addWidget(self.info_count_lbl)
        counters.addWidget(self.warn_count_lbl)
        counters.addWidget(self.error_count_lbl)
        counters.addStretch()

        lay.addLayout(counters)

        self.list = QListWidget()
        lay.addWidget(self.list)

        self._update_counters()
        self._update_filter_button_states()

    def add(self, level: str, message: str) -> None:
        """Append a new log entry."""
        normalized = (level or "INFO").upper().strip()
        if normalized not in _COLORS:
            normalized = "INFO"

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._entries.append((timestamp, normalized, message))
        self._update_counters()
        self._render_last()

    def clear_logs(self) -> None:
        """Remove all log entries."""
        self._entries.clear()
        self.list.clear()
        self._update_counters()

    def copy_all(self) -> None:
        """Copy currently stored logs to clipboard."""
        lines = [
            f"[{ts}] [{lvl}] {msg}"
            for ts, lvl, msg in self._entries
        ]
        text = "\n".join(lines).strip()
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    def _set_filter(self, level: str) -> None:
        self._filter = None if level == "ALL" else level
        self._update_filter_button_states()
        self._render_all()

    def _render_last(self) -> None:
        if self._entries:
            ts, lvl, msg = self._entries[-1]
            if not self._filter or self._filter == lvl:
                self._add_item(ts, lvl, msg)
        self.list.scrollToBottom()

    def _render_all(self) -> None:
        self.list.clear()
        for ts, lvl, msg in self._entries:
            if self._filter and lvl != self._filter:
                continue
            self._add_item(ts, lvl, msg)
        self.list.scrollToBottom()

    def _add_item(self, ts: str, lvl: str, msg: str) -> None:
        item = QListWidgetItem(f"[{ts}] [{lvl}]  {msg}")
        item.setForeground(QColor(_COLORS.get(lvl, P.TEXT_PRIMARY)))
        self.list.addItem(item)

    def _update_counters(self) -> None:
        info_count = sum(1 for _, lvl, _ in self._entries if lvl == "INFO")
        warn_count = sum(1 for _, lvl, _ in self._entries if lvl == "WARNING")
        error_count = sum(1 for _, lvl, _ in self._entries if lvl == "ERROR")

        self.info_count_lbl.setText(f"INFO: {info_count}")
        self.warn_count_lbl.setText(f"WARNING: {warn_count}")
        self.error_count_lbl.setText(f"ERROR: {error_count}")

    def _update_filter_button_states(self) -> None:
        current = self._filter or "ALL"
        mapping = {
            "ALL": self.filter_all_btn,
            "INFO": self.filter_info_btn,
            "WARNING": self.filter_warning_btn,
            "ERROR": self.filter_error_btn,
        }
        for key, btn in mapping.items():
            btn.setEnabled(key != current)

    @staticmethod
    def _make_small_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("btn_secondary")
        btn.setFixedHeight(28)
        return btn
