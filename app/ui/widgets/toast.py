"""Transient toast notification that auto-hides after N ms."""
from __future__ import annotations
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PySide6.QtWidgets import QLabel, QWidget

from app.utils.theme import ColorPalette as P

_STYLES: dict[str, str] = {
    "success": f"background:{P.SUCCESS};    color:white",
    "warning": f"background:{P.WARNING};    color:white",
    "error":   f"background:{P.ERROR};      color:white",
    "info":    f"background:{P.ACCENT};     color:white",
}


class Toast(QLabel):
    """Floating notification label — attach to wizard/dialog parent."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWordWrap(True)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, kind: str = "info",
                     duration: int = 3000) -> None:
        """Display *text* as a toast of *kind* for *duration* ms."""
        base = _STYLES.get(kind, _STYLES["info"])
        self.setStyleSheet(
            f"{base}; padding:12px 22px; border-radius:10px;"
            "font-weight:bold; font-size:13px;"
            "font-family:'Vazirmatn','Tahoma',sans-serif;")
        self.setText(text)
        self.adjustSize()
        pw = self.parent()
        if pw:
            x = pw.width()  - self.width()  - 20
            y = pw.height() - self.height() - 50
            self.move(x, y)
        self.show()
        self.raise_()
        self._timer.stop()
        self._timer.start(duration)
