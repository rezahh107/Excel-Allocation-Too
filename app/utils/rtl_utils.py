"""RTL helpers for Persian UI."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget


def apply_rtl(widget: QWidget) -> None:
    """Force RTL layout direction on a widget."""
    widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)


def apply_app_rtl(app: QApplication) -> None:
    """Apply RTL globally to the application."""
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
